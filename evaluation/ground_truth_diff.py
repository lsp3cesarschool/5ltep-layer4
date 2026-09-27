"""Ground-truth check of the change events recorded by the toolkit.

Independently diffs every pair of consecutive *distinct* snapshots stored in
data/snapshots (field by field, without using the Hash Engine), derives the
expected change class for each modified dataset, and matches it against the
events recorded in provenance_logs/ (same dataset, detected in the same run).

Usage (from the repository root):
    python evaluation/ground_truth_diff.py
"""
import collections
import glob
import gzip
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
SNAP_DIR = REPO / "data" / "snapshots"

# Fields covered by the fingerprint (see src/hash_engine.py)
DATASET_FIELDS = ["name", "title", "notes", "metadata_modified", "num_resources"]
RESOURCE_FIELDS = ["id", "name", "format", "url", "size", "last_modified"]


def load_snapshot(file_name):
    path = SNAP_DIR / file_name
    if not path.exists():
        path = SNAP_DIR / (file_name + ".gz")
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return {d.get("id"): d for d in json.loads(raw.decode("utf-8")) if "_error" not in d}


def run_time(run_id):
    return datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def expected_class(before, after):
    """Classify a dataset modification from a field-level diff."""
    manifest = lambda d: [(r.get("name"), r.get("format")) for r in d.get("resources", [])]
    fields = [f for f in DATASET_FIELDS if before.get(f) != after.get(f)]
    for f in RESOURCE_FIELDS:
        if [r.get(f) for r in before.get("resources", [])] != [r.get(f) for r in after.get("resources", [])]:
            fields.append("resource." + f)
    if not fields:
        return None, fields  # only non-fingerprinted fields changed
    if manifest(before) != manifest(after):
        return "SCHEMA_DRIFT", fields
    if (after.get("metadata_modified") or "") <= (before.get("metadata_modified") or ""):
        return "RETRO_ALTER", fields
    return "CONTENT_MOD", fields


def main():
    manifest = json.loads((SNAP_DIR / "manifest.json").read_text(encoding="utf-8"))
    transitions = []
    for run_id, digest in sorted(manifest["runs"].items()):
        if not transitions or transitions[-1][1] != digest:
            transitions.append((run_id, digest))

    truth, additions, unfingerprinted = [], [], 0
    field_counts, other_counts = collections.Counter(), collections.Counter()
    for (_, d0), (run1, d1) in zip(transitions, transitions[1:]):
        before = load_snapshot(manifest["snapshots"][d0])
        after = load_snapshot(manifest["snapshots"][d1])
        for ds in sorted(set(before) | set(after)):
            if ds not in before:
                additions.append((run1, ds))
            elif ds in after and before[ds] != after[ds]:
                label, fields = expected_class(before[ds], after[ds])
                if label is None:
                    unfingerprinted += 1
                    continue
                truth.append((run1, ds, label))
                field_counts.update(set(fields))
                other_counts.update(k for k in set(before[ds]) | set(after[ds])
                                    if k not in DATASET_FIELDS + ["resources"]
                                    and before[ds].get(k) != after[ds].get(k))

    recorded = []
    for path in glob.glob(str(REPO / "provenance_logs" / "*.jsonld")):
        for record in json.loads(Path(path).read_text(encoding="utf-8"))["provenance_chain"]:
            entity = next(n for n in record["@graph"] if "prov:Entity" in n["@type"])
            detected = datetime.fromisoformat(entity["5ltep:detectedAt"]["@value"])
            recorded.append((detected, entity["5ltep:datasetId"], entity["5ltep:changeType"]))

    unmatched = list(recorded)
    matches = collections.Counter()
    for run1, ds, label in truth:
        hit = next((r for r in unmatched if r[1] == ds
                    and abs((r[0] - run_time(run1)).total_seconds()) < 1800), None)
        if hit is None:
            matches["missed"] += 1
            print("MISSED", run1, ds, label)
            continue
        unmatched.remove(hit)
        matches["correct" if hit[2] == label else "wrong_class"] += 1

    print(f"cycles recorded: {len(manifest['runs'])}; distinct snapshots: {len(transitions)}")
    print(f"ground truth: {len(truth)} modifications, {len(additions)} additions, "
          f"{unfingerprinted} non-fingerprinted-only changes")
    print("expected classes:", dict(collections.Counter(t[2] for t in truth)))
    print("fingerprinted fields changed:", dict(field_counts))
    print("co-changed dataset fields outside the fingerprint:", dict(other_counts))
    print(f"recorded events: {len(recorded)}; matched correct: {matches['correct']}, "
          f"wrong class: {matches['wrong_class']}, missed: {matches['missed']}, "
          f"spurious (no ground truth): {len(unmatched)}")


if __name__ == "__main__":
    main()
