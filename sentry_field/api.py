from __future__ import annotations

import json
from urllib.parse import urlparse

from . import api_v2 as _gateway
from .api_robust import FIELD_API_PORT, app
from .fast_stream_camera import stream as _fast_stream
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

_state = _gateway._state
_events = _gateway._events
_load_demo_tenders = _gateway._load_demo_tenders
_find_tender = _gateway._find_tender
_set = _gateway._set
_snapshot = _gateway._snapshot
_snap = _snapshot
_frame_url = _gateway._frame_url
_camera = _gateway._camera
_caps = _gateway._caps


def _valid_http_camera_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


@app.middleware("http")
async def canonical_contract_validation(request: Request, call_next) -> Response:
    if request.method == "POST" and request.url.path == "/dispatch":
        body = await request.body()
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            tender_id = str(payload.get("tender_id") or "").strip()
            requirement_id = str(payload.get("requirement_id") or "").strip()
            capability = str(payload.get("capability") or "").strip()
            if tender_id and requirement_id and capability:
                try:
                    tender_rows = _load_demo_tenders()
                    tender = next((row for row in tender_rows if str(row.get("id")) == tender_id or str(row.get("tender_id")) == tender_id), None)
                except Exception:
                    tender = None
                if tender is not None:
                    requirement = next((item for item in tender.get("requirements") or [] if str(item.get("id")) == requirement_id), None)
                    if requirement is not None and str(requirement.get("capability") or "") != capability:
                        return Response(content=json.dumps({"detail": "Capability does not match the selected tender requirement"}), status_code=400, media_type="application/json")
        request._body = body

    if request.method == "GET" and request.url.path == "/stream":
        camera_url = str(request.query_params.get("camera_url") or "").strip()
        if not _valid_http_camera_url(camera_url):
            return Response(content=json.dumps({"detail": "camera_url must be a valid http(s) URL"}), status_code=400, media_type="application/json")
        mission_id = request.query_params.get("mission_id")
        requirement_id = request.query_params.get("requirement_id")
        if not mission_id or not requirement_id:
            return Response(content=json.dumps({"detail": "mission_id and requirement_id are required"}), status_code=400, media_type="application/json")

        # Browser stream owns the camera session. The exact mission tuple comes from dispatch;
        # avoid rejecting the stream because short-lived status polling raced with /dispatch.
        with _gateway._lock:
            _state["authorized"] = True
            _state["running"] = True
            _state["mission_id"] = mission_id
            _state["requirement_id"] = requirement_id
            _state["camera_url"] = camera_url

        try:
            confidence = float(request.query_params.get("confidence") or _gateway.DEFAULT_CONFIG.confidence)
            every_n_frames = int(request.query_params.get("every_n_frames") or _gateway.DEFAULT_CONFIG.every_n_frames)
            capabilities = [value.strip() for value in str(request.query_params.get("capabilities") or "").split(",") if value.strip()]
            selected_caps = _caps(capabilities or None)
            return StreamingResponse(
                _fast_stream(
                    _camera(camera_url), confidence, every_n_frames, mission_id, requirement_id, selected_caps
                ),
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "X-Accel-Buffering": "no", "Access-Control-Allow-Origin": "*"},
            )
        except Exception as exc:
            return Response(content=json.dumps({"detail": f"FIELD stream setup failed: {exc}"}), status_code=500, media_type="application/json")

    return await call_next(request)


__all__ = ["FIELD_API_PORT", "app", "_state", "_events", "_load_demo_tenders", "_find_tender", "_set", "_snapshot", "_snap", "_frame_url", "_camera", "_caps"]
