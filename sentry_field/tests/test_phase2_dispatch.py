from __future__ import annotations

from fastapi.testclient import TestClient

from sentry_field import api


def _profile():
    return {
        "id": "FIELD-DEMO-001",
        "tender_id": "2026_CCMS_ARUNACHAL",
        "requirements": [
            {
                "id": "REQ-CCMS-01",
                "capability": "streetlight",
                "label": "Streetlight presence",
                "expected_quantity": 6,
            }
        ],
        "machine": "Normal Vision Rover",
        "demo_site": "Demo Field Zone A",
    }


def test_dispatch_authorizes_exact_profile_requirement(monkeypatch):
    monkeypatch.setattr(api, "_load_demo_tenders", lambda: [_profile()])
    client = TestClient(api.app)

    response = client.post(
        "/dispatch",
        json={
            "tender_id": "FIELD-DEMO-001",
            "mission_id": "mission-phase2-test",
            "requirement_id": "REQ-CCMS-01",
            "capability": "streetlight",
            "machine": "Normal Vision Rover",
            "demo_site": "Demo Field Zone A",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["authorized"] is True
    assert body["tender"]["id"] == "FIELD-DEMO-001"
    assert body["requirement"]["id"] == "REQ-CCMS-01"
    assert api._snap()["mission_id"] == "mission-phase2-test"
    assert api._snap()["requirement_id"] == "REQ-CCMS-01"
    assert api._snap()["tender_id"] == "FIELD-DEMO-001"


def test_dispatch_rejects_capability_mismatch(monkeypatch):
    monkeypatch.setattr(api, "_load_demo_tenders", lambda: [_profile()])
    client = TestClient(api.app)

    response = client.post(
        "/dispatch",
        json={
            "tender_id": "FIELD-DEMO-001",
            "mission_id": "mission-phase2-negative",
            "requirement_id": "REQ-CCMS-01",
            "capability": "pothole",
            "machine": "Normal Vision Rover",
        },
    )

    assert response.status_code == 400
    assert "Capability does not match" in response.json()["detail"]
