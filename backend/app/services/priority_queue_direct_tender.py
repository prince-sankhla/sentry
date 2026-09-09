from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tender
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES

ROOT = Path(__file__).resolve().parents[3]
PROFILE_FILE = ROOT / "sentry_field" / "data" / "demo_tenders.json"

# Audit reconstructions use explicit DB aliases because their physical profile
# identities intentionally differ from the reconstructed tender identities.
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
        value = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


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


def direct_field_tender_leads(db: Session) -> list[dict]:
    """Return every current tender that has a registered executable FIELD profile.

    The field profile catalog is authoritative for physical-verification eligibility;
    the procurement DB supplies the exact immutable tender identity used by the
    investigation flow. This includes both normal FIELD records and registered
    CAG reconstruction profiles.
    """
    rows = db.execute(
        select(Tender)
        .where(Tender.deleted_at.is_(None))
        .where(Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES))
        .order_by(Tender.created_at.desc().nullslast(), Tender.id.desc())
    ).scalars().all()
    profiles = _load_profiles()
    seen_tenders: set[str] = set()
    out: list[dict] = []

    for profile in profiles:
        profile_id = str(profile.get("id") or "").strip()
        requirements = profile.get("requirements") or []
        if not profile_id or not requirements:
            continue
        tender = next((candidate for candidate in rows if _profile_matches_tender(profile, candidate)), None)
        if tender is None or str(tender.id) in seen_tenders:
            continue
        seen_tenders.add(str(tender.id))
        capabilities: list[str] = []
        normalized_requirements: list[dict] = []
        for requirement in requirements:
            capability = str(requirement.get("capability") or "").strip()
            req_id = str(requirement.get("id") or "").strip()
            if not req_id or not capability:
                continue
            if capability not in capabilities:
                capabilities.append(capability)
            normalized_requirements.append({
                "id": req_id,
                "capability": capability,
                "label": str(requirement.get("label") or capability),
                "expected_quantity": int(requirement.get("expected_quantity") or 1),
            })
        if not normalized_requirements:
            continue
        out.append({
            "tender_id": str(tender.id),
            "reference_number": tender.reference_number,
            "source_record_id": tender.source_record_id,
            "tender_title": tender.title,
            "subject": tender.title,
            "title": tender.title,
            "procuring_entity": tender.procuring_entity,
            "category": tender.category or profile.get("category"),
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
            "field_ready": True,
            "field_profile_id": profile_id,
            "machine": profile.get("machine") or "Normal Vision Rover",
            "demo_site": profile.get("demo_site"),
            "auto_capabilities": capabilities,
            "requirements": normalized_requirements,
            "reasons": [
                "Registered SENTRY FIELD inspection profile is available for this tender",
                "Capabilities are selected automatically from the executable requirements",
            ],
        })

    return out
