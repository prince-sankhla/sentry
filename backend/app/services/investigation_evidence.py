"""Evidence Engine — the provenance backbone of the investigation reasoning layer.

Every AI conclusion in SENTRY must be independently verifiable. This module is
the *single* place that turns raw ``InvestigationPackage`` records into
:class:`ReasoningCitation` objects carrying full provenance:

    original source · original URL · attached document/PDF · retrieved time ·
    publication date · confidence · a ready-to-paste citation string

It also assembles the investigation-wide **evidence ledger** (every distinct
source referenced, de-duplicated) and a :class:`GroundingReport` proving how much
of the narrative is anchored to evidence.

Principle: the LLM explains, the backend proves. Nothing here invents facts — it
only formats provenance that already exists on the retrieved records.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.investigation_executor import (
    InvestigationDocumentResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
)
from app.schemas.investigation_reasoning import GroundingReport, ReasoningCitation

# Source authority weighting — official Indian procurement portals are primary
# evidence; international feeds and open-web pages carry less evidential weight.
# Keys are matched against the citation's source_name (lowercased, prefix match).
_SOURCE_AUTHORITY: dict[str, int] = {
    "gem": 40,
    "cppp": 40,
    "nic": 38,
    "state_eproc": 36,
    "eproc": 36,
    "cag": 38,
    "datagovin": 34,
    "data.gov.in": 34,
    "adb": 26,
    "un_procurement": 24,
    "world_bank": 24,
    "prozorro": 20,
    "web": 14,
}


def _authority(source_name: str) -> int:
    key = (source_name or "").lower().strip()
    for prefix, score in _SOURCE_AUTHORITY.items():
        if key.startswith(prefix):
            return score
    return 18  # unknown but named source


def score_evidence_quality(cit: ReasoningCitation) -> tuple[int, str]:
    """Rank a citation 0-100 and assign a tier.

    Additive, explainable, deterministic — no model involved:
      * source authority (0-40): official Indian portals rank highest
      * verifiability (0-35): a clickable source URL and an attached document
      * recency (0-15): how recently the record was retrieved
      * completeness (0-10): presence of a publication date + reference
    """
    score = _authority(cit.source_name)

    # verifiability
    if cit.source_url:
        score += 20
    if cit.document_url:
        score += 15

    # recency (based on retrieved_at)
    if cit.retrieved_at:
        now = datetime.now(timezone.utc)
        ret = cit.retrieved_at if cit.retrieved_at.tzinfo else cit.retrieved_at.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (now - ret).days)
        if age_days <= 30:
            score += 15
        elif age_days <= 180:
            score += 10
        elif age_days <= 365:
            score += 5

    # completeness
    if cit.published_date:
        score += 6
    if cit.related_tender:
        score += 4

    score = max(0, min(100, score))
    if score >= 75:
        tier = "primary"
    elif score >= 55:
        tier = "corroborating"
    elif score >= 35:
        tier = "weak"
    else:
        tier = "unverified"
    return score, tier


def _document_for(record: InvestigationProcurementRecord) -> InvestigationDocumentResult | None:
    """Best attached document for a record — prefer a tender/contract PDF."""
    if not record.documents:
        return None
    preferred = [d for d in record.documents if (d.url and _looks_like_document(d))]
    chosen = preferred[0] if preferred else record.documents[0]
    return chosen


def _looks_like_document(doc: InvestigationDocumentResult) -> bool:
    hay = f"{doc.document_type} {doc.url or ''} {doc.title}".lower()
    return any(tok in hay for tok in ("pdf", "tender", "contract", "notice", "boq", "document"))


def format_citation(cit: ReasoningCitation) -> str:
    """Compose an analyst-grade, ready-to-paste citation string."""
    parts: list[str] = [cit.label.strip()]
    parts.append(cit.source_name)
    if cit.related_tender:
        parts.append(f"Ref {cit.related_tender}")
    if cit.published_date:
        parts.append(f"published {cit.published_date}")
    if cit.retrieved_at:
        parts.append(f"retrieved {cit.retrieved_at.date().isoformat()}")
    tail = f" {cit.source_url}" if cit.source_url else ""
    conf = f" (confidence {round(cit.confidence * 100)}%)" if cit.confidence else ""
    return f"{'. '.join(p for p in parts if p)}.{conf}{tail}".strip()


def citation_from_record(
    record: InvestigationProcurementRecord,
    *,
    confidence: float,
    related_entity: str | None = None,
    evidence_type: str = "procurement_record",
) -> ReasoningCitation:
    """Build a fully-provenanced citation from a single procurement record."""
    tender = record.tender
    meta = tender.metadata
    doc = _document_for(record)

    cit = ReasoningCitation(
        label=tender.title or tender.reference_number,
        source_name=meta.source_name,
        source_record_id=meta.source_record_id,
        source_url=meta.source_url,
        document_url=doc.url if doc else None,
        document_type=(doc.document_type if doc else None),
        retrieved_at=meta.retrieved_at,
        published_date=tender.published_date.isoformat() if tender.published_date else None,
        confidence=round(max(0.0, min(1.0, confidence)), 2),
        related_tender=tender.reference_number,
        related_entity=related_entity,
        evidence_type=evidence_type,
    )
    cit.citation = format_citation(cit)
    cit.quality, cit.quality_tier = score_evidence_quality(cit)
    return cit


def build_evidence_ledger(pkg: InvestigationPackage) -> list[ReasoningCitation]:
    """Every distinct record in the package as a fully-provenanced citation.

    De-duplicated by (source_name, source_record_id). Confidence is seeded from
    the record's presence and whether a verifiable URL/document exists, so the
    ledger honestly reflects how checkable each item is.
    """
    seen: set[tuple[str, str | None]] = set()
    ledger: list[ReasoningCitation] = []
    for record in pkg.records:
        meta = record.tender.metadata
        key = (meta.source_name, meta.source_record_id)
        if key in seen:
            continue
        seen.add(key)
        # Verifiable evidence (has a source URL) is scored higher than
        # index-only records that can't be opened directly.
        has_url = bool(meta.source_url)
        has_doc = bool(_document_for(record))
        confidence = 0.9 if (has_url and has_doc) else 0.75 if has_url else 0.5
        ledger.append(citation_from_record(record, confidence=confidence))
    # Strongest, most-verifiable evidence first — the analyst reads primary before weak.
    ledger.sort(key=lambda c: c.quality, reverse=True)
    return ledger


def grounding_report(
    pkg: InvestigationPackage,
    total_findings: int,
    evidence_backed_findings: int,
    total_citations: int,
) -> GroundingReport:
    documents_available = sum(1 for r in pkg.records if _document_for(r) is not None)
    return GroundingReport(
        total_findings=total_findings,
        evidence_backed_findings=evidence_backed_findings,
        total_citations=total_citations,
        records_reviewed=len(pkg.records),
        documents_available=documents_available,
        fully_grounded=(total_findings == 0 or evidence_backed_findings == total_findings),
    )
