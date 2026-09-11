from __future__ import annotations

import time
from threading import Event, Lock, Thread
from typing import Any, Generator
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener


def _valid_http(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class MjpegReader:
    def __init__(self, source: str) -> None:
        import cv2

        self.source = source
        self.cv2 = cv2
        self.response = None
        self.buffer = bytearray()
        self.closed = False
        self.opener = build_opener(ProxyHandler({}))
        self.opened_at = 0.0

    def open(self) -> bool:
        if self.closed:
            return False
        try:
            self.close_response()
            req = Request(
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
            self.response = self.opener.open(req, timeout=5)
            try:
                sock = self.response.fp.raw._sock  # type: ignore[attr-defined]
                sock.settimeout(None)
            except Exception:
                pass
            content_type = str(self.response.headers.get("Content-Type") or "").lower()
            if "multipart" not in content_type and "image/jpeg" not in content_type:
                self.close_response()
                return False
            self.buffer.clear()
            self.opened_at = time.monotonic()
            return True
        except Exception:
            self.close_response()
            return False

    def close_response(self) -> None:
        response = self.response
        self.response = None
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    def read(self):
        import numpy as np

        while not self.closed:
            if self.response is None and not self.open():
                time.sleep(0.15)
                continue
            try:
                chunk = self.response.read(32768) if self.response is not None else b""
            except Exception:
                self.close_response()
                continue
            if not chunk:
                self.close_response()
                continue
            self.buffer.extend(chunk)
            while True:
                start = self.buffer.find(b"\xff\xd8")
                if start < 0:
                    if len(self.buffer) > 2_000_000:
                        del self.buffer[:-500_000]
                    break
                if start:
                    del self.buffer[:start]
                end = self.buffer.find(b"\xff\xd9", 2)
                if end < 0:
                    break
                payload = bytes(self.buffer[: end + 2])
                del self.buffer[: end + 2]
                frame = self.cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), self.cv2.IMREAD_COLOR)
                if frame is not None:
                    return True, frame
        return False, None

    def close(self) -> None:
        self.closed = True
        self.close_response()


