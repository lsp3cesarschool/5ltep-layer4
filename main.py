"""
Main Orchestrator — 5L-TEP Layer 4 Provenance Toolkit
======================================================
Entry point for the GitHub Actions workflow. Runs the L4 pipeline:

  1. Harvest datasets from CKAN portal (package_list + package_show)
  2. Detect changes via SHA-256 hashing (4-type classification)
  3. Map changes to W3C PROV-DM records (L4 — core contribution)
  4. Save provenance logs to append-only Git repository

This toolkit implements ONLY Layer 4 (Observability & Provenance) of the
Five-Layer Trust Engineering Pyramid (5L-TEP). Layers 1–3 (structural,
semantic, anomaly validation) and Layer 5 (governance dashboards) are
outside this implementation's scope.

Usage (local):
    python main.py --portal https://dadosabertos.ibama.gov.br

Usage (GitHub Actions):
    Triggered automatically via .github/workflows/monitor.yml (cron 6h)

References:
    Pinheiro & Sérgio (2026). 5L-TEP: A Five-Layer Trust Engineering
    Pyramid for Open Government Data. SOFTENG 2026.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add src/ to path for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from ckan_harvester import CKANHarvester
from hash_engine import HashEngine, ChangeType, Severity
from prov_mapper import ProvMapper

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("5ltep.main")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")
HASHES_FILE = DATA_DIR / "hash_store.json"
PROV_DIR = Path("provenance_logs")
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
MANIFEST_FILE = SNAPSHOTS_DIR / "manifest.json"

for d in [DATA_DIR, PROV_DIR, SNAPSHOTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------

def _load_manifest() -> Dict[str, Dict[str, str]]:
    """Load the snapshot deduplication manifest."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"runs": {}, "snapshots": {}}


def _save_manifest(manifest: Dict[str, Dict[str, str]]) -> None:
    """Persist the snapshot deduplication manifest."""
    with open(MANIFEST_FILE, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)


