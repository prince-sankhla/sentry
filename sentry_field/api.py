from __future__ import annotations

import json
import os
import time
from collections import deque
from pathlib import Path
from threading import Lock
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

app = FastAPI(title="SENTRY FIELD Local Gateway", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/evidence-files", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence-files")

_lock = Lock()
_state = {
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
    "gps": {"status": "unavailable", "source": None, "lat": None, "lon": None},
    "stop_token": 0,
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
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.netloc:
        raise HTTPException(400, "Camera URL must be a valid http(s) URL")
    return url


def _caps(values: list[str] | None) -> list[str]:
    allowed = set(CAPABILITY_ALIASES.values())
    if not values:
        return list(allowed)
    out = []
    for v in values:
        v = v.strip()
        if v in allowed and v not in out:
            out.append(v)
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
    found = next(
        (x for x in _load_demo_tenders() if x.get("id") == tender_key or x.get("tender_id") == tender_key),
        None,
    )
    if not found:
        raise HTTPException(404, "Tender not found")
    return found


def _set(**updates):
    with _lock:
        _state.update(updates)
        _state["updated_at"] = time.time()


def _snap():
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
    return JSONResponse({"ok": True, "service": "sentry-field", "camera_url": DEFAULT_CAMERA_URL})


@app.get("/capabilities")
def capabilities():
    return JSONResponse({"capabilities": [{"label": k, "value": v} for k, v in CAPABILITY_ALIASES.items()]})


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
    requirement = next((r for r in tender_row.get("requirements", []) if r.get("id") == request.requirement_id), None)
    if requirement is None:
        raise HTTPException(400, "Requirement does not belong to selected tender")
    if requirement.get("capability") != request.capability:
        raise HTTPException(400, "Capability does not match selected requirement")
    if request.machine != tender_row.get("machine"):
        raise HTTPException(400, "Machine does not match the tender field profile")
    with _lock:
        _state["stop_token"] += 1
        _state.update(
            {
                "running": False,
                "authorized": True,
                "mission_id": request.mission_id,
                "requirement_id": request.requirement_id,
                "tender_id": tender_row["id"],
                "capabilities": [request.capability],
                "machine": request.machine,
                "demo_site": request.demo_site or tender_row.get("demo_site"),
                "dispatch_at": time.time(),
                "findings": 0,
                "evidence": 0,
                "last_detection": None,
                "last_identity": None,
                "last_error": None,
            }
        )
        _state["updated_at"] = time.time()
    _events.clear()
    _events.appendleft(
        {
            "type": "dispatch",
            "mission_id": request.mission_id,
            "requirement_id": request.requirement_id,
            "tender_id": tender_row["id"],
            "capability": request.capability,
            "machine": request.machine,
            "demo_site": request.demo_site or tender_row.get("demo_site"),
            "observed_at": time.time(),
        }
    )
    return JSONResponse({"ok": True, "authorized": True, "tender": tender_row, "requirement": requirement})


@app.post("/telemetry")
def telemetry(request: TelemetryRequest):
    gps = {"status": "unavailable", "source": request.machine_id, "lat": request.lat, "lon": request.lon}
    if request.lat is not None and request.lon is not None:
        gps["status"] = "live"
    _set(machine_id=request.machine_id, battery=request.battery, speed=request.speed, gps=gps)
    _events.appendleft(
        {
            "type": "telemetry",
            "machine_id": request.machine_id,
            "battery": request.battery,
            "speed": request.speed,
            "gps": gps,
            "observed_at": time.time(),
            "mission_id": _state.get("mission_id"),
            "requirement_id": _state.get("requirement_id"),
        }
    )
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


def _stream(
    camera_url: str,
    confidence: float,
    every_n_frames: int,
    mission_id: str | None,
    requirement_id: str | None,
    capabilities: list[str],
) -> Generator[bytes, None, None]:
    config = build_config(
        source=camera_url,
        confidence=confidence,
        every_n_frames=every_n_frames,
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
    )
    scanner = FieldScanner(config)
    cap = cv2.VideoCapture(camera_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cap.isOpened():
        _set(running=False, last_error=f"Could not open camera: {camera_url}")
        raise RuntimeError(f"Could not open video source: {camera_url}")

    _events.clear()
    with _lock:
        _state["stop_token"] += 1
        token = _state["stop_token"]
    _set(
        running=True,
        authorized=True,
        camera_url=camera_url,
        last_error=None,
        mission_id=mission_id,
        requirement_id=requirement_id,
        capabilities=capabilities,
        confidence=config.confidence,
        every_n_frames=config.every_n_frames,
    )

    idx = 0
    prev = time.monotonic()
    fps = 0.0
    try:
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
            detections, context, qr, barcode, ocr, persisted = scanner.scan(frame, idx)
            display = frame.copy()
            for d in detections:
                x1, y1, x2, y2 = d.bbox
                cv2.rectangle(display, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(
                    display,
                    f"{d.label} {d.confidence:.2f}",
                    (x1, max(22, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 0, 0),
                    2,
                )
                _events.appendleft(
                    {
                        "type": d.label,
                        "capability": d.label.lower().replace(" ", "_"),
                        "confidence": round(d.confidence, 3),
                        "bbox": d.bbox,
                        "detector": d.detector,
                        "track_id": d.track_id,
                        "observed_at": time.time(),
                        "mission_id": mission_id,
                        "requirement_id": requirement_id,
                    }
                )
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
                _events.appendleft(
                    {
                        "type": "identity",
                        "value": " | ".join(ids)[:200],
                        "detector": "qr/barcode/ocr",
                        "observed_at": time.time(),
                        "mission_id": mission_id,
                        "requirement_id": requirement_id,
                    }
                )
            now = time.monotonic()
            dt = now - prev
            prev = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1 / dt)
            ms = (time.monotonic() - started) * 1000
            with _lock:
                _state.update(
                    {
                        "fps": round(fps, 1),
                        "inference_ms": round(ms, 1),
                        "findings": len(detections),
                        "evidence": sum(1 for e in _events if e.get("type") == "evidence"),
                        "last_detection": {
                            "type": detections[0].label,
                            "confidence": round(detections[0].confidence, 3),
                            "track_id": detections[0].track_id,
                        }
                        if detections
                        else _state.get("last_detection"),
                        "last_identity": " | ".join(ids)[:200] if ids else _state.get("last_identity"),
                        "updated_at": time.time(),
                    }
                )
            cv2.rectangle(display, (0, 0), (min(display.shape[1], 900), 44), (15, 18, 25), -1)
            cv2.putText(
                display,
                f"SENTRY FIELD | FPS {fps:.1f} | {ms:.0f}ms | findings {len(detections)}",
                (14, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                (255, 255, 255),
                2,
            )
            if ids:
                cv2.putText(
                    display,
                    f"ID: {' | '.join(ids)[:110]}",
                    (14, 70),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (0, 255, 0),
                    2,
                )
            ok, enc = cv2.imencode(".jpg", display, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            if ok:
                yield (
                    b"--frame\r\nContent-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n\r\n" + enc.tobytes() + b"\r\n"
                )
    except Exception as exc:
        _set(running=False, last_error=str(exc))
        raise
    finally:
        cap.release()
        with _lock:
            if _state["stop_token"] == token:
                _state["running"] = False
        _set()


@app.get("/stream")
def stream(
    camera_url: str | None = Query(None),
    confidence: float = Query(DEFAULT_CONFIG.confidence, ge=.05, le=.99),
    every_n_frames: int = Query(DEFAULT_CONFIG.every_n_frames, ge=1, le=60),
    mission_id: str | None = Query(None),
    requirement_id: str | None = Query(None),
    capabilities: str | None = Query(None),
):
    with _lock:
        authorized = bool(_state["authorized"])
        active_mission = _state.get("mission_id")
        active_requirement = _state.get("requirement_id")
    if not authorized:
        raise HTTPException(409, "Inspection requires operator dispatch authorization")
    if mission_id != active_mission or requirement_id != active_requirement:
        raise HTTPException(409, "Mission/requirement do not match the authorized dispatch")
    selected = _caps(capabilities.split(",") if capabilities else None)
    return StreamingResponse(
        _stream(_camera(camera_url), confidence, every_n_frames, mission_id, requirement_id, selected),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
