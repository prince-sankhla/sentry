"""Government e-Marketplace (GeM) downloader.

GeM does not expose an open public API and its portal (gem.gov.in) enforces
strong bot protection / authenticated sessions, so live ingestion is BLOCKED
pending official data access (API credentials or the published contracts
dataset). This connector is production-ready for whichever JSON contracts/bids
feed GeM makes available: point ``endpoint`` at it and rows flow through the
shared feed downloader with full envelope/provenance/attachment preservation.
"""

from __future__ import annotations

from pathlib import Path

from app.connectors.common.json_feed import JsonFeedDownloader
from app.connectors.gem.mapper import SOURCE_NAME

# Placeholder — replace with the official GeM contracts/bids data endpoint.
DEFAULT_ENDPOINT = "https://gem.gov.in/api/public/contracts"


class GeMDownloader(JsonFeedDownloader):
    def __init__(self, output_dir: Path, endpoint: str = DEFAULT_ENDPOINT, page_size: int = 100, timeout: float = 30.0) -> None:
        super().__init__(
            output_dir,
            source_name=SOURCE_NAME,
            endpoint=endpoint,
            records_keys=("contracts", "results", "data", "items"),
            id_keys=("contract_no", "contract_number", "bid_no", "id"),
            page_size=page_size,
            timeout=timeout,
        )
