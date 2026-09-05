from __future__ import annotations

import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.webintel.crawler import get_default_crawler
from app.webintel.extractor import extract_evidence
from app.webintel.intelligence import build_intelligence
from app.webintel.models import WebEvidence
from app.webintel.schemas import ProcurementIntelligenceResponse, SearchRequest, StoredPage
from app.webintel.search import get_default_search_provider
from app.webintel.source_authority import classify_source
from app.webintel.utils import canonicalize_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/web", tags=["web-intelligence"])

_CONTEXT_NEWS_HOSTS = (
    "thehindu.com",
    "indianexpress.com",
    "timesofindia.indiatimes.com",
    "economictimes.indiatimes.com",
    "business-standard.com",
    "hindustantimes.com",
    "moneycontrol.com",
    "livemint.com",
    "financialexpress.com",
    "deccanherald.com",
    "telegraphindia.com",
)

_CONTEXT_KEYWORDS = (
    "tender", "procurement", "contract", "award", "bid", "vendor", "supplier",
    "work order", "purchase order", "audit", "vigilance", "investigation",
    "irregularity", "probe", "litigation", "court", "tribunal", "blacklist", "debar",
    "scam", "allegation", "dispute", "government spending", "public works",
    "company", "corporate", "annual report", "director", "subsidiary", "financial",
    "regulatory", "compliance", "order", "judgment", "case", "notice", "penalty",
)


class WebContextSearchRequest(SearchRequest):
    focus: str = "tender contract procurement news audit investigation history"
    limit: int = 8


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _is_context_host(url: str) -> bool:
    host = _host(url)
    if any(host == suffix or host.endswith("." + suffix) for suffix in _CONTEXT_NEWS_HOSTS):
        return True
    return classify_source(url).admissible


def _query_tokens(query: str) -> list[str]:
    cleaned = query.replace("||", " ").replace("/", " ").replace("-", " ")
    return [token for token in cleaned.casefold().split() if len(token) > 3]


def _is_context_relevant(query: str, title: str | None, content: str, url: str) -> bool:
    # Never include the query itself in the searchable haystack: doing so makes
    # every result appear subject-relevant even when the source says nothing about it.
    haystack = " ".join([title or "", url, content[:16000]]).casefold()
    keyword_hits = sum(1 for keyword in _CONTEXT_KEYWORDS if keyword in haystack)
    if keyword_hits < 1:
        return False

    tokens = _query_tokens(query)
    if not tokens:
        return keyword_hits >= 2

    # For multi-token entities require at least two subject tokens. For a single
    # token subject, one match is enough. This rejects generic pages such as a
    # Delhi tourism homepage for a Delhi University investigation.
    required = 1 if len(tokens) == 1 else min(2, len(tokens))
    subject_hits = sum(1 for token in tokens[:10] if token in haystack)
    return subject_hits >= required


def search_web_context(request: WebContextSearchRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Search public-web context with deterministic subject relevance guards.

    Context pages may be captured for review, but they remain outside primary
    procurement evidence and therefore cannot alter deterministic risk.
    """
    subject = request.query.strip()
    focus = request.focus.strip() or "procurement context"
    limit = min(max(request.limit, 1), 10)
    search_query = f'"{subject}" {focus}'
    search_provider = get_default_search_provider()
    crawler = get_default_crawler()

    raw_results = search_provider.search(query=search_query, limit=max(limit * 3, 18))
    selected_results = []
    stored: list[StoredPage] = []
    rejected = 0
    seen: set[str] = set()

    for result in raw_results:
        url = canonicalize_url(result.url)
        if url in seen:
            continue
        seen.add(url)
        if not _is_context_host(url):
            rejected += 1
            continue

        page = None
        try:
            page = crawler.fetch(url)
        except Exception as exc:  # noqa: BLE001
            logger.info("Context crawler failed url=%s error=%s", url, exc)

        if page is not None:
            relevant = _is_context_relevant(subject, page.title or result.title, page.content, page.url)
        else:
            relevant = _is_context_relevant(subject, result.title, result.snippet or "", url)

        if not relevant:
            rejected += 1
            continue

        selected_results.append(result)
        if page is not None:
            existing = db.scalar(
                select(WebEvidence).where(
                    or_(WebEvidence.content_hash == page.content_hash, WebEvidence.url == page.url)
                )
            )
            if existing is None:
                evidence = WebEvidence(
                    query=f"context:{subject}",
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

        if len(selected_results) >= limit:
            break

    return {
        "query": subject,
        "focus": focus,
        "search_query": search_query,
        "search_results": [item.model_dump(mode="json") for item in selected_results],
        "downloaded_pages": len(stored),
        "stored_pages": [item.model_dump(mode="json") for item in stored],
        "rejected_non_context": rejected,
        "classification": "supplementary_context_only",
        "risk_impact": "none",
    }


@router.post("/context-search")
def context_search(request: WebContextSearchRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Run one visible open-web research lane and return captured context."""
    return search_web_context(request, db)


@router.get("/context", response_model=ProcurementIntelligenceResponse)
def get_web_context(
    q: str,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> ProcurementIntelligenceResponse:
    """Return only previously captured context that still matches the subject."""
    query = q.strip()
    search_term = f"%context:{query}%"
    statement = (
        select(WebEvidence)
        .where(WebEvidence.query.ilike(search_term))
        .order_by(WebEvidence.retrieved_at.desc(), WebEvidence.id.desc())
        .limit(min(max(limit, 1), 200))
    )
    evidences = [
        evidence
        for evidence in db.scalars(statement).all()
        if _is_context_relevant(query, evidence.title, evidence.content, evidence.url)
    ]
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
