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
    """Return stable, database-backed direct tender leads for the investigator landing page."""
    items = direct_field_tender_leads(db)
    return {"items": items, "total": len(items)}


_POTHOLE_TERMS = (
    "%pothole%",
    "%pot hole%",
    "%road surface distress%",
    "%surface distress%",
    "%potholes repair%",
    "%pothole repair%",
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
    """Return separate recommendation buckets sourced from the live tender database.

    Field-ready records are identified by the explicit FIELD: reference convention.
    Pothole recommendations are keyword-matched over the live tender title,
    description and reference; a tender may intentionally appear in both buckets
    when it is both pothole-relevant and field-verification-ready.
    """
    field_items = direct_field_tender_leads(db)[:field_limit]

    rows = db.execute(
        select(Tender)
        .where(Tender.deleted_at.is_(None))
        .where(Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES))
        .where(_pothole_match())
        .order_by(Tender.published_date.desc().nullslast(), Tender.created_at.desc(), Tender.id.desc())
        .limit(pothole_limit)
    ).scalars().all()

    seen: set[str] = set()
    pothole_items: list[dict] = []
    for tender in rows:
        key = str(tender.id)
        if key in seen:
            continue
        seen.add(key)
        pothole_items.append(
            {
                "tender_id": key,
                "reference_number": tender.reference_number,
                "title": tender.title,
                "procuring_entity": tender.procuring_entity,
                "category": tender.category,
                "source_name": tender.source_name,
                "source_url": tender.source_url,
                "field_ready": bool((tender.reference_number or "").upper().startswith("FIELD:")),
                "pothole_relevant": True,
                "reasons": [
                    "Tender text explicitly references pothole / road-surface distress work",
                    "Open the exact tender investigation before any physical escalation",
                ],
            }
        )

    return {
        "field_ready": [
            {
                **item,
                "title": item.get("title") or item.get("tender_title") or item.get("subject") or "",
                "field_ready": True,
                "pothole_relevant": False,
            }
            for item in field_items
        ],
        "pothole": pothole_items,
        "totals": {"field_ready": len(field_items), "pothole": len(pothole_items)},
    }
