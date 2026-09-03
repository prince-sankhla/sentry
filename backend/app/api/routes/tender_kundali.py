from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.tender_kundali import TenderKundaliResponse
from app.services.tender_kundali import build_tender_kundali

router = APIRouter(prefix="/api/tenders", tags=["tender-kundali"])


@router.get("/{tender_id}/kundali", response_model=TenderKundaliResponse)
def get_tender_kundali(tender_id: UUID, db: Session = Depends(get_db)) -> TenderKundaliResponse:
    result = build_tender_kundali(db, tender_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tender {tender_id} was not found.")
    return result
