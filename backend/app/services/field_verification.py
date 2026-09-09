from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tender import Tender

ROOT = Path(__file__).resolve().parents[3]
PROFILE_FILE = ROOT / "sentry_field" / "data" / "demo_tenders.json"


def _load_profiles() -> list[dict]:
    try:
        rows = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, f"Field verification profile catalog unavailable: {exc}") from exc
    if not isinstance(rows, list):
        raise HTTPException(500, "Field verification profile catalog must be a JSON list")
    return rows


def _profile_key(value: str | None) -> str:
    value = (value or "").strip()
    return value.removeprefix("FIELD:")


def build_field_verification_plan(db: Session, tender_id: UUID) -> dict:
    tender = db.get(Tender, tender_id)
    if tender is None or tender.deleted_at is not None:
        raise HTTPException(404, "Tender not found")

    source_key = _profile_key(tender.source_record_id)
    candidates = _load_profiles()
    profile = next(
        (
            row
            for row in candidates
            if _profile_key(str(row.get("tender_id"))) == source_key
            or str(row.get("reference_number", "")).strip() == (tender.reference_number or "").strip()
        ),
        None,
    )
    if profile is None:
        raise HTTPException(404, "No physical verification profile is registered for this tender")

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
        "machine": profile.get("machine") or "Normal Vision Rover",
        "demo_site": profile.get("demo_site"),
        "category": profile.get("category"),
        "requirements": requirements,
        "verification_notes": profile.get("verification_notes"),
        "source_profile_verified_on": profile.get("source_verified_on"),
    }
