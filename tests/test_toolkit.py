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


@pytest.fixture(autouse=True)
def _isolated_docs(tmp_path, monkeypatch):
    """Dashboard data, badges and failure records written by run_pipeline go to tmp_path, never to
    docs/ or data/; and no test asks the GitHub Actions API, even when the suite runs in CI."""
    monkeypatch.setattr(main, "DOCS_DATA_DIR", tmp_path / "docs_data")
    monkeypatch.setattr(main, "FAILURES_FILE", tmp_path / "cycle_failures.json")
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


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

    def test_dry_run_engine_leaves_store_untouched(self, sample_dataset, tmp_path):
        """persist=False (main.py --dry-run) never writes the hash store."""
        store = tmp_path / "hashes.json"
        HashEngine(hash_store_path=str(store), portal_url="https://test.gov.br",
                   persist=False).detect_changes([sample_dataset])
        assert not store.exists()

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

    def test_context_declares_portal_namespace(self, tmp_path):
        """@context declares the portal base IRI so all IRIs compact to QNames."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"))
        record = mapper.generate_record(self._make_event("https://dados.gov.br/"))
        assert record["@context"]["portal"] == "https://dados.gov.br/"

    def test_software_agent_id_is_absolute(self, tmp_path):
        """GITHUB_REPOSITORY ("owner/repo") is expanded to an absolute IRI."""
        mapper = ProvMapper(
            provenance_dir=str(tmp_path / "prov"),
            repository_url="user/repo",
            commit_sha="deadbeef12345",
        )
        sw_agent = mapper.generate_record(self._make_event())["@graph"][2]
        assert sw_agent["@id"] == "https://github.com/user/repo@deadbee"

    def test_local_run_uses_toolkit_agent_id(self, tmp_path):
        """Local runs (repository 'local') fall back to the toolkit QName."""
        mapper = ProvMapper(provenance_dir=str(tmp_path / "prov"), repository_url="local")
        sw_agent = mapper.generate_record(self._make_event())["@graph"][2]
        assert sw_agent["@id"].startswith("5ltep:toolkit-v")

    def test_record_loads_with_prov_library(self, tmp_path):
        """Records are readable by the `prov` library's PROV-O (RDF) reader."""
        prov_model = pytest.importorskip("prov.model")
        pytest.importorskip("rdflib")
        mapper = ProvMapper(
            provenance_dir=str(tmp_path / "prov"),
            repository_url="user/repo",
            commit_sha="deadbeef12345",
        )
        record = mapper.generate_record(self._make_event("https://dadosabertos.ibama.gov.br"))
        doc = prov_model.ProvDocument.deserialize(
            content=json.dumps(record), format="rdf", rdf_format="json-ld")
        types = [r.get_type().localpart for r in doc.get_records()]
        assert types.count("Entity") == 1
        assert types.count("Derivation") == 1

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
        monkeypatch.setattr(main, "CHANGES_FILE", tmp_path / "changes.md")

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
        monkeypatch.setattr(main, "CHANGES_FILE", tmp_path / "changes.md")

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


# ---------------------------------------------------------------------------
# Change details and changes.md (change_summary)
# ---------------------------------------------------------------------------

from change_summary import describe_change  # noqa: E402


