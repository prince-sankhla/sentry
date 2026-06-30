from __future__ import annotations

from urllib.parse import urlparse


def compact_unique(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = (value or "").strip()
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def normalize_registration_number(value: str | None) -> str | None:
    if not value:
        return None
    normalized = "".join(character for character in value.upper() if character.isalnum())
    return normalized or None


def extract_domain(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip().lower()
    if not candidate:
        return None
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    domain = (parsed.netloc or parsed.path).split("/")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def source_key(source_type: str, source_id: str) -> str:
    return f"{source_type}:{source_id}"
