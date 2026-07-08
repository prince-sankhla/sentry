"""Asian Development Bank procurement/contract-award downloader.

Thin wrapper over the shared JSON feed downloader. The default endpoint targets
ADB's contract-awards data service; override ``endpoint`` for the specific ADB
dataset being ingested (see Remaining work: confirm the live ADB feed URL).
"""

from __future__ import annotations

from pathlib import Path

from app.connectors.adb.mapper import SOURCE_NAME
from app.connectors.common.json_feed import JsonFeedDownloader

DEFAULT_ENDPOINT = "https://www.adb.org/rest/procurement/contract-awards"


class ADBDownloader(JsonFeedDownloader):
    def __init__(self, output_dir: Path, endpoint: str = DEFAULT_ENDPOINT, page_size: int = 100, timeout: float = 30.0) -> None:
        super().__init__(
            output_dir,
            source_name=SOURCE_NAME,
            endpoint=endpoint,
            id_keys=("contract_number", "csrn", "reference", "notice_id", "id"),
            page_size=page_size,
            timeout=timeout,
        )
