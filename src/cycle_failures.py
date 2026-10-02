"""
Cycle Failures — 5L-TEP Layer 4 Toolkit
========================================
Why a monitoring cycle failed, recorded so the dashboard can say it.

A failed cycle still fails its workflow run, as described in the WFA 2026
paper (Section 3.2: every failed run produces GitHub's e-mail; Section 4: the
cycles that aborted inside the monitoring step and later recovered). This
module only records the cause, in `data/cycle_failures.json`:

- the cycle itself classifies the exception that stopped it (`source: cycle`);
- every cycle also asks the GitHub Actions API about failed runs it has no
  record of (older runs, or a failure outside the monitoring step) and
  classifies them from the failed step or from the job's log (`source: log`,
  `source: actions`). Logs are kept by GitHub for a limited time; a run whose
  log is gone is recorded as `unknown`.

Categories: portal_down (HTTP 5xx), portal_slow (no answer in time), dns (the
portal's domain did not resolve), network (connection refused or failed,
certificate), blocked (HTTP 401/403/429), unexpected (other HTTP error, not
JSON, CKAN success=false), toolkit (an error in this toolkit), setup (the
runner or its dependencies), commit (saving to the repository), cancelled,
unknown.

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("5ltep.cycle_failures")

MONITOR_STEP = "Run monitoring cycle"
API = "https://api.github.com"
API_TIMEOUT = (10, 30)

# Last exception line of a Python traceback, as printed in a job log.
_EXCEPTION_LINE = re.compile(r"((?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*(?:Error|Exception|Timeout)): (.*)$")
_HTTP = re.compile(r"(\d{3}) (?:Client|Server) Error: (.*?) for url: (\S+)")


def _http_detail(code: str, reason: str, url: str) -> str:
    path = re.sub(r"^https?://[^/]+", "", url)
    return f"HTTP {code} {reason} ({path})"


def classify_line(line: str) -> Tuple[str, str]:
    """Classify one exception line ("Type: message") into (category, detail)."""
    m = _EXCEPTION_LINE.search(line.strip())
    kind, message = (m.group(1), m.group(2)) if m else ("", line.strip())
    http = _HTTP.search(message)
    if http:
        code = int(http.group(1))
        detail = _http_detail(http.group(1), http.group(2), http.group(3))
        if code >= 500:
            return "portal_down", detail
        if code in (401, 403, 429):
            return "blocked", detail
        return "unexpected", detail
    host = re.search(r"host='([^']+)'", message)
    where = f" ({host.group(1)})" if host else ""
    if re.search(r"NameResolution|getaddrinfo|Name or service not known|name resolution", message):
        return "dns", f"NameResolutionError{where}"
    if "ConnectTimeout" in kind or "ConnectTimeout" in message:
        return "network", f"ConnectTimeout{where}"
    if "ReadTimeout" in kind or "Read timed out" in message:
        return "portal_slow", f"ReadTimeout{where}"
    if "SSLError" in kind or re.search(r"SSL|CERTIFICATE", message):
        return "network", f"SSLError{where}"
    if "ConnectionError" in kind or re.search(r"Connection (refused|reset|aborted)|RemoteDisconnected", message):
        return "network", f"ConnectionError{where}: {message[:120]}"
    if "JSONDecodeError" in kind or "success=false" in message:
        return "unexpected", f"{kind.split('.')[-1] or 'Error'}: {message[:160]}"
    if kind:
        return "toolkit", f"{kind.split('.')[-1]}: {message[:160]}"
    return "unknown", message[:160]


def classify_exception(exc: BaseException) -> Tuple[str, str]:
    """Classify the exception that stopped a cycle."""
    return classify_line(f"{type(exc).__name__}: {exc}")


def classify_log(text: str) -> Tuple[str, str]:
    """Classify a failed job from its log: the last exception line wins."""
    lines = [line for line in text.splitlines()
             if _EXCEPTION_LINE.search(line) and "WARNING" not in line and "##[" not in line]
    if not lines:
        return "unknown", "no exception in the log"
    # drop the log's timestamp prefix ("2026-10-02T22:11:59.7136331Z ")
    return classify_line(re.sub(r"^\S+Z\s+", "", lines[-1]))


def load(path: Path) -> List[dict]:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _save(path: Path, entries: List[dict]) -> None:
    entries = sorted(entries, key=lambda e: e.get("when") or "")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(entries, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")


def record(path: Path, category: str, detail: str, when: datetime, run_id: Optional[int] = None,
           step: str = MONITOR_STEP, source: str = "cycle") -> dict:
    """Append one failure (replacing an older record of the same run)."""
    entry = {"run_id": run_id, "when": when.astimezone(timezone.utc).isoformat(timespec="seconds"),
             "category": category, "detail": detail, "step": step, "source": source}
    entries = [e for e in load(path) if run_id is None or e.get("run_id") != run_id]
    _save(path, entries + [entry])
    return entry


def _step_category(step: Optional[str], conclusion: str) -> str:
    if conclusion in ("cancelled", "timed_out"):
        return "cancelled"
    if not step:
        return "unknown"
    if step.startswith("Commit"):
        return "commit"
    if step.startswith(("Set up", "Install", "Checkout")):
        return "setup"
    return "unknown"


def sync_from_actions(path: Path, repository: str, token: Optional[str],
                      workflow: str = "monitor.yml", max_runs: int = 100) -> int:
    """Record the failed runs of the monitoring workflow that have no record yet. Returns how many."""
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"{API}/repos/{repository}/actions"
    known = {e.get("run_id") for e in load(path)}
    runs = []
    for status in ("failure", "cancelled", "timed_out"):
        r = requests.get(f"{base}/workflows/{workflow}/runs", headers=headers, timeout=API_TIMEOUT,
                         params={"status": status, "per_page": max_runs})
        r.raise_for_status()
        runs += r.json().get("workflow_runs", [])
    added = []
    for run in runs:
        if run["id"] in known:
            continue
        jobs = requests.get(f"{base}/runs/{run['id']}/jobs", headers=headers, timeout=API_TIMEOUT)
        jobs.raise_for_status()
        job = (jobs.json().get("jobs") or [{}])[0]
        failed = next((s["name"] for s in job.get("steps", []) if s.get("conclusion") == "failure"), None)
        when = datetime.fromisoformat((run.get("run_started_at") or run["created_at"]).replace("Z", "+00:00"))
        if failed == MONITOR_STEP and job.get("id"):
            log = requests.get(f"{base}/jobs/{job['id']}/logs", headers=headers, timeout=API_TIMEOUT)
            if log.ok:
                category, detail = classify_log(log.text)
                source = "log"
            else:
                category, detail, source = "unknown", f"job log no longer available (HTTP {log.status_code})", "actions"
        else:
            category = _step_category(failed, run.get("conclusion") or "")
            detail = f"step: {failed}" if failed else f"run {run.get('conclusion')}"
            source = "actions"
        added.append({"run_id": run["id"], "when": when.astimezone(timezone.utc).isoformat(timespec="seconds"),
                      "category": category, "detail": detail, "step": failed, "source": source})
        known.add(run["id"])
    if added:
        _save(path, load(path) + added)
        logger.info("Recorded %d failed run(s) from the GitHub Actions API", len(added))
    return len(added)


def summary(entries: List[dict]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in entries:
        out[e["category"]] = out.get(e["category"], 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