def _diagnostic_frame(text: str) -> bytes:
    import cv2
    import numpy as np

    frame = np.zeros((360, 960, 3), dtype=np.uint8)
    cv2.putText(frame, "SENTRY FIELD", (28, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    cv2.putText(frame, text[:90], (28, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 220, 255), 2)
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        return b""
    return b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"


def stream(
    camera_url: str,
    confidence: float,
    every_n_frames: int,
    mission_id: str | None,
    requirement_id: str | None,
    capabilities: list[str],
) -> Generator[bytes, None, None]:
    """FIELD stream with immediate camera output, automatic OpenCV fallback, and isolated AI worker."""
    import cv2
    import numpy as np

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
        bootstrap_models=False,
    )

    lock = Lock()
    stop = Event()
    state: dict[str, Any] = {"frame": None, "seq": 0, "capture_error": None}
    vision: dict[str, Any] = {"scanner": None, "detections": [], "error": "Vision warming up…", "inference_ms": 0.0}

    def capture_loop() -> None:
        reader: MjpegReader | None = MjpegReader(camera_url) if _valid_http(camera_url) else None
        cv_cap = None
        use_cv = False
        started = time.monotonic()
        try:
            while not stop.is_set():
                if reader is not None and not use_cv:
                    ok, frame = reader.read()
                    if ok and frame is not None:
                        started = time.monotonic()
                        with lock:
                            state["frame"] = frame
                            state["seq"] += 1
                            state["capture_error"] = None
                        continue
                    if time.monotonic() - started > 2.5:
                        reader.close()
                        use_cv = True
                        state["capture_error"] = "MJPEG reader fallback → OpenCV"
                        cv_cap = cv2.VideoCapture(camera_url)
                        cv_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        continue
                if cv_cap is None:
                    cv_cap = cv2.VideoCapture(camera_url)
                    cv_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not cv_cap.isOpened():
                    cv_cap.release()
                    cv_cap = None
                    time.sleep(0.25)
                    continue
                ok, frame = cv_cap.read()
                if ok and frame is not None:
                    with lock:
                        state["frame"] = frame
                        state["seq"] += 1
                        state["capture_error"] = None
                    continue
                cv_cap.release()
                cv_cap = None
                time.sleep(0.1)
        finally:
            if reader is not None:
                reader.close()
            if cv_cap is not None:
                cv_cap.release()

    def vision_loop() -> None:
        try:
            scanner = FieldScanner(config)
            with lock:
                vision["scanner"] = scanner
                vision["error"] = None
        except Exception as exc:
            with lock:
                vision["error"] = f"Vision models unavailable: {exc}"
            return

        last_seq = -1
        last_run = 0.0
        interval = 0.32 if config.device == "cpu" else 0.10
        while not stop.is_set():
            with lock:
                seq = int(state["seq"])
                frame = state["frame"]
            now = time.monotonic()
            if frame is None or seq == last_seq or now - last_run < interval:
                time.sleep(0.01)
                continue
            last_seq = seq
            last_run = now
            started = time.monotonic()
            try:
                with gateway._lock:
                    gps = dict(gateway._state.get("gps") or {})
                detections, _context, qr, barcode, ocr, persisted = scanner.scan(frame.copy(), max(1, seq), gps=gps)
                with lock:
                    vision["detections"] = detections
                    vision["error"] = None
                    vision["inference_ms"] = (time.monotonic() - started) * 1000.0
                for item in persisted:
                    key = f"{item.get('capability') or 'evidence'}:{item.get('track_id') or 'single'}"
                    with gateway._lock:
                        seen = gateway._state.setdefault("seen_evidence_keys", set())
                    if key in seen:
                        continue
                    seen.add(key)
                    event = dict(item)
                    event["type"] = "evidence"
                    event["frame_url"] = gateway._frame_url(event)
                    event["tender_id"] = gateway._state.get("tender_id")
                    event["machine_id"] = gateway._state.get("machine_id")
                    event["gps"] = gps
                    gateway._events.appendleft(event)
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
                        "gps": gps,
                    })
            except Exception as exc:
                with lock:
                    vision["error"] = f"Vision inference failed: {exc}"

    Thread(target=capture_loop, daemon=True, name="sentry-field-capture").start()
    Thread(target=vision_loop, daemon=True, name="sentry-field-vision").start()

    with gateway._lock:
        gateway._state["stop_token"] += 1
        token = gateway._state["stop_token"]
        gateway._state["seen_evidence_keys"] = set()
    gateway._set(
        running=True,
        authorized=True,
        camera_url=camera_url,
        last_error="Camera connecting…",
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
        confidence=config.confidence,
        every_n_frames=config.every_n_frames,
    )
    gateway._events.clear()
    gateway._events.appendleft({"type": "dispatch", "mission_id": mission_id, "requirement_id": requirement_id, "tender_id": gateway._state.get("tender_id"), "capabilities": capabilities, "observed_at": time.time()})

    last_seq = -1
    latest = np.zeros((360, 640, 3), dtype=np.uint8)
    last_emit = 0.0
    display_frames = 0
    display_started = time.monotonic()
    fps = 0.0

    try:
        # Yield immediately so the browser knows /stream is alive even while camera/model starts.
        placeholder = _diagnostic_frame("Connecting to DroidCam…")
        if placeholder:
            yield placeholder
        while not stop.is_set():
            with gateway._lock:
                if gateway._state["stop_token"] != token or not gateway._state["authorized"]:
                    break
            with lock:
                seq = int(state["seq"])
                frame = state["frame"]
                capture_error = state["capture_error"]
            with lock:
                detections = list(vision["detections"])
                scanner_error = vision["error"]
                inference_ms = float(vision["inference_ms"] or 0.0)
            if frame is not None and seq != last_seq:
                last_seq = seq
                latest = frame.copy()

            display = latest.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(display, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

            now = time.monotonic()
            if now - display_started >= 1.0:
                fps = display_frames / max(now - display_started, 0.001)
                display_frames = 0
                display_started = now
            display_frames += 1
            h, w = display.shape[:2]
            if w > config.stream_max_width:
                scale = config.stream_max_width / float(w)
                display = cv2.resize(display, (config.stream_max_width, max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 1000), 46), (15, 18, 25), -1)
            cv2.putText(display, f"SENTRY FIELD | CAPTURE {fps:.1f} FPS | AI {inference_ms:.0f}ms | {len(detections)} findings", (14, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            if capture_error or scanner_error:
                cv2.putText(display, str(scanner_error or capture_error)[:100], (14, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 2)
            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality), int(cv2.IMWRITE_JPEG_OPTIMIZE), 0])
            if ok and time.monotonic() - last_emit >= (1.0 / 25.0):
                last_emit = time.monotonic()
                with gateway._lock:
                    unique = {f"{d.label.lower()}:{d.track_id or d.bbox}" for d in detections}
                    gateway._state.update({
                        "fps": round(fps, 1),
                        "inference_ms": round(inference_ms, 1),
                        "findings": len(unique),
                        "evidence": len([e for e in gateway._events if e.get("type") == "evidence"]),
                        "last_detection": {"type": detections[0].label, "confidence": round(float(detections[0].confidence), 3), "track_id": detections[0].track_id} if detections else gateway._state.get("last_detection"),
                        "updated_at": time.time(),
                    })
                    if scanner_error:
                        gateway._state["last_error"] = scanner_error
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
            time.sleep(0.002)
    finally:
        stop.set()
        with gateway._lock:
            if gateway._state["stop_token"] == token:
                gateway._state["running"] = False
