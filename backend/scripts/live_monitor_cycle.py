from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urljoin, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.connectors.common.envelope import build_envelope, write_envelope
from app.connectors.common.http import BaseHttpDownloader
from app.connectors.cppp.connector import CPPPSourceConnector
from app.connectors.gem.connector import GeMSourceConnector
from app.db.session import SessionLocal
from app.importers.generic import GenericConnectorImporter
from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationCompanyResult,
    InvestigationDocumentResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan
from app.services.investigation_indicators import build_indicators
from app.services.live_gem_ingestion import LiveGeMIngestion
from app.services.risk_engine import assess_risk_v2

CPPP_FEED_URL = "https://www.eprocure.gov.in/eprocure/app?page=Home&service=page"
GEM_FEED_URL = "https://bidplus-global.gem.gov.in/"
MAX_LINKS_PER_SOURCE = 15
TENDER_ID_RE = re.compile(r"\b\d{4}_[A-Z0-9]+_\d+_\d+\b", re.I)
GEM_BID_RE = re.compile(r"\bGEM/\d{4}/B/\d+\b", re.I)


class AnchorParser:
    def __init__(self) -> None:
        from html.parser import HTMLParser

        class Parser(HTMLParser):
            def __init__(self, outer: "AnchorParser") -> None:
                super().__init__(convert_charrefs=True)
                self.outer = outer
                self.href: str | None = None
                self.parts: list[str] = []

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                if tag.lower() == "a":
                    self.href = dict(attrs).get("href")
                    self.parts = []

            def handle_data(self, data: str) -> None:
                if self.href is not None:
                    self.parts.append(data)

            def handle_endtag(self, tag: str) -> None:
                if tag.lower() == "a" and self.href is not None:
                    label = re.sub(r"\s+", " ", " ".join(self.parts)).strip()
                    self.outer.links.append((self.href, label))
                    self.href = None
                    self.parts = []

        self.links: list[tuple[str, str]] = []
        self._parser = Parser(self)

    def feed(self, html: str) -> None:
        self._parser.feed(html)


def _absolute(base: str, href: str) -> str:
    return urljoin(base, href.strip())


def _official(url: str, hosts: set[str]) -> bool:
    try:
        return (urlparse(url).hostname or "").lower() in hosts
    except ValueError:
        return False


def discover_links(html: str, *, source: str) -> list[str]:
    parser = AnchorParser()
    parser.feed(html)
    base = CPPP_FEED_URL if source == "cppp" else GEM_FEED_URL
    hosts = (
        {"eprocure.gov.in", "www.eprocure.gov.in"}
        if source == "cppp"
        else {"gem.gov.in", "www.gem.gov.in", "bidplus.gem.gov.in", "bidplus-global.gem.gov.in"}
    )
    seen: set[str] = set()
    results: list[str] = []
    for href, label in parser.links:
        url = _absolute(base, href)
        if not _official(url, hosts) or url in seen:
            continue
        if source == "cppp":
            if "service=direct" not in url and "FrontEndTenderDetails" not in url:
                continue
            if not label and not TENDER_ID_RE.search(url):
                continue
        elif not GEM_BID_RE.search(f"{url} {label}"):
            continue
        seen.add(url)
        results.append(url)
        if len(results) >= MAX_LINKS_PER_SOURCE:
            break
    return results


