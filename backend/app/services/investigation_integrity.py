"""Weighted Procurement Integrity Assessment.

Risk must never equal "number of indicators fired". A single-bidder pattern
across many tenders and one lone high-value tender should not score the same
just because each produced one indicator. This module computes an explainable,
weighted integrity score where every factor contributes differently.

Factors (each with a distinct weight):
    * single_bidder           — repeated lack of competition
    * buyer_concentration     — a buyer routing awards to few suppliers
    * supplier_concentration  — a supplier dependent on one buyer
    * award_timing            — awards implausibly soon after publication
    * bid/award_clustering    — many awards to one supplier in a short window
    * repeat_award            — same buyer→supplier pairing recurring
    * abnormal_value          — statistical value outliers
    * entity_relationships    — density of resolved counterparties
    * evidence_confidence     — how confident the underlying indicators are
    * source_reliability      — official Indian portals vs weak sources
    * document_quality        — availability of primary documents

Each factor yields a normalized strength (0-1); the score is the weighted blend
scaled to 0-100. The result is fully auditable: every factor reports its weight,
strength, point contribution, and a plain-language reason.
"""

from __future__ import annotations

from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_reasoning import IntegrityAssessment, RiskFactor, RiskLevel

# Indicator types grouped by the integrity factor they inform.
_FACTOR_INDICATORS: dict[str, tuple[str, ...]] = {
    "single_bidder": ("single_bidder", "high_value_direct_award"),
    "buyer_concentration": ("buyer_concentration",),
    "supplier_concentration": ("supplier_concentration",),
    "award_timing": ("suspicious_timing",),
    "award_clustering": ("award_clustering",),
    "repeat_award": ("repeat_supplier",),
    "abnormal_value": ("abnormal_value", "high_value"),
    "process_integrity": ("duplicate_description", "missing_award_data", "duplicate_descriptions"),
}

# Weights sum to 1.0 across all factors. Adverse-pattern factors dominate;
# evidence/source/document factors modulate confidence in those patterns.
_WEIGHTS: dict[str, float] = {
    "single_bidder": 0.16,
    "buyer_concentration": 0.13,
    "supplier_concentration": 0.11,
    "award_timing": 0.12,
    "award_clustering": 0.09,
    "repeat_award": 0.09,
    "abnormal_value": 0.09,
    "process_integrity": 0.05,
    "entity_relationships": 0.04,
    "evidence_confidence": 0.05,
    "source_reliability": 0.04,
    "document_quality": 0.03,
}

_LABELS: dict[str, str] = {
    "single_bidder": "Competition suppression (single bidder)",
    "buyer_concentration": "Buyer award concentration",
    "supplier_concentration": "Supplier single-buyer dependence",
    "award_timing": "Award timing anomalies",
    "award_clustering": "Award clustering",
    "repeat_award": "Repeat buyer–supplier awards",
    "abnormal_value": "Abnormal contract values",
    "process_integrity": "Process integrity gaps",
    "entity_relationships": "Entity relationship density",
    "evidence_confidence": "Evidence confidence",
    "source_reliability": "Source reliability",
    "document_quality": "Primary document availability",
}

# Official Indian procurement / oversight sources → higher reliability.
_RELIABLE_SOURCES = frozenset(
    {"gem", "cppp", "cag", "cvc", "datagovin", "nic",
     "eproc_rajasthan", "eproc_maharashtra", "eproc_kerala",
     "eproc_odisha", "eproc_westbengal", "eproc_karnataka"}
)


def _indicator_strength(pkg: InvestigationPackage, types: tuple[str, ...]) -> tuple[float, list[str], float]:
    """Aggregate strength (0-1) for a factor from its indicator types.

    Strength blends the strongest matching indicator's score with how many
    records corroborate it, so a pattern seen across many tenders outweighs a
    one-off. Returns (strength, matched_types, mean_confidence).
    """
    matched = [i for i in pkg.indicators if i.type in types]
    if not matched:
        return 0.0, [], 0.0
    top_score = max(i.score for i in matched) / 100.0
    # corroboration: distinct supporting tenders across these indicators
    tenders = {t for i in matched for t in i.related_tenders}
    corroboration = min(1.0, len(tenders) / 5.0)  # 5+ tenders => full corroboration
    strength = min(1.0, 0.7 * top_score + 0.3 * corroboration)
    mean_conf = sum(i.confidence for i in matched) / len(matched)
    return strength, sorted({i.type for i in matched}), mean_conf


def _entity_relationship_strength(pkg: InvestigationPackage) -> float:
    """More resolved counterparties + buyer/supplier edges => denser network."""
    companies = len(pkg.canonical_companies)
    buyers = len({r.tender.procuring_entity for r in pkg.records if r.tender.procuring_entity})
    return min(1.0, (companies + buyers) / 12.0)


