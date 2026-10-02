"""
Dashboard Data & Status Badges — 5L-TEP Layer 4 Toolkit
=========================================================
Turns the persisted state of the pipeline (snapshot manifest, change history,
PROV-DM logs) into the files GitHub Pages serves from `docs/`:

- `docs/data/layer4.json`: everything the dashboard (`docs/index.html`) shows;
- `docs/data/status.json` / `status.pt.json`: shields.io endpoint badges for
  the README (English) and LEIAME (Portuguese).

The badge files replace text that a workflow would otherwise rewrite inside
the README, so the README stays static and identical across instances of the
toolkit (IBAMA, ANEEL, Recife).

Read-only with respect to the durable state: nothing here changes
`data/hash_store.json`, the snapshots or the provenance logs.

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.
"""

import collections
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from change_summary import latest_snapshot

DASHBOARD_FILE = "layer4.json"
STATUS_FILES = {"en": "status.json", "pt": "status.pt.json"}
PROV_TYPES = ("CONTENT_MOD", "SCHEMA_DRIFT", "RETRO_ALTER")
CRITICAL_WINDOW_DAYS = 30   # a critical event this recent turns the badge red


def _parse_run(run_id: str) -> datetime:
    return datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _log_name(dataset_id: str) -> str:
    """File name of a dataset's PROV log (same sanitisation as ProvMapper.save_records)."""
    return dataset_id.replace("/", "_").replace("\\", "_") + ".jsonld"


def _host(url: Optional[str]) -> str:
    """Server part of a resource URL, exactly as the portal records it (a port, if written, is kept).

    "" when the portal records no URL at all; "?" when the URL has no scheme://host.
    """
    url = (url or "").strip()
    if not url:
        return ""
    return url.split("/")[2] if "://" in url else "?"


def _chain_lengths(prov_dir: Path) -> Dict[str, int]:
    lengths = {}
    for path in Path(prov_dir).glob("*.jsonld"):
        try:
            lengths[path.name] = len(json.loads(path.read_text(encoding="utf-8"))["provenance_chain"])
        except (OSError, ValueError, KeyError):
            continue
    return lengths


def _monitoring(runs: List[str]) -> Dict[str, object]:
    """Cycle counts per day and the longest gap between cycles (last 30 days)."""
    times = sorted(_parse_run(r) for r in runs)
    if not times:
        return {"since": None, "last_cycle": None, "cycles": 0, "cycles_by_day": {},
                "cycles_30d": 0, "max_gap_hours_30d": None}
    last = times[-1]
    recent = [t for t in times if t >= last - timedelta(days=30)]
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(recent, recent[1:])]
    by_day = collections.Counter(t.strftime("%Y-%m-%d") for t in times)
    return {
        "since": times[0].isoformat(),
        "last_cycle": last.isoformat(),
        "cycles": len(times),
        "cycles_by_day": dict(sorted(by_day.items())),
        "cycles_30d": len(recent),
        "max_gap_hours_30d": round(max(gaps), 1) if gaps else None,
    }


