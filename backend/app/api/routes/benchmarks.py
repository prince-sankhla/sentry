from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.phase6_benchmark import TenderBenchmarkComparison
from app.services.phase6_benchmark import compare_tender_estimate

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])


@router.get("/tender/{tender_id}", response_model=TenderBenchmarkComparison)
def tender_benchmark(tender_id: str, db: Session = Depends(get_db)) -> TenderBenchmarkComparison:
    result = compare_tender_estimate(db, tender_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return result
