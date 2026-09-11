from __future__ import annotations

import time
from threading import Event, Lock, Thread
from typing import Any, Generator


def stream(
    camera_url: str,
    confidence: float,
    every_n_frames: int,
    mission_id: str | None,
    requirement_id: str | None,
    capabilities: list[str],
) -> Generator[bytes, None, None]:
    """Low-latency FIELD stream with independent capture and AI workers."""
    import cv2
    from . import api_v2 as gateway
    from .vision.config import build_config
    from .vision.scanner import FieldScanner

    config = build_config(
        source=camera_url,
        confidence=confidence,
        every_n_frames=every_n_frames,
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
    )

    lock = Lock()
    stop_event = Event()
    shared: dict[str, Any] = {
        "frame": None,
        "seq": 0,
        "capture_error": None,
        "detections": [],
        "scanner_error": None,
        "inference_ms": 0.0,
    }

    with gateway._lock:
        gateway._state["stop_token"] += 1
        token = gateway._state["stop_token"]
        tender_id = gateway._state.get("tender_id")

    gateway._events.clear()
    gateway._events.appendleft({
        "type": "dispatch",
        "mission_id": mission_id,
        "requirement_id": requirement_id,
        "tender_id": tender_id,
        "capabilities": capabilities,
        "observed_at": time.time(),
    })

    def should_stop() -> bool:
        with gateway._lock:
            return stop_event.is_set() or gateway._state["stop_token"] != token or not gateway._state["authorized"]

    def capture_loop() -> None:
        capture = None
        reconnect_delay = 0.2
        try:
            while not should_stop():
                if capture is None or not capture.isOpened():
                    if capture is not None:
                        capture.release()
                    capture = cv2.VideoCapture(camera_url)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    if not capture.isOpened():
                        with lock:
                            shared["capture_error"] = "Camera unavailable; reconnecting"
                        time.sleep(reconnect_delay)
                        reconnect_delay = min(2.0, reconnect_delay * 1.5)
                        continue
                    reconnect_delay = 0.2
                ok, frame = capture.read()
                if not ok or frame is None:
                    with lock:
                        shared["capture_error"] = "Camera frame read failed; reconnecting"
                    capture.release()
                    capture = None
                    continue
                with lock:
                    shared["frame"] = frame
                    shared["seq"] += 1
                    shared["capture_error"] = None
        finally:
            if capture is not None:
                capture.release()

    def inference_loop() -> None:
        scanner: FieldScanner | None = None
        try:
            try:
                scanner = FieldScanner(config)
            except Exception as exc:
                with lock:
                    shared["scanner_error"] = f"Vision models unavailable: {exc}"
            last_seq = -1
            index = 0
            seen_evidence_tracks: set[str] = set()
            while not should_stop():
                with lock:
                    seq = int(shared["seq"])
                    frame = shared["frame"]
                if frame is None or seq == last_seq:
                    time.sleep(0.002)
                    continue
                if seq % max(1, every_n_frames) != 0 and last_seq >= 0:
                    last_seq = seq
                    continue
                last_seq = seq
                index += 1
                started = time.monotonic()
                try:
                    gps = dict(gateway._state.get("gps") or {})
                    detections: list[Any] = []
                    persisted: list[dict[str, Any]] = []
                    qr = barcode = ocr = None
                    if scanner is not None:
                        detections, _context, qr, barcode, ocr, persisted = scanner.scan(frame.copy(), index, gps=gps)
                    filtered_persisted: list[dict[str, Any]] = []
                    for item in persisted:
                        track_id = str(item.get("track_id") or item.get("event_id") or "")
                        if track_id and track_id in seen_evidence_tracks:
                            continue
                        if track_id:
                            seen_evidence_tracks.add(track_id)
                        filtered_persisted.append(item)
                    with lock:
                        shared["detections"] = detections
                        shared["scanner_error"] = None
                        shared["inference_ms"] = (time.monotonic() - started) * 1000

                    for detection in detections:
                        gateway._events.appendleft({
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
                    for item in filtered_persisted:
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
                except Exception as exc:
                    with lock:
                        shared["scanner_error"] = f"Vision inference failed: {exc}"

        finally:
            pass

    Thread(target=capture_loop, daemon=True, name="sentry-field-camera").start()
    Thread(target=inference_loop, daemon=True, name="sentry-field-ai").start()

    gateway._set(
        running=True,
        authorized=True,
        camera_url=camera_url,
        last_error=None,
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
        confidence=config.confidence,
        every_n_frames=config.every_n_frames,
    )

    output_seq = -1
    display_started = time.monotonic()
    display_frames = 0
    capture_fps = 0.0
    try:
        while not should_stop():
            with lock:
                seq = int(shared["seq"])
                frame = shared["frame"]
                detections = list(shared["detections"])
                capture_error = shared["capture_error"]
                scanner_error = shared["scanner_error"]
                inference_ms = float(shared["inference_ms"] or 0.0)
            if frame is None or seq == output_seq:
                time.sleep(0.002)
                continue
            output_seq = seq
            display = frame.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(display, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

            display_frames += 1
            now = time.monotonic()
            if now - display_started >= 1.0:
                capture_fps = display_frames / (now - display_started)
                display_frames = 0
                display_started = now

            max_width = max(320, int(config.stream_max_width))
            if display.shape[1] > max_width:
                scale = max_width / float(display.shape[1])
                display = cv2.resize(display, (max_width, max(1, int(round(display.shape[0] * scale)))), interpolation=cv2.INTER_AREA)
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 1000), 44), (15, 18, 25), -1)
            cv2.putText(display, f"SENTRY FIELD | CAPTURE {capture_fps:.1f} FPS | AI {inference_ms:.0f}ms | {len(detections)} findings", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
            if capture_error or scanner_error:
                cv2.putText(display, "RECOVERING / AI DEGRADED", (14, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 200, 255), 2)

            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality), int(cv2.IMWRITE_JPEG_OPTIMIZE), 0])
            if ok:
                gateway._set(
                    fps=round(capture_fps, 1),
                    inference_ms=round(inference_ms, 1),
                    findings=len(detections),
                    evidence=len([e for e in gateway._events if e.get("type") == "evidence"]),
                    last_detection={"type": detections[0].label, "confidence": round(float(detections[0].confidence), 3), "track_id": detections[0].track_id} if detections else gateway._state.get("last_detection"),
                    last_error=scanner_error or capture_error,
                )
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
    finally:
        stop_event.set()
        with gateway._lock:
            if gateway._state["stop_token"] == token:
                gateway._state["running"] = False
