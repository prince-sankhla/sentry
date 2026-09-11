from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Tender
from app.services.priority_queue_direct_tender import direct_field_tender_leads
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES

router = APIRouter(prefix="/api/investigations", tags=["investigations"])

@router.get("/field-tender-leads")
def field_tender_leads(db: Session = Depends(get_db)) -> dict:
    items = direct_field_tender_leads(db)
    return {"items": items, "total": len(items)}

_POTHOLE_TERMS = (
    "%pothole%", "%pot hole%", "%road surface distress%", "%surface distress%",
    "%potholes repair%", "%pothole repair%", "%patch repair%"
)

def _pothole_match():
    fields = (Tender.title, Tender.description, Tender.reference_number)
    return or_(*[field.ilike(term) for field in fields for term in _POTHOLE_TERMS])

@router.get("/tender-recommendations")
def tender_recommendations(
    pothole_limit: int = Query(100, ge=1, le=200),
    field_limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    field_items = direct_field_tender_leads(db)[:field_limit]
    rows = db.execute(
        select(Tender)
        .where(Tender.deleted_at.is_(None))
        .where(Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES))
        .where(_pothole_match())
        .order_by(Tender.published_date.desc().nullslast(), Tender.created_at.desc(), Tender.id.desc())
        .limit(pothole_limit)
    ).scalars().all()
    seen: set[str] = set(); pothole_items: list[dict] = []
    for tender in rows:
        key = str(tender.id)
        if key in seen:
            continue
        seen.add(key)
        text = " ".join(str(value or "").lower() for value in (tender.title, tender.description, tender.reference_number, tender.category))
        capabilities = ["pothole"] if any(term in text for term in ("pothole", "pot hole", "patch repair")) else []
        if any(term in text for term in ("road crack", "surface distress", "damaged road", "road repair", "patch repair")):
            capabilities.append("road_crack")
        if any(term in text for term in ("drain", "drainage", "culvert", "sewer", "manhole")):
            capabilities.append("drain")
        if "asset_text" not in capabilities:
            capabilities.append("asset_text")
        pothole_items.append({
            "tender_id": key,
            "reference_number": tender.reference_number,
            "title": tender.title,
            "procuring_entity": tender.procuring_entity,
            "category": tender.category,
            "source_name": tender.source_name,
            "source_url": tender.source_url,
            "investigation_type": "tender",
            "field_ready": True,
            "pothole_relevant": True,
            "auto_capabilities": capabilities,
            "reasons": [
                "Tender text references pothole / patch-repair road work",
                "Open the exact tender investigation before physical escalation",
            ],
        })
    return {
        "field_ready": [{**item, "title": item.get("title") or item.get("tender_title") or item.get("subject") or "", "field_ready": True} for item in field_items],
        "pothole": pothole_items,
        "totals": {"field_ready": len(field_items), "pothole": len(pothole_items)},
    }
