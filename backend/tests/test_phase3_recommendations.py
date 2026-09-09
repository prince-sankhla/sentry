from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.api.routes.investigation_field_leads import tender_recommendations
from app.services.investigation_planner import InvestigationPlanner


class FakeScalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return FakeScalars(self.rows)


class FakeDb:
    def __init__(self, field_rows, pothole_rows):
        self.results = [FakeResult(field_rows), FakeResult(pothole_rows)]

    def execute(self, _statement):
        return self.results.pop(0)


def _tender(reference: str, title: str, *, source_record_id: str | None = None):
    return SimpleNamespace(
        id=uuid4(),
        reference_number=reference,
        source_record_id=source_record_id or reference,
        title=title,
        description=title,
        procuring_entity="PWD",
        category="Road works",
        source_name="Government eProcurement System of India",
        source_url="https://eprocure.gov.in/example",
        deleted_at=None,
        created_at=None,
        published_date=None,
    )


def test_audit_case_reference_stays_tender_investigation():
    query = "CAG Annual Technical Inspection Report on Local Bodies · 2017"
    plan = InvestigationPlanner().build_plan(query)
    assert plan.investigation_type == "tender"
    assert plan.query == query
    assert plan.confidence >= 0.97
    assert plan.steps[0].module == "tender_connectors"


def test_recommendation_endpoint_separates_field_and_pothole_buckets():
    field = _tender("FIELD:ROAD-001", "Streetlight inspection", source_record_id="FIELD:ROAD-001")
    pothole = _tender("WORK/POTHOLE/001", "Repair of potholes on municipal road")
    payload = tender_recommendations(FakeDb([field], [pothole]))

    assert payload["totals"] == {"field_ready": 1, "pothole": 1}
    assert payload["field_ready"][0]["field_ready"] is True
    assert payload["field_ready"][0]["reference_number"] == "FIELD:ROAD-001"
    assert payload["pothole"][0]["pothole_relevant"] is True
    assert payload["pothole"][0]["reference_number"] == "WORK/POTHOLE/001"


def test_recommendations_never_use_title_as_identity():
    field = _tender("FIELD:ROAD-002", "Same human-readable title")
    pothole = _tender("WORK/POTHOLE/002", "Same human-readable title")
    payload = tender_recommendations(FakeDb([field], [pothole]))

    assert payload["field_ready"][0]["tender_id"]
    assert payload["field_ready"][0]["reference_number"]
    assert payload["field_ready"][0]["title"] == "Same human-readable title"
    assert payload["pothole"][0]["tender_id"]
    assert payload["pothole"][0]["reference_number"]