class TestChangeSummary:
    def test_host_move_and_packaging_change(self, sample_dataset):
        """A download relocated to another host and unzipped is described as such."""
        after = json.loads(json.dumps(sample_dataset))
        after["metadata_modified"] = "2026-06-02T00:00:00"
        after["resources"][0]["url"] = "https://blob.example.net/dados/embargos.csv"
        before = json.loads(json.dumps(sample_dataset))
        before["resources"][0]["url"] = "https://ibama.gov.br/data/embargos_csv.zip"

        details = describe_change(before, after)
        assert details["resourceUrlChanges"] == 1
        assert details["hostMoves"] == 1
        assert details["packagingChanges"] == 1
        assert "resource.url" in details["changedFields"]
        assert "moved from ibama.gov.br to blob.example.net" in details["summary"]
        assert "zip → plain file" in details["summary"]

    def test_resource_added_and_format_changed(self, sample_dataset):
        after = json.loads(json.dumps(sample_dataset))
        after["resources"][0]["format"] = "XLSX"
        after["resources"].append({"id": "r4", "name": "new.pdf", "format": "PDF"})
        details = describe_change(sample_dataset, after)
        assert "1 resource(s) added" in details["summary"]
        assert "declared format CSV → XLSX" in details["summary"]

    def test_resource_removed_is_not_misreported(self, sample_dataset):
        """Removing a resource must not look like edits to the remaining ones."""
        after = json.loads(json.dumps(sample_dataset))
        del after["resources"][0]
        details = describe_change(sample_dataset, after)
        assert details["summary"] == "1 resource(s) removed"
        assert details["resourceUrlChanges"] == 0

    def test_change_outside_fingerprint(self, sample_dataset):
        """License-only edits are reported as outside the fingerprint."""
        after = {**sample_dataset, "license_title": "Outra (Aberta)"}
        details = describe_change(sample_dataset, after)
        assert details["changedFields"] == []
        assert details["fieldsOutsideFingerprint"] == ["license_title"]
        assert details["summary"] == "License title changed"

    def test_prov_record_carries_details(self, sample_dataset, tmp_path):
        """Details are written to the PROV entity and still load with `prov`."""
        after = json.loads(json.dumps(sample_dataset))
        after["metadata_modified"] = "2026-06-02T00:00:00"
        after["resources"][0]["url"] = "https://blob.example.net/dados/embargos.csv"
        event = ChangeEvent(
            dataset_id="abc123", change_type=ChangeType.CONTENT_MOD,
            current_hash="b" * 64, previous_hash="a" * 64,
            current_timestamp=after["metadata_modified"],
            previous_timestamp=sample_dataset["metadata_modified"],
            portal_url="https://dadosabertos.ibama.gov.br", organization="ibama",
        )
        event.details = describe_change(sample_dataset, after)
        record = ProvMapper(provenance_dir=str(tmp_path / "prov")).generate_record(event)
        entity = record["@graph"][0]
        assert entity["5ltep:hostMoves"] == 1
        assert "resource URL(s) changed" in entity["5ltep:changeSummary"]

        prov_model = pytest.importorskip("prov.model")
        pytest.importorskip("rdflib")
        prov_model.ProvDocument.deserialize(
            content=json.dumps(record), format="rdf", rdf_format="json-ld")

    def test_pipeline_writes_changes_md(self, sample_dataset, tmp_path, monkeypatch):
        """Two cycles with a relocation: PROV details + a changes.md row."""
        snaps = tmp_path / "snapshots"
        prov = tmp_path / "prov"
        snaps.mkdir(parents=True, exist_ok=True)
        prov.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(main, "HASHES_FILE", tmp_path / "hash_store.json")
        monkeypatch.setattr(main, "SNAPSHOTS_DIR", snaps)
        monkeypatch.setattr(main, "MANIFEST_FILE", snaps / "manifest.json")
        monkeypatch.setattr(main, "PROV_DIR", prov)
        monkeypatch.setattr(main, "CHANGES_FILE", tmp_path / "changes.md")

        relocated = json.loads(json.dumps(sample_dataset))
        relocated["metadata_modified"] = "2026-06-02T00:00:00"
        relocated["resources"][0]["url"] = "https://blob.example.net/dados/embargos.csv"
        cycles = iter([[sample_dataset], [relocated]])

        class _FakeHarvester:
            def __init__(self, *args, **kwargs):
                pass

            def harvest_all(self):
                return next(cycles)

        monkeypatch.setattr(main, "CKANHarvester", _FakeHarvester)
        run_ids = iter(["20260601T000000Z", "20260602T000000Z"])

        class _Clock:
            @staticmethod
            def now(tz=None):
                from datetime import datetime as real
                return real.strptime(next(run_ids), "%Y%m%dT%H%M%SZ").replace(tzinfo=tz)

        monkeypatch.setattr(main, "datetime", _Clock)
        main.run_pipeline(portal_url="https://test.gov.br")
        summary = main.run_pipeline(portal_url="https://test.gov.br")
        assert summary["change_events"] == 1

        log = json.loads((prov / "abc123.jsonld").read_text(encoding="utf-8"))
        entity = log["provenance_chain"][-1]["@graph"][0]
        assert entity["5ltep:resourceUrlChanges"] == 1

        changes = (tmp_path / "changes.md").read_text(encoding="utf-8")
        assert "Embargos Ambientais Federais" in changes
        assert "`CONTENT_MOD`" in changes
        assert "moved from ibama.gov.br to blob.example.net" in changes

        data = json.loads((main.DOCS_DATA_DIR / "layer4.json").read_text(encoding="utf-8"))
        event = data["events"][0]  # its type depends on the real detection time; not checked here
        assert "movida(s) de ibama.gov.br para blob.example.net" in event["summary_pt"]
        assert data["relocations"][0]["to"] == "blob.example.net"
        assert data["monitoring"]["cycles"] == 2
        assert data["datasets"][0]["prov_records"] == 1
        badge = json.loads((main.DOCS_DATA_DIR / "status.json").read_text(encoding="utf-8"))
        assert badge["message"].startswith("1 datasets · ") and badge["label"] == "Layer 4"
        assert badge["color"] == "brightgreen"


