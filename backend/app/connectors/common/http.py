"""Reusable HTTP downloader with resume, dedup and conditional requests.

Every connector downloader subclasses :class:`BaseHttpDownloader` so it gets,
for free: tenacity retry, resume-after-interruption (via existing files),
duplicate detection (by ``source_record_id``), and scalable "don't re-download
unchanged records" using content hashes plus ETag / Last-Modified caching.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
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

from app.connectors.common.envelope import build_envelope, content_hash, write_envelope
from app.connectors.common.parse import now_utc

logger = logging.getLogger(__name__)


class DownloaderError(RuntimeError):
    """Raised when a source endpoint returns an unusable response."""


@dataclass
class DownloadStats:
    downloaded: int = 0
    skipped_existing: int = 0
    unchanged: int = 0
    failed: int = 0
    pages: int = 0
    total_available: int | None = None


class ConditionalCache:
    """Persist ETag / Last-Modified per URL so repeat runs can send 304s."""

    filename = ".http_cache.json"

    def __init__(self, directory: Path) -> None:
        self.path = directory / self.filename
        self._entries: dict[str, dict[str, str]] = self._load()

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            logger.warning("Unreadable HTTP cache at %s; starting fresh.", self.path)
            return {}

    def headers_for(self, url: str) -> dict[str, str]:
        entry = self._entries.get(url) or {}
        headers: dict[str, str] = {}
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]
        return headers

    def update(self, url: str, response: httpx.Response) -> None:
        etag = response.headers.get("ETag")
        last_modified = response.headers.get("Last-Modified")
        if not etag and not last_modified:
            return
        self._entries[url] = {"etag": etag or "", "last_modified": last_modified or ""}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self._entries, file, ensure_ascii=False, indent=2)


class BaseHttpDownloader:
    source_name: str = "base"
    user_agent = "SENTRY-Procurement-Ingest/1.0 (+https://sentry.local)"

    def __init__(self, output_dir: Path, timeout: float = 30.0) -> None:
        self.output_dir = output_dir
        self.timeout = httpx.Timeout(timeout)
        self.cache = ConditionalCache(output_dir)

    # -- resume / dedup ----------------------------------------------------
    def existing_record_ids(self) -> set[str]:
        record_ids: set[str] = set()
        if not self.output_dir.exists():
            return record_ids
        for path in self.output_dir.glob("*.json"):
            try:
                with path.open("r", encoding="utf-8") as file:
                    payload = json.load(file)
            except Exception:
                continue
            value = payload.get("source_record_id") if isinstance(payload, dict) else None
            if isinstance(value, str) and value:
                record_ids.add(value)
        return record_ids

    def downloaded_count(self) -> int:
        return sum(1 for _ in self.output_dir.glob("*.json")) if self.output_dir.exists() else 0

    def record_path(self, record_id: str) -> Path:
        return self.output_dir / f"{safe_filename(record_id)}.json"

    def stored_hash(self, path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except Exception:
            return None
        value = payload.get("content_hash") if isinstance(payload, dict) else None
        return value if isinstance(value, str) else None

    def save_record(
        self,
        *,
        record_id: str,
        source_url: str | None,
        data: Any,
        documents: list[dict[str, Any]] | None = None,
        content_type: str | None = None,
        retrieved_at: datetime | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> str:
        """Write an envelope. Returns 'downloaded', 'unchanged' or 'skipped'.

        Unchanged records (same content hash as the copy on disk) are skipped
        so re-runs never rewrite or re-import identical tenders.
        """
        path = self.record_path(record_id)
        new_hash = content_hash(data)
        if path.exists() and self.stored_hash(path) == new_hash:
            return "unchanged"
        envelope = build_envelope(
            source_name=self.source_name,
            source_record_id=record_id,
            source_url=source_url,
            data=data,
            documents=documents,
            retrieved_at=retrieved_at or now_utc(),
            content_type=content_type,
            etag=etag,
            last_modified=last_modified,
        )
        write_envelope(path, envelope)
        return "downloaded"

    # -- HTTP --------------------------------------------------------------
    def _headers(self, conditional_url: str | None) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        if conditional_url:
            headers.update(self.cache.headers_for(conditional_url))
        return headers

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, DownloaderError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def request(
        self,
        client: httpx.Client,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: Any = None,
        conditional: bool = False,
    ) -> httpx.Response:
        response = client.request(
            method,
            url,
            params=params,
            content=data,
            headers=self._headers(url if conditional else None),
        )
        if response.status_code == 304:
            return response
        response.raise_for_status()
        if conditional:
            self.cache.update(url, response)
        return response

    def get_json(
        self, client: httpx.Client, url: str, params: dict[str, Any] | None = None, conditional: bool = False
    ) -> Any:
        response = self.request(client, "GET", url, params=params, conditional=conditional)
        if response.status_code == 304:
            return None
        try:
            return response.json()
        except Exception as error:  # noqa: BLE001
            raise DownloaderError(f"Expected JSON from {url}") from error

    def get_text(
        self, client: httpx.Client, url: str, params: dict[str, Any] | None = None, conditional: bool = False
    ) -> str | None:
        response = self.request(client, "GET", url, params=params, conditional=conditional)
        if response.status_code == 304:
            return None
        return response.text

    def client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout, follow_redirects=True, headers={"User-Agent": self.user_agent})

    def finalize(self, stats: DownloadStats) -> DownloadStats:
        self.cache.save()
        logger.info(
            "%s download finished: downloaded=%s unchanged=%s skipped_existing=%s failed=%s pages=%s total=%s",
            self.source_name,
            stats.downloaded,
            stats.unchanged,
            stats.skipped_existing,
            stats.failed,
            stats.pages,
            stats.total_available,
        )
        return stats


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[:150]
    return cleaned or content_hash(value)[:24]
