"""Shared parsing helpers reused by every connector mapper."""

from __future__ import annotations

import html
import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

_DATE_FORMATS = (
    "%d-%b-%Y %I:%M %p",
    "%d-%b-%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y-%m-%dT%H:%M:%SZ",
    "%m/%d/%Y",
)


def optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def required_string(payload: dict[str, Any], key: str) -> str:
    value = optional_string(payload.get(key))
    if value is None:
        raise ValueError(f"Missing required string field: {key}")
    return value


def first_present(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = optional_string(payload.get(key))
        if value is not None:
            return value
    return None


def truncate(value: str | None, length: int) -> str | None:
    if value is None:
        return None
    return value.strip()[:length]


def parse_date(value: Any) -> date | None:
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    if not isinstance(value, str) or not value.strip():
        return None
    stripped = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(stripped[:24], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(stripped.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        parsed_date = parse_date(value)
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=UTC) if parsed_date else None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    normalized = re.sub(r"[^0-9.]", "", str(value))
    if not normalized or normalized == ".":
        return None
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def first_decimal(values: Iterable[Any]) -> Decimal | None:
    for value in values:
        parsed = parse_decimal(value)
        if parsed is not None:
            return parsed
    return None


def currency(value: Any, default: str = "INR") -> str:
    text = optional_string(value)
    return text[:3].upper() if text else default


def html_to_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"(?i)<\s*(br|/div|/p|/tr|/h\d|/li)\s*/?>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in html.unescape(value).splitlines()]
    text = "\n".join(line for line in lines if line)
    return text or None


def is_url(value: Any) -> bool:
    return isinstance(value, str) and bool(re.match(r"https?://", value.strip(), re.IGNORECASE))


def now_utc() -> datetime:
    return datetime.now(UTC)
