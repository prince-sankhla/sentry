"""Reusable paginated-JSON feed downloader for list-style procurement APIs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Sequence

from app.connectors.common.http import BaseHttpDownloader, DownloadStats
from app.connectors.common.parse import is_url, optional_string

logger = logging.getLogger(__name__)


class JsonFeedDownloader(BaseHttpDownloader):
    """Generic downloader: page a JSON endpoint and persist one envelope per row.

    Subclasses/instances supply how to build page params, locate the record
    list inside the response, and derive a stable id + source url per record.
    """

    def __init__(
        self,
        output_dir: Path,
        source_name: str,
        endpoint: str,
        *,
        records_keys: Sequence[str] = ("results", "records", "data", "items", "notices"),
        id_keys: Sequence[str] = ("id", "reference", "reference_no", "notice_id", "tender_id"),
        page_size: int = 100,
        timeout: float = 30.0,
        page_param: str = "offset",
        size_param: str = "limit",
        extra_params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(output_dir, timeout=timeout)
        self._source_name = source_name
        self.endpoint = endpoint
        self.records_keys = records_keys
        self.id_keys = id_keys
        self.page_size = min(max(page_size, 1), 1000)
        self.page_param = page_param
        self.size_param = size_param
        self.extra_params = extra_params or {}

    @property
    def source_name(self) -> str:  # type: ignore[override]
        return self._source_name

    @source_name.setter
    def source_name(self, value: str) -> None:
        self._source_name = value

    def download(self, limit: int = 1000) -> DownloadStats:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stats = DownloadStats()
        offset = 0
        collected = 0
        with self.client() as client:
            while collected < limit:
                params = {
                    self.page_param: offset,
                    self.size_param: min(self.page_size, limit - collected),
                    **self.extra_params,
                }
                try:
                    payload = self.get_json(client, self.endpoint, params=params, conditional=True)
                except Exception:
                    stats.failed += 1
                    logger.exception("%s feed page failed at offset=%s", self.source_name, offset)
                    break
                if payload is None:
                    break
                records = self._records(payload)
                if not records:
                    break
                stats.pages += 1
                for index, record in enumerate(records):
                    if not isinstance(record, dict):
                        stats.failed += 1
                        continue
                    record_id = self._record_id(record) or f"{offset + index}"
                    outcome = self.save_record(
                        record_id=record_id,
                        source_url=self._source_url(record),
                        data=record,
                        documents=self._documents(record),
                    )
                    if outcome == "downloaded":
                        stats.downloaded += 1
                    elif outcome == "unchanged":
                        stats.unchanged += 1
                    else:
                        stats.skipped_existing += 1
                    collected += 1
                offset += len(records)
        return self.finalize(stats)

    def _records(self, payload: Any) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in self.records_keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return value
        return []

    def _record_id(self, record: dict[str, Any]) -> str | None:
        for key in self.id_keys:
            value = optional_string(record.get(key))
            if value:
                return value
        return None

    def _source_url(self, record: dict[str, Any]) -> str | None:
        for key, value in record.items():
            if "url" in str(key).lower() and is_url(value):
                return str(value).strip()
        return None

    def _documents(self, record: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"title": str(key), "url": str(value).strip(), "document_type": "attachment"}
            for key, value in record.items()
            if is_url(value)
        ]
