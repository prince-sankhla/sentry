from __future__ import annotations

import os
import time
from collections import deque
from threading import Event, Lock, Thread
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
STREAM_FPS = max(15.0, float(os.getenv("SENTRY_FIELD_STREAM_FPS", "30")))
JPEG_QUALITY = min(95, max(70, int(os.getenv("SENTRY_FIELD_JPEG_QUALITY", "90"))))

app = FastAPI(title="SENTRY FIELD Low-Latency Gateway", version="0.3.0")
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
        payload = dict(_state)
    payload["recent_events"] = list(_recent_events)
    return payload


@app.get("/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "sentry-field-fast", "camera_url": DEFAULT_CAMERA_URL})


@app.get("/status")
def status() -> JSONResponse:
    return JSONResponse(_snapshot())


@app.get("/events")
def events() -> JSONResponse:
    return JSONResponse({"events": list(_recent_events)})


class _LatestCamera:
    """Drain DroidCam continuously so slow inference never accumulates stale frames."""

    def __init__(self, capture: cv2.VideoCapture) -> None:
        self.capture = capture
        self.stop = Event()
        self.ready = Event()
        self.lock = Lock()
        self.frame = None
        self.sequence = 0
        self.thread = Thread(target=self._run, name="sentry-field-camera", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        while not self.stop.is_set():
            ok, frame = self.capture.read()
            if not ok:
                time.sleep(0.01)
                continue
            with self.lock:
                self.frame = frame
                self.sequence += 1
            self.ready.set()

    def get_latest(self, after: int):
        while not self.stop.is_set():
            with self.lock:
                if self.frame is not None and self.sequence != after:
                    return self.sequence, self.frame.copy()
            self.ready.wait(0.05)
            self.ready.clear()
        return after, None

    def close(self) -> None:
        self.stop.set()
        self.ready.set()
        self.thread.join(timeout=1)
        self.capture.release()


def _stream(camera_url: str) -> Generator[bytes, None, None]:
    config = VisionConfig(source=camera_url)
    scanner = FieldScanner(config)
    capture = cv2.VideoCapture(camera_url)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        _set_state(running=False, last_error=f"Could not open camera: {camera_url}")
        raise RuntimeError(f"Could not open video source: {camera_url}")

    camera = _LatestCamera(capture)
    camera.start()
    _set_state(running=True, camera_url=camera_url, last_error=None)

    processed = 0
    inference_fps = 0.0
    previous = time.monotonic()
    latest_jpeg: bytes | None = None
    next_emit = time.monotonic()

    try:
        while not camera.stop.is_set():
            sequence, frame = camera.get_latest(processed)
            if frame is not None:
                processed = sequence
                detections, context, qr_value, barcode_value, ocr_text = scanner.scan(frame, sequence)
                display = frame.copy()

                for detection in detections:
                    x1, y1, x2, y2 = detection.bbox
                    cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    label = f"{detection.label} {detection.confidence:.2f}"
                    if detection.track_id:
                        label += f" [{detection.track_id}]"
                    cv2.putText(display, label, (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
                    _recent_events.appendleft({
                        "type": detection.label,
                        "confidence": round(detection.confidence, 3),
                        "bbox": detection.bbox,
                        "detector": detection.detector,
                        "track_id": detection.track_id,
                        "observed_at": time.time(),
                    })

                now = time.monotonic()
                dt = now - previous
                previous = now
                if dt > 0:
                    sample = 1.0 / dt
                    inference_fps = sample if not inference_fps else 0.85 * inference_fps + 0.15 * sample

                with _state_lock:
                    _state["fps"] = round(inference_fps, 1)
                    _state["findings"] = len(detections)
                    _state["evidence"] = len(_recent_events)
                    _state["last_detection"] = ({
                        "type": detections[0].label,
                        "confidence": round(detections[0].confidence, 3),
                        "track_id": detections[0].track_id,
                    } if detections else _state.get("last_detection"))
                    _state["updated_at"] = time.time()

                hud = f"SENTRY FIELD | INF {inference_fps:.1f} | findings {len(detections)} | context {len(context)}"
                cv2.rectangle(display, (0, 0), (min(display.shape[1], 760), 44), (15, 18, 25), -1)
                cv2.putText(display, hud, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
                identity_parts = [v for v in (qr_value, barcode_value, ocr_text) if v]
                if identity_parts:
                    cv2.putText(display, f"ID: {' | '.join(identity_parts)[:110]}", (14, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)

                ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if ok:
                    latest_jpeg = encoded.tobytes()

            if latest_jpeg is None:
                continue

            now = time.monotonic()
            if now < next_emit:
                time.sleep(min(0.005, next_emit - now))
                continue
            next_emit = now + (1.0 / STREAM_FPS)
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n"
                b"Cache-Control: no-cache, no-store, must-revalidate\r\n"
                b"Pragma: no-cache\r\n\r\n" + latest_jpeg + b"\r\n"
            )
    except GeneratorExit:
        raise
    except Exception as exc:
        _set_state(running=False, last_error=str(exc))
        raise
    finally:
        camera.close()
        _set_state(running=False)


@app.get("/stream")
def stream(camera_url: str | None = Query(default=None)) -> StreamingResponse:
    return StreamingResponse(
        _stream(_camera_url(camera_url)),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )
