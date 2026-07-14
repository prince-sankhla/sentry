"""Structured analyst-report builder — grounded, deterministic projections.

The LLM narrates; the backend proves. Every section here is computed purely from
the finalized :class:`InvestigationPackage` (records, awards, entities,
indicators, timeline, evidence, grounding) — no invented entities, values,
dates, or relationships. This is what turns the package into a production
analyst report: buyer / supplier / award / timeline analysis, procurement
patterns, automatically-detected contradictions, missing-evidence gaps, and a
confidence figure derived from measurable investigation quality (never a bare
number).

Grounding contract: a detector that cannot ground a statement in the package
emits nothing rather than guess.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from app.schemas.investigation_executor import InvestigationPackage, InvestigationProcurementRecord
from app.schemas.investigation_reasoning import (
    AnalystReport,
    AwardAnalysis,
    BuyerInsight,
    ConfidenceAssessment,
    ConfidenceDimension,
    Contradiction,
    GroundingReport,
    ProcurementPattern,
    SupplierInsight,
    TimelineAnalysis,
)

# Official Indian procurement / oversight sources → higher reliability. Mirrors
# the integrity engine so the two agree on what counts as a primary source.
_RELIABLE_SOURCES = frozenset(
    {"gem", "cppp", "cag", "cvc", "datagovin", "nic",
     "eproc_rajasthan", "eproc_maharashtra", "eproc_kerala",
     "eproc_odisha", "eproc_westbengal", "eproc_karnataka"}
)

_SUSPICIOUS_AWARD_DAYS = 3


def _fmt(value: Decimal | None, currency: str | None) -> str | None:
    if value is None:
        return None
    return f"{value:,.0f} {currency}".strip() if currency else f"{value:,.0f}"


def _buyer(record: InvestigationProcurementRecord) -> str:
    return (record.tender.procuring_entity or "").strip()


def _reliable(record: InvestigationProcurementRecord) -> bool:
    src = (record.tender.metadata.source_name or "").lower()
    return any(src.startswith(s) for s in _RELIABLE_SOURCES)


# --------------------------------------------------------------------------- buyers

def _buyer_analysis(pkg: InvestigationPackage) -> list[BuyerInsight]:
    by_buyer: dict[str, list[InvestigationProcurementRecord]] = defaultdict(list)
    for record in pkg.records:
        buyer = _buyer(record)
        if buyer:
            by_buyer[buyer].append(record)

    insights: list[BuyerInsight] = []
    for buyer, records in by_buyer.items():
        supplier_values: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
        award_count = 0
        total = Decimal(0)
        currency: str | None = None
        for record in records:
            for award in record.awards:
                award_count += 1
                if award.award_value is not None:
                    supplier_values[award.company_name] += award.award_value
                    total += award.award_value
                    currency = currency or award.currency
        top = sorted(supplier_values.items(), key=lambda kv: kv[1], reverse=True)
        top_suppliers = [name for name, _ in top[:3]]
        concentration = None
        if total > 0 and top:
            concentration = int(top[0][1] / total * 100)
        note = ""
        if concentration is not None and concentration >= 60:
            note = f"{top[0][0]} received {concentration}% of this buyer's awarded value — elevated concentration."
        insights.append(
            BuyerInsight(
                name=buyer,
                tender_count=len(records),
                award_count=award_count,
                total_award_value=_fmt(total if total > 0 else None, currency),
                currency=currency,
                top_suppliers=top_suppliers,
                concentration_pct=concentration,
                note=note,
            )
        )
    insights.sort(key=lambda b: (b.tender_count, b.award_count), reverse=True)
    return insights[:10]


# --------------------------------------------------------------------------- suppliers

def _supplier_analysis(pkg: InvestigationPackage) -> list[SupplierInsight]:
    buyers_by_supplier: dict[str, set[str]] = defaultdict(set)
    value_by_supplier: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
    count_by_supplier: dict[str, int] = defaultdict(int)
    currency_by_supplier: dict[str, str | None] = {}
    for record in pkg.records:
        buyer = _buyer(record)
        for award in record.awards:
            name = award.company_name.strip()
            if not name:
                continue
            count_by_supplier[name] += 1
            if buyer:
                buyers_by_supplier[name].add(buyer)
            if award.award_value is not None:
                value_by_supplier[name] += award.award_value
                currency_by_supplier.setdefault(name, award.currency)

    insights: list[SupplierInsight] = []
    for name, count in count_by_supplier.items():
        buyers = sorted(buyers_by_supplier.get(name, set()))
        single_buyer = len(buyers) == 1 and count >= 2
        note = ""
        if single_buyer:
            note = f"All {count} awards to {name} come from a single buyer ({buyers[0]}) — single-buyer dependence."
        total = value_by_supplier.get(name, Decimal(0))
        insights.append(
            SupplierInsight(
                name=name,
                award_count=count,
                total_award_value=_fmt(total if total > 0 else None, currency_by_supplier.get(name)),
                currency=currency_by_supplier.get(name),
                buyers=buyers[:5],
                single_buyer_dependence=single_buyer,
                note=note,
            )
        )
    insights.sort(key=lambda s: (s.award_count, s.single_buyer_dependence), reverse=True)
    return insights[:10]


# --------------------------------------------------------------------------- awards

def _award_analysis(pkg: InvestigationPackage) -> AwardAnalysis | None:
    awards = [(a, r) for r in pkg.records for a in r.awards]
    if not awards:
        return None
    valued = [(a, r) for a, r in awards if a.award_value is not None]
    total = sum((a.award_value for a, _ in valued), Decimal(0))
    currency = valued[0][0].currency if valued else None
    largest = max(valued, key=lambda ar: ar[0].award_value, default=None)
    note = ""
    if valued and largest is not None:
        note = (
            f"{len(awards)} award(s) recorded; {len(valued)} carry a value totalling "
            f"{_fmt(total, currency)}. Largest: {_fmt(largest[0].award_value, currency)} to "
            f"{largest[0].company_name}."
        )
    elif awards:
        note = f"{len(awards)} award(s) recorded but none carry a value — award values are missing."
    return AwardAnalysis(
        total_awards=len(awards),
        valued_awards=len(valued),
        total_value=_fmt(total if valued else None, currency),
        currency=currency,
        largest_award_value=_fmt(largest[0].award_value, currency) if largest else None,
        largest_award_supplier=largest[0].company_name if largest else None,
        largest_award_tender=largest[1].tender.reference_number if largest else None,
        note=note,
    )


# --------------------------------------------------------------------------- timeline

def _as_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def _timeline_analysis(pkg: InvestigationPackage) -> TimelineAnalysis | None:
    events = pkg.timeline
    fast_awards = 0
    for record in pkg.records:
        pub = record.tender.published_date
        if pub is None:
            continue
        for award in record.awards:
            if award.award_date is not None and 0 <= (award.award_date - pub).days <= _SUSPICIOUS_AWARD_DAYS:
                fast_awards += 1
    if not events:
        note = "No dated events are available — timeline analysis is not possible."
        return TimelineAnalysis(event_count=0, fast_awards=fast_awards, note=note)
    dates = sorted(_as_date(e.event_date) for e in events)
    span = (dates[-1] - dates[0]).days
    note = (
        f"{len(events)} dated event(s) spanning {span} day(s) "
        f"({dates[0].isoformat()} → {dates[-1].isoformat()})."
    )
    if fast_awards:
        note += f" {fast_awards} award(s) landed within {_SUSPICIOUS_AWARD_DAYS} days of publication."
    return TimelineAnalysis(
        event_count=len(events),
        first_event=dates[0].isoformat(),
        last_event=dates[-1].isoformat(),
        span_days=span,
        fast_awards=fast_awards,
        note=note,
    )


# --------------------------------------------------------------------------- patterns

def _procurement_patterns(pkg: InvestigationPackage) -> list[ProcurementPattern]:
    """Surface indicator-derived patterns as report-level pattern statements."""
    by_type: dict[str, list[str]] = defaultdict(list)
    label: dict[str, str] = {}
    for ind in pkg.indicators:
        by_type[ind.type].extend(ind.related_tenders)
        label.setdefault(ind.type, ind.title)
    patterns: list[ProcurementPattern] = []
    for itype, refs in by_type.items():
        uniq = sorted(set(refs))
        patterns.append(
            ProcurementPattern(
                pattern=label.get(itype, itype.replace("_", " ").title()),
                detail=f"Observed across {len(uniq)} tender(s) in the record set.",
                supporting_tenders=uniq[:10],
            )
        )
    patterns.sort(key=lambda p: len(p.supporting_tenders), reverse=True)
    return patterns


# --------------------------------------------------------------------------- contradictions

def _contradictions(pkg: InvestigationPackage) -> list[Contradiction]:
    out: list[Contradiction] = []

    # 1. Date inconsistencies: award before publication, or closing before publication.
    for record in pkg.records:
        t = record.tender
        if t.published_date and t.closing_date and t.closing_date < t.published_date:
            out.append(Contradiction(
                type="date_inconsistency", severity="medium",
                summary=f"Tender {t.reference_number}: closing date precedes publication date.",
                detail=f"Published {t.published_date.isoformat()}, closes {t.closing_date.isoformat()}.",
                related_tenders=[t.reference_number],
            ))
        for a in record.awards:
            if t.published_date and a.award_date and a.award_date < t.published_date:
                out.append(Contradiction(
                    type="date_inconsistency", severity="high",
                    summary=f"Tender {t.reference_number}: award dated before the tender was published.",
                    detail=f"Published {t.published_date.isoformat()}, awarded {a.award_date.isoformat()} to {a.company_name}.",
                    related_tenders=[t.reference_number], related_entities=[a.company_name],
                ))

    # 2. Missing award records: a closed tender (closing date in the past) with no awards.
    today = _package_reference_date(pkg)
    for record in pkg.records:
        t = record.tender
        if not record.awards and t.closing_date and today is not None and t.closing_date < today:
            out.append(Contradiction(
                type="missing_award", severity="medium",
                summary=f"Tender {t.reference_number}: closed with no award on record.",
                detail=f"Closed {t.closing_date.isoformat()} but no award notice is present — an award data gap.",
                related_tenders=[t.reference_number],
            ))

    # 3. Award value exceeds the tender estimate materially (>2x).
    for record in pkg.records:
        t = record.tender
        if t.estimated_value and t.estimated_value > 0:
            for a in record.awards:
                if a.award_value and a.award_value > t.estimated_value * 2:
                    out.append(Contradiction(
                        type="value_inconsistency", severity="medium",
                        summary=f"Tender {t.reference_number}: award value materially exceeds the estimate.",
                        detail=(f"Estimated {t.estimated_value:,.0f}, awarded {a.award_value:,.0f} "
                                f"({a.award_value / t.estimated_value:.1f}×) to {a.company_name}."),
                        related_tenders=[t.reference_number], related_entities=[a.company_name],
                    ))

    # 4. Award without a company name (award value but no supplier).
    for record in pkg.records:
        for a in record.awards:
            if a.award_value is not None and not a.company_name.strip():
                out.append(Contradiction(
                    type="award_without_company", severity="high",
                    summary=f"Tender {record.tender.reference_number}: award has a value but no recorded supplier.",
                    related_tenders=[record.tender.reference_number],
                ))

    # 5. Conflicting suppliers: one tender awarded to multiple distinct suppliers.
    for record in pkg.records:
        suppliers = sorted({a.company_name.strip() for a in record.awards if a.company_name.strip()})
        if len(suppliers) > 1:
            out.append(Contradiction(
                type="conflicting_supplier", severity="low",
                summary=f"Tender {record.tender.reference_number}: multiple distinct awarded suppliers.",
                detail="Suppliers: " + ", ".join(suppliers[:5]) + " — verify whether this is a split/multi-lot award.",
                related_tenders=[record.tender.reference_number], related_entities=suppliers[:5],
            ))

    # 6. Duplicate contracts: same buyer + title + value under different references.
    seen: dict[tuple, str] = {}
    for record in pkg.records:
        t = record.tender
        key = ((t.procuring_entity or "").casefold().strip(), (t.title or "").casefold().strip(),
               str(t.estimated_value) if t.estimated_value is not None else "")
        if all(key) and key in seen and seen[key] != t.reference_number:
            out.append(Contradiction(
                type="duplicate_contract", severity="medium",
                summary=f"Possible duplicate tender: {t.reference_number} mirrors {seen[key]}.",
                detail="Same buyer, title, and estimated value under two references — verify for duplication.",
                related_tenders=sorted({t.reference_number, seen[key]}),
            ))
        elif all(key):
            seen[key] = t.reference_number

    # Strongest first, capped.
    order = {"high": 3, "medium": 2, "low": 1}
    out.sort(key=lambda c: order.get(c.severity, 0), reverse=True)
    return out[:25]


def _package_reference_date(pkg: InvestigationPackage) -> date | None:
    """Latest known date in the package — a data-derived 'now' (no wall clock).

    Using a date drawn from the evidence keeps the detector deterministic and
    reproducible (Date.now-style calls are avoided), while still letting us judge
    whether a tender's closing date is in the past relative to the dataset.
    """
    candidates: list[date] = []
    for record in pkg.records:
        t = record.tender
        for d in (t.published_date, t.closing_date):
            if d is not None:
                candidates.append(d)
        for a in record.awards:
            if a.award_date is not None:
                candidates.append(a.award_date)
    return max(candidates) if candidates else None


# --------------------------------------------------------------------------- missing evidence

def _missing_evidence(pkg: InvestigationPackage) -> list[str]:
    gaps: list[str] = []
    n = len(pkg.records)
    if n == 0:
        return ["Insufficient evidence is currently available to support this conclusion."]

    from app.services.investigation_indicators import record_has_primary_document

    no_docs = sum(1 for r in pkg.records if not record_has_primary_document(r))
    no_awards = sum(1 for r in pkg.records if not r.awards)
    awards = [a for r in pkg.records for a in r.awards]
    unvalued_awards = sum(1 for a in awards if a.award_value is None)
    no_pub = sum(1 for r in pkg.records if r.tender.published_date is None)
    no_close = sum(1 for r in pkg.records if r.tender.closing_date is None)
    no_url = sum(1 for r in pkg.records if not r.tender.metadata.source_url)
    unresolved = [c for c in pkg.canonical_companies if c.confidence < 0.6]

    if no_docs:
        gaps.append(f"{no_docs} of {n} tenders have no primary procurement document (only a portal source notice) "
                    "— request the NIT, BoQ, corrigendum, tender PDF or award letter.")
    if no_awards:
        gaps.append(f"{no_awards} of {n} tenders have no award notice on record — request the missing award notices.")
    if awards and unvalued_awards:
        gaps.append(f"{unvalued_awards} of {len(awards)} awards have no recorded value — obtain the awarded contract values.")
    if no_pub:
        gaps.append(f"{no_pub} of {n} tenders lack a publication date — retrieve the original notice dates.")
    if no_close:
        gaps.append(f"{no_close} of {n} tenders lack a closing date — retrieve the bid submission deadlines.")
    if no_url:
        gaps.append(f"{no_url} of {n} records have no source URL — confirm the originating portal reference.")
    if unresolved:
        gaps.append(f"{len(unresolved)} resolved entity(ies) have low match confidence — confirm identity via registration/CIN.")
    return gaps


# --------------------------------------------------------------------------- confidence

_CONFIDENCE_WEIGHTS = {
    "evidence_coverage": 0.16,
    "source_reliability": 0.16,
    "independent_corroboration": 0.14,
    "document_availability": 0.12,
    "entity_resolution_quality": 0.12,
    "award_completeness": 0.12,
    "timeline_completeness": 0.10,
    "cross_source_consistency": 0.08,
}


def _confidence_assessment(
    pkg: InvestigationPackage, grounding: GroundingReport, contradictions: list[Contradiction]
) -> ConfidenceAssessment:
    n = len(pkg.records)
    if n == 0:
        return ConfidenceAssessment(
            score=0.0, level="very_low", dimensions=[],
            explanation="No procurement records were retrieved, so confidence is not assessable.",
        )

    from app.services.investigation_indicators import record_has_primary_document

    awards = [a for r in pkg.records for a in r.awards]
    with_url = sum(1 for r in pkg.records if r.tender.metadata.source_url)
    # Primary procurement documents only — portal source notices are not counted.
    with_docs = sum(1 for r in pkg.records if record_has_primary_document(r))
    reliable = sum(1 for r in pkg.records if _reliable(r))
    distinct_sources = len({r.tender.metadata.source_name for r in pkg.records})
    with_awards = sum(1 for r in pkg.records if r.awards)
    valued_awards = sum(1 for a in awards if a.award_value is not None)
    dated = sum(1 for r in pkg.records if r.tender.published_date or r.tender.closing_date)
    resolved_ok = [c for c in pkg.canonical_companies if c.confidence >= 0.6]

    dims: list[ConfidenceDimension] = [
        ConfidenceDimension(
            key="evidence_coverage", label="Evidence coverage", score=with_url / n,
            detail=f"{with_url}/{n} records have a verifiable source URL.",
        ),
        ConfidenceDimension(
            key="source_reliability", label="Source reliability", score=reliable / n,
            detail=f"{reliable}/{n} records come from official Indian procurement/oversight sources.",
        ),
        ConfidenceDimension(
            key="independent_corroboration", label="Independent corroboration",
            score=min(1.0, (distinct_sources - 1) / 2) if n > 1 else 0.0,
            detail=f"{distinct_sources} distinct source(s) contribute to the record set.",
        ),
        ConfidenceDimension(
            key="document_availability", label="Primary-document availability", score=with_docs / n,
            detail=(f"{with_docs}/{n} records carry a primary procurement document "
                    "(NIT/BoQ/corrigendum/tender PDF/award letter); portal source notices are not counted."),
        ),
        ConfidenceDimension(
            key="entity_resolution_quality", label="Entity-resolution quality",
            score=(len(resolved_ok) / len(pkg.canonical_companies)) if pkg.canonical_companies else 0.0,
            detail=(f"{len(resolved_ok)}/{len(pkg.canonical_companies)} entities resolved with high confidence."
                    if pkg.canonical_companies else "No canonical entities were resolved."),
        ),
        ConfidenceDimension(
            key="award_completeness", label="Award completeness",
            score=(with_awards / n) * (valued_awards / len(awards) if awards else 0.0),
            detail=f"{with_awards}/{n} tenders have awards; {valued_awards}/{len(awards) or 0} awards carry a value.",
        ),
        ConfidenceDimension(
            key="timeline_completeness", label="Timeline completeness", score=dated / n,
            detail=f"{dated}/{n} records carry at least one date.",
        ),
        ConfidenceDimension(
            key="cross_source_consistency", label="Cross-source consistency",
            score=max(0.0, 1.0 - len(contradictions) / max(n, 5)),
            detail=(f"{len(contradictions)} contradiction(s) detected across {n} records."
                    if contradictions else "No contradictions detected across the record set."),
        ),
    ]

    score = round(sum(_CONFIDENCE_WEIGHTS[d.key] * d.score for d in dims), 2)
    level = "high" if score >= 0.7 else "moderate" if score >= 0.45 else "low" if score >= 0.25 else "very_low"

    strongest = max(dims, key=lambda d: d.score)
    weakest = min(dims, key=lambda d: d.score)
    explanation = (
        f"Confidence is {level.replace('_', ' ')} ({int(score * 100)}%), a weighted blend of eight "
        f"measurable quality signals. Strongest: {strongest.label.lower()} ({int(strongest.score * 100)}%). "
        f"Weakest: {weakest.label.lower()} ({int(weakest.score * 100)}%). "
        + ("Detected contradictions lower cross-source consistency. " if contradictions else "")
        + "Confidence rises as document coverage, official-source share, corroboration and award completeness improve."
    )
    return ConfidenceAssessment(score=score, level=level, dimensions=dims, explanation=explanation)


# --------------------------------------------------------------------------- assembler

def build_analyst_report(pkg: InvestigationPackage, grounding: GroundingReport) -> AnalystReport:
    """Assemble the full grounded, structured analyst report from the package."""
    contradictions = _contradictions(pkg)
    return AnalystReport(
        procurement_patterns=_procurement_patterns(pkg),
        buyer_analysis=_buyer_analysis(pkg),
        supplier_analysis=_supplier_analysis(pkg),
        award_analysis=_award_analysis(pkg),
        timeline_analysis=_timeline_analysis(pkg),
        contradictions=contradictions,
        missing_evidence=_missing_evidence(pkg),
        confidence_assessment=_confidence_assessment(pkg, grounding, contradictions),
    )
