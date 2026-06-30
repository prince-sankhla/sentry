from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.webintel.crawler import get_default_crawler
from app.webintel.extractor import extract_evidence
from app.webintel.models import WebEvidence, WebProcurementEvidence
from app.webintel.procurement_extractor import normalize_company_name
from app.webintel.procurement_store import ensure_procurement_evidence
from app.webintel.schemas import ProcurementEvidence, ProcurementEvidenceResponse, SearchRequest, StoredPage, WebSearchResponse
from app.webintel.search import get_default_search_provider
from app.webintel.utils import canonicalize_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/web", tags=["web-intelligence"])


@router.post("/search", response_model=WebSearchResponse)
def search_web(request: SearchRequest, db: Session = Depends(get_db)) -> WebSearchResponse:
    query = request.query.strip()
    search_provider = get_default_search_provider()
    crawler = get_default_crawler()
    search_results = search_provider.search(query=query, limit=10)

    downloaded_pages = 0
    duplicates_skipped = 0
    stored_pages: list[StoredPage] = []
    seen_urls: set[str] = set()

    for result in search_results:
        url = canonicalize_url(result.url)
        if url in seen_urls:
            duplicates_skipped += 1
            continue
        seen_urls.add(url)

        page = crawler.fetch(url)
        if page is None:
            continue
        downloaded_pages += 1

        existing = db.scalar(
            select(WebEvidence).where(
                (WebEvidence.content_hash == page.content_hash) | (WebEvidence.url == page.url)
            )
        )
        if existing is not None:
            ensure_procurement_evidence(db, existing)
            db.commit()
            db.refresh(existing)
            duplicates_skipped += 1
            stored_pages.append(_stored_page(existing))
            if len(stored_pages) >= 5:
                break
            continue

        extraction = extract_evidence(page.content)
        evidence = WebEvidence(
            query=query,
            url=page.url,
            title=page.title or result.title,
            content=page.content,
            source=page.source or result.source,
            retrieved_at=page.retrieved_at,
            content_hash=page.content_hash,
            extraction=extraction.model_dump(),
        )
        db.add(evidence)
        try:
            db.flush()
            ensure_procurement_evidence(db, evidence)
            db.commit()
        except IntegrityError:
            db.rollback()
            duplicates_skipped += 1
            existing = db.scalar(select(WebEvidence).where(WebEvidence.content_hash == page.content_hash))
            if existing is not None:
                ensure_procurement_evidence(db, existing)
                db.commit()
                db.refresh(existing)
                stored_pages.append(_stored_page(existing))
            continue

        db.refresh(evidence)
        stored_pages.append(_stored_page(evidence))
        logger.info("Stored web evidence query=%s url=%s", query, page.url)

        if len(stored_pages) >= 5:
            break

    return WebSearchResponse(
        search_results=search_results,
        downloaded_pages=downloaded_pages,
        stored_pages=stored_pages,
        duplicates_skipped=duplicates_skipped,
    )


@router.get("/procurement-evidence", response_model=ProcurementEvidenceResponse)
def list_procurement_evidence(
    q: str,
    limit: int = 25,
    db: Session = Depends(get_db),
) -> ProcurementEvidenceResponse:
    query = q.strip()
    normalized_query = normalize_company_name(query)
    search_term = f"%{query}%"
    normalized_term = f"%{normalized_query}%"
    statement = (
        select(WebEvidence)
        .join(WebProcurementEvidence, WebProcurementEvidence.web_evidence_id == WebEvidence.id)
        .where(
            or_(
                WebEvidence.query.ilike(search_term),
                WebProcurementEvidence.company_name.ilike(search_term),
                WebProcurementEvidence.normalized_company_name.ilike(normalized_term),
                WebProcurementEvidence.government_buyer.ilike(search_term),
                WebProcurementEvidence.tender_title.ilike(search_term),
                WebProcurementEvidence.contract_title.ilike(search_term),
                WebProcurementEvidence.organization.ilike(search_term),
            )
        )
        .order_by(WebEvidence.retrieved_at.desc(), WebEvidence.id.desc())
        .limit(min(max(limit, 1), 100))
    )
    return ProcurementEvidenceResponse(items=[_stored_page(evidence) for evidence in db.scalars(statement).all()])


def _stored_page(evidence: WebEvidence) -> StoredPage:
    extraction = (
        evidence.extraction
        if isinstance(evidence.extraction, dict) and evidence.extraction
        else extract_evidence(evidence.content).model_dump()
    )
    return StoredPage(
        id=str(evidence.id),
        query=evidence.query,
        url=evidence.url,
        title=evidence.title,
        source=evidence.source,
        retrieved_at=evidence.retrieved_at,
        content_hash=evidence.content_hash,
        extraction=extraction,
        procurement_evidence=_procurement_evidence(evidence.procurement_evidence),
    )


def _procurement_evidence(evidence: WebProcurementEvidence | None) -> ProcurementEvidence | None:
    if evidence is None:
        return None

    return ProcurementEvidence(
        id=str(evidence.id),
        web_evidence_id=str(evidence.web_evidence_id),
        tender_id=str(evidence.tender_id) if evidence.tender_id else None,
        company_id=str(evidence.company_id) if evidence.company_id else None,
        award_id=str(evidence.award_id) if evidence.award_id else None,
        company_name=evidence.company_name,
        normalized_company_name=evidence.normalized_company_name,
        government_buyer=evidence.government_buyer,
        tender_title=evidence.tender_title,
        contract_title=evidence.contract_title,
        contract_value=str(evidence.contract_value) if evidence.contract_value is not None else None,
        currency=evidence.currency,
        tender_category=evidence.tender_category,
        procurement_sector=evidence.procurement_sector,
        country=evidence.country,
        publication_date=evidence.publication_date.isoformat() if evidence.publication_date else None,
        award_date=evidence.award_date.isoformat() if evidence.award_date else None,
        contract_number=evidence.contract_number,
        tender_number=evidence.tender_number,
        organization=evidence.organization,
        people_mentioned=evidence.people_mentioned or [],
        related_companies=evidence.related_companies or [],
        raw_signals=evidence.raw_signals or {},
    )
