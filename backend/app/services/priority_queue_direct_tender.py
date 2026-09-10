from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tender
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES

FIELD_REFERENCE_PATTERN = "FIELD:%"

_PHYSICAL_CAPABILITY_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("pothole", ("pothole", "pot hole", "potholes")),
    ("road_crack", ("road crack", "surface distress", "road surface distress", "damaged road", "road repair", "regrading of the approach roads")),
    ("drain", ("drain", "drainage", "culvert", "storm water", "sewer line", "sewerage", "manhole", "desilting")),
    ("streetlight", ("street light", "streetlight", "led light", "led street", "lighting pole", "luminary")),
    ("cctv_camera", ("cctv", "camera system", "surveillance system")),
    ("signboard", ("sign board", "signboard")),
    ("solar_panel", ("solar panel", "solar power", "solar energy")),
    ("asset_qr", ("asset qr", "qr code", "qr/")),
)


def _physical_capabilities(tender: Tender) -> list[str]:
    text = " ".join(part.lower() for part in (tender.title or "", tender.description or "", tender.reference_number or "", tender.category or "") if part)
    capabilities: list[str] = []
    for capability, terms in _PHYSICAL_CAPABILITY_TERMS:
        if any(term in text for term in terms):
            capabilities.append(capability)
    return capabilities


def _priority_score(tender: Tender, capabilities: list[str], profile: dict | None) -> int:
    text = " ".join(value.lower() for value in (tender.title, tender.description, tender.reference_number, tender.procuring_entity) if value)
    score = 0
    if "dharmagarh" in text:
        score += 300
    if "pothole" in capabilities:
        score += 100
    if "road_crack" in capabilities:
        score += 80
    if "drain" in capabilities:
        score += 70
    if profile is not None:
        score += 40
    if tender.source_url:
        score += 5
    return score


def direct_field_tender_leads(db: Session) -> list[dict]:
    """Return every current DB tender that is plausibly inspectable in the field."""
    rows = db.execute(
        select(Tender)
        .where(Tender.deleted_at.is_(None))
        .where(Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES))
        .order_by(Tender.created_at.desc().nullslast(), Tender.id.desc())
    ).scalars().all()

    import json
    from pathlib import Path

    profile_file = Path(__file__).resolve().parents[3] / "sentry_field" / "data" / "demo_tenders.json"
    try:
        profiles = json.loads(profile_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        profiles = []
    profiles = profiles if isinstance(profiles, list) else []

    def profile_for_tender(tender: Tender) -> dict | None:
        source = (tender.source_record_id or "").strip()
        reference = (tender.reference_number or "").strip()
        for profile in profiles:
            profile_id = str(profile.get("id") or "").strip()
            profile_tender_id = str(profile.get("tender_id") or "").strip()
            profile_reference = str(profile.get("reference_number") or "").strip()
            if source == profile_tender_id or reference == profile_reference:
                return profile
            if profile_id == "FIELD-AUDIT-DELHI-CWG" and reference == "AUDIT:2026_CAG_DELHI_CWG_STREETLIGHT":
                return profile
            if profile_id == "FIELD-AUDIT-DHANBAD-LED" and reference == "AUDIT:2026_CAG_DHANBAD_LED":
                return profile
        return None

    seen: set[str] = set()
    out: list[dict] = []
    for tender in rows:
        capabilities = _physical_capabilities(tender)
        profile = profile_for_tender(tender)
        explicit_field = (tender.reference_number or "").upper().startswith("FIELD:")
        if not capabilities and profile is None and not explicit_field:
            continue
        key = str(tender.id)
        if key in seen:
            continue
        seen.add(key)
        requirements: list[dict] = []
        profile_caps: list[str] = []
        if profile:
            for item in profile.get("requirements") or []:
                capability = str(item.get("capability") or "").strip()
                req_id = str(item.get("id") or "").strip()
                if not capability or not req_id:
                    continue
                if capability not in profile_caps:
                    profile_caps.append(capability)
                requirements.append({"id": req_id, "capability": capability, "label": str(item.get("label") or capability), "expected_quantity": int(item.get("expected_quantity") or 1)})
        auto_capabilities = profile_caps or capabilities or ["asset_text"]
        out.append({
            "tender_id": key,
            "reference_number": tender.reference_number,
            "source_record_id": tender.source_record_id,
            "tender_title": tender.title,
            "subject": tender.title,
            "title": tender.title,
            "procuring_entity": tender.procuring_entity,
            "category": tender.category or (profile or {}).get("category"),
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
            "field_profile_id": (profile or {}).get("id"),
            "mission_ready": True,
            "machine": (profile or {}).get("machine") or "Normal Vision Rover",
            "demo_site": (profile or {}).get("demo_site"),
            "auto_capabilities": auto_capabilities,
            "requirements": requirements,
            "reasons": ["Tender contains physical work or asset signals that can be inspected on site", "Capabilities are inferred from the procurement record; registered requirements are preferred when available"],
            "field_priority_score": _priority_score(tender, auto_capabilities, profile),
        })
    out.sort(key=lambda item: (-int(item.get("field_priority_score") or 0), item.get("title") or "", item.get("tender_id") or ""))
    return out
