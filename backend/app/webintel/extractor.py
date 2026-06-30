from __future__ import annotations

import re

from app.webintel.schemas import ExtractedEvidence
from app.webintel.utils import unique_preserve_order

URL_RE = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
DATE_RE = re.compile(
    r"\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})\b",
    re.IGNORECASE,
)
ORG_SUFFIX_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.,' -]{2,}?\s+"
    r"(?:Limited|Ltd|Private Limited|Pvt Ltd|Inc|Corporation|Corp|LLC|LLP|PLC|Company|Co\.|Bank|Authority|Agency|Department|Ministry|Commission|Board|Council))\b"
)
GOV_RE = re.compile(
    r"\b((?:Government of|Ministry of|Department of|Office of|Public Works Department|Municipal Corporation|"
    r"National [A-Z][A-Za-z ]+ Authority|State [A-Z][A-Za-z ]+ Department)[A-Za-z0-9&.,' -]*)\b"
)


def extract_evidence(text: str) -> ExtractedEvidence:
    organizations = unique_preserve_order(ORG_SUFFIX_RE.findall(text))
    governments = unique_preserve_order(GOV_RE.findall(text))
    return ExtractedEvidence(
        company_mentions=[value for value in organizations if value not in governments],
        organization_names=organizations,
        government_entities=governments,
        urls=unique_preserve_order(URL_RE.findall(text)),
        emails=unique_preserve_order(EMAIL_RE.findall(text)),
        phone_numbers=unique_preserve_order(PHONE_RE.findall(text)),
        dates=unique_preserve_order(DATE_RE.findall(text)),
    )
