from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Generator
from urllib.parse import urlparse

import cv2
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .vision.config import CAPABILITY_ALIASES, DEFAULT_CONFIG, build_config
from .vision.scanner import FieldScanner

ROOT = Path(__file__).resolve().parents[1]
DEMO_TENDER_FILE = ROOT / "sentry_field" / "data" / "demo_tenders.json"
EVIDENCE_DIR = ROOT / "field_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CAMERA_URL = os.getenv("SENTRY_CAMERA_URL", DEFAULT_CONFIG.source)
FIELD_API_PORT = int(os.getenv("SENTRY_FIELD_API_PORT", "8001"))
STREAM_FPS = float(os.getenv("SENTRY_STREAM_FPS", "60"))
JPEG_QUALITY = int(os.getenv("SENTRY_STREAM_JPEG_QUALITY", "78"))

app = FastAPI(title="SENTRY FIELD Low-Latency Gateway", version="0.6.1")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
app.mount("/evidence-files", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence-files")

_lock = Lock()
_state = {
    "running": False, "authorized": False, "camera_url": DEFAULT_CAMERA_URL,
    "fps": 0.0, "capture_fps": 0.0, "inference_fps": 0.0, "inference_ms": 0.0,
    "findings": 0, "evidence": 0, "last_detection": None, "last_identity": None,
    "last_error": None, "updated_at": None, "mission_id": None, "requirement_id": None,
    "tender_id": None, "capabilities": [], "confidence": DEFAULT_CONFIG.confidence,
    "every_n_frames": 1, "machine": None, "demo_site": None, "dispatch_at": None,
    "machine_id": None, "battery": None, "speed": None,
    "gps": {"status": "unavailable", "source": None, "lat": None, "lon": None}, "stop_token": 0,
}
_events: deque[dict] = deque(maxlen=150)


class DispatchRequest(BaseModel):
    tender_id: str
    mission_id: str
    requirement_id: str
    capability: str
    machine: str = "Normal Vision Rover"
    demo_site: str | None = None


class TelemetryRequest(BaseModel):
    machine_id: str
    battery: float | None = None
    speed: float | None = None
    lat: float | None = None
    lon: float | None = None


def _camera(value: str | None) -> str:
    url = (value or DEFAULT_CAMERA_URL).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "Camera URL must be a valid http(s) URL")
    return url


def _caps(values: list[str] | None) -> list[str]:
    allowed = set(CAPABILITY_ALIASES.values())
    if not values:
        return list(allowed)
    out: list[str] = []
    for value in values:
        value = value.strip()
        if value in allowed and value not in out:
            out.append(value)
    if not out:
        raise HTTPException(400, "No valid capabilities selected")
    return out


def _load_demo_tenders() -> list[dict]:
    try:
        rows = json.loads(DEMO_TENDER_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, f"Demo tender catalog unavailable: {exc}") from exc
    if not isinstance(rows, list):
        raise HTTPException(500, "Demo tender catalog must be a JSON list")
    return rows


def _find_tender(tender_key: str) -> dict:
    found = next((row for row in _load_demo_tenders() if row.get("id") == tender_key or row.get("tender_id") == tender_key), None)
    if not found:
        raise HTTPException(404, "Tender not found")
    return found


def _set(**updates):
    with _lock:
        _state.update(updates)
        _state["updated_at"] = time.time()


def _snap() -> dict:
    with _lock:
        snapshot = dict(_state)
        snapshot["gps"] = dict(_state["gps"])
    snapshot.pop("stop_token", None)
    snapshot["recent_events"] = list(_events)
    return snapshot


def _frame_url(event: dict) -> str | None:
    frame_path = event.get("frame_path")
    if not frame_path:
        return None
    path = Path(frame_path)
    try:
        relative = path.relative_to(EVIDENCE_DIR)
    except ValueError:
        return None
    return "/evidence-files/" + "/".join(relative.parts)


@app.get("/health")
def health():
    return JSONResponse({"ok": True, "service": "sentry-field-low-latency", "camera_url": DEFAULT_CAMERA_URL})


@app.get("/capabilities")
def capabilities():
    return JSONResponse({"capabilities": [{"label": key, "value": value} for key, value in CAPABILITY_ALIASES.items()]})


@app.get("/tenders")
def tenders():
    return JSONResponse({"tenders": _load_demo_tenders(), "source": "verified government eProcurement examples + explicit demo inspection profiles"})


@app.get("/tenders/{tender_key}")
def tender(tender_key: str):
    return JSONResponse(_find_tender(tender_key))


@app.get("/status")
def status():
    return JSONResponse(_snap())


@app.get("/events")
def events():
    return JSONResponse({"events": list(_events)})