def _source_reliability_strength(pkg: InvestigationPackage) -> float:
    """Share of records from reliable official sources (higher = more trustworthy)."""
    if not pkg.records:
        return 0.0
    reliable = sum(
        1 for r in pkg.records
        if any(r.tender.metadata.source_name.lower().startswith(s) for s in _RELIABLE_SOURCES)
    )
    return reliable / len(pkg.records)


def _document_quality_strength(pkg: InvestigationPackage) -> float:
    """Share of records carrying at least one primary document."""
    if not pkg.records:
        return 0.0
    with_docs = sum(1 for r in pkg.records if r.documents)
    return with_docs / len(pkg.records)


def _evidence_confidence_strength(pkg: InvestigationPackage) -> float:
    """Mean confidence across all fired indicators (0 if none)."""
    if not pkg.indicators:
        return 0.0
    return sum(i.confidence for i in pkg.indicators) / len(pkg.indicators)


def _band(score: int, has_records: bool) -> RiskLevel:
    if not has_records:
        return "insufficient"
    if score >= 75:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 32:
        return "medium"
    return "low"


def assess_integrity(pkg: InvestigationPackage) -> IntegrityAssessment:
    """Compute the weighted, explainable procurement integrity assessment."""
    if not pkg.records:
        return IntegrityAssessment(
            score=0, level="insufficient", confidence=0.0, factors=[],
            summary="No procurement records were retrieved, so no integrity assessment is possible.",
        )

    factors: list[RiskFactor] = []
    conf_signals: list[float] = []

    # Pattern factors derived from indicators.
    for key, types in _FACTOR_INDICATORS.items():
        strength, matched_types, mean_conf = _indicator_strength(pkg, types)
        if mean_conf:
            conf_signals.append(mean_conf)
        weight = _WEIGHTS[key]
        contribution = round(weight * strength * 100, 1)
        factors.append(
            RiskFactor(
                key=key,
                label=_LABELS[key],
                weight=weight,
                strength=round(strength, 2),
                contribution=contribution,
                detail=_factor_detail(key, strength, matched_types),
                supporting_indicator_types=matched_types,
            )
        )

    # Context factors derived from package structure/evidence.
    context = {
        "entity_relationships": _entity_relationship_strength(pkg),
        "evidence_confidence": _evidence_confidence_strength(pkg),
        "source_reliability": _source_reliability_strength(pkg),
        "document_quality": _document_quality_strength(pkg),
    }
    for key, strength in context.items():
        weight = _WEIGHTS[key]
        contribution = round(weight * strength * 100, 1)
        factors.append(
            RiskFactor(
                key=key,
                label=_LABELS[key],
                weight=weight,
                strength=round(strength, 2),
                contribution=contribution,
                detail=_factor_detail(key, strength, []),
            )
        )

    score = int(round(min(100.0, sum(f.contribution for f in factors))))
    level = _band(score, has_records=True)

    # Confidence in the assessment: driven by evidence confidence, source
    # reliability, and how much data we had to work with.
    data_conf = min(1.0, len(pkg.records) / 20.0)
    confidence = round(
        0.5 * (sum(conf_signals) / len(conf_signals) if conf_signals else 0.4)
        + 0.3 * context["source_reliability"]
        + 0.2 * data_conf,
        2,
    )

    return IntegrityAssessment(
        score=score,
        level=level,
        confidence=confidence,
        factors=sorted(factors, key=lambda f: f.contribution, reverse=True),
        summary=_summary(score, level, factors),
    )


def _factor_detail(key: str, strength: float, matched_types: list[str]) -> str:
    if strength <= 0:
        return f"No {_LABELS[key].lower()} signal detected in the retrieved records."
    band = "strong" if strength >= 0.66 else "moderate" if strength >= 0.33 else "weak"
    if matched_types:
        return (
            f"{band.capitalize()} {_LABELS[key].lower()} signal "
            f"(indicators: {', '.join(matched_types)})."
        )
    return f"{band.capitalize()} {_LABELS[key].lower()} contribution from package context."


def _summary(score: int, level: RiskLevel, factors: list[RiskFactor]) -> str:
    drivers = [f.label.lower() for f in sorted(factors, key=lambda f: f.contribution, reverse=True) if f.contribution > 0][:3]
    if not drivers:
        return (
            f"Weighted procurement integrity score {score}/100 ({level}); no adverse "
            "patterns dominated — the assessment reflects clean recorded activity."
        )
    return (
        f"Weighted procurement integrity score {score}/100 ({level}), driven chiefly by "
        f"{', '.join(drivers)}. The score is a weighted blend of distinct integrity "
        "factors, not a count of indicators."
    )
