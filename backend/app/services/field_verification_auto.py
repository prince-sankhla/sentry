from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.services.field_verification import build_field_verification_plan, build_field_verification_plan_by_reference

CAPABILITY_LABELS = {
    "pothole": "Pothole / road-surface condition",
    "road_crack": "Road crack / surface distress",
    "drain": "Drain / manhole / culvert condition",
    "streetlight": "Streetlight / lighting asset",
    "cctv_camera": "CCTV / surveillance asset",
    "signboard": "Road sign / signboard",
    "solar_panel": "Solar / PV asset",
    "asset_text": "Asset identification / OCR",
}

RULES = (
    ("pothole", ("pothole", "pot hole", "patch repair")),
    ("road_crack", ("road crack", "crack in road", "surface crack", "cracks", "patch repair")),
    ("drain", ("drain", "drainage", "sewer", "manhole", "culvert", "desilting", "sewage")),
    ("streetlight", ("street light", "streetlight", "led light", "led street", "light pole", "lighting", "ccms")),
    ("cctv_camera", ("cctv", "camera system", "surveillance", "video analytic")),
    ("signboard", ("signboard", "road sign", "signage")),
    ("solar_panel", ("solar", "photovoltaic", "pv panel")),
)


def auto_capabilities_for_tender(tender: Tender) -> list[str]:
    text = " ".join(
        value.lower()
        for value in (tender.title, tender.description, tender.reference_number, tender.category)
        if value
    )
    found: list[str] = []
    for capability, terms in RULES:
        if any(term in text for term in terms):
            found.append(capability)
    if "asset_text" not in found:
        found.append("asset_text")
    return found


def _synthetic_plan(tender: Tender) -> dict:
    capabilities = auto_capabilities_for_tender(tender)
    return {
        "id": str(tender.id),
        "reference_number": tender.reference_number,
        "title": tender.title,
        "source_record_id": tender.source_record_id,
        "source_url": tender.source_url,
        "procuring_entity": tender.procuring_entity,
        "tender": {
            "id": str(tender.id),
            "reference_number": tender.reference_number,
            "title": tender.title,
            "source_record_id": tender.source_record_id,
            "source_url": tender.source_url,
            "procuring_entity": tender.procuring_entity,
        },
        "verification_required": True,
        "profile_id": f"AUTO:{tender.id}",
        "field_tender_key": str(tender.id),
        "machine": "Normal Vision Rover",
        "demo_site": None,
        "category": tender.category or "Physical procurement asset verification",
        "requirements": [
            {
                "id": f"AUTO-{capability}",
                "capability": capability,
                "label": CAPABILITY_LABELS[capability],
                "expected_quantity": 1,
            }
            for capability in capabilities
        ],
        "verification_notes": "Auto-planned from tender text. Camera inference provides visual observations; physical measurements and non-visual characteristics require on-site verification.",
        "source_profile_verified_on": None,
        "auto_generated": True,
    }


def build_auto_field_verification_plan(db: Session, tender_id) -> dict:
    try:
        return build_field_verification_plan(db, tender_id)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        tender = db.get(Tender, tender_id)
        if tender is None or tender.deleted_at is not None:
            raise
        return _synthetic_plan(tender)


def build_auto_field_verification_plan_by_reference(db: Session, reference_number: str) -> dict:
    try:
        return build_field_verification_plan_by_reference(db, reference_number)
    except HTTPException as exc:
        if exc.status_code not in {404, 409}:
            raise
        reference = reference_number.strip()
        rows = db.query(Tender).filter(Tender.reference_number == reference, Tender.deleted_at.is_(None)).all()
        if len(rows) != 1:
            raise
        return _synthetic_plan(rows[0])
