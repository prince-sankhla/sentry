from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import urlparse


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower() or "https"
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    return parsed._replace(scheme=scheme, netloc=host, path=path, fragment="").geturl()


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


def content_sha256(content: str) -> str:
    normalized = re.sub(r"\s+", " ", content).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        cleaned = clean_whitespace(value)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output