@app.post("/dispatch")
def dispatch(request: DispatchRequest):
    tender_row = _find_tender(request.tender_id)
    requirement = next((row for row in tender_row.get("requirements", []) if row.get("id") == request.requirement_id), None)
    if requirement is None:
        raise HTTPException(400, "Requirement does not belong to selected tender")
    if requirement.get("capability") != request.capability:
        raise HTTPException(400, "Capability does not match selected requirement")
    if request.machine != tender_row.get("machine"):
        raise HTTPException(400, "Machine does not match the tender field profile")
    with _lock:
        _state["stop_token"] += 1
        _state.update({
            "running": False, "authorized": True, "mission_id": request.mission_id,
            "requirement_id": request.requirement_id, "tender_id": tender_row["id"],
            "capabilities": [request.capability], "machine": request.machine,
            "demo_site": request.demo_site or tender_row.get("demo_site"), "dispatch_at": time.time(),
            "findings": 0, "evidence": 0, "last_detection": None, "last_identity": None, "last_error": None,
        })
        _state["updated_at"] = time.time()
    _events.clear()
    _events.appendleft({
        "type": "dispatch", "mission_id": request.mission_id, "requirement_id": request.requirement_id,
        "tender_id": tender_row["id"], "capability": request.capability, "machine": request.machine,
        "demo_site": request.demo_site or tender_row.get("demo_site"), "observed_at": time.time(),
    })
    return JSONResponse({"ok": True, "authorized": True, "tender": tender_row, "requirement": requirement})


@app.post("/telemetry")
def telemetry(request: TelemetryRequest):
    gps = {"status": "unavailable", "source": request.machine_id, "lat": request.lat, "lon": request.lon}
    if request.lat is not None and request.lon is not None:
        gps["status"] = "live"
    _set(machine_id=request.machine_id, battery=request.battery, speed=request.speed, gps=gps)
    _events.appendleft({
        "type": "telemetry", "machine_id": request.machine_id, "battery": request.battery,
        "speed": request.speed, "gps": gps, "observed_at": time.time(),
        "mission_id": _state.get("mission_id"), "requirement_id": _state.get("requirement_id"),
    })
    return JSONResponse({"ok": True, "gps": gps})


@app.post("/stop")
def stop():
    with _lock:
        _state["stop_token"] += 1
        _state["running"] = False
        _state["authorized"] = False
        _state["updated_at"] = time.time()
    _events.appendleft({"type": "stop", "observed_at": time.time(), "mission_id": _state.get("mission_id")})
    return JSONResponse({"ok": True, "stopped": True})


class LatestFrame:
    """Single-slot newest-frame buffer; old frames are intentionally dropped."""
    def __init__(self):
        self.lock = Lock()
        self.frame = None
        self.index = 0
        self.captured_at = 0.0
        self.closed = False

    def put(self, frame, index: int):
        with self.lock:
            self.frame = frame
            self.index = index
            self.captured_at = time.monotonic()

    def get(self):
        with self.lock:
            if self.frame is None:
                return None, 0, 0.0
            return self.frame.copy(), self.index, self.captured_at

    def close(self):
        with self.lock:
            self.closed = True


