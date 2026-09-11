from __future__ import annotations

import time
from threading import Lock, Thread
from typing import Any, Generator
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener


def _valid_http_camera_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class _MjpegCapture:
    """Persistent DroidCam/HTTP MJPEG reader with no socket read timeout."""

    def __init__(self, source: str) -> None:
        import cv2

        self.source = source
        self._cv2 = cv2
        self.response = None
        self.buffer = bytearray()
        self.closed = False
        self.failures = 0
        self.opener = build_opener(ProxyHandler({}))
        self._open()

    def _open(self) -> bool:
        if self.closed:
            return False
        try:
            self._close_response()
            request = Request(
                self.source,
                headers={
                    "Accept": "multipart/x-mixed-replace,image/jpeg,*/*",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Connection": "keep-alive",
                    "User-Agent": "SENTRY-FIELD/1.0",
                },
                method="GET",
            )
            self.response = self.opener.open(request, timeout=8)
            content_type = str(self.response.headers.get("Content-Type") or "").lower()
            if "multipart" not in content_type and "image/jpeg" not in content_type:
                self._close_response()
                return False
            try:
                self.response.fp.raw._sock.settimeout(None)  # type: ignore[attr-defined]
            except Exception:
                pass
            self.buffer.clear()
            self.failures = 0
            return True
        except Exception:
            self._close_response()
            return False

    def isOpened(self) -> bool:  # noqa: N802
        return self.response is not None and not self.closed

    def _read_chunk(self) -> bool:
        if not self.response:
            return False
        try:
            chunk = self.response.read(16384)
        except Exception:
            return False
        if not chunk:
            return False
        self.buffer.extend(chunk)
        return True

    def _reconnect(self) -> bool:
        if self.closed:
            return False
        self.failures += 1
        if self.failures > 8:
            return False
        time.sleep(min(0.15 * self.failures, 1.0))
        return self._open()

    def read(self):
        if not self.isOpened() and not self._open():
            return False, None
        while not self.closed:
            start = self.buffer.find(b"\xff\xd8")
            if start < 0:
                if self._read_chunk():
                    continue
                if self._reconnect():
                    continue
                return False, None
            if start:
                del self.buffer[:start]
            end = self.buffer.find(b"\xff\xd9", 2)
            if end < 0:
                if len(self.buffer) > 4_000_000:
                    del self.buffer[:-1_000_000]
                if self._read_chunk():
                    continue
                if self._reconnect():
                    continue
                return False, None
            frame_bytes = bytes(self.buffer[: end + 2])
            del self.buffer[: end + 2]
            import numpy as np
            frame = self._cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), self._cv2.IMREAD_COLOR)
            if frame is None:
                continue
            self.failures = 0
            return True, frame
        return False, None

    def set(self, *_args) -> bool:
        return True

    def release(self) -> None:
        self.closed = True
        self._close_response()

    def _close_response(self) -> None:
        response = self.response
        self.response = None
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def stream(
    camera_url: str,
    confidence: float,
    every_n_frames: int,
    mission_id: str | None,
    requirement_id: str | None,
    capabilities: list[str],
) -> Generator[bytes, None, None]:
    """Low-latency FIELD stream: camera capture is independent from AI inference."""
    import cv2
    from .vision.scanner import FieldScanner
    from .vision.config import build_config
    from . import api_v2 as gateway

    config = build_config(
        source=camera_url,
        confidence=confidence,
        every_n_frames=max(1, every_n_frames),
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
    )

    cap_lock = Lock()
    shared: dict[str, Any] = {"frame": None, "seq": 0, "closed": False, "error": None}

    def capture_loop() -> None:
        capture = _MjpegCapture(camera_url) if _valid_http_camera_url(camera_url) else cv2.VideoCapture(camera_url)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        while True:
            with cap_lock:
                if shared["closed"]:
                    break
            if not capture.isOpened():
                if isinstance(capture, _MjpegCapture):
                    if not capture._reconnect():
                        shared["error"] = "Camera could not be reopened"
                        time.sleep(0.5)
                    continue
                capture.release()
                time.sleep(0.25)
                capture = cv2.VideoCapture(camera_url)
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            ok, frame = capture.read()
            if not ok or frame is None:
                shared["error"] = "Camera frame read failed; reconnecting"
                if isinstance(capture, _MjpegCapture):
                    if not capture._reconnect():
                        time.sleep(0.5)
                else:
                    capture.release()
                    time.sleep(0.25)
                    capture = cv2.VideoCapture(camera_url)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue
            shared["error"] = None
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
        latest_detections: list[Any] = []
        latest_persisted: list[dict[str, Any]] = []
        seen_evidence_keys: set[str] = set()
        idx = 0
        display_frames = 0
        display_started = time.monotonic()
        capture_fps = 0.0
        last_emit = 0.0

        while True:
            with gateway._lock:
                if gateway._state["stop_token"] != token or not gateway._state["authorized"]:
                    break
            with cap_lock:
                seq = int(shared["seq"])
                frame = shared["frame"]
                capture_error = shared.get("error")
            if frame is None:
                time.sleep(0.002)
                continue
            if seq == last_seq:
                time.sleep(0.002)
                continue
            last_seq = seq
            idx += 1
            latest_frame = frame.copy()

            if seq != last_infer_seq and (seq % max(1, every_n_frames) == 0 or last_infer_seq < 0):
                last_infer_seq = seq
                try:
                    current_gps = dict(gateway._state.get("gps") or {})
                    if scanner is not None:
                        detections, _context, qr, barcode, ocr, persisted = scanner.scan(latest_frame, idx, gps=current_gps)
                        latest_detections = detections
                        filtered_persisted: list[dict[str, Any]] = []
                        for item in persisted:
                            capability = str(item.get("capability") or "evidence")
                            track_id = str(item.get("track_id") or "").strip()
                            if not track_id:
                                matching = next((d for d in latest_detections if str(getattr(d, "label", "")).lower().replace(" ", "_") == capability.lower().replace(" ", "_")), None)
                                track_id = str(getattr(matching, "track_id", "") or "").strip()
                            evidence_key = f"{capability}:{track_id}" if track_id else f"{capability}:single"
                            if evidence_key in seen_evidence_keys:
                                continue
                            seen_evidence_keys.add(evidence_key)
                            item = dict(item)
                            item["track_id"] = track_id or None
                            filtered_persisted.append(item)
                        latest_persisted = filtered_persisted
                    else:
                        latest_detections = []
                        latest_persisted = []
                    scanner_error = None
                except Exception as exc:
                    scanner_error = f"Vision inference failed: {exc}"
                    gateway._set(last_error=scanner_error)

                for detection in latest_detections:
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
                capture_fps = display_frames / max(now - display_started, 0.001)
                display_frames = 0
                display_started = now
            display_frames += 1

            if display.shape[1] > max(320, int(config.stream_max_width)):
                max_width = max(320, int(config.stream_max_width))
                scale = max_width / float(display.shape[1])
                display = cv2.resize(display, (max_width, max(1, int(round(display.shape[0] * scale)))), interpolation=cv2.INTER_AREA)
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 1000), 44), (15, 18, 25), -1)
            cv2.putText(display, f"SENTRY FIELD | CAPTURE {capture_fps:.1f} FPS | AI {len(latest_detections)} findings", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
            if capture_error or scanner_error:
                cv2.putText(display, "STREAM RECOVERING / AI DEGRADED", (14, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 200, 255), 2)
            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality), int(cv2.IMWRITE_JPEG_OPTIMIZE), 0])
            if ok:
                now = time.monotonic()
                if now - last_emit < (1 / 60):
                    continue
                last_emit = now
                with gateway._lock:
                    unique_tracks = {f"{str(getattr(d, 'label', '')).lower()}:{getattr(d, 'track_id', None) or getattr(d, 'bbox', None)}" for d in latest_detections}
                    gateway._state.update({
                        "fps": round(capture_fps, 1),
                        "inference_ms": round(0.0, 1),
                        "findings": len(unique_tracks),
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
        with gateway._lock:
            if gateway._state["stop_token"] == token:
                gateway._state["running"] = False
