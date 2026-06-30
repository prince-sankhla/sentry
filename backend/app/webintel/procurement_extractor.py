from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.webintel.extractor import extract_evidence
from app.webintel.utils import clean_whitespace, unique_preserve_order


COMPANY_ALIASES = {
    "tcs": "Tata Consultancy Services",
    "tata consultancy services ltd": "Tata Consultancy Services",
    "tata consultancy services limited": "Tata Consultancy Services",
    "infosys ltd": "Infosys",
    "infosys limited": "Infosys",
    "reliance jio infocomm ltd": "Reliance Jio",
    "reliance jio infocomm limited": "Reliance Jio",
    "l&t": "Larsen and Toubro",
    "l and t": "Larsen and Toubro",
    "larsen & toubro": "Larsen and Toubro",
    "larsen and toubro": "Larsen and Toubro",
    "larsen and toubro ltd": "Larsen and Toubro",
    "adani enterprises ltd": "Adani Enterprises",
    "adani enterprises limited": "Adani Enterprises",
}

COMPANY_SUFFIX_RE = re.compile(
    r"\b(?:private|pvt|limited|ltd|inc|corporation|corp|company|co|llc|llp|plc)\.?\b",
    re.IGNORECASE,
)
VALUE_RE = re.compile(
    r"(?:(?P<currency>INR|USD|EUR|GBP|Rs\.?|₹|\$)\s*)"
    r"(?P<amount>\d[\d,]*(?:\.\d+)?)\s*"
    r"(?P<scale>crore|cr|lakh|million|billion|mn|bn)?",
    re.IGNORECASE,
)
NUMBER_PATTERNS = {
    "tender_number": re.compile(
        r"\b(?:tender|rfp|bid|notice|nit)\s*(?:no\.?|number|ref(?:erence)?\.?)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_.-]{4,})",
        re.IGNORECASE,
    ),
    "contract_number": re.compile(
        r"\b(?:contract|agreement|work order|po)\s*(?:no\.?|number|ref(?:erence)?\.?)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/_.-]{4,})",
        re.IGNORECASE,
    ),
}
DATE_PATTERNS = {
    "publication_date": re.compile(
        r"\b(?:published|publication|issued|notice date|date of publication)\s*(?:on|date)?\s*[:#-]?\s*"
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})",
        re.IGNORECASE,
    ),
    "award_date": re.compile(
        r"\b(?:awarded|award date|contract awarded|date of award)\s*(?:on|date)?\s*[:#-]?\s*"
        r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|20\d{2}[-/]\d{1,2}[-/]\d{1,2}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+20\d{2})",
        re.IGNORECASE,
    ),
}
BUYER_PATTERNS = [
    re.compile(r"\b(?:buyer|procuring entity|client|department|ministry)\s*[:#-]\s*([^.\n]{4,160})", re.IGNORECASE),
    re.compile(
        r"\b((?:Government of|Ministry of|Department of|Office of|Public Works Department|Municipal Corporation|"
        r"[A-Z][A-Za-z& ]+ Authority|[A-Z][A-Za-z& ]+ Department|[A-Z][A-Za-z& ]+ Board)[A-Za-z0-9&.,' -]{0,120})\b"
    ),
]
TITLE_PATTERNS = {
    "tender_title": re.compile(r"\b(?:tender title|title of tender|tender for|rfp for|bid for)\s*[:#-]?\s*([^.\n]{8,220})", re.IGNORECASE),
    "contract_title": re.compile(r"\b(?:contract title|contract for|work order for|agreement for)\s*[:#-]?\s*([^.\n]{8,220})", re.IGNORECASE),
}
PERSON_RE = re.compile(r"\b(?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){0,2}\b")

SECTOR_KEYWORDS = [
    ("Information Technology", ("software", "cloud", "data center", "cyber", "digital", "application", "it services", "systems integration")),
    ("Telecommunications", ("telecom", "5g", "4g", "broadband", "spectrum", "fiber", "fibre", "network")),
    ("Construction", ("construction", "civil work", "building", "road", "bridge", "engineering procurement construction", "epc")),
    ("Energy", ("solar", "power", "electricity", "renewable", "transmission", "oil", "gas", "hydrogen")),
    ("Transport", ("rail", "metro", "airport", "port", "logistics", "transport")),
    ("Consulting", ("consulting", "advisory", "audit", "professional services")),
]


@dataclass
class ProcurementExtraction:
    company_name: str | None = None
    normalized_company_name: str | None = None
    government_buyer: str | None = None
    tender_title: str | None = None
    contract_title: str | None = None
    contract_value: Decimal | None = None
    currency: str | None = None
    tender_category: str | None = None
    procurement_sector: str | None = None
    country: str | None = None
    publication_date: date | None = None
    award_date: date | None = None
    contract_number: str | None = None
    tender_number: str | None = None
    organization: str | None = None
    people_mentioned: list[str] = field(default_factory=list)
    related_companies: list[str] = field(default_factory=list)
    raw_signals: dict[str, Any] = field(default_factory=dict)


