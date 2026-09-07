"""Compatibility entrypoint for the historical low-latency gateway.

The hackathon/demo stack now uses the canonical `sentry_field.api:app` so that
there is one authoritative dispatch, telemetry, streaming and evidence API.
This module remains import-compatible for existing scripts.
"""
from __future__ import annotations

import os

from .api import app

FIELD_API_PORT = int(os.getenv("SENTRY_FIELD_API_PORT", "8001"))
