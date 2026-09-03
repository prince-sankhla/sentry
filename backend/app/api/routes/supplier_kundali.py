from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.supplier_kundali import SupplierKundaliResponse
from app.services.supplier_kundali import build_supplier_kundali

router = APIRouter(prefix="/api/companies", tags=["supplier-kundali"])


@router.get("/{company_id}/kundali", response_model=SupplierKundaliResponse)
def get_supplier_kundali(company_id: UUID, db: Session = Depends(get_db)) -> SupplierKundaliResponse:
    kundali = build_supplier_kundali(db, company_id)
    if kundali is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} was not found.",
        )

    # Keep the frontend's existing field name while the backend uses the clearer
    # `max_awards_at_buyer` metric internally.
    kundali.repeat_winner["max_consecutive_awards_at_buyer"] = kundali.repeat_winner["max_awards_at_buyer"]
    return kundali
