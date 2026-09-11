from __future__ import annotations

import time
from threading import Lock, Thread
from typing import Any, Generator


def stream(
    camera_url: str,
    confidence: float,
    every_n_frames: int,
    mission_id: str | None,
    requirement_id: str | None,
    capabilities: list[str],
) -> Generator[bytes, None, None]:
    """Low-latency FIELD stream: capture runs independently from AI inference."""
    import cv2
    from .vision.scanner import FieldScanner
    from .vision.config import build_config

    config = build_config(
        source=camera_url,
        confidence=confidence,
        every_n_frames=every_n_frames,
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
    )

    cap_lock = Lock()
    shared: dict[str, Any] = {"frame": None, "seq": 0, "closed": False, "error": None}

    def capture_loop() -> None:
        nonlocal shared
        capture = cv2.VideoCapture(camera_url)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        reconnect_delay = 0.25
        while True:
            with cap_lock:
                if shared["closed"]:
                    break
            if not capture.isOpened():
                capture.release()
                time.sleep(reconnect_delay)
                reconnect_delay = min(2.0, reconnect_delay * 1.5)
                capture = cv2.VideoCapture(camera_url)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            ok, frame = capture.read()
            if not ok or frame is None:
                shared["error"] = "Camera frame read failed; reconnecting"
                capture.release()
                time.sleep(reconnect_delay)
                reconnect_delay = min(2.0, reconnect_delay * 1.5)
                capture = cv2.VideoCapture(camera_url)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            reconnect_delay = 0.25
            with cap_lock:
                shared["frame"] = frame
                shared["seq"] += 1
        capture.release()

    Thread(target=capture_loop, daemon=True, name="sentry-field-camera").start()

    scanner: FieldScanner | None = None
    scanner_error: str | None = None
    try:
        try:
            scanner = FieldScanner(config)
        except Exception as exc:
            scanner_error = f"Vision models unavailable: {exc}"

        from . import api_v2 as gateway
        with gateway._lock:
            gateway._state["stop_token"] += 1
            token = gateway._state["stop_token"]
        gateway._set(
            running=True,
            authorized=True,
            camera_url=camera_url,
            last_error=scanner_error,
            mission_id=mission_id,
            requirement_id=requirement_id,
            capabilities=capabilities,
            confidence=config.confidence,
            every_n_frames=config.every_n_frames,
        )
        gateway._events.clear()
        gateway._events.appendleft({
            "type": "dispatch",
            "mission_id": mission_id,
            "requirement_id": requirement_id,
            "tender_id": gateway._state.get("tender_id"),
            "capabilities": capabilities,
            "observed_at": time.time(),
        })

        last_seq = 0
        last_infer_seq = -1
        latest_frame = None
        latest_display = None
        latest_detections: list[Any] = []
        latest_persisted: list[dict[str, Any]] = []
        seen_evidence_tracks: set[str] = set()
        idx = 0
        display_frames = 0
        display_started = time.monotonic()
        fps = 0.0
        last_emit = 0.0

        while True:
            with gateway._lock:
                if gateway._state["stop_token"] != token or not gateway._state["authorized"]:
                    break
            with cap_lock:
                seq = int(shared["seq"])
                frame = shared["frame"]
                capture_error = shared.get("error")
            if seq == last_seq and frame is None:
                time.sleep(0.005)
                continue
            if frame is None:
                time.sleep(0.005)
                continue
            last_seq = seq
            idx += 1
            latest_frame = frame.copy()

            # Run inference on fresh frames, but never block camera delivery on inference.
            if seq != last_infer_seq and (seq % max(1, every_n_frames) == 0 or last_infer_seq < 0):
                last_infer_seq = seq
                try:
                    current_gps = dict(gateway._state.get("gps") or {})
                    if scanner is not None:
                        latest_detections, _context, qr, barcode, ocr, persisted = scanner.scan(
                            latest_frame,
                            idx,
                            gps=current_gps,
                        )
                        filtered_persisted = []
                        for item in persisted:
                            track_id = str(item.get("track_id") or item.get("event_id") or "")
                            if track_id and track_id in seen_evidence_tracks:
                                continue
                            if track_id:
                                seen_evidence_tracks.add(track_id)
                            filtered_persisted.append(item)
                        latest_persisted = filtered_persisted
                    else:
                        latest_persisted = []
                    scanner_error = None
                except Exception as exc:
                    scanner_error = f"Vision inference failed: {exc}"
                    gateway._set(last_error=scanner_error)

                for detection in latest_detections:
                    _events = gateway._events
                    _events.appendleft({
                        "type": "detection",
                        "capability": detection.label.lower().replace(" ", "_"),
                        "observation": f"{detection.label} observed in field camera frame",
                        "confidence": round(float(detection.confidence), 3),
                        "bbox": detection.bbox,
                        "detector": detection.detector,
                        "track_id": detection.track_id,
                        "observed_at": time.time(),
                        "mission_id": mission_id,
                        "requirement_id": requirement_id,
                        "tender_id": gateway._state.get("tender_id"),
                        "machine_id": gateway._state.get("machine_id"),
                        "gps": dict(gateway._state.get("gps") or {}),
                    })
                for item in latest_persisted:
                    event = dict(item)
                    event["type"] = "evidence"
                    event["frame_url"] = gateway._frame_url(event)
                    event["tender_id"] = gateway._state.get("tender_id")
                    event["machine_id"] = gateway._state.get("machine_id")
                    event["gps"] = dict(gateway._state.get("gps") or {})
                    gateway._events.appendleft(event)

                ids = [value for value in (qr, barcode, ocr) if value]
                if ids:
                    gateway._events.appendleft({
                        "type": "identity",
                        "value": " | ".join(ids)[:200],
                        "detector": "qr/barcode/ocr",
                        "observed_at": time.time(),
                        "mission_id": mission_id,
                        "requirement_id": requirement_id,
                        "tender_id": gateway._state.get("tender_id"),
                        "gps": dict(gateway._state.get("gps") or {}),
                    })

            display = latest_frame.copy()
            for detection in latest_detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(display, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
            now = time.monotonic()
            if now - display_started >= 1.0:
                fps = display_frames / (now - display_started)
                display_frames = 0
                display_started = now
            display_frames += 1
            ms = 0.0 if last_infer_seq != seq else 0.0
            if display.shape[1] > max(320, int(config.stream_max_width)):
                max_width = max(320, int(config.stream_max_width))
                scale = max_width / float(display.shape[1])
                display = cv2.resize(display, (max_width, max(1, int(round(display.shape[0] * scale)))), interpolation=cv2.INTER_AREA)
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 1000), 44), (15, 18, 25), -1)
            cv2.putText(display, f"SENTRY FIELD | CAPTURE {fps:.1f} FPS | AI {len(latest_detections)} findings", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
            if capture_error or scanner_error:
                cv2.putText(display, "STREAM RECOVERING / AI DEGRADED", (14, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 200, 255), 2)
            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality), int(cv2.IMWRITE_JPEG_OPTIMIZE), 0])
            if ok:
                now = time.monotonic()
                if now - last_emit < 1 / 60:
                    continue
                last_emit = now
                with gateway._lock:
                    gateway._state.update({
                        "fps": round(fps, 1),
                        "inference_ms": round(0.0, 1),
                        "findings": len(latest_detections),
                        "evidence": len([event for event in gateway._events if event.get("type") == "evidence"]),
                        "last_detection": {
                            "type": latest_detections[0].label,
                            "confidence": round(float(latest_detections[0].confidence), 3),
                            "track_id": latest_detections[0].track_id,
                        } if latest_detections else gateway._state.get("last_detection"),
                        "updated_at": time.time(),
                    })
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
    finally:
        with cap_lock:
            shared["closed"] = True
        try:
            with __import__("sentry_field.api_v2", fromlist=["_lock"])._lock:
                if __import__("sentry_field.api_v2", fromlist=["_state"])._state["stop_token"] == token:
                    __import__("sentry_field.api_v2", fromlist=["_state"])._state["running"] = False
        except Exception:
            pass
