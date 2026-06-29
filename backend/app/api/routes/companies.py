from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models import Award, Company, Tender
from app.schemas.common import Pagination
from app.schemas.companies import (
    CompanyAwardHistoryItem,
    CompanyAwardHistoryResponse,
    CompanyDetail,
    CompanyListResponse,
    CompanyOverview,
    CompanyProfile,
    CompanySummary,
    CompanyTenderHistoryItem,
    CompanyTenderHistoryResponse,
    RelatedTender,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=CompanyListResponse)
def list_companies(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CompanyListResponse:
    total = db.scalar(select(func.count()).select_from(Company)) or 0
    companies = db.scalars(
        select(Company).order_by(Company.created_at.desc(), Company.name.asc()).limit(limit).offset(offset)
    ).all()

    return CompanyListResponse(
        items=[CompanySummary.model_validate(company) for company in companies],
        pagination=Pagination(limit=limit, offset=offset, total=total),
    )


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(company_id: UUID, db: Session = Depends(get_db)) -> CompanyDetail:
    company = db.execute(
        select(Company)
        .where(Company.id == company_id)
        .options(joinedload(Company.awards).joinedload(Award.tender))
    ).unique().scalar_one_or_none()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} was not found.",
        )

    tenders = sorted(
        {award.tender for award in company.awards if award.tender is not None},
        key=lambda tender: (tender.published_date is None, tender.published_date),
        reverse=True,
    )

    return CompanyDetail(
        **CompanySummary.model_validate(company).model_dump(),
        related_tenders=[RelatedTender.model_validate(tender) for tender in tenders],
        awards_won=company.awards,
    )


@router.get("/{company_id}/overview", response_model=CompanyOverview)
def get_company_overview(company_id: UUID, db: Session = Depends(get_db)) -> CompanyOverview:
    company = _get_company_or_404(company_id, db)
    awards = db.execute(
        select(Award)
        .where(Award.company_id == company_id)
        .options(joinedload(Award.tender))
    ).unique().scalars().all()

    tender_ids = {award.tender_id for award in awards}
    award_values = [award.award_value for award in awards if award.award_value is not None]
    procurement_dates = [
        procurement_date
        for award in awards
        for procurement_date in [award.award_date or (award.tender.published_date if award.tender else None)]
        if procurement_date is not None
    ]
    total_value = sum(award_values)
    average_value = total_value / len(award_values) if award_values else 0

    return CompanyOverview(
        company=_company_profile(company),
        registration_identifier=company.registration_number,
        address=None,
        total_tenders=len(tender_ids),
        total_awards_won=len(awards),
        total_procurement_value=total_value,
        average_award_value=average_value,
        first_procurement_date=min(procurement_dates) if procurement_dates else None,
        latest_procurement_date=max(procurement_dates) if procurement_dates else None,
    )


@router.get("/{company_id}/tenders", response_model=CompanyTenderHistoryResponse)
def get_company_tenders(
    company_id: UUID,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    sort: str = Query(default="latest", pattern="^(latest|published_date|value|title|award_value)$"),
    db: Session = Depends(get_db),
) -> CompanyTenderHistoryResponse:
    _get_company_or_404(company_id, db)

    filters = [Award.company_id == company_id]
    if q:
        search_term = f"%{q.strip()}%"
        filters.append(or_(Tender.title.ilike(search_term), Tender.procuring_entity.ilike(search_term)))

    total = db.scalar(
        select(func.count())
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(*filters)
    ) or 0

    statement = (
        select(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(*filters)
        .options(joinedload(Award.tender))
    )
    awards = db.execute(
        _apply_company_tender_sort(statement, sort).limit(limit).offset(offset)
    ).unique().scalars().all()

    return CompanyTenderHistoryResponse(
        items=[
            CompanyTenderHistoryItem(
                id=award.tender.id,
                reference_number=award.tender.reference_number,
                title=award.tender.title,
                tender_value=award.tender.estimated_value,
                currency=award.tender.currency,
                publication_date=award.tender.published_date,
                procurement_status=None,
                buyer=award.tender.procuring_entity,
                award_amount=award.award_value,
                award_date=award.award_date,
            )
            for award in awards
            if award.tender is not None
        ],
        pagination=Pagination(limit=limit, offset=offset, total=total),
    )


@router.get("/{company_id}/awards", response_model=CompanyAwardHistoryResponse)
def get_company_awards(
    company_id: UUID,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="latest", pattern="^(latest|award_date|amount|tender_title)$"),
    db: Session = Depends(get_db),
) -> CompanyAwardHistoryResponse:
    _get_company_or_404(company_id, db)
    total = db.scalar(select(func.count()).select_from(Award).where(Award.company_id == company_id)) or 0
    statement = (
        select(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(Award.company_id == company_id)
        .options(joinedload(Award.tender))
    )
    awards = db.execute(
        _apply_company_award_sort(statement, sort).limit(limit).offset(offset)
    ).unique().scalars().all()

    return CompanyAwardHistoryResponse(
        items=[
            CompanyAwardHistoryItem(
                id=award.id,
                award_amount=award.award_value,
                award_date=award.award_date,
                currency=award.currency,
                tender_id=award.tender.id,
                tender_title=award.tender.title,
                tender_reference_number=award.tender.reference_number,
            )
            for award in awards
            if award.tender is not None
        ],
        pagination=Pagination(limit=limit, offset=offset, total=total),
    )


def _get_company_or_404(company_id: UUID, db: Session) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} was not found.",
        )
    return company


def _company_profile(company: Company) -> CompanyProfile:
    return CompanyProfile(
        id=company.id,
        name=company.name,
        registration_number=company.registration_number,
        address=None,
        created_at=company.created_at,
        updated_at=company.updated_at,
    )


def _apply_company_tender_sort(statement: Select[tuple[Award]], sort: str) -> Select[tuple[Award]]:
    if sort == "published_date":
        return statement.order_by(Tender.published_date.desc().nullslast(), Tender.created_at.desc(), Tender.id.desc())
    if sort == "value":
        return statement.order_by(Tender.estimated_value.desc().nullslast(), Tender.created_at.desc(), Tender.id.desc())
    if sort == "title":
        return statement.order_by(Tender.title.asc(), Tender.created_at.desc(), Tender.id.desc())
    if sort == "award_value":
        return statement.order_by(Award.award_value.desc().nullslast(), Award.created_at.desc(), Award.id.desc())
    return statement.order_by(Award.created_at.desc(), Award.award_date.desc().nullslast(), Award.id.desc())


def _apply_company_award_sort(statement: Select[tuple[Award]], sort: str) -> Select[tuple[Award]]:
    if sort == "award_date":
        return statement.order_by(Award.award_date.desc().nullslast(), Award.created_at.desc(), Award.id.desc())
    if sort == "amount":
        return statement.order_by(Award.award_value.desc().nullslast(), Award.created_at.desc(), Award.id.desc())
    if sort == "tender_title":
        return statement.order_by(Tender.title.asc(), Award.created_at.desc(), Award.id.desc())
    return statement.order_by(Award.created_at.desc(), Award.award_date.desc().nullslast(), Award.id.desc())
