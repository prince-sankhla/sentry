"""Evidence Packet — the auditor/journalist-facing deliverable.

This module assembles a single, self-contained **Evidence Packet** from a fully
executed :class:`InvestigationPackage` and its :class:`InvestigationReasoning`,
and renders it as a print-ready HTML document (Print → PDF works natively via
``@media print``). It is the artifact judges consume.

Design contract (identical to the rest of the reasoning layer):
* **The backend proves; nothing is invented.** Every number, tender, document,
  and source URL in the packet is copied from the executed package. The optional
  AI summary is the grounding-guarded narrative already produced upstream.
* **Deterministic.** The packet ID, section content, alternative explanations,
  and verification checklist are pure functions of the package — reproducible.
* **Oversight, not accusation.** Alternative (benign) explanations and a manual
  verification checklist are first-class sections, so a reader is handed both the
  indicator and the honest counter-hypothesis.

The 15 required sections (all grounded in existing package data):
 1 title · 2 investigation ID · 3 date · 4 methodology · 5 timeline ·
 6 triggered typologies · 7 supporting tenders · 8 supporting documents ·
 9 official source URLs · 10 evidence confidence · 11 missing evidence ·
 12 alternative explanations · 13 manual verification checklist ·
 14 investigator notes · 15 AI summary (optional).
"""

from __future__ import annotations

import hashlib
import html
from dataclasses import dataclass, field
from datetime import date, datetime

from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_reasoning import InvestigationReasoning
from app.schemas.investigation_risk import OVERSIGHT_DISCLAIMER

# --------------------------------------------------------------------------- deterministic rubrics

# Benign, procedurally-legitimate explanations per indicator/typology. These are
# a FIXED rubric (never model-generated) so the packet always hands the reader the
# honest counter-hypothesis alongside the indicator. Keyed by Risk Engine V2
# indicator id AND the analyst-finding indicator_type (they overlap 1:1).
_ALTERNATIVE_EXPLANATIONS: dict[str, str] = {
    "single_bidder": "A single recorded awardee may reflect a genuinely sole-qualified supplier, a specialised or proprietary requirement, an emergency/works contract with one winner, or simply that competing bids were not captured in the source feed (which records the awardee, not the bid count).",
    "high_value_direct_award": "High-value single-winner awards are normal for large EPC, defence, and infrastructure contracts, which are routinely won by a single prime contractor after a competitive process the feed may not fully expose.",
    "high_value": "A high contract value alone reflects project scale, not irregularity; large public works and equipment procurements legitimately run into hundreds of crore.",
    "repeat_supplier": "Repeat awards to one supplier can reflect legitimate specialisation, framework/rate contracts, or a small qualified-vendor pool for a niche requirement — not necessarily favouritism.",
    "buyer_concentration": "Award concentration can reflect a genuinely thin supplier market for the category, or a small sample of records rather than systemic steering.",
    "supplier_concentration": "A supplier winning only from one buyer may simply serve a single specialised client (e.g. a defence or railway-specific vendor), which is lawful.",
    "abnormal_value": "A value outlier can be a legitimately larger-scope lot, a different work category, or a small-sample artefact rather than mispricing.",
    "award_clustering": "A burst of awards in a short window is expected for a large national supplier bidding across many unrelated buyers, or reflects a common fiscal-year/quarter award cycle.",
    "suspicious_timing": "A short publication-to-award gap can be a lawful emergency/disaster procurement, a corrigendum-shortened cycle, or a pre-qualified/rate-contract call-off.",
    "duplicate_description": "Reused tender text is common for recurring or standardised requirements and often reflects a shared template, not tailored specifications.",
    "missing_award_data": "Missing award notices usually reflect feed latency or an unconcluded/cancelled tender rather than a concealed award.",
    "award_value_exceeds_tender": "An award above estimate can be a lawful price discovery outcome, a scope revision, or an estimate that was conservative.",
    "buyer_equals_supplier": "A buyer and supplier resolving to the same entity is most often a lawful intra-organisation or inter-unit transfer (common within a PSU group), or an entity-resolution artefact where a unit and its parent share one registration.",
    "missing_documents": "Absent attachments usually reflect a source portal that did not expose the PDF, not a suppressed record.",
    "gst_overlap": "A shared GSTIN across names can be a legitimate branch/division of one registered entity.",
    "director_overlap": "Shared directors are common across group companies and independent-director appointments and are not themselves improper.",
    "address_overlap": "A shared registered address can reflect a common business park, shared secretarial service, or group premises.",
}

