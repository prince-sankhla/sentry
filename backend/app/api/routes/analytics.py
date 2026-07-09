from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models import Award, Company, Tender
from app.schemas.analytics import (
    AwardItem,
    AwardStats,
    AwardsResponse,
    GeographyResponse,
    MonthlyPoint,
    OverviewResponse,
    OverviewTotals,
    PortfolioRisk,
    Region,
    SourceCount,
    TimelineEvent,
    TimelineResponse,
    TopBuyer,
    TopSupplier,
)
from app.schemas.common import Pagination
from app.services.procurement_intelligence import build_portfolio_risk
from app.services.search_query import source_rank_ordering

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

UNATTRIBUTED = "Unattributed"

# Indian states and union territories used for best-effort geographic attribution.
INDIAN_REGIONS: tuple[str, ...] = (
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
)


@router.get("/awards", response_model=AwardsResponse)
def list_awards(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1, max_length=200),
    sort: str = Query(default="newest", pattern="^(newest|amount|award_date|buyer)$"),
    db: Session = Depends(get_db),
) -> AwardsResponse:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                Company.name.ilike(term),
                Tender.title.ilike(term),
                Tender.reference_number.ilike(term),
            )
        )

    stats_row = db.execute(
        select(
            func.count(Award.id),
            func.coalesce(func.sum(Award.award_value), 0),
            func.coalesce(func.avg(Award.award_value), 0),
            func.count(func.distinct(Award.company_id)),
            func.count(func.distinct(Tender.procuring_entity)),
        )
        .select_from(Award)
        .join(Company, Award.company_id == Company.id)
        .join(Tender, Award.tender_id == Tender.id)
        .where(*filters)
    ).one()

    total = int(stats_row[0])
    stats = AwardStats(
        total_awards=total,
        total_value=stats_row[1],
        average_value=stats_row[2],
        awarded_suppliers=int(stats_row[3]),
        awarding_buyers=int(stats_row[4]),
    )

    statement = (
        select(Award)
        .join(Company, Award.company_id == Company.id)
        .join(Tender, Award.tender_id == Tender.id)
        .where(*filters)
        .options(joinedload(Award.company), joinedload(Award.tender))
    )
    awards = db.execute(
        _apply_award_sort(statement, sort).limit(limit).offset(offset)
    ).unique().scalars().all()

    return AwardsResponse(
        items=[AwardItem.model_validate(award) for award in awards],
        pagination=Pagination(limit=limit, offset=offset, total=total),
        stats=stats,
    )


@router.get("/overview", response_model=OverviewResponse)
def get_overview(db: Session = Depends(get_db)) -> OverviewResponse:
    total_tenders = db.scalar(select(func.count()).select_from(Tender)) or 0
    total_companies = db.scalar(select(func.count()).select_from(Company)) or 0
    total_awards = db.scalar(select(func.count()).select_from(Award)) or 0
    total_tender_value = db.scalar(select(func.coalesce(func.sum(Tender.estimated_value), 0))) or 0
    total_awarded_value = db.scalar(select(func.coalesce(func.sum(Award.award_value), 0))) or 0
    average_tender_value = db.scalar(select(func.coalesce(func.avg(Tender.estimated_value), 0))) or 0
    buyers = db.scalar(select(func.count(func.distinct(Tender.procuring_entity)))) or 0

    single_bidder_subquery = (
        select(Award.tender_id)
        .group_by(Award.tender_id)
        .having(func.count(func.distinct(Award.company_id)) == 1)
        .subquery()
    )
    single_bidder_tenders = db.scalar(
        select(func.count()).select_from(single_bidder_subquery)
    ) or 0

    totals = OverviewTotals(
        tenders=total_tenders,
        companies=total_companies,
        awards=total_awards,
        total_tender_value=total_tender_value,
        total_awarded_value=total_awarded_value,
        average_tender_value=average_tender_value,
        single_bidder_tenders=single_bidder_tenders,
        buyers=buyers,
    )

    # Indian procurement first: rank Indian buyers/suppliers ahead of
    # international ones (by best/lowest source rank in the group), then by value.
    buyer_label = func.coalesce(Tender.procuring_entity, UNATTRIBUTED)
    buyer_value = func.coalesce(func.sum(Award.award_value), 0)
    buyer_rank = func.min(source_rank_ordering())
    top_buyers = [
        TopBuyer(buyer=row[0], tenders=int(row[1]), awards=int(row[2]), total_value=row[3])
        for row in db.execute(
            select(
                buyer_label,
                func.count(func.distinct(Award.tender_id)),
                func.count(Award.id),
                buyer_value,
            )
            .select_from(Award)
            .join(Tender, Award.tender_id == Tender.id)
            .group_by(buyer_label)
            .order_by(buyer_rank.asc(), buyer_value.desc())
            .limit(8)
        ).all()
    ]

    supplier_value = func.coalesce(func.sum(Award.award_value), 0)
    supplier_rank = func.min(source_rank_ordering())
    top_suppliers = [
        TopSupplier(company_id=row[0], name=row[1], awards=int(row[2]), total_value=row[3])
        for row in db.execute(
            select(
                Company.id,
                Company.name,
                func.count(Award.id),
                supplier_value,
            )
            .select_from(Award)
            .join(Company, Award.company_id == Company.id)
            .join(Tender, Award.tender_id == Tender.id)
            .group_by(Company.id, Company.name)
            .order_by(supplier_rank.asc(), supplier_value.desc())
            .limit(8)
        ).all()
    ]

    month_expr = func.to_char(Tender.published_date, "YYYY-MM")
    monthly_rows = db.execute(
        select(
            month_expr,
            func.count(Tender.id),
            func.coalesce(func.sum(Tender.estimated_value), 0),
        )
        .where(Tender.published_date.is_not(None))
        .group_by(month_expr)
        .order_by(month_expr.desc())
        .limit(12)
    ).all()
    monthly = [
        MonthlyPoint(month=row[0], tenders=int(row[1]), value=row[2])
        for row in reversed(monthly_rows)
    ]

    source_label = func.coalesce(Tender.source_name, "unknown")
    sources = [
        SourceCount(source_name=row[0], tenders=int(row[1]))
        for row in db.execute(
            select(source_label, func.count(Tender.id))
            .group_by(source_label)
            .order_by(func.count(Tender.id).desc())
        ).all()
    ]

    return OverviewResponse(
        totals=totals,
        top_buyers=top_buyers,
        top_suppliers=top_suppliers,
        monthly=monthly,
        sources=sources,
    )


