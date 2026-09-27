"""
Change Summary Module — Human-Readable Change Details & changes.md
===================================================================
Complements the Hash Engine: while the Hash Engine *classifies* a change
(CLEAN_UPDATE / SCHEMA_DRIFT / RETRO_ALTER / CONTENT_MOD), this module
*describes* it, by diffing the previous and current CKAN metadata of a
dataset field by field:

- which fields changed (fingerprinted or not);
- resource URL changes, split into host moves (e.g., relocation of downloads
  to cloud storage) and packaging changes (zip <-> plain file), which the
  CKAN-declared format does not reveal;
- a one-line English summary for humans.

The same diff reconstructs the full change history from the stored snapshots
and renders it as `changes.md`, a human-readable log of what changed in the
monitored portal, when, and how.

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.
"""

import collections
import glob
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Fields covered by the fingerprint (see HashEngine.compute_hash)
DATASET_FIELDS = ["name", "title", "notes", "metadata_modified", "num_resources"]
RESOURCE_FIELDS = ["id", "name", "format", "url", "size", "last_modified"]

# Human-readable names used in summaries
FIELD_LABELS = {
    "title": "title changed",
    "name": "dataset name changed",
    "notes": "description edited",
    "resource.size": "file size updated",
    "resource.last_modified": "file date updated",
    "resource.name": "resource renamed",
    "license_title": "license title changed",
    "resource.description": "resource descriptions edited",
}

MAX_TABLE_ROWS = 200


# ---------------------------------------------------------------------------
# Describing one change
# ---------------------------------------------------------------------------

def _is_zip(url: str) -> bool:
    return urlparse(url or "").path.lower().endswith(".zip")


def describe_change(before: dict, after: dict) -> Dict[str, object]:
    """Describe how a dataset's CKAN metadata changed between two snapshots.

    Returns a dict with the changed fields, resource URL change counts and a
    one-line English summary.
    """
    res_before = before.get("resources", []) or []
    res_after = after.get("resources", []) or []
    pairs, added, removed = _match_resources(res_before, res_after)

    changed = [f for f in DATASET_FIELDS if before.get(f) != after.get(f)]
    for field in RESOURCE_FIELDS:
        if any(old.get(field) != new.get(field) for old, new in pairs):
            changed.append("resource." + field)
    if added or removed:
        changed.append("resources")
    outside = sorted(
        k for k in set(before) | set(after)
        if k not in DATASET_FIELDS + ["resources"] and before.get(k) != after.get(k)
    )
    outside += sorted({
        "resource." + k
        for old, new in pairs
        for k in set(old) | set(new)
        if k not in RESOURCE_FIELDS + ["metadata_modified"] and old.get(k) != new.get(k)
    })

    urls = collections.Counter()
    hosts = collections.Counter()
    formats = []
    for old, new in pairs:
        if old.get("url") != new.get("url"):
            urls["changed"] += 1
            host_old = urlparse(old.get("url") or "").netloc
            host_new = urlparse(new.get("url") or "").netloc
            if host_old != host_new:
                urls["host_moves"] += 1
                hosts[(host_old, host_new)] += 1
            if _is_zip(old.get("url")) and not _is_zip(new.get("url")):
                urls["zip_to_plain"] += 1
            elif _is_zip(new.get("url")) and not _is_zip(old.get("url")):
                urls["plain_to_zip"] += 1
        if old.get("format") != new.get("format"):
            formats.append(f"{old.get('format')} → {new.get('format')}")

    details = {
        "changedFields": changed,
        "fieldsOutsideFingerprint": outside,
        "resourceUrlChanges": urls["changed"],
        "hostMoves": urls["host_moves"],
        "packagingChanges": urls["zip_to_plain"] + urls["plain_to_zip"],
    }
    details["summary"] = _summarise(changed, outside, urls, hosts, formats, added, removed)
    return details


def _match_resources(res_before: list, res_after: list):
    """Pair resources by CKAN id (by position when ids are missing).

    Returns (pairs, added, removed) so that adding or removing a resource is
    not misreported as edits to every resource after it.
    """
    if all(r.get("id") for r in res_before + res_after):
        old_by_id = {r["id"]: r for r in res_before}
        new_by_id = {r["id"]: r for r in res_after}
        pairs = [(old_by_id[i], new_by_id[i]) for i in old_by_id if i in new_by_id]
        added = [r for i, r in new_by_id.items() if i not in old_by_id]
        removed = [r for i, r in old_by_id.items() if i not in new_by_id]
        return pairs, added, removed
    n = min(len(res_before), len(res_after))
    return list(zip(res_before[:n], res_after[:n])), res_after[n:], res_before[n:]


