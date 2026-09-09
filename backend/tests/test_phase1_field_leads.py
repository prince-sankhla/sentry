from __future__ import annotations

from app.api.routes import investigation_field_leads
from app.services.investigation_planner import InvestigationPlanner


def test_field_leads_endpoint_exposes_stable_identity(monkeypatch):
    sample = [
        {
            "tender_id": "11111111-1111-1111-1111-111111111111",
            "reference_number": "FIELD:2026_DEMO_ROAD",
            "source_record_id": "FIELD:2026_DEMO_ROAD",
            "tender_title": "Construction of Retaining wall and Drain Works",
            "subject": "Construction of Retaining wall and Drain Works",
            "source_url": "https://eprocure.gov.in/example",
            "investigation_type": "tender",
            "priority": "review",
            "risk_level": "insufficient",
            "typology_count": 0,
            "linked_records": 1,
            "evidence_strength": "high",
            "evidence_completeness": 1.0,
            "primary_pattern": "Field verification candidate",
            "reasons": ["Eligible for SENTRY FIELD capability planning after procurement review"],
        }
    ]

    monkeypatch.setattr(investigation_field_leads, "direct_field_tender_leads", lambda db: sample)
    body = investigation_field_leads.field_tender_leads(object())

    assert body["total"] == 1
    assert body["items"][0]["tender_id"] == sample[0]["tender_id"]
    assert body["items"][0]["reference_number"] == sample[0]["reference_number"]
    assert body["items"][0]["source_record_id"] == sample[0]["source_record_id"]
    assert body["items"][0]["tender_title"] == sample[0]["tender_title"]


def test_field_reference_is_planned_as_exact_tender_investigation():
    reference = "FIELD:2026_DEMO_ROAD"
    plan = InvestigationPlanner().build_plan(reference)

    assert plan.investigation_type == "tender"
    assert plan.query == reference
    assert plan.steps[0].inputs["query"] == reference
