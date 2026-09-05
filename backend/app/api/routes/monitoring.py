from __future__ import annotations

import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.live_monitoring import poll_live_sources

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _authorize(authorization: str | None, x_monitor_token: str | None) -> None:
    expected = os.getenv("SENTRY_MONITOR_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Monitoring worker is not configured.")
    supplied = x_monitor_token or ""
    if authorization and authorization.startswith("Bearer "):
        supplied = authorization.removeprefix("Bearer ").strip()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid monitoring token.")


@router.post("/poll")
def poll_sources(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_monitor_token: str | None = Header(default=None),
) -> dict[str, object]:
    """Poll official Indian procurement feeds and idempotently ingest discovered records."""
    _authorize(authorization, x_monitor_token)
    return poll_live_sources(db)
