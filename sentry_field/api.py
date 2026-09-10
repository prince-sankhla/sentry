from __future__ import annotations

import json

from . import api_v2 as _gateway
from .api_robust import FIELD_API_PORT, app
from starlette.requests import Request
from starlette.responses import Response

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


@app.middleware("http")
async def canonical_contract_validation(request: Request, call_next) -> Response:
    """Validate public FIELD contracts before the camera/vision stream starts."""
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
        mission_id = request.query_params.get("mission_id")
        requirement_id = request.query_params.get("requirement_id")
        with _gateway._lock:
            authorized = bool(_state.get("authorized"))
            active_mission = _state.get("mission_id")
            active_requirement = _state.get("requirement_id")
        if not authorized or not mission_id or not requirement_id or mission_id != active_mission or requirement_id != active_requirement:
            return Response(content=json.dumps({"detail": "FIELD mission is not authorised for this stream"}), status_code=409, media_type="application/json")

    return await call_next(request)


__all__ = ["FIELD_API_PORT", "app", "_state", "_events", "_load_demo_tenders", "_find_tender", "_set", "_snapshot", "_snap", "_frame_url", "_camera", "_caps"]
