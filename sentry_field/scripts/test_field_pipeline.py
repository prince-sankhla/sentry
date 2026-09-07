from __future__ import annotations

import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient

from sentry_field.api import app
from sentry_field.api_fast import app as fast_app
from sentry_field.vision.capabilities import CAPABILITIES
from sentry_field.vision.config import CAPABILITY_ALIASES
from sentry_field.vision.scanner import FieldScanner

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "sentry_field" / "data" / "demo_tenders.json"


def main() -> None:
    rows = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert len(rows) >= 8, f"Expected demo tender catalog, got {len(rows)}"

    known_capabilities = set(CAPABILITIES)
    known_values = set(CAPABILITY_ALIASES.values())
    assert known_values <= known_capabilities, "Capability alias drift detected"
    for tender in rows:
        assert tender["requirements"], tender["id"]
        for requirement in tender["requirements"]:
            assert requirement["capability"] in known_capabilities, requirement["id"]

    source = inspect.getsource(FieldScanner.__init__)
    scan_source = inspect.getsource(FieldScanner.scan)
    assert "self.context_model" in source, "FieldScanner context model is not initialized"
    assert "self.context_model" in scan_source, "FieldScanner context path is not wired"
    assert fast_app is app, "api_fast must stay a compatibility alias to the canonical gateway"

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200 and health.json()["ok"] is True

    catalog = client.get("/tenders")
    assert catalog.status_code == 200
    api_rows = catalog.json()["tenders"]
    assert len(api_rows) == len(rows)

    first = api_rows[0]
    detail = client.get(f"/tenders/{first['id']}")
    assert detail.status_code == 200
    requirement = first["requirements"][0]

    unauthorized = client.get(
        "/stream",
        params={
            "camera_url": "http://127.0.0.1:4747/video",
            "mission_id": "UNAUTH-MISSION",
            "requirement_id": requirement["id"],
            "capabilities": requirement["capability"],
        },
    )
    assert unauthorized.status_code == 409, unauthorized.text

    dispatch = client.post(
        "/dispatch",
        json={
            "tender_id": first["id"],
            "mission_id": "PIPELINE-TEST-MISSION",
            "requirement_id": requirement["id"],
            "capability": requirement["capability"],
            "machine": first["machine"],
            "demo_site": first["demo_site"],
        },
    )
    assert dispatch.status_code == 200, dispatch.text
    assert dispatch.json()["authorized"] is True

    status = client.get("/status").json()
    assert status["authorized"] is True
    assert status["tender_id"] == first["id"]
    assert status["requirement_id"] == requirement["id"]

    telemetry = client.post(
        "/telemetry",
        json={
            "machine_id": "ROVER-TEST",
            "battery": 87,
            "speed": 0.4,
            "lat": 26.9124,
            "lon": 75.7873,
        },
    )
    assert telemetry.status_code == 200
    assert telemetry.json()["gps"]["status"] == "live"
    assert client.get("/status").json()["machine_id"] == "ROVER-TEST"

    stop = client.post("/stop")
    assert stop.status_code == 200
    assert client.get("/status").json()["authorized"] is False

    print(f"Field pipeline smoke test passed: {len(rows)} tender profiles validated")


if __name__ == "__main__":
    main()
