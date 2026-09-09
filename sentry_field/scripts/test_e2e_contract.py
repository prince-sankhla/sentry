from __future__ import annotations

import time

from fastapi.testclient import TestClient

from sentry_field import api_v2


client = TestClient(api_v2.app)


def test_health_and_capabilities_contract():
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True
    caps = client.get("/capabilities")
    assert caps.status_code == 200
    values = {item["value"] for item in caps.json()["capabilities"]}
    assert {"pothole", "road_crack", "drain", "streetlight", "asset_text"}.issubset(values)


def test_dispatch_accepts_entire_auto_selected_capability_set(monkeypatch):
    tender = {
        "id": "db-tender-1",
        "tender_id": "db-tender-1",
        "reference_number": "TEST/DHARMAGARH/001",
        "title": "Dharmagarh road drain pothole repair",
        "source_name": "Government eProcurement System of India",
        "source_url": "https://eprocure.gov.in/example",
        "contract_location": "Dharmagarh",
        "category": "Road + drain",
        "machine": "Normal Vision Rover",
        "demo_site": None,
        "requirements": [
            {"id": "AUTO-pothole", "capability": "pothole", "label": "Pothole", "expected_quantity": 1},
            {"id": "AUTO-drain", "capability": "drain", "label": "Drain", "expected_quantity": 1},
            {"id": "AUTO-road_crack", "capability": "road_crack", "label": "Road crack", "expected_quantity": 1},
            {"id": "AUTO-asset_text", "capability": "asset_text", "label": "OCR", "expected_quantity": 1},
        ],
    }
    monkeypatch.setattr(api_v2, "_find_tender", lambda _key: tender)
    response = client.post(
        "/dispatch",
        json={
            "tender_id": "db-tender-1",
            "mission_id": "mission-1",
            "requirement_id": "AUTO-pothole",
            "capability": "pothole",
            "capabilities": ["pothole", "drain", "road_crack", "asset_text"],
            "machine": "Normal Vision Rover",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["capabilities"] == ["pothole", "drain", "road_crack", "asset_text"]
    assert payload["authorized"] is True


def test_mobile_gps_is_bound_to_authorised_mission(monkeypatch):
    tender = {
        "id": "db-tender-2",
        "tender_id": "db-tender-2",
        "reference_number": "TEST/GPS/001",
        "title": "Pothole repair",
        "source_name": "Government eProcurement System of India",
        "source_url": "https://eprocure.gov.in/example",
        "machine": "Normal Vision Rover",
        "demo_site": None,
        "requirements": [{"id": "AUTO-pothole", "capability": "pothole", "label": "Pothole", "expected_quantity": 1}],
    }
    monkeypatch.setattr(api_v2, "_find_tender", lambda _key: tender)
    dispatch = client.post(
        "/dispatch",
        json={
            "tender_id": "db-tender-2",
            "mission_id": "mission-gps",
            "requirement_id": "AUTO-pothole",
            "capability": "pothole",
            "capabilities": ["pothole"],
            "machine": "Normal Vision Rover",
        },
    )
    assert dispatch.status_code == 200
    gps = client.post(
        "/telemetry/mobile",
        json={
            "tender_id": "db-tender-2",
            "mission_id": "mission-gps",
            "requirement_id": "AUTO-pothole",
            "machine_id": "browser-gps:test",
            "lat": 26.1,
            "lon": 74.1,
            "accuracy_m": 8,
            "captured_at": time.time(),
            "speed": 0,
        },
    )
    assert gps.status_code == 200
    assert gps.json()["gps"]["source"] == "browser-geolocation"
    assert gps.json()["gps"]["lat"] == 26.1
