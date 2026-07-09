from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Company, Tender
from app.schemas.profiles import AutocompleteResponse, SearchHit, SearchResponse
from app.services.search_query import matches, relevance_score, source_rank_ordering

router = APIRouter(prefix="/api/search", tags=["search"])


def _tender_source_rank():
    """Indian-first source ordering for tender search (lower rank shown first)."""
    return source_rank_ordering()


@router.get("", response_model=SearchResponse)
def global_search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SearchResponse:
    term = f"%{q.strip()}%"

    # Ranked full-text + fuzzy + synonym search, Indian procurement first.
    tenders = db.scalars(
        select(Tender)
        .where(matches(q))
        .order_by(
            _tender_source_rank().asc(),
            relevance_score(q).desc(),
            Tender.published_date.desc().nullslast(),
        )
        .limit(limit)
    ).all()
    companies = db.scalars(
        select(Company)
        .where(or_(Company.name.ilike(term), Company.name.op("%")(q.strip())))
        .order_by(func.similarity(Company.name, q.strip()).desc(), Company.name)
        .limit(limit)
    ).all()
    buyer_rows = db.execute(
        select(Tender.procuring_entity, func.count())
        .where(
            or_(Tender.procuring_entity.ilike(term), Tender.procuring_entity.op("%")(q.strip())),
            Tender.procuring_entity.is_not(None),
        )
        .group_by(Tender.procuring_entity)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()

    tender_hits = [
        SearchHit(type="tender", id=str(t.id), label=t.title, sublabel=t.reference_number) for t in tenders
    ]
    company_hits = [
        SearchHit(type="company", id=str(c.id), label=c.name, sublabel=c.registration_number) for c in companies
    ]
    buyer_hits = [
        SearchHit(type="buyer", id=name, label=name, sublabel=f"{count} tenders") for name, count in buyer_rows
    ]
    return SearchResponse(
        query=q,
        tenders=tender_hits,
        companies=company_hits,
        buyers=buyer_hits,
        total=len(tender_hits) + len(company_hits) + len(buyer_hits),
    )


@router.get("/autocomplete", response_model=AutocompleteResponse)
def autocomplete(
    q: str = Query(min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
) -> AutocompleteResponse:
    term = f"%{q.strip()}%"
    per = max(2, limit // 3)
    suggestions: list[SearchHit] = []

    for t in db.scalars(
        select(Tender)
        .where(matches(q))
        .order_by(
            _tender_source_rank().asc(),
            relevance_score(q).desc(),
            Tender.published_date.desc().nullslast(),
        )
        .limit(per)
    ):
        suggestions.append(SearchHit(type="tender", id=str(t.id), label=t.title, sublabel=t.reference_number))
    for c in db.scalars(select(Company).where(Company.name.ilike(term)).limit(per)):
        suggestions.append(SearchHit(type="company", id=str(c.id), label=c.name, sublabel=c.registration_number))
    for name, _ in db.execute(
        select(Tender.procuring_entity, func.count())
        .where(Tender.procuring_entity.ilike(term), Tender.procuring_entity.is_not(None))
        .group_by(Tender.procuring_entity)
        .limit(per)
    ).all():
        suggestions.append(SearchHit(type="buyer", id=name, label=name))

    return AutocompleteResponse(query=q, suggestions=suggestions[:limit])
