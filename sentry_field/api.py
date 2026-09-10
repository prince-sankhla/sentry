from . import api_v2 as _gateway
from .api_robust import FIELD_API_PORT, app

# Canonical gateway is api_v2 wrapped by api_robust. Keep the historical
# module-level state/helpers available because the existing contract tests and
# a few local tools import them from sentry_field.api.
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

__all__ = [
    "FIELD_API_PORT",
    "app",
    "_state",
    "_events",
    "_load_demo_tenders",
    "_find_tender",
    "_set",
    "_snapshot",
    "_snap",
    "_frame_url",
    "_camera",
    "_caps",
]
