"""Investigation intent detection — Entity Resolution V2, Phase 1.

Before planning, determine what the user is actually investigating and separate
the *entity* from any *modifier*. "Archaeological Survey of India directors" is a
Director investigation of the authority "Archaeological Survey of India" — not a
company named "…directors", and certainly not a topical search that should drag
in NHAI, RailTel or World Bank projects.

The detector returns:
    * ``investigation_type`` — mapped onto the existing planner types so the
      pipeline is unchanged (authority/PSU/ministry → buyer; individual → director;
      identifiers → tender/company).
    * ``intent`` — the finer-grained analyst intent (authority, psu, director,
      registration, gst, cin, tender_id, …) for explainability.
    * ``entity_query`` — the clean entity string with modifiers stripped, which is
      what resolution and retrieval must use (never the raw text).

Deterministic and explainable — pure string logic, no model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.investigation_planner import InvestigationType

# Modifier words that describe an ASPECT of an entity, not the entity itself.
# Stripped from the entity query so resolution matches the entity, not the aspect.
_DIRECTOR_MODIFIERS = ("directors", "director", "owners", "owner", "beneficial owner",
                       "board", "officers", "officer", "promoters", "promoter", "management")
_SUPPLIER_MODIFIERS = ("suppliers", "supplier", "vendors", "vendor", "contractors", "contractor", "bidders", "bidder")
_TENDER_MODIFIERS = ("tenders", "tender", "rfp", "rfps", "bids", "bid", "notices", "notice")
_AWARD_MODIFIERS = ("awards", "award", "contracts", "contract", "work orders", "purchase orders")

# Authority / PSU / ministry cue words → a buyer-side investigation.
_AUTHORITY_CUES = ("authority", "survey", "commission", "corporation", "board", "council",
                   "directorate", "department", "ministry", "municipal", "municipality",
                   "nigam", "pradhikaran", "vibhag", "mission", "institute", "university",
                   "development authority")
_PSU_CUES = ("limited", "ltd", "psu", "public sector")
_MINISTRY_CUES = ("ministry", "department of", "directorate", "vibhag")

# Identifier patterns (Indian).
_CIN_RE = re.compile(r"\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b", re.IGNORECASE)
_GST_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z\d]Z[A-Z\d]\b", re.IGNORECASE)
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
_TENDER_ID_RE = re.compile(r"\b[A-Z]{2,8}[:/][A-Z0-9][A-Z0-9./_-]{3,}\b", re.IGNORECASE)
_REG_RE = re.compile(r"\b[A-Z]{2,}\d[A-Z0-9]{4,}\b", re.IGNORECASE)


@dataclass(frozen=True)
class InvestigationIntent:
    entity_query: str          # cleaned entity string used for resolution/retrieval
    investigation_type: InvestigationType
    intent: str                # fine-grained: authority/psu/director/registration/gst/cin/tender_id/company/...
    identifier: str | None     # the raw identifier when the query IS one
    matched_field: str | None  # which field the identifier targets (cin/gst/pan/tender_id/reference)
    confidence: float
    reason: str


def _strip_trailing(query: str, modifiers: tuple[str, ...]) -> tuple[str, bool]:
    """Remove a trailing modifier phrase (e.g. '... directors') if present."""
    q = query.strip()
    low = q.casefold()
    for m in sorted(modifiers, key=len, reverse=True):
        if low.endswith(" " + m) or low == m:
            cut = q[: len(q) - len(m)].strip(" -–—:,")
            return (cut or q), True
    return q, False


def detect_intent(query: str) -> InvestigationIntent:
    """Classify the query's investigation intent and extract the clean entity."""
    q = re.sub(r"\s+", " ", (query or "")).strip()
    if not q:
        return InvestigationIntent("", "company", "unknown", None, None, 0.3, "empty query")

    # 1. Exact identifiers win outright — highest-precision investigations.
    if _CIN_RE.search(q):
        return InvestigationIntent(q, "company", "cin", q, "cin", 0.98, "query is a CIN")
    if _GST_RE.search(q):
        return InvestigationIntent(q, "company", "gst", q, "gst", 0.98, "query is a GSTIN")
    if _TENDER_ID_RE.search(q):
        return InvestigationIntent(q, "tender", "tender_id", q, "reference_number", 0.95, "query is a tender/reference id")
    if _PAN_RE.fullmatch(q):
        return InvestigationIntent(q, "company", "pan", q, "pan", 0.95, "query is a PAN")
    if _REG_RE.fullmatch(q):
        return InvestigationIntent(q, "company", "registration", q, "registration_number", 0.9, "query is a registration number")

    # 2. Aspect modifiers — separate the entity from what is being asked about it.
    entity, is_director = _strip_trailing(q, _DIRECTOR_MODIFIERS)
    if is_director:
        return InvestigationIntent(entity, "director", "director", None, None, 0.85,
                                   f"director investigation of “{entity}”")
    entity, is_supplier = _strip_trailing(q, _SUPPLIER_MODIFIERS)
    if is_supplier:
        # "suppliers to X" / "X suppliers" — X is the buyer; suppliers are the aspect.
        return InvestigationIntent(entity, "buyer", "supplier_of_buyer", None, None, 0.75,
                                   f"suppliers-to-buyer investigation of “{entity}”")
    entity, is_tender = _strip_trailing(q, _TENDER_MODIFIERS)
    if is_tender:
        return InvestigationIntent(entity, "buyer", "tenders_of_buyer", None, None, 0.7,
                                   f"tenders-of-buyer investigation of “{entity}”")
    entity, is_award = _strip_trailing(q, _AWARD_MODIFIERS)
    if is_award:
        return InvestigationIntent(entity, "buyer", "awards_of_buyer", None, None, 0.7,
                                   f"awards-of-buyer investigation of “{entity}”")

    low = q.casefold()

    # 3. Authority / PSU / ministry cues → buyer-side entity (never a supplier).
    if any(cue in low for cue in _MINISTRY_CUES):
        return InvestigationIntent(q, "ministry", "ministry", None, None, 0.8, "ministry/department cue")
    if any(cue in low for cue in _AUTHORITY_CUES):
        return InvestigationIntent(q, "buyer", "authority", None, None, 0.72,
                                   "authority/government-body cue → buyer investigation")
    if any(re.search(rf"\b{re.escape(cue)}\b", low) for cue in _PSU_CUES):
        return InvestigationIntent(q, "company", "psu", None, None, 0.65, "corporate/PSU cue → company")

    # 4. No strong cue: an entity name, resolved downstream. Kept as company but
    #    the resolver may re-type it as a government_buyer from the real data.
    return InvestigationIntent(q, "company", "entity", None, None, 0.5,
                               "named entity — resolved against the indexed database")
