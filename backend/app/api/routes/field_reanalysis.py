from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
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


def _ensure_store(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS field_verifications (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tender_id UUID NOT NULL REFERENCES tenders(id),
                version INTEGER NOT NULL,
                mission_id VARCHAR(200) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'verified',
                submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                requirements JSONB NOT NULL,
                observations JSONB NOT NULL,
                result JSONB NOT NULL,
                supersedes_id UUID NULL REFERENCES field_verifications(id),
                UNIQUE (tender_id, version)
            )
            """
        )
    )
    db.execute(text("CREATE INDEX IF NOT EXISTS idx_field_verifications_tender ON field_verifications(tender_id)"))
    db.commit()


def _latest_verification(db: Session, tender_id: UUID) -> dict[str, Any] | None:
    _ensure_store(db)
    row = db.execute(
        text(
            """
            SELECT id::text, version, mission_id, status, submitted_at, updated_at,
                   jsonb_array_length(observations) AS observation_count,
                   COALESCE((result->'summary'->>'evidence_count')::int, 0) AS evidence_count,
                   COALESCE((result->'summary'->>'gps_evidence_count')::int, 0) AS gps_evidence_count
            FROM field_verifications
            WHERE tender_id = :tender_id
            ORDER BY version DESC
            LIMIT 1
            """
        ),
        {"tender_id": str(tender_id)},
    ).mappings().first()
    if not row:
        return None
    return {
        "id": row["id"],
        "version": row["version"],
        "status": row["status"],
        "mission_id": row["mission_id"],
        "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "observation_count": row["observation_count"],
        "evidence_count": row["evidence_count"],
        "gps_evidence_count": row["gps_evidence_count"],
    }


def _verification_history(db: Session, tender_id: UUID) -> list[dict[str, Any]]:
    _ensure_store(db)
    rows = db.execute(
        text(
            """
            SELECT id::text, version, mission_id, status, submitted_at, updated_at,
                   jsonb_array_length(observations) AS observation_count,
                   COALESCE((result->'summary'->>'evidence_count')::int, 0) AS evidence_count,
                   COALESCE((result->'summary'->>'gps_evidence_count')::int, 0) AS gps_evidence_count
            FROM field_verifications
            WHERE tender_id = :tender_id
            ORDER BY version ASC
            """
        ),
        {"tender_id": str(tender_id)},
    ).mappings().all()
    return [
        {
            "id": row["id"],
            "version": row["version"],
            "status": row["status"],
            "mission_id": row["mission_id"],
            "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "observation_count": row["observation_count"],
            "evidence_count": row["evidence_count"],
            "gps_evidence_count": row["gps_evidence_count"],
        }
        for row in rows
    ]


def _save_verification(db: Session, tender_id: UUID, request: FieldReanalysisRequest, result: dict[str, Any]) -> dict[str, Any]:
    _ensure_store(db)
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": str(tender_id)})
    latest = db.execute(
        text("SELECT id, version FROM field_verifications WHERE tender_id = :tender_id ORDER BY version DESC LIMIT 1"),
        {"tender_id": str(tender_id)},
    ).mappings().first()
    version = int(latest["version"]) + 1 if latest else 1
    row = db.execute(
        text(
            """
            INSERT INTO field_verifications
              (tender_id, version, mission_id, status, requirements, observations, result, supersedes_id)
            VALUES
              (:tender_id, :version, :mission_id, 'verified', CAST(:requirements AS jsonb),
               CAST(:observations AS jsonb), CAST(:result AS jsonb), :supersedes_id)
            RETURNING id::text, version, submitted_at, updated_at
            """
        ),
        {
            "tender_id": str(tender_id),
            "version": version,
            "mission_id": request.mission_id,
            "requirements": json.dumps([item.model_dump() for item in request.requirements]),
            "observations": json.dumps([item.model_dump() for item in request.observations]),
            "result": json.dumps(result),
            "supersedes_id": str(latest["id"]) if latest else None,
        },
    ).mappings().one()
    db.commit()
    return {
        "id": row["id"],
        "version": row["version"],
        "status": "verified",
        "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        "supersedes_version": latest["version"] if latest else None,
    }


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
        "signboard": ["Compare visible signage with the approved sign schedule and completion record"],
        "solar_panel": [
            "Reconcile visible installations with the approved asset schedule",
            "Check commissioning and electrical-generation test records",
        ],
    }
    return checks.get(capability, ["Verify the tender requirement against the approved site-wise work/asset records"])


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
            discrepancies.append({
                "requirement_id": requirement.id,
                "capability": requirement.capability,
                "label": requirement.label or requirement.capability,
                "expected": expected,
                "observed": observed,
                "gap": gap,
                "signal": "discrepancy",
            })
        for check in _checks_for(requirement.capability):
            if check not in next_checks:
                next_checks.append(check)
        for explanation in _explanations_for(requirement.capability):
            if explanation not in explanations:
                explanations.append(explanation)

    evidence_count = sum(1 for item in request.observations if item.frame_url)
    gps_count = sum(1 for item in request.observations if item.gps and item.gps.get("lat") is not None and item.gps.get("lon") is not None)
    status = "discrepancy_review" if discrepancies else "no_observed_shortfall"

    result = {
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
    result["verification"] = _save_verification(db, tender_id, request, result)
    return result


@router.get("/tenders/{tender_id}/field-verification-status")
def field_verification_status(tender_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    tender = db.get(Tender, tender_id)
    if tender is None or tender.deleted_at is not None:
        raise HTTPException(404, "Tender not found")
    latest = _latest_verification(db, tender_id)
    return {
        "tender_id": str(tender_id),
        "verified": bool(latest),
        "latest": latest,
        "history": _verification_history(db, tender_id),
        "deletion_allowed": False,
        "update_allowed": True,
    }