# Per-typology manual verification steps an investigator performs to confirm or
# clear the indicator against the primary source. Fixed rubric, deterministic.
_VERIFICATION_STEPS: dict[str, list[str]] = {
    "single_bidder": ["Open the tender's NIT and evaluation minutes; confirm how many bids were received versus recorded.",
                      "Check for a documented single-bidder / nomination justification."],
    "high_value_direct_award": ["Confirm the value band's mandated approval and audit workflow was followed.",
                                "Verify whether an open competitive process preceded the single-winner award."],
    "repeat_supplier": ["List every award in the buyer→supplier relationship and check for a framework/rate contract.",
                        "Cross-check director/ownership records for a conflict of interest."],
    "buyer_concentration": ["Benchmark the concentration against comparable buyers for the same category.",
                            "Confirm whether the supplier market for this category is genuinely thin."],
    "supplier_concentration": ["Confirm whether the supplier is a category-specific vendor for this buyer.",
                               "Check for a captive/related-party relationship."],
    "abnormal_value": ["Compare the outlier award's scope/BoQ against the baseline lots.",
                       "Confirm the value against the awarded contract and any published disclosure."],
    "award_clustering": ["Confirm the clustered awards are unrelated procurements, not a split of one requirement.",
                         "Check against the buyer's fiscal award calendar."],
    "suspicious_timing": ["Retrieve the tender calendar (publication, clarification, close, award) and confirm the bid window.",
                          "Check for an emergency/disaster or corrigendum justification for a compressed cycle."],
    "buyer_equals_supplier": ["Confirm whether the buyer is a distinct legal person from the supplier, or the same entity/unit.",
                              "Classify the transaction: lawful inter-unit transfer, subsidiary/JV, or improper self-award.",
                              "Verify both CINs on MCA21 and confirm the entity-resolution boundary."],
    "missing_award_data": ["Request the missing award notices for the closed tenders."],
    "duplicate_description": ["Compare the full specifications of the duplicated tenders for tailoring."],
    "award_value_exceeds_tender": ["Obtain the scope-change/variation record justifying the value increase."],
    "missing_documents": ["Request the tender/contract PDFs directly from the procuring entity."],
}

_GENERIC_VERIFICATION_STEPS: list[str] = [
    "Open each official source URL below and confirm the tender reference, buyer, supplier, value, and dates match this packet.",
    "Corroborate each awarded supplier's identity (CIN on MCA21, GSTIN on the GST portal).",
    "Confirm every attached document opens and matches the record it is cited against.",
]

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}

# --------------------------------------------------------------------------- source-URL stability (P1)

# Stable public entry points per source portal, used to give an auditor a durable
# way to locate a record when the captured deep-link is session-scoped.
_PORTAL_BASE: dict[str, str] = {
    "eproc_odisha": "https://tendersodisha.gov.in",
    "cppp": "https://eprocure.gov.in",
    "gem": "https://gem.gov.in",
}

# Markers of an ephemeral, session-scoped portal link (NIC GePNIC "DirectLink"
# search URLs carry a live session token and a date-list page, not a permanent
# tender-detail URL — they expire and must never be presented as permanent evidence).
_EPHEMERAL_URL_MARKERS = ("session=", "sp=", "FrontEndListTendersbyDate", "DirectLink", "%24DirectLink")


def _is_ephemeral_url(url: str | None) -> bool:
    if not url:
        return False
    return any(marker in url for marker in _EPHEMERAL_URL_MARKERS)


def _portal_base(source_name: str | None) -> str:
    return _PORTAL_BASE.get((source_name or "").strip().casefold(), "")


# --------------------------------------------------------------------------- document classification (P2)

# The portal "source notice" is the tender listing entry itself — NOT a primary
# procurement document. Everything else the connectors capture (NIT, BoQ,
# corrigendum, tender/award notice, technical spec, eligibility) is primary.
_NON_PRIMARY_DOC_TYPES = {"source_notice", "source notice", ""}


def _is_primary_document(doc_type: str | None) -> bool:
    return (doc_type or "").strip().casefold() not in _NON_PRIMARY_DOC_TYPES


# --------------------------------------------------------------------------- award-timing note (C3)

def _award_timing_note(pkg) -> str:
    """Explain, deterministically, why 'Missing Award' is or is not an active typology."""
    from app.services.investigation_indicators import award_timing_status

    status = award_timing_status(pkg)
    closed = status["closed_no_award"]
    if not closed:
        return ""
    grace, as_of = status["grace_days"], status["as_of"]
    n = len(closed)
    if status["active"]:
        return (
            f"Missing Award is ACTIVE: {len(status['overdue'])} tender(s) closed more than {grace} days "
            f"before the data snapshot ({as_of}) with no award on record — beyond the expected "
            f"award-publication window, so the absence is treated as a genuine transparency gap."
        )
    if as_of is None:
        return (
            f"Missing Award is NOT flagged: {n} tender(s) have no award on record, but the data-retrieval "
            "date is unavailable, so time elapsed since close cannot be established — a missing-award "
            "anomaly is not asserted without that timing."
        )
    med = status["median_elapsed"]
    return (
        f"Missing Award is NOT flagged: {n} tender(s) have no award on record, but they closed a median of "
        f"{med} day(s) before the data snapshot ({as_of}) — within the expected ~{grace}-day "
        "award-publication lifecycle. Awards are pending, not withheld; the absence of an award is not yet "
        "an anomaly."
    )


# --------------------------------------------------------------------------- base-rate context (C5)

_MIN_ABNORMAL_SAMPLE = 5  # mirror the abnormal-value detector's minimum-sample requirement


