from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.field_verification import build_field_verification_plan

router = APIRouter(prefix="/api/investigations", tags=["field-verification"])


@router.get("/tenders/{tender_id}/field-verification")
def field_verification(tender_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Resolve the exact tender to a registered, executable field requirement profile."""
    return build_field_verification_plan(db, tender_id)
