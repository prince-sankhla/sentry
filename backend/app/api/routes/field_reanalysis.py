from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.tender import Tender

router = APIRouter(prefix="/api/investigations", tags=["field-reanalysis"])


class FieldRequirement(BaseModel):
    id: str
    capability: str
    label: str = ""
    expected_quantity: int = Field(default=1, ge=0)


class FieldObservation(BaseModel):
    capability: str = ""
    observation: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)
    track_id: str | None = None
    frame_url: str | None = None
    gps: dict[str, Any] | None = None
    observed_at: float | None = None


class FieldReanalysisRequest(BaseModel):
    tender_id: str
    mission_id: str = Field(min_length=1, max_length=200)
    requirements: list[FieldRequirement] = []
    observations: list[FieldObservation] = []


def _observed_count(observations: list[FieldObservation], capability: str) -> int:
    rows = [item for item in observations if item.capability.strip().lower() == capability.strip().lower()]
    unique = {item.track_id for item in rows if item.track_id}
    return len(unique) if unique else len(rows)


def _checks_for(capability: str) -> list[str]:
    checks = {
        "pothole": [
            "Review site-wise road condition records and approved repair quantities",
            "Confirm field coverage and inaccessible locations before reconciling quantity",
        ],
        "road_crack": [
            "Compare the observed road section with the contracted work package and site plan",
            "Verify measurement-book entries and completion/acceptance records",
        ],
        "drain": [
            "Compare visible drain/manhole coverage with the site-wise work list",
            "Verify measurements, completion certificates and approved variations",
        ],
        "streetlight": [
            "Reconcile the visible asset list against the supplied/installed quantity",
            "Check maintenance outages and electrical test records before concluding non-functionality",
        ],
        "cctv_camera": [
            "Reconcile visible camera positions against the approved deployment list",
            "Check commissioning/acceptance and video-analytics test records",
        ],
        "signboard": [
            "Compare visible signage with the approved sign schedule and completion record",
        ],
        "solar_panel": [
            "Reconcile visible installations with the approved asset schedule",
            "Check commissioning and electrical-generation test records",
        ],
    }
    return checks.get(capability, [
        "Verify the tender requirement against the approved site-wise work/asset records",
    ])


def _explanations_for(capability: str) -> list[str]:
    generic = [
        "Approved variation or scope change may explain a quantity difference",
        "Maintenance, outage, obstruction or inaccessible coverage may affect a visual count",
        "A current visual observation does not by itself establish non-compliance or fraud",
    ]
    if capability == "streetlight":
        return generic + ["Electrical status requires appropriate electrical testing; RGB vision is observational"]
    if capability in {"road_crack", "pothole"}:
        return generic + ["Road-condition observations can change over time and should be reconciled with inspection dates"]
    return generic


@router.post("/field-reanalysis")
def field_reanalysis(request: FieldReanalysisRequest, db: Session = Depends(get_db)) -> dict:
    try:
        tender_id = UUID(request.tender_id)
    except ValueError as exc:
        raise HTTPException(400, "tender_id must be a valid UUID") from exc

    tender = db.get(Tender, tender_id)
    if tender is None or tender.deleted_at is not None:
        raise HTTPException(404, "Tender not found")

    discrepancies: list[dict[str, Any]] = []
    next_checks: list[str] = []
    explanations: list[str] = []
    observed_total = 0
    expected_total = 0

    for requirement in request.requirements:
        expected = requirement.expected_quantity
        observed = _observed_count(request.observations, requirement.capability)
        gap = max(0, expected - observed)
        expected_total += expected
        observed_total += min(expected, observed)
        if gap > 0:
            discrepancies.append(
                {
                    "requirement_id": requirement.id,
                    "capability": requirement.capability,
                    "label": requirement.label or requirement.capability,
                    "expected": expected,
                    "observed": observed,
                    "gap": gap,
                    "signal": "discrepancy",
                }
            )
        for check in _checks_for(requirement.capability):
            if check not in next_checks:
                next_checks.append(check)
        for explanation in _explanations_for(requirement.capability):
            if explanation not in explanations:
                explanations.append(explanation)

    evidence_count = sum(1 for item in request.observations if item.frame_url)
    gps_count = sum(1 for item in request.observations if item.gps and item.gps.get("lat") is not None and item.gps.get("lon") is not None)
    status = "discrepancy_review" if discrepancies else "no_observed_shortfall"

    return {
        "status": status,
        "mission_id": request.mission_id,
        "tender": {
            "id": str(tender.id),
            "reference_number": tender.reference_number,
            "title": tender.title,
            "procuring_entity": tender.procuring_entity,
        },
        "summary": {
            "expected_total": expected_total,
            "observed_total": observed_total,
            "gap_total": max(0, expected_total - observed_total),
            "evidence_count": evidence_count,
            "gps_evidence_count": gps_count,
            "observation_count": len(request.observations),
        },
        "discrepancies": discrepancies,
        "possible_explanations": explanations[:8],
        "next_checks": next_checks[:10],
        "guardrail": "SENTRY reports a verification discrepancy signal, not a fraud finding. Investigator review is required.",
    }
