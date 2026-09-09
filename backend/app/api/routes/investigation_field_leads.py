from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.priority_queue_direct_tender import direct_field_tender_leads

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("/field-tender-leads")
def field_tender_leads(db: Session = Depends(get_db)) -> dict:
    """Return stable, database-backed direct tender leads for the investigator landing page."""
    items = direct_field_tender_leads(db)
    return {"items": items, "total": len(items)}
