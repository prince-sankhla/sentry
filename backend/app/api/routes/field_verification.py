from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.field_verification import (
    build_field_verification_plan,
    build_field_verification_plan_by_reference,
)

router = APIRouter(prefix="/api/investigations", tags=["field-verification"])


@router.get("/tenders/{tender_id}/field-verification")
def field_verification(tender_id: UUID, db: Session = Depends(get_db)) -> dict:
    """Resolve the exact tender to a registered, executable field requirement profile."""
    return build_field_verification_plan(db, tender_id)


@router.get("/field-verification")
def field_verification_by_reference(
    reference_number: str = Query(..., min_length=1, max_length=300),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve a tender reference to its unique physical verification profile."""
    return build_field_verification_plan_by_reference(db, reference_number)
