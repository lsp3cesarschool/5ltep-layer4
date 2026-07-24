"""
Tests for the 5L-TEP Layer 4 Provenance Toolkit
=================================================
Run with: pytest tests/ -v

Covers only L4-essential modules: hash_engine, prov_mapper, ckan_harvester.

Change taxonomy (5L-TEP L4 specification):
    CLEAN_UPDATE  → INFO
    SCHEMA_DRIFT  → CRITICAL
    RETRO_ALTER   → CRITICAL
    CONTENT_MOD   → WARNING
"""

import json
import os
import sys
import tempfile
from typing import Any, Dict

import pytest

# Add repository root and src/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import main
from hash_engine import HashEngine, ChangeType, Severity, ChangeEvent, SEVERITY_MAP
from prov_mapper import ProvMapper


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_dataset() -> Dict[str, Any]:
    """Complete, valid CKAN dataset metadata fixture (IBAMA-like)."""
    return {
        "id": "abc123",
        "name": "embargos-ambientais",
        "title": "Embargos Ambientais Federais",
        "state": "active",
        "license_id": "cc-by",
        "metadata_created": "2024-01-01T00:00:00",
        "metadata_modified": "2026-05-01T10:00:00",
        "frequency": "monthly",
        "num_resources": 3,
        "notes": "Dados sobre embargos ambientais emitidos pelo IBAMA.",
        "resources": [
            {"id": "r1", "name": "embargos.csv", "format": "CSV",
             "url": "https://ibama.gov.br/data/1.csv", "size": 1024,
             "last_modified": "2026-05-01"},
            {"id": "r2", "name": "embargos.json", "format": "JSON",
             "url": "https://ibama.gov.br/data/1.json", "size": 2048,
             "last_modified": "2026-05-01"},
            {"id": "r3", "name": "embargos.xml", "format": "XML",
             "url": "https://ibama.gov.br/data/1.xml", "size": 4096,
             "last_modified": "2026-05-01"},
        ],
        "tags": [{"name": "ibama"}, {"name": "embargo"}, {"name": "meio-ambiente"}],
        "organization": {"name": "ibama", "title": "IBAMA"},
    }


# ---------------------------------------------------------------------------
# Hash Engine Tests
# ---------------------------------------------------------------------------

