"""Operational statistics of the deployment, from the GitHub Actions API.

Reports scheduled monitoring cycles, success rate, longest gap between
successful cycles, run durations, and minutes billed in the last 30 days
(each run rounded up to the next minute, per workflow).

Usage (from the repository root; GITHUB_TOKEN is optional, raises rate limits):
    python evaluation/actions_stats.py [owner/repo]
"""
import collections
import math
import os
import statistics
import sys
from datetime import datetime, timedelta

import requests

REPO = sys.argv[1] if len(sys.argv) > 1 else "lsp3cesarschool/5ltep-layer4"
HEADERS = {"Accept": "application/vnd.github+json"}
if os.environ.get("GITHUB_TOKEN"):
    HEADERS["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def duration(run):
    return (parse(run["updated_at"]) - parse(run["run_started_at"])).total_seconds()


def fetch_runs():
    runs, page = [], 1
    while True:
        resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/runs",
                            params={"per_page": 100, "page": page}, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        batch = resp.json()["workflow_runs"]
        if not batch:
            return runs
        runs += batch
        page += 1


def main():
    runs = [r for r in fetch_runs() if r["status"] == "completed"]
    monitor = [r for r in runs if "Monitoring" in r["name"] and r["event"] == "schedule"]
    ok = sorted(parse(r["created_at"]) for r in monitor if r["conclusion"] == "success")
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(ok, ok[1:])]
    durations = sorted(duration(r) for r in monitor if r["conclusion"] == "success")

    print(f"period: {ok[0]:%Y-%m-%d} .. {ok[-1]:%Y-%m-%d} ({(ok[-1] - ok[0]).days} days)")
    print(f"scheduled monitoring cycles: {len(monitor)}; successful: {len(ok)} "
          f"({100 * len(ok) / len(monitor):.1f}%); longest gap between successes: {max(gaps):.1f} h")
    print(f"cycle duration: median {statistics.median(durations):.0f} s, "
          f"p90 {durations[int(0.9 * len(durations))]:.0f} s")
    for name in sorted({r["name"] for r in runs}):
        conclusions = collections.Counter(r["conclusion"] for r in runs if r["name"] == name)
        print(f"  {name}: {dict(conclusions)}")

    end = max(parse(r["created_at"]) for r in runs)
    billed, count = collections.Counter(), collections.Counter()
    for r in runs:
        if parse(r["created_at"]) >= end - timedelta(days=30) and r["event"] == "schedule":
            billed[r["name"]] += math.ceil(max(duration(r), 1) / 60)
            count[r["name"]] += 1
    total = sum(billed.values())
    print(f"last 30 days (scheduled): {dict(count)} runs; {total} billed minutes "
          f"({100 * total / 2000:.1f}% of the 2,000-minute free tier)")


if __name__ == "__main__":
    main()
