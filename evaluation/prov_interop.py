"""Check that every 5LTEP-L4 PROV-DM record parses with the `prov` library.

Each record in provenance_logs/*.jsonld is parsed as JSON-LD (rdflib) and
deserialised into a prov.model.ProvDocument (prov's RDF/PROV-O reader).

Records written before v1.0.1 lack the "portal" prefix in their @context;
--declare-portal-ns adds it at read time.

Requires: pip install prov rdflib
Usage (from the repository root):
    python evaluation/prov_interop.py [--declare-portal-ns]
"""
import glob
import json
import os
import sys

import prov
from prov.model import ProvDocument

REPO = next((a for a in sys.argv[1:] if not a.startswith("--")),
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATCH = "--declare-portal-ns" in sys.argv
ok, fail, counts = 0, 0, {"entities": 0, "activities": 0, "agents": 0, "derivations": 0}
for path in sorted(glob.glob(os.path.join(REPO, "provenance_logs", "*.jsonld"))):
    log = json.load(open(path, encoding="utf-8"))
    for record in log["provenance_chain"]:
        if PATCH:  # pre-v1.0.1 records: declare the portal prefix at read time
            record["@context"]["portal"] = log["5ltep:portalUrl"].rstrip("/") + "/"
        try:
            doc = ProvDocument.deserialize(
                content=json.dumps(record), format="rdf", rdf_format="json-ld")
            recs = list(doc.get_records())
            counts["entities"] += sum(r.get_type().localpart == "Entity" for r in recs)
            counts["activities"] += sum(r.get_type().localpart == "Activity" for r in recs)
            counts["agents"] += sum(r.get_type().localpart == "Agent" for r in recs)
            counts["derivations"] += sum(r.get_type().localpart == "Derivation" for r in recs)
            ok += 1
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print("FAIL", os.path.basename(path), type(exc).__name__, str(exc)[:120])
print(f"prov {prov.__version__} (portal ns declared={PATCH}): {ok} records parsed, {fail} failed; {counts}")

