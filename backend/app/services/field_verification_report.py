from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.schemas.field_verification import FieldObservation, FieldReanalysisRequest, FieldRequirement


def _observed_count(observations: list[FieldObservation], capability: str) -> int:
    rows = [
        item
        for item in observations
        if item.capability.strip().lower() == capability.strip().lower()
    ]
    unique = {item.track_id for item in rows if item.track_id}
    return len(unique) if unique else len(rows)


def _label(requirement: FieldRequirement) -> str:
    return requirement.label.strip() or requirement.capability.replace("_", " ")


def _evidence_quality(observations: list[FieldObservation]) -> dict[str, Any]:
    total = len(observations)
    if total == 0:
        return {
            "score": 0,
            "tier": "limited",
            "frame_coverage": 0.0,
            "gps_coverage": 0.0,
            "confidence_coverage": 0.0,
            "limitations": ["No field observations were returned by the mission."],
        }

    frame_coverage = sum(1 for item in observations if item.frame_url) / total
    gps_coverage = sum(
        1
        for item in observations
        if item.gps
        and item.gps.get("lat") is not None
        and item.gps.get("lon") is not None
    ) / total
    confidence_rows = [item.confidence for item in observations if item.confidence is not None]
    confidence_coverage = len(confidence_rows) / total

    score = round(
        100
        * (
            0.45 * frame_coverage
            + 0.35 * gps_coverage
            + 0.20 * confidence_coverage
        )
    )
    tier = "high" if score >= 80 else "moderate" if score >= 55 else "limited"
    limitations: list[str] = []
    if frame_coverage < 1:
        limitations.append("Not every returned observation has a preserved frame URL.")
    if gps_coverage < 1:
        limitations.append("Not every returned observation has GPS coordinates.")
    if confidence_coverage < 1:
        limitations.append("Not every observation carries a model/operator confidence value.")
    limitations.append(
        "Coverage score reflects returned observation provenance only; it does not prove that every site location was physically traversed."
    )
    return {
        "score": score,
        "tier": tier,
        "frame_coverage": round(frame_coverage, 3),
        "gps_coverage": round(gps_coverage, 3),
        "confidence_coverage": round(confidence_coverage, 3),
        "limitations": limitations,
    }


