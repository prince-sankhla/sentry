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


def _field_catalog_profile(key: str) -> dict | None:
    repo_root = Path(__file__).resolve().parents[4]
    catalog = repo_root / "sentry_field" / "data" / "demo_tenders.json"
    try:
        rows = json.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(rows, list):
        return None
    return next(
        (
            row
            for row in rows
            if str(row.get("id")) == key or str(row.get("tender_id")) == key
        ),
        None,
    )


def _hydrate_field_profile(db: Session, profile: dict) -> Tender | None:
    """Materialize a missing FIELD demo profile into the existing core tender table.

    This is idempotent: an existing source_record_id/reference_number is reused.
    It keeps FIELD on the same core SENTRY tender model instead of introducing a
    parallel persistence path just for physical-verification demos.
    """
    source_record_id = str(profile.get("tender_id") or "").strip()
    reference_number = str(profile.get("reference_number") or "").strip()
    if not source_record_id and not reference_number:
        return None

    query = db.query(Tender).filter(Tender.deleted_at.is_(None))
    tender = None
    if source_record_id:
        tender = query.filter(Tender.source_record_id == source_record_id).first()
    if tender is None and reference_number:
        tender = query.filter(Tender.reference_number == reference_number).first()

    description = (
        f"SENTRY FIELD demo profile. Official source: {profile.get('source_name') or ''}. "
        f"Contract location: {profile.get('contract_location') or ''}. "
        f"Field demo site: {profile.get('demo_site') or ''}. "
        f"Verification policy: {profile.get('verification_notes') or ''}"
    )

    if tender is None:
        tender = Tender(reference_number=reference_number or source_record_id)
        db.add(tender)

    tender.title = str(profile.get("title") or "SENTRY FIELD physical verification")[:500]
    tender.description = description
    tender.procuring_entity = profile.get("source_name")
    tender.category = profile.get("category")
    tender.geography = str(profile.get("contract_location") or "")[:100]
    tender.source_name = profile.get("source_name")
    tender.source_record_id = source_record_id or None
    tender.source_url = profile.get("source_url")
    tender.currency = "INR"
    db.flush()
    db.commit()
    db.refresh(tender)
    return tender


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

    profile = _field_catalog_profile(key)
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

        # The FIELD catalog is part of the checked-in SENTRY product, so hydrate
        # the missing profile into the existing core tender store on first use.
        hydrated = _hydrate_field_profile(db, profile)
        if hydrated is not None:
            return hydrated.id

    raise HTTPException(
        404,
        "FIELD tender could not be resolved to a core SENTRY tender.",
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
