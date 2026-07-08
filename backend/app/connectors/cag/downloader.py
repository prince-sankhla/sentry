"""CAG audit-report downloader (document-URL harvesting).

CAG procurement/performance audit reports are published as PDFs on cag.gov.in.
Without OCR we still capture, per report, its title + every PDF document URL so
future OCR/RAG can process the attachments. One envelope is written per report,
with the PDF links preserved in ``documents``.
"""

from __future__ import annotations

import html
import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from app.connectors.common.envelope import content_hash
from app.connectors.common.http import BaseHttpDownloader, DownloadStats
from app.connectors.cag.mapper import SOURCE_NAME

logger = logging.getLogger(__name__)

DEFAULT_INDEX_URLS = ("https://cag.gov.in/en/audit-report",)


class CAGDownloader(BaseHttpDownloader):
    source_name = SOURCE_NAME

    def __init__(self, output_dir: Path, index_urls: Iterable[str] = DEFAULT_INDEX_URLS, timeout: float = 30.0) -> None:
        super().__init__(output_dir, timeout=timeout)
        self.index_urls = [url for url in index_urls if url]

    def download(self, limit: int = 500) -> DownloadStats:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stats = DownloadStats()
        collected = 0
        with self.client() as client:
            for index_url in self.index_urls:
                if collected >= limit:
                    break
                try:
                    page = self.get_text(client, index_url, conditional=True)
                except Exception:
                    stats.failed += 1
                    logger.exception("Failed to fetch CAG index %s", index_url)
                    continue
                if page is None:
                    continue
                stats.pages += 1
                for title, pdf_url in _extract_reports(page, index_url):
                    if collected >= limit:
                        break
                    record_id = f"cag:{content_hash(pdf_url)[:16]}"
                    outcome = self.save_record(
                        record_id=record_id,
                        source_url=pdf_url,
                        data={"title": title, "report_url": pdf_url, "report_no": record_id},
                        documents=[{"title": title, "url": pdf_url, "document_type": "audit_report"}],
                        content_type="application/pdf",
                    )
                    if outcome == "downloaded":
                        stats.downloaded += 1
                    elif outcome == "unchanged":
                        stats.unchanged += 1
                    else:
                        stats.skipped_existing += 1
                    collected += 1
        return self.finalize(stats)


class _PdfLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href and href.lower().split("?")[0].endswith(".pdf"):
            self._href = html.unescape(href)
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            title = re.sub(r"\s+", " ", "".join(self._text)).strip() or "CAG audit report"
            self.links.append((title[:500], self._href))
            self._href = None
            self._text = []


def _extract_reports(page_html: str, base_url: str) -> list[tuple[str, str]]:
    parser = _PdfLinkParser()
    parser.feed(page_html)
    seen: set[str] = set()
    reports: list[tuple[str, str]] = []
    for title, href in parser.links:
        url = urljoin(base_url, href)
        if url in seen:
            continue
        seen.add(url)
        reports.append((title, url))
    return reports