def save_snapshot(datasets: List[Dict[str, Any]], run_id: str) -> Path:
    """Persist harvested dataset snapshots, deduplicating identical content.

    Snapshots are content-addressed: a new file is written only when its
    SHA-256 differs from any previously stored snapshot. Otherwise, only
    a reference is recorded in `manifest.json`, mapping the current run_id
    to the pre-existing snapshot file. This preserves full auditability
    while avoiding redundant storage when portal data is unchanged.
    """
    content = json.dumps(datasets, indent=2, ensure_ascii=False)
    snapshot_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    manifest = _load_manifest()

    if snapshot_hash in manifest["snapshots"]:
        existing_file = manifest["snapshots"][snapshot_hash]
        manifest["runs"][run_id] = snapshot_hash
        _save_manifest(manifest)
        logger.info(
            "Snapshot identical to %s — reference recorded (no file written)",
            existing_file,
        )
        return SNAPSHOTS_DIR / existing_file

    snap_file = f"snapshot_{run_id}.json"
    snap_path = SNAPSHOTS_DIR / snap_file
    with open(snap_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    manifest["snapshots"][snapshot_hash] = snap_file
    manifest["runs"][run_id] = snapshot_hash
    _save_manifest(manifest)
    logger.info("Snapshot saved: %s (hash %s...)", snap_file, snapshot_hash[:12])
    return snap_path


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    portal_url: str,
    org_filter: str = "",
    dry_run: bool = False,
    max_datasets: int = 0,
) -> Dict[str, Any]:
    """Execute the L4 provenance monitoring pipeline.

    Implements the workflow described in the KDMiLe 2026 paper (Section 3.5):
    (1) harvest metadata; (2) compute SHA-256 fingerprints;
    (3) classify changes (4 types); (4) generate PROV-DM records;
    (5) commit updated provenance logs.

    Parameters
    ----------
    portal_url  : Root URL of the CKAN portal.
    org_filter  : If set, only process datasets from this organization.
    dry_run     : If True, skip persisting results (useful for testing).
    max_datasets: If > 0, limit harvest to this many datasets.

    Returns
    -------
    Summary dict with counts and paths.
    """
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    logger.info("=== L4 Provenance Pipeline Run %s ===", run_id)
    logger.info("Portal: %s | Org filter: '%s' | Dry run: %s",
                portal_url, org_filter, dry_run)

    # ------------------------------------------------------------------
    # Step 1 – Harvest (CKAN Harvester)
    # ------------------------------------------------------------------
    logger.info("Step 1/3 — Harvesting datasets from CKAN portal...")
    harvester = CKANHarvester(portal_url)

    if max_datasets > 0:
        dataset_ids = harvester.list_datasets()[:max_datasets]
        datasets = []
        for did in dataset_ids:
            try:
                datasets.append(harvester.get_dataset_metadata(did))
            except Exception as e:
                logger.error("Failed to harvest '%s': %s", did, e)
                datasets.append({"id": did, "_error": str(e)})
    else:
        datasets = harvester.harvest_all()

    if org_filter:
        datasets = [
            d for d in datasets
            if d.get("organization", {}).get("name", "") == org_filter
        ]
        logger.info("Filtered to %d datasets for org '%s'", len(datasets), org_filter)

    if not datasets:
        logger.warning("No datasets harvested. Exiting.")
        return {"run_id": run_id, "datasets": 0, "changes": 0, "prov_records": 0}

    if not dry_run:
        save_snapshot(datasets, run_id)

    # ------------------------------------------------------------------
    # Step 2 – Hash Engine (change detection, Section 3.2)
    # ------------------------------------------------------------------
    logger.info("Step 2/3 — Running Hash Engine on %d datasets...", len(datasets))
    hash_engine = HashEngine(
        hash_store_path=str(HASHES_FILE),
        portal_url=portal_url,
    )
    change_events = hash_engine.detect_changes(datasets)
    logger.info("Processed %d datasets for change detection.", len(change_events))

    # Filter meaningful events (exclude CLEAN_UPDATE baselines)
    meaningful_events = [
        e for e in change_events
        if e.change_type != ChangeType.CLEAN_UPDATE
    ]
    logger.info("Meaningful changes (non-CLEAN_UPDATE): %d", len(meaningful_events))

    # Isolate CRITICAL events (SCHEMA_DRIFT, RETRO_ALTER) — the core L4 concern
    critical_events = [
        e for e in meaningful_events
        if e.severity == Severity.CRITICAL
    ]
    if critical_events:
        logger.warning(
            "CRITICAL changes detected (%d): %s",
            len(critical_events),
            ", ".join(f"{e.dataset_id}={e.change_type.value}" for e in critical_events),
        )

    # ------------------------------------------------------------------
    # Step 3 – PROV-DM Mapper (L4 Core Contribution, Section 3.3)
    # ------------------------------------------------------------------
    logger.info("Step 3/3 — Mapping changes to W3C PROV-DM records (L4 core)...")
    prov_mapper = ProvMapper(
        provenance_dir=str(PROV_DIR),
        repository_url=os.environ.get("GITHUB_REPOSITORY", "local"),
        commit_sha=os.environ.get("GITHUB_SHA", "local"),
    )

    if meaningful_events:
        prov_records = prov_mapper.generate_records(meaningful_events)
        if not dry_run:
            saved_paths = prov_mapper.save_records(meaningful_events)
            logger.info(
                "Generated %d PROV-DM records, saved to %d files",
                len(prov_records), len(saved_paths),
            )
        else:
            logger.info("Dry run — %d records generated but not persisted.", len(prov_records))
        prov_summary = prov_mapper.get_summary(meaningful_events)
    else:
        prov_records = []
        prov_summary = {"total_datasets": 0}
        logger.info("No meaningful changes — no PROV-DM records generated.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    summary = {
        "run_id": run_id,
        "portal": portal_url,
        "scope": "Layer 4 — Observability & Provenance",
        "datasets_harvested": len(datasets),
        "change_events": len(meaningful_events),
        "critical_events": len(critical_events),
        "critical_datasets": [
            {"dataset_id": e.dataset_id, "change_type": e.change_type.value}
            for e in critical_events
        ],
        "prov_records": len(prov_records),
    }

    logger.info("=== Run %s complete ===", run_id)
    logger.info(
        "Datasets: %d | Changes: %d | PROV records: %d",
        summary["datasets_harvested"],
        summary["change_events"],
        summary["prov_records"],
    )

    return summary


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="5L-TEP Layer 4 — Provenance & Observability Monitoring Toolkit"
    )
    parser.add_argument(
        "--portal",
        default=os.environ.get("CKAN_PORTAL_URL", "https://dadosabertos.ibama.gov.br"),
        help="CKAN portal base URL (or set CKAN_PORTAL_URL env var)",
    )
    parser.add_argument(
        "--org",
        default=os.environ.get("CKAN_ORG_FILTER", ""),
        help="Filter datasets by organization name",
    )
    parser.add_argument(
        "--max-datasets",
        type=int,
        default=int(os.environ.get("MAX_DATASETS", "0")),
        help="Limit harvest to N datasets (0 = all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run pipeline without persisting results",
    )
    return parser.parse_args()


def _emit_github_output(summary: Dict[str, Any]) -> None:
    """Expose critical-change signals to the GitHub Actions workflow.

    Writes to the file referenced by $GITHUB_OUTPUT (when running in CI) so a
    later workflow step can alert on CRITICAL events WITHOUT failing this
    process — keeping the provenance-log commit step intact regardless.
    """
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    n_critical = summary.get("critical_events", 0)
    affected = "; ".join(
        f"{c['dataset_id']} ({c['change_type']})"
        for c in summary.get("critical_datasets", [])
    )
    # Sanitized filenames matching ProvMapper.save_records, for direct links
    # to the affected provenance logs in the alert workflow step.
    affected_files = ",".join(
        c["dataset_id"].replace("/", "_").replace("\\", "_") + ".jsonld"
        for c in summary.get("critical_datasets", [])
    )
    with open(github_output, "a", encoding="utf-8") as fh:
        fh.write(f"critical={'true' if n_critical > 0 else 'false'}\n")
        fh.write(f"critical_events={n_critical}\n")
        fh.write(f"critical_datasets={affected}\n")
        fh.write(f"critical_dataset_files={affected_files}\n")


if __name__ == "__main__":
    args = parse_args()
    summary = run_pipeline(
        portal_url=args.portal,
        org_filter=args.org,
        dry_run=args.dry_run,
        max_datasets=args.max_datasets,
    )
    print(json.dumps(summary, indent=2))
    _emit_github_output(summary)
