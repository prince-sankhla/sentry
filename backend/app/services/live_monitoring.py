from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from app.connectors.common.http import BaseHttpDownloader
from app.services.live_cppp_ingestion import LiveCPPPIngestion, LiveCPPPIngestionError
from app.services.live_gem_ingestion import LiveGeMIngestion, LiveGeMIngestionError

CPPP_FEED_URL = "https://www.eprocure.gov.in/eprocure/app?page=Home&service=page"
GEM_FEED_URL = "https://bidplus-global.gem.gov.in/"
_MAX_LINKS_PER_SOURCE = 15

_TENDER_ID_RE = re.compile(r"\b\d{4}_[A-Z0-9]+_\d+_\d+\b", re.I)
_GEM_BID_RE = re.compile(r"\bGEM/\d{4}/B/\d+\b", re.I)


@dataclass(frozen=True)
class FeedLink:
    source: str
    url: str
    label: str


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = dict(attrs).get("href")
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._href is None:
            return
        label = re.sub(r"\s+", " ", " ".join(self._parts)).strip()
        self.links.append((self._href, label))
        self._href = None
        self._parts = []


def _absolute(base: str, href: str) -> str:
    return urljoin(base, href.strip())


def _official(url: str, hosts: set[str]) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in hosts


def discover_cppp_links(html: str) -> list[FeedLink]:
    parser = _AnchorParser()
    parser.feed(html)
    seen: set[str] = set()
    results: list[FeedLink] = []
    for href, label in parser.links:
        url = _absolute(CPPP_FEED_URL, href)
        if not _official(url, {"eprocure.gov.in", "www.eprocure.gov.in"}):
            continue
        if "service=direct" not in url and "FrontEndTenderDetails" not in url:
            continue
        if url in seen:
            continue
        if not label and not _TENDER_ID_RE.search(url):
            continue
        seen.add(url)
        results.append(FeedLink("cppp", url, label))
        if len(results) >= _MAX_LINKS_PER_SOURCE:
            break
    return results


def discover_gem_links(html: str) -> list[FeedLink]:
    parser = _AnchorParser()
    parser.feed(html)
    seen: set[str] = set()
    results: list[FeedLink] = []
    for href, label in parser.links:
        url = _absolute(GEM_FEED_URL, href)
        bid_match = _GEM_BID_RE.search(f"{url} {label}")
        if not bid_match:
            continue
        if not _official(url, {"gem.gov.in", "www.gem.gov.in", "bidplus.gem.gov.in", "bidplus-global.gem.gov.in"}):
            continue
        if url in seen:
            continue
        seen.add(url)
        results.append(FeedLink("gem", url, label))
        if len(results) >= _MAX_LINKS_PER_SOURCE:
            break
    return results


def _fetch_html(url: str) -> str:
    with httpx.Client(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        headers={"User-Agent": BaseHttpDownloader.user_agent},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def poll_live_sources(db: Session) -> dict[str, object]:
    """Fetch current official source listings and idempotently ingest discovered records."""
    sources = (("cppp", CPPP_FEED_URL, discover_cppp_links), ("gem", GEM_FEED_URL, discover_gem_links))
    totals = {"sources": 0, "discovered": 0, "imported": 0, "updated": 0, "unchanged": 0, "failed": 0}
    details: list[dict[str, object]] = []

    for source, feed_url, discover in sources:
        source_result: dict[str, object] = {"source": source, "feed_url": feed_url, "discovered": 0, "imported": 0, "updated": 0, "unchanged": 0, "failed": 0, "errors": []}
        totals["sources"] += 1
        try:
            links = discover(_fetch_html(feed_url))
        except Exception as exc:  # noqa: BLE001
            source_result["failed"] = 1
            source_result["errors"] = [f"Feed fetch failed: {exc}"]
            totals["failed"] += 1
            details.append(source_result)
            continue

        source_result["discovered"] = len(links)
        totals["discovered"] += len(links)
        for link in links:
            try:
                if source == "cppp":
                    result = LiveCPPPIngestion().ingest(db, link.url)
                else:
                    result = LiveGeMIngestion().ingest(db, link.url)
                status = result["status"]
                key = "updated" if status == "imported" and result.get("updated_tenders") else "imported" if status == "imported" else "unchanged"
                source_result[key] = int(source_result[key]) + 1
                totals[key] = int(totals[key]) + 1
            except (LiveCPPPIngestionError, LiveGeMIngestionError, httpx.HTTPError, ValueError) as exc:
                source_result["failed"] = int(source_result["failed"]) + 1
                totals["failed"] += 1
                errors = source_result["errors"]
                assert isinstance(errors, list)
                if len(errors) < 5:
                    errors.append(f"{link.url}: {exc}")

        details.append(source_result)

    return {"status": "ok" if not totals["failed"] else "partial", "totals": totals, "sources": details}
