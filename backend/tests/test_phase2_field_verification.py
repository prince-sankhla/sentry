from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from app.services import field_verification


TENDER_ID = UUID("5d5cf9e5-7d28-4c51-97dc-944e070d1cec")


def _tender():
    return SimpleNamespace(
        id=TENDER_ID,
        reference_number="RW/ITA/Tender/CCMS",
        title="Supply Installation Testing Commissioning Operation Maintenance of Centralized WebBased Street Light Control Monitoring System",
        source_record_id="FIELD:2026_CCMS_ARUNACHAL",
        source_url="https://eprocure.gov.in/eprocure/app?sp=l954664",
        procuring_entity="PWD Highway Zone Arunachal Pradesh",
        deleted_at=None,
    )


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args):
        return self

    def all(self):
        return self.rows


class FakeDb:
    def __init__(self, tender):
        self.tender = tender

    def get(self, model, key):
        return self.tender if key == self.tender.id else None

    def query(self, model):
        return FakeQuery([self.tender])


def test_exact_tender_id_resolves_registered_field_requirements(monkeypatch):
    monkeypatch.setattr(field_verification, "_load_profiles", lambda: [{
        "id": "FIELD-DEMO-001",
        "tender_id": "2026_CCMS_ARUNACHAL",
        "reference_number": "RW/ITA/Tender/CCMS",
        "machine": "Normal Vision Rover",
        "demo_site": "Demo Field Zone A",
        "category": "Street lighting / CCMS",
        "requirements": [
            {"id": "REQ-CCMS-01", "capability": "streetlight", "label": "Streetlight presence", "expected_quantity": 6},
            {"id": "REQ-CCMS-02", "capability": "asset_qr", "label": "Asset identity via QR / ID", "expected_quantity": 6},
        ],
        "verification_notes": "Visual verification only.",
        "source_verified_on": "2026-09-07",
    }])

    payload = field_verification.build_field_verification_plan(FakeDb(_tender()), TENDER_ID)

    assert payload["verification_required"] is True
    assert payload["tender"]["id"] == str(TENDER_ID)
    assert payload["field_tender_key"] == "FIELD-DEMO-001"
    assert payload["requirements"][0]["id"] == "REQ-CCMS-01"
    assert payload["requirements"][0]["capability"] == "streetlight"


def test_reference_resolution_preserves_exact_tender_identity(monkeypatch):
    tender = _tender()
    monkeypatch.setattr(field_verification, "_load_profiles", lambda: [{
        "id": "FIELD-DEMO-001",
        "tender_id": "2026_CCMS_ARUNACHAL",
        "reference_number": "RW/ITA/Tender/CCMS",
        "machine": "Normal Vision Rover",
        "demo_site": "Demo Field Zone A",
        "requirements": [{"id": "REQ-CCMS-01", "capability": "streetlight", "label": "Streetlight presence", "expected_quantity": 6}],
        "verification_notes": "Visual verification only.",
    }])

    payload = field_verification.build_field_verification_plan_by_reference(FakeDb(tender), tender.reference_number)

    assert payload["tender"]["id"] == str(TENDER_ID)
    assert payload["tender"]["reference_number"] == tender.reference_number
    assert payload["field_tender_key"] == "FIELD-DEMO-001"
    assert payload["requirements"][0]["capability"] == "streetlight"
