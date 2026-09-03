from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from app.connectors.common.envelope import build_envelope, write_envelope
from app.connectors.common.http import BaseHttpDownloader
from app.connectors.gem.connector import GeMSourceConnector
from app.importers.generic import GenericConnectorImporter
from app.models import Tender

_GEM_HOSTS = {
    "gem.gov.in",
    "www.gem.gov.in",
    "bidplus.gem.gov.in",
    "bidplus-global.gem.gov.in",
}
_BID_RE = re.compile(r"\bGEM/(?:\d{4})/B/\d+\b", re.I)


class LiveGeMIngestionError(ValueError):
    pass


class LiveGeMIngestion:
    source_name = "gem"

    def _validate_url(self, url: str) -> str:
        value = url.strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in _GEM_HOSTS:
            raise LiveGeMIngestionError(
                "Only an official GeM URL from gem.gov.in or bidplus.gem.gov.in is accepted."
            )
        return value

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()

    @staticmethod
    def _parse_money(value: str | None) -> Decimal | None:
        if not value:
            return None
        normalized = re.sub(r"[^0-9.]", "", value)
        if not normalized:
            return None
        try:
            return Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_datetime(value: str | None) -> str | None:
        if not value:
            return None
        for fmt in (
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%d-%m-%Y",
        ):
            try:
                return datetime.strptime(value.strip(), fmt).replace(tzinfo=UTC).isoformat()
            except ValueError:
                continue
        return None

    def _extract_pairs(self, html: str) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, re.I | re.S):
            cells = [self._clean(x) for x in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", row, re.I | re.S)]
            if len(cells) >= 2 and cells[0] and cells[1]:
                pairs.setdefault(cells[0].casefold().rstrip(":"), cells[1])
        return pairs

    def _build_flat_record(self, url: str, html: str, retrieved_at: datetime, bid_number: str) -> dict:
        pairs = self._extract_pairs(html)

        def pick(*labels: str) -> str | None:
            for label in labels:
                value = pairs.get(label.casefold().rstrip(":"))
                if value:
                    return value
            return None

        title = pick("global tender title", "bid title", "tender title", "item category", "category")
        buyer = pick("organisation name", "organisation", "office name", "department name", "ministry/state name")
        department = pick("department name")
        category = pick("item category", "product category", "service category")
        bid_end = pick("bid end date/time", "bid end date", "bid submission end date/time")
        bid_open = pick("bid opening date/time", "bid opening date")
        published = pick("dated", "bid start date", "start date")
        value = pick("estimated bid value", "total value", "bid value")
        location = pick("delivery location", "consignee location", "state name", "ministry/state name")

        flat = {
            "bid_number": bid_number,
            "bid_title": title or f"GeM bid {bid_number}",
            "buyer_name": buyer,
            "department": department,
            "category_name": category,
            "bid_end_date": self._parse_datetime(bid_end),
            "published_date": self._parse_datetime(published),
            "bid_opening_date": self._parse_datetime(bid_open),
            "location": location,
            "description": title,
            "amount": self._parse_money(value),
            "page_html": html,
        }
        return flat

    def ingest(self, db, url: str) -> dict:
        source_url = self._validate_url(url)
        retrieved_at = datetime.now(UTC)
        try:
            with httpx.Client(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                headers={"User-Agent": BaseHttpDownloader.user_agent},
            ) as client:
                response = client.get(source_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LiveGeMIngestionError(f"GeM page could not be fetched: {exc}") from exc

        html = response.text
        match = _BID_RE.search(html) or _BID_RE.search(source_url)
        if not match:
            raise LiveGeMIngestionError(
                "No GeM Bid Number was found. Use an official public GeM BidPlus detail/document URL."
            )
        bid_number = match.group(0).upper()
        record = self._build_flat_record(source_url, html, retrieved_at, bid_number)

        with TemporaryDirectory(prefix="sentry-gem-") as tmp:
            out = Path(tmp)
            envelope = build_envelope(
                source_name=self.source_name,
                source_record_id=bid_number,
                source_url=source_url,
                data=record,
                retrieved_at=retrieved_at,
                content_type=response.headers.get("content-type"),
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
            write_envelope(out / f"{bid_number.replace('/', '_')}.json", envelope)
            stats = GenericConnectorImporter(db, self.source_name, batch_size=1).import_directory(out)

        tender = db.scalar(
            select(Tender).where(
                Tender.source_name == self.source_name,
                Tender.source_record_id == bid_number,
            )
        )
        if tender is None:
            raise LiveGeMIngestionError("GeM page was fetched but no normalized tender row was produced.")

        return {
            "status": "imported" if stats.imported_tenders or stats.updated_tenders else "unchanged",
            "tender_id": bid_number,
            "tender_pk": str(tender.id),
            "reference_number": tender.reference_number,
            "source_url": source_url,
            "retrieved_at": retrieved_at.isoformat(),
            "imported_tenders": stats.imported_tenders,
            "updated_tenders": stats.updated_tenders,
            "imported_companies": stats.imported_companies,
            "imported_awards": stats.imported_awards,
            "imported_documents": stats.imported_documents,
            "unchanged_records": stats.unchanged_records,
            "failed": stats.failed,
            "message": "Live GeM bid normalized and stored with provenance." if not stats.failed else "Live GeM bid fetched but import reported failures.",
        }