def build_dashboard(history: List[dict], snapshots_dir: Path, prov_dir: Path,
                    portal: Dict[str, str], repository: Optional[str] = None,
                    toolkit_version: str = "", now: Optional[datetime] = None) -> Dict[str, object]:
    """Assemble the dashboard data from the change history and the stored state."""
    snapshots_dir, prov_dir = Path(snapshots_dir), Path(prov_dir)
    manifest_path = snapshots_dir / "manifest.json"
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.exists() else {"runs": {}, "snapshots": {}})
    current = latest_snapshot(snapshots_dir) or {}
    chains = _chain_lengths(prov_dir)

    events = []
    for h in sorted(history, key=lambda h: (h["when"], h["title"]), reverse=True):
        d = h.get("details") or {}
        log = _log_name(h["dataset_id"])
        events.append({
            "when": h["when"].isoformat(), "type": h["type"], "severity": h["severity"],
            "dataset_id": h["dataset_id"], "name": h["name"], "title": h["title"],
            "summary": h["summary"], "summary_pt": h.get("summary_pt", h["summary"]),
            "host_pairs": d.get("hostPairs", []),
            "zip_to_plain": d.get("zipToPlain", 0), "plain_to_zip": d.get("plainToZip", 0),
            "prov_log": log if h["type"] in PROV_TYPES and log in chains else None,
        })

    per_dataset = collections.defaultdict(list)
    for e in events:
        per_dataset[e["dataset_id"]].append(e)

    datasets = []
    for ds_id, meta in current.items():
        mine = per_dataset.get(ds_id, [])
        changes = [e for e in mine if e["type"] != "NEW"]
        log = _log_name(ds_id)
        datasets.append({
            "id": ds_id, "name": meta.get("name") or ds_id,
            "title": meta.get("title") or meta.get("name") or ds_id,
            "organization": (meta.get("organization") or {}).get("title")
                            or (meta.get("organization") or {}).get("name"),
            "resources": len(meta.get("resources") or []),
            "metadata_modified": meta.get("metadata_modified"),
            "prov_records": chains.get(log, 0),
            "prov_log": log if log in chains else None,
            "changes": len(changes),
            "last_change": changes[0]["when"] if changes else None,
            "last_type": changes[0]["type"] if changes else None,
        })
    datasets.sort(key=lambda d: (d["last_change"] or "", d["title"]), reverse=True)

    hosts_now = collections.Counter(
        _host(r.get("url")) for meta in current.values() for r in (meta.get("resources") or []))
    # Resources whose URL has no server ("" or "?"): listed so the dashboard can name them.
    urls_without_host = sorted((
        {"dataset": meta.get("name"), "title": meta.get("title") or meta.get("name"),
         "resource": r.get("name") or r.get("id"), "format": r.get("format"), "url": (r.get("url") or "").strip(),
         "host": _host(r.get("url"))}
        for meta in current.values() for r in (meta.get("resources") or []) if _host(r.get("url")) in ("", "?")),
        key=lambda x: (x["title"] or "", x["resource"] or ""))
    moves = {}
    for e in events:
        for old, new, n in e["host_pairs"]:
            m = moves.setdefault((old, new), {"from": old, "to": new, "urls": 0,
                                               "events": 0, "datasets": set(), "last": e["when"]})
            m["urls"] += n
            m["events"] += 1
            m["datasets"].add(e["dataset_id"])
    relocations = sorted(({**m, "datasets": len(m["datasets"])} for m in moves.values()),
                         key=lambda m: -m["urls"])

    prov_events = [e for e in events if e["type"] in PROV_TYPES]
    counts = collections.Counter(e["type"] for e in events)
    return {
        "schema": 1,
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "toolkit_version": toolkit_version,
        "repository": repository,
        "portal": portal,
        "monitoring": {**_monitoring(list(manifest.get("runs", {}))),
                       "distinct_snapshots": len(manifest.get("snapshots", {}))},
        "totals": {
            "datasets": len(current),
            "resources": sum(d["resources"] for d in datasets),
            "organizations": len({d["organization"] for d in datasets if d["organization"]}),
            "prov_events": len(prov_events),
            "prov_records": sum(chains.values()),
            "critical": sum(e["severity"] == "CRITICAL" for e in prov_events),
            "datasets_changed": len({e["dataset_id"] for e in prov_events}),
            "by_type": dict(counts),
        },
        "events": events,
        "datasets": datasets,
        "hosts_now": dict(hosts_now.most_common()),
        "urls_without_host": urls_without_host,
        "relocations": relocations,
        "packaging": {"zip_to_plain": sum(e["zip_to_plain"] for e in events),
                      "plain_to_zip": sum(e["plain_to_zip"] for e in events)},
    }


def _num(n: int, lang: str) -> str:
    return f"{n:,}".replace(",", "." if lang == "pt" else ",")


def status_badges(data: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    """shields.io endpoint badges (English and Portuguese) for the README/LEIAME."""
    totals, monitoring = data["totals"], data["monitoring"]
    last = monitoring.get("last_cycle")
    recent_critical = False
    if last:
        cutoff = datetime.fromisoformat(last) - timedelta(days=CRITICAL_WINDOW_DAYS)
        recent_critical = any(e["severity"] == "CRITICAL" and datetime.fromisoformat(e["when"]) >= cutoff
                              for e in data["events"])
    color = "red" if recent_critical else "brightgreen"
    badges = {}
    for lang in ("en", "pt"):
        n, ev, cr = (_num(totals[k], lang) for k in ("datasets", "prov_events", "critical"))
        if not last:
            message = "waiting for the first cycle" if lang == "en" else "aguardando o primeiro ciclo"
            badge_color = "lightgrey"
        elif lang == "en":
            message, badge_color = f"{n} datasets · {ev} changes · {cr} critical", color
        else:
            message, badge_color = f"{n} conjuntos · {ev} mudanças · {cr} críticas", color
        badges[lang] = {"schemaVersion": 1, "label": "Layer 4" if lang == "en" else "Camada 4",
                        "message": message, "color": badge_color}
    return badges


def write_dashboard(out_dir: Path, data: Dict[str, object]) -> None:
    """Write layer4.json and the two status badges into `out_dir` (docs/data)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / DASHBOARD_FILE).write_text(
        json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    for lang, badge in status_badges(data).items():
        (out_dir / STATUS_FILES[lang]).write_text(
            json.dumps(badge, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
