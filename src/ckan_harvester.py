"""
CKAN Harvester Module — Portal Metadata Ingestion
===================================================
Polls the CKAN API to retrieve dataset metadata snapshots using
exponential backoff retry logic and per-resource enumeration.

Part of the 5L-TEP Layer 4 (Observability & Provenance) Toolkit.

As described in the KDMiLe 2026 paper (Section 3.1):
    "The CKAN Harvester polls package_list and package_show endpoints
    using exponential backoff retry logic and per-resource enumeration."

References:
    - CKAN API Guide: https://docs.ckan.org/en/latest/api/
    - Pinheiro & Sérgio (2026). 5L-TEP. SOFTENG 2026.
"""

import time
import logging
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)

# Default timeout and retry configuration
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds (exponential backoff base)


class CKANHarvester:
    """
    Client for harvesting dataset metadata from CKAN-based OGD portals.

    Implements the input stage of the L4 pipeline: retrieves dataset metadata
    via CKAN's REST API (package_list + package_show) with exponential backoff
    retry logic for resilience against transient network failures.
    """

    def __init__(self, portal_url: str, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the CKAN harvester.

        Args:
            portal_url: Base URL of the CKAN portal
                        (e.g., https://dadosabertos.ibama.gov.br)
            timeout: Request timeout in seconds.
        """
        self.portal_url = portal_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "5LTEP-Layer4/1.0 (L4 Provenance Monitor)"
        })

    def _api_url(self, action: str) -> str:
        """Build full API URL for a CKAN action."""
        return urljoin(self.portal_url + "/", f"api/3/action/{action}")

    def _request_with_retry(self, url: str, params: Optional[dict] = None) -> dict:
        """
        Make a GET request with exponential backoff retry.

        Implements the retry strategy described in the paper:
        up to MAX_RETRIES attempts with exponential wait between failures.

        Args:
            url: The URL to request.
            params: Optional query parameters.

        Returns:
            Parsed JSON response (result field).

        Raises:
            requests.HTTPError: If all retries fail.
        """
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("success"):
                    return data["result"]
                raise ValueError(f"CKAN API returned success=false: {data.get('error')}")
            except (requests.RequestException, ValueError) as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {wait}s..."
                    )
                    time.sleep(wait)
        raise last_error

    def list_datasets(self) -> list[str]:
        """
        Retrieve the list of all dataset identifiers from the portal.

        Calls CKAN's package_list endpoint.

        Returns:
            List of dataset ID strings.
        """
        url = self._api_url("package_list")
        logger.info(f"Listing datasets from {url}")
        result = self._request_with_retry(url)
        logger.info(f"Found {len(result)} datasets")
        return result

    def get_dataset_metadata(self, dataset_id: str) -> dict:
        """
        Retrieve full metadata for a single dataset.

        Calls CKAN's package_show endpoint with per-resource enumeration.

        Args:
            dataset_id: The CKAN dataset identifier.

        Returns:
            Dictionary with full dataset metadata including resources.
        """
        url = self._api_url("package_show")
        return self._request_with_retry(url, params={"id": dataset_id})

    def harvest_all(self) -> list[dict]:
        """
        Harvest metadata for all datasets in the portal.

        Iterates through all datasets returned by package_list and
        retrieves full metadata for each via package_show.

        Returns:
            List of dataset metadata dictionaries.
        """
        dataset_ids = self.list_datasets()
        datasets = []
        for i, dataset_id in enumerate(dataset_ids):
            try:
                metadata = self.get_dataset_metadata(dataset_id)
                datasets.append(metadata)
                if (i + 1) % 10 == 0:
                    logger.info(f"Harvested {i + 1}/{len(dataset_ids)} datasets")
            except Exception as e:
                logger.error(f"Failed to harvest '{dataset_id}': {e}")
                datasets.append({"id": dataset_id, "_error": str(e)})
        logger.info(f"Harvest complete: {len(datasets)} datasets processed")
        return datasets