# ---------------------------------------------------------------------------
# Portal configuration, badges and documentation
# ---------------------------------------------------------------------------

from portal_config import load_portal  # noqa: E402
from dashboard import build_dashboard, status_badges  # noqa: E402


class TestPortalConfig:
    def _file(self, tmp_path):
        path = tmp_path / "portal.json"
        path.write_text(json.dumps({"portal_url": "https://dados.example.gov.br/",
                                    "name": "Example", "title": "Example portal"}),
                        encoding="utf-8")
        return path

    def test_reads_portal_json(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CKAN_PORTAL_URL", raising=False)
        portal = load_portal(path=self._file(tmp_path))
        assert portal == {"portal_url": "https://dados.example.gov.br",
                          "name": "Example", "title": "Example portal"}

    def test_environment_then_explicit_url_take_precedence(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CKAN_PORTAL_URL", "https://env.example.org")
        path = self._file(tmp_path)
        assert load_portal(path=path)["portal_url"] == "https://env.example.org"
        other = load_portal("https://cli.example.org/", path=path)
        assert other == {"portal_url": "https://cli.example.org",
                         "name": "cli.example.org", "title": "cli.example.org"}

    def test_missing_url_is_an_error(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CKAN_PORTAL_URL", raising=False)
        with pytest.raises(ValueError):
            load_portal(path=tmp_path / "absent.json")

    def test_repository_declares_a_portal(self, monkeypatch):
        monkeypatch.delenv("CKAN_PORTAL_URL", raising=False)
        assert load_portal()["portal_url"].startswith("https://")


class TestDashboardHosts:
    def test_hosts_as_recorded_and_resources_without_url(self, sample_dataset, tmp_path):
        """Hosts keep a written port; an empty URL is "" and is listed by dataset and resource."""
        snaps = tmp_path / "snapshots"
        snaps.mkdir()
        ds = json.loads(json.dumps(sample_dataset))
        ds["resources"][1]["url"] = "http://ibama.gov.br:80/data/1.json"
        ds["resources"][2]["url"] = ""
        (snaps / "snapshot_20261002T000000Z.json").write_text(json.dumps([ds]), encoding="utf-8")
        (snaps / "manifest.json").write_text(json.dumps(
            {"runs": {"20261002T000000Z": "h"}, "snapshots": {"h": "snapshot_20261002T000000Z.json"}}),
            encoding="utf-8")
        data = build_dashboard([], snaps, tmp_path / "prov", {"portal_url": "https://x", "name": "x", "title": "x"})
        assert data["hosts_now"] == {"ibama.gov.br": 1, "ibama.gov.br:80": 1, "": 1}
        assert data["urls_without_host"] == [{"dataset": "embargos-ambientais", "title": "Embargos Ambientais Federais",
                                              "resource": "embargos.xml", "format": "XML", "url": "", "host": ""}]


class TestBadges:
    def _data(self, severity="WARNING", when="2026-09-30T00:00:00+00:00"):
        return {"totals": {"datasets": 1234, "prov_events": 5, "critical": int(severity == "CRITICAL")},
                "monitoring": {"last_cycle": "2026-10-01T00:00:00+00:00"},
                "events": [{"severity": severity, "when": when}]}

    def test_layer4_badge_both_languages(self):
        badges = status_badges(self._data())
        assert badges["en"]["message"] == "1,234 datasets · 5 changes · 0 critical"
        assert badges["pt"]["message"] == "1.234 conjuntos · 5 mudanças · 0 críticas"
        assert badges["en"]["schemaVersion"] == 1 and badges["en"]["color"] == "brightgreen"

    def test_recent_critical_turns_badge_red(self):
        assert status_badges(self._data("CRITICAL"))["en"]["color"] == "red"
        old = self._data("CRITICAL", when="2026-06-01T00:00:00+00:00")
        assert status_badges(old)["en"]["color"] == "brightgreen"

    def test_before_first_cycle(self):
        data = {"totals": {"datasets": 0, "prov_events": 0, "critical": 0},
                "monitoring": {"last_cycle": None}, "events": []}
        assert status_badges(data)["pt"]["message"] == "aguardando o primeiro ciclo"

    def test_cross_check_badges(self):
        import cross_check
        ok = cross_check.badges("IN_SYNC", day="2026-10-02")
        assert ok["en"] == {"schemaVersion": 1, "label": "cross-check",
                            "message": "in sync · 2026-10-02", "color": "brightgreen"}
        stale = cross_check.badges("STALE", divergences=3, day="2026-10-02")
        assert stale["pt"]["message"] == "desatualizada: 3 divergência(s) · 2026-10-02"
        assert stale["pt"]["color"] == "orange"
        assert cross_check.badges("ERROR", coverage=0.8)["en"]["message"] == "error: 80% reached"


class TestDocs:
    def test_readme_and_leiame_match(self):
        """README.md and LEIAME.md: same heading structure, code blocks and cross links."""
        import re
        root = os.path.join(os.path.dirname(__file__), "..")
        readme = open(os.path.join(root, "README.md"), encoding="utf-8").read()
        leiame = open(os.path.join(root, "LEIAME.md"), encoding="utf-8").read()

        def outline(text):
            lines, fenced = [], False
            for line in text.splitlines():
                if line.startswith("```"):
                    fenced = not fenced
                    lines.append("```")
                elif not fenced and re.match(r"#{1,6} ", line):
                    lines.append(line.split(" ")[0])
            return lines

        assert outline(readme) == outline(leiame)
        assert "(LEIAME.md)" in readme and "(README.md)" in leiame
        assert "docs%2Fdata%2Fstatus.json" in readme and "docs%2Fdata%2Fstatus.pt.json" in leiame
        assert "CROSS_CHECK_STATUS" not in readme + leiame  # no workflow rewrites the READMEs


class TestCrossCheck:
    def test_package_list_failure_is_recorded_as_error(self, sample_dataset, tmp_path, monkeypatch):
        """A portal that refuses package_list yields an ERROR report and badge, not a crash."""
        import urllib.error
        import cross_check
        snaps = tmp_path / "snapshots"
        snaps.mkdir()
        (snaps / "snapshot_20261002T000000Z.json").write_text(json.dumps([sample_dataset]), encoding="utf-8")
        (snaps / "manifest.json").write_text(json.dumps(
            {"runs": {"20261002T000000Z": "h"}, "snapshots": {"h": "snapshot_20261002T000000Z.json"}}),
            encoding="utf-8")
        docs = tmp_path / "docs_data"
        monkeypatch.setattr(cross_check, "MANIFEST", snaps / "manifest.json")
        monkeypatch.setattr(cross_check, "SNAPSHOTS_DIR", snaps)
        monkeypatch.setattr(cross_check, "REPORT", tmp_path / "report.json")
        monkeypatch.setattr(cross_check, "DOCS_DATA", docs)
        monkeypatch.setattr(cross_check, "PANEL", docs / "cross_check.json")
        monkeypatch.setattr(cross_check, "BADGES", {"en": docs / "b.json", "pt": docs / "b.pt.json"})

        def refuse(url):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, None)

        monkeypatch.setattr(cross_check, "fetch", refuse)
        assert cross_check.main() == 1
        report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
        assert report["status"] == "ERROR" and report["errors"][0]["name"] == "package_list"
        assert json.loads((docs / "b.json").read_text(encoding="utf-8"))["color"] == "red"


class TestPaperClaims:
    """Behaviour stated in the WFA 2026 paper (Pinheiro & Sérgio), kept from regressing."""

    @staticmethod
    def _workflow(name):
        path = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows", name)
        return open(path, encoding="utf-8").read()

    def test_workflows_read_the_repository_variable(self):
        """§3.2: adopters fork, set one repository variable, and both workflows read it."""
        for name in ("monitor.yml", "cross_check.yml"):
            assert "CKAN_PORTAL_URL: ${{ vars.CKAN_PORTAL_URL }}" in self._workflow(name)

    def test_schedules(self):
        """§3.2: monitoring every 6 h; cross-check daily 03:30 UTC; compression Sundays 03:00 UTC."""
        assert "*/6 * * *'" in self._workflow("monitor.yml")
        assert "cron: '30 3 * * *'" in self._workflow("cross_check.yml")
        assert "cron: '0 3 * * 0'" in self._workflow("compress.yml")

    def test_monitor_commits_before_alerting(self):
        """§3.2: six steps, the commit before the conditional alert on CRITICAL events."""
        text = self._workflow("monitor.yml")
        steps = [line.strip() for line in text.splitlines() if line.strip().startswith("- name:")
                 or line.strip().startswith("- uses:")]
        assert len(steps) == 6
        assert text.index("Commit provenance logs") < text.index("Alert on CRITICAL")
        assert "steps.monitor.outputs.critical == 'true'" in text
        # the commit also runs after a failed cycle, to save its cause; the alert step does not
        assert "if: success() || failure()" in text
        assert "python-version: ${{ env.PYTHON_VERSION }}" in text and "PYTHON_VERSION: '3.11'" in text

    def test_sparql_finds_retro_alter(self, sample_dataset, tmp_path):
        """§3.2: the JSON-LD records answer "which datasets had retroactive alterations?" in SPARQL."""
        pytest.importorskip("rdflib")
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evaluation"))
        import sparql_query
        engine = HashEngine(hash_store_path=str(tmp_path / "h.json"), portal_url="https://test.gov.br")
        engine.detect_changes([sample_dataset])
        silent = {**sample_dataset, "notes": "Edited without a new timestamp"}
        events = engine.detect_changes([silent])
        assert events[0].change_type == ChangeType.RETRO_ALTER
        prov = tmp_path / "prov"
        ProvMapper(provenance_dir=str(prov), repository_url="o/r", commit_sha="abc1234").save_records(events)
        graph, records = sparql_query.load_graph(str(prov))
        since = "2000-01-01T00:00:00+00:00"
        rows = list(graph.query(sparql_query.WINDOW_QUERY % (sparql_query.NS_5LTEP, "RETRO_ALTER", since)))
        assert records == 1 and len(rows) == 1 and str(rows[0][0]) == "abc123"


# ---------------------------------------------------------------------------
# Failed cycles: why a cycle failed, recorded for the dashboard
# ---------------------------------------------------------------------------

import requests  # noqa: E402
import cycle_failures  # noqa: E402


def _http_error(code, reason, url="https://portal.gov.br/api/3/action/package_list"):
    response = requests.Response()
    response.status_code, response.reason, response.url = code, reason, url
    kind = "Server" if code >= 500 else "Client"
    return requests.HTTPError(f"{code} {kind} Error: {reason} for url: {url}", response=response)


class TestCycleFailures:
    @pytest.mark.parametrize("exc, category", [
        (_http_error(502, "Bad Gateway"), "portal_down"),
        (_http_error(403, "Forbidden"), "blocked"),
        (_http_error(429, "Too Many Requests"), "blocked"),
        (_http_error(404, "Not Found"), "unexpected"),
        (requests.ReadTimeout("HTTPSConnectionPool(host='p.gov.br', port=443): Read timed out."), "portal_slow"),
        (requests.ConnectTimeout("HTTPSConnectionPool(host='p.gov.br', port=443): ConnectTimeoutError"), "network"),
        (requests.ConnectionError("HTTPSConnectionPool(host='p.gov.br', port=443): Max retries exceeded "
                                  "(Caused by NameResolutionError(...))"), "dns"),
        (requests.ConnectionError("HTTPSConnectionPool(host='p.gov.br', port=443): Connection refused"), "network"),
        (ValueError("CKAN API returned success=false: {'message': 'x'}"), "unexpected"),
        (KeyError("resources"), "toolkit"),
    ])
    def test_classify_exception(self, exc, category):
        assert cycle_failures.classify_exception(exc)[0] == category

    def test_classify_log_uses_the_last_exception(self):
        log = ("2026-10-02T22:11:02.75Z 2026-10-02T22:11:02 [WARNING] ckan_harvester: Attempt 1 failed: "
               "HTTPSConnectionPool(host='p.gov.br', port=443): Read timed out.\n"
               "2026-10-02T22:11:59.71Z requests.exceptions.HTTPError: 502 Server Error: Bad Gateway for url: "
               "https://p.gov.br/api/3/action/package_list\n")
        assert cycle_failures.classify_log(log) == ("portal_down", "HTTP 502 Bad Gateway (/api/3/action/package_list)")
        assert cycle_failures.classify_log("no traceback here")[0] == "unknown"

    def test_failed_cycle_is_recorded_and_still_fails(self, sample_dataset, tmp_path, monkeypatch):
        """The run still fails (as in the paper); its cause is recorded and shown on the dashboard."""
        snaps = tmp_path / "snapshots"
        snaps.mkdir()
        monkeypatch.setattr(main, "SNAPSHOTS_DIR", snaps)
        monkeypatch.setattr(main, "MANIFEST_FILE", snaps / "manifest.json")
        monkeypatch.setattr(main, "HASHES_FILE", tmp_path / "hash_store.json")
        monkeypatch.setattr(main, "PROV_DIR", tmp_path / "prov")
        monkeypatch.setattr(main, "CHANGES_FILE", tmp_path / "changes.md")
        monkeypatch.setenv("GITHUB_RUN_ID", "123")
        monkeypatch.setattr(sys, "argv", ["main.py", "--portal", "https://p.gov.br"])

        class _Down:
            def __init__(self, *args, **kwargs):
                pass

            def harvest_all(self):
                raise _http_error(403, "Forbidden")

        monkeypatch.setattr(main, "CKANHarvester", _Down)
        with pytest.raises(requests.HTTPError):
            main.cli()
        entry = cycle_failures.load(main.FAILURES_FILE)[0]
        assert entry["run_id"] == 123 and entry["category"] == "blocked" and entry["source"] == "cycle"
        data = json.loads((main.DOCS_DATA_DIR / "layer4.json").read_text(encoding="utf-8"))
        assert data["monitoring"]["failures"][0]["category"] == "blocked"
        assert data["monitoring"]["failures_by_category"] == {"blocked": 1}

    def test_sync_from_actions(self, tmp_path, monkeypatch):
        """Runs without a record are classified from the failed step, or from the job log."""
        store = tmp_path / "f.json"
        cycle_failures.record(store, "blocked", "HTTP 403", datetime_utc(), run_id=1)
        runs = {"failure": [{"id": 1, "created_at": "2026-09-01T00:00:00Z"},
                            {"id": 2, "created_at": "2026-09-02T00:00:00Z"},
                            {"id": 3, "created_at": "2026-09-03T00:00:00Z"}],
                "cancelled": [], "timed_out": []}
        jobs = {2: {"id": 20, "steps": [{"name": "Install dependencies", "conclusion": "failure"}]},
                3: {"id": 30, "steps": [{"name": "Run monitoring cycle", "conclusion": "failure"}]}}

        class _R:
            def __init__(self, payload=None, text="", status=200):
                self.payload, self.text, self.status_code, self.ok = payload, text, status, status < 400

            def json(self):
                return self.payload

            def raise_for_status(self):
                pass

        def fake_get(url, params=None, **kwargs):
            if url.endswith("/runs"):
                return _R({"workflow_runs": runs[params["status"]]})
            if url.endswith("/jobs"):
                return _R({"jobs": [jobs[int(url.split("/")[-2])]]})
            return _R(text="Z requests.exceptions.ConnectionError: HTTPSConnectionPool(host='p.gov.br', "
                           "port=443): Max retries exceeded (Caused by NameResolutionError(x))")

        monkeypatch.setattr(cycle_failures.requests, "get", fake_get)
        assert cycle_failures.sync_from_actions(store, "o/r", None) == 2
        by_run = {e["run_id"]: e for e in cycle_failures.load(store)}
        assert by_run[2]["category"] == "setup" and by_run[2]["source"] == "actions"
        assert by_run[3]["category"] == "dns" and by_run[3]["source"] == "log"
        assert cycle_failures.sync_from_actions(store, "o/r", None) == 0      # nothing new the second time


def datetime_utc():
    from datetime import datetime as _dt, timezone as _tz
    return _dt(2026, 9, 1, tzinfo=_tz.utc)