def _baseline_note(pkg) -> str:
    """State the comparative/statistical context available — or its absence — never invented."""
    records = pkg.records
    n = len(records)
    if n == 0:
        return ""
    buyers = {(r.tender.procuring_entity or "").split("||")[0].strip() for r in records if r.tender.procuring_entity}
    award_values = [a.award_value for r in records for a in r.awards if a.award_value is not None]
    years = {r.tender.published_date.year for r in records if r.tender.published_date}
    # Insufficient comparative history: a single buyer/category and too few awarded
    # values to compute a price baseline → say so explicitly; invent no base rate.
    if len(buyers) <= 1 and len(award_values) < _MIN_ABNORMAL_SAMPLE:
        return (
            f"Statistical context — category/peer baseline unavailable: this assessment draws on {n} "
            "record(s) from a single procuring entity, with no prior-period or peer-buyer comparators in "
            "scope and too few awarded values to compute a category price baseline. Findings rest on "
            "internal structure alone; no statistical base rate was computed and none was invented — "
            "interpret any anomaly signal cautiously as a lead, not a measured deviation."
        )
    parts = [f"{n} records across {len(buyers)} procuring entit{'y' if len(buyers) == 1 else 'ies'}"]
    if years:
        parts.append(f"publication years {min(years)}–{max(years)}" if len(years) > 1 else f"publication year {next(iter(years))}")
    if len(award_values) >= _MIN_ABNORMAL_SAMPLE:
        med = sorted(award_values)[len(award_values) // 2]
        parts.append(f"award-value baseline: median {med:,.0f} over {len(award_values)} awards")
    else:
        parts.append("no category price baseline (fewer than "
                     f"{_MIN_ABNORMAL_SAMPLE} awarded values) — value anomalies not computed")
    return "Statistical context — " + "; ".join(parts) + "."


# --------------------------------------------------------------------------- structured document

@dataclass
class PacketTypology:
    name: str
    severity: str
    kind: str            # "pattern" | "indicator"
    detail: str
    evidence_status: str = ""
    context_notes: list[str] = field(default_factory=list)
    supporting_tenders: list[str] = field(default_factory=list)


@dataclass
class PacketTender:
    reference: str
    title: str
    buyer: str
    supplier: str
    estimated_value: str
    award_value: str
    currency: str
    published: str
    closing: str
    source_name: str
    source_url: str
    source_is_permalink: bool = True      # False when the captured URL is session-scoped (P1)
    stable_portal: str = ""               # durable portal entry point for this record (P1)


@dataclass
class PacketDocument:
    title: str
    doc_type: str
    url: str
    tender_reference: str
    source_name: str
    is_primary: bool = True               # False for portal "source notices" (P2)


@dataclass
class EvidencePacketDocument:
    """Fully-assembled Evidence Packet — the 15 required sections, grounded."""

    title: str
    investigation_id: str
    generated_at: str
    subject: str
    investigation_type: str
    risk_level: str
    risk_score: int
    verification_level: str
    confidence_pct: int
    confidence_level: str
    confidence_explanation: str
    confidence_dimensions: list[tuple[str, int, str]]
    methodology: list[str]
    timeline: list[tuple[str, str, str, str]]           # (date, label, source, tender)
    typologies: list[PacketTypology]
    tenders: list[PacketTender]
    documents: list[PacketDocument]
    source_urls: list[tuple[str, str]]                  # (label, url)
    missing_evidence: list[str]
    alternative_explanations: list[tuple[str, str]]     # (typology name, explanation)
    verification_checklist: list[str]
    ai_summary: str
    ai_summary_provenance: str
    # Packet-level integrity totals (reused from reasoning.evidence_packet).
    total_findings: int
    verified_findings: int
    total_evidence_items: int
    documents_available: int
    primary_source_share: float
    fully_grounded: bool
    insufficient_evidence: bool
    # P1 — source-URL stability. When true, at least one source link is session-scoped
    # and must not be treated as a permanent URL; the caveat explains the durable pointer.
    has_ephemeral_urls: bool = False
    evidence_url_caveat: str = ""
    # P2 — primary-document availability. When false, only portal notices were
    # retrievable (no NIT/BoQ/corrigendum/award letter); the note states this plainly.
    has_primary_documents: bool = True
    primary_documents_note: str = ""
    # C3 — award as-of-time gate. Explains WHY "Missing Award" is / is not an active
    # typology (award pending within the expected lifecycle vs. genuinely overdue).
    award_timing_note: str = ""
    # C5 — statistical/base-rate context. States the comparative history available
    # (or its absence), so a finding never reads as stronger than the evidence.
    baseline_note: str = ""
    disclaimer: str = OVERSIGHT_DISCLAIMER


# --------------------------------------------------------------------------- helpers

def _fmt_value(value, currency: str | None) -> str:
    if value is None:
        return "—"
    try:
        return f"{value:,.0f} {currency or ''}".strip()
    except (TypeError, ValueError):
        return str(value)


def _fmt_date(value: date | datetime | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def _packet_id(subject: str, refs: list[str]) -> str:
    """Deterministic, reproducible packet ID from subject + evidence references."""
    basis = subject.strip().casefold() + "|" + "|".join(sorted(refs))
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8].upper()
    return f"SENTRY-CASE-{digest}"


def _clean_buyer(raw: str | None) -> str:
    """Render a pipe-delimited ``category||org||unit`` buyer string readably.

    Procuring entities are stored as ``segment||segment`` hierarchies. Showing only
    the FIRST segment hides the specific procuring body — for e.g.
    ``Municipal Bodies||Dharmagarh NAC`` that would print the generic category
    "Municipal Bodies" and drop the council the whole case is about. We instead
    join every distinct segment with an en-dash so both the category and the
    specific unit are always visible; nothing is hidden and nothing is invented.
    """
    if not raw:
        return "—"
    segments = [s.strip() for s in raw.split("||") if s.strip()]
    # De-duplicate while preserving order (buyer strings sometimes repeat a segment).
    seen: set[str] = set()
    unique = [s for s in segments if not (s in seen or seen.add(s))]
    return " — ".join(unique) or raw.strip()


# --------------------------------------------------------------------------- builder

def build_packet_document(
    pkg: InvestigationPackage,
    reasoning: InvestigationReasoning,
    *,
    subject: str,
    generated_at: datetime | None = None,
) -> EvidencePacketDocument:
    """Assemble the complete Evidence Packet from the executed investigation.

    Pure/deterministic except ``generated_at`` (the export timestamp), which the
    caller injects; everything else is a projection of the package.
    """
    risk_v2 = pkg.risk_assessment_v2
    report = reasoning.analyst_report
    refs = [r.tender.reference_number for r in pkg.records]
    generated = (generated_at or datetime(1970, 1, 1)).date().isoformat()

    # 6 — triggered typologies (patterns first, then indicators).
    typologies: list[PacketTypology] = []
    if risk_v2 is not None:
        for p in risk_v2.patterns:
            typologies.append(PacketTypology(
                name=p.name, severity=p.severity, kind="pattern",
                detail=p.reason or p.rule, evidence_status="",
                supporting_tenders=sorted({t for i in risk_v2.indicators if i.id in p.indicators for t in i.supporting_records}),
            ))
        for i in risk_v2.indicators:
            typologies.append(PacketTypology(
                name=i.name, severity=i.severity, kind="indicator",
                detail=i.reason, evidence_status=i.evidence_status,
                context_notes=list(i.context_notes), supporting_tenders=list(i.supporting_records),
            ))

    # 7 — every supporting tender.
    tenders: list[PacketTender] = []
    for r in pkg.records:
        t = r.tender
        supplier = ", ".join(sorted({a.company_name for a in r.awards})) or "—"
        award_val = next((a.award_value for a in r.awards if a.award_value is not None), None)
        award_cur = next((a.currency for a in r.awards if a.award_value is not None), t.currency)
        tender_url = t.metadata.source_url or ""
        tenders.append(PacketTender(
            reference=t.reference_number, title=t.title or "—", buyer=_clean_buyer(t.procuring_entity),
            supplier=supplier, estimated_value=_fmt_value(t.estimated_value, t.currency),
            award_value=_fmt_value(award_val, award_cur), currency=t.currency,
            published=_fmt_date(t.published_date), closing=_fmt_date(t.closing_date),
            source_name=t.metadata.source_name, source_url=tender_url,
            source_is_permalink=not _is_ephemeral_url(tender_url),
            stable_portal=_portal_base(t.metadata.source_name),
        ))

    # 8 — every supporting document.
    documents: list[PacketDocument] = []
    for r in pkg.records:
        for d in r.documents:
            documents.append(PacketDocument(
                title=d.title or "—", doc_type=d.document_type or "document",
                url=d.url or d.metadata.source_url or "", tender_reference=r.tender.reference_number,
                source_name=d.metadata.source_name,
                is_primary=_is_primary_document(d.document_type),
            ))

    # P1 — flag session-scoped source links so they are never presented as permanent.
    has_ephemeral_urls = any(not t.source_is_permalink for t in tenders)
    evidence_url_caveat = ""
    if has_ephemeral_urls:
        portals = sorted({t.stable_portal for t in tenders if not t.source_is_permalink and t.stable_portal})
        portal_hint = f" Locate each record by its Tender Reference Number at {', '.join(portals)}." if portals else ""
        evidence_url_caveat = (
            "The source portal (NIC GePNIC) exposes only session-scoped deep links, which "
            "expire and are not permanent URLs. Each source link below is therefore a session "
            "link, not a permalink; the durable, citable identifier for every record is its "
            "Tender Reference Number." + portal_hint
        )

    # P2 — state plainly when no primary procurement documents were retrievable.
    has_primary_documents = any(d.is_primary for d in documents)
    primary_documents_note = ""
    if not has_primary_documents:
        primary_documents_note = (
            "No primary procurement documents (NIT, BoQ, corrigendum, tender PDF, or award "
            "letter) were retrievable from the source portal for these records. The only "
            "attached artefact per tender is the portal source notice (the tender listing "
            "entry itself). Evidence is authentic but thin — sufficient to establish that the "
            "tenders exist, insufficient to examine their specifications, bidders, or award."
        )

    # 9 — every official source URL (tender pages + document URLs), de-duplicated.
    seen_urls: set[str] = set()
    source_urls: list[tuple[str, str]] = []
    for r in pkg.records:
        u = r.tender.metadata.source_url
        if u and u not in seen_urls:
            seen_urls.add(u)
            source_urls.append((f"Tender {r.tender.reference_number} ({r.tender.metadata.source_name})", u))
    for d in documents:
        if d.url and d.url not in seen_urls:
            seen_urls.add(d.url)
            source_urls.append((f"{d.title} ({d.source_name})", d.url))

    # 10 — evidence confidence (Risk Engine V2 headline + multidimensional breakdown).
    conf_pct = int(round((risk_v2.confidence.score if risk_v2 and risk_v2.confidence else reasoning.confidence) * 100))
    conf_level = (risk_v2.confidence.level if risk_v2 and risk_v2.confidence else "").replace("_", " ")
    conf_expl = risk_v2.confidence.explanation if risk_v2 and risk_v2.confidence else ""
    dims: list[tuple[str, int, str]] = []
    if report and report.confidence_assessment:
        for d in report.confidence_assessment.dimensions:
            dims.append((d.label, int(round(d.score * 100)), d.detail))

    # 12 — alternative explanations, one per distinct triggered typology.
    alt: list[tuple[str, str]] = []
    seen_alt: set[str] = set()
    if risk_v2 is not None:
        for i in risk_v2.indicators:
            if i.id in _ALTERNATIVE_EXPLANATIONS and i.id not in seen_alt:
                seen_alt.add(i.id)
                alt.append((i.name, _ALTERNATIVE_EXPLANATIONS[i.id]))

    # 13 — manual verification checklist (per-typology steps + generic steps).
    checklist: list[str] = list(_GENERIC_VERIFICATION_STEPS)
    if risk_v2 is not None:
        for i in risk_v2.indicators:
            for step in _VERIFICATION_STEPS.get(i.id, []):
                labelled = f"[{i.name}] {step}"
                if labelled not in checklist:
                    checklist.append(labelled)

    # 15 — AI summary (optional) with honest provenance.
    if reasoning.generated_by == "llm":
        prov = f"Phrased by {reasoning.provider or 'LLM'}"
        if reasoning.model:
            prov += f" · {reasoning.model}"
        prov += " — accepted by the deterministic grounding guard (no fabricated quantity or entity)."
    else:
        prov = "Composed deterministically from package facts (no live LLM narration)."

    ep = reasoning.evidence_packet

    return EvidencePacketDocument(
        title=f"Procurement Integrity Evidence Packet — {subject}",
        investigation_id=_packet_id(subject, refs),
        generated_at=generated,
        subject=subject,
        investigation_type=reasoning.investigation_type,
        risk_level=reasoning.risk_level,
        risk_score=(risk_v2.overall_score if risk_v2 else 0),
        verification_level=_verification_level(reasoning),
        confidence_pct=conf_pct,
        confidence_level=conf_level,
        confidence_explanation=conf_expl,
        confidence_dimensions=dims,
        methodology=_methodology(),
        timeline=[(_fmt_date(e.event_date), e.label, e.source_name, e.related_tender or "") for e in pkg.timeline],
        typologies=typologies,
        tenders=tenders,
        documents=documents,
        source_urls=source_urls,
        missing_evidence=(report.missing_evidence if report else []),
        alternative_explanations=alt,
        verification_checklist=checklist,
        ai_summary=reasoning.executive_summary,
        ai_summary_provenance=prov,
        total_findings=(ep.total_findings if ep else len(reasoning.findings)),
        verified_findings=(ep.verified_findings if ep else 0),
        total_evidence_items=(ep.total_evidence_items if ep else len(reasoning.evidence_ledger)),
        documents_available=(ep.documents_available if ep else len(documents)),
        primary_source_share=(ep.primary_source_share if ep else 0.0),
        fully_grounded=reasoning.grounding.fully_grounded,
        insufficient_evidence=reasoning.insufficient_evidence,
        has_ephemeral_urls=has_ephemeral_urls,
        evidence_url_caveat=evidence_url_caveat,
        has_primary_documents=has_primary_documents,
        primary_documents_note=primary_documents_note,
        award_timing_note=_award_timing_note(pkg),
        baseline_note=_baseline_note(pkg),
    )


def _verification_level(reasoning: InvestigationReasoning) -> str:
    if reasoning.insufficient_evidence or not reasoning.findings:
        return "UNVERIFIED"
    g = reasoning.grounding
    if g.total_findings and g.verified_findings == g.total_findings:
        return "VERIFIED"
    if g.evidence_backed_findings == g.total_findings:
        return "EVIDENCE-BACKED"
    return "PARTIAL"


def _methodology() -> list[str]:
    return [
        "Subject resolved to a canonical entity; records retrieved only where they directly reference that entity (precision retrieval, Indian sources only).",
        "Procurement-integrity indicators computed by deterministic detectors over the retrieved records — no model decides risk.",
        "Risk classified by the deterministic Risk Engine V2: named rule-combination patterns over evidence-validated indicators; overall severity is the strongest pattern, never an arithmetic sum.",
        "Each indicator's evidence independently validated (verified / probable / unknown) against the attached records; unverifiable indicators are capped in severity.",
        "Context rules suppress or hold severity for expected situations (emergency, disaster, correction notice, PSU-internal procurement) to reduce false positives.",
        "Any AI narrative is constrained to package facts and rejected by a deterministic grounding guard if it introduces a quantity or entity not in evidence.",
        "This is an oversight signal for investigator review — it does not allege wrongdoing.",
    ]


# --------------------------------------------------------------------------- HTML renderer

_SEVERITY_CLASS = {"low": "sev-low", "medium": "sev-med", "high": "sev-high", "critical": "sev-crit"}


def _e(text: object) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def _link(url: str, label: str | None = None) -> str:
    if not url:
        return _e(label or "—")
    return f'<a href="{_e(url)}" target="_blank" rel="noopener">{_e(label or url)}</a>'


def _sev_badge(sev: str) -> str:
    return f'<span class="badge {_SEVERITY_CLASS.get(sev, "sev-low")}">{_e(sev.upper())}</span>'


def render_packet_html(doc: EvidencePacketDocument) -> str:
    """Render the Evidence Packet as a self-contained, print-ready HTML document."""
    sections: list[str] = []

    def section(num: int, title: str, body: str) -> None:
        sections.append(
            f'<section class="pkt"><h2><span class="num">{num}</span>{_e(title)}</h2>{body}</section>'
        )

    # 4 — methodology
    section(4, "Investigation methodology",
            "<ol class='meth'>" + "".join(f"<li>{_e(m)}</li>" for m in doc.methodology) + "</ol>")

    # 5 — timeline
    if doc.timeline:
        rows = "".join(
            f"<tr><td class='mono'>{_e(d)}</td><td>{_e(label)}</td><td>{_e(src)}</td>"
            f"<td class='mono'>{_e(ref)}</td></tr>"
            for d, label, src, ref in doc.timeline
        )
        body = f"<table><thead><tr><th>Date</th><th>Event</th><th>Source</th><th>Tender</th></tr></thead><tbody>{rows}</tbody></table>"
    else:
        body = "<p class='muted'>No dated events available.</p>"
    section(5, "Timeline", body)

    # 6 — triggered typologies
    if doc.typologies:
        rows = "".join(
            f"<tr><td>{_sev_badge(t.severity)}</td><td><strong>{_e(t.name)}</strong>"
            f"<span class='kind'>{_e(t.kind)}</span></td><td>{_e(t.detail)}"
            + (f"<div class='ctx'>Context: {_e('; '.join(t.context_notes))}</div>" if t.context_notes else "")
            + f"</td><td>{_e(t.evidence_status or '—')}</td>"
            f"<td class='mono small'>{_e(', '.join(t.supporting_tenders[:8]))}</td></tr>"
            for t in doc.typologies
        )
        body = f"<table><thead><tr><th>Severity</th><th>Typology</th><th>Basis</th><th>Evidence</th><th>Supporting tenders</th></tr></thead><tbody>{rows}</tbody></table>"
    else:
        body = "<p class='muted'>No procurement-integrity typologies triggered.</p>"
    if doc.award_timing_note:
        body += f"<p class='muted small'><strong>Award-timing gate:</strong> {_e(doc.award_timing_note)}</p>"
    section(6, "Triggered typologies", body)

    # 7 — supporting tenders. The Reference cell links to the captured source URL,
    # but when that link is session-scoped it is flagged (P1) and the durable
    # identifier (the reference number itself) is what an auditor should cite.
    if doc.tenders:
        def _tender_ref_cell(t: PacketTender) -> str:
            if t.source_url and not t.source_is_permalink:
                link = _link(t.source_url, t.reference)
                return f"{link} <span class='warn small'>session link</span>"
            return _link(t.source_url, t.reference)
        rows = "".join(
            f"<tr><td class='mono'>{_tender_ref_cell(t)}</td><td>{_e(t.title)}</td>"
            f"<td>{_e(t.buyer)}</td><td>{_e(t.supplier)}</td>"
            f"<td class='num'>{_e(t.estimated_value)}</td><td class='num'>{_e(t.award_value)}</td>"
            f"<td class='mono'>{_e(t.published)}</td><td class='mono'>{_e(t.closing)}</td>"
            f"<td>{_e(t.source_name)}</td></tr>"
            for t in doc.tenders
        )
        body = (f"<table><thead><tr><th>Reference</th><th>Title</th><th>Buyer</th><th>Awarded supplier</th>"
                f"<th>Estimate</th><th>Award</th><th>Published</th><th>Closing</th><th>Source</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>")
        if doc.has_ephemeral_urls:
            body += f"<p class='muted small'>{_e(doc.evidence_url_caveat)}</p>"
    else:
        body = "<p class='muted'>No supporting tenders.</p>"
    section(7, "Every supporting tender", body)

    # 8 — supporting documents. Primary procurement documents (NIT/BoQ/award/etc.)
    # are distinguished from the portal "source notice" (the tender listing entry),
    # and when no primary document exists that is stated plainly (P2).
    if doc.documents:
        def _doc_type_cell(d: PacketDocument) -> str:
            if not d.is_primary:
                return "<span class='muted'>portal source notice</span> <span class='warn small'>not a primary document</span>"
            return f"<span class='ok small'>primary</span> {_e(d.doc_type)}"
        rows = "".join(
            f"<tr><td>{_link(d.url, d.title)}</td><td>{_doc_type_cell(d)}</td>"
            f"<td class='mono'>{_e(d.tender_reference)}</td><td>{_e(d.source_name)}</td></tr>"
            for d in doc.documents
        )
        body = f"<table><thead><tr><th>Document</th><th>Type</th><th>Tender</th><th>Source</th></tr></thead><tbody>{rows}</tbody></table>"
        if not doc.has_primary_documents and doc.primary_documents_note:
            body = f"<p class='warn small'>{_e(doc.primary_documents_note)}</p>" + body
    else:
        body = "<p class='muted'>No attached documents.</p>"
    section(8, "Every supporting document", body)

    # 9 — official source URLs. Session-scoped links are marked so none is read as
    # a permanent URL; the caveat names the durable identifier to cite instead (P1).
    if doc.source_urls:
        def _url_item(label: str, url: str) -> str:
            tag = " <span class='warn small'>session link — may expire</span>" if _is_ephemeral_url(url) else ""
            return f"<li>{_e(label)} — {_link(url)}{tag}</li>"
        items = "".join(_url_item(label, url) for label, url in doc.source_urls)
        caveat = f"<p class='warn small'>{_e(doc.evidence_url_caveat)}</p>" if doc.has_ephemeral_urls else ""
        body = caveat + f"<ul class='urls'>{items}</ul>"
    else:
        body = "<p class='muted'>No source URLs recorded.</p>"
    section(9, "Official government source URLs", body)

    # 10 — evidence confidence
    conf_body = (
        f"<p class='big'>{doc.confidence_pct}% <span class='muted'>({_e(doc.confidence_level)})</span></p>"
        f"<p>{_e(doc.confidence_explanation)}</p>"
    )
    if doc.confidence_dimensions:
        bars = "".join(
            f"<tr><td>{_e(label)}</td><td class='num'>{pct}%</td>"
            f"<td class='barcell'><span class='bar' style='width:{max(2,pct)}%'></span></td>"
            f"<td class='small muted'>{_e(detail)}</td></tr>"
            for label, pct, detail in doc.confidence_dimensions
        )
        conf_body += f"<table><thead><tr><th>Dimension</th><th>Score</th><th></th><th>Detail</th></tr></thead><tbody>{bars}</tbody></table>"
    conf_body += (f"<p class='muted small'>Evidence completeness measures how <em>checkable</em> the "
                  f"evidence is — URLs and documents present, awards and dates complete, entities "
                  f"resolved. It is a data-completeness metric, <strong>not</strong> a probability that "
                  f"any finding is true, and is <strong>independent of the risk score</strong>.</p>")
    if doc.baseline_note:
        conf_body += f"<p class='muted small'><strong>Base rate:</strong> {_e(doc.baseline_note)}</p>"
    section(10, "Evidence completeness", conf_body)

    # 11 — missing evidence
    if doc.missing_evidence:
        body = "<ul class='gaps'>" + "".join(f"<li>{_e(m)}</li>" for m in doc.missing_evidence) + "</ul>"
    else:
        body = "<p class='muted'>No material evidence gaps detected in the retrieved records.</p>"
    section(11, "Missing evidence", body)

    # 12 — alternative explanations
    if doc.alternative_explanations:
        body = ("<p class='muted small'>Every indicator is presented with its honest benign counter-hypothesis. "
                "An investigator must rule these out before drawing any adverse conclusion.</p>"
                + "".join(f"<div class='alt'><div class='alt-h'>{_e(name)}</div><p>{_e(expl)}</p></div>"
                          for name, expl in doc.alternative_explanations))
    else:
        body = "<p class='muted'>No typologies requiring alternative explanations.</p>"
    section(12, "Alternative explanations", body)

    # 13 — manual verification checklist
    items = "".join(f"<li><span class='chk'>&#9744;</span> {_e(s)}</li>" for s in doc.verification_checklist)
    section(13, "Manual verification checklist", f"<ul class='checklist'>{items}</ul>")

    # 14 — investigator notes
    section(14, "Investigator notes",
            "<div class='notes'>" + "".join("<div class='rule'></div>" for _ in range(8)) + "</div>"
            "<div class='signoff'><div>Investigator: ______________________</div>"
            "<div>Date: ____________</div><div>Disposition: &#9744; Confirmed &nbsp; &#9744; Cleared &nbsp; &#9744; Escalated</div></div>")

    # 15 — AI summary (optional)
    if doc.ai_summary:
        section(15, "AI summary (advisory)",
                f"<blockquote>{_e(doc.ai_summary)}</blockquote>"
                f"<p class='muted small'>{_e(doc.ai_summary_provenance)}</p>")

    body_html = "".join(sections)
    verdict_class = _SEVERITY_CLASS.get(doc.risk_level, "sev-low")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(doc.investigation_id)} — Evidence Packet</title>
