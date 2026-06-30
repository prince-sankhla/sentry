from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin

import httpx
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

SOURCE_NAME = "cppp"

logger = logging.getLogger(__name__)


class CPPPDownloaderError(RuntimeError):
    """Raised when CPPP public pages cannot be processed."""


@dataclass
class CPPPDownloadStats:
    downloaded: int = 0
    skipped_existing: int = 0
    failed: int = 0
    list_pages: int = 0


class CPPPDownloader:
    base_url = "https://eprocure.gov.in"
    list_url = "https://eprocure.gov.in/eprocure/app?page=FrontEndListTendersbyDate&service=page"

    def __init__(self, output_dir: Path, timeout: float = 30.0, max_list_pages: int = 20) -> None:
        self.output_dir = output_dir
        self.timeout = httpx.Timeout(timeout)
        self.max_list_pages = max_list_pages

    def download(self, limit: int = 100) -> CPPPDownloadStats:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stats = CPPPDownloadStats()
        downloaded_or_existing = self._downloaded_count()
        seen_record_ids = self._existing_record_ids()
        seen_list_fingerprints: set[str] = set()

        logger.info(
            "Starting CPPP download: target=%s existing=%s output_dir=%s",
            limit,
            downloaded_or_existing,
            self.output_dir,
        )

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            list_pages: list[tuple[str, str, list[tuple[str, str]] | None]] = [
                ("closing-date", self.list_url, None)
            ]

            while list_pages and downloaded_or_existing < limit and stats.list_pages < self.max_list_pages:
                page_label, page_url, post_data = list_pages.pop(0)
                try:
                    list_html = self._fetch_list_page(client, page_url, post_data)
                except Exception:
                    stats.failed += 1
                    logger.exception("Failed to fetch CPPP list page %s", page_label)
                    continue

                detail_links = _extract_detail_links(list_html, self.base_url)
                fingerprint = _fingerprint(detail_links)
                if fingerprint in seen_list_fingerprints:
                    logger.info("Skipping repeated CPPP list page %s", page_label)
                    continue
                seen_list_fingerprints.add(fingerprint)
                stats.list_pages += 1

                logger.info("Processing CPPP list page %s with %s detail links", page_label, len(detail_links))
                for detail_url in detail_links:
                    if downloaded_or_existing >= limit:
                        break
                    try:
                        detail_html = self._fetch_detail_page(client, detail_url)
                        record_id = _extract_tender_id(detail_html) or _hash_id(detail_url)
                        output_path = self.output_dir / f"{_safe_filename(record_id)}.json"
                        if record_id in seen_record_ids or output_path.exists():
                            stats.skipped_existing += 1
                            continue
                        self._save_record(output_path, record_id, detail_url, detail_html)
                        seen_record_ids.add(record_id)
                        downloaded_or_existing += 1
                        stats.downloaded += 1
                    except Exception:
                        stats.failed += 1
                        logger.exception("Failed to download CPPP detail page %s", detail_url)

                for submit_name in _extract_submit_names(list_html):
                    form_data = _extract_form_data(list_html, "ListTendersbyDate")
                    if not form_data:
                        continue
                    next_data = [(key, submit_name if key == "submitname" else value) for key, value in form_data]
                    list_pages.append((submit_name, "https://eprocure.gov.in/eprocure/app", next_data))

        logger.info(
            "Finished CPPP download: downloaded=%s skipped_existing=%s failed=%s list_pages=%s",
            stats.downloaded,
            stats.skipped_existing,
            stats.failed,
            stats.list_pages,
        )
        return stats

    def _downloaded_count(self) -> int:
        return sum(1 for _ in self.output_dir.glob("*.json")) if self.output_dir.exists() else 0

    def _existing_record_ids(self) -> set[str]:
        record_ids: set[str] = set()
        for path in self.output_dir.glob("*.json") if self.output_dir.exists() else []:
            try:
                with path.open("r", encoding="utf-8") as file:
                    payload = json.load(file)
            except Exception:
                continue
            value = payload.get("source_record_id") if isinstance(payload, dict) else None
            if isinstance(value, str) and value:
                record_ids.add(value)
        return record_ids

    def _save_record(self, output_path: Path, record_id: str, source_url: str, detail_html: str) -> None:
        envelope = {
            "source_name": SOURCE_NAME,
            "source_record_id": record_id,
            "source_url": source_url,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "content_type": "text/html",
            "data": {
                "detail_html": detail_html,
            },
        }
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(envelope, file, ensure_ascii=False, indent=2)
            file.write("\n")

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, CPPPDownloaderError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch_list_page(
        self,
        client: httpx.Client,
        url: str,
        post_data: list[tuple[str, str]] | None,
    ) -> str:
        logger.info("Requesting CPPP list page %s", url)
        if post_data is not None:
            response = client.post(
                url,
                content=urlencode(post_data).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        else:
            response = client.get(url)
        response.raise_for_status()
        if "Stale Session" in response.text:
            raise CPPPDownloaderError("CPPP session expired while fetching list page.")
        return response.text

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, CPPPDownloaderError)),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        stop=stop_after_attempt(4),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch_detail_page(self, client: httpx.Client, detail_url: str) -> str:
        logger.info("Requesting CPPP detail page %s", detail_url)
        response = client.get(detail_url)
        response.raise_for_status()
        if "Stale Session" in response.text:
            raise CPPPDownloaderError("CPPP session expired while fetching detail page.")
        if "Tender Details" not in response.text:
            raise CPPPDownloaderError("CPPP detail page did not contain tender details.")
        return response.text


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self.hrefs.append(html.unescape(href))


