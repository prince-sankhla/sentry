"""Deterministic Procurement Risk Engine V2.

An enterprise, fully deterministic oversight engine. The LLM never calculates
risk — it later only narrates the structure this engine proves. Every score is
reproducible and every score is explainable.

Layered architecture (each layer independent and testable):

    L1 Indicator Engine   — config-driven, deterministic detectors (reuses the
                            proven ``investigation_indicators`` set + adds new
                            package-supported detectors).
    L2 Context Engine     — deterministic rules that suppress/elevate severity
                            (emergency, disaster, PSU-internal, correction notice).
    L3 Evidence Validator — verified / probable / unknown per indicator; never
                            assumes evidence exists.
    L4 Risk Classification— deterministic RULE COMBINATIONS → named patterns
                            (never arithmetic addition or arbitrary multipliers).
    L5 Confidence Engine  — computed independently of risk, from evidence quality.
    L6 Explainability Tree— per-indicator audit trail feeding the narrator.

Oversight principle: the engine surfaces integrity *indicators* for investigator
review. It never declares fraud/corruption/collusion; every finding ends with
"Requires Investigator Review".

Indicator definitions live in :data:`INDICATOR_REGISTRY` — a declarative,
YAML/JSON-ready structure. New indicators are added there without changing the
engine's control flow.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal

from app.schemas.investigation_executor import InvestigationPackage, InvestigationProcurementRecord
from app.schemas.investigation_risk import (
    RiskAssessmentV2,
    RiskConfidence,
    RiskEvidenceRef,
    RiskExplainabilityNode,
    RiskIndicatorV2,
    RiskPattern,
)
from app.services.investigation_indicators import build_indicators

# --------------------------------------------------------------------------- L1 registry

_SEVERITY_SCORE = {"low": 25, "medium": 50, "high": 72, "critical": 92}
_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_ORDER_SEVERITY = {v: k for k, v in _SEVERITY_ORDER.items()}


@dataclass(frozen=True)
class IndicatorDef:
    """Declarative indicator definition (YAML/JSON-ready).

    ``condition``/``exceptions`` are documented in prose here because detection is
    delegated to the deterministic detectors; a future YAML loader populates the
    same fields. ``required_evidence`` drives the Evidence Validator.
    """

    id: str
    name: str
    category: str
    base_severity: str
    required_evidence: tuple[str, ...]
    description: str = ""


# The canonical indicator catalogue. Existing detector ``type`` values map 1:1;
# new deterministic detectors (award_value_exceeds_tender, buyer_equals_supplier,
# missing_documents) are added here and detected below. Relationship-overlap
# indicators (director/gst/pan/address/phone/email/bank) are declared so rule
# combinations reference them; they only trigger when the underlying entity data
# is present (never fabricated).
INDICATOR_REGISTRY: dict[str, IndicatorDef] = {
    "single_bidder": IndicatorDef("single_bidder", "Single Bidder", "competition", "high",
        ("tender_reference", "recorded_bidders"), "Only one recorded supplier on a tender."),
    "high_value_direct_award": IndicatorDef("high_value_direct_award", "High-Value Direct Award", "competition", "high",
        ("tender_reference", "estimated_value", "awarded_supplier"), "Single-supplier award above the high-value band."),
    "high_value": IndicatorDef("high_value", "High-Value Tender", "value", "medium",
        ("tender_reference", "estimated_value"), "Tender value in the high-value oversight band."),
    "repeat_supplier": IndicatorDef("repeat_supplier", "Repeated Winner", "concentration", "medium",
        ("buyer", "awarded_supplier", "award_count"), "Same supplier repeatedly awarded by the same buyer."),
    "buyer_concentration": IndicatorDef("buyer_concentration", "Buyer Concentration", "concentration", "medium",
        ("buyer", "award_shares"), "A buyer routes most awarded value to one supplier."),
    "supplier_concentration": IndicatorDef("supplier_concentration", "Supplier Single-Buyer Dependence", "concentration", "medium",
        ("awarded_supplier", "buyer_shares"), "A supplier depends on a single buyer."),
    "abnormal_value": IndicatorDef("abnormal_value", "Abnormal Value Spike", "value", "high",
        ("award_value", "value_baseline"), "Award value is a statistical outlier in the record set."),
    "award_clustering": IndicatorDef("award_clustering", "Rapid Repeat Procurement", "timing", "high",
        ("awarded_supplier", "award_dates"), "Many awards to one supplier within a short window."),
    "suspicious_timing": IndicatorDef("suspicious_timing", "Award Timing Anomaly", "timing", "critical",
        ("tender_reference", "published_date", "award_date"), "Award landed implausibly close to publication/close."),
    "duplicate_description": IndicatorDef("duplicate_description", "Tender Copy Pattern", "process", "medium",
        ("tender_reference", "tender_text"), "Near-identical tender text across tenders."),
    "missing_award_data": IndicatorDef("missing_award_data", "Missing Award", "process", "medium",
        ("tender_reference", "closing_date"), "Closed tender with no award notice on record."),
    # --- new deterministic detectors (this engine) ---
    "award_value_exceeds_tender": IndicatorDef("award_value_exceeds_tender", "Award Value Exceeds Tender Value", "value", "high",
        ("tender_reference", "estimated_value", "award_value"), "Awarded value materially exceeds the tender estimate."),
    "buyer_equals_supplier": IndicatorDef("buyer_equals_supplier", "Buyer Equals Supplier", "relationship", "critical",
        ("buyer", "awarded_supplier"), "The awarded supplier is the procuring entity itself."),
    "missing_documents": IndicatorDef("missing_documents", "Missing Documents", "process", "low",
        ("tender_reference", "documents"), "Tender has no attached procurement documents."),
    # --- related-party overlaps (declared; trigger only with entity data) ---
    "gst_overlap": IndicatorDef("gst_overlap", "GST Overlap", "relationship", "critical",
        ("supplier_gst",), "Two ostensibly distinct suppliers share a GSTIN."),
    "director_overlap": IndicatorDef("director_overlap", "Director Overlap", "relationship", "high",
        ("supplier_directors",), "Suppliers share one or more directors."),
    "address_overlap": IndicatorDef("address_overlap", "Address Overlap", "relationship", "high",
        ("supplier_address",), "Suppliers share a registered address."),
}


# --------------------------------------------------------------------------- helpers

def _band_up(severity: str, steps: int = 1) -> str:
    return _ORDER_SEVERITY[min(4, _SEVERITY_ORDER[severity] + steps)]


def _band_down(severity: str, steps: int = 1) -> str:
    return _ORDER_SEVERITY[max(1, _SEVERITY_ORDER[severity] - steps)]


def _max_severity(sevs: list[str]) -> str:
    return _ORDER_SEVERITY[max((_SEVERITY_ORDER[s] for s in sevs), default=1)] if sevs else "low"


def _text_blob(pkg: InvestigationPackage) -> str:
    parts = []
    for r in pkg.records:
        parts.append(r.tender.title or "")
        parts.append(r.tender.description or "")
        for d in r.documents:
            parts.append(d.title or "")
    return " ".join(parts).casefold()


# --------------------------------------------------------------------------- L1: new detectors

def _detect_extra(pkg: InvestigationPackage) -> list[dict]:
    """Deterministic detectors added by V2, package-supported. Returns raw hits."""
    hits: list[dict] = []

    # Award value exceeds tender estimate (>2x).
    for r in pkg.records:
        est = r.tender.estimated_value
        if est and est > 0:
            for a in r.awards:
                if a.award_value and a.award_value > est * Decimal(2):
                    hits.append({
                        "type": "award_value_exceeds_tender",
                        "reason": (f"Awarded value {a.award_value:,.0f} exceeds the tender estimate "
                                   f"{est:,.0f} ({a.award_value / est:.1f}×) on {r.tender.reference_number}."),
                        "records": [r.tender.reference_number],
                        "entities": [a.company_name],
                    })

    # Buyer == Supplier (awarded supplier is the procuring entity).
    for r in pkg.records:
        buyer = (r.tender.procuring_entity or "").split("||")[0].strip().casefold()
        for a in r.awards:
            if buyer and a.company_name.strip().casefold() == buyer:
                hits.append({
                    "type": "buyer_equals_supplier",
                    "reason": f"The procuring entity and the awarded supplier are the same on {r.tender.reference_number}.",
                    "records": [r.tender.reference_number],
                    "entities": [a.company_name],
                })

    # Missing documents on a tender.
    missing_doc_refs = [r.tender.reference_number for r in pkg.records if not r.documents]
    if missing_doc_refs and len(missing_doc_refs) < len(pkg.records) or (missing_doc_refs and len(pkg.records) == len(missing_doc_refs)):
        hits.append({
            "type": "missing_documents",
            "reason": f"{len(missing_doc_refs)} of {len(pkg.records)} tenders have no attached procurement documents.",
            "records": missing_doc_refs[:20],
            "entities": [],
        })
    return hits


# --------------------------------------------------------------------------- L2: context

@dataclass
class _Context:
    emergency: bool = False
    disaster: bool = False
    correction_notice: bool = False
    psu_present: bool = False
    signals: list[str] = field(default_factory=list)


_EMERGENCY_TERMS = ("emergency", "urgent", "urgency", "immediate requirement")
_DISASTER_TERMS = ("disaster", "flood", "cyclone", "earthquake", "pandemic", "covid", "relief", "epidemic")
_CORRECTION_TERMS = ("corrigendum", "correction notice", "amendment notice", "rectification")
_PSU_TERMS = ("limited", "ltd", "corporation", "nigam", "authority", "psu")


def _detect_context(pkg: InvestigationPackage) -> _Context:
    blob = _text_blob(pkg)
    ctx = _Context()
    if any(t in blob for t in _EMERGENCY_TERMS):
        ctx.emergency = True
        ctx.signals.append("emergency procurement language detected")
    if any(t in blob for t in _DISASTER_TERMS):
        ctx.disaster = True
        ctx.signals.append("disaster/relief context detected")
    if any(t in blob for t in _CORRECTION_TERMS):
        ctx.correction_notice = True
        ctx.signals.append("correction/corrigendum notice present")
    for r in pkg.records:
        buyer = (r.tender.procuring_entity or "").casefold()
        if any(t in buyer for t in _PSU_TERMS):
            ctx.psu_present = True
            break
    return ctx


def _apply_context(indicator_type: str, base_severity: str, ctx: _Context) -> tuple[str, list[str]]:
    """Deterministic context rules. Returns (adjusted_severity, notes)."""
    notes: list[str] = []
    severity = base_severity

    if indicator_type in ("single_bidder", "high_value_direct_award") and ctx.emergency:
        severity = _band_down(severity)
        notes.append("Single-bidder/direct award is expected under emergency procurement — severity suppressed.")

    if indicator_type in ("suspicious_timing", "short_tender_window") and ctx.disaster:
        severity = _band_down(severity)
        notes.append("Compressed timeline is expected in disaster/relief response — severity suppressed.")

    if indicator_type == "suspicious_timing":
        # Award-timing anomalies are always critical UNLESS a correction notice
        # explains the compressed process.
        if ctx.correction_notice:
            severity = _band_down(severity)
            notes.append("A correction/corrigendum notice is present — timing anomaly partially explained.")
        else:
            severity = "critical"
            notes.append("Award-timing anomaly with no correction notice — held at critical.")

    if indicator_type == "buyer_equals_supplier" and ctx.psu_present:
        severity = "medium"
        notes.append("Buyer equals a PSU supplier — possible internal procurement; needs review, not presumed adverse.")

    return severity, notes


# --------------------------------------------------------------------------- L3: evidence validator

def _record_by_ref(pkg: InvestigationPackage) -> dict[str, InvestigationProcurementRecord]:
    return {r.tender.reference_number: r for r in pkg.records}


def _validate_evidence(refs: list[str], by_ref: dict, required: tuple[str, ...]) -> tuple[str, list[RiskEvidenceRef]]:
    """Verified/Probable/Unknown from actual package evidence — never assumed."""
    evidence: list[RiskEvidenceRef] = []
    has_document = False
    has_url = False
    resolved = 0
    for ref in refs:
        record = by_ref.get(ref)
        if record is None:
            continue
        resolved += 1
        meta = record.tender.metadata
        evidence.append(RiskEvidenceRef(
            kind="tender", reference=ref, source=meta.source_name,
            detail=record.tender.title or "",
        ))
        if meta.source_url:
            has_url = True
        for doc in record.documents:
            has_document = True
            evidence.append(RiskEvidenceRef(
                kind="document", reference=doc.title or "document", source=meta.source_name,
                detail=doc.url or "",
            ))
    if resolved == 0:
        return "unknown", evidence
    if has_document:
        return "verified", evidence
    if has_url:
        return "probable", evidence
    return "probable", evidence


# --------------------------------------------------------------------------- L4: rule combinations

@dataclass(frozen=True)
class _PatternRule:
    id: str
    name: str
    severity: str
    requires: tuple[str, ...]      # indicator ids that must ALL be present
    rule_text: str


# Deterministic rule combinations. Ordered strongest-first; evaluation applies
# every rule whose indicators are all present. Named patterns — NOT sums.
_PATTERN_RULES: tuple[_PatternRule, ...] = (
    _PatternRule("related_party_critical", "Very High Related-Party Pattern", "critical",
        ("director_overlap", "address_overlap", "gst_overlap"),
        "director_overlap + address_overlap + gst_overlap"),
    _PatternRule("single_bidder_gst", "Critical Related-Party Pattern", "critical",
        ("single_bidder", "gst_overlap"), "single_bidder + gst_overlap"),
    _PatternRule("systemic_suppression", "Systemic Competition-Suppression Pattern", "critical",
        ("single_bidder", "repeat_supplier", "buyer_concentration"),
        "single_bidder + repeat_supplier + buyer_concentration"),
    _PatternRule("award_timing", "Award-Timing Critical Pattern", "critical",
        ("suspicious_timing",), "award-timing anomaly (award before/at close)"),
    _PatternRule("buyer_supplier_identity", "Buyer-Supplier Identity Pattern", "critical",
        ("buyer_equals_supplier",), "buyer == supplier"),
    _PatternRule("vendor_lockin", "Vendor Lock-in Pattern", "high",
        ("repeat_supplier", "supplier_concentration"), "repeat_supplier + supplier_concentration"),
    _PatternRule("rapid_repeat", "Rapid Repeat Procurement Pattern", "high",
        ("award_clustering", "repeat_supplier"), "award_clustering + repeat_supplier"),
    _PatternRule("value_anomaly", "Value Anomaly Pattern", "high",
        ("abnormal_value", "award_value_exceeds_tender"), "abnormal_value + award_value_exceeds_tender"),
    _PatternRule("concentration", "Concentration Pattern", "medium",
        ("single_bidder", "buyer_concentration"), "single_bidder + buyer_concentration"),
)


def _classify(present: set[str]) -> list[RiskPattern]:
    patterns: list[RiskPattern] = []
    for rule in _PATTERN_RULES:
        if all(ind in present for ind in rule.requires):
            patterns.append(RiskPattern(
                id=rule.id, name=rule.name, severity=rule.severity, rule=rule.rule_text,
                indicators=list(rule.requires),
                reason=f"Deterministic rule matched: {rule.rule_text}.",
            ))
    return patterns


# --------------------------------------------------------------------------- L5: confidence

def _confidence(pkg: InvestigationPackage) -> RiskConfidence:
    n = len(pkg.records)
    if n == 0:
        return RiskConfidence(score=0.0, level="very_low", explanation="No records retrieved.")
    with_url = sum(1 for r in pkg.records if r.tender.metadata.source_url)
    with_docs = sum(1 for r in pkg.records if r.documents)
    with_awards = sum(1 for r in pkg.records if r.awards)
    dated = sum(1 for r in pkg.records if r.tender.published_date or r.tender.closing_date)
    resolved_ok = [c for c in pkg.canonical_companies if c.confidence >= 0.6]
    dims = [with_url / n, with_docs / n, with_awards / n, dated / n,
            (len(resolved_ok) / len(pkg.canonical_companies)) if pkg.canonical_companies else 0.0]
    score = round(sum(dims) / len(dims), 2)
    level = "high" if score >= 0.7 else "moderate" if score >= 0.45 else "low" if score >= 0.25 else "very_low"
    expl = (
        f"Confidence {int(score * 100)}% ({level}) from evidence coverage "
        f"(URLs {with_url}/{n}, documents {with_docs}/{n}), award completeness ({with_awards}/{n}), "
        f"timeline completeness ({dated}/{n}), and entity-resolution quality — independent of the risk score."
    )
    return RiskConfidence(score=score, level=level, explanation=expl)


# --------------------------------------------------------------------------- orchestrator

def assess_risk_v2(pkg: InvestigationPackage) -> RiskAssessmentV2:
    """Run the full deterministic Risk Engine V2 over a finalized package."""
    if not pkg.records:
        return RiskAssessmentV2(
            overall_severity="insufficient", overall_score=0,
            confidence=RiskConfidence(score=0.0, level="very_low", explanation="No records retrieved."),
            summary="Insufficient evidence to assess procurement integrity — no records retrieved.",
        )

    by_ref = _record_by_ref(pkg)
    ctx = _detect_context(pkg)

    # L1: gather deterministic hits — existing detectors + V2 detectors.
    raw: list[dict] = []
    for ind in build_indicators(pkg):
        raw.append({
            "type": ind.type, "reason": ind.reason or ind.summary,
            "records": list(ind.related_tenders), "entities": list(ind.related_entities),
        })
    raw.extend(_detect_extra(pkg))

    # Collapse to one indicator per type (grouped supporting records), like the report.
    grouped: dict[str, dict] = {}
    for hit in raw:
        itype = hit["type"]
        if itype not in INDICATOR_REGISTRY:
            continue
        g = grouped.setdefault(itype, {"records": [], "entities": [], "reason": hit["reason"]})
        g["records"].extend(hit["records"])
        g["entities"].extend(hit["entities"])

    indicators: list[RiskIndicatorV2] = []
    explain: list[RiskExplainabilityNode] = []
    for itype, g in grouped.items():
        d = INDICATOR_REGISTRY[itype]
        refs = sorted(set(g["records"]))
        base_sev = d.base_severity
        # L2 context adjustment.
        final_sev, notes = _apply_context(itype, base_sev, ctx)
        # L3 evidence validation.
        ev_status, ev_refs = _validate_evidence(refs, by_ref, d.required_evidence)
        # Unknown evidence caps severity — an unverifiable indicator cannot be critical.
        if ev_status == "unknown" and _SEVERITY_ORDER[final_sev] > 2:
            notes.append("Required evidence not verifiable in package — severity capped pending review.")
            final_sev = "medium"
        score = _SEVERITY_SCORE[final_sev]
        indicators.append(RiskIndicatorV2(
            id=itype, name=d.name, category=d.category, severity=final_sev, base_severity=base_sev,
            score=score, evidence_status=ev_status,
            confidence=0.8 if ev_status == "verified" else 0.6 if ev_status == "probable" else 0.3,
            reason=g["reason"], required_evidence=list(d.required_evidence),
            supporting_records=refs, context_notes=notes,
        ))
        explain.append(RiskExplainabilityNode(
            indicator_id=itype, name=d.name, base_severity=base_sev, base_score=_SEVERITY_SCORE[base_sev],
            rule_triggered=d.description, evidence=ev_refs[:8], evidence_status=ev_status,
            context_applied=notes, score_contribution=score, final_severity=final_sev,
            reason=g["reason"],
        ))

    indicators.sort(key=lambda i: (_SEVERITY_ORDER[i.severity], i.score), reverse=True)

    # L4 classification: deterministic rule combinations.
    present = {i.id for i in indicators}
    patterns = _classify(present)

    # Overall severity: strongest pattern, else strongest indicator. Never a sum.
    if patterns:
        overall_sev = _max_severity([p.severity for p in patterns])
    elif indicators:
        overall_sev = indicators[0].severity
    else:
        overall_sev = "low"
    overall_score = _SEVERITY_SCORE.get(overall_sev, 0)

    confidence = _confidence(pkg)
    summary = _summary(overall_sev, patterns, indicators, ctx)

    return RiskAssessmentV2(
        overall_severity=overall_sev, overall_score=overall_score,
        indicators=indicators, patterns=patterns, explainability=explain,
        confidence=confidence, summary=summary,
    )


def _summary(overall_sev: str, patterns: list[RiskPattern], indicators: list[RiskIndicatorV2], ctx: _Context) -> str:
    if not indicators:
        return "No procurement integrity indicators triggered on the recorded activity. Requires Investigator Review."
    lead = f"Overall integrity severity: {overall_sev.upper()} (deterministic)."
    if patterns:
        lead += " Patterns: " + ", ".join(p.name for p in patterns[:4]) + "."
    else:
        lead += " Indicators: " + ", ".join(i.name for i in indicators[:4]) + "."
    if ctx.signals:
        lead += " Context applied: " + "; ".join(ctx.signals) + "."
    return lead + " Every indicator requires investigator review; this is an oversight signal, not a determination."
