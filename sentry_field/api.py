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

from .vision.config import DEFAULT_CONFIG, VisionConfig
from .vision.scanner import FieldScanner


DEFAULT_CAMERA_URL = os.getenv("SENTRY_CAMERA_URL", DEFAULT_CONFIG.source)
FIELD_API_PORT = int(os.getenv("SENTRY_FIELD_API_PORT", "8001"))

app = FastAPI(title="SENTRY FIELD Local Gateway", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_state_lock = Lock()
_state = {
    "running": False,
    "camera_url": DEFAULT_CAMERA_URL,
    "fps": 0.0,
    "findings": 0,
    "evidence": 0,
    "last_detection": None,
    "last_error": None,
    "updated_at": None,
}
_recent_events: deque[dict] = deque(maxlen=50)


def _camera_url(value: str | None) -> str:
    url = (value or DEFAULT_CAMERA_URL).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Camera URL must be a valid http(s) URL")
    return url


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


@app.get("/status")
def status() -> JSONResponse:
    return JSONResponse(_snapshot())


@app.get("/events")
def events() -> JSONResponse:
    return JSONResponse({"events": list(_recent_events)})


def _stream(camera_url: str) -> Generator[bytes, None, None]:
    config = VisionConfig(source=camera_url)
    scanner = FieldScanner(config)
    capture = cv2.VideoCapture(camera_url)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not capture.isOpened():
        _set_state(running=False, last_error=f"Could not open camera: {camera_url}")
        raise RuntimeError(f"Could not open video source: {camera_url}")

    _set_state(running=True, camera_url=camera_url, last_error=None)
    frame_index = 0
    previous = time.monotonic()
    fps = 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                _set_state(running=False, last_error="Camera frame read failed")
                break

            frame_index += 1
            detections, context, qr_value, barcode_value, ocr_text = scanner.scan(frame, frame_index)
            display = frame.copy()

            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                label = f"{detection.label} {detection.confidence:.2f}"
                if detection.track_id:
                    label += f" [{detection.track_id}]"
                cv2.putText(
                    display,
                    label,
                    (x1, max(22, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 0, 0),
                    2,
                )

                event = {
                    "type": detection.label,
                    "confidence": round(detection.confidence, 3),
                    "bbox": detection.bbox,
                    "detector": detection.detector,
                    "track_id": detection.track_id,
                    "observed_at": time.time(),
                }
                _recent_events.appendleft(event)

            now = time.monotonic()
            dt = now - previous
            previous = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt)

            with _state_lock:
                _state["fps"] = round(fps, 1)
                _state["findings"] = len(detections)
                _state["evidence"] = len(_recent_events)
                _state["last_detection"] = (
                    {
                        "type": detections[0].label,
                        "confidence": round(detections[0].confidence, 3),
                        "track_id": detections[0].track_id,
                    }
                    if detections
                    else _state.get("last_detection")
                )
                _state["updated_at"] = time.time()

            hud = f"SENTRY FIELD | FPS {fps:.1f} | findings {len(detections)} | context {len(context)}"
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 760), 44), (15, 18, 25), -1)
            cv2.putText(display, hud, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)

            identity_parts = [value for value in (qr_value, barcode_value, ocr_text) if value]
            if identity_parts:
                cv2.putText(
                    display,
                    f"ID: {' | '.join(identity_parts)[:110]}",
                    (14, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (0, 255, 0),
                    2,
                )

            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if not ok:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Cache-Control: no-cache\r\n\r\n"
                + encoded.tobytes()
                + b"\r\n"
            )
    except GeneratorExit:
        raise
    except Exception as exc:
        _set_state(running=False, last_error=str(exc))
        raise
    finally:
        capture.release()
        _set_state(running=False)


@app.get("/stream")
def stream(camera_url: str | None = Query(default=None)) -> StreamingResponse:
    url = _camera_url(camera_url)
    return StreamingResponse(
        _stream(url),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
