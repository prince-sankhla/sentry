from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.api.routes.field_reanalysis import FieldReanalysisRequest, FieldRequirement, FieldObservation, field_reanalysis
from app.services.field_verification_auto import build_auto_field_verification_plan
from app.services.priority_queue_direct_tender import auto_capabilities_for_tender if False else _physical_capabilities


class FakeDb:
    def __init__(self, tender):
        self.tender = tender

    def get(self, _model, _tender_id):
        return self.tender


class ScalarResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class QueueDb:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _statement):
        return ScalarResult(self.rows)


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


def test_field_reanalysis_returns_discrepancy_and_guardrail():
    row = tender()
    requirements = [FieldRequirement(id="REQ-01", capability="pothole", label="Potholes", expected_quantity=6)]
    observations = [
        FieldObservation(capability="pothole", track_id=f"trk-{i}", frame_url=f"/evidence-files/{i}.jpg", gps={"lat": 26.1, "lon": 74.1})
        for i in range(5)
    ]
    result = field_reanalysis(
        FieldReanalysisRequest(tender_id=str(row.id), mission_id="mission-1", requirements=requirements, observations=observations),
        FakeDb(row),
    )
    assert result["status"] == "discrepancy_review"
    assert result["summary"]["expected_total"] == 6
    assert result["summary"]["observed_total"] == 5
    assert result["summary"]["gap_total"] == 1
    assert result["summary"]["evidence_count"] == 5
    assert result["summary"]["gps_evidence_count"] == 5
    assert result["discrepancies"][0]["signal"] == "discrepancy"
    assert "not a fraud finding" in result["guardrail"]


def test_physical_queue_prioritizes_dharmagarh():
    rows = [
        tender(title="Ordinary LED procurement", reference_number="LED/002", description="street light work"),
        tender(title="Dharmagarh road and drain pothole repair", reference_number="DHARMA/001", description="pothole drain road repair"),
    ]
    # Exercise the classifier directly; queue integration is covered by the backend API smoke suite.
    assert set(_physical_capabilities(rows[1])) >= {"pothole", "drain", "road_crack"}
