from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import app.api.routes.field_reanalysis as field_reanalysis_route
from app.schemas.field_verification import (
    FieldObservation,
    FieldReanalysisRequest,
    FieldRequirement,
)
from app.services.field_verification_auto import build_auto_field_verification_plan
from app.services.field_verification_report import build_field_verification_report
from app.services.priority_queue_direct_tender import _physical_capabilities


class FakeDb:
    def __init__(self, tender):
        self.tender = tender

    def get(self, _model, _tender_id):
        return self.tender


def tender(**overrides):
    values = {
        "id": uuid4(),
        "reference_number": "TEST/PHYSICAL/001",
        "source_record_id": "",
        "title": "Construction of CC road and drain with pothole repair at Dharmagarh",
        "description": "Road surface distress, drain and pothole repair work",
        "category": None,
        "procuring_entity": "Dharmagarh NAC",
        "source_name": "Government eProcurement System of India",
        "source_url": "https://eprocure.gov.in/example",
        "deleted_at": None,
        "created_at": None,
        "published_date": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_auto_field_plan_is_executable_for_unprofiled_tender():
    row = tender()
    plan = build_auto_field_verification_plan(FakeDb(row), row.id)
    assert plan["verification_required"] is True
    assert plan["auto_generated"] is True
    capabilities = {item["capability"] for item in plan["requirements"]}
    assert {"pothole", "drain"}.issubset(capabilities)
    assert "asset_text" in capabilities
    assert plan["field_tender_key"] == str(row.id)


def test_field_reanalysis_returns_discrepancy_and_closeout_report(monkeypatch):
    row = tender()
    requirements = [
        FieldRequirement(
            id="REQ-01",
            capability="pothole",
            label="Potholes",
            expected_quantity=6,
        )
    ]
    observations = [
        FieldObservation(
            capability="pothole",
            track_id=f"trk-{i}",
            frame_url=f"/evidence-files/{i}.jpg",
            gps={"lat": 26.1, "lon": 74.1},
            confidence=0.9,
        )
        for i in range(5)
    ]

    monkeypatch.setattr(
        field_reanalysis_route,
        "_save_verification",
        lambda _db, _tender_id, _request, result: {
            "id": "test-verification",
            "version": 1,
            "status": result["report"]["lifecycle_state"],
            "outcome": result["report"]["outcome"],
            "lifecycle_state": result["report"]["lifecycle_state"],
            "observation_count": result["summary"]["observation_count"],
            "evidence_count": result["summary"]["evidence_count"],
            "gps_evidence_count": result["summary"]["gps_evidence_count"],
        },
    )

    result = field_reanalysis_route.field_reanalysis(
        FieldReanalysisRequest(
            tender_id=str(row.id),
            mission_id="mission-1",
            requirements=requirements,
            observations=observations,
        ),
        FakeDb(row),
    )

    assert result["status"] == "discrepancy_review"
    assert result["summary"]["expected_total"] == 6
    assert result["summary"]["observed_total"] == 5
    assert result["summary"]["gap_total"] == 1
    assert result["summary"]["evidence_count"] == 5
    assert result["summary"]["gps_evidence_count"] == 5
    assert result["discrepancies"][0]["signal"] == "discrepancy"
    assert result["report"]["outcome"] == "PARTIALLY_VERIFIED"
    assert result["report"]["lifecycle_state"] == "RECONCILIATION_REQUIRED"
    assert result["report"]["next_actions"]
    assert "not a fraud finding" in result["guardrail"]


def test_closeout_report_is_inconclusive_without_observations():
    row = tender()
    request = FieldReanalysisRequest(
        tender_id=str(row.id),
        mission_id="mission-empty",
        requirements=[
            FieldRequirement(
                id="REQ-01",
                capability="streetlight",
                label="Streetlights",
                expected_quantity=10,
            )
        ],
        observations=[],
    )
    result = {
        "status": "no_observed_shortfall",
        "mission_id": "mission-empty",
        "tender": {
            "id": str(row.id),
            "reference_number": row.reference_number,
            "title": row.title,
            "procuring_entity": row.procuring_entity,
        },
        "summary": {
            "expected_total": 10,
            "observed_total": 0,
            "gap_total": 10,
            "evidence_count": 0,
            "gps_evidence_count": 0,
            "observation_count": 0,
        },
        "discrepancies": [],
        "possible_explanations": [],
        "next_checks": [],
        "guardrail": "review",
    }
    report = build_field_verification_report(request, result)
    assert report["outcome"] == "INCONCLUSIVE"
    assert report["lifecycle_state"] == "EVIDENCE_REVIEW_REQUIRED"
    assert report["case_state"]["automatic_close"] is False
    assert report["next_actions"][0]["id"] == "verify_field_coverage"


def test_physical_capability_classifier_covers_dharmagarh_case():
    row = tender()
    capabilities = set(_physical_capabilities(row))
    assert {"pothole", "drain", "road_crack"}.issubset(capabilities)