class TestHashEngine:
    def test_compute_hash_deterministic(self, sample_dataset):
        """Same input always produces same hash (canonical JSON serialisation)."""
        h1 = HashEngine.compute_hash(sample_dataset)
        h2 = HashEngine.compute_hash(sample_dataset)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest length

    def test_compute_hash_changes_with_data(self, sample_dataset):
        """Different input produces different hash."""
        h1 = HashEngine.compute_hash(sample_dataset)
        modified = {**sample_dataset, "title": "Modified Title"}
        modified["resources"] = sample_dataset["resources"]
        h2 = HashEngine.compute_hash(modified)
        assert h1 != h2

    def test_first_run_produces_clean_update(self, sample_dataset, tmp_path):
        """First observation is classified as CLEAN_UPDATE (baseline)."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        events = engine.detect_changes([sample_dataset])
        assert len(events) == 1
        assert events[0].change_type == ChangeType.CLEAN_UPDATE

    def test_no_change_produces_clean_update(self, sample_dataset, tmp_path):
        """Same data on second run is CLEAN_UPDATE."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        engine.detect_changes([sample_dataset])  # seed
        events = engine.detect_changes([sample_dataset])  # same data
        assert len(events) == 1
        assert events[0].change_type == ChangeType.CLEAN_UPDATE

    def test_content_mod_detected(self, sample_dataset, tmp_path):
        """Changed content with advancing timestamp → CONTENT_MOD (WARNING)."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        engine.detect_changes([sample_dataset])  # seed

        modified = {**sample_dataset, "metadata_modified": "2026-06-01T00:00:00",
                    "notes": "Updated description"}
        modified["resources"] = sample_dataset["resources"]
        events = engine.detect_changes([modified])

        assert len(events) == 1
        assert events[0].change_type == ChangeType.CONTENT_MOD
        assert events[0].severity == Severity.WARNING

    def test_schema_drift_detected(self, sample_dataset, tmp_path):
        """Adding a resource → SCHEMA_DRIFT (CRITICAL)."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        engine.detect_changes([sample_dataset])  # seed

        drifted = {**sample_dataset, "metadata_modified": "2026-06-02T00:00:00"}
        drifted["num_resources"] = 4
        drifted["resources"] = sample_dataset["resources"] + [
            {"id": "r4", "name": "new.pdf", "format": "PDF",
             "url": "https://ibama.gov.br/data/1.pdf", "size": 8192,
             "last_modified": "2026-06-02"},
        ]
        events = engine.detect_changes([drifted])

        assert len(events) == 1
        assert events[0].change_type == ChangeType.SCHEMA_DRIFT
        assert events[0].severity == Severity.CRITICAL

    def test_retro_alter_detected(self, sample_dataset, tmp_path):
        """Hash changes but timestamp goes backward → RETRO_ALTER (CRITICAL)."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        engine.detect_changes([sample_dataset])  # seed (timestamp: 2026-05-01)

        retro = {**sample_dataset, "metadata_modified": "2023-01-01T00:00:00",
                 "notes": "Silently altered content"}
        retro["resources"] = sample_dataset["resources"]
        events = engine.detect_changes([retro])

        assert len(events) == 1
        assert events[0].change_type == ChangeType.RETRO_ALTER
        assert events[0].severity == Severity.CRITICAL

    def test_hash_store_persisted(self, sample_dataset, tmp_path):
        """Hash store is written to disk after processing."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        engine.detect_changes([sample_dataset])

        assert os.path.exists(store_path)
        with open(store_path) as f:
            store = json.load(f)
        assert "abc123" in store
        assert "content_hash" in store["abc123"]
        assert "manifest_hash" in store["abc123"]

    def test_severity_mapping_v16(self):
        """Verify severity mapping matches 5L-TEP L4 specification."""
        assert SEVERITY_MAP[ChangeType.SCHEMA_DRIFT] == Severity.CRITICAL
        assert SEVERITY_MAP[ChangeType.RETRO_ALTER] == Severity.CRITICAL
        assert SEVERITY_MAP[ChangeType.CONTENT_MOD] == Severity.WARNING
        assert SEVERITY_MAP[ChangeType.CLEAN_UPDATE] == Severity.INFO

    def test_organization_captured(self, sample_dataset, tmp_path):
        """Organization name is captured from CKAN metadata for dual-agent model."""
        store_path = str(tmp_path / "hashes.json")
        engine = HashEngine(hash_store_path=store_path, portal_url="https://test.gov.br")
        events = engine.detect_changes([sample_dataset])
        assert events[0].organization == "ibama"


# ---------------------------------------------------------------------------
# PROV Mapper Tests
# ---------------------------------------------------------------------------

