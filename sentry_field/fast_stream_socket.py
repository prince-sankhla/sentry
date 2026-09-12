from __future__ import annotations

import socket
import time
from threading import Event, Lock, Thread
from typing import Any, Generator
from urllib.parse import urlparse


def _valid_http(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == "http" and bool(parsed.hostname)


class SocketMjpegReader:
    """Small raw-socket MJPEG reader for DroidCam HTTP streams.

    urllib/BufferedReader can wait for a requested byte count on an endless
    multipart response. Reading directly from the socket avoids that behaviour.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.closed = False

    def open(self) -> bool:
        if self.closed:
            return False
        self.close_socket()
        parsed = urlparse(self.source)
        host = parsed.hostname
        if not host:
            return False
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.settimeout(2.0)
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "Accept: multipart/x-mixed-replace,image/jpeg,*/*\r\n"
                "Cache-Control: no-cache\r\n"
                "Pragma: no-cache\r\n"
                "Connection: keep-alive\r\n"
                "User-Agent: SENTRY-FIELD/1.0\r\n\r\n"
            ).encode("ascii", errors="ignore")
            sock.sendall(request)
            header = bytearray()
            deadline = time.monotonic() + 5.0
            while b"\r\n\r\n" not in header:
                if time.monotonic() > deadline:
                    sock.close()
                    return False
                chunk = sock.recv(8192)
                if not chunk:
                    sock.close()
                    return False
                header.extend(chunk)
                if len(header) > 128_000:
                    sock.close()
                    return False
            head_end = header.find(b"\r\n\r\n") + 4
            status_line = header.split(b"\r\n", 1)[0]
            if b" 200 " not in status_line:
                sock.close()
                return False
            content_type = header[:head_end].lower()
            if b"multipart" not in content_type and b"image/jpeg" not in content_type:
                sock.close()
                return False
            self.sock = sock
            self.buffer = bytearray(header[head_end:])
            return True
        except OSError:
            self.close_socket()
            return False

    def close_socket(self) -> None:
        sock = self.sock
        self.sock = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def read(self):
        import cv2
        import numpy as np

        while not self.closed:
            if self.sock is None and not self.open():
                time.sleep(0.15)
                continue

            start = self.buffer.find(b"\xff\xd8")
            if start >= 0:
                if start:
                    del self.buffer[:start]
                end = self.buffer.find(b"\xff\xd9", 2)
                if end >= 0:
                    payload = bytes(self.buffer[: end + 2])
                    del self.buffer[: end + 2]
                    frame = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        return True, frame

            try:
                chunk = self.sock.recv(65536) if self.sock is not None else b""
            except socket.timeout:
                continue
            except OSError:
                self.close_socket()
                continue
            if not chunk:
                self.close_socket()
                continue
            self.buffer.extend(chunk)
            if len(self.buffer) > 4_000_000:
                start = self.buffer.find(b"\xff\xd8")
                self.buffer = self.buffer[start if start >= 0 else -1_000_000 :]
        return False, None

    def close(self) -> None:
        self.closed = True
        self.close_socket()


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
    import cv2

    from . import api_v2 as gateway
    from .vision.config import build_config
    from .vision.scanner import FieldScanner

    config = build_config(
        source=camera_url,
        confidence=confidence,
        every_n_frames=max(1, every_n_frames),
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
        bootstrap_models=False,
    )

    frame_lock = Lock()
    stop = Event()
    shared: dict[str, Any] = {"frame": None, "seq": 0, "error": "Camera connecting…"}
    vision: dict[str, Any] = {"scanner": None, "detections": [], "error": "Vision warming up…", "inference_ms": 0.0}

    def capture_loop() -> None:
        reader = SocketMjpegReader(camera_url) if _valid_http(camera_url) else None
        capture = None
        try:
            while not stop.is_set():
                if reader is not None:
                    ok, frame = reader.read()
                    if ok and frame is not None:
                        with frame_lock:
                            shared["frame"] = frame
                            shared["seq"] += 1
                            shared["error"] = None
                        continue
                    with frame_lock:
                        shared["error"] = "DroidCam MJPEG reconnecting…"
                    time.sleep(0.15)
                    continue

                if capture is None:
                    capture = cv2.VideoCapture(camera_url)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not capture.isOpened():
                    capture.release()
                    capture = None
                    time.sleep(0.25)
                    continue
                ok, frame = capture.read()
                if ok and frame is not None:
                    with frame_lock:
                        shared["frame"] = frame
                        shared["seq"] += 1
                        shared["error"] = None
                else:
                    capture.release()
                    capture = None
                    time.sleep(0.1)
        finally:
            if reader is not None:
                reader.close()
            if capture is not None:
                capture.release()

    def vision_loop() -> None:
        try:
            scanner = FieldScanner(config)
            with frame_lock:
                vision["scanner"] = scanner
                vision["error"] = None
        except Exception as exc:
            with frame_lock:
                vision["error"] = f"Vision models unavailable: {exc}"
            return

        last_seq = -1
        last_run = 0.0
        interval = 0.28 if config.device == "cpu" else 0.08
        seen_evidence: set[str] = set()
        while not stop.is_set():
            with frame_lock:
                seq = int(shared["seq"])
                frame = shared["frame"]
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
                with frame_lock:
                    vision["detections"] = detections
                    vision["inference_ms"] = (time.monotonic() - started) * 1000.0
                    vision["error"] = None
                for item in persisted:
                    capability = str(item.get("capability") or "evidence")
                    track_id = str(item.get("track_id") or "").strip()
                    key = f"{capability}:{track_id or 'single'}"
                    if key in seen_evidence:
                        continue
                    seen_evidence.add(key)
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
                with frame_lock:
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

    latest = None
    last_seq = -1
    display_frames = 0
    display_started = time.monotonic()
    fps = 0.0
    last_emit = 0.0

    try:
        first = _diagnostic_frame("Connecting to DroidCam…")
        if first:
            yield first
        while not stop.is_set():
            with gateway._lock:
                if gateway._state["stop_token"] != token or not gateway._state["authorized"]:
                    break
            with frame_lock:
                seq = int(shared["seq"])
                frame = shared["frame"]
                capture_error = shared["error"]
                detections = list(vision["detections"])
                scanner_error = vision["error"]
                inference_ms = float(vision["inference_ms"] or 0.0)
            if frame is not None and seq != last_seq:
                last_seq = seq
                latest = frame.copy()
            if latest is None:
                time.sleep(0.005)
                continue

            display = latest.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(display, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)

            now = time.monotonic()
            display_frames += 1
            if now - display_started >= 1.0:
                fps = display_frames / max(now - display_started, 0.001)
                display_frames = 0
                display_started = now
            if display.shape[1] > config.stream_max_width:
                scale = config.stream_max_width / float(display.shape[1])
                display = cv2.resize(display, (config.stream_max_width, max(1, int(display.shape[0] * scale))), interpolation=cv2.INTER_AREA)
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 1000), 46), (15, 18, 25), -1)
            cv2.putText(display, f"SENTRY FIELD | CAMERA {fps:.1f} FPS | AI {inference_ms:.0f}ms | {len(detections)} findings", (14, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            if capture_error or scanner_error:
                cv2.putText(display, str(scanner_error or capture_error)[:100], (14, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 2)

            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality)])
            if not ok:
                continue
            now = time.monotonic()
            if now - last_emit < 1 / 25:
                time.sleep(0.001)
                continue
            last_emit = now
            with gateway._lock:
                unique = {f"{d.label.lower()}:{d.track_id or d.bbox}" for d in detections}
                gateway._state.update({
                    "fps": round(fps, 1),
                    "inference_ms": round(inference_ms, 1),
                    "findings": len(unique),
                    "evidence": len([event for event in gateway._events if event.get("type") == "evidence"]),
                    "last_detection": {"type": detections[0].label, "confidence": round(float(detections[0].confidence), 3), "track_id": detections[0].track_id} if detections else gateway._state.get("last_detection"),
                    "updated_at": time.time(),
                    "last_error": scanner_error or capture_error,
                })
            yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
    finally:
        stop.set()
        with gateway._lock:
            if gateway._state["stop_token"] == token:
                gateway._state["running"] = False
