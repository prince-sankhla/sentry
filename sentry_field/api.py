from __future__ import annotations

import os
import time
from collections import deque
from threading import Lock
from typing import Generator
from urllib.parse import urlparse

import cv2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .vision.config import CAPABILITY_ALIASES, DEFAULT_CONFIG, build_config
from .vision.scanner import FieldScanner

DEFAULT_CAMERA_URL = os.getenv("SENTRY_CAMERA_URL", DEFAULT_CONFIG.source)
FIELD_API_PORT = int(os.getenv("SENTRY_FIELD_API_PORT", "8001"))

app = FastAPI(title="SENTRY FIELD Local Gateway", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

_state_lock = Lock()
_state = {
    "running": False,
    "camera_url": DEFAULT_CAMERA_URL,
    "fps": 0.0,
    "inference_ms": 0.0,
    "findings": 0,
    "evidence": 0,
    "last_detection": None,
    "last_identity": None,
    "last_error": None,
    "updated_at": None,
    "mission_id": None,
    "requirement_id": None,
    "capabilities": [],
    "confidence": DEFAULT_CONFIG.confidence,
    "every_n_frames": DEFAULT_CONFIG.every_n_frames,
    "gps": {"status": "unavailable", "source": None, "lat": None, "lon": None},
}
_recent_events: deque[dict] = deque(maxlen=100)


def _camera_url(value: str | None) -> str:
    url = (value or DEFAULT_CAMERA_URL).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Camera URL must be a valid http(s) URL")
    return url


def _normalise_capabilities(values: list[str] | None) -> list[str]:
    allowed = set(CAPABILITY_ALIASES.values())
    if not values:
        return list(allowed)
    result: list[str] = []
    for value in values:
        value = value.strip()
        if value in allowed and value not in result:
            result.append(value)
    if not result:
        raise HTTPException(status_code=400, detail="No valid capabilities selected")
    return result


def _set_state(**updates) -> None:
    with _state_lock:
        _state.update(updates)
        _state["updated_at"] = time.time()


def _snapshot() -> dict:
    with _state_lock:
        snapshot = dict(_state)
    snapshot["recent_events"] = list(_recent_events)
    return snapshot


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "sentry-field", "camera_url": DEFAULT_CAMERA_URL})


@app.get("/capabilities")
def capabilities() -> JSONResponse:
    return JSONResponse({"capabilities": [{"label": label, "value": value} for label, value in CAPABILITY_ALIASES.items()]})


@app.get("/status")
def status() -> JSONResponse:
    return JSONResponse(_snapshot())


@app.get("/events")
def events() -> JSONResponse:
    return JSONResponse({"events": list(_recent_events)})


def _stream(camera_url: str, confidence: float, every_n_frames: int, mission_id: str | None, requirement_id: str | None, capabilities: list[str]) -> Generator[bytes, None, None]:
    config = build_config(source=camera_url, confidence=confidence, every_n_frames=every_n_frames, mission_id=mission_id, requirement_id=requirement_id, capabilities=capabilities)
    scanner = FieldScanner(config)
    capture = cv2.VideoCapture(camera_url)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        _set_state(running=False, last_error=f"Could not open camera: {camera_url}")
        raise RuntimeError(f"Could not open video source: {camera_url}")

    _recent_events.clear()
    _set_state(running=True, camera_url=camera_url, last_error=None, mission_id=mission_id, requirement_id=requirement_id, capabilities=capabilities, confidence=config.confidence, every_n_frames=config.every_n_frames, gps={"status": "unavailable", "source": None, "lat": None, "lon": None})
    frame_index = 0
    previous = time.monotonic()
    fps = 0.0

    try:
        while True:
            started = time.monotonic()
            ok, frame = capture.read()
            if not ok:
                _set_state(running=False, last_error="Camera frame read failed")
                break
            frame_index += 1
            detections, context, qr_value, barcode_value, ocr_text, evidence = scanner.scan(frame, frame_index)
            display = frame.copy()

            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                label = f"{detection.label} {detection.confidence:.2f}"
                if detection.track_id:
                    label += f" [{detection.track_id}]"
                cv2.putText(display, label, (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
                _recent_events.appendleft({"type": detection.label, "confidence": round(detection.confidence, 3), "bbox": detection.bbox, "detector": detection.detector, "track_id": detection.track_id, "observed_at": time.time(), "mission_id": mission_id, "requirement_id": requirement_id})

            identity_parts = [value for value in (qr_value, barcode_value, ocr_text) if value]
            if identity_parts:
                _recent_events.appendleft({"type": "identity", "value": " | ".join(identity_parts)[:200], "detector": "qr/barcode/ocr", "observed_at": time.time(), "mission_id": mission_id, "requirement_id": requirement_id})

            now = time.monotonic()
            dt = now - previous
            previous = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)
            inference_ms = (time.monotonic() - started) * 1000.0
            with _state_lock:
                _state["fps"] = round(fps, 1)
                _state["inference_ms"] = round(inference_ms, 1)
                _state["findings"] = len(detections)
                _state["evidence"] = len(_recent_events)
                _state["last_detection"] = {"type": detections[0].label, "confidence": round(detections[0].confidence, 3), "track_id": detections[0].track_id} if detections else _state.get("last_detection")
                _state["last_identity"] = " | ".join(identity_parts)[:200] if identity_parts else _state.get("last_identity")
                _state["updated_at"] = time.time()

            hud = f"SENTRY FIELD | FPS {fps:.1f} | {inference_ms:.0f}ms | findings {len(detections)}"
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 900), 44), (15, 18, 25), -1)
            cv2.putText(display, hud, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
            if identity_parts:
                cv2.putText(display, f"ID: {' | '.join(identity_parts)[:110]}", (14, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)
            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
    except Exception as exc:
        _set_state(running=False, last_error=str(exc))
        raise
    finally:
        capture.release()
        _set_state(running=False)


@app.get("/stream")
def stream(camera_url: str | None = Query(default=None), confidence: float = Query(default=DEFAULT_CONFIG.confidence, ge=0.05, le=0.99), every_n_frames: int = Query(default=DEFAULT_CONFIG.every_n_frames, ge=1, le=60), mission_id: str | None = Query(default=None), requirement_id: str | None = Query(default=None), capabilities: str | None = Query(default=None)) -> StreamingResponse:
    url = _camera_url(camera_url)
    selected = _normalise_capabilities(capabilities.split(",") if capabilities else None)
    return StreamingResponse(_stream(url, confidence, every_n_frames, mission_id, requirement_id, selected), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