class TestProvMapper:
    def _make_event(self, portal_url="https://dados.gov.br") -> ChangeEvent:
        """Create a sample ChangeEvent for testing."""
        return ChangeEvent(
            dataset_id="abc123",
            change_type=ChangeType.SCHEMA_DRIFT,
            current_hash="b" * 64,
            previous_hash="a" * 64,
            current_timestamp="2026-06-01T00:00:00",
            previous_timestamp="2026-05-01T00:00:00",
            portal_url=portal_url,
            organization="ibama",
        )

    def test_generate_record_structure(self, tmp_path):
        """Record contains @context and @graph with dual-agent model."""
        mapper = ProvMapper(
            provenance_dir=str(tmp_path / "prov"),
            repository_url="https://github.com/test/repo",
            commit_sha="abc1234567890",
        )
        event = self._make_event()
        record = mapper.generate_record(event)

        assert "@context" in record
        assert "@graph" in record
        # 4 nodes: entity, activity, software agent, custodian agent
        assert len(record["@graph"]) == 4

    def test_entity_has_content_addressable_uri(self, tmp_path):
        """Entity URI includes SHA-256 hash prefix (§3.3.1)."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        event = self._make_event()
        record = mapper.generate_record(event)

        entity = record["@graph"][0]
        assert "bbbbbbbbbbbb" in entity["@id"]  # first 12 chars of hash
        assert "abc123" in entity["@id"]

    def test_derivation_chain_present(self, tmp_path):
        """Entity includes wasDerivedFrom when previous hash exists (§3.3.3)."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        event = self._make_event()
        record = mapper.generate_record(event)

        entity = record["@graph"][0]
        assert "prov:wasDerivedFrom" in entity
        assert "aaaaaaaaaaaa" in entity["prov:wasDerivedFrom"]["@id"]

    def test_no_derivation_for_first_observation(self, tmp_path):
        """No derivation when previous_hash is None."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        event = ChangeEvent(
            dataset_id="new_ds",
            change_type=ChangeType.CLEAN_UPDATE,
            current_hash="c" * 64,
            previous_hash=None,
            current_timestamp="2026-06-01T00:00:00",
            previous_timestamp=None,
            portal_url="https://dados.gov.br",
            organization="ibama",
        )
        record = mapper.generate_record(event)
        entity = record["@graph"][0]
        assert "prov:wasDerivedFrom" not in entity

    def test_change_type_and_severity_in_entity(self, tmp_path):
        """Entity includes change type and severity annotations (§3.2)."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        event = self._make_event()  # SCHEMA_DRIFT -> CRITICAL
        record = mapper.generate_record(event)

        entity = record["@graph"][0]
        assert entity["5ltep:changeType"] == "SCHEMA_DRIFT"
        assert entity["5ltep:severity"] == "CRITICAL"

    def test_dual_agent_model(self, tmp_path):
        """
        Dual-agent model (§3.3.2): software agent (observer) and
        data custodian (government agency) are both present.
        """
        mapper = ProvMapper(
            provenance_dir=str(tmp_path / "prov"),
            repository_url="https://github.com/user/repo",
            commit_sha="deadbeef12345",
        )
        event = self._make_event()
        record = mapper.generate_record(event)

        # Software agent (observer)
        sw_agent = record["@graph"][2]
        assert "prov:SoftwareAgent" in sw_agent["@type"]
        assert "deadbee" in sw_agent["@id"]

        # Custodian agent (government agency)
        custodian = record["@graph"][3]
        assert "5ltep:DataCustodian" in custodian["@type"]
        assert "ibama" in custodian["@id"]

    def test_entity_attributed_to_custodian(self, tmp_path):
        """Entity wasAttributedTo points to custodian, not software agent (§3.3.2)."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        event = self._make_event()
        record = mapper.generate_record(event)

        entity = record["@graph"][0]
        assert "ibama" in entity["prov:wasAttributedTo"]["@id"]

    def test_save_records_creates_file(self, tmp_path):
        """save_records creates a per-dataset JSON-LD file (§3.4)."""
        prov_dir = str(tmp_path / "prov")
        mapper = ProvMapper(provenance_dir=prov_dir)
        event = self._make_event()
        paths = mapper.save_records([event])

        assert len(paths) == 1
        assert os.path.exists(paths[0])

        with open(paths[0]) as f:
            log = json.load(f)
        assert log["5ltep:datasetId"] == "abc123"
        assert len(log["provenance_chain"]) == 1

    def test_save_records_appends(self, tmp_path):
        """Multiple calls append to the same log file (append-only, §3.4)."""
        prov_dir = str(tmp_path / "prov")
        mapper = ProvMapper(provenance_dir=prov_dir)
        event = self._make_event()

        mapper.save_records([event])
        mapper.save_records([event])

        log_path = tmp_path / "prov" / "abc123.jsonld"
        with open(log_path) as f:
            log = json.load(f)
        assert len(log["provenance_chain"]) == 2

    def test_generate_records_batch(self, tmp_path):
        """generate_records processes multiple events."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        events = [self._make_event() for _ in range(3)]
        records = mapper.generate_records(events)
        assert len(records) == 3

    def test_get_summary(self, tmp_path):
        """get_summary produces correct statistics."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        events = [
            self._make_event(),
            ChangeEvent(
                dataset_id="other",
                change_type=ChangeType.CONTENT_MOD,
                current_hash="x" * 64,
                previous_hash="y" * 64,
                current_timestamp="2026-06-01",
                previous_timestamp="2026-05-01",
                portal_url="https://test.gov.br",
                organization="icmbio",
            ),
        ]
        summary = mapper.get_summary(events)
        assert summary["total_datasets"] == 2
        assert "SCHEMA_DRIFT" in summary["change_types"]
        assert "CONTENT_MOD" in summary["change_types"]
        assert "Layer 4" in summary["scope"]


# ---------------------------------------------------------------------------
# Integration Test (Pipeline)
# ---------------------------------------------------------------------------

class TestPipeline:
    def test_full_pipeline_hash_to_prov(self, sample_dataset, tmp_path):
        """End-to-end: HashEngine → ProvMapper produces valid PROV-DM records."""
        store_path = str(tmp_path / "hashes.json")
        prov_dir = str(tmp_path / "prov")

        # Step 1: Seed the hash engine
        engine = HashEngine(hash_store_path=store_path, portal_url="https://dados.gov.br")
        engine.detect_changes([sample_dataset])

        # Step 2: Modify data and detect changes
        modified = {**sample_dataset, "metadata_modified": "2026-06-07T12:00:00",
                    "notes": "Updated environmental data"}
        modified["resources"] = sample_dataset["resources"]
        events = engine.detect_changes([modified])

        # Step 3: Generate provenance records
        mapper = ProvMapper(provenance_dir=prov_dir)
        non_clean = [e for e in events if e.change_type != ChangeType.CLEAN_UPDATE]
        assert len(non_clean) == 1
        assert non_clean[0].change_type == ChangeType.CONTENT_MOD

        records = mapper.generate_records(non_clean)
        assert len(records) == 1
        assert records[0]["@graph"][0]["5ltep:changeType"] == "CONTENT_MOD"
        assert records[0]["@graph"][0]["5ltep:severity"] == "WARNING"

        # Step 4: Save and verify persistence
        paths = mapper.save_records(non_clean)
        assert os.path.exists(paths[0])

    def test_retro_alter_pipeline(self, sample_dataset, tmp_path):
        """RETRO_ALTER end-to-end: undocumented edit detection → PROV record."""
        store_path = str(tmp_path / "hashes.json")
        prov_dir = str(tmp_path / "prov")

        # Seed
        engine = HashEngine(hash_store_path=store_path, portal_url="https://dados.gov.br")
        engine.detect_changes([sample_dataset])

        # Retroactive alteration: timestamp goes backward
        retro = {**sample_dataset, "metadata_modified": "2025-01-01T00:00:00",
                 "notes": "Silently changed"}
        retro["resources"] = sample_dataset["resources"]
        events = engine.detect_changes([retro])

        non_clean = [e for e in events if e.change_type != ChangeType.CLEAN_UPDATE]
        assert len(non_clean) == 1
        assert non_clean[0].change_type == ChangeType.RETRO_ALTER
        assert non_clean[0].severity == Severity.CRITICAL

        # Generate and verify PROV record
        mapper = ProvMapper(provenance_dir=prov_dir)
        records = mapper.generate_records(non_clean)
        entity = records[0]["@graph"][0]
        assert entity["5ltep:changeType"] == "RETRO_ALTER"
        assert entity["5ltep:severity"] == "CRITICAL"
        assert "prov:wasDerivedFrom" in entity


# ---------------------------------------------------------------------------
# Critical-change alerting (main.run_pipeline summary + CI signalling)
# ---------------------------------------------------------------------------

class TestCriticalAlerting:
    def _drifted(self, sample_dataset):
        """sample_dataset with an extra resource → SCHEMA_DRIFT (CRITICAL)."""
        drifted = {**sample_dataset, "metadata_modified": "2026-06-02T00:00:00",
                   "num_resources": 4}
        drifted["resources"] = sample_dataset["resources"] + [
            {"id": "r4", "name": "new.pdf", "format": "PDF",
             "url": "https://ibama.gov.br/data/1.pdf", "size": 8192,
             "last_modified": "2026-06-02"},
        ]
        return drifted

    def test_run_pipeline_counts_critical_schema_drift(
        self, sample_dataset, tmp_path, monkeypatch
    ):
        """run_pipeline reports SCHEMA_DRIFT in summary.critical_events."""
        hashes = tmp_path / "hash_store.json"
        snaps = tmp_path / "snapshots"
        prov = tmp_path / "prov"
        snaps.mkdir(parents=True, exist_ok=True)
        prov.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(main, "HASHES_FILE", hashes)
        monkeypatch.setattr(main, "SNAPSHOTS_DIR", snaps)
        monkeypatch.setattr(main, "MANIFEST_FILE", snaps / "manifest.json")
        monkeypatch.setattr(main, "PROV_DIR", prov)

        # Seed baseline so the next observation is a comparison, not a baseline.
        HashEngine(hash_store_path=str(hashes),
                   portal_url="https://test.gov.br").detect_changes([sample_dataset])

        drifted = self._drifted(sample_dataset)

        class _FakeHarvester:
            def __init__(self, *args, **kwargs):
                pass

            def harvest_all(self):
                return [drifted]

        monkeypatch.setattr(main, "CKANHarvester", _FakeHarvester)

        summary = main.run_pipeline(portal_url="https://test.gov.br")

        assert summary["critical_events"] == 1
        assert summary["change_events"] == 1
        assert summary["critical_datasets"][0]["dataset_id"] == "abc123"
        assert summary["critical_datasets"][0]["change_type"] == "SCHEMA_DRIFT"

    def test_run_pipeline_no_critical_on_content_mod(
        self, sample_dataset, tmp_path, monkeypatch
    ):
        """CONTENT_MOD (WARNING) is a change but NOT counted as critical."""
        hashes = tmp_path / "hash_store.json"
        snaps = tmp_path / "snapshots"
        prov = tmp_path / "prov"
        snaps.mkdir(parents=True, exist_ok=True)
        prov.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(main, "HASHES_FILE", hashes)
        monkeypatch.setattr(main, "SNAPSHOTS_DIR", snaps)
        monkeypatch.setattr(main, "MANIFEST_FILE", snaps / "manifest.json")
        monkeypatch.setattr(main, "PROV_DIR", prov)

        HashEngine(hash_store_path=str(hashes),
                   portal_url="https://test.gov.br").detect_changes([sample_dataset])

        modified = {**sample_dataset, "metadata_modified": "2026-06-03T00:00:00",
                    "notes": "Legitimate update"}
        modified["resources"] = sample_dataset["resources"]

        class _FakeHarvester:
            def __init__(self, *args, **kwargs):
                pass

            def harvest_all(self):
                return [modified]

        monkeypatch.setattr(main, "CKANHarvester", _FakeHarvester)

        summary = main.run_pipeline(portal_url="https://test.gov.br")

        assert summary["change_events"] == 1
        assert summary["critical_events"] == 0
        assert summary["critical_datasets"] == []

    def test_emit_github_output_flags_critical(self, tmp_path, monkeypatch):
        """_emit_github_output writes critical=true with count and dataset list."""
        out = tmp_path / "gh_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(out))
        main._emit_github_output({
            "critical_events": 2,
            "critical_datasets": [
                {"dataset_id": "ds-a", "change_type": "SCHEMA_DRIFT"},
                {"dataset_id": "ds-b", "change_type": "RETRO_ALTER"},
            ],
        })
        content = out.read_text(encoding="utf-8")
        assert "critical=true" in content
        assert "critical_events=2" in content
        assert "ds-a (SCHEMA_DRIFT)" in content
        assert "ds-b (RETRO_ALTER)" in content
        assert "critical_dataset_files=ds-a.jsonld,ds-b.jsonld" in content

    def test_emit_github_output_silent_when_clean(self, tmp_path, monkeypatch):
        """No critical events → critical=false (no alert)."""
        out = tmp_path / "gh_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(out))
        main._emit_github_output({"critical_events": 0, "critical_datasets": []})
        content = out.read_text(encoding="utf-8")
        assert "critical=false" in content
        assert "critical_events=0" in content

    def test_emit_github_output_noop_outside_ci(self, monkeypatch):
        """Outside Actions ($GITHUB_OUTPUT unset) the call is a harmless no-op."""
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        main._emit_github_output({"critical_events": 1, "critical_datasets": []})
