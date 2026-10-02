# 5LTEP-L4: 5L-TEP Layer 4 Provenance Toolkit

[![Tests](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/tests.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/tests.yml) [![Layer 4](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Flsp3cesarschool%2F5ltep-layer4%2Fmain%2Fdocs%2Fdata%2Fstatus.json)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/monitor.yml) [![Cross-check](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Flsp3cesarschool%2F5ltep-layer4%2Fmain%2Fdocs%2Fdata%2Fstatus-cross-check.json)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/cross_check.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**English** · [Português](LEIAME.md)

**Records what changed in an open data portal, when, and how, as W3C PROV-DM provenance.**
Every six hours it reads the metadata of every dataset of a CKAN portal, fingerprints it, classifies
each change, and appends it to a per-dataset derivation chain that git makes tamper-evident.

| Resource | What you find there |
|---|---|
| 📊 **Dashboard** | [lsp3cesarschool.github.io/5ltep-layer4](https://lsp3cesarschool.github.io/5ltep-layer4/?lang=en): changes per month, where the files are, latest changes, monitoring health, every dataset |
| 📄 **Change log** | [`changes.md`](changes.md): every detected change in plain words, rebuilt each cycle |
| 🔗 **Provenance records** | [`provenance_logs/`](provenance_logs/): one append-only W3C PROV-DM (JSON-LD) chain per dataset |
| ✅ **Cross-check** | [`data/cross_check_report.json`](data/cross_check_report.json): a daily, independent comparison with the live portal (badge above) |
| 🔁 **Control experiments** | [5ltep-layer4-aneel](https://github.com/lsp3cesarschool/5ltep-layer4-aneel) and [5ltep-layer4-recife](https://github.com/lsp3cesarschool/5ltep-layer4-recife): the same code on two other portals (a federal regulator and a municipality) |
| 🧪 **Evaluation** | [`evaluation/`](evaluation/): scripts that reproduce the paper's evaluation |

> **Status: research demonstration.** This toolkit is part of a master's research project and is
> maintained by its author. It is not an official IBAMA service, and it does not assume that any
> agency will review its results or adopt it. Alerts reach the maintainer of this repository, not the
> agency; the records are ready for anyone who wants to audit the portal's history.

## Use case in one paragraph

Open data portals change in silence. Suppose a team downloads a dataset every month for a report.
Between two downloads the portal moves the files to another server and swaps a zip for a plain CSV,
while the format it declares stays "CSV" and nothing on the page says what changed: the team's
script breaks, or, worse, keeps running on a different file. This happened on IBAMA's portal in
August and September 2026, dataset after dataset, and this toolkit recorded each step (see the
dashboard's *Where the files are*). It reads the metadata of every dataset every six hours and
records each change as a provenance entity linked to the version before it: what changed, when it
was first seen, who is accountable for the data (the publishing agency) and who observed it (this
toolkit). A change made without a new modification date, which would otherwise go unnoticed, is
flagged as critical. Before trusting a file, anyone who reuses the data can check whether it is
still the one they validated, and an auditor gets an append-only history of the portal.

## Key terms

| Term | Meaning here |
|---|---|
| **Snapshot** | The metadata of every dataset of the portal as read in one monitoring cycle (stored once per distinct content). |
| **Fingerprint** | SHA-256 of a dataset's stable metadata fields; a different fingerprint means the dataset changed. |
| **Resource manifest** | Names, formats and count of a dataset's resources; when it changes, the change is a `SCHEMA_DRIFT`. |
| **PROV entity** | One version of a dataset, identified by its URL plus a fingerprint prefix (W3C PROV-DM). |
| **Derivation chain** | The versions of a dataset linked by `prov:wasDerivedFrom`, oldest to newest, never rewritten. |
| **Observer and custodian** | The two agents of each record: this toolkit, which saw the change, and the agency that publishes the data. |
| **Critical change** | `SCHEMA_DRIFT` (resources added, removed, renamed or re-formatted) or `RETRO_ALTER` (changed without a new modification date). |
| **Cross-check** | A separate daily script that re-reads the portal and compares the fields the agency sets with the latest snapshot. |

## Overview

This toolkit implements **Layer 4 (Observability & Provenance)** of the Five-Layer Trust Engineering Pyramid (5L-TEP) for Open Government Data quality assurance. It monitors CKAN-based data portals (e.g., [IBAMA](https://dadosabertos.ibama.gov.br)), detects changes via SHA-256 fingerprinting, and generates W3C PROV-DM–compliant provenance records in JSON-LD. Since v1.0.2, each record also describes *how* the dataset changed (changed fields, resource URL relocations, zip/plain packaging switches), and the same description feeds [`changes.md`](changes.md). Since v1.1.0, each cycle also writes the data of the [dashboard](https://lsp3cesarschool.github.io/5ltep-layer4/) and of the status badges (`docs/data/`), so the README itself is never rewritten by a workflow.

> **Scope**: This repository contains **only** the L4-essential modules. Layers 1–3 (structural/semantic/anomaly validation) and Layer 5 (governance dashboards) are outside this implementation's scope; combining the results of several layers is Layer 5's job.

### Architecture

```
┌──────────────────────────────────────────────────┐
│            GitHub Actions (cron 6h)              │
│           free for public repositories           │
└──────────────────────────┬───────────────────────┘
                           │ triggers
                           ▼
┌──────────────────────────────────────────────────┐
│  ① CKAN Harvester                                │
│     API polling + exponential backoff retry      │
│     (package_list + package_show)                │
└──────────────────────────┬───────────────────────┘
                           │ metadata snapshots
                           ▼
┌──────────────────────────────────────────────────┐
│  ② Hash Engine                                   │
│     SHA-256 content + resource-manifest hashes   │
│     Change taxonomy: 4 event types               │
│     (CLEAN_UPDATE, SCHEMA_DRIFT,                 │
│      RETRO_ALTER, CONTENT_MOD)                   │
└──────────────────────────┬───────────────────────┘
                           │ ChangeEvents
                           ▼
┌──────────────────────────────────────────────────┐
│  ★ ③ PROV-DM Mapper (L4 CORE)  ★                │
│     W3C PROV-DM JSON-LD generation               │
│     Content-addressable entity URIs              │
│     Dual-agent model: observer + custodian       │
│     Derivation chains + change annotations       │
└──────────────────────────┬───────────────────────┘
                           │ provenance records
                           ▼
┌──────────────────────────────────────────────────┐
│  Git Repository (append-only, immutable)         │
│  per-dataset .jsonld provenance logs             │
│  tamper-evident via Git commit hashes            │
└──────────────────────────────────────────────────┘
```

## Change-Detection Taxonomy


| Change Type | Severity | Description |
|---|---|---|
| `CLEAN_UPDATE` | INFO | No change detected (baseline or unchanged) |
| `SCHEMA_DRIFT` | **CRITICAL** | Structural change — resource count/names/formats altered |
| `RETRO_ALTER` | **CRITICAL** | Hash changed WITHOUT timestamp advancement — undocumented retroactive edit |
| `CONTENT_MOD` | WARNING | Content modification with proper timestamp update |

### Detection Logic

```
Given: h_t = SHA-256(canonical_json(stable_fields(metadata_t)))
       (title, notes, metadata_modified and each resource's name, format,
        URL, size and last modification; volatile API fields are excluded)
       h_{t-1} = stored hash from previous cycle

1. If h_{t-1} is NULL           → CLEAN_UPDATE (first observation)
2. If h_t == h_{t-1}            → CLEAN_UPDATE (no change)
3. If manifest_hash differs     → SCHEMA_DRIFT (structural break)
4. If timestamp_t ≤ timestamp_{t-1} → RETRO_ALTER (retroactive edit)
5. Otherwise                    → CONTENT_MOD (normal update)
```

## PROV-DM Mapping Strategy

### Dual-Agent Model

The toolkit implements a dual-agent provenance model that distinguishes the **observer** from the **data custodian**:

- **prov:SoftwareAgent** (observer): The 5L-TEP toolkit / GitHub Actions runner
- **5ltep:DataCustodian** (custodian): The originating government agency (from CKAN's `organization` field)

This ensures accountability is correctly attributed (cf. Simmhan et al., 2005), in alignment with Brazil's LAI transparency obligations.

### Entity Identification

Each dataset snapshot becomes a `prov:Entity` identified by a content-addressable URI:
```
{portal_url}/dataset/{dataset_id}#{sha256_prefix}
```
Because any change produces a cryptographically distinct identifier, PROV-DM's entity immutability requirement is inherently satisfied.

### Derivation Chains

When a dataset changes, the new entity links to its predecessor via `wasDerivedFrom`, forming an immutable derivation chain annotated with `5ltep:changeType` and `5ltep:severity`. Since v1.0.2, each record also describes *how* the dataset changed: `5ltep:changeSummary` (one-line English summary), `5ltep:changedFields`, `5ltep:fieldsOutsideFingerprint`, `5ltep:resourceUrlChanges`, `5ltep:hostMoves` and `5ltep:packagingChanges`.

## Quick Start

### Prerequisites

- Python 3.10+
- A CKAN-based open data portal

### Installation

```bash
git clone https://github.com/lsp3cesarschool/5ltep-layer4.git
cd 5ltep-layer4
pip install -r requirements.txt
```

### Running Locally

```bash
# Monitor 5 datasets from IBAMA portal
python main.py --portal https://dadosabertos.ibama.gov.br --max-datasets 5

# Dry run (no file persistence)
python main.py --portal https://dadosabertos.ibama.gov.br --max-datasets 3 --dry-run

# Full run (all datasets from specific organization)
python main.py --portal https://dadosabertos.ibama.gov.br --org ibama
```

### Running Tests

```bash
pytest tests/ -v
# 67 tests covering: hash determinism, 4 change types, dual-agent model,
# derivation chains, append-only persistence, end-to-end pipeline,
# critical-change alerting (SCHEMA_DRIFT/RETRO_ALTER) and CI signalling,
# PROV-O interoperability with the `prov` library (needs: pip install prov rdflib),
# change details (relocations, packaging), changes.md and dashboard data,
# portal.json, status badges, README/LEIAME structure, and the workflow
# behaviour stated in the WFA 2026 paper (schedules, alert order, SPARQL query)
```

### GitHub Actions Deployment

The toolkit runs automatically every 6 hours via GitHub Actions. It costs nothing: public repositories are not charged for standard runners (in a private repository, the measured usage would be about 15% of the 2,000-minute free tier). See `.github/workflows/monitor.yml`. The dashboard is a static page served by GitHub Pages from `docs/` (*Settings → Pages*: branch `main`, folder `/docs`).

Alerts cost nothing and need no mail server: on a critical event (`SCHEMA_DRIFT` or `RETRO_ALTER`) the workflow first commits the provenance records and then fails on purpose, and GitHub e-mails the maintainer about the failed run. The daily cross-check alerts the same way when portal coverage drops below 90% or divergences stay unreconciled for more than 7 h.

## PROV-DM Output Example

When a retroactive alteration is detected:

```json
{
  "@context": {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "5ltep": "https://5ltep.example.org/ontology#",
    "ckan": "https://ckan.org/schema#",
    "portal": "https://dadosabertos.ibama.gov.br/"
  },
  "@graph": [
    {
      "@id": "https://dadosabertos.ibama.gov.br/dataset/abc123#a1b2c3d4e5f6",
      "@type": ["prov:Entity", "5ltep:DatasetSnapshot"],
      "prov:wasGeneratedBy": {"@id": "5ltep:run-20260607T100000Z"},
      "prov:wasAttributedTo": {"@id": "https://dadosabertos.ibama.gov.br/organization/ibama"},
      "prov:wasDerivedFrom": {"@id": "https://dadosabertos.ibama.gov.br/dataset/abc123#f6e5d4c3b2a1"},
      "5ltep:changeType": "RETRO_ALTER",
      "5ltep:severity": "CRITICAL",
      "5ltep:contentHash": "a1b2c3d4e5f6...",
      "5ltep:detectedAt": {"@value": "2026-06-07T10:00:00+00:00", "@type": "xsd:dateTime"},
      "5ltep:changeSummary": "Description edited",
      "5ltep:changedFields": ["notes"],
      "5ltep:fieldsOutsideFingerprint": [],
      "5ltep:resourceUrlChanges": 0,
      "5ltep:hostMoves": 0,
      "5ltep:packagingChanges": 0
    },
    {
      "@id": "5ltep:run-20260607T100000Z",
      "@type": ["prov:Activity", "5ltep:MonitoringRun"],
      "prov:startedAtTime": {"@value": "2026-06-07T10:00:00+00:00", "@type": "xsd:dateTime"},
      "prov:endedAtTime": {"@value": "2026-06-07T10:00:02+00:00", "@type": "xsd:dateTime"},
      "prov:wasAssociatedWith": {"@id": "https://github.com/lsp3cesarschool/5ltep-layer4@abc1234"},
      "prov:used": {"@id": "https://dadosabertos.ibama.gov.br/api/3/action/package_show?id=abc123"}
    },
    {
      "@id": "https://github.com/lsp3cesarschool/5ltep-layer4@abc1234",
      "@type": ["prov:Agent", "prov:SoftwareAgent"],
      "rdfs:label": "5L-TEP Toolkit v1.0.2 (Layer 4 — Observability & Provenance)",
      "5ltep:repositoryUrl": "https://github.com/lsp3cesarschool/5ltep-layer4",
      "5ltep:commitSha": "abc1234567890"
    },
    {
      "@id": "https://dadosabertos.ibama.gov.br/organization/ibama",
      "@type": ["prov:Agent", "5ltep:DataCustodian"],
      "rdfs:label": "ibama",
      "5ltep:portalUrl": "https://dadosabertos.ibama.gov.br"
    }
  ]
}
```

## Project Structure

```
5ltep-layer4/
├── main.py                          # L4 pipeline orchestrator (entry point)
├── requirements.txt                 # Python dependencies
├── LICENSE                          # MIT License
├── README.md                        # This file
├── LEIAME.md                        # This file, in Portuguese
├── portal.json                      # The monitored portal (the one value to change for another portal)
├── changes.md                       # Human-readable change log (generated each cycle)
├── compress_snapshots.py            # Weekly gzip of snapshots older than 90 days
├── cross_check.py                   # Independent validator vs. live CKAN portal
├── .github/
│   └── workflows/
│       ├── monitor.yml              # Scheduled monitoring (every 6h, at :10)
│       ├── compress.yml             # Weekly snapshot compression (Sun 03:00 UTC)
│       ├── cross_check.yml          # Daily independent validation (03:30 UTC, off-peak)
│       └── tests.yml                # CI/CD test runner
├── src/
│   ├── __init__.py
│   ├── ckan_harvester.py            # CKAN API client with retry logic
│   ├── hash_engine.py              # SHA-256 fingerprinting & change detection
│   ├── change_summary.py           # Change details (fields, relocations) + changes.md
│   ├── dashboard.py                # Dashboard data + status badges (docs/data)
│   ├── cycle_failures.py           # Why a cycle failed (portal down, blocked, DNS...) for the dashboard
│   ├── portal_config.py            # Reads portal.json
│   └── prov_mapper.py              # ★ W3C PROV-DM JSON-LD generator (L4 core)
├── tests/
│   ├── __init__.py
│   └── test_toolkit.py             # 67 unit + integration tests
├── docs/                            # Dashboard (GitHub Pages): index.html, app.js, style.css
│   └── data/                        # layer4.json, cross_check.json, badges (committed by bot)
├── evaluation/                      # Scripts + results reproducing the paper's evaluation
├── data/                            # Runtime data (committed by bot)
│   ├── hash_store.json
│   ├── cross_check_report.json
│   ├── cycle_failures.json          # Why each failed cycle failed (recorded by the cycle or read from its log)
│   └── snapshots/
│       ├── manifest.json
│       └── snapshot_*.json[.gz]
└── provenance_logs/                 # PROV-DM JSON-LD logs (committed to git)
    └── {dataset_id}.jsonld
```

## Configuration

The monitored portal is declared in [`portal.json`](portal.json) (`portal_url`, plus a `name` and `title` for the dashboard).

| Environment Variable | Default | Description |
|---|---|---|
| `CKAN_PORTAL_URL` | _(empty)_ | Overrides `portal.json`; in GitHub Actions, set it as a repository variable (`--portal` overrides both) |
| `CKAN_ORG_FILTER` | _(empty)_ | Filter by organization |
| `MAX_DATASETS` | `0` (all) | Limit harvested datasets |
| `GITHUB_REPOSITORY` | `local` | Used for software agent identification |
| `GITHUB_SHA` | `local` | Used for software agent identification |

### Monitoring another CKAN portal

The continuous monitoring (every 6 h, with failure e-mails from GitHub) and the
daily cross-check read the portal from the repository variable `CKAN_PORTAL_URL`
when it is set, and otherwise from the versioned file [`portal.json`](portal.json).
No code change is needed:

1. **Fork** this repository.
2. In the fork, either create the repository variable `CKAN_PORTAL_URL`
   (*Settings → Secrets and variables → Actions → Variables*) with the portal's
   root URL (e.g., `https://dados.recife.pe.gov.br`), or edit `portal.json`
   (`portal_url`, plus the `name` and `title` the dashboard shows). The ANEEL
   and Recife instances use `portal.json`, so the difference is visible in git.
3. **Start with a clean history:** delete the whole `data/` and
   `provenance_logs/` folders, the `docs/data/` folder and the `changes.md` file
   inherited from this repository, and commit. They are recreated automatically.
4. Enable the workflows in the fork's **Actions** tab (GitHub disables scheduled
   workflows in forks until you do), and GitHub Pages in *Settings → Pages*
   (branch `main`, folder `/docs`). Failure e-mails go to the fork's owner. In
   the README of the fork, replace `lsp3cesarschool/5ltep-layer4` in the badge
   and dashboard links with the fork's name.
5. Optionally, run *5L-TEP Layer 4 Monitoring Workflow* once by hand
   (*Actions → Run workflow*) to record the baseline right away instead of
   waiting for the next 6-hour slot. Until the first cycle, the daily cross-check
   simply reports that there is nothing to compare yet.

Do not change the portal in this repository: its provenance history and
[`changes.md`](changes.md) refer to IBAMA, and mixing portals would corrupt them.
To try a portal once, without GitHub, run `python main.py --portal <url>` in a
separate working copy.

## Evaluation

The evaluation reported in the WFA/WebMedia 2026 paper (ground-truth check of
recorded events, fault injection, `prov` interoperability, operational statistics)
can be reproduced with the scripts in [`evaluation/`](evaluation/).

## Academic References

- Pinheiro, L. S., et al. (2026). *Towards Trust Engineering in Open Data Systems: A Layered Conceptual Framework Integrating Quality Assurance and Governance Perspectives*. SOFTENG 2026, IARIA, pp. 21–28.
- Pinheiro, L. S. & Sérgio, A. T. (2026). *5LTEP-L4: An Open-Source CKAN Toolkit for Provenance-Enabled Observability of Open Government Data*. XXV Workshop de Ferramentas e Aplicações (WFA), Anais Estendidos do WebMedia 2026, Lavras/MG, Brazil (to appear).
- Moreau, L. & Missier, P. (Eds.) (2013). *PROV-DM: The PROV Data Model*. W3C Recommendation. https://www.w3.org/TR/prov-dm/
- Groth, P. & Moreau, L. (2013). *PROV-Overview*. https://www.w3.org/TR/prov-overview/
- Simmhan, Y. L. et al. (2005). *A survey of data provenance in e-science*. ACM SIGMOD Record.

## License

MIT — see [LICENSE](LICENSE).
