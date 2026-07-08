from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.connectors.common.source_priority import _SOURCE_RANK, _UNKNOWN_RANK
from app.models import Company, Tender
from app.schemas.profiles import AutocompleteResponse, SearchHit, SearchResponse

router = APIRouter(prefix="/api/search", tags=["search"])


def _tender_source_rank():
    """Indian-first source ordering for tender search (lower rank shown first)."""
    return case(
        {name: rank for name, rank in _SOURCE_RANK.items()},
        value=Tender.source_name,
        else_=_UNKNOWN_RANK,
    )


@router.get("", response_model=SearchResponse)
def global_search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SearchResponse:
    term = f"%{q.strip()}%"

    tenders = db.scalars(
        select(Tender)
        .where(or_(Tender.title.ilike(term), Tender.reference_number.ilike(term), Tender.procuring_entity.ilike(term)))
        .order_by(_tender_source_rank().asc(), Tender.published_date.desc().nullslast())
        .limit(limit)
    ).all()
    companies = db.scalars(select(Company).where(Company.name.ilike(term)).order_by(Company.name).limit(limit)).all()
    buyer_rows = db.execute(
        select(Tender.procuring_entity, func.count())
        .where(Tender.procuring_entity.ilike(term), Tender.procuring_entity.is_not(None))
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
        .where(or_(Tender.title.ilike(term), Tender.reference_number.ilike(term)))
        .order_by(_tender_source_rank().asc(), Tender.published_date.desc().nullslast())
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
