from __future__ import annotations

import json
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen

from . import api_v2 as _gateway
from .api_robust import FIELD_API_PORT, app
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


class _MjpegCapture:
    """Open a DroidCam/HTTP MJPEG stream without relying on OpenCV's URL backend."""

    def __init__(self, source: str) -> None:
        import cv2

        self.source = source
        self.response = None
        self.buffer = bytearray()
        self.closed = False
        try:
            request = UrlRequest(
                source,
                headers={
                    "Accept": "multipart/x-mixed-replace,image/jpeg,*/*",
                    "Cache-Control": "no-cache",
                    "User-Agent": "SENTRY-FIELD/0.8",
                },
                method="GET",
            )
            self.response = urlopen(request, timeout=10)
            content_type = str(self.response.headers.get("Content-Type") or "").lower()
            if "multipart" not in content_type and "image/jpeg" not in content_type:
                self.release()
                return
            self._cv2 = cv2
        except Exception:
            self.release()
            self._cv2 = cv2

    def isOpened(self) -> bool:  # noqa: N802
        return self.response is not None and not self.closed

    def set(self, *_args) -> bool:
        return True

    def _read_chunk(self) -> bool:
        if not self.response:
            return False
        try:
            chunk = self.response.read(65536)
        except Exception:
            return False
        if not chunk:
            return False
        self.buffer.extend(chunk)
        return True

    def read(self):
        if not self.isOpened():
            return False, None
        while not self.closed:
            start = self.buffer.find(b"\xff\xd8")
            if start < 0:
                if not self._read_chunk():
                    return False, None
                continue
            if start > 0:
                del self.buffer[:start]
            end = self.buffer.find(b"\xff\xd9", 2)
            if end < 0:
                if len(self.buffer) > 8_000_000:
                    del self.buffer[:-1_000_000]
                if not self._read_chunk():
                    return False, None
                continue
            frame_bytes = bytes(self.buffer[: end + 2])
            del self.buffer[: end + 2]
            import numpy as np

            frame = self._cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), self._cv2.IMREAD_COLOR)
            if frame is None:
                continue
            return True, frame
        return False, None

    def release(self) -> None:
        self.closed = True
        response = self.response
        self.response = None
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def _patched_gateway_stream(*args, **kwargs):
    import cv2

    original_capture = cv2.VideoCapture
    cv2.VideoCapture = _MjpegCapture
    try:
        yield from _gateway._stream(*args, **kwargs)
    finally:
        cv2.VideoCapture = original_capture


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
        camera_url = str(request.query_params.get("camera_url") or "").strip()
        if not _valid_http_camera_url(camera_url):
            return Response(content=json.dumps({"detail": "camera_url must be a valid http(s) URL"}), status_code=400, media_type="application/json")
        mission_id = request.query_params.get("mission_id")
        requirement_id = request.query_params.get("requirement_id")
        with _gateway._lock:
            authorized = bool(_state.get("authorized"))
            active_mission = _state.get("mission_id")
            active_requirement = _state.get("requirement_id")
        if not authorized or not mission_id or not requirement_id or mission_id != active_mission or requirement_id != active_requirement:
            return Response(content=json.dumps({"detail": "FIELD mission is not authorised for this stream"}), status_code=409, media_type="application/json")

        try:
            confidence = float(request.query_params.get("confidence") or _gateway.DEFAULT_CONFIG.confidence)
            every_n_frames = int(request.query_params.get("every_n_frames") or _gateway.DEFAULT_CONFIG.every_n_frames)
            capabilities = [value for value in str(request.query_params.get("capabilities") or "").split(",") if value]
            selected_caps = _caps(capabilities or None)
            stream = _patched_gateway_stream(
                _camera(camera_url),
                confidence,
                every_n_frames,
                mission_id,
                requirement_id,
                selected_caps,
            )
            return StreamingResponse(
                stream,
                media_type="multipart/x-mixed-replace; boundary=frame",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )
        except Exception as exc:
            return Response(content=json.dumps({"detail": f"FIELD stream setup failed: {exc}"}), status_code=500, media_type="application/json")

    return await call_next(request)


__all__ = ["FIELD_API_PORT", "app", "_state", "_events", "_load_demo_tenders", "_find_tender", "_set", "_snapshot", "_snap", "_frame_url", "_camera", "_caps"]
