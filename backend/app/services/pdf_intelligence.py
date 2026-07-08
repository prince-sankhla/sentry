"""PDF / tender-document intelligence — deterministic structured extraction.

Turns raw tender-document text into structured, provenanced fields (tender ref,
estimated value, EMD, bid submission/opening dates, category, bidder count, …)
using explainable regex patterns tuned for Indian procurement documents (GeM,
CPPP, NIC eProcurement, state portals).

Grounding contract: this module *only* extracts values that literally appear in
the text. Every :class:`ExtractedField` keeps the source span it was read from
and a confidence. It never infers or invents — if a field is absent, it is
simply not returned. The AI layer may cite these fields; it may not add to them.

PDF bytes are read with ``pypdf`` when installed; otherwise callers pass already
extracted text (e.g. from the connector's ``html_to_text``). No hard dependency.
"""

from __future__ import annotations

import re
from decimal import Decimal

from app.schemas.pdf_intelligence import ExtractedField, TenderDocumentExtraction

# --------------------------------------------------------------------------- money


_CRORE = Decimal("10000000")
_LAKH = Decimal("100000")


def parse_indian_amount(raw: str) -> Decimal | None:
    """Parse Indian-format currency text into a Decimal rupee value.

    Handles ``Rs. 50,00,000`` / ``₹5.5 Crore`` / ``INR 1.2 Cr`` / ``12 Lakh``.
    """
    text = raw.lower().replace(",", " ").strip()
    mult = Decimal(1)
    if re.search(r"\bcr(ore)?s?\b", text):
        mult = _CRORE
    elif re.search(r"\b(lakh|lac|lacs|lakhs)\b", text):
        mult = _LAKH
    m = re.search(r"(\d+(?:\.\d+)?)", text.replace(" ", ""))
    if not m:
        return None
    try:
        return (Decimal(m.group(1)) * mult).quantize(Decimal("1"))
    except Exception:
        return None


# --------------------------------------------------------------------------- patterns

# Each entry: (field_name, compiled pattern, confidence, post-processor)
_MONEY = r"(?:rs\.?|inr|₹)?\s*[\d,]+(?:\.\d+)?\s*(?:cr(?:ore)?s?|lakhs?|lacs?)?"
_DATE = r"\d{1,2}[-/\s][A-Za-z0-9]{2,9}[-/\s]\d{2,4}(?:\s+\d{1,2}:\d{2})?"


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", v).strip(" .:-\t")


def _field(name: str, value: str, span: str, confidence: float) -> ExtractedField:
    return ExtractedField(name=name, value=_clean(value), source_span=_clean(span)[:240], confidence=confidence)


def _search(text: str, label: str, value_pat: str) -> tuple[str, str] | None:
    """Find ``label ... value`` and return (value, full_span)."""
    pat = re.compile(rf"({label})\s*[:\-–]?\s*({value_pat})", re.IGNORECASE)
    m = pat.search(text)
    if not m:
        return None
    return m.group(2), m.group(0)


