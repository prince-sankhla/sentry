"""Shared deterministic helpers for the procurement platform package."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def ratio(part: int | Decimal, whole: int | Decimal) -> float:
    whole = int(whole)
    return round(int(part) / whole, 4) if whole else 0.0


def pct(part: int | Decimal, whole: int | Decimal) -> float:
    return round(ratio(part, whole) * 100, 2)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
