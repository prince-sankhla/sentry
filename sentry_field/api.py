from __future__ import annotations

import json
import time
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request as UrlRequest, build_opener

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
    """Persistent DroidCam/HTTP MJPEG reader with reconnect-safe socket handling."""

    def __init__(self, source: str) -> None:
        import cv2

        self.source = source
        self.response = None
        self.buffer = bytearray()
        self.closed = False
        self._cv2 = cv2
        self._opener = build_opener(ProxyHandler({}))
        self._consecutive_failures = 0
        self._open()

    def _open(self) -> bool:
        if self.closed:
            return False
        try:
            self._close_response()
            request = UrlRequest(
                self.source,
                headers={
                    "Accept": "multipart/x-mixed-replace,image/jpeg,*/*",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "User-Agent": "SENTRY-FIELD/0.9",
                },
                method="GET",
            )
            # DroidCam is an intentionally long-lived MJPEG response. The
            # request itself needs a connect timeout, but the response socket
            # must not inherit a 10s read timeout or the camera feed gets
            # torn down while the phone is still serving frames.
            self.response = self._opener.open(request, timeout=8)
            content_type = str(self.response.headers.get("Content-Type") or "").lower()
            if "multipart" not in content_type and "image/jpeg" not in content_type:
                self._close_response()
                return False
            self._disable_read_timeout()
            self._consecutive_failures = 0
            return True
        except Exception as exc:
            self._close_response()
            _set(last_error=f"Camera connection failed: {exc}")
            return False

    def _disable_read_timeout(self) -> None:
        """Remove urllib's connect timeout from the long-lived MJPEG socket."""
        response = self.response
        try:
            sock = response.fp.raw._sock  # type: ignore[attr-defined]
            sock.settimeout(None)
        except Exception:
            pass

    def isOpened(self) -> bool:  # noqa: N802
        return self.response is not None and not self.closed

    def set(self, *_args) -> bool:
        return True

    def _read_chunk(self) -> bool:
        if not self.response:
            return False
        try:
            chunk = self.response.read(16384)
        except Exception as exc:
            _set(last_error=f"Camera read interrupted: {exc}")
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
                if self._read_chunk():
                    continue
                if self._reconnect():
                    continue
                return False, None

            if start > 0:
                del self.buffer[:start]

            end = self.buffer.find(b"\xff\xd9", 2)
            if end < 0:
                if len(self.buffer) > 8_000_000:
                    del self.buffer[:-1_000_000]
                if self._read_chunk():
                    continue
                if self._reconnect():
                    continue
                return False, None

            frame_bytes = bytes(self.buffer[: end + 2])
            del self.buffer[: end + 2]
            frame = self._cv2.imdecode(
                __import__("numpy").frombuffer(frame_bytes, dtype=__import__("numpy").uint8),
                self._cv2.IMREAD_COLOR,
            )
            if frame is None:
                continue
            self._consecutive_failures = 0
            return True, frame

        return False, None

    def _reconnect(self) -> bool:
        self._consecutive_failures += 1
        if self.closed or self._consecutive_failures > 6:
            return False
        self.buffer.clear()
        time.sleep(min(0.25 * self._consecutive_failures, 1.0))
        return self._open()

    def _close_response(self) -> None:
        response = self.response
        self.response = None
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    def release(self) -> None:
        self.closed = True
        self._close_response()


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