def _summarise(changed, outside, urls, hosts, formats, added, removed) -> str:
    parts = []
    if added:
        parts.append(f"{len(added)} resource(s) added")
    if removed:
        parts.append(f"{len(removed)} resource(s) removed")
    if formats:
        parts.append("declared format " + ", ".join(formats))
    if urls["changed"]:
        text = f"{urls['changed']} resource URL(s) changed"
        extra = []
        for (old, new), n in hosts.items():
            extra.append(f"{n} moved from {old or '?'} to {new or '?'}")
        if urls["zip_to_plain"]:
            extra.append(f"{urls['zip_to_plain']} zip → plain file")
        if urls["plain_to_zip"]:
            extra.append(f"{urls['plain_to_zip']} plain file → zip")
        if extra:
            text += " (" + "; ".join(extra) + ")"
        parts.append(text)
    for field in changed + outside:
        label = FIELD_LABELS.get(field)
        if label and label not in parts:
            parts.append(label)
    if not parts:
        parts.append("metadata timestamp updated" if "metadata_modified" in changed
                     else "metadata changed outside the fingerprint")
    text = "; ".join(parts)
    return text[0].upper() + text[1:]


# ---------------------------------------------------------------------------
# Snapshot history
# ---------------------------------------------------------------------------

def load_snapshot(snapshots_dir: Path, file_name: str):
    """Load a stored snapshot (plain or gzip). Returns (datasets_by_id, errored_ids)."""
    path = Path(snapshots_dir) / file_name
    if not path.exists():
        path = Path(snapshots_dir) / (file_name + ".gz")
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    datasets, errored = {}, set()
    for d in json.loads(raw.decode("utf-8")):
        if "_error" in d:
            errored.add(d.get("id"))
        else:
            datasets[d.get("id")] = d
    return datasets, errored


def latest_snapshot(snapshots_dir: Path) -> Optional[Dict[str, dict]]:
    """Return the datasets of the most recent stored snapshot, if any."""
    manifest_path = Path(snapshots_dir) / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("runs"):
        return None
    last_run = max(manifest["runs"])
    return load_snapshot(snapshots_dir, manifest["snapshots"][manifest["runs"][last_run]])[0]


def _recorded_events(prov_dir: Path) -> List[tuple]:
    events = []
    for path in glob.glob(str(Path(prov_dir) / "*.jsonld")):
        for record in json.loads(Path(path).read_text(encoding="utf-8"))["provenance_chain"]:
            entity = next(n for n in record["@graph"] if "prov:Entity" in n["@type"])
            events.append((datetime.fromisoformat(entity["5ltep:detectedAt"]["@value"]),
                           entity["5ltep:datasetId"], entity["5ltep:changeType"],
                           entity["5ltep:severity"]))
    return events


def build_history(snapshots_dir: Path, prov_dir: Path) -> List[dict]:
    """Reconstruct every change between consecutive distinct snapshots."""
    manifest = json.loads((Path(snapshots_dir) / "manifest.json").read_text(encoding="utf-8"))
    transitions = []
    for run_id, digest in sorted(manifest["runs"].items()):
        if not transitions or transitions[-1][1] != digest:
            transitions.append((run_id, digest))
    recorded = _recorded_events(prov_dir)

    history = []
    for (_, d0), (run_id, d1) in zip(transitions, transitions[1:]):
        before, err0 = load_snapshot(snapshots_dir, manifest["snapshots"][d0])
        after, err1 = load_snapshot(snapshots_dir, manifest["snapshots"][d1])
        when = datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        for ds in sorted(set(before) | set(after)):
            if ds in err0 or ds in err1:
                continue  # harvest error in one of the snapshots: not a change
            if ds not in before:
                entry = {"type": "NEW", "severity": "INFO",
                         "summary": f"Dataset published ({len(after[ds].get('resources', []))} resources)"}
                meta = after[ds]
            elif ds not in after:
                entry = {"type": "REMOVED", "severity": "WARNING", "summary": "Dataset no longer listed"}
                meta = before[ds]
            elif before[ds] != after[ds]:
                details = describe_change(before[ds], after[ds])
                match = next((r for r in recorded if r[1] == ds
                              and abs((r[0] - when).total_seconds()) < 1800), None)
                entry = {"type": match[2] if match else "NOT_FINGERPRINTED",
                         "severity": match[3] if match else "INFO",
                         "summary": details["summary"]}
                meta = after[ds]
            else:
                continue
            entry.update({"when": when, "dataset_id": ds,
                          "title": meta.get("title") or meta.get("name") or ds,
                          "name": meta.get("name") or ds})
            history.append(entry)
    return history


