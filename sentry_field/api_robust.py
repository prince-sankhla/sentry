from __future__ import annotations

from typing import Any, Generator

from . import api_v2 as gateway

app = gateway.app
FIELD_API_PORT = gateway.FIELD_API_PORT


def _diagnostic_frame(message: str) -> bytes:
    import cv2
    import numpy as np

    frame = np.zeros((360, 960, 3), dtype=np.uint8)
    cv2.putText(frame, "SENTRY FIELD", (28, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    cv2.putText(frame, "Camera stream unavailable", (28, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 220, 255), 2)
    cv2.putText(frame, message[:110], (28, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    cv2.putText(frame, "Check the DroidCam /video URL and FIELD terminal.", (28, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return b""
    return b"--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n" + encoded.tobytes() + b"\r\n"


def _safe_stream(*args: Any, **kwargs: Any) -> Generator[bytes, None, None]:
    try:
        yield from gateway.__dict__["_original_stream"](*args, **kwargs)
    except Exception as exc:
        message = str(exc) or "Unknown camera/vision stream error"
        gateway._set(running=False, last_error=message)
        try:
            frame = _diagnostic_frame(message)
        except Exception:
            frame = b""
        if frame:
            yield frame


if "_original_stream" not in gateway.__dict__:
    gateway.__dict__["_original_stream"] = gateway.__dict__["_stream"]
gateway.__dict__["_stream"] = _safe_stream

__all__ = ["app", "FIELD_API_PORT"]
