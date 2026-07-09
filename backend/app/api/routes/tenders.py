from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models import Award, Tender
from app.schemas.common import Pagination
from app.schemas.tenders import (
    BuyerInfo,
    CompanySummary,
    TenderDetail,
    TenderListResponse,
    TenderSummary,
)
from app.services.pdf_intelligence import extract_tender_fields
from app.services.procurement_intelligence import build_tender_intelligence
from app.services.search_query import matches, relevance_score, source_rank_ordering

router = APIRouter(prefix="/api/tenders", tags=["tenders"])


@router.get("", response_model=TenderListResponse)
def list_tenders(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1, max_length=200, description="Search tender title, description, buyer, supplier and reference."),
    sort: str = Query(default="newest", pattern="^(newest|published_date|value|title|relevance)$"),
    db: Session = Depends(get_db),
) -> TenderListResponse:
    total_statement = select(func.count()).select_from(Tender)
    tender_statement = select(Tender)
    if q:
        # Full-text + fuzzy + synonym retrieval (shared with global search).
        total_statement = total_statement.where(matches(q))
        tender_statement = tender_statement.where(matches(q))

    total = db.scalar(total_statement) or 0
    tenders = db.scalars(
        _apply_tender_sort(tender_statement, sort, q).limit(limit).offset(offset)
    ).all()

    return TenderListResponse(
        items=[TenderSummary.model_validate(tender) for tender in tenders],
        pagination=Pagination(limit=limit, offset=offset, total=total),
    )


def _apply_tender_sort(statement: Select[tuple[Tender]], sort: str, q: str | None = None) -> Select[tuple[Tender]]:
    # Indian procurement first everywhere; secondary key varies by requested sort.
    indian_first = source_rank_ordering().asc()
    if sort == "relevance" and q:
        return statement.order_by(indian_first, relevance_score(q).desc(), Tender.published_date.desc().nullslast())
    if sort == "published_date":
        return statement.order_by(indian_first, Tender.published_date.desc().nullslast(), Tender.created_at.desc(), Tender.id.desc())
    if sort == "value":
        return statement.order_by(indian_first, Tender.estimated_value.desc().nullslast(), Tender.created_at.desc(), Tender.id.desc())
    if sort == "title":
        return statement.order_by(indian_first, Tender.title.asc(), Tender.created_at.desc(), Tender.id.desc())
    return statement.order_by(indian_first, Tender.created_at.desc(), Tender.published_date.desc().nullslast(), Tender.id.desc())


@router.get("/{tender_id}", response_model=TenderDetail)
def get_tender(tender_id: UUID, db: Session = Depends(get_db)) -> TenderDetail:
    tender = db.execute(
        select(Tender)
        .where(Tender.id == tender_id)
        .options(joinedload(Tender.awards).joinedload(Award.company))
    ).unique().scalar_one_or_none()
    if tender is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender {tender_id} was not found.",
        )

    companies = sorted(
        {award.company for award in tender.awards if award.company is not None},
        key=lambda company: company.name,
    )

    # Expose the existing deterministic document-intelligence extractor over the
    # tender's stored text. Grounded: only values literally present are returned,
    # each with its source span; an empty extraction is surfaced as such so the
    # UI can hide the panel when no structured signal exists.
    document_text = "\n".join(part for part in (tender.title, tender.description) if part)
    pdf_intelligence = extract_tender_fields(document_text)

    return TenderDetail(
        **TenderSummary.model_validate(tender).model_dump(),
        description=tender.description,
        buyer=BuyerInfo(name=tender.procuring_entity),
        awards=tender.awards,
        participating_companies=[CompanySummary.model_validate(company) for company in companies],
        intelligence=build_tender_intelligence(db, tender),
        pdf_intelligence=pdf_intelligence,
    )