# ---------------------------------------------------------------------------
# changes.md
# ---------------------------------------------------------------------------

def render_changes_md(history: List[dict], portal_url: str, current_datasets: int,
                      monitored_since: Optional[str]) -> str:
    """Render the change history as Markdown (newest first)."""
    portal = portal_url.rstrip("/")
    tracked = [h for h in history if h["type"] not in ("NEW", "REMOVED", "NOT_FINGERPRINTED")]
    new = [h for h in history if h["type"] == "NEW"]
    critical = [h for h in history if h["severity"] == "CRITICAL"]
    last = max((h["when"] for h in history), default=None)

    lines = [
        f"# Changes in {portal}",
        "",
        "Human-readable log of what changed in the monitored CKAN portal, when, and how.",
        "Generated automatically by the monitoring workflow from the stored snapshots and",
        "PROV-DM records; do not edit by hand. Times are UTC (detection time, i.e., the",
        "first monitoring cycle that saw the change).",
        "",
        f"- **Monitored since:** {monitored_since or 'n/a'}",
        f"- **Datasets in the latest snapshot:** {current_datasets}",
        f"- **Changes recorded as PROV events:** {len(tracked)} "
        f"({len(critical)} critical)",
        f"- **New datasets:** {len(new)}",
        f"- **Last change detected:** {last:%Y-%m-%d %H:%M} UTC" if last else "- **Last change detected:** none",
        "",
        "Types: `CONTENT_MOD` (content changed with a new timestamp), `SCHEMA_DRIFT`",
        "(resources added, removed, renamed or re-formatted; critical), `RETRO_ALTER`",
        "(changed without a new timestamp; critical), `NEW` (dataset first published),",
        "`REMOVED`, `NOT_FINGERPRINTED` (only fields outside the fingerprint changed; no PROV event).",
        "",
        "## By month",
        "",
        "| Month | PROV events | Critical | New datasets |",
        "|---|---:|---:|---:|",
    ]
    months = collections.OrderedDict()
    for h in sorted(history, key=lambda h: h["when"], reverse=True):
        m = months.setdefault(h["when"].strftime("%Y-%m"), collections.Counter())
        m["events"] += h["type"] not in ("NEW", "REMOVED", "NOT_FINGERPRINTED")
        m["critical"] += h["severity"] == "CRITICAL"
        m["new"] += h["type"] == "NEW"
    for month, c in months.items():
        lines.append(f"| {month} | {c['events']} | {c['critical']} | {c['new']} |")

    lines += ["", "## Latest changes", "",
              "| Detected (UTC) | Dataset | Type | What changed | Provenance |",
              "|---|---|---|---|---|"]
    ordered = sorted(history, key=lambda h: (h["when"], h["title"]), reverse=True)
    for h in ordered[:MAX_TABLE_ROWS]:
        dataset = f"[{h['title']}]({portal}/dataset/{h['name']})"
        prov = (f"[log](provenance_logs/{h['dataset_id']}.jsonld)"
                if h["type"] not in ("NEW", "REMOVED", "NOT_FINGERPRINTED") else "")
        summary = h["summary"].replace("|", "\\|")
        lines.append(f"| {h['when']:%Y-%m-%d %H:%M} | {dataset} | `{h['type']}` | {summary} | {prov} |")
    if len(ordered) > MAX_TABLE_ROWS:
        lines.append(f"\n_Showing the latest {MAX_TABLE_ROWS} of {len(ordered)} changes._")
    return "\n".join(lines) + "\n"


def write_changes_md(snapshots_dir: Path, prov_dir: Path, portal_url: str, out_path: Path) -> int:
    """Rebuild changes.md from the stored history. Returns the number of entries."""
    manifest = json.loads((Path(snapshots_dir) / "manifest.json").read_text(encoding="utf-8"))
    history = build_history(snapshots_dir, prov_dir)
    first_run = min(manifest["runs"]) if manifest.get("runs") else None
    since = (datetime.strptime(first_run, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d")
             if first_run else None)
    current = latest_snapshot(snapshots_dir) or {}
    Path(out_path).write_text(
        render_changes_md(history, portal_url, len(current), since), encoding="utf-8",
        newline="\n")
    return len(history)
