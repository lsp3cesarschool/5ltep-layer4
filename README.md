# 5L-TEP Layer 4 Provenance Toolkit

**W3C PROV-DM–compliant provenance monitoring for CKAN-based Open Government Data portals.**

[![Tests](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/tests.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/tests.yml)
[![Monitoring](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/monitor.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/monitor.yml)
[![Cross-Check](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/cross_check.yml/badge.svg)](https://github.com/lsp3cesarschool/5ltep-layer4/actions/workflows/cross_check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

<!-- CROSS_CHECK_STATUS:START -->
✅ **Cross-check passing** — last verified 2026-06-29 08:32 UTC. All 73 reachable datasets in sync with live IBAMA portal; latest snapshot is 4.5h old.
<!-- CROSS_CHECK_STATUS:END -->

## Overview

This toolkit implements **Layer 4 (Observability & Provenance)** of the Five-Layer Trust Engineering Pyramid (5L-TEP) for Open Government Data quality assurance. It monitors CKAN-based data portals (e.g., [IBAMA](https://dadosabertos.ibama.gov.br)), detects changes via SHA-256 fingerprinting, and generates W3C PROV-DM–compliant provenance records in JSON-LD.

> **Scope**: This repository contains **only** the L4-essential modules. Layers 1–3 (structural/semantic/anomaly validation) and Layer 5 (governance dashboards) are outside this implementation's scope.

### Architecture

```
┌──────────────────────────────────────────────────┐
│            GitHub Actions (cron 6h)               │
│            free-tier < 12% budget                 │
└──────────────────────────┬───────────────────────┘
                           │ triggers
                           ▼
┌──────────────────────────────────────────────────┐
│  ① CKAN Harvester                                │
│     API polling + exponential backoff retry       │
│     (package_list + package_show)                 │
└──────────────────────────┬───────────────────────┘
                           │ metadata snapshots
                           ▼
┌──────────────────────────────────────────────────┐
│  ② Hash Engine                                   │
│     SHA-256 content + schema fingerprinting      │
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

As formalised in Section 3.2 of the KDMiLe 2026 paper:

| Change Type | Severity | Description |
|---|---|---|
| `CLEAN_UPDATE` | INFO | No change detected (baseline or unchanged) |
| `SCHEMA_DRIFT` | **CRITICAL** | Structural change — resource count/names/formats altered |
| `RETRO_ALTER` | **CRITICAL** | Hash changed WITHOUT timestamp advancement — undocumented retroactive edit |
| `CONTENT_MOD` | WARNING | Content modification with proper timestamp update |

### Detection Logic

```
Given: h_t = SHA-256(canonical_json(metadata_t))
       h_{t-1} = stored hash from previous cycle

1. If h_{t-1} is NULL           → CLEAN_UPDATE (first observation)
2. If h_t == h_{t-1}            → CLEAN_UPDATE (no change)
3. If manifest_hash differs     → SCHEMA_DRIFT (structural break)
4. If timestamp_t ≤ timestamp_{t-1} → RETRO_ALTER (retroactive edit)
5. Otherwise                    → CONTENT_MOD (normal update)
```

## PROV-DM Mapping Strategy (Section 3.3)

### Dual-Agent Model

The toolkit implements a dual-agent provenance model that distinguishes the **observer** from the **data custodian**:

- **prov:SoftwareAgent** (observer): The 5L-TEP toolkit / GitHub Actions runner
- **5ltep:DataCustodian** (custodian): The originating government agency (from CKAN's `organization` field)

This ensures accountability is correctly attributed (cf. Simmhan et al., 2005), in alignment with Brazil's LAI transparency obligations.

### Entity Identification (§3.3.1)

Each dataset snapshot becomes a `prov:Entity` identified by a content-addressable URI:
```
{portal_url}/dataset/{dataset_id}#{sha256_prefix}
```
Because any change produces a cryptographically distinct identifier, PROV-DM's entity immutability requirement is inherently satisfied.

### Derivation Chains (§3.3.3)

When a dataset changes, the new entity links to its predecessor via `wasDerivedFrom`, forming an immutable derivation chain annotated with `5ltep:changeType`.

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
# 28 tests covering: hash determinism, 4 change types, dual-agent model,
# derivation chains, append-only persistence, end-to-end pipeline,
# critical-change alerting (SCHEMA_DRIFT/RETRO_ALTER) and CI signalling
```

### GitHub Actions Deployment

The toolkit runs automatically every 6 hours via GitHub Actions (within the free-tier limit of ~12% usage). See `.github/workflows/monitor.yml`.

## PROV-DM Output Example

When a retroactive alteration is detected:

```json
{
  "@context": {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "5ltep": "https://5ltep.example.org/ontology#",
    "ckan": "https://ckan.org/schema#"
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
      "5ltep:detectedAt": {"@value": "2026-06-07T10:00:00+00:00", "@type": "xsd:dateTime"}
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
      "rdfs:label": "5L-TEP Toolkit v1.0.0 (Layer 4 — Observability & Provenance)",
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
├── compress_snapshots.py            # Weekly gzip of snapshots older than 90 days
├── cross_check.py                   # Independent validator vs. live CKAN portal
├── .github/
│   └── workflows/
│       ├── monitor.yml              # Scheduled monitoring (every 6h)
│       ├── compress.yml             # Weekly snapshot compression (Sun 03:00 UTC)
│       ├── cross_check.yml          # Daily independent validation (03:30 UTC, off-peak)
│       └── tests.yml                # CI/CD test runner
├── src/
│   ├── __init__.py
│   ├── ckan_harvester.py            # CKAN API client with retry logic
│   ├── hash_engine.py              # SHA-256 fingerprinting & change detection
│   └── prov_mapper.py              # ★ W3C PROV-DM JSON-LD generator (L4 core)
├── tests/
│   ├── __init__.py
│   └── test_toolkit.py             # 23 unit + integration tests
├── data/                            # Runtime data (committed by bot)
│   ├── hash_store.json
│   ├── cross_check_report.json
│   └── snapshots/
│       ├── manifest.json
│       └── snapshot_*.json[.gz]
└── provenance_logs/                 # PROV-DM JSON-LD logs (committed to git)
    └── {dataset_id}.jsonld
```

## Configuration

| Environment Variable | Default | Description |
|---|---|---|
| `CKAN_PORTAL_URL` | `https://dadosabertos.ibama.gov.br` | Target CKAN portal |
| `CKAN_ORG_FILTER` | _(empty)_ | Filter by organization |
| `MAX_DATASETS` | `0` (all) | Limit harvested datasets |
| `GITHUB_REPOSITORY` | `local` | Used for software agent identification |
| `GITHUB_SHA` | `local` | Used for software agent identification |

## Academic References

- Pinheiro, L. S., et al. (2026). *5L-TEP: A Five-Layer Trust Engineering Pyramid for Open Government Data*. SOFTENG 2026.
- Pinheiro, L. S. & Sérgio, A. T. (2026). *Provenance-based Observability for Open Government Data via W3C PROV-DM and GitHub Actions*. KDMiLe 2026 (preprint).
- W3C. (2013). *PROV-DM: The PROV Data Model*. https://www.w3.org/TR/prov-dm/
- Groth, P. & Moreau, L. (2013). *PROV-Overview*. https://www.w3.org/TR/prov-overview/
- Simmhan, Y. L. et al. (2005). *A survey of data provenance in e-science*. ACM SIGMOD Record.

## License

MIT — see [LICENSE](LICENSE).
