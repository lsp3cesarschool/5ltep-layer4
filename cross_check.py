"""
Cross-Check — 5L-TEP Layer 4 Toolkit
=====================================
Independent validator that compares the live CKAN portal against the most
recent committed snapshot using the portal's own metadata_modified timestamp
and num_resources count — fields that are set by the data custodian, not
by this toolkit. This provides empirical triangulation of the main
pipeline's change-detection results.

Runs in parallel to main.py (separate workflow, no shared state at runtime),
writes data/cross_check_report.json, and updates a status sentence in
README.md between dedicated markers.

Exit codes:
  0  IN_SYNC   — live matches latest snapshot exactly
  0  PENDING   — divergences exist but snapshot is fresh (< tolerance window)
  0  DEGRADED  — some transient fetch failures but coverage above threshold
  1  STALE     — divergences exist and snapshot is older than tolerance window
  1  ERROR     — fetch coverage below threshold or package_list failed
"""

import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PORTAL = "https://dadosabertos.ibama.gov.br"
MANIFEST = Path("data/snapshots/manifest.json")
SNAPSHOTS_DIR = Path("data/snapshots")
REPORT = Path("data/cross_check_report.json")
README = Path("README.md")
USER_AGENT = "5LTEP-Layer4/1.0 (parallel cross-check)"
MONITOR_TOLERANCE_HOURS = 7
MIN_COVERAGE_RATIO = 0.90
FETCH_RETRIES = 3
FETCH_BACKOFF_SECONDS = 1.5

MARKER_START = "<!-- CROSS_CHECK_STATUS:START -->"
MARKER_END = "<!-- CROSS_CHECK_STATUS:END -->"


def fetch(url: str) -> dict:
    last_exc = None
    for attempt in range(FETCH_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last_exc = e
            if e.code < 500 or attempt == FETCH_RETRIES - 1:
                raise
            time.sleep(FETCH_BACKOFF_SECONDS * (2 ** attempt))
        except (urllib.error.URLError, TimeoutError) as e:
            last_exc = e
            if attempt == FETCH_RETRIES - 1:
                raise
            time.sleep(FETCH_BACKOFF_SECONDS * (2 ** attempt))
    raise last_exc


def load_snapshot(path: Path) -> list:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def latest_snapshot_path():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    latest_run = max(manifest["runs"].keys())
    snap_hash = manifest["runs"][latest_run]
    return latest_run, SNAPSHOTS_DIR / manifest["snapshots"][snap_hash]


def render_status(divergences, snapshot_age_h, shared, errors, coverage, ended):
    ts = ended.strftime("%Y-%m-%d %H:%M UTC")
    cov_pct = coverage * 100
    if coverage < MIN_COVERAGE_RATIO:
        return "ERROR", 1, (
            f"❌ **Cross-check error** — last attempt {ts}; coverage {cov_pct:.0f}% "
            f"below {MIN_COVERAGE_RATIO * 100:.0f}% threshold ({errors} fetch failure(s)). "
            f"See `data/cross_check_report.json`."
        )
    note = "" if errors == 0 else f" Coverage: {cov_pct:.0f}% ({errors} transient fetch error(s))."
    if divergences == 0:
        emoji = "✅" if errors == 0 else "🟡"
        label = "passing" if errors == 0 else "degraded"
        return ("IN_SYNC" if errors == 0 else "DEGRADED"), 0, (
            f"{emoji} **Cross-check {label}** — last verified {ts}. All {shared} reachable "
            f"datasets in sync with live IBAMA portal; latest snapshot is {snapshot_age_h:.1f}h old.{note}"
        )
    if snapshot_age_h <= MONITOR_TOLERANCE_HOURS:
        return "PENDING", 0, (
            f"⏳ **Cross-check pending** — last verified {ts}. {divergences} divergence(s) "
            f"detected; next monitor run will reconcile (snapshot age {snapshot_age_h:.1f}h "
            f"≤ {MONITOR_TOLERANCE_HOURS}h tolerance).{note}"
        )
    return "STALE", 1, (
        f"⚠️ **Cross-check stale** — last verified {ts}. {divergences} unreconciled "
        f"divergence(s); latest snapshot is {snapshot_age_h:.1f}h old (> "
        f"{MONITOR_TOLERANCE_HOURS}h). Monitor workflow may need attention.{note}"
    )


def update_readme(sentence: str) -> bool:
    text = README.read_text(encoding="utf-8")
    if MARKER_START not in text or MARKER_END not in text:
        return False
    head, _, rest = text.partition(MARKER_START)
    _, _, tail = rest.partition(MARKER_END)
    README.write_text(f"{head}{MARKER_START}\n{sentence}\n{MARKER_END}{tail}", encoding="utf-8")
    return True


def main() -> int:
    started = datetime.now(timezone.utc)
    print(f"[{started.isoformat()}] cross-check vs {PORTAL}")

    latest_run, snap_path = latest_snapshot_path()
    print(f"  latest snapshot: run={latest_run} file={snap_path.name}")
    local = {d["id"]: d for d in load_snapshot(snap_path)}
    name_to_id = {d["name"]: did for did, d in local.items()}

    live_set = set(fetch(f"{PORTAL}/api/3/action/package_list")["result"])
    local_set = set(name_to_id.keys())
    added = sorted(live_set - local_set)
    removed = sorted(local_set - live_set)
    shared = sorted(live_set & local_set)
    print(f"  added={len(added)} removed={len(removed)} shared={len(shared)}")

    modified, errors = [], []
    for name in shared:
        try:
            d = fetch(f"{PORTAL}/api/3/action/package_show?id={name}")["result"]
            snap = local[name_to_id[name]]
            if (d.get("metadata_modified") != snap.get("metadata_modified")
                    or d.get("num_resources") != snap.get("num_resources")):
                modified.append({
                    "id": name_to_id[name], "name": name,
                    "snapshot_metadata_modified": snap.get("metadata_modified"),
                    "live_metadata_modified": d.get("metadata_modified"),
                    "snapshot_num_resources": snap.get("num_resources"),
                    "live_num_resources": d.get("num_resources"),
                })
        except Exception as e:
            errors.append({"name": name, "error": str(e)})
        time.sleep(0.2)

    ended = datetime.now(timezone.utc)
    snap_dt = datetime.strptime(latest_run, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    snapshot_age_h = (ended - snap_dt).total_seconds() / 3600
    divergences = len(added) + len(removed) + len(modified)
    coverage = (len(shared) - len(errors)) / len(shared) if shared else 0.0
    status, exit_code, sentence = render_status(
        divergences, snapshot_age_h, len(shared), len(errors), coverage, ended
    )

    REPORT.write_text(json.dumps({
        "status": status, "checked_at": ended.isoformat(),
        "duration_seconds": round((ended - started).total_seconds(), 2),
        "portal_url": PORTAL, "snapshot_run_id": latest_run, "snapshot_file": snap_path.name,
        "snapshot_age_hours": round(snapshot_age_h, 2),
        "monitor_tolerance_hours": MONITOR_TOLERANCE_HOURS,
        "coverage_ratio": round(coverage, 4),
        "min_coverage_ratio": MIN_COVERAGE_RATIO,
        "datasets": {"snapshot": len(local), "live": len(live_set),
                     "shared": len(shared), "added": added, "removed": removed},
        "modified": modified, "errors": errors,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    updated = update_readme(sentence)
    print(f"  status={status} divergences={divergences} errors={len(errors)} readme_updated={updated}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
