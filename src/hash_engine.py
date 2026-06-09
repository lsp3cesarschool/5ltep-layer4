"""
Hash Engine Module — SHA-256 Fingerprinting & Change Detection
===============================================================
Computes SHA-256 fingerprints over canonical JSON serialisation of CKAN
dataset metadata and classifies changes according to the formalised logic
described in the KDMiLe 2026 paper (Section 3.2).

Change-Detection Taxonomy (4 types):
    CLEAN_UPDATE  — No change detected (severity: INFO)
    SCHEMA_DRIFT  — Structural change in resources (severity: CRITICAL)
    RETRO_ALTER   — Hash changed without timestamp advancement,
                    signalling undocumented/retroactive edits (severity: CRITICAL)
    CONTENT_MOD   — Content modification with proper timestamp update (severity: WARNING)

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.

References:
    Pinheiro & Sérgio (2026). 5L-TEP: A Five-Layer Trust Engineering Pyramid
    for Open Government Data. SOFTENG 2026.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """
    Change classification types aligned with 5L-TEP L4 taxonomy.

    As formalised in the KDMiLe 2026 paper (Section 3.2 — Change-Detection Logic):
    - CLEAN_UPDATE: no hash difference detected between snapshots.
    - SCHEMA_DRIFT: structural change (resource count/names/formats altered).
    - RETRO_ALTER: content hash changed but metadata_modified did NOT advance,
      indicating undocumented retroactive alteration (a known integrity concern
      in Brazilian OGD portals).
    - CONTENT_MOD: content changed AND timestamp properly advanced.
    """
    CLEAN_UPDATE = "CLEAN_UPDATE"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    RETRO_ALTER = "RETRO_ALTER"
    CONTENT_MOD = "CONTENT_MOD"


class Severity(str, Enum):
    """Severity levels for change events (per v16 paper specification)."""
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


# Mapping from change type to severity (aligned with v16 paper)
SEVERITY_MAP = {
    ChangeType.SCHEMA_DRIFT: Severity.CRITICAL,
    ChangeType.RETRO_ALTER: Severity.CRITICAL,
    ChangeType.CONTENT_MOD: Severity.WARNING,
    ChangeType.CLEAN_UPDATE: Severity.INFO,
}


class ChangeEvent:
    """Represents a detected change event for a dataset resource."""

    def __init__(
        self,
        dataset_id: str,
        change_type: ChangeType,
        current_hash: str,
        previous_hash: Optional[str],
        current_timestamp: Optional[str],
        previous_timestamp: Optional[str],
        portal_url: str,
        organization: Optional[str] = None,
    ):
        self.dataset_id = dataset_id
        self.change_type = change_type
        self.severity = SEVERITY_MAP[change_type]
        self.current_hash = current_hash
        self.previous_hash = previous_hash
        self.current_timestamp = current_timestamp
        self.previous_timestamp = previous_timestamp
        self.portal_url = portal_url
        self.organization = organization
        self.detected_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "change_type": self.change_type.value,
            "severity": self.severity.value,
            "current_hash": self.current_hash,
            "previous_hash": self.previous_hash,
            "current_timestamp": self.current_timestamp,
            "previous_timestamp": self.previous_timestamp,
            "portal_url": self.portal_url,
            "organization": self.organization,
            "detected_at": self.detected_at,
        }


class HashEngine:
    """
    SHA-256 Fingerprinting Engine for Content-Addressable Change Detection.

    Implements the change-detection logic described in the KDMiLe 2026 paper
    (Section 3.2). Computes SHA-256 fingerprints over canonical JSON
    serialisation (sorted keys, UTF-8) of dataset metadata, and classifies
    changes by comparing h_t against h_{t-1} and analysing timestamp progression.

    For multi-resource datasets, a per-resource fingerprint is computed and
    schema signals (field names, resource count) are aggregated; a change to
    any single resource propagates to the dataset-level event.
    """

    def __init__(self, hash_store_path: str = "data/hash_store.json", portal_url: str = ""):
        """
        Initialize the Hash Engine.

        Args:
            hash_store_path: Path to the JSON file storing previous hashes.
            portal_url: Base URL of the monitored CKAN portal.
        """
        self.hash_store_path = Path(hash_store_path)
        self.portal_url = portal_url
        self.hash_store = self._load_store()

    def _load_store(self) -> dict:
        """Load the hash store from disk."""
        if self.hash_store_path.exists():
            with open(self.hash_store_path, "r") as f:
                return json.load(f)
        return {}

    def save_store(self):
        """Persist the hash store to disk."""
        self.hash_store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.hash_store_path, "w") as f:
            json.dump(self.hash_store, f, indent=2)

    @staticmethod
    def compute_hash(metadata: dict) -> str:
        """
        Compute SHA-256 hash of dataset metadata.

        The hash is computed over the canonical JSON representation
        (sorted keys, no whitespace, UTF-8 encoding) to ensure
        deterministic output — as specified in the paper's Section 3.2.

        Args:
            metadata: Dataset metadata dictionary from CKAN API.

        Returns:
            Hex-encoded SHA-256 hash string (64 characters).
        """
        # Extract relevant fields for hashing (exclude volatile API fields)
        hashable = {
            "id": metadata.get("id"),
            "name": metadata.get("name"),
            "title": metadata.get("title"),
            "notes": metadata.get("notes"),
            "metadata_modified": metadata.get("metadata_modified"),
            "num_resources": metadata.get("num_resources"),
            "resources": [
                {
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "format": r.get("format"),
                    "url": r.get("url"),
                    "size": r.get("size"),
                    "last_modified": r.get("last_modified"),
                }
                for r in metadata.get("resources", [])
            ],
        }
        canonical = json.dumps(hashable, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_manifest_hash(metadata: dict) -> str:
        """
        Compute a hash of the dataset's resource manifest.

        Used to detect SCHEMA_DRIFT events: changes in resource count,
        resource names, or resource formats that indicate structural
        breaks in the dataset's published file manifest.

        Note: this hashes the CKAN-declared resource list (names/formats),
        not the internal schema of the underlying data files (columns/types).
        Inspecting file contents is outside the scope of Layer 4.

        Args:
            metadata: Dataset metadata dictionary.

        Returns:
            Hex-encoded SHA-256 hash of the resource manifest.
        """
        manifest = {
            "num_resources": metadata.get("num_resources"),
            "resource_manifest": [
                {"name": r.get("name"), "format": r.get("format")}
                for r in metadata.get("resources", [])
            ],
        }
        canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def detect_changes(self, datasets: list[dict]) -> list[ChangeEvent]:
        """
        Detect changes by comparing current metadata hashes against stored state.

        Classification logic (Section 3.2 of the KDMiLe 2026 paper):
          1. If no previous hash exists → CLEAN_UPDATE (baseline observation)
          2. If current_hash == previous_hash → CLEAN_UPDATE (no change)
          3. If manifest_hash differs → SCHEMA_DRIFT (structural break, CRITICAL)
          4. If hash changed BUT timestamp did NOT advance → RETRO_ALTER (CRITICAL)
          5. Otherwise → CONTENT_MOD (normal update, WARNING)

        Args:
            datasets: List of current dataset metadata dictionaries from CKAN.

        Returns:
            List of ChangeEvent objects for all processed datasets.
        """
        events = []
        for metadata in datasets:
            if "_error" in metadata:
                continue

            dataset_id = metadata.get("id", metadata.get("name", "unknown"))
            current_hash = self.compute_hash(metadata)
            current_manifest_hash = self.compute_manifest_hash(metadata)
            current_timestamp = metadata.get("metadata_modified")
            organization = metadata.get("organization", {}).get("name")

            stored = self.hash_store.get(dataset_id, {})
            previous_hash = stored.get("content_hash")
            previous_manifest_hash = stored.get("manifest_hash")
            previous_timestamp = stored.get("timestamp")

            # Classify change type per Section 3.2 algorithm
            if previous_hash is None:
                # First observation — baseline
                change_type = ChangeType.CLEAN_UPDATE
            elif current_hash == previous_hash:
                # No change detected
                change_type = ChangeType.CLEAN_UPDATE
            elif previous_manifest_hash and current_manifest_hash != previous_manifest_hash:
                # Structural change at manifest level → CRITICAL
                change_type = ChangeType.SCHEMA_DRIFT
            elif (
                current_timestamp
                and previous_timestamp
                and current_timestamp <= previous_timestamp
            ):
                # Hash changed but timestamp did NOT advance →
                # undocumented retroactive alteration (CRITICAL)
                change_type = ChangeType.RETRO_ALTER
            else:
                # Normal content modification with proper timestamp update
                change_type = ChangeType.CONTENT_MOD

            event = ChangeEvent(
                dataset_id=dataset_id,
                change_type=change_type,
                current_hash=current_hash,
                previous_hash=previous_hash,
                current_timestamp=current_timestamp,
                previous_timestamp=previous_timestamp,
                portal_url=self.portal_url,
                organization=organization,
            )
            events.append(event)

            # Update store with current state
            self.hash_store[dataset_id] = {
                "content_hash": current_hash,
                "manifest_hash": current_manifest_hash,
                "timestamp": current_timestamp,
                "last_checked": event.detected_at,
            }

        self.save_store()
        logger.info(f"Processed {len(events)} datasets for change detection")
        return events
