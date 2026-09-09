from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tender
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES


def direct_field_tender_leads(db: Session) -> list[dict]:
    """Return current field-ready tenders with stable identity fields.

    ``reference_number`` is the investigation lookup key; ``tender_id`` is the
    immutable database identity. Both are returned so the UI never has to use a
    human-readable title as the lookup key.
    """
    rows = db.execute(
        select(Tender)
        .where(Tender.deleted_at.is_(None))
        .where(Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES))
        .where(Tender.reference_number.ilike("FIELD:%"))
        .order_by(Tender.created_at.desc())
    ).scalars().all()
    seen: set[str] = set()
    out: list[dict] = []
    for tender in rows:
        key = (tender.source_record_id or tender.reference_number or str(tender.id)).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "tender_id": str(tender.id),
            "reference_number": tender.reference_number,
            "source_record_id": tender.source_record_id,
            "tender_title": tender.title,
            "subject": tender.title,
            "title": tender.title,
            "procuring_entity": tender.procuring_entity,
            "category": tender.category,
            "source_name": tender.source_name,
            "source_url": tender.source_url,
            "investigation_type": "tender",
            "priority": "review",
            "risk_level": "insufficient",
            "typology_count": 0,
            "linked_records": 1,
            "evidence_strength": "high" if tender.source_url else "limited",
            "evidence_completeness": 1.0 if tender.source_url else 0.0,
            "primary_pattern": "Field verification candidate",
            "reasons": [
                "Field-verification-ready tender record in the current procurement database",
                "Direct tender lead — investigate the record before physical verification",
            ],
        })
    return out