def fetch(url: str) -> tuple[str, dict[str, str]]:
    with httpx.Client(
        timeout=httpx.Timeout(30.0),
        follow_redirects=True,
        headers={"User-Agent": BaseHttpDownloader.user_agent},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text, {k.lower(): v for k, v in response.headers.items()}


def normalize(source: str, url: str, html: str, retrieved_at: datetime):
    if source == "cppp":
        match = TENDER_ID_RE.search(html) or TENDER_ID_RE.search(url)
        if not match:
            raise ValueError("No CPPP tender id")
        record_id = match.group(0)
        envelope = build_envelope(
            source_name="cppp",
            source_record_id=record_id,
            source_url=url,
            data={"detail_html": html},
            retrieved_at=retrieved_at,
        )
        return envelope, CPPPSourceConnector().normalize(envelope)

    match = GEM_BID_RE.search(html) or GEM_BID_RE.search(url)
    if not match:
        raise ValueError("No GeM bid number")
    record_id = match.group(0).upper()
    flat = LiveGeMIngestion()._build_flat_record(html, record_id)
    envelope = build_envelope(
        source_name="gem",
        source_record_id=record_id,
        source_url=url,
        data=flat,
        retrieved_at=retrieved_at,
    )
    return envelope, GeMSourceConnector().normalize(envelope)


def to_package(records) -> InvestigationPackage:
    def meta(m):
        return InvestigationSourceMetadata(
            source_name=m.source_name,
            source_record_id=m.source_record_id,
            source_url=m.source_url,
            retrieved_at=m.retrieved_at,
        )

    package_records: list[InvestigationProcurementRecord] = []
    for record in records:
        t = record.tender
        pr = InvestigationProcurementRecord(
            tender=InvestigationTenderResult(
                reference_number=t.reference_number,
                title=t.title,
                description=t.description,
                procuring_entity=t.procuring_entity,
                published_date=t.published_date,
                closing_date=t.closing_date,
                estimated_value=t.estimated_value,
                currency=t.currency,
                metadata=meta(t.metadata),
            ),
            companies=[
                InvestigationCompanyResult(
                    name=c.name,
                    registration_number=c.registration_number,
                    company_identifier=c.registration_number,
                    metadata=meta(c.metadata),
                )
                for c in record.companies
            ],
            awards=[
                InvestigationAwardResult(
                    tender_reference_number=a.tender_reference_number,
                    company_name=a.company_name,
                    company_registration_number=a.company_registration_number,
                    company_identifier=a.company_registration_number,
                    award_date=a.award_date,
                    award_value=a.award_value,
                    currency=a.currency,
                    metadata=meta(a.metadata),
                )
                for a in record.awards
            ],
            documents=[
                InvestigationDocumentResult(
                    title=d.title,
                    url=d.url,
                    document_type=d.document_type,
                    metadata=meta(d.metadata),
                )
                for d in record.documents
            ],
        )
        package_records.append(pr)

    package = InvestigationPackage(
        plan=InvestigationPlan(
            query="live procurement monitor",
            investigation_type="tender",
            confidence=1.0,
            connectors=["cppp", "gem"],
            modules=["retrieval", "risk"],
            steps=[],
        ),
        records=package_records,
    )
    package.indicators = build_indicators(package)
    package.risk_assessment_v2 = assess_risk_v2(package)
    return package


def flagged_references(package: InvestigationPackage) -> set[str]:
    refs: set[str] = set()
    assessment = package.risk_assessment_v2
    if assessment is None or not assessment.indicators:
        return refs
    for indicator in assessment.indicators:
        refs.update(getattr(indicator, "related_tenders", []) or [])
    return refs or {r.tender.reference_number for r in package.records}


def main() -> int:
    candidates: list[tuple[dict, object]] = []
    stats = {"discovered": 0, "normalized": 0, "flagged": 0, "persisted": 0, "failed": 0}

    for source, feed_url in (("cppp", CPPP_FEED_URL), ("gem", GEM_FEED_URL)):
        try:
            feed_html, _ = fetch(feed_url)
            links = discover_links(feed_html, source=source)
        except Exception as exc:
            print(f"{source}: feed failed: {exc}")
            stats["failed"] += 1
            continue

        stats["discovered"] += len(links)
        for url in links:
            try:
                html, headers = fetch(url)
                retrieved_at = datetime.now(UTC)
                envelope, record = normalize(source, url, html, retrieved_at)
                envelope["content_type"] = headers.get("content-type")
                envelope["etag"] = headers.get("etag")
                envelope["last_modified"] = headers.get("last-modified")
                candidates.append((envelope, record))
                stats["normalized"] += 1
            except Exception as exc:
                print(f"{source}: detail failed {url}: {exc}")
                stats["failed"] += 1

    if not candidates:
        print({**stats, "status": "ok", "message": "No candidate records discovered."})
        return 0

    package = to_package([record for _, record in candidates])
    keep = flagged_references(package)
    stats["flagged"] = len(keep)

    if not keep:
        print({**stats, "status": "ok", "message": "No current records triggered deterministic indicators; nothing persisted."})
        return 0

    db = SessionLocal()
    try:
        for envelope, record in candidates:
            if record.tender.reference_number not in keep:
                continue
            source = str(envelope["source_name"])
            with TemporaryDirectory(prefix=f"sentry-monitor-{source}-") as tmp:
                path = Path(tmp) / f"{envelope['source_record_id']}.json"
                write_envelope(path, envelope)
                result = GenericConnectorImporter(db, source, batch_size=1).import_directory(Path(tmp))
                stats["persisted"] += result.imported_tenders + result.updated_tenders
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print({**stats, "status": "ok", "message": "Only flagged live records were persisted."})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
