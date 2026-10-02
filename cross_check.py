"""
Cross-Check — 5L-TEP Layer 4 Toolkit
=====================================
Independent validator that compares the live CKAN portal against the most
recent committed snapshot using the portal's own metadata_modified timestamp
and num_resources count — fields that are set by the data custodian, not
by this toolkit. This provides empirical triangulation of the main
pipeline's change-detection results.

Runs in parallel to main.py (separate workflow, no shared state at runtime),
writes data/cross_check_report.json, and publishes the result for people:
docs/data/cross_check.json (the dashboard's panel, with an English and a
Portuguese sentence) and docs/data/status-cross-check[.pt].json (shields.io
endpoint badges shown in README.md and LEIAME.md). The READMEs themselves are
never rewritten, so they stay identical across instances of the toolkit.

Exit codes:
  0  IN_SYNC   — live matches latest snapshot exactly
  0  PENDING   — divergences exist but snapshot is fresh (< tolerance window)
  0  DEGRADED  — some transient fetch failures but coverage above threshold
  1  STALE     — divergences exist and snapshot is older than tolerance window
  1  ERROR     — fetch coverage below threshold or package_list failed
"""

import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from portal_config import load_portal  # noqa: E402

# Same portal as the monitoring workflow (portal.json)
PORTAL = load_portal()["portal_url"]
MANIFEST = Path("data/snapshots/manifest.json")
SNAPSHOTS_DIR = Path("data/snapshots")
REPORT = Path("data/cross_check_report.json")
DOCS_DATA = Path("docs/data")
PANEL = DOCS_DATA / "cross_check.json"
BADGES = {"en": DOCS_DATA / "status-cross-check.json", "pt": DOCS_DATA / "status-cross-check.pt.json"}
USER_AGENT = "5LTEP-Layer4/1.0 (parallel cross-check)"
MONITOR_TOLERANCE_HOURS = 7
MIN_COVERAGE_RATIO = 0.90
FETCH_RETRIES = 3
FETCH_BACKOFF_SECONDS = 1.5

# Badge text and shields.io colour per status: (English, Portuguese, colour)
BADGE = {
    "IN_SYNC": ("in sync", "sincronizada", "brightgreen"),
    "DEGRADED": ("in sync, {cov}% reached", "sincronizada, {cov}% consultados", "yellow"),
    "PENDING": ("pending: {div} divergence(s)", "pendente: {div} divergência(s)", "yellow"),
    "STALE": ("stale: {div} divergence(s)", "desatualizada: {div} divergência(s)", "orange"),
    "ERROR": ("error: {cov}% reached", "erro: {cov}% consultados", "red"),
    "WAITING": ("waiting for the first cycle", "aguardando o primeiro ciclo", "lightgrey"),
}


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


def _pt(value: float, fmt: str) -> str:
    """Format a number with the Portuguese decimal comma."""
    return format(value, fmt).replace(".", ",")