@router.get("/risk", response_model=PortfolioRisk)
def get_risk(db: Session = Depends(get_db)) -> PortfolioRisk:
    return build_portfolio_risk(db)


@router.get("/timeline", response_model=TimelineResponse)
def get_timeline(
    limit: int = Query(default=60, ge=1, le=200),
    db: Session = Depends(get_db),
) -> TimelineResponse:
    events: list[TimelineEvent] = []

    published_tenders = db.scalars(
        select(Tender)
        .where(Tender.published_date.is_not(None))
        .order_by(Tender.published_date.desc())
        .limit(limit)
    ).all()
    for tender in published_tenders:
        events.append(
            TimelineEvent(
                date=tender.published_date,
                kind="tender_published",
                title=tender.title,
                subtitle=tender.procuring_entity,
                reference=tender.reference_number,
                entity_type="tender",
                entity_id=tender.id,
            )
        )

    closing_tenders = db.scalars(
        select(Tender)
        .where(Tender.closing_date.is_not(None))
        .order_by(Tender.closing_date.desc())
        .limit(limit)
    ).all()
    for tender in closing_tenders:
        events.append(
            TimelineEvent(
                date=tender.closing_date,
                kind="tender_closing",
                title=tender.title,
                subtitle=tender.procuring_entity,
                reference=tender.reference_number,
                entity_type="tender",
                entity_id=tender.id,
            )
        )

    awards = db.execute(
        select(Award)
        .where(Award.award_date.is_not(None))
        .options(joinedload(Award.company), joinedload(Award.tender))
        .order_by(Award.award_date.desc())
        .limit(limit)
    ).unique().scalars().all()
    for award in awards:
        if award.company is None:
            continue
        tender_title = award.tender.title if award.tender is not None else "tender"
        events.append(
            TimelineEvent(
                date=award.award_date,
                kind="award",
                title=award.company.name,
                subtitle=f"Awarded: {tender_title}",
                reference=award.tender.reference_number if award.tender is not None else None,
                entity_type="company",
                entity_id=award.company.id,
            )
        )

    events.sort(key=_event_sort_key, reverse=True)
    return TimelineResponse(events=events[:limit])


@router.get("/geography", response_model=GeographyResponse)
def get_geography(db: Session = Depends(get_db)) -> GeographyResponse:
    award_counts: dict[UUID, int] = {
        row[0]: int(row[1])
        for row in db.execute(
            select(Award.tender_id, func.count(Award.id)).group_by(Award.tender_id)
        ).all()
    }

    tenders = db.execute(
        select(Tender.id, Tender.title, Tender.procuring_entity, Tender.estimated_value)
    ).all()

    tender_counts: dict[str, int] = defaultdict(int)
    value_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    award_totals: dict[str, int] = defaultdict(int)
    matched = 0

    for tender_id, title, procuring_entity, estimated_value in tenders:
        region = _match_region(procuring_entity, title)
        if region != UNATTRIBUTED:
            matched += 1
        tender_counts[region] += 1
        if estimated_value is not None:
            value_totals[region] += estimated_value
        award_totals[region] += award_counts.get(tender_id, 0)

    total = len(tenders)
    regions = [
        Region(
            region=region,
            tenders=count,
            value=value_totals[region],
            awards=award_totals[region],
        )
        for region, count in tender_counts.items()
    ]
    regions.sort(key=lambda item: item.tenders, reverse=True)

    return GeographyResponse(
        regions=regions,
        matched=matched,
        unmatched=total - matched,
        total=total,
    )


def _apply_award_sort(statement: Select[tuple[Award]], sort: str) -> Select[tuple[Award]]:
    if sort == "amount":
        return statement.order_by(
            Award.award_value.desc().nullslast(), Award.created_at.desc(), Award.id.desc()
        )
    if sort == "award_date":
        return statement.order_by(
            Award.award_date.desc().nullslast(), Award.created_at.desc(), Award.id.desc()
        )
    if sort == "buyer":
        return statement.order_by(
            Tender.procuring_entity.asc().nullslast(), Award.created_at.desc(), Award.id.desc()
        )
    return statement.order_by(Award.created_at.desc(), Award.id.desc())


def _event_sort_key(event: TimelineEvent) -> datetime:
    value = event.date
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return datetime(value.year, value.month, value.day)


def _match_region(procuring_entity: str | None, title: str | None) -> str:
    haystack = f"{procuring_entity or ''} {title or ''}".casefold()
    for region in INDIAN_REGIONS:
        if region.casefold() in haystack:
            return region
    return UNATTRIBUTED
