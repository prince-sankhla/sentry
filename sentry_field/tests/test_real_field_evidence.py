from __future__ import annotations

from types import SimpleNamespace

from sentry_field.vision.scanner import Detection, FieldScanner


def test_detection_evidence_receives_live_gps() -> None:
    scanner = FieldScanner.__new__(FieldScanner)
    scanner.last_evidence_at = {}
    scanner.current_gps = {
        "status": "live",
        "source": "browser-geolocation",
        "lat": 26.912400,
        "lon": 75.787300,
        "accuracy_m": 4.8,
    }
    scanner.config = SimpleNamespace(
        evidence_cooldown_seconds=0,
        mission_id="mission-1",
        requirement_id="REQ-1",
        source="http://127.0.0.1:4747/video",
    )

    captured: dict = {}

    class Writer:
        def record_detection(self, frame, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(to_dict=lambda: {"event_id": "field-test"})

    scanner.writer = Writer()
    detection = Detection("pothole", 0.91, [1, 2, 30, 40], "pothole_model", "trk-00001")

    event = scanner._save_detection(object(), detection, "trk-00001", "test")

    assert event["event_id"] == "field-test"
    assert captured["gps"]["lat"] == 26.9124
    assert captured["gps"]["lon"] == 75.7873
    assert captured["mission_id"] == "mission-1"
    assert captured["requirement_id"] == "REQ-1"
