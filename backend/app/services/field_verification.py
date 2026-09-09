from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tender import Tender

ROOT = Path(__file__).resolve().parents[3]
PROFILE_FILE = ROOT / "sentry_field" / "data" / "demo_tenders.json"

# Explicit aliases bridge historical/audit reconstruction DB identities to their
# registered physical-verification profiles without relying on human-readable
# title matching.
PROFILE_DB_ALIASES: dict[str, tuple[str, ...]] = {
    "FIELD-AUDIT-DELHI-CWG": (
        "AUDIT:2026_CAG_DELHI_CWG_STREETLIGHT",
        "CAG_CWG2010_DELHI_STREETLIGHT",
    ),
    "FIELD-AUDIT-DHANBAD-LED": (
        "AUDIT:2026_CAG_DHANBAD_LED",
        "CAG_JHARKHAND_DHANBAD_LED",
    ),
}


def _load_profiles() -> list[dict]:
    try:
        rows = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, f"Field verification profile catalog unavailable: {exc}") from exc
    if not isinstance(rows, list):
        raise HTTPException(500, "Field verification profile catalog must be a JSON list")
    return rows


def _profile_key(value: str | None) -> str:
    return (value or "").strip().removeprefix("FIELD:")


def _profile_matches_tender(profile: dict, tender: Tender) -> bool:
    source_record_id = (tender.source_record_id or "").strip()
    reference = (tender.reference_number or "").strip()
    profile_id = str(profile.get("id") or "").strip()
    profile_tender_id = str(profile.get("tender_id") or "").strip()
    profile_reference = str(profile.get("reference_number") or "").strip()
    aliases = PROFILE_DB_ALIASES.get(profile_id, ())
    return (
        source_record_id in aliases
        or reference in aliases
        or _profile_key(profile_tender_id) == _profile_key(source_record_id)
        or profile_reference == reference
        or reference == f"FIELD:{profile_tender_id}"
        or source_record_id == profile_tender_id
    )


def _profile_for_tender(tender: Tender) -> dict:
    profile = next(
        (row for row in _load_profiles() if _profile_matches_tender(row, tender)),
        None,
    )
    if profile is None:
        raise HTTPException(404, "No physical verification profile is registered for this tender")
    return profile


def _plan_payload(tender: Tender, profile: dict) -> dict:
    requirements = [
        {
            "id": str(item.get("id")),
            "capability": str(item.get("capability")),
            "label": str(item.get("label")),
            "expected_quantity": int(item.get("expected_quantity") or 1),
        }
        for item in profile.get("requirements", [])
        if item.get("id") and item.get("capability")
    ]
    if not requirements:
        raise HTTPException(422, "Physical verification profile has no executable requirements")
    return {
        "tender": {
            "id": str(tender.id),
            "reference_number": tender.reference_number,
            "title": tender.title,
            "source_record_id": tender.source_record_id,
            "source_url": tender.source_url,
            "procuring_entity": tender.procuring_entity,
        },
        "verification_required": True,
        "profile_id": profile.get("id"),
        "field_tender_key": profile.get("id"),
        "machine": profile.get("machine") or "Normal Vision Rover",
        "demo_site": profile.get("demo_site"),
        "category": profile.get("category"),
        "requirements": requirements,
        "verification_notes": profile.get("verification_notes"),
        "source_profile_verified_on": profile.get("source_verified_on"),
    }


def build_field_verification_plan(db: Session, tender_id: UUID) -> dict:
    tender = db.get(Tender, tender_id)
    if tender is None or tender.deleted_at is not None:
        raise HTTPException(404, "Tender not found")
    return _plan_payload(tender, _profile_for_tender(tender))


def build_field_verification_plan_by_reference(db: Session, reference_number: str) -> dict:
    reference = reference_number.strip()
    if not reference:
        raise HTTPException(400, "reference_number is required")
    rows = (
        db.query(Tender)
        .filter(Tender.reference_number == reference, Tender.deleted_at.is_(None))
        .all()
    )
    if len(rows) == 0:
        raise HTTPException(404, "Tender not found")
    if len(rows) > 1:
        rows = [row for row in rows if (row.source_record_id or "").startswith("FIELD:")]
    if len(rows) != 1:
        raise HTTPException(409, "Reference number does not uniquely identify a tender")
    tender = rows[0]
    return _plan_payload(tender, _profile_for_tender(tender))
