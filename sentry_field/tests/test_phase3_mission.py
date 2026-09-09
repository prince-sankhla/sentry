from __future__ import annotations

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
            "gps": {"status": "unavailable", "source": None, "lat": None, "lon": None},
            "last_error": None,
        }
    )


def test_dispatch_establishes_exact_mission_linkage() -> None:
    response = client.post(
        "/dispatch",
        json={
            "tender_id": "FIELD-DEMO-001",
            "mission_id": "FIELD-DEMO-001-REQ-CCMS-01-TEST",
            "requirement_id": "REQ-CCMS-01",
            "capability": "streetlight",
            "machine": "Normal Vision Rover",
            "demo_site": "Demo Field Zone A",
        },
    )
    assert response.status_code == 200
    status = client.get("/status").json()
    assert status["authorized"] is True
    assert status["mission_id"] == "FIELD-DEMO-001-REQ-CCMS-01-TEST"
    assert status["requirement_id"] == "REQ-CCMS-01"
    assert status["tender_id"] == "FIELD-DEMO-001"


def test_telemetry_records_real_coordinates_only_when_supplied() -> None:
    before = client.get("/status").json()["gps"]
    assert before["status"] == "unavailable"
    assert before["lat"] is None
    assert before["lon"] is None

    response = client.post(
        "/telemetry",
        json={
            "machine_id": "browser-gps:test-device",
            "lat": 26.9124,
            "lon": 75.7873,
            "speed": 0.4,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["gps"]["status"] == "live"
    assert payload["gps"]["lat"] == 26.9124
    assert payload["gps"]["lon"] == 75.7873

    status = client.get("/status").json()
    assert status["machine_id"] == "browser-gps:test-device"
    assert status["gps"]["status"] == "live"
    assert status["gps"]["lat"] == 26.9124
    assert status["gps"]["lon"] == 75.7873


def test_stream_contract_requires_valid_http_camera_url() -> None:
    invalid = client.get(
        "/stream",
        params={"camera_url": "not-a-url", "mission_id": "m", "requirement_id": "r"},
    )
    assert invalid.status_code == 400


def test_stop_revokes_authorization() -> None:
    dispatch = client.post(
        "/dispatch",
        json={
            "tender_id": "FIELD-DEMO-001",
            "mission_id": "m-stop-test",
            "requirement_id": "REQ-CCMS-01",
            "capability": "streetlight",
            "machine": "Normal Vision Rover",
        },
    )
    assert dispatch.status_code == 200
    stopped = client.post("/stop")
    assert stopped.status_code == 200
    status = client.get("/status").json()
    assert status["authorized"] is False
    assert status["running"] is False
