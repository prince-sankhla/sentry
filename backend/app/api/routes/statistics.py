from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.procurement_statistics import ProcurementStatistics
from app.services.procurement_statistics import build_procurement_statistics

router = APIRouter(prefix="/api/statistics", tags=["statistics"])


@router.get("", response_model=ProcurementStatistics)
def procurement_statistics(
    top_n: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ProcurementStatistics:
    """Platform-wide procurement intelligence statistics, all DB-derived.

    Buyer/supplier rankings, award concentration (HHI), supplier diversity,
    competition metrics, tender success rates, and procurement/category/state
    trends — computed live from imported tenders, awards, and companies. Sources
    are annotated Indian-first.
    """
    return build_procurement_statistics(db, top_n=top_n)
