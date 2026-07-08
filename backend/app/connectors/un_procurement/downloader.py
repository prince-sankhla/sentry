"""United Nations (UNGM) procurement notice / contract-award downloader.

Wraps the shared JSON feed downloader against the UN Global Marketplace public
data service. UNGM applies bot protection on its HTML search; supply the
official notice/award JSON endpoint via ``endpoint`` (see Remaining work).
"""

from __future__ import annotations

from pathlib import Path

from app.connectors.common.json_feed import JsonFeedDownloader
from app.connectors.un_procurement.mapper import SOURCE_NAME

DEFAULT_ENDPOINT = "https://www.ungm.org/Public/Notice/Search"


class UNProcurementDownloader(JsonFeedDownloader):
    def __init__(self, output_dir: Path, endpoint: str = DEFAULT_ENDPOINT, page_size: int = 100, timeout: float = 30.0) -> None:
        super().__init__(
            output_dir,
            source_name=SOURCE_NAME,
            endpoint=endpoint,
            records_keys=("notices", "results", "data", "items"),
            id_keys=("reference", "noticeId", "notice_id", "id"),
            page_size=page_size,
            timeout=timeout,
        )
