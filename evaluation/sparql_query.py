"""
Lineage queries over the PROV-DM records with SPARQL (rdflib).

The WFA 2026 paper (Section 3.2) states that the JSON-LD records can be
ingested into SPARQL endpoints for lineage queries such as "which datasets had
retroactive alterations in the last 30 days?". This script demonstrates it:
it loads every record of provenance_logs/ into one RDF graph (no conversion
step: the files are already JSON-LD) and runs that query, plus a count of the
recorded changes by type, which shows the same query machinery on data the
portal actually produced.

Usage (from the repository root):
    pip install rdflib
    python evaluation/sparql_query.py                      # RETRO_ALTER, last 30 days
    python evaluation/sparql_query.py --type CONTENT_MOD --days 120
"""

import argparse
import glob
import json
from datetime import datetime, timedelta, timezone

from rdflib import Graph

NS_5LTEP = "https://5ltep.example.org/ontology#"

WINDOW_QUERY = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
PREFIX l4:   <%s>
SELECT ?dataset ?entity ?previous ?when WHERE {
  ?entity a prov:Entity ;
          l4:changeType "%s" ;
          l4:datasetId ?dataset ;
          l4:detectedAt ?when .
  OPTIONAL { ?entity prov:wasDerivedFrom ?previous }
  FILTER (?when >= "%s"^^xsd:dateTime)
}
ORDER BY DESC(?when)
"""

BY_TYPE_QUERY = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX l4:   <%s>
SELECT ?type (COUNT(?entity) AS ?events) (COUNT(DISTINCT ?dataset) AS ?datasets) WHERE {
  ?entity a prov:Entity ; l4:changeType ?type ; l4:datasetId ?dataset .
}
GROUP BY ?type ORDER BY DESC(?events)
"""


def load_graph(prov_dir: str) -> tuple:
    graph, records = Graph(), 0
    for path in sorted(glob.glob(f"{prov_dir}/*.jsonld")):
        with open(path, encoding="utf-8") as fh:
            for record in json.load(fh)["provenance_chain"]:
                graph.parse(data=json.dumps(record), format="json-ld")
                records += 1
    return graph, records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prov-dir", default="provenance_logs")
    ap.add_argument("--type", default="RETRO_ALTER", help="change type to look for (default: RETRO_ALTER)")
    ap.add_argument("--days", type=int, default=30, help="window, counted back from now (default: 30)")
    args = ap.parse_args()

    graph, records = load_graph(args.prov_dir)
    print(f"loaded {records} PROV-DM records from {args.prov_dir}/ into one RDF graph ({len(graph)} triples)")

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    rows = list(graph.query(WINDOW_QUERY % (NS_5LTEP, args.type, since)))
    print(f"\nQ1. Which datasets had {args.type} events in the last {args.days} days (since {since[:10]})?")
    if not rows:
        print("    none")
    for dataset, entity, previous, when in rows:
        print(f"    {when}  dataset {dataset}\n        entity  {entity}\n        derived from {previous or '(first recorded version)'}")

    print("\nQ2. Recorded changes by type (all time):")
    for change_type, events, datasets in graph.query(BY_TYPE_QUERY % NS_5LTEP):
        print(f"    {change_type:<13} {int(events):>4} events in {int(datasets)} datasets")


if __name__ == "__main__":
    main()
