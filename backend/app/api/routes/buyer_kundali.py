from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.buyer_kundali import BuyerKundaliResponse
from app.services.buyer_kundali import build_buyer_kundali

router = APIRouter(prefix="/api/buyers", tags=["buyer-kundali"])


@router.get("/kundali", response_model=BuyerKundaliResponse)
def get_buyer_kundali(
    buyer: str = Query(min_length=1, max_length=255),
    db: Session = Depends(get_db),
) -> BuyerKundaliResponse:
    kundali = build_buyer_kundali(db, buyer)
    if kundali is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Buyer {buyer!r} was not found in the indexed Indian procurement corpus.",
        )
    return kundali
