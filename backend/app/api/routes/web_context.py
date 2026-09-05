from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.webintel.crawler import get_default_crawler
from app.webintel.extractor import extract_evidence
from app.webintel.intelligence import build_intelligence
from app.webintel.models import WebEvidence
from app.webintel.schemas import ProcurementIntelligenceResponse, SearchRequest, StoredPage, WebSearchResponse
from app.webintel.search import get_default_search_provider
from app.webintel.source_authority import classify_source, is_procurement_relevant
from app.webintel.utils import canonicalize_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/web", tags=["web-intelligence"])


class WebContextSearchRequest(SearchRequest):
    focus: str = "procurement context"
    limit: int = 8


@router.post("/context-search")
def search_web_context(request: WebContextSearchRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Search and store contextual web material for an investigation.

    This route deliberately does NOT create WebProcurementEvidence links. Context
    can inform an investigator about prior reporting, contracts, litigation,
    audit/compliance history, or government statements, but it is kept outside the
    authoritative procurement evidence/risk path.
    """
    subject = request.query.strip()
    focus = request.focus.strip() or "procurement context"
    limit = min(max(request.limit, 1), 10)
    search_query = f'"{subject}" {focus}'
    provider = get_default_search_provider()
    crawler = get_default_crawler()
    results = provider.search(query=search_query, limit=limit)

    stored: list[StoredPage] = []
    rejected = 0
    seen: set[str] = set()

    for result in results:
        url = canonicalize_url(result.url)
        if url in seen:
            continue
        seen.add(url)

        classification = classify_source(url, title=result.title)
        if not classification.admissible:
            rejected += 1
            continue

        page = crawler.fetch(url)
        if page is None:
            continue
        if not is_procurement_relevant(page.title or result.title, page.url, page.content):
            rejected += 1
            continue

        existing = db.scalar(
            select(WebEvidence).where(
                or_(WebEvidence.content_hash == page.content_hash, WebEvidence.url == page.url)
            )
        )
        if existing is None:
            evidence = WebEvidence(
                query=subject,
                url=page.url,
                title=page.title or result.title,
                content=page.content,
                source=page.source or result.source,
                retrieved_at=page.retrieved_at,
                content_hash=page.content_hash,
                extraction=extract_evidence(page.content).model_dump(),
            )
            db.add(evidence)
            try:
                db.commit()
                db.refresh(evidence)
                existing = evidence
            except Exception:
                db.rollback()
                existing = db.scalar(select(WebEvidence).where(WebEvidence.content_hash == page.content_hash))

        if existing is not None:
            stored.append(_stored_page(existing))

    logger.info(
        "Stored web context subject=%s focus=%s results=%s stored=%s rejected=%s",
        subject,
        focus,
        len(results),
        len(stored),
        rejected,
    )
    return {
        "query": subject,
        "focus": focus,
        "search_query": search_query,
        "search_results": [item.model_dump() for item in results],
        "downloaded_pages": len(stored),
        "stored_pages": [item.model_dump() for item in stored],
        "rejected_non_context": rejected,
    }


@router.get("/context", response_model=ProcurementIntelligenceResponse)
def get_web_context(
    q: str,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ProcurementIntelligenceResponse:
    """Return classified web context without elevating it into case evidence."""
    query = q.strip()
    search_term = f"%{query}%"
    statement = (
        select(WebEvidence)
        .where(WebEvidence.query.ilike(search_term))
        .order_by(WebEvidence.retrieved_at.desc(), WebEvidence.id.desc())
        .limit(min(max(limit, 1), 200))
    )
    evidences = list(db.scalars(statement).all())
    return build_intelligence(query, evidences)


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
        procurement_evidence=None,
    )