<style>{_CSS}</style></head>
<body>
<div class="toolbar no-print">
  <button onclick="window.print()">Print / Save as PDF</button>
  <span class="hint">Use your browser's “Save as PDF” in the print dialog for a PDF copy.</span>
</div>
<article class="doc">
  <header class="cover">
    <div class="brand">SENTRY · Procurement Integrity</div>
    <h1>{_e(doc.title)}</h1>
    <div class="meta-grid">
      <div><span>Investigation ID</span><strong class="mono">{_e(doc.investigation_id)}</strong></div>
      <div><span>Date</span><strong>{_e(doc.generated_at)}</strong></div>
      <div><span>Subject</span><strong>{_e(doc.subject)}</strong></div>
      <div><span>Type</span><strong>{_e(doc.investigation_type)}</strong></div>
      <div><span>Risk (deterministic)</span><strong>{_sev_badge(doc.risk_level)} {doc.risk_score}/100</strong></div>
      <div><span>Evidence level</span><strong class="vlevel">{_e(doc.verification_level)}</strong></div>
      <div><span>Evidence completeness</span><strong>{doc.confidence_pct}% ({_e(doc.confidence_level)})</strong></div>
      <div><span>Primary-source share</span><strong>{int(round(doc.primary_source_share*100))}%</strong></div>
    </div>
    <div class="totals">
      {doc.verified_findings}/{doc.total_findings} findings verified ·
      {doc.total_evidence_items} evidence items · {doc.documents_available} documents ·
      {"fully grounded" if doc.fully_grounded else "partially grounded"}
    </div>
    <div class="disclaimer">{_e(doc.disclaimer)}</div>
  </header>
  {body_html}
  <footer class="foot">
    <div>{_e(doc.investigation_id)} · generated {_e(doc.generated_at)} · SENTRY oversight tool</div>
    <div class="muted small">Deterministic risk · evidence-validated · grounding-guarded. Every figure above traces to an official source URL in §9.</div>
  </footer>
