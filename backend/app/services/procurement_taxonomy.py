"""Deterministic procurement taxonomy classifiers.

Pure, dependency-light functions that bucket a procurement record along the
dimensions the coverage and statistics engines report on: Indian state,
ministry/department, spend category, procurement method and year. Every
classifier is deterministic keyword/pattern matching — no AI, no network — so
the same input always yields the same bucket.

These are intentionally *reporting* classifiers (coverage/statistics), not
identity or risk signals; an "Unattributed"/"Unspecified"/"Other" bucket is
always returned rather than guessing.
"""

from __future__ import annotations

import re
from datetime import date

UNATTRIBUTED = "Unattributed"
UNSPECIFIED = "Unspecified"
OTHER = "Other"

INDIAN_STATES: tuple[str, ...] = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands",
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
)

# Common abbreviations / alternates mapped to the canonical state.
_STATE_ALIASES: dict[str, str] = {
    "ap": "Andhra Pradesh", "up": "Uttar Pradesh", "mp": "Madhya Pradesh",
    "wb": "West Bengal", "tn": "Tamil Nadu", "j&k": "Jammu and Kashmir",
    "ncr": "Delhi", "new delhi": "Delhi", "bengal": "West Bengal",
    "orissa": "Odisha", "pondicherry": "Puducherry", "bombay": "Maharashtra",
}

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Construction & Roads", ("road", "bridge", "construction", "building", "civil", "infrastructure", "highway")),
    ("Electrical & Power", ("electric", "power", "transformer", "solar", "energy", "lighting", "cable", "grid")),
    ("Medical & Health", ("medical", "hospital", "medicine", "drug", "health", "surgical", "pharma", "vaccine")),
    ("IT & Software", ("software", "computer", "server", "network", "laptop", "hardware", "it ", "digital")),
    ("Water & Sanitation", ("water", "sewer", "sanitation", "pipe", "drainage", "pump", "irrigation")),
    ("Supply & Goods", ("supply", "procurement of", "purchase", "goods", "material", "equipment", "furniture")),
    ("Consultancy & Services", ("consultancy", "consultant", "service", "maintenance", "repair", "audit")),
    ("Transport & Vehicles", ("vehicle", "bus", "truck", "transport", "railway", "rolling stock")),
    ("Agriculture & Food", ("agriculture", "seed", "fertiliser", "fertilizer", "crop", "food", "grain")),
    ("Education", ("school", "education", "university", "college", "teaching", "training")),
)

# Procurement-method classifiers (deterministic keyword match on title/description).
_METHOD_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Open Tender", ("open tender", "open competitive", "advertised tender", "e-tender", "national competitive", "international competitive", "icb", "ncb")),
    ("Limited Tender", ("limited tender", "limited enquiry", "restricted tender", "prequalified")),
    ("Single / Direct", ("single tender", "direct award", "direct contract", "nomination basis", "proprietary", "sole source")),
    ("Request for Proposal", ("request for proposal", "rfp", "expression of interest", "eoi", "request for quotation", "rfq")),
    ("E-Auction", ("e-auction", "reverse auction", "auction")),
    ("Framework / Rate Contract", ("rate contract", "framework agreement", "empanelment")),
)

_MINISTRY_RE = re.compile(r"(ministry of [a-z&,\-\s]+?)(?:,|;|\(|$)", re.IGNORECASE)
_DEPARTMENT_RE = re.compile(r"(department of [a-z&,\-\s]+?)(?:,|;|\(|$)", re.IGNORECASE)


def state_of(buyer: str | None, title: str | None = None) -> str:
    """Best-effort Indian state attribution from buyer/title text."""
    haystack = f"{buyer or ''} {title or ''}"
    folded = haystack.casefold()
    for state in INDIAN_STATES:
        if state.casefold() in folded:
            return state
    for alias, state in _STATE_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", folded):
            return state
    return UNATTRIBUTED


def ministry_of(buyer: str | None) -> str:
    """Extract a canonical ministry/department bucket from a buyer name."""
    if not buyer:
        return UNATTRIBUTED
    match = _MINISTRY_RE.search(buyer)
    if match:
        return _titlecase(match.group(1))
    match = _DEPARTMENT_RE.search(buyer)
    if match:
        return _titlecase(match.group(1))
    return UNATTRIBUTED


_AUTHORITY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("PSU / Enterprise", ("limited", "psu", "enterprise", "nigam", "corporation ltd", "ongc", "ntpc", "bhel", "sail")),
    ("Municipal / Urban", ("municipal", "corporation", "nagar", "panchayat", "urban", "development authority")),
    ("Board", ("board",)),
    ("Ministry", ("ministry",)),
    ("Department", ("department", "directorate", "dept")),
    ("University / Institute", ("university", "institute", "college", "iit", "iim", "aiims")),
    ("Authority", ("authority", "commission", "council")),
)


def authority_of(buyer: str | None) -> str:
    text = (buyer or "").casefold()
    if not text:
        return UNATTRIBUTED
    for label, keywords in _AUTHORITY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return label
    return OTHER


def department_of(buyer: str | None) -> str:
    if not buyer:
        return UNATTRIBUTED
    match = _DEPARTMENT_RE.search(buyer)
    if match:
        return _titlecase(match.group(1))
    return UNATTRIBUTED


def category_of(title: str | None, description: str | None = None) -> str:
    text = f"{title or ''} {description or ''}".casefold()
    for label, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return label
    return OTHER


def procurement_method_of(title: str | None, description: str | None = None) -> str:
    text = f"{title or ''} {description or ''}".casefold()
    for label, keywords in _METHOD_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return label
    return UNSPECIFIED


def year_of(value: date | None) -> str:
    return str(value.year) if value is not None else UNSPECIFIED


def _titlecase(value: str) -> str:
    return " ".join(word.capitalize() for word in value.strip().split())
