from __future__ import annotations

import re

from app.entity_resolution.utils import compact_unique

ABBREVIATIONS = {
    "tcs": "tata consultancy services",
    "larsen and toubro": "larsen toubro",
    "lt": "larsen toubro",
    "l and t": "larsen toubro",
    "l t": "larsen toubro",
    "l&t": "larsen toubro",
    "jio": "reliance jio",
}

TOKEN_ABBREVIATIONS = {
    "co": "company",
    "corp": "corporation",
    "intl": "international",
    "tech": "technology",
    "svc": "services",
}

SUFFIX_TOKENS = {
    "limited",
    "ltd",
    "private",
    "pvt",
    "company",
    "co",
    "corporation",
    "corp",
    "inc",
    "incorporated",
    "llp",
    "plc",
    "india",
}


def normalize_company_name(name: str | None) -> str:
    if not name:
        return ""
    normalized = name.casefold().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""
    normalized = ABBREVIATIONS.get(normalized, normalized)
    tokens = [TOKEN_ABBREVIATIONS.get(token, token) for token in normalized.split()]
    stripped = [token for token in tokens if token not in SUFFIX_TOKENS]
    if stripped:
        tokens = stripped
    return " ".join(tokens)


def company_tokens(name: str | None) -> set[str]:
    return set(normalize_company_name(name).split())


def canonical_aliases(*names: str | None) -> list[str]:
    return compact_unique([name for name in names if name])
