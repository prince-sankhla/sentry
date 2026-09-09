from __future__ import annotations

import time

from fastapi.testclient import TestClient

from sentry_field import api


client = TestClient(api.app)


def setup_function() -> None:
    api._events.clear()
    api._state.update(
        {
            "running": False,
            "authorized": False,
            "mission_id": None,
            "requirement_id": None,
            "tender_id": None,
            "machine_id": None,
            "battery": None,
            "speed": None,
            "gps": {
                "status": "unavailable",
                "source": None,
                "lat": None,
                "lon": None,
                "accuracy_m": None,
                "captured_at": None,
                "received_at": None,
                "mission_id": None,
                "requirement_id": None,
                "tender_id": None,
            },
            "last_error": None,
        }
    )


def dispatch_test_mission() -> None:
    response = client.post(
        "/dispatch",
        json={
            "tender_id": "FIELD-DEMO-001",
            "mission_id": "FIELD-DEMO-001-REQ-CCMS-01-PHASE4",
            "requirement_id": "REQ-CCMS-01",
            "capability": "streetlight",
            "machine": "Normal Vision Rover",
            "demo_site": "Demo Field Zone A",
        },
    )
    assert response.status_code == 200


def mobile_payload(**overrides: object) -> dict:
    payload = {
        "tender_id": "FIELD-DEMO-001",
        "mission_id": "FIELD-DEMO-001-REQ-CCMS-01-PHASE4",
        "requirement_id": "REQ-CCMS-01",
        "machine_id": "mobile-gps:test-device",
        "lat": 26.9124,
        "lon": 75.7873,
        "accuracy_m": 4.8,
        "captured_at": time.time() * 1000,
        "speed": 0.4,
    }
    payload.update(overrides)
    return payload


def test_mobile_gps_is_rejected_before_mission_authorisation() -> None:
    response = client.post("/telemetry/mobile", json=mobile_payload())
    assert response.status_code == 403
    status = client.get("/status").json()
    assert status["gps"]["status"] == "unavailable"
    assert status["gps"]["lat"] is None
    assert status["gps"]["lon"] is None


def test_mobile_gps_records_real_fix_with_accuracy_and_timestamp() -> None:
    dispatch_test_mission()
    captured_ms = int(time.time() * 1000)
    response = client.post("/telemetry/mobile", json=mobile_payload(captured_at=captured_ms))
    assert response.status_code == 200
    gps = response.json()["gps"]
    assert gps["status"] == "live"
    assert gps["source"] == "browser-geolocation"
    assert gps["lat"] == 26.9124
    assert gps["lon"] == 75.7873
    assert gps["accuracy_m"] == 4.8
    assert abs(gps["captured_at"] - captured_ms / 1000) < 0.01
    assert gps["mission_id"] == "FIELD-DEMO-001-REQ-CCMS-01-PHASE4"
    assert gps["requirement_id"] == "REQ-CCMS-01"
    assert gps["tender_id"] == "FIELD-DEMO-001"

    status = client.get("/status").json()
    assert status["gps"]["accuracy_m"] == 4.8
    assert status["gps"]["captured_at"] == gps["captured_at"]
    events = client.get("/events").json()["events"]
    assert events[0]["type"] == "mobile_gps"
    assert events[0]["gps"]["source"] == "browser-geolocation"


def test_mobile_gps_rejects_wrong_mission_context() -> None:
    dispatch_test_mission()
    response = client.post("/telemetry/mobile", json=mobile_payload(mission_id="OTHER-MISSION"))
    assert response.status_code == 409
    assert client.get("/status").json()["gps"]["status"] == "unavailable"


def test_mobile_gps_rejects_wrong_tender_context() -> None:
    dispatch_test_mission()
    response = client.post("/telemetry/mobile", json=mobile_payload(tender_id="OTHER-TENDER"))
    assert response.status_code == 409


def test_mobile_gps_rejects_stale_and_future_timestamps() -> None:
    dispatch_test_mission()
    stale = client.post("/telemetry/mobile", json=mobile_payload(captured_at=(time.time() - 86401) * 1000))
    assert stale.status_code == 400
    future = client.post("/telemetry/mobile", json=mobile_payload(captured_at=(time.time() + 301) * 1000))
    assert future.status_code == 400


def test_stop_revokes_mobile_gps_and_clears_fix() -> None:
    dispatch_test_mission()
    assert client.post("/telemetry/mobile", json=mobile_payload()).status_code == 200
    stopped = client.post("/stop")
    assert stopped.status_code == 200
    status = client.get("/status").json()
    assert status["authorized"] is False
    assert status["gps"]["status"] == "unavailable"
    assert status["gps"]["lat"] is None
    assert status["gps"]["accuracy_m"] is None