def render_status(divergences, snapshot_age_h, shared, errors, coverage, ended):
    """Return (status, exit_code, English sentence, Portuguese sentence)."""
    ts = ended.strftime("%Y-%m-%d %H:%M UTC")
    cov_pct = coverage * 100
    host = PORTAL.split('//')[-1]
    age, age_pt = f"{snapshot_age_h:.1f}h", f"{_pt(snapshot_age_h, '.1f')} h"
    if coverage < MIN_COVERAGE_RATIO:
        return "ERROR", 1, (
            f"❌ **Cross-check error** — last attempt {ts}; coverage {cov_pct:.0f}% "
            f"below {MIN_COVERAGE_RATIO * 100:.0f}% threshold ({errors} fetch failure(s)). "
            f"See `data/cross_check_report.json`."
        ), (
            f"❌ **Erro na verificação cruzada** — última tentativa em {ts}; cobertura de "
            f"{cov_pct:.0f}%, abaixo do limite de {MIN_COVERAGE_RATIO * 100:.0f}% "
            f"({errors} falha(s) de consulta). Veja `data/cross_check_report.json`."
        )
    note = "" if errors == 0 else f" Coverage: {cov_pct:.0f}% ({errors} transient fetch error(s))."
    note_pt = "" if errors == 0 else f" Cobertura: {cov_pct:.0f}% ({errors} erro(s) transitório(s) de consulta)."
    if divergences == 0:
        emoji = "✅" if errors == 0 else "🟡"
        label = "passing" if errors == 0 else "degraded"
        label_pt = "aprovada" if errors == 0 else "degradada"
        return ("IN_SYNC" if errors == 0 else "DEGRADED"), 0, (
            f"{emoji} **Cross-check {label}** — last verified {ts}. All {shared} reachable "
            f"datasets in sync with the live portal ({host}); latest snapshot is {age} old.{note}"
        ), (
            f"{emoji} **Verificação cruzada {label_pt}** — última verificação em {ts}. Todos os "
            f"{shared} conjuntos de dados acessíveis estão sincronizados com o portal ao vivo "
            f"({host}); o snapshot mais recente tem {age_pt}.{note_pt}"
        )
    if snapshot_age_h <= MONITOR_TOLERANCE_HOURS:
        return "PENDING", 0, (
            f"⏳ **Cross-check pending** — last verified {ts}. {divergences} divergence(s) "
            f"detected; next monitor run will reconcile (snapshot age {age} "
            f"≤ {MONITOR_TOLERANCE_HOURS}h tolerance).{note}"
        ), (
            f"⏳ **Verificação cruzada pendente** — última verificação em {ts}. "
            f"{divergences} divergência(s) detectada(s); a próxima execução do monitoramento "
            f"vai reconciliá-las (snapshot com {age_pt} ≤ tolerância de "
            f"{MONITOR_TOLERANCE_HOURS} h).{note_pt}"
        )
    return "STALE", 1, (
        f"⚠️ **Cross-check stale** — last verified {ts}. {divergences} unreconciled "
        f"divergence(s); latest snapshot is {age} old (> "
        f"{MONITOR_TOLERANCE_HOURS}h). Monitor workflow may need attention.{note}"
    ), (
        f"⚠️ **Verificação cruzada desatualizada** — última verificação em {ts}. "
        f"{divergences} divergência(s) não reconciliada(s); o snapshot mais recente tem "
        f"{age_pt} (> {MONITOR_TOLERANCE_HOURS} h). O workflow de monitoramento pode "
        f"precisar de atenção.{note_pt}"
    )


def badges(status: str, divergences: int = 0, coverage: float = 1.0, day: str = "") -> dict:
    """shields.io endpoint badges ({"en": ..., "pt": ...}) for a cross-check status."""
    en, pt, color = BADGE[status]
    out = {}
    for lang, text, label in (("en", en, "cross-check"), ("pt", pt, "verificação cruzada")):
        message = text.format(div=divergences, cov=f"{coverage * 100:.0f}")
        out[lang] = {"schemaVersion": 1, "label": label,
                     "message": f"{message} · {day}" if day else message, "color": color}
    return out


def publish(status: str, panel: dict, divergences: int = 0, coverage: float = 1.0,
            day: str = "") -> None:
    """Write the dashboard panel and the two badges under docs/data."""
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(panel, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    for lang, badge in badges(status, divergences, coverage, day).items():
        BADGES[lang].write_text(json.dumps(badge, indent=1, ensure_ascii=False),
                                encoding="utf-8", newline="\n")


def main() -> int:
    started = datetime.now(timezone.utc)
    print(f"[{started.isoformat()}] cross-check vs {PORTAL}")

    if not MANIFEST.exists():
        # Fresh repository/fork: the monitoring workflow has not run yet.
        print("  no snapshot yet (first monitoring cycle pending); nothing to cross-check")
        publish("WAITING", {"status": "WAITING", "portal_url": PORTAL,
                            "checked_at": started.isoformat()})
        return 0

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
    status, exit_code, sentence, sentence_pt = render_status(
        divergences, snapshot_age_h, len(shared), len(errors), coverage, ended
    )

    report = {
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
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    publish(status, {**report, "sentence": sentence, "sentence_pt": sentence_pt},
            divergences, coverage, ended.strftime("%Y-%m-%d"))
    print(f"  status={status} divergences={divergences} errors={len(errors)}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
