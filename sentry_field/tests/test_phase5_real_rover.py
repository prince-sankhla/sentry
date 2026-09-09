from __future__ import annotations

from fastapi.testclient import TestClient

from sentry_field import api
from sentry_field.api_fast import app as fast_app


client = TestClient(api.app)


MISSION = {
    "tender_id": "FIELD-DEMO-001",
    "mission_id": "FIELD-DEMO-001-REQ-CCMS-01-PHASE5",
    "requirement_id": "REQ-CCMS-01",
    "capability": "streetlight",
    "machine": "Normal Vision Rover",
    "demo_site": "Demo Field Zone A",
}


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


def dispatch() -> None:
    response = client.post("/dispatch", json=MISSION)
    assert response.status_code == 200, response.text
    assert response.json()["authorized"] is True


def test_real_rover_mission_dispatch_telemetry_and_stop_contract() -> None:
    dispatch()

    telemetry = client.post(
        "/telemetry",
        json={
            "machine_id": "ROVER-001",
            "battery": 87,
            "speed": 0.42,
            "lat": 26.9124,
            "lon": 75.7873,
        },
    )
    assert telemetry.status_code == 200, telemetry.text
    payload = telemetry.json()
    assert payload["ok"] is True
    assert payload["gps"]["status"] == "live"
    assert payload["gps"]["lat"] == 26.9124
    assert payload["gps"]["lon"] == 75.7873
    assert payload["gps"]["source"] == "ROVER-001"

    status = client.get("/status").json()
    assert status["authorized"] is True
    assert status["machine_id"] == "ROVER-001"
    assert status["battery"] == 87
    assert status["speed"] == 0.42
    assert status["gps"]["mission_id"] == MISSION["mission_id"]
    assert status["gps"]["requirement_id"] == MISSION["requirement_id"]
    assert status["gps"]["tender_id"] == MISSION["tender_id"]

    events = client.get("/events").json()["events"]
    assert events[0]["type"] == "telemetry"
    assert events[0]["machine_id"] == "ROVER-001"
    assert events[0]["battery"] == 87
    assert events[0]["speed"] == 0.42

    stopped = client.post("/stop")
    assert stopped.status_code == 200
    stopped_status = client.get("/status").json()
    assert stopped_status["authorized"] is False
    assert stopped_status["running"] is False


def test_rover_can_send_battery_and_speed_without_gps() -> None:
    dispatch()
    response = client.post(
        "/telemetry",
        json={
            "machine_id": "ROVER-001",
            "battery": 64,
            "speed": 0.0,
        },
    )
    assert response.status_code == 200, response.text
    gps = response.json()["gps"]
    assert gps["status"] == "unavailable"
    assert gps["lat"] is None
    assert gps["lon"] is None
    status = client.get("/status").json()
    assert status["battery"] == 64
    assert status["speed"] == 0.0


def test_gateway_compatibility_entrypoint_remains_canonical() -> None:
    assert fast_app is api.app
