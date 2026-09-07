from __future__ import annotations

import inspect
import json
from pathlib import Path

from fastapi.testclient import TestClient

from sentry_field.api import app
from sentry_field.vision.scanner import FieldScanner

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "sentry_field" / "data" / "demo_tenders.json"


def main() -> None:
    rows = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert len(rows) >= 8, f"Expected demo tender catalog, got {len(rows)}"
    for tender in rows:
        assert tender["requirements"], tender["id"]
        for requirement in tender["requirements"]:
            assert requirement["capability"], requirement["id"]

    source = inspect.getsource(FieldScanner.__init__)
    scan_source = inspect.getsource(FieldScanner.scan)
    assert "self.context_model" in source, "FieldScanner context model is not initialized"
    assert "self.context_model" in scan_source, "FieldScanner context path is not wired"

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

    stop = client.post("/stop")
    assert stop.status_code == 200
    assert client.get("/status").json()["authorized"] is False

    print(f"Field pipeline smoke test passed: {len(rows)} tender profiles validated")


if __name__ == "__main__":
    main()
