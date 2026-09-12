from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.tender import Tender
from app.services.field_verification_auto import (
    build_auto_field_verification_plan,
    build_auto_field_verification_plan_by_reference,
)

router = APIRouter(prefix="/api/investigations", tags=["field-verification"])


def _resolve_tender_id(db: Session, key: str) -> UUID:
    """Accept core UUIDs and SENTRY FIELD catalog keys without changing the FIELD UI."""
    try:
        return UUID(key)
    except ValueError:
        pass

    direct = (
        db.query(Tender)
        .filter(Tender.source_record_id == key, Tender.deleted_at.is_(None))
        .first()
    )
    if direct is not None:
        return direct.id

    # FIELD demo profiles intentionally have their own UI-safe keys (FIELD-*).
    # Resolve those keys to the corresponding core tender using the existing
    # seeded source_record_id/reference_number rather than creating another data path.
    repo_root = Path(__file__).resolve().parents[4]
    catalog = repo_root / "sentry_field" / "data" / "demo_tenders.json"
    try:
        rows = json.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        rows = []

    profile = next(
        (row for row in rows if str(row.get("id")) == key or str(row.get("tender_id")) == key),
        None,
    )
    if profile:
        source_record_id = str(profile.get("tender_id") or "").strip()
        reference_number = str(profile.get("reference_number") or "").strip()
        query = db.query(Tender).filter(Tender.deleted_at.is_(None))
        if source_record_id:
            matched = query.filter(Tender.source_record_id == source_record_id).first()
            if matched is not None:
                return matched.id
        if reference_number:
            matched = query.filter(Tender.reference_number == reference_number).first()
            if matched is not None:
                return matched.id

    raise HTTPException(
        404,
        "FIELD tender is not mapped to a core SENTRY tender. Run scripts/seed_field_demo_tenders.py first.",
    )


@router.get("/tenders/{tender_id}/field-verification")
def field_verification(tender_id: str, db: Session = Depends(get_db)) -> dict:
    """Resolve a core UUID or a SENTRY FIELD demo key to an executable FIELD plan."""
    resolved_id = _resolve_tender_id(db, tender_id)
    return build_auto_field_verification_plan(db, resolved_id)


@router.get("/field-verification")
def field_verification_by_reference(
    reference_number: str = Query(..., min_length=1, max_length=300),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve any tender reference to an executable SENTRY FIELD plan."""
    return build_auto_field_verification_plan_by_reference(db, reference_number)
