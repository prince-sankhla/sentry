"""data.gov.in CKAN resource downloader.

Official open-government API. Each configured resource id is a procurement
dataset; records are paginated via ``offset``/``limit`` and one envelope is
written per row. Requires a (free) data.gov.in API key.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Iterable

from app.connectors.common.http import BaseHttpDownloader, DownloadStats
from app.connectors.common.parse import is_url, optional_string
from app.connectors.datagovin.mapper import SOURCE_NAME

logger = logging.getLogger(__name__)


class DataGovInDownloader(BaseHttpDownloader):
    source_name = SOURCE_NAME
    api_base = "https://api.data.gov.in/resource"

    def __init__(
        self,
        output_dir: Path,
        resource_ids: Iterable[str],
        api_key: str | None = None,
        page_size: int = 100,
        timeout: float = 30.0,
    ) -> None:
        super().__init__(output_dir, timeout=timeout)
        self.resource_ids = [rid for rid in resource_ids if rid]
        self.api_key = api_key or os.environ.get("DATA_GOV_IN_API_KEY", "")
        self.page_size = min(max(page_size, 1), 1000)

    def download(self, limit: int = 1000) -> DownloadStats:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stats = DownloadStats()
        if not self.api_key:
            logger.warning("DATA_GOV_IN_API_KEY missing; skipping data.gov.in download.")
            return self.finalize(stats)

        with self.client() as client:
            for resource_id in self.resource_ids:
                self._download_resource(client, resource_id, limit, stats)
        return self.finalize(stats)

    def _download_resource(self, client, resource_id: str, limit: int, stats: DownloadStats) -> None:
        url = f"{self.api_base}/{resource_id}"
        offset = 0
        collected = 0
        while collected < limit:
            params = {
                "api-key": self.api_key,
                "format": "json",
                "offset": offset,
                "limit": min(self.page_size, limit - collected),
            }
            payload = self.get_json(client, url, params=params, conditional=True)
            if payload is None:
                break
            records = payload.get("records") if isinstance(payload, dict) else None
            if not isinstance(records, list) or not records:
                break
            stats.pages += 1
            stats.total_available = _as_int(payload.get("total")) if isinstance(payload, dict) else None
            for index, record in enumerate(records):
                if not isinstance(record, dict):
                    stats.failed += 1
                    continue
                record_id = f"{resource_id}:{_row_id(record) or offset + index}"
                source_url = _row_source_url(record) or f"https://data.gov.in/resource/{resource_id}"
                outcome = self.save_record(
                    record_id=record_id,
                    source_url=source_url,
                    data=record,
                    documents=_row_documents(record),
                )
                _tally(stats, outcome)
                collected += 1
            offset += len(records)
            if stats.total_available is not None and offset >= stats.total_available:
                break


def _row_id(record: dict[str, Any]) -> str | None:
    for key in ("id", "s_no", "sno", "tender_id", "reference_no"):
        value = optional_string(record.get(key))
        if value:
            return value
    return None


def _row_source_url(record: dict[str, Any]) -> str | None:
    for key, value in record.items():
        if "url" in str(key).lower() and is_url(value):
            return str(value).strip()
    return None


def _row_documents(record: dict[str, Any]) -> list[dict[str, str]]:
    documents = []
    for key, value in record.items():
        if is_url(value):
            documents.append({"title": str(key), "url": str(value).strip(), "document_type": "attachment"})
    return documents


def _tally(stats: DownloadStats, outcome: str) -> None:
    if outcome == "downloaded":
        stats.downloaded += 1
    elif outcome == "unchanged":
        stats.unchanged += 1
    else:
        stats.skipped_existing += 1


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
