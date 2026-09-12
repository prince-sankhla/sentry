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


class DroidCamReader:
    """Raw HTTP/MJPEG reader. Camera transport never depends on the vision stack."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.closed = False

    def close_socket(self) -> None:
        sock = self.sock
        self.sock = None
        if sock is None:
            return
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass

    def open(self) -> bool:
        if self.closed:
            return False
        self.close_socket()
        parsed = urlparse(self.url)
        host = parsed.hostname
        if not host:
            return False
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        try:
            sock = socket.create_connection((host, port), timeout=5.0)
            sock.settimeout(1.0)
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "Accept: multipart/x-mixed-replace,image/jpeg,*/*\r\n"
                "Cache-Control: no-cache\r\n"
                "Pragma: no-cache\r\n"
                "Connection: keep-alive\r\n"
                "User-Agent: SENTRY-FIELD/1.0\r\n\r\n"
            ).encode("ascii", "ignore")
            sock.sendall(request)
            header = bytearray()
            deadline = time.monotonic() + 5.0
            while b"\r\n\r\n" not in header:
                if time.monotonic() > deadline:
                    sock.close()
                    return False
                try:
                    chunk = sock.recv(8192)
                except socket.timeout:
                    continue
                if not chunk:
                    sock.close()
                    return False
                header.extend(chunk)
                if len(header) > 128_000:
                    sock.close()
                    return False
            marker = header.find(b"\r\n\r\n")
            status = header.split(b"\r\n", 1)[0]
            if b" 200 " not in status:
                sock.close()
                return False
            self.sock = sock
            self.buffer = bytearray(header[marker + 4 :])
            return True
        except OSError:
            self.close_socket()
            return False

    def read_jpeg(self) -> bytes | None:
        while not self.closed:
            start = self.buffer.find(b"\xff\xd8")
            if start >= 0:
                if start:
                    del self.buffer[:start]
                end = self.buffer.find(b"\xff\xd9", 2)
                if end >= 0:
                    jpeg = bytes(self.buffer[: end + 2])
                    del self.buffer[: end + 2]
                    return jpeg
            if self.sock is None and not self.open():
                time.sleep(0.15)
                continue
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
                self.buffer = self.buffer[start:] if start >= 0 else bytearray()
        return None

    def close(self) -> None:
        self.closed = True
        self.close_socket()


def _multipart(jpeg: bytes) -> bytes:
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Content-Length: " + str(len(jpeg)).encode("ascii") +
        b"\r\nCache-Control: no-cache\r\n\r\n" + jpeg + b"\r\n"
    )


def _diagnostic(text: str) -> bytes:
    try:
        import cv2
        import numpy as np

        frame = np.zeros((300, 900, 3), dtype=np.uint8)
        cv2.putText(frame, "SENTRY FIELD", (25, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2)
        cv2.putText(frame, text[:100], (25, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
        return _multipart(encoded.tobytes()) if ok else b""
    except Exception:
        return b""


def stream(
    camera_url: str,
    confidence: float,
    every_n_frames: int,
    mission_id: str | None,
    requirement_id: str | None,
    capabilities: list[str],
) -> Generator[bytes, None, None]:
    """Canonical single FIELD camera+AI stream.

    Camera transport is independent from CV/model startup. The browser receives
    raw camera JPEGs immediately; once the scanner is ready, annotated frames
    replace the raw frames without changing the mission or opening a second
    camera connection.
    """
    from . import api_v2 as gateway
    from .vision.config import build_config

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
    shared: dict[str, Any] = {
        "jpeg": None,
        "frame": None,
        "seq": 0,
        "camera_error": f"Connecting to {camera_url}",
        "annotated": None,
    }
    vision: dict[str, Any] = {
        "scanner": None,
        "detections": [],
        "error": "Vision warming up…",
        "inference_ms": 0.0,
    }

    def capture_loop() -> None:
        reader: DroidCamReader | None = DroidCamReader(camera_url) if _valid_http(camera_url) else None
        capture = None
        try:
            # Camera path uses stdlib socket first; cv2 is only needed for non-HTTP sources.
            while not stop.is_set():
                if reader is not None:
                    jpeg = reader.read_jpeg()
                    if jpeg:
                        with frame_lock:
                            shared["jpeg"] = jpeg
                            shared["camera_error"] = None
                            shared["seq"] += 1
                        continue
                    with frame_lock:
                        shared["camera_error"] = "DroidCam reconnecting…"
                    time.sleep(0.10)
                    continue

                try:
                    import cv2
                except Exception as exc:
                    with frame_lock:
                        shared["camera_error"] = f"OpenCV unavailable: {exc}"
                    time.sleep(1.0)
                    continue
                if capture is None:
                    capture = cv2.VideoCapture(camera_url)
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not capture.isOpened():
                    capture.release()
                    capture = None
                    with frame_lock:
                        shared["camera_error"] = "Camera open failed; retrying…"
                    time.sleep(0.25)
                    continue
                ok, frame = capture.read()
                if not ok or frame is None:
                    capture.release()
                    capture = None
                    continue
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality)])
                if ok:
                    with frame_lock:
                        shared["jpeg"] = encoded.tobytes()
                        shared["frame"] = frame
                        shared["camera_error"] = None
                        shared["seq"] += 1
        finally:
            if reader is not None:
                reader.close()
            if capture is not None:
                capture.release()

    def vision_loop() -> None:
        # Vision imports and model construction can fail without taking down camera relay.
        try:
            import cv2
            import numpy as np
            from .vision.scanner import FieldScanner

            scanner = FieldScanner(config)
            with frame_lock:
                vision["scanner"] = scanner
                vision["error"] = None
        except Exception as exc:
            with frame_lock:
                vision["error"] = f"Vision unavailable: {exc}"
            gateway._set(last_error=vision["error"])
            return

        last_seq = -1
        last_run = 0.0
        interval = 0.30 if config.device == "cpu" else 0.08
        seen_evidence: set[str] = set()

        while not stop.is_set():
            with frame_lock:
                seq = int(shared["seq"])
                jpeg = shared["jpeg"]
            now = time.monotonic()
            if jpeg is None or seq == last_seq or now - last_run < interval:
                time.sleep(0.01)
                continue
            last_seq = seq
            last_run = now
            try:
                frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                started = time.monotonic()
                with gateway._lock:
                    gps = dict(gateway._state.get("gps") or {})
                detections, _context, qr, barcode, ocr, persisted = scanner.scan(frame, seq, gps=gps)
                inference_ms = (time.monotonic() - started) * 1000.0

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

                identities = [value for value in (qr, barcode, ocr) if value]
                if identities:
                    gateway._events.appendleft({
                        "type": "identity",
                        "value": " | ".join(identities)[:200],
                        "detector": "qr/barcode/ocr",
                        "observed_at": time.time(),
                        "mission_id": mission_id,
                        "requirement_id": requirement_id,
                        "tender_id": gateway._state.get("tender_id"),
                        "gps": gps,
                    })

                display = frame.copy()
                for detection in detections:
                    x1, y1, x2, y2 = detection.bbox
                    cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(display, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
                if display.shape[1] > max(320, int(config.stream_max_width)):
                    width = max(320, int(config.stream_max_width))
                    scale = width / float(display.shape[1])
                    display = cv2.resize(display, (width, max(1, int(round(display.shape[0] * scale)))), interpolation=cv2.INTER_AREA)
                cv2.rectangle(display, (0, 0), (min(display.shape[1], 1000), 44), (15, 18, 25), -1)
                cv2.putText(display, f"SENTRY FIELD | AI {inference_ms:.0f}ms | {len(detections)} findings", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality)])
                with frame_lock:
                    vision["detections"] = detections
                    vision["inference_ms"] = inference_ms
                    vision["error"] = None
                    if ok:
                        shared["annotated"] = encoded.tobytes()
                gateway._set(last_error=None)
            except Exception as exc:
                with frame_lock:
                    vision["error"] = f"Vision inference failed: {exc}"
                gateway._set(last_error=vision["error"])

    Thread(target=capture_loop, daemon=True, name="sentry-field-camera").start()
    Thread(target=vision_loop, daemon=True, name="sentry-field-vision").start()

    with gateway._lock:
        gateway._state["stop_token"] += 1
        token = gateway._state["stop_token"]
    gateway._set(
        running=True,
        authorized=True,
        camera_url=camera_url,
        last_error=f"Connecting to camera: {camera_url}",
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
        confidence=config.confidence,
        every_n_frames=config.every_n_frames,
    )
    gateway._events.appendleft({
        "type": "stream_start",
        "mission_id": mission_id,
        "requirement_id": requirement_id,
        "camera_url": camera_url,
        "capabilities": capabilities,
        "observed_at": time.time(),
    })

    # Send bytes immediately so the browser never waits for AI/model initialization.
    diagnostic = _diagnostic("Camera connected / vision warming up…")
    if diagnostic:
        yield diagnostic

    last_seq = -1
    last_emit = 0.0
    try:
        while not stop.is_set():
            with gateway._lock:
                if gateway._state["stop_token"] != token or not gateway._state["authorized"]:
                    break
            with frame_lock:
                seq = int(shared["seq"])
                raw = shared["jpeg"]
                annotated = shared["annotated"]
                camera_error = shared["camera_error"]
                vision_error = vision["error"]
                inference_ms = float(vision["inference_ms"] or 0.0)
                findings = len(vision["detections"])
            if raw is None or seq == last_seq:
                time.sleep(0.005)
                continue
            last_seq = seq
            jpeg = annotated or raw
            now = time.monotonic()
            if now - last_emit < 1 / 25:
                time.sleep(0.001)
                continue
            last_emit = now
            with gateway._lock:
                gateway._state.update({
                    "fps": 0.0,
                    "inference_ms": round(inference_ms, 1),
                    "findings": findings,
                    "evidence": len([event for event in gateway._events if event.get("type") == "evidence"]),
                    "updated_at": time.time(),
                    "last_error": vision_error or camera_error,
                })
            yield _multipart(jpeg)
    finally:
        stop.set()
        with gateway._lock:
            if gateway._state["stop_token"] == token:
                gateway._state["running"] = False
                gateway._state["last_error"] = None
