"""Deterministic normalization for procurement entities.

This module is the single, dependency-free (stdlib only) source of truth for
turning messy source values — organisation names, registration numbers,
references, currencies, document titles — into two things:

* a **canonical display value** (light-touch: trimmed, whitespace-collapsed,
  legal-suffix casing tidied) that is safe to store, and
* a **match key** (aggressive: case-folded, punctuation-stripped, legal
  suffixes removed) that is used ONLY for de-duplication and coverage
  reporting — never stored in place of the display value.

No AI, no network, no fuzzy ML — every function is pure and deterministic so
the same input always yields the same output. Buyers, suppliers and generic
organisations all share the same org normaliser; tenders/awards reuse the
reference and currency helpers.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = [
    "normalize_org_name",
    "org_match_key",
    "normalize_registration",
    "normalize_reference",
    "normalize_currency",
    "normalize_document_title",
    "normalize_text",
    "is_normalized_org",
    "CURRENCY_SYMBOLS",
]

# Legal / corporate suffixes stripped when building an org *match key*. Ordered
# longest-first so multi-word forms are removed before their abbreviations.
_ORG_SUFFIXES: tuple[str, ...] = (
    "private limited",
    "public limited company",
    "limited liability partnership",
    "incorporated",
    "corporation",
    "company",
    "limited",
    "private",
    "pvt ltd",
    "pvt. ltd.",
    "pvt",
    "ltd",
    "llp",
    "llc",
    "plc",
    "inc",
    "corp",
    "co",
    "gmbh",
    "pte",
    "pte ltd",
    "sarl",
    "srl",
    "spa",
    "bv",
    "nv",
    "sa",
    "ag",
    "oyj",
    "as",
)

# Common noise tokens that carry no identity signal in a match key.
_ORG_NOISE: frozenset[str] = frozenset({"the", "and", "of", "for", "m/s", "ms"})

CURRENCY_SYMBOLS: dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "$": "USD",
    "us$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "₴": "UAH",
    "uah": "UAH",
}

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_ALNUM_RE = re.compile(r"[^A-Za-z0-9]")


def normalize_text(value: str | None) -> str | None:
    """Trim, unicode-normalise (NFKC) and collapse internal whitespace.

    The universal light-touch cleaner: safe for any free-text field. Returns
    ``None`` for empty/whitespace-only input so callers can treat it as missing.
    """
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).replace(" ", " ")
    text = _WS_RE.sub(" ", text).strip()
    return text or None


def normalize_org_name(value: str | None) -> str | None:
    """Canonical **display** form for a buyer / supplier / organisation.

    Light-touch only: strips a leading ``M/s``/``M/s.`` honorific, collapses
    whitespace and normalises punctuation spacing. Does NOT drop legal suffixes
    (that would change the stored identity) — use :func:`org_match_key` for
    de-duplication.
    """
    text = normalize_text(value)
    if text is None:
        return None
    # Drop a leading "M/s" / "M/s." supplier honorific.
    text = re.sub(r"^(?:m/s\.?|messrs\.?)\s+", "", text, flags=re.IGNORECASE)
    # Normalise spacing around ampersands and commas.
    text = re.sub(r"\s*&\s*", " & ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = _WS_RE.sub(" ", text).strip(" ,")
    return text or None


def org_match_key(value: str | None) -> str | None:
    """Aggressive comparison key for org de-duplication.

    Case-folds, strips punctuation, removes legal suffixes and noise tokens.
    Two org names that differ only by ``Pvt Ltd`` vs ``Private Limited`` vs
    punctuation collapse to the same key. Returns ``None`` if nothing of
    substance remains.
    """
    display = normalize_org_name(value)
    if display is None:
        return None
    text = _PUNCT_RE.sub(" ", display.casefold())
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        return None
    # Remove trailing legal suffixes repeatedly (e.g. "foo co pvt ltd").
    changed = True
    while changed:
        changed = False
        for suffix in _ORG_SUFFIXES:
            if text == suffix:
                continue
            if text.endswith(" " + suffix):
                text = text[: -(len(suffix) + 1)].strip()
                changed = True
    tokens = [tok for tok in text.split(" ") if tok and tok not in _ORG_NOISE]
    return " ".join(tokens) or None


def normalize_registration(value: str | None) -> str | None:
    """Canonical form for a registration id (GSTIN / PAN / CIN / vendor id).

    Upper-cases and removes every non-alphanumeric character so
    ``29ABCDE1234F1Z5`` and ``29-ABCDE1234F1Z5`` unify. Returns ``None`` when no
    alphanumerics survive.
    """
    if value is None:
        return None
    cleaned = _ALNUM_RE.sub("", str(value)).upper()
    return cleaned or None


def normalize_reference(value: str | None) -> str | None:
    """Canonical tender/award reference: trimmed, whitespace-collapsed, uppercased.

    References are opaque identifiers, so we keep every alphanumeric and
    separator but normalise case and spacing for stable equality.
    """
    text = normalize_text(value)
    if text is None:
        return None
    return _WS_RE.sub("", text).upper() or None


def normalize_currency(value: str | None, default: str = "INR") -> str:
    """Map a currency symbol/code to a 3-letter ISO-4217 code (best effort)."""
    if value is None:
        return default
    raw = str(value).strip().casefold()
    if raw in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[raw]
    # Strip trailing separators e.g. "USD." / "INR "
    stripped = raw.strip(" .")
    if stripped in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[stripped]
    letters = re.sub(r"[^a-z]", "", raw)
    if len(letters) == 3:
        return letters.upper()
    return default


def normalize_document_title(value: str | None, fallback: str = "Document") -> str:
    """Canonical document title: cleaned text, never empty."""
    text = normalize_org_name(value) if value else None
    text = normalize_text(text) if text else None
    return text or fallback


def is_normalized_org(value: str | None) -> bool:
    """True when ``value`` already equals its canonical display form.

    Used by normalization-coverage reporting to count how many stored names are
    already clean without mutating anything.
    """
    if value is None:
        return False
    return normalize_org_name(value) == value.strip()
