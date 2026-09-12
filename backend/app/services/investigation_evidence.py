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
from app.schemas.investigation_reasoning import (
    EvidencePacket,
    EvidencePacketItem,
    GroundingReport,
    ReasoningCitation,
    ReasoningFinding,
)

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

# Stable public entry points for official procurement portals. These are used
# only when the captured URL is a known session-scoped NIC/GePNIC link.
_OFFICIAL_PORTAL_BASES: dict[str, str] = {
    "cppp": "https://eprocure.gov.in/eprocure/app",
    "gem": "https://gem.gov.in",
    "eproc_odisha": "https://tendersodisha.gov.in/nicgep/app",
    "odisha": "https://tendersodisha.gov.in/nicgep/app",
    "rajasthan": "https://eproc.rajasthan.gov.in",
    "maharashtra": "https://mahatenders.gov.in",
    "karnataka": "https://kppp.karnataka.gov.in",
    "kerala": "https://etenders.kerala.gov.in",
    "tamil_nadu": "https://tntenders.gov.in",
    "gujarat": "https://tender.nprocure.com",
    "delhi": "https://govtprocurement.delhi.gov.in",
    "west_bengal": "https://wbtenders.gov.in",
    "andhra_pradesh": "https://tender.apeprocurement.gov.in",
    "telangana": "https://tender.telangana.gov.in",
    "punjab": "https://eproc.punjab.gov.in",
    "haryana": "https://etenders.hry.nic.in",
    "uttar_pradesh": "https://etender.up.nic.in",
}

# NIC GePNIC listing/download links commonly contain these session-specific
# parameters. Such URLs are not durable after a portal/session restart.
_EPHEMERAL_URL_MARKERS = (
    "session=",
    "sp=",
    "FrontEndListTendersbyDate",
    "DirectLink",
    "%24DirectLink",
)


def _is_ephemeral_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(marker.lower() in lowered for marker in _EPHEMERAL_URL_MARKERS)


def _official_portal_url(source_name: str | None) -> str | None:
    key = (source_name or "").strip().casefold()
    if key in _OFFICIAL_PORTAL_BASES:
        return _OFFICIAL_PORTAL_BASES[key]
    for source_key, url in _OFFICIAL_PORTAL_BASES.items():
        if source_key in key or key in source_key:
            return url
    return None


def _stable_source_url(source_name: str | None, captured_url: str | None) -> str | None:
    """Return a durable official portal URL for user-facing evidence links.

    The captured URL remains available in the underlying procurement record for
    provenance, but session-scoped government deep links must not be exposed as
    clickable permanent links in the evidence ledger.
    """
    if not captured_url:
        return None
    if not _is_ephemeral_url(captured_url):
        return captured_url
    return _official_portal_url(source_name) or captured_url


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
    # User-facing source URL is normalised to a durable official portal when the
    # original capture was a session-scoped NIC/GePNIC deep link. The raw URL is
    # still retained by the underlying procurement record for audit provenance.
    source_url = _stable_source_url(meta.source_name, meta.source_url)
    # Session-scoped document URLs are not presented as permanent PDF links.
    document_url = doc.url if doc and not _is_ephemeral_url(doc.url) else None

    cit = ReasoningCitation(
        label=tender.title or tender.reference_number,
        source_name=meta.source_name,
        source_record_id=meta.source_record_id,
        source_url=source_url,
        document_url=document_url,
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
        has_url = bool(_stable_source_url(meta.source_name, meta.source_url))
        has_doc = bool(_document_for(record) and not _is_ephemeral_url(_document_for(record).url))
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
    verified_findings: int = 0,
) -> GroundingReport:
    documents_available = sum(1 for r in pkg.records if _document_for(r) is not None)
    return GroundingReport(
        total_findings=total_findings,
        evidence_backed_findings=evidence_backed_findings,
        verified_findings=verified_findings,
        total_citations=total_citations,
        records_reviewed=len(pkg.records),
        documents_available=documents_available,
        fully_grounded=(total_findings == 0 or evidence_backed_findings == total_findings),
    )


# Evidence tiers the packet counts as "primary" (official, high-authority source).
_PRIMARY_TIERS = frozenset({"primary"})


def build_evidence_packet(
    pkg: InvestigationPackage,
    findings: list[ReasoningFinding],
    *,
    subject: str,
    risk_level: str,
    generated_by: str = "deterministic",
) -> EvidencePacket:
    """Consolidate findings + their provenanced citations into one proof bundle.

    Deterministic and additive: it reuses the citations already resolved on each
    finding and the package records — it invents nothing. Packet-level totals let
    an investigator (or judge) see at a glance how much of the case is *verified*
    versus merely cited, how many primary sources back it, and whether every
    finding is grounded.
    """
    items: list[EvidencePacketItem] = [
        EvidencePacketItem(
            finding_title=f.title,
            severity=f.severity,
            verification=f.verification,
            score=f.score,
            occurrences=f.occurrences,
            supporting_records=f.supporting_records,
            citations=f.citations,
        )
        for f in findings
    ]

    verified = sum(1 for f in findings if f.verification == "verified")
    backed = sum(1 for f in findings if f.evidence_backed)
    ledger = build_evidence_ledger(pkg)
    distinct_sources = sorted({c.source_name for c in ledger if c.source_name})
    primary = sum(1 for c in ledger if c.quality_tier in _PRIMARY_TIERS)
    primary_share = round(primary / len(ledger), 2) if ledger else 0.0
    documents_available = sum(1 for r in pkg.records if _document_for(r) is not None)

    return EvidencePacket(
        subject=subject,
        risk_level=risk_level,  # type: ignore[arg-type]
        generated_by=generated_by,  # type: ignore[arg-type]
        items=items,
        total_findings=len(findings),
        verified_findings=verified,
        evidence_backed_findings=backed,
        total_evidence_items=len(ledger),
        documents_available=documents_available,
        distinct_sources=distinct_sources,
        primary_source_share=primary_share,
        fully_grounded=(not findings or backed == len(findings)),
    )
