"""Controlled fault-injection evaluation of the 5LTEP-L4 change classifier.

Takes the latest real IBAMA snapshot as baseline, applies one synthetic
mutation per (dataset, scenario), runs HashEngine.detect_changes against the
baseline state and reports a confusion matrix of expected vs. predicted type.

Usage (from the repository root):
    python evaluation/fault_injection.py
"""
import copy
import collections
import gzip
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

REPO = next((a for a in sys.argv[1:] if not a.startswith("--")),
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "src"))
from hash_engine import HashEngine  # noqa: E402


def load_snapshot(fn):
    p = os.path.join(REPO, "data", "snapshots", fn)
    if not os.path.exists(p):
        p += ".gz"
    raw = open(p, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


manifest = json.load(open(os.path.join(REPO, "data", "snapshots", "manifest.json")))
last_run = sorted(manifest["runs"])[-1]
baseline = [d for d in load_snapshot(manifest["snapshots"][manifest["runs"][last_run]])
            if "_error" not in d]


def bump(ts):
    return (datetime.fromisoformat(ts) + timedelta(hours=1)).isoformat()


def notes_edit(d, advance):
    d["notes"] = (d.get("notes") or "") + " [edited]"
    if advance:
        d["metadata_modified"] = bump(d["metadata_modified"])


def reupload(d, advance):
    if not d.get("resources"):
        return notes_edit(d, advance)
    d["resources"][0]["url"] = (d["resources"][0].get("url") or "") + "?v=2"
    if advance:
        d["metadata_modified"] = bump(d["metadata_modified"])


def add_resource(d, advance):
    d.setdefault("resources", []).append({"id": "new", "name": "extra.csv", "format": "CSV"})
    d["num_resources"] = len(d["resources"])
    if advance:
        d["metadata_modified"] = bump(d["metadata_modified"])


def change_format(d, advance):
    if not d.get("resources"):
        return add_resource(d, advance)
    d["resources"][0]["format"] = "XLSX" if d["resources"][0].get("format") != "XLSX" else "CSV"
    if advance:
        d["metadata_modified"] = bump(d["metadata_modified"])


def remove_resource(d, advance):
    if not d.get("resources"):
        return add_resource(d, advance)
    d["resources"].pop()
    d["num_resources"] = len(d["resources"])
    if advance:
        d["metadata_modified"] = bump(d["metadata_modified"])


def unhashed_edit(d, advance):
    # Fields outside the fingerprint (tags, license) -- out of scope by design.
    d["license_title"] = (d.get("license_title") or "") + " (rev)"
    d["tags"] = d.get("tags", []) + [{"name": "injected"}]


# (scenario, mutation, advance timestamp?, expected label)
SCENARIOS = [
    ("no change (control)", None, False, "CLEAN_UPDATE"),
    ("notes edit + ts", notes_edit, True, "CONTENT_MOD"),
    ("resource re-upload + ts", reupload, True, "CONTENT_MOD"),
    ("resource added", add_resource, True, "SCHEMA_DRIFT"),
    ("resource removed", remove_resource, True, "SCHEMA_DRIFT"),
    ("format changed", change_format, True, "SCHEMA_DRIFT"),
    ("notes edit, no ts", notes_edit, False, "RETRO_ALTER"),
    ("re-upload, no ts", reupload, False, "RETRO_ALTER"),
    ("tags/license edit (unhashed)", unhashed_edit, True, "CHANGE_NOT_FINGERPRINTED"),
]

confusion = collections.Counter()
per_scenario = collections.defaultdict(collections.Counter)
with tempfile.TemporaryDirectory() as tmp:
    for name, mutate, advance, expected in SCENARIOS:
        store = os.path.join(tmp, f"{abs(hash(name))}.json")
        engine = HashEngine(hash_store_path=store, portal_url="https://example")
        engine.detect_changes(copy.deepcopy(baseline))  # baseline observation
        mutated = copy.deepcopy(baseline)
        for d in mutated:
            if mutate:
                mutate(d, advance)
        for ev in HashEngine(hash_store_path=store, portal_url="https://example").detect_changes(mutated):
            pred = ev.change_type.value
            confusion[(expected, pred)] += 1
            per_scenario[name][pred] += 1

n = sum(confusion.values())
labeled = {k: v for k, v in confusion.items() if k[0] != "CHANGE_NOT_FINGERPRINTED"}
correct = sum(v for (e, p), v in labeled.items() if e == p)
print(f"baseline run {last_run}: {len(baseline)} datasets; {n} injected cases")
for name, *_ in SCENARIOS:
    print(f"  {name:32s} {dict(per_scenario[name])}")
print(f"accuracy on in-scope scenarios: {correct}/{sum(labeled.values())}")
print("confusion (expected -> predicted):")
for (e, p), v in sorted(confusion.items()):
    print(f"  {e:26s} -> {p:14s} {v}")