def extract_tender_fields(text: str) -> TenderDocumentExtraction:
    """Extract structured procurement fields from tender-document text."""
    if not text or not text.strip():
        return TenderDocumentExtraction(empty=True, coverage=0.0, char_count=0)

    result = TenderDocumentExtraction(char_count=len(text), empty=True)
    found: list[ExtractedField] = []

    def take(attr: str, label: str, value_pat: str, conf: float) -> None:
        hit = _search(text, label, value_pat)
        if hit is None:
            return
        value, span = hit
        field = _field(attr, value, span, conf)
        setattr(result, attr, field)
        found.append(field)

    # reference / tender number. The label greedily consumes the full
    # "Reference No" phrase so the value capture starts at the real id (avoids
    # matching a trailing fragment like "erence" from "Reference").
    take("tender_reference", r"(?:tender|bid|nit|contract)\s*(?:ref(?:erence)?\s*)?(?:no\.?|number|id)", r"[A-Za-z0-9][A-Za-z0-9/_\-]{3,40}", 0.9)
    # estimated / tender value
    take("estimated_value", r"(?:estimated\s*value|tender\s*value|contract\s*value|value\s*of\s*(?:tender|work))", _MONEY, 0.85)
    # estimated cost (distinct from tender value in Indian NIT documents)
    take("estimated_cost", r"(?:estimated\s*cost|approx(?:imate)?\s*cost|probable\s*amount\s*of\s*contract|pac)", _MONEY, 0.8)
    # EMD
    take("emd_amount", r"(?:emd|earnest\s*money(?:\s*deposit)?|bid\s*security)", _MONEY, 0.85)
    # tender fee
    take("tender_fee", r"(?:tender\s*(?:fee|document\s*cost)|document\s*fee|cost\s*of\s*(?:tender|document)|e-?tender\s*processing\s*fee)", _MONEY, 0.8)
    # dates
    take("bid_submission_end", r"(?:bid\s*submission\s*(?:end|closing|last)\s*date|last\s*date\s*(?:of|for)\s*submission|closing\s*date|submission\s*deadline)", _DATE, 0.85)
    take("bid_opening_date", r"(?:bid\s*opening\s*date|(?:technical\s*)?opening\s*date|date\s*of\s*opening)", _DATE, 0.85)
    take("publication_date", r"(?:published\s*date|date\s*of\s*publish(?:ing)?|publication\s*date|nit\s*date|tender\s*date)", _DATE, 0.8)
    # procuring entity / organisation / department / buyer
    take("procuring_entity", r"(?:organisation|organization|procuring\s*entity|tender\s*inviting\s*authority|inviting\s*authority)", r"[A-Za-z][A-Za-z0-9 ,.&()\-]{4,80}", 0.7)
    take("department", r"(?:department|directorate|ministry|division|wing)", r"[A-Za-z][A-Za-z0-9 ,.&()\-]{4,80}", 0.65)
    take("buyer", r"(?:buyer|purchaser|indenting\s*officer|consignee|on\s*behalf\s*of)", r"[A-Za-z][A-Za-z0-9 ,.&()\-]{4,80}", 0.65)
    # category / work type
    take("category", r"(?:category|work\s*type|item\s*category|nature\s*of\s*work|procurement\s*category|work\s*category)", r"[A-Za-z][A-Za-z0-9 ,.&()/\-]{3,60}", 0.7)
    # location / place of work
    take("location", r"(?:location|place\s*of\s*(?:work|supply|delivery)|delivery\s*location|site\s*location|work\s*location)", r"[A-Za-z][A-Za-z0-9 ,.&()/\-]{3,60}", 0.65)
    # BOQ references
    take("boq_reference", r"(?:boq|bill\s*of\s*quantit(?:y|ies))\s*(?:no|number|ref(?:erence)?)?", r"[A-Za-z0-9/_\-]{2,40}", 0.7)
    # eligibility
    take("eligibility", r"(?:eligibility(?:\s*criteria)?|qualification\s*(?:criteria|requirement)|minimum\s*eligibility|pre-?qualification)", r"[A-Za-z0-9][A-Za-z0-9 ,.&()/%\-]{6,160}", 0.6)
    # award information
    take("awarded_to", r"(?:awarded\s*to|award(?:ed)?\s*in\s*favour\s*of|successful\s*bidder|l1\s*bidder|contractor\s*name)", r"[A-Za-z][A-Za-z0-9 ,.&()/\-]{3,80}", 0.7)
    take("award_value", r"(?:awarded\s*(?:value|amount|cost)|contract\s*awarded\s*for|accepted\s*(?:value|amount|bid))", _MONEY, 0.75)
    # bidders count
    take("bidders_count", r"(?:no\.?\s*of\s*bids?\s*received|number\s*of\s*bidders?|bids?\s*received|total\s*bidders?|participating\s*bidders?)", r"\d{1,4}", 0.8)
    # title (fallback: first strong "name of work" line)
    take("title", r"(?:name\s*of\s*(?:work|tender)|work\s*description|tender\s*title|subject)", r"[A-Za-z][A-Za-z0-9 ,.&()/\-]{6,120}", 0.65)

    result.fields = found
    attempted = 20
    result.coverage = round(len(found) / attempted, 2)
    result.empty = not found
    return result


def extract_from_pdf_bytes(data: bytes) -> TenderDocumentExtraction:
    """Extract structured fields from raw PDF bytes.

    Uses ``pypdf`` when available. If the dependency is missing or the bytes are
    not parseable, returns an empty extraction rather than raising — the platform
    degrades gracefully to text-only extraction.
    """
    try:
        import io

        from pypdf import PdfReader  # type: ignore
    except Exception:
        return TenderDocumentExtraction(empty=True, coverage=0.0, char_count=0)
    try:
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return TenderDocumentExtraction(empty=True, coverage=0.0, char_count=0)
    return extract_tender_fields(text)