</article>
</body></html>"""


_CSS = """
:root{--ink:#14181f;--muted:#6b7480;--line:#dfe3e8;--bg:#fff;--accent:#7a4d2b;--accentbg:#f6efe8;
--low:#5a6b3f;--med:#8a6d1f;--high:#a24a1e;--crit:#8b1e1e;}
*{box-sizing:border-box}
body{margin:0;background:#eef1f4;color:var(--ink);font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.toolbar{position:sticky;top:0;display:flex;gap:12px;align-items:center;padding:10px 16px;background:#14181f;color:#fff;z-index:10}
.toolbar button{background:var(--accent);color:#fff;border:0;padding:8px 16px;border-radius:6px;font-weight:600;cursor:pointer}
.toolbar .hint{color:#aeb6bf;font-size:12px}
.doc{max-width:960px;margin:20px auto;background:var(--bg);padding:44px 52px;box-shadow:0 1px 4px rgba(0,0,0,.12)}
.cover{border-bottom:3px solid var(--ink);padding-bottom:22px;margin-bottom:8px}
.brand{letter-spacing:.14em;text-transform:uppercase;font-size:11px;color:var(--accent);font-weight:700}
h1{font-size:26px;margin:8px 0 18px;line-height:1.25}
.meta-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px 28px;margin-bottom:14px}
.meta-grid div{display:flex;justify-content:space-between;gap:12px;border-bottom:1px dotted var(--line);padding:4px 0}
.meta-grid span{color:var(--muted)}
.vlevel{color:var(--accent);letter-spacing:.06em}
.warn{color:var(--crit);font-weight:600}
.ok{color:var(--low);font-weight:600}
.totals{background:var(--accentbg);border:1px solid #ecdfd2;border-radius:6px;padding:8px 12px;font-size:13px;color:#5c4326}
.disclaimer{margin-top:12px;font-size:12px;color:var(--muted);font-style:italic;border-left:3px solid var(--line);padding-left:12px}
.pkt{margin:26px 0;page-break-inside:avoid}
.pkt h2{font-size:16px;border-bottom:2px solid var(--ink);padding-bottom:6px;display:flex;align-items:center;gap:10px}
.num{display:inline-flex;width:24px;height:24px;align-items:center;justify-content:center;background:var(--ink);color:#fff;border-radius:50%;font-size:12px}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:12.5px}
th{text-align:left;background:#f4f6f8;border-bottom:2px solid var(--line);padding:6px 8px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
td{border-bottom:1px solid var(--line);padding:6px 8px;vertical-align:top}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11.5px}
.small{font-size:11px}.num{white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid #d8c3ad}
.muted{color:var(--muted)}.big{font-size:24px;font-weight:700;margin:2px 0}
.badge{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:700;color:#fff}
.sev-low{background:var(--low)}.sev-med{background:var(--med)}.sev-high{background:var(--high)}.sev-crit{background:var(--crit)}
.kind{margin-left:8px;font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.ctx{color:var(--muted);font-size:11px;margin-top:3px;font-style:italic}
.meth li,.gaps li{margin:5px 0}
.urls{list-style:none;padding:0}.urls li{padding:4px 0;border-bottom:1px dotted var(--line);word-break:break-all}
.alt{border-left:3px solid var(--accent);background:var(--accentbg);padding:8px 12px;margin:8px 0;border-radius:0 6px 6px 0}
.alt-h{font-weight:700;font-size:13px}
.alt p{margin:4px 0 0;font-size:12.5px}
.checklist{list-style:none;padding:0}.checklist li{padding:5px 0;border-bottom:1px dotted var(--line)}
.chk{color:var(--accent);margin-right:8px}
.barcell{width:120px}.bar{display:block;height:8px;background:var(--accent);border-radius:4px}
.notes{margin-top:6px}.notes .rule{border-bottom:1px solid var(--line);height:26px}
.signoff{margin-top:14px;display:flex;gap:24px;flex-wrap:wrap;font-size:12px;color:#333}
blockquote{margin:6px 0;padding:10px 14px;background:#f6f8fa;border-left:3px solid var(--muted);font-size:13.5px}
.foot{margin-top:34px;border-top:2px solid var(--ink);padding-top:10px;font-size:12px;color:#333;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
@media print{
  body{background:#fff}
  .no-print{display:none!important}
  .doc{box-shadow:none;margin:0;max-width:none;padding:0}
  a{color:#000;border:0}
  th{background:#eee!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .badge,.bar,.totals,.alt{-webkit-print-color-adjust:exact;print-color-adjust:exact}
  .pkt{page-break-inside:avoid}
}
"""
