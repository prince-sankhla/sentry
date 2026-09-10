from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Generator
from urllib.error import URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .vision.config import CAPABILITY_ALIASES, DEFAULT_CONFIG, build_config

ROOT = Path(__file__).resolve().parents[1]
DEMO_TENDER_FILE = ROOT / "sentry_field" / "data" / "demo_tenders.json"
EVIDENCE_DIR = ROOT / "field_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CAMERA_URL = os.getenv("SENTRY_CAMERA_URL", DEFAULT_CONFIG.source)
BACKEND_URL = os.getenv("SENTRY_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
FIELD_API_PORT = int(os.getenv("SENTRY_FIELD_API_PORT", "8001"))

app = FastAPI(title="SENTRY FIELD Local Gateway", version="0.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/evidence-files", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence-files")

_lock = Lock()
_state: dict[str, Any] = {
    "running": False,
    "authorized": False,
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
    "tender_id": None,
    "capabilities": [],
    "confidence": DEFAULT_CONFIG.confidence,
    "every_n_frames": DEFAULT_CONFIG.every_n_frames,
    "machine": None,
    "demo_site": None,
    "dispatch_at": None,
    "machine_id": None,
    "battery": None,
    "speed": None,
    "gps": {"status": "unavailable", "source": None, "lat": None, "lon": None, "accuracy_m": None, "captured_at": None, "received_at": None, "mission_id": None, "requirement_id": None, "tender_id": None},
    "stop_token": 0,
}
_events: deque[dict[str, Any]] = deque(maxlen=500)


class DispatchRequest(BaseModel):
    tender_id: str
    mission_id: str
    requirement_id: str
    capability: str
    capabilities: list[str] = Field(default_factory=list)
    machine: str = "Normal Vision Rover"
    demo_site: str | None = None


class TelemetryRequest(BaseModel):
    machine_id: str
    battery: float | None = None
    speed: float | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class MobileGpsRequest(BaseModel):
    tender_id: str
    mission_id: str
    requirement_id: str
    machine_id: str = Field(min_length=1, max_length=160)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    accuracy_m: float = Field(ge=0, le=100000)
    captured_at: float = Field(gt=0)
    speed: float | None = Field(default=None, ge=0, le=500)


def _camera(value: str | None) -> str:
    url = (value or DEFAULT_CAMERA_URL).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(400, "Camera URL must be a valid http(s) URL")
    return url


def _caps(values: list[str] | None) -> list[str]:
    allowed = set(CAPABILITY_ALIASES.values())
    requested = values or list(allowed)
    out: list[str] = []
    for value in requested:
        normalized = value.strip()
        if normalized in allowed and normalized not in out:
            out.append(normalized)
    if not out:
        raise HTTPException(400, "No valid capabilities selected")
    return out


def _load_demo_tenders() -> list[dict[str, Any]]:
    try:
        rows = json.loads(DEMO_TENDER_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(500, f"Field tender catalog unavailable: {exc}") from exc
    if not isinstance(rows, list):
        raise HTTPException(500, "Field tender catalog must be a JSON list")
    return rows


def _backend_field_plan(tender_key: str) -> dict[str, Any] | None:
    try:
        request = Request(
            f"{BACKEND_URL}/api/investigations/tenders/{quote(tender_key, safe='')}/field-verification",
            headers={"Accept": "application/json", "User-Agent": "SENTRY-FIELD/0.7"},
            method="GET",
        )
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        tender = payload.get("tender") or {}
        requirements = payload.get("requirements") or []
        if not tender.get("id") or not requirements:
            return None
        return {
            "id": str(tender["id"]),
            "tender_id": str(tender["id"]),
            "reference_number": tender.get("reference_number") or "",
            "title": tender.get("title") or "",
            "source_name": tender.get("procuring_entity") or "SENTRY procurement database",
            "source_url": tender.get("source_url") or "",
            "source_verified_on": payload.get("source_profile_verified_on") or "",
            "contract_location": payload.get("demo_site") or "Site supplied by operator",
            "category": payload.get("category") or "Physical procurement asset verification",
            "machine": payload.get("machine") or "Normal Vision Rover",
            "demo_site": payload.get("demo_site") or "Site supplied by operator",
            "requirements": requirements,
            "verification_notes": payload.get("verification_notes") or "Camera inference provides visual observations; specialist checks may be required.",
            "auto_generated": bool(payload.get("auto_generated")),
        }
    except (OSError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _find_tender(tender_key: str) -> dict[str, Any]:
    found = next((item for item in _load_demo_tenders() if str(item.get("id")) == tender_key or str(item.get("tender_id")) == tender_key), None)
    if found:
        return found
    backend = _backend_field_plan(tender_key)
    if backend:
        return backend
    raise HTTPException(404, "Tender not found")


def _set(**updates: Any) -> None:
    with _lock:
        _state.update(updates)
        _state["updated_at"] = time.time()


def _snapshot() -> dict[str, Any]:
    with _lock:
        snapshot = dict(_state)
        snapshot["gps"] = dict(_state["gps"])
    snapshot.pop("stop_token", None)
    snapshot["recent_events"] = list(_events)
    return snapshot


def _frame_url(event: dict[str, Any]) -> str | None:
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
def health() -> dict[str, Any]:
    return {"ok": True, "service": "sentry-field", "camera_url": DEFAULT_CAMERA_URL}


@app.get("/capabilities")
def capabilities() -> dict[str, Any]:
    return {"capabilities": [{"label": label, "value": value} for label, value in CAPABILITY_ALIASES.items()]}


@app.get("/tenders")
def tenders() -> dict[str, Any]:
    return {"tenders": _load_demo_tenders(), "source": "registered FIELD profiles + backend-derived tender plans"}


@app.get("/tenders/{tender_key}")
def tender(tender_key: str) -> dict[str, Any]:
    return _find_tender(tender_key)


@app.get("/status")
def status() -> dict[str, Any]:
    return _snapshot()


@app.get("/events")
def events() -> dict[str, Any]:
    return {"events": list(_events)}


@app.post("/dispatch")
def dispatch(request: DispatchRequest) -> dict[str, Any]:
    tender_row = _find_tender(request.tender_id)
    requirements = tender_row.get("requirements") or []
    requirement = next((item for item in requirements if item.get("id") == request.requirement_id), None)
    if requirement is None:
        raise HTTPException(400, "Requirement does not belong to selected tender")
    selected = _caps(request.capabilities or [str(requirement.get("capability") or "")])
    allowed = {str(item.get("capability")) for item in requirements if item.get("capability")}
    if not set(selected).issubset(allowed):
        raise HTTPException(400, "One or more capabilities do not belong to selected tender")
    if str(requirement.get("capability")) not in selected:
        raise HTTPException(400, "Primary capability must be included in the mission capability set")
    if request.machine != (tender_row.get("machine") or "Normal Vision Rover"):
        raise HTTPException(400, "Machine does not match the tender field profile")

    with _lock:
        _state["stop_token"] += 1
        _state.update({
            "running": False,
            "authorized": True,
            "mission_id": request.mission_id,
            "requirement_id": request.requirement_id,
            "tender_id": tender_row["id"],
            "capabilities": selected,
            "machine": request.machine,
            "demo_site": request.demo_site or tender_row.get("demo_site"),
            "dispatch_at": time.time(),
            "findings": 0,
            "evidence": 0,
            "last_detection": None,
            "last_identity": None,
            "last_error": None,
            "gps": {"status": "unavailable", "source": None, "lat": None, "lon": None, "accuracy_m": None, "captured_at": None, "received_at": None, "mission_id": request.mission_id, "requirement_id": request.requirement_id, "tender_id": tender_row["id"]},
            "machine_id": None,
            "updated_at": time.time(),
        })
    _events.clear()
    _events.appendleft({"type": "dispatch", "mission_id": request.mission_id, "requirement_id": request.requirement_id, "tender_id": tender_row["id"], "capability": requirement.get("capability"), "capabilities": selected, "machine": request.machine, "demo_site": request.demo_site or tender_row.get("demo_site"), "observed_at": time.time()})
    return {"ok": True, "authorized": True, "tender": tender_row, "requirement": requirement, "capabilities": selected}


@app.post("/telemetry")
def telemetry(request: TelemetryRequest) -> dict[str, Any]:
    gps = {"status": "live" if request.lat is not None and request.lon is not None else "unavailable", "source": request.machine_id, "lat": request.lat, "lon": request.lon, "accuracy_m": None, "captured_at": None, "received_at": time.time(), "mission_id": _state.get("mission_id"), "requirement_id": _state.get("requirement_id"), "tender_id": _state.get("tender_id")}
    _set(machine_id=request.machine_id, battery=request.battery, speed=request.speed, gps=gps)
    _events.appendleft({"type": "telemetry", "machine_id": request.machine_id, "battery": request.battery, "speed": request.speed, "gps": gps, "observed_at": time.time(), "mission_id": _state.get("mission_id"), "requirement_id": _state.get("requirement_id"), "tender_id": _state.get("tender_id")})
    return {"ok": True, "gps": gps}


@app.post("/telemetry/mobile")
def mobile_telemetry(request: MobileGpsRequest) -> dict[str, Any]:
    captured_at = request.captured_at / 1000 if request.captured_at > 10_000_000_000 else request.captured_at
    now = time.time()
    if captured_at > now + 300 or captured_at < now - 86400:
        raise HTTPException(400, "Mobile GPS timestamp outside accepted range")
    with _lock:
        if not _state["authorized"]:
            raise HTTPException(403, "Rover mission is not authorised")
        for key, label in (("tender_id", "tender"), ("mission_id", "mission"), ("requirement_id", "requirement")):
            if getattr(request, key) != _state.get(key):
                raise HTTPException(409, f"GPS {label} does not match the authorised mission")
        gps = {"status": "live", "source": "browser-geolocation", "lat": request.lat, "lon": request.lon, "accuracy_m": request.accuracy_m, "captured_at": captured_at, "received_at": now, "mission_id": request.mission_id, "requirement_id": request.requirement_id, "tender_id": request.tender_id}
        _state["machine_id"] = request.machine_id
        _state["speed"] = request.speed
        _state["gps"] = gps
        _state["updated_at"] = now
    _events.appendleft({"type": "mobile_gps", "machine_id": request.machine_id, "gps": gps, "speed": request.speed, "observed_at": now, "mission_id": request.mission_id, "requirement_id": request.requirement_id, "tender_id": request.tender_id})
    return {"ok": True, "gps": gps}


@app.post("/stop")
def stop() -> dict[str, bool]:
    with _lock:
        _state["stop_token"] += 1
        _state["running"] = False
        _state["authorized"] = False
        _state["gps"] = {"status": "unavailable", "source": None, "lat": None, "lon": None, "accuracy_m": None, "captured_at": None, "received_at": None, "mission_id": _state.get("mission_id"), "requirement_id": _state.get("requirement_id"), "tender_id": _state.get("tender_id")}
        _state["machine_id"] = None
        _state["updated_at"] = time.time()
    _events.appendleft({"type": "stop", "observed_at": time.time(), "mission_id": _state.get("mission_id")})
    return {"ok": True, "stopped": True}


def _stream(camera_url: str, confidence: float, every_n_frames: int, mission_id: str | None, requirement_id: str | None, capabilities: list[str]) -> Generator[bytes, None, None]:
    import cv2
    from .vision.scanner import FieldScanner

    cap = cv2.VideoCapture(camera_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        _set(running=False, last_error=f"Could not open camera: {camera_url}")
        raise RuntimeError(f"Could not open video source: {camera_url}")

    scanner: FieldScanner | None = None
    scanner_error: str | None = None
    try:
        config = build_config(source=camera_url, confidence=confidence, every_n_frames=every_n_frames, mission_id=mission_id, requirement_id=requirement_id, capabilities=capabilities)
        try:
            scanner = FieldScanner(config)
        except Exception as exc:
            scanner_error = f"Vision models unavailable: {exc}"
            _set(last_error=scanner_error)

        _events.clear()
        with _lock:
            _state["stop_token"] += 1
            token = _state["stop_token"]
        _set(running=True, authorized=True, camera_url=camera_url, last_error=scanner_error, mission_id=mission_id, requirement_id=requirement_id, capabilities=capabilities, confidence=config.confidence, every_n_frames=config.every_n_frames)

        idx = 0
        prev = time.monotonic()
        fps = 0.0
        while True:
            with _lock:
                if _state["stop_token"] != token or not _state["authorized"]:
                    break
            started = time.monotonic()
            ok, frame = cap.read()
            if not ok:
                _set(running=False, last_error="Camera frame read failed")
                break
            idx += 1
            detections: list[Any] = []
            qr = barcode = ocr = None
            persisted: list[dict[str, Any]] = []
            if scanner is not None:
                try:
                    current_gps = dict(_state.get("gps") or {})
                    detections, _context, qr, barcode, ocr, persisted = scanner.scan(frame, idx, gps=current_gps)
                except Exception as exc:
                    scanner_error = f"Vision inference failed: {exc}"
                    _set(last_error=scanner_error)
            display = frame.copy()
            for detection in detections:
                x1, y1, x2, y2 = detection.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(display, f"{detection.label} {detection.confidence:.2f}", (x1, max(22, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 0), 2)
                _events.appendleft({"type": "detection", "capability": detection.label.lower().replace(" ", "_"), "observation": f"{detection.label} observed in field camera frame", "confidence": round(float(detection.confidence), 3), "bbox": detection.bbox, "detector": detection.detector, "track_id": detection.track_id, "observed_at": time.time(), "mission_id": mission_id, "requirement_id": requirement_id, "tender_id": _state.get("tender_id"), "machine_id": _state.get("machine_id"), "gps": dict(_state.get("gps") or {})})
            for item in persisted:
                event = dict(item)
                event["type"] = "evidence"
                event["frame_url"] = _frame_url(event)
                event["tender_id"] = _state.get("tender_id")
                event["machine_id"] = _state.get("machine_id")
                event["gps"] = dict(_state.get("gps") or {})
                _events.appendleft(event)
            ids = [value for value in (qr, barcode, ocr) if value]
            if ids:
                _events.appendleft({"type": "identity", "value": " | ".join(ids)[:200], "detector": "qr/barcode/ocr", "observed_at": time.time(), "mission_id": mission_id, "requirement_id": requirement_id, "tender_id": _state.get("tender_id"), "gps": dict(_state.get("gps") or {})})
            now_mono = time.monotonic()
            dt = now_mono - prev
            prev = now_mono
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1 / dt)
            ms = (time.monotonic() - started) * 1000
            with _lock:
                _state.update({"fps": round(fps, 1), "inference_ms": round(ms, 1), "findings": len(detections), "evidence": sum(1 for event in _events if event.get("type") == "evidence"), "last_detection": {"type": detections[0].label, "confidence": round(float(detections[0].confidence), 3), "track_id": detections[0].track_id} if detections else _state.get("last_detection"), "last_identity": " | ".join(ids)[:200] if ids else _state.get("last_identity"), "updated_at": time.time()})
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 900), 44), (15, 18, 25), -1)
            cv2.putText(display, f"SENTRY FIELD | FPS {fps:.1f} | {ms:.0f}ms | findings {len(detections)}", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
            if scanner_error:
                cv2.putText(display, "VISION DEGRADED - see mission status", (14, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 200, 255), 2)
            max_width = max(320, int(config.stream_max_width))
            if display.shape[1] > max_width:
                scale = max_width / float(display.shape[1])
                display = cv2.resize(display, (max_width, max(1, int(round(display.shape[0] * scale)))), interpolation=cv2.INTER_AREA)
            ok, encoded = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), int(config.jpeg_quality), int(cv2.IMWRITE_JPEG_OPTIMIZE), 1])
            if ok:
                yield b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"
    finally:
        cap.release()
        with _lock:
            if _state["stop_token"] == token:
                _state["running"] = False
        _set()


@app.get("/stream")
def stream(camera_url: str | None = Query(None), confidence: float = Query(DEFAULT_CONFIG.confidence, ge=.05, le=.99), every_n_frames: int = Query(DEFAULT_CONFIG.every_n_frames, ge=1, le=60), mission_id: str | None = Query(None), requirement_id: str | None = Query(None), capabilities: str | None = Query(None)) -> StreamingResponse:
    selected_caps = _caps([value for value in (capabilities or "").split(",") if value] or None)
    return StreamingResponse(_stream(_camera(camera_url), confidence, every_n_frames, mission_id, requirement_id, selected_caps), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Access-Control-Allow-Origin": "*"})