def _next_actions(
    request: FieldReanalysisRequest,
    result: dict[str, Any],
    evidence_quality: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    observations = request.observations
    summary = result["summary"]
    discrepancies = result.get("discrepancies", [])

    def add(
        action_id: str,
        title: str,
        owner: str,
        priority: str,
        rationale: str,
        evidence_needed: list[str],
        completion_condition: str,
    ) -> None:
        if any(item["id"] == action_id for item in actions):
            return
        actions.append(
            {
                "id": action_id,
                "title": title,
                "owner": owner,
                "priority": priority,
                "rationale": rationale,
                "evidence_needed": evidence_needed,
                "completion_condition": completion_condition,
            }
        )

    missing_provenance = (
        evidence_quality["frame_coverage"] < 1
        or evidence_quality["gps_coverage"] < 1
    )
    if not observations or missing_provenance:
        add(
            "verify_field_coverage",
            "Verify mission coverage and provenance",
            "FIELD operator / investigator",
            "P1",
            "The returned evidence does not prove complete physical coverage of all requested locations.",
            [
                "Mission route or site-coverage log",
                "Missing frame/GPS records for returned observations",
            ],
            "The investigator can reconcile each required site/asset to a timestamped, location-linked observation or document the coverage exception.",
        )

    if discrepancies:
        add(
            "reconcile_expected_quantity",
            "Reconcile expected vs observed quantity",
            "Investigator",
            "P1",
            "FIELD observed fewer units/conditions than the tender requirement for at least one capability.",
            [
                "Approved site-wise work or asset list",
                "Measurement book / completion record",
                "Approved variation or scope-change documents",
            ],
            "Every reported gap has a documented explanation or a reconciled asset/work-item mapping.",
        )

        capabilities = {item["capability"] for item in discrepancies}
        if capabilities & {"streetlight", "cctv_camera", "solar_panel"}:
            add(
                "technical_acceptance_check",
                "Validate asset commissioning and technical status",
                "Technical verifier",
                "P1",
                "Visual presence does not establish commissioning, functionality, or electrical performance.",
                [
                    "Commissioning / acceptance certificate",
                    "Relevant electrical or system test record",
                    "Maintenance / outage log where applicable",
                ],
                "Technical status is confirmed independently of visual observation.",
            )

        if "asset_text" in capabilities:
            add(
                "asset_identity_reconcile",
                "Reconcile asset identities",
                "Investigator / records desk",
                "P2",
                "Asset identity evidence can connect physical observations to the procurement schedule but was not sufficient to close the reconciliation.",
                [
                    "Asset register or site-wise asset IDs",
                    "OCR/QR/barcode capture and source records",
                ],
                "Observed assets can be mapped to the approved asset schedule without unresolved identity conflicts.",
            )

        if capabilities & {"pothole", "road_crack", "drain"}:
            add(
                "retrieve_work_measurements",
                "Retrieve work measurement records",
                "Procurement / works records desk",
                "P1",
                "Physical condition counts should be reconciled against the contracted work package and dated measurements.",
                [
                    "Measurement book entries",
                    "Completion / acceptance certificate",
                    "Approved site plan and variation orders",
                ],
                "The measured work scope explains the field observation or identifies a documented exception.",
            )
    elif observations:
        add(
            "investigator_closure_review",
            "Perform investigator closure review",
            "Investigator",
            "P2",
            "FIELD did not observe a shortfall within the returned observations, but physical verification is not an automatic compliance determination.",
            [
                "Field Verification Report",
                "Original procurement finding and supporting documents",
            ],
            "An investigator records whether the procurement question is resolved, remains open, or needs another evidence source.",
        )

    if evidence_quality["tier"] == "limited":
        add(
            "repeat_field_capture",
            "Repeat field capture with stronger provenance",
            "FIELD operator",
            "P1",
            "Evidence quality is limited for reliable reconciliation.",
            [
                "Stable frame capture for each observation",
                "GPS-linked timestamps",
                "Mission coverage record",
            ],
            "The replacement mission reaches at least moderate evidence quality with location-linked media.",
        )

    return actions[:8]


def build_field_verification_report(
    request: FieldReanalysisRequest,
    result: dict[str, Any],
    *,
    verification_version: int | None = None,
) -> dict[str, Any]:
    """Build a durable, deterministic FIELD closeout report.

    This layer does not declare fraud, compliance, or guilt. It records what
    the physical mission established, what remains unresolved, and which
    evidence/action should be pursued next.
    """
    observations = request.observations
    requirements = request.requirements
    summary = result["summary"]
    discrepancies = result.get("discrepancies", [])
    quality = _evidence_quality(observations)

    if not observations or summary["evidence_count"] == 0:
        outcome = "INCONCLUSIVE"
        lifecycle_state = "EVIDENCE_REVIEW_REQUIRED"
    elif discrepancies:
        outcome = "PARTIALLY_VERIFIED"
        lifecycle_state = "RECONCILIATION_REQUIRED"
    else:
        outcome = "CORROBORATED"
        lifecycle_state = "INVESTIGATOR_CLOSURE_REVIEW"

    established: list[str] = []
    for requirement in requirements:
        observed = _observed_count(observations, requirement.capability)
        expected = requirement.expected_quantity
        label = _label(requirement)
        if observed >= expected:
            established.append(
                f"FIELD returned {observed} observed {label} against an expected quantity of {expected}; no observed shortfall was recorded for this requirement."
            )
        else:
            established.append(
                f"FIELD returned {observed} observed {label} against an expected quantity of {expected}; the unresolved gap is {expected - observed}."
            )

    unresolved: list[str] = []
    for item in discrepancies:
        unresolved.append(
            f"What explains the {item['gap']} gap for {item['label']}: scope change, incomplete coverage, missing asset records, maintenance/outage, or another documented reason?"
        )
    if quality["gps_coverage"] < 1:
        unresolved.append("Was every returned observation tied to the correct physical location?")
    if not observations:
        unresolved.append("No physical observations were returned, so the verification question remains untested.")
    unresolved.append(
        "Does the procurement record (site-wise list, measurement book, completion/acceptance record, or variation) reconcile the field evidence?"
    )

    evidence_items: list[dict[str, Any]] = []
    for index, item in enumerate(observations, start=1):
        payload = {
            "mission_id": request.mission_id,
            "observation_index": index,
            "capability": item.capability,
            "observation": item.observation,
            "track_id": item.track_id,
            "frame_url": item.frame_url,
            "gps": item.gps,
            "observed_at": item.observed_at,
        }
        evidence_id = "FIELD-" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        evidence_items.append(
            {
                "evidence_id": evidence_id,
                "capability": item.capability,
                "observation": item.observation,
                "confidence": item.confidence,
                "track_id": item.track_id,
                "frame_url": item.frame_url,
                "gps": item.gps,
                "observed_at": item.observed_at,
                "provenance": {
                    "mission_id": request.mission_id,
                    "observation_index": index,
                },
            }
        )

    canonical_for_hash = {
        "mission_id": request.mission_id,
        "requirements": [item.model_dump(mode="json") for item in requirements],
        "observations": [item.model_dump(mode="json") for item in observations],
        "result": result,
    }
    report_hash = hashlib.sha256(
        json.dumps(canonical_for_hash, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    actions = _next_actions(request, result, quality)
    now = datetime.now(timezone.utc).isoformat()

    return {
        "schema_version": "field-verification-report.v1",
        "report_type": "field_verification_closeout",
        "generated_at": now,
        "outcome": outcome,
        "lifecycle_state": lifecycle_state,
        "verification_context": {
            "mission_id": request.mission_id,
            "verification_objective": request.verification_objective
            or "Verify the physical requirements listed in the FIELD mission plan against the procurement record.",
            "dispatch_reason": request.dispatch_reason
            or "SENTRY dispatched FIELD to test physical requirements raised by the procurement investigation.",
            "operator_id": request.operator_id,
            "rover_id": request.rover_id,
            "mission_started_at": request.mission_started_at,
            "mission_completed_at": request.mission_completed_at,
        },
        "tender": result["tender"],
        "execution_summary": {
            "expected_total": summary["expected_total"],
            "observed_total": summary["observed_total"],
            "gap_total": summary["gap_total"],
            "observation_count": summary["observation_count"],
            "evidence_count": summary["evidence_count"],
            "gps_evidence_count": summary["gps_evidence_count"],
        },
        "evidence_quality": quality,
        "requirements": [
            {
                "id": requirement.id,
                "capability": requirement.capability,
                "label": _label(requirement),
                "expected_quantity": requirement.expected_quantity,
                "observed_quantity": _observed_count(
                    observations, requirement.capability
                ),
            }
            for requirement in requirements
        ],
        "evidence": evidence_items,
        "findings": {
            "discrepancies": discrepancies,
            "established": established,
            "not_established": [
                "FIELD evidence does not by itself establish payment, billing, acceptance, or fraud.",
                "Visual presence/absence does not by itself prove the contractual reason for a quantity difference.",
            ],
        },
        "alternative_explanations": result.get("possible_explanations", [])[:8],
        "unresolved_questions": list(dict.fromkeys(unresolved))[:10],
        "next_actions": actions,
        "case_state": {
            "state": lifecycle_state,
            "automatic_close": False,
            "investigator_decision_required": True,
            "decision_options": ["OPEN", "CONTINUE_INVESTIGATION", "CLOSE_AFTER_REVIEW"],
        },
        "provenance": {
            "source": "SENTRY FIELD",
            "verification_version": verification_version,
            "report_hash": report_hash,
            "hash_scope": "Mission payload, requirement metadata, returned observation metadata, and derived result JSON; remote media bytes are not hashed here.",
        },
        "guardrail": "This report is a physical-verification closeout signal. It does not declare fraud, non-compliance, or guilt; investigator review and documentary reconciliation remain required.",
    }
