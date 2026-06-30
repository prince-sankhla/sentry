from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.connectors.world_bank.models import SOURCE_NAME

logger = logging.getLogger(__name__)


class WorldBankDownloaderError(RuntimeError):
    """Raised when the World Bank Procurement Notices API cannot be processed."""


@dataclass
class DownloadStats:
    downloaded_notices: int = 0
    skipped_existing: int = 0
    failed: int = 0
    pages: int = 0
    total_available: int | None = None


class WorldBankProcurementDownloader:
    base_url = "https://search.worldbank.org/api/v2/procnotices"
    detail_url_template = "https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"

    def __init__(
        self,
        output_dir: Path,
        rows: int = 100,
        timeout: float = 30.0,
    ) -> None:
        self.output_dir = output_dir
        self.rows = min(max(rows, 1), 1000)
        self.timeout = httpx.Timeout(timeout)

    def download(self, limit: int = 1000) -> DownloadStats:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stats = DownloadStats()
        offset = self._resume_offset()
        collected = self._downloaded_count()
        started_at = time.monotonic()

        logger.info(
            "Starting %s download: target=%s existing=%s offset=%s output_dir=%s",
            SOURCE_NAME,
            limit,
            collected,
            offset,
            self.output_dir,
        )

        while collected < limit:
            page_started_at = time.monotonic()
            payload = self._fetch_page(offset=offset, rows=min(self.rows, limit - collected))
            notices = payload.get("procnotices")
            if not isinstance(notices, list):
                raise WorldBankDownloaderError("Expected 'procnotices' list in response.")

            stats.pages += 1
            stats.total_available = _parse_int(payload.get("total"))
            if not notices:
                logger.info("No notices returned at offset=%s; stopping.", offset)
                break

            for notice in notices:
                if not isinstance(notice, dict):
                    stats.failed += 1
                    logger.warning("Skipping non-object notice at offset=%s", offset)
                    continue

                notice_id = _notice_id(notice)
                if notice_id is None:
                    stats.failed += 1
                    logger.warning("Skipping notice without id at offset=%s", offset)
                    continue

                output_path = self.output_dir / f"{notice_id}.json"
                if output_path.exists():
                    stats.skipped_existing += 1
                    collected += 1
                    continue

                try:
                    self._save_notice(output_path, notice_id, notice)
                except Exception:
                    stats.failed += 1
                    logger.exception("Failed to save World Bank notice %s; continuing.", notice_id)
                    continue

                stats.downloaded_notices += 1
                collected += 1

            elapsed = max(time.monotonic() - started_at, 0.001)
            remaining = max(limit - collected, 0)
            rate = collected / elapsed
            eta = remaining / rate if rate > 0 else None
            logger.info(
                "Progress page=%s offset=%s downloaded=%s successful=%s failed=%s existing=%s remaining=%s eta=%s page_seconds=%.2f",
                stats.pages,
                offset,
                collected,
                stats.downloaded_notices,
                stats.failed,
                stats.skipped_existing,
                remaining,
                _format_seconds(eta),
                time.monotonic() - page_started_at,
            )

            offset += len(notices)
            if stats.total_available is not None and offset >= stats.total_available:
                break

        logger.info(
            "Finished World Bank download: downloaded=%s skipped_existing=%s failed=%s pages=%s total_available=%s",
            stats.downloaded_notices,
            stats.skipped_existing,
            stats.failed,
            stats.pages,
            stats.total_available,
        )
        return stats

    def _resume_offset(self) -> int:
        return self._downloaded_count()

    def _downloaded_count(self) -> int:
        return sum(1 for _ in self.output_dir.glob("*.json")) if self.output_dir.exists() else 0

    def _save_notice(self, output_path: Path, notice_id: str, notice: dict[str, Any]) -> None:
        envelope = {
            "source_name": SOURCE_NAME,
            "source_record_id": notice_id,
            "source_url": self.detail_url_template.format(notice_id=notice_id),
            "retrieved_at": datetime.now(UTC).isoformat(),
            "data": notice,
        }
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(envelope, file, ensure_ascii=False, indent=2)
            file.write("\n")

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, WorldBankDownloaderError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch_page(self, offset: int, rows: int) -> dict[str, Any]:
        params = {"format": "json", "rows": rows, "os": offset}
        logger.info("Requesting World Bank notices offset=%s rows=%s", offset, rows)
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(self.base_url, params=params)
            response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict):
            raise WorldBankDownloaderError("Expected JSON object from World Bank API.")
        return payload


def _notice_id(notice: dict[str, Any]) -> str | None:
    value = notice.get("id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int):
        return str(value)
    return None


def _parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(int(seconds), 0)
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {remainder}s"
    if minutes:
        return f"{minutes}m {remainder}s"
    return f"{remainder}s"
