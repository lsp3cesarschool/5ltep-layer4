"""
PROV-DM Mapper Module — Layer 4 Core Contribution
===================================================
Generates W3C PROV-DM–compliant JSON-LD provenance records implementing
the 5L-TEP Layer 4 PROV-DM mapping strategy.

Mapping Strategy:
    Entity:   Dataset snapshot → prov:Entity (content-addressable URI via SHA-256)
    Activity: Monitoring run → prov:Activity (ISO-8601 timestamped)
    Agent:    Dual-agent model:
              - prov:SoftwareAgent (toolkit/GitHub Actions runner = observer)
              - Government agency (CKAN organization = data custodian)
    Relations: wasGeneratedBy, used, wasDerivedFrom, wasAttributedTo,
              wasAssociatedWith

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.

References:
    - W3C PROV-DM: https://www.w3.org/TR/prov-dm/
    - W3C PROV-O: https://www.w3.org/TR/prov-o/
    - JSON-LD: https://www.w3.org/TR/json-ld/
    - Pinheiro, L.S. et al. (2026). 5L-TEP: A Five-Layer Trust Engineering
      Pyramid for Open Government Data. SOFTENG 2026.
    - Simmhan et al. (2005). A survey of data provenance. ACM SIGMOD Record.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from src.hash_engine import ChangeEvent
except ImportError:
    from hash_engine import ChangeEvent

logger = logging.getLogger(__name__)

# W3C PROV-DM JSON-LD Context
PROV_CONTEXT = {
    "prov": "http://www.w3.org/ns/prov#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "5ltep": "https://5ltep.example.org/ontology#",
    "ckan": "https://ckan.org/schema#",
}

# Toolkit version for agent identification
TOOLKIT_VERSION = "1.0.0"
TOOLKIT_SCOPE = "Layer 4 — Observability & Provenance"


class ProvMapper:
    """
    W3C PROV-DM Mapper for OGD Quality Events (L4 Core).

    Translates ChangeEvent objects into PROV-DM–compliant JSON-LD records
    following the 5L-TEP Layer 4 PROV-DM mapping strategy:

    - Entity: Dataset snapshot (content-addressable URI via SHA-256 hash fragment).
      Because any change produces a cryptographically distinct identifier,
      PROV-DM's entity immutability requirement is inherently satisfied.
    - Activity: Monitoring run (timestamped workflow execution).
    - Agent: Dual-agent model distinguishing the *observer* (software agent)
      from the *data custodian* (government agency), ensuring accountability
      is correctly attributed (Simmhan et al., 2005).
    """

    def __init__(
        self,
        provenance_dir: str = "provenance_logs",
        repository_url: str = "",
        commit_sha: str = "local",
    ):
        """
        Initialize the PROV-DM Mapper.

        Args:
            provenance_dir: Directory for storing provenance JSON-LD files.
            repository_url: GitHub repository URL for agent identification.
            commit_sha: Git commit SHA of the running workflow.
        """
        self.provenance_dir = Path(provenance_dir)
        self.provenance_dir.mkdir(parents=True, exist_ok=True)
        self.repository_url = repository_url
        self.commit_sha = commit_sha
        self.run_id = f"5ltep:run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        self.run_start = datetime.now(timezone.utc)

    def _build_entity_uri(self, event: ChangeEvent) -> str:
        """
        Build a content-addressable entity URI.

        Format: {portal_url}/dataset/{id}#{sha256_prefix}
        Any change produces a cryptographically distinct
        identifier, satisfying PROV-DM's entity immutability requirement.
        """
        base = event.portal_url.rstrip("/")
        return f"{base}/dataset/{event.dataset_id}#{event.current_hash[:12]}"

    def _build_previous_entity_uri(self, event: ChangeEvent) -> Optional[str]:
        """Build URI for the previous entity version (derivation chains, §3.3.3)."""
        if event.previous_hash is None:
            return None
        base = event.portal_url.rstrip("/")
        return f"{base}/dataset/{event.dataset_id}#{event.previous_hash[:12]}"

    def _build_software_agent_id(self) -> str:
        """Build the software agent (observer) identifier."""
        if self.repository_url:
            return f"{self.repository_url}@{self.commit_sha[:7]}"
        return f"5ltep:toolkit-v{TOOLKIT_VERSION}"

    def _build_custodian_agent_id(self, event: ChangeEvent) -> Optional[str]:
        """
        Build the data custodian agent identifier.

        The originating government agency (from CKAN's
        organization field) is recorded via prov:wasAttributedTo on the entity.
        """
        if event.organization:
            base = event.portal_url.rstrip("/")
            return f"{base}/organization/{event.organization}"
        return None

    def _build_activity(self, event: ChangeEvent) -> dict:
        """
        Build the prov:Activity node for this monitoring run.

        Each monitoring run constitutes a prov:Activity
        with ISO-8601 timestamps, associated with the software agent.
        """
        run_end = datetime.now(timezone.utc)
        activity = {
            "@id": self.run_id,
            "@type": ["prov:Activity", "5ltep:MonitoringRun"],
            "prov:startedAtTime": {
                "@value": self.run_start.isoformat(),
                "@type": "xsd:dateTime",
            },
            "prov:endedAtTime": {
                "@value": run_end.isoformat(),
                "@type": "xsd:dateTime",
            },
            "prov:wasAssociatedWith": {"@id": self._build_software_agent_id()},
        }
        # Record the CKAN API endpoint used by the activity
        api_endpoint = (
            f"{event.portal_url.rstrip('/')}/api/3/action/package_show"
            f"?id={event.dataset_id}"
        )
        activity["prov:used"] = {"@id": api_endpoint}
        return activity

    def _build_software_agent(self) -> dict:
        """Build the prov:SoftwareAgent node (observer role)."""
        return {
            "@id": self._build_software_agent_id(),
            "@type": ["prov:Agent", "prov:SoftwareAgent"],
            "rdfs:label": f"5L-TEP Toolkit v{TOOLKIT_VERSION} ({TOOLKIT_SCOPE})",
            "5ltep:repositoryUrl": self.repository_url or "local",
            "5ltep:commitSha": self.commit_sha,
        }

    def _build_custodian_agent(self, event: ChangeEvent) -> Optional[dict]:
        """
        Build the data custodian agent node.

        The dual-agent model distinguishes the observer
        (software agent) from the data custodian (government agency),
        ensuring accountability is correctly attributed.
        """
        agent_id = self._build_custodian_agent_id(event)
        if agent_id is None:
            return None
        return {
            "@id": agent_id,
            "@type": ["prov:Agent", "5ltep:DataCustodian"],
            "rdfs:label": event.organization,
            "5ltep:portalUrl": event.portal_url,
        }

    def generate_record(self, event: ChangeEvent) -> dict:
        """
        Generate a W3C PROV-DM JSON-LD record for a single change event.

        Implements the full 5L-TEP L4 PROV-DM mapping strategy:
        - Entity with content-addressable URI (§3.3.1)
        - Activity with dual-agent model (§3.3.2)
        - Derivation chain via wasDerivedFrom (§3.3.3)
        - Change type annotation (§3.2)

        Args:
            event: The ChangeEvent to convert to provenance.

        Returns:
            A JSON-LD document conforming to W3C PROV-DM.
        """
        entity_uri = self._build_entity_uri(event)
        previous_uri = self._build_previous_entity_uri(event)

        # Build entity node (§3.3.1 — content-addressable identification)
        entity = {
            "@id": entity_uri,
            "@type": ["prov:Entity", "5ltep:DatasetSnapshot"],
            "prov:wasGeneratedBy": {"@id": self.run_id},
            "5ltep:changeType": event.change_type.value,
            "5ltep:severity": event.severity.value,
            "5ltep:datasetId": event.dataset_id,
            "5ltep:contentHash": event.current_hash,
            "5ltep:detectedAt": {
                "@value": event.detected_at,
                "@type": "xsd:dateTime",
            },
        }

        # Dual-agent attribution (§3.3.2):
        # - wasAttributedTo → data custodian (government agency)
        # - wasGeneratedBy → activity → wasAssociatedWith → software agent
        custodian_id = self._build_custodian_agent_id(event)
        if custodian_id:
            entity["prov:wasAttributedTo"] = {"@id": custodian_id}
        else:
            # Fallback: attribute to software agent if no organization info
            entity["prov:wasAttributedTo"] = {"@id": self._build_software_agent_id()}

        # Derivation chain (§3.3.3): link to predecessor via wasDerivedFrom
        if previous_uri:
            entity["prov:wasDerivedFrom"] = {"@id": previous_uri}

        # Build activity (§3.3.2)
        activity = self._build_activity(event)

        # Compose @graph: entity + activity + agent(s)
        graph = [entity, activity, self._build_software_agent()]
        custodian_agent = self._build_custodian_agent(event)
        if custodian_agent:
            graph.append(custodian_agent)

        # Full JSON-LD document
        record = {
            "@context": PROV_CONTEXT,
            "@graph": graph,
        }

        return record

    def generate_records(self, events: list[ChangeEvent]) -> list[dict]:
        """
        Generate PROV-DM records for a batch of change events.

        Args:
            events: List of ChangeEvent objects.

        Returns:
            List of JSON-LD provenance records.
        """
        records = []
        for event in events:
            record = self.generate_record(event)
            records.append(record)
        logger.info(f"Generated {len(records)} PROV-DM records")
        return records

    def save_records(self, events: list[ChangeEvent]) -> list[str]:
        """
        Generate and persist provenance records (one file per dataset, append-only).

        Provenance records are stored as append-only JSON-LD
        files (one per dataset) in a Git repository. Git's commit hashes
        provide tamper-evidence — a lightweight alternative to blockchain.

        Args:
            events: List of ChangeEvent objects.

        Returns:
            List of file paths where records were saved.
        """
        saved_files = []
        for event in events:
            record = self.generate_record(event)

            # Per-dataset provenance log (append-only)
            safe_id = event.dataset_id.replace("/", "_").replace("\\", "_")
            log_path = self.provenance_dir / f"{safe_id}.jsonld"

            # Load existing log or start new
            if log_path.exists():
                with open(log_path, "r") as f:
                    log = json.load(f)
            else:
                log = {
                    "@context": PROV_CONTEXT,
                    "5ltep:datasetId": event.dataset_id,
                    "5ltep:portalUrl": event.portal_url,
                    "provenance_chain": [],
                }

            # Append new record to chain (immutable append-only)
            log["provenance_chain"].append(record)

            # Write back
            with open(log_path, "w") as f:
                json.dump(log, f, indent=2, ensure_ascii=False)

            saved_files.append(str(log_path))

        logger.info(f"Saved provenance logs for {len(saved_files)} datasets")
        return saved_files

    def get_summary(self, events: list[ChangeEvent]) -> dict:
        """
        Generate a summary of the monitoring run.

        Args:
            events: List of ChangeEvent objects.

        Returns:
            Summary dictionary with counts and statistics.
        """
        from collections import Counter

        type_counts = Counter(e.change_type.value for e in events)
        severity_counts = Counter(e.severity.value for e in events)

        return {
            "run_id": self.run_id,
            "run_start": self.run_start.isoformat(),
            "run_end": datetime.now(timezone.utc).isoformat(),
            "total_datasets": len(events),
            "change_types": dict(type_counts),
            "severity_counts": dict(severity_counts),
            "agent": self._build_software_agent_id(),
            "scope": TOOLKIT_SCOPE,
        }
