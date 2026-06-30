from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.webintel.schemas import SearchResult
from app.webintel.utils import canonicalize_url, clean_whitespace, domain_from_url

logger = logging.getLogger(__name__)


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        raise NotImplementedError


class TavilySearchProvider(SearchProvider):
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        raise NotImplementedError("Tavily support is an extension point and requires an API key.")


class BraveSearchProvider(SearchProvider):
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        raise NotImplementedError("Brave Search support is an extension point and requires an API key.")


class SearXNGSearchProvider(SearchProvider):
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        raise NotImplementedError("SearXNG support is an extension point and requires a configured instance.")


class DuckDuckGoSearchProvider(SearchProvider):
    search_url = "https://duckduckgo.com/html/"

    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = httpx.Timeout(timeout)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        html = self._fetch(query)
        results = _DuckDuckGoHTMLParser().parse(html)
        return results[:limit]

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch(self, query: str) -> str:
        headers = {
            "User-Agent": "SENTRY-WebIntel/0.1 (+public evidence collection; contact: local)",
            "Accept": "text/html,application/xhtml+xml",
        }
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(self.search_url, params={"q": query})
            response.raise_for_status()
            return response.text


class _DuckDuckGoHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[SearchResult] = []
        self._in_link = False
        self._in_snippet = False
        self._current_href: str | None = None
        self._current_title: list[str] = []
        self._current_snippet: list[str] = []

    def parse(self, html: str) -> list[SearchResult]:
        self.feed(html)
        return self.results

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        classes = set(attr.get("class", "").split())
        if tag == "a" and "result__a" in classes:
            self._in_link = True
            self._current_href = attr.get("href")
            self._current_title = []
            self._current_snippet = []
        elif tag in {"a", "div"} and ("result__snippet" in classes or "result__body" in classes):
            self._in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_link:
            title = clean_whitespace(" ".join(self._current_title))
            url = _duckduckgo_result_url(self._current_href or "")
            if title and url:
                canonical_url = canonicalize_url(url)
                domain = domain_from_url(canonical_url)
                self.results.append(
                    SearchResult(
                        title=title,
                        url=canonical_url,
                        snippet=None,
                        source=domain,
                        provider="duckduckgo",
                        domain=domain,
                        published_date=_extract_date(title),
                    )
                )
            self._in_link = False
            self._current_href = None
        elif tag in {"a", "div"} and self._in_snippet:
            snippet = clean_whitespace(" ".join(self._current_snippet))
            if snippet and self.results:
                latest = self.results[-1]
                self.results[-1] = latest.model_copy(
                    update={"snippet": snippet, "published_date": latest.published_date or _extract_date(snippet)}
                )
            self._in_snippet = False

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._current_title.append(data)
        elif self._in_snippet:
            self._current_snippet.append(data)


def _duckduckgo_result_url(href: str) -> str | None:
    if not href:
        return None
    parsed = urlparse(href)
    if parsed.path == "/l/":
        values = parse_qs(parsed.query).get("uddg")
        return unquote(values[0]) if values else None
    if parsed.scheme and parsed.netloc:
        return href
    return None


def _extract_date(text: str) -> datetime | None:
    match = re.search(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b", text)
    if not match:
        return None
    try:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def get_default_search_provider() -> SearchProvider:
    return DuckDuckGoSearchProvider()
