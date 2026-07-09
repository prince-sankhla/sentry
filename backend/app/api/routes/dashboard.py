from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.models import Award, Company, Tender
from app.schemas.dashboard import DashboardRecent, DashboardSummary
from app.services.search_query import source_rank_ordering

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    total_tenders = db.scalar(select(func.count()).select_from(Tender)) or 0
    total_companies = db.scalar(select(func.count()).select_from(Company)) or 0
    total_awards = db.scalar(select(func.count()).select_from(Award)) or 0
    total_procurement_value = db.scalar(select(func.coalesce(func.sum(Tender.estimated_value), 0))) or 0
    average_tender_value = db.scalar(select(func.coalesce(func.avg(Tender.estimated_value), 0))) or 0
    latest_import_date = db.scalar(select(func.max(Tender.created_at)))

    return DashboardSummary(
        total_tenders=total_tenders,
        total_companies=total_companies,
        total_awards=total_awards,
        total_procurement_value=total_procurement_value,
        average_tender_value=average_tender_value,
        latest_import_date=latest_import_date,
    )


@router.get("/recent", response_model=DashboardRecent)
def get_dashboard_recent(
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
) -> DashboardRecent:
    # Indian procurement first: recent activity surfaces Indian tenders ahead of
    # international ones, then by recency, so the dashboard is not World-Bank-dominated.
    latest_tenders = db.scalars(
        select(Tender)
        .order_by(source_rank_ordering().asc(), Tender.created_at.desc(), Tender.id.desc())
        .limit(limit)
    ).all()
    latest_awarded_companies = db.scalars(
        select(Company).order_by(Company.created_at.desc(), Company.name.asc()).limit(limit)
    ).all()
    latest_awards = db.execute(
        select(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .options(joinedload(Award.company), joinedload(Award.tender))
        .order_by(source_rank_ordering().asc(), Award.created_at.desc(), Award.id.desc())
        .limit(limit)
    ).unique().scalars().all()

    return DashboardRecent(
        latest_tenders=latest_tenders,
        latest_awarded_companies=latest_awarded_companies,
        latest_awards=latest_awards,
    )
