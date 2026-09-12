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


class DroidCamSocket:
    """Single-connection DroidCam MJPEG reader.

    Reads directly from the TCP socket so an endless multipart response never
    blocks waiting for an arbitrary BufferedReader byte count.
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.closed = False

    def open(self) -> bool:
        if self.closed:
            return False
        self.close()
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
            sock.settimeout(0.5)
            request = (
                f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
                "Accept: multipart/x-mixed-replace,image/jpeg,*/*\r\n"
                "Cache-Control: no-cache\r\nPragma: no-cache\r\n"
                "Connection: keep-alive\r\nUser-Agent: SENTRY-FIELD/1.0\r\n\r\n"
            ).encode("ascii", "ignore")
            sock.sendall(request)
            header = bytearray()
            deadline = time.monotonic() + 5.0
            while b"\r\n\r\n" not in header:
                if time.monotonic() > deadline:
                    sock.close()
                    return False
                part = sock.recv(4096)
                if not part:
                    sock.close()
                    return False
                header.extend(part)
                if len(header) > 64_000:
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
            self.close()
            return False

    def close(self) -> None:
        sock = self.sock
        self.sock = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def read_jpeg(self) -> bytes | None:
        while not self.closed:
            start = self.buffer.find(b"\xff\xd8")
            if start >= 0:
                if start:
                    del self.buffer[:start]
                end = self.buffer.find(b"\xff\xd9", 2)
                if end >= 0:
                    payload = bytes(self.buffer[: end + 2])
                    del self.buffer[: end + 2]
                    return payload
            if self.sock is None and not self.open():
                time.sleep(0.15)
                continue
            try:
                chunk = self.sock.recv(65536) if self.sock is not None else b""
            except socket.timeout:
                continue
            except OSError:
                self.close()
                continue
            if not chunk:
                self.close()
                continue
            self.buffer.extend(chunk)
            if len(self.buffer) > 4_000_000:
                start = self.buffer.find(b"\xff\xd8")
                self.buffer = self.buffer[start:] if start >= 0 else bytearray()
        return None


def _multipart(jpeg: bytes) -> bytes:
    return b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\nCache-Control: no-cache\r\n\r\n" + jpeg + b"\r\n"


def stream(camera_url: str, confidence: float, every_n_frames: int, mission_id: str | None, requirement_id: str | None, capabilities: list[str]) -> Generator[bytes, None, None]:
    import cv2
    import numpy as np

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

    lock = Lock()
    stop = Event()
    shared: dict[str, Any] = {"jpeg": None, "frame": None, "seq": 0, "error": "Connecting to DroidCam…"}
    vision: dict[str, Any] = {"scanner": None, "detections": [], "error": "Vision warming up…", "inference_ms": 0.0}

    def capture_loop() -> None:
        reader = DroidCamSocket(camera_url) if _valid_http(camera_url) else None
        capture = None
        try:
            while not stop.is_set():
                if reader is not None:
                    jpeg = reader.read_jpeg()
                    if jpeg:
                        frame = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            with lock:
                                shared["jpeg"] = jpeg
                                shared["frame"] = frame
                                shared["seq"] += 1
                                shared["error"] = None
                        continue
                    with lock:
                        shared["error"] = "DroidCam reconnecting…"
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
                if not ok or frame is None:
                    capture.release()
                    capture = None
                    continue
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality)])
                if ok:
                    with lock:
                        shared["jpeg"] = encoded.tobytes()
                        shared["frame"] = frame
                        shared["seq"] += 1
                        shared["error"] = None
        finally:
            if reader is not None:
                reader.close()
            if capture is not None:
                capture.release()

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
        interval = 0.30 if config.device == "cpu" else 0.08
        seen_evidence: set[str] = set()
        while not stop.is_set():
            with lock:
                seq = int(shared["seq"])
                frame = shared["frame"]
            now = time.monotonic()
            if frame is None or seq == last_seq or now - last_run < interval:
                time.sleep(0.01)
                continue
            last_seq = seq
            last_run = now
            try:
                with gateway._lock:
                    gps = dict(gateway._state.get("gps") or {})
                detections, _context, qr, barcode, ocr, persisted = scanner.scan(frame.copy(), seq, gps=gps)
                with lock:
                    vision["detections"] = detections
                    vision["inference_ms"] = (time.monotonic() - last_run) * 1000.0
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
                with gateway._lock:
                    gateway._state["last_error"] = None
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
    last_emit = 0.0
    try:
        while not stop.is_set():
            with gateway._lock:
                if gateway._state["stop_token"] != token or not gateway._state["authorized"]:
                    break
            with lock:
                seq = int(shared["seq"])
                jpeg = shared["jpeg"]
                capture_error = shared["error"]
                detections = list(vision["detections"])
                scanner_error = vision["error"]
                inference_ms = float(vision["inference_ms"] or 0.0)
            if jpeg is None or seq == last_seq:
                time.sleep(0.005)
                continue
            last_seq = seq
            now = time.monotonic()
            with gateway._lock:
                unique = {f"{d.label.lower()}:{d.track_id or d.bbox}" for d in detections}
                gateway._state.update({
                    "fps": 0.0,
                    "inference_ms": round(inference_ms, 1),
                    "findings": len(unique),
                    "evidence": len([event for event in gateway._events if event.get("type") == "evidence"]),
                    "last_detection": {"type": detections[0].label, "confidence": round(float(detections[0].confidence), 3), "track_id": detections[0].track_id} if detections else gateway._state.get("last_detection"),
                    "updated_at": time.time(),
                    "last_error": scanner_error or capture_error,
                })
            if now - last_emit >= 1 / 30:
                last_emit = now
                yield _multipart(jpeg)
            else:
                time.sleep(0.001)
    finally:
        stop.set()
        with gateway._lock:
            if gateway._state["stop_token"] == token:
                gateway._state["running"] = False