def extract_procurement_intelligence(query: str, title: str | None, content: str) -> ProcurementExtraction:
    text = clean_whitespace(" ".join(part for part in [title or "", content] if part))
    evidence = extract_evidence(text)
    organizations = evidence.organization_names
    company_name = _select_company_name(query, organizations)
    normalized_company = normalize_company_name(company_name) if company_name else None
    sector = _detect_sector(text)
    value, currency = _extract_value(text)

    extraction = ProcurementExtraction(
        company_name=company_name,
        normalized_company_name=normalized_company,
        government_buyer=_first_match(text, BUYER_PATTERNS),
        tender_title=_extract_title(text, "tender_title"),
        contract_title=_extract_title(text, "contract_title"),
        contract_value=value,
        currency=currency,
        tender_category=sector,
        procurement_sector=sector,
        country=_detect_country(text),
        publication_date=_extract_date_field(text, "publication_date"),
        award_date=_extract_date_field(text, "award_date"),
        contract_number=_extract_number(text, "contract_number"),
        tender_number=_extract_number(text, "tender_number"),
        organization=organizations[0] if organizations else None,
        people_mentioned=unique_preserve_order(PERSON_RE.findall(text)),
        related_companies=[
            organization
            for organization in organizations
            if normalize_company_name(organization) != normalized_company
        ][:12],
        raw_signals={
            "organizations": organizations[:20],
            "government_entities": evidence.government_entities[:20],
            "dates": evidence.dates[:20],
            "urls": evidence.urls[:20],
        },
    )
    return extraction


def normalize_company_name(value: str) -> str:
    cleaned = clean_whitespace(value).strip(".,")
    key = cleaned.casefold().replace("&", "and")
    key = COMPANY_SUFFIX_RE.sub("", key)
    key = re.sub(r"[^a-z0-9]+", " ", key).strip()
    alias = COMPANY_ALIASES.get(key)
    if alias:
        return alias
    if len(key) <= 5 and key.upper() == key:
        return key.upper()
    return " ".join(part.capitalize() for part in key.split())


def _select_company_name(query: str, organizations: list[str]) -> str | None:
    normalized_query = normalize_company_name(query)
    if normalized_query:
        for organization in organizations:
            if normalize_company_name(organization) == normalized_query:
                return organization
        for organization in organizations:
            haystack = normalize_company_name(organization).casefold()
            needle = normalized_query.casefold()
            if needle in haystack:
                return normalized_query
            if haystack in needle:
                return organization
        return normalized_query
    return organizations[0] if organizations else None


def _first_match(text: str, patterns: list[re.Pattern[str]]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return clean_whitespace(match.group(1)).strip(" .,:;-")
    return None


def _extract_title(text: str, field: str) -> str | None:
    match = TITLE_PATTERNS[field].search(text)
    if match:
        return clean_whitespace(match.group(1)).strip(" .,:;-")

    keyword = "tender" if field == "tender_title" else "contract"
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        if keyword in sentence.casefold() and 20 <= len(sentence) <= 260:
            return clean_whitespace(sentence).strip(" .,:;-")
    return None


def _extract_value(text: str) -> tuple[Decimal | None, str | None]:
    match = VALUE_RE.search(text)
    if not match:
        return None, None

    currency = _normalize_currency(match.group("currency"))
    amount_text = match.group("amount").replace(",", "")
    try:
        value = Decimal(amount_text)
    except InvalidOperation:
        return None, currency

    scale = (match.group("scale") or "").casefold()
    if scale in {"crore", "cr"}:
        value *= Decimal("10000000")
    elif scale == "lakh":
        value *= Decimal("100000")
    elif scale in {"million", "mn"}:
        value *= Decimal("1000000")
    elif scale in {"billion", "bn"}:
        value *= Decimal("1000000000")
    return value.quantize(Decimal("0.01")), currency


def _normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.upper().replace(".", "")
    if normalized in {"RS", "₹"}:
        return "INR"
    if normalized == "$":
        return "USD"
    return normalized[:3]


def _detect_sector(text: str) -> str | None:
    normalized = text.casefold()
    for sector, keywords in SECTOR_KEYWORDS:
        if any(keyword in normalized for keyword in keywords):
            return sector
    if "tender" in normalized or "procurement" in normalized:
        return "General Procurement"
    return None


def _detect_country(text: str) -> str | None:
    countries = ("India", "Ukraine", "United States", "United Kingdom", "Canada", "Australia")
    normalized = text.casefold()
    for country in countries:
        if country.casefold() in normalized:
            return country
    return None


def _extract_number(text: str, field: str) -> str | None:
    match = NUMBER_PATTERNS[field].search(text)
    if not match:
        return None
    value = clean_whitespace(match.group(1)).strip(" .,:;-")
    if not any(character.isdigit() for character in value):
        return None
    return value


def _extract_date_field(text: str, field: str) -> date | None:
    match = DATE_PATTERNS[field].search(text)
    if not match:
        return None
    return _parse_date(match.group(1))


def _parse_date(value: str) -> date | None:
    from datetime import datetime

    formats = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%b %d %Y", "%b %d, %Y", "%B %d %Y", "%B %d, %Y")
    cleaned = clean_whitespace(value)
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None