def _stream(camera_url: str, confidence: float, mission_id: str | None, requirement_id: str | None, capabilities: list[str]) -> Generator[bytes, None, None]:
    """Capture runs continuously; AI inference runs independently on the newest frame."""
    config = build_config(source=camera_url, confidence=confidence, every_n_frames=1, mission_id=mission_id, requirement_id=requirement_id, capabilities=capabilities)
    scanner = FieldScanner(config)
    cap = cv2.VideoCapture(camera_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    try:
        cap.set(cv2.CAP_PROP_FPS, 60)
    except Exception:
        pass
    if not cap.isOpened():
        _set(running=False, last_error=f"Could not open camera: {camera_url}")
        raise RuntimeError(f"Could not open video source: {camera_url}")

    latest = LatestFrame()
    stop_event = Event()
    shared_lock = Lock()
    shared = {
        "frame": None,
        "frame_index": 0,
        "detections": [],
        "qr": None,
        "barcode": None,
        "ocr": None,
        "detection_frame_index": -1,
    }

    with _lock:
        authorized = _state["authorized"]
        current_token = _state["stop_token"]
    if not authorized:
        cap.release()
        raise HTTPException(403, "Field mission is not authorized; dispatch the mission first")

    _events.clear()
    _set(running=True, authorized=True, camera_url=camera_url, last_error=None, mission_id=mission_id, requirement_id=requirement_id, capabilities=capabilities, confidence=config.confidence, every_n_frames=1)

    def capture_loop():
        index = 0
        period_start = time.monotonic()
        count = 0
        try:
            while not stop_event.is_set():
                with _lock:
                    if _state["stop_token"] != current_token or not _state["authorized"]:
                        break
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.003)
                    continue
                index += 1
                latest.put(frame, index)
                with shared_lock:
                    shared["frame"] = frame
                    shared["frame_index"] = index
                count += 1
                now = time.monotonic()
                if now - period_start >= 0.5:
                    _set(capture_fps=round(count / (now - period_start), 1))
                    count = 0
                    period_start = now
        except Exception as exc:
            _set(last_error=str(exc))
        finally:
            latest.close()

    def inference_loop():
        last_index = -1
        period_start = time.monotonic()
        infer_count = 0
        try:
            while not stop_event.is_set():
                with _lock:
                    if _state["stop_token"] != current_token or not _state["authorized"]:
                        break
                frame, index, _ = latest.get()
                if frame is None or index == last_index:
                    time.sleep(0.001)
                    continue
                last_index = index
                started = time.monotonic()
                detections, _context, qr, barcode, ocr, persisted = scanner.scan(frame, index)
                with shared_lock:
                    shared["detections"] = list(detections)
                    shared["qr"] = qr
                    shared["barcode"] = barcode
                    shared["ocr"] = ocr
                    shared["detection_frame_index"] = index
                for detection in detections:
                    _events.appendleft({
                        "type": detection.label, "capability": detection.label.lower().replace(" ", "_"),
                        "confidence": round(detection.confidence, 3), "bbox": detection.bbox,
                        "detector": detection.detector, "track_id": detection.track_id,
                        "observed_at": time.time(), "mission_id": mission_id, "requirement_id": requirement_id,
                    })
                for item in persisted:
                    event = dict(item)
                    event["type"] = "evidence"
                    event["frame_url"] = _frame_url(event)
                    event["tender_id"] = _state.get("tender_id")
                    event["machine_id"] = _state.get("machine_id")
                    event["gps"] = _state.get("gps")
                    _events.appendleft(event)
                ids = [value for value in (qr, barcode, ocr) if value]
                if ids:
                    _events.appendleft({"type": "identity", "value": " | ".join(ids)[:200], "detector": "qr/barcode/ocr", "observed_at": time.time(), "mission_id": mission_id, "requirement_id": requirement_id})
                elapsed = (time.monotonic() - started) * 1000
                infer_count += 1
                now = time.monotonic()
                window = now - period_start
                if window >= 0.5:
                    _set(inference_fps=round(infer_count / window, 1))
                    infer_count = 0
                    period_start = now
                _set(
                    inference_ms=round(elapsed, 1),
                    findings=len(detections),
                    evidence=sum(1 for event in _events if event.get("type") == "evidence"),
                    last_detection={"type": detections[0].label, "confidence": round(detections[0].confidence, 3), "track_id": detections[0].track_id} if detections else _state.get("last_detection"),
                    last_identity=" | ".join(ids)[:200] if ids else _state.get("last_identity"),
                )
        except Exception as exc:
            _set(running=False, last_error=str(exc))

    capture_thread = Thread(target=capture_loop, name="sentry-camera-capture", daemon=True)
    inference_thread = Thread(target=inference_loop, name="sentry-ai-inference", daemon=True)
    capture_thread.start()
    inference_thread.start()

    frame_interval = 1.0 / max(1.0, STREAM_FPS)
    try:
        while True:
            with _lock:
                if _state["stop_token"] != current_token or not _state["authorized"]:
                    break
            started = time.monotonic()
            with shared_lock:
                frame = shared["frame"].copy() if shared["frame"] is not None else None
                detections = list(shared["detections"])
                ids = [value for value in (shared["qr"], shared["barcode"], shared["ocr"]) if value]
            if frame is None:
                time.sleep(0.002)
                continue
            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
            state = _snap()
            cv2.rectangle(frame, (0, 0), (min(frame.shape[1], 1000), 48), (15, 18, 25), -1)
            cv2.putText(frame, f"SENTRY FIELD | LIVE {state.get('capture_fps', 0):.0f} FPS | AI {state.get('inference_fps', 0):.1f} FPS | {state.get('inference_ms', 0):.0f}ms", (14, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
            if ids:
                cv2.putText(frame, f"ID: {' | '.join(ids)[:110]}", (14, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 0), 2)
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache, no-store, must-revalidate\r\nPragma: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
            elapsed = time.monotonic() - started
            delay = frame_interval - elapsed
            if delay > 0:
                time.sleep(delay)
    finally:
        stop_event.set()
        capture_thread.join(timeout=0.5)
        inference_thread.join(timeout=0.5)
        cap.release()
        with _lock:
            if _state["stop_token"] == current_token:
                _state["running"] = False
        _set()


@app.get("/stream")
def stream(
    camera_url: str | None = Query(None),
    confidence: float = Query(DEFAULT_CONFIG.confidence, ge=.05, le=.99),
    every_n_frames: int = Query(1, ge=1, le=60),
    mission_id: str | None = Query(None),
    requirement_id: str | None = Query(None),
    capabilities: str | None = Query(None),
):
    camera = _camera(camera_url)
    with _lock:
        authorized = _state["authorized"]
        current_mission = _state.get("mission_id")
        current_requirement = _state.get("requirement_id")
    if not authorized:
        raise HTTPException(403, "Field mission is not authorized; dispatch the mission first")
    if mission_id and current_mission and mission_id != current_mission:
        raise HTTPException(409, "Mission does not match the authorized dispatch")
    if requirement_id and current_requirement and requirement_id != current_requirement:
        raise HTTPException(409, "Requirement does not match the authorized dispatch")
    selected = _caps([item for item in (capabilities or "").split(",") if item.strip()] or None)
    return StreamingResponse(_stream(camera, confidence, mission_id or current_mission, requirement_id or current_requirement, selected), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "X-Accel-Buffering": "no"})
