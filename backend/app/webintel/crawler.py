from __future__ import annotations

import logging
import re
import urllib.robotparser
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.webintel.schemas import CrawledPage
from app.webintel.utils import canonicalize_url, clean_whitespace, content_sha256

logger = logging.getLogger(__name__)


class Crawler(ABC):
    @abstractmethod
    def fetch(self, url: str) -> CrawledPage | None:
        raise NotImplementedError


class Crawl4AICrawler(Crawler):
    def fetch(self, url: str) -> CrawledPage | None:
        raise NotImplementedError("Crawl4AI support is an extension point for a local/self-hosted crawler.")


class JinaReaderCrawler(Crawler):
    def fetch(self, url: str) -> CrawledPage | None:
        raise NotImplementedError("Jina Reader support is an extension point for reader mode fetching.")


class FirecrawlCrawler(Crawler):
    def fetch(self, url: str) -> CrawledPage | None:
        raise NotImplementedError("Firecrawl support is an extension point and requires service configuration.")


class HttpCrawler(Crawler):
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = httpx.Timeout(timeout)
        self.user_agent = "SENTRY-WebIntel/0.1 (+public evidence collection; contact: local)"
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def fetch(self, url: str) -> CrawledPage | None:
        url = canonicalize_url(url)
        if not self._allowed_by_robots(url):
            logger.info("Skipping URL disallowed by robots.txt: %s", url)
            return None

        response = self._fetch(url)
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            logger.info("Skipping non-HTML URL content_type=%s url=%s", content_type, url)
            return None

        parser = _ContentHTMLParser(base_url=url)
        parser.feed(response.text)
        text = parser.content()
        if not text:
            logger.info("Skipping URL with no extractable text: %s", url)
            return None

        retrieved_at = datetime.now(UTC)
        return CrawledPage(
            url=str(response.url),
            title=parser.title,
            content=text,
            metadata=parser.metadata,
            source=urlparse(url).netloc,
            retrieved_at=retrieved_at,
            content_hash=content_sha256(text),
        )

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _fetch(self, url: str) -> httpx.Response:
        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}
        with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            return response

    def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        root = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = urljoin(root, "/robots.txt")
        parser = self._robots_cache.get(root)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception:
                logger.warning("Could not read robots.txt, skipping host for caution: %s", robots_url)
                return False
            self._robots_cache[root] = parser
        return parser.can_fetch(self.user_agent, url)


class _ContentHTMLParser(HTMLParser):
    block_tags = {"p", "div", "section", "article", "li", "tr", "br", "h1", "h2", "h3", "h4"}
    ignored_tags = {"script", "style", "noscript", "svg", "canvas", "form", "nav", "footer", "header"}

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title: str | None = None
        self.metadata: dict[str, str] = {}
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._stack: list[str] = []
        self._ignore_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack.append(tag)
        if tag in self.ignored_tags:
            self._ignore_depth += 1
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attr = {key.lower(): value or "" for key, value in attrs}
            name = attr.get("name") or attr.get("property")
            content = attr.get("content")
            if name and content and name.lower() in {"description", "og:title", "og:description", "article:published_time"}:
                self.metadata[name.lower()] = clean_whitespace(content)
        if tag in self.block_tags:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            title = clean_whitespace(" ".join(self._title_parts))
            if title:
                self.title = title
        if tag in self.ignored_tags and self._ignore_depth:
            self._ignore_depth -= 1
        if tag in self.block_tags:
            self._text_parts.append("\n")
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._ignore_depth:
            return
        cleaned = clean_whitespace(data)
        if cleaned:
            self._text_parts.append(cleaned)

    def content(self) -> str:
        text = " ".join(self._text_parts)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n\s+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def get_default_crawler() -> Crawler:
    return HttpCrawler()