class _FormInputParser(HTMLParser):
    def __init__(self, form_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.form_id = form_id
        self.in_form = False
        self.inputs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag.lower() == "form" and attrs_dict.get("id") == self.form_id:
            self.in_form = True
            return
        if self.in_form and tag.lower() == "input":
            name = attrs_dict.get("name")
            if name:
                self.inputs.append((html.unescape(name), html.unescape(attrs_dict.get("value") or "")))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self.in_form:
            self.in_form = False


def _extract_detail_links(page_html: str, base_url: str) -> list[str]:
    parser = _LinkParser()
    parser.feed(page_html)
    links: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        if "component=%24DirectLink" not in href or "page=FrontEndListTendersbyDate" not in href:
            continue
        url = urljoin(base_url, href)
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


def _extract_submit_names(page_html: str) -> list[str]:
    names = re.findall(r"tapestry\.form\.submit\('ListTendersbyDate',\s*'([^']+)'\)", page_html)
    ignored = {"tabByClosingToday"}
    deduped: list[str] = []
    for name in names:
        if name in ignored or name in deduped:
            continue
        deduped.append(name)
    return deduped


def _extract_form_data(page_html: str, form_id: str) -> list[tuple[str, str]]:
    parser = _FormInputParser(form_id)
    parser.feed(page_html)
    return parser.inputs


def _extract_tender_id(detail_html: str) -> str | None:
    fields = _extract_caption_fields(detail_html)
    tender_id = fields.get("tender id")
    if tender_id:
        return tender_id
    return None


def _extract_caption_fields(page_html: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pattern = re.compile(
        r'<td\b[^>]*class="[^"]*\btd_caption\b[^"]*"[^>]*>(?P<label>.*?)</td>\s*'
        r'<td\b[^>]*class="[^"]*\btd_field\b[^"]*"[^>]*>(?P<value>.*?)</td>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(page_html):
        label = _normalize_text(match.group("label")).replace("₹", "").strip().strip(":").lower()
        value = _normalize_text(match.group("value"))
        if label and value:
            fields.setdefault(label, value)
    return fields


def _normalize_text(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")[:150] or _hash_id(value)


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _fingerprint(values: list[str]) -> str:
    return hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
