# Evaluation scripts

Scripts that reproduce the evaluation reported in the WFA/WebMedia 2026 paper
*"5LTEP-L4: An Open-Source CKAN Toolkit for Provenance-Enabled Observability of
Open Government Data"*. Run them from the repository root. Outputs obtained on
2026-09-27 are kept in [`results/`](results/).

| Script | What it checks | Paper claim |
|---|---|---|
| `ground_truth_diff.py` | Diffs every pair of consecutive distinct snapshots in `data/snapshots/` field by field (without the Hash Engine) and matches the result against the events in `provenance_logs/` | 31/31 recorded events match the ground truth; no misses, no spurious events |
| `fault_injection.py` | Injects 9 change scenarios into every dataset of the latest snapshot and reports the confusion matrix of the classifier | 632/632 in-scope cases correct; tag/license-only edits are not fingerprinted |
| `prov_interop.py` | Loads every PROV-DM record with the [`prov`](https://github.com/trungdong/prov) library's PROV-O reader | 31/31 records load (records written before v1.0.1 need `--declare-portal-ns`) |
| `actions_stats.py` | Queries the GitHub Actions API for cycles, success rate, gaps, durations and billed minutes | 430 cycles, 97.2% successful, 290 billed min in 30 days |

```bash
python evaluation/ground_truth_diff.py
python evaluation/fault_injection.py
pip install prov rdflib && python evaluation/prov_interop.py --declare-portal-ns
python evaluation/actions_stats.py            # optional: export GITHUB_TOKEN=...
```

## Portability to other CKAN portals

No code change is needed; only the portal URL:

```bash
python main.py --portal https://dados.recife.pe.gov.br      # 223 datasets
python main.py --portal https://dadosabertos.aneel.gov.br   # 72 datasets
```

Three consecutive cycles per portal are recorded in [`results/portability.txt`](results/portability.txt).
Run them in a separate working copy, since `main.py` writes to `data/` and `provenance_logs/`.
