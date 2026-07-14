"""Explainable procurement risk engine — SENTRY's flagship capability.

Every indicator derived here is *explainable and evidence-backed*: it carries a
risk score, a calibrated confidence, a plain-language reason, the human-readable
evidence lines, and the full supporting set it was computed from — supporting
tenders, buyers, suppliers, documents, and a dated timeline. Nothing is a black
box; an analyst can audit exactly which records produced each score.

Operates purely on the collected :class:`InvestigationPackage` records so the
signals travel with the package to the frontend. It never invents facts — a
detector that cannot ground a signal in real records emits nothing.

Detectors (spec-aligned):
  * single_bidder            — only one recorded supplier on a tender
  * high_value_direct_award  — single-bidder award above the high-value band
  * repeat_supplier          — same supplier repeatedly awarded by same buyer
  * buyer_concentration      — a buyer routes most awards to one supplier
  * supplier_concentration   — a supplier depends on a single buyer
  * abnormal_value           — contract value is a statistical outlier
  * award_clustering         — many awards to a supplier in a short window
  * suspicious_timing        — award landed implausibly soon after publication
  * duplicate_description    — near-identical tender text across tenders
  * missing_award_data       — closed tenders with no recorded award
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.schemas.investigation_executor import (
    InvestigationPackage,
    InvestigationProcurementIndicator,
    InvestigationProcurementRecord,
    RiskTimelineEvent,
)

_CONCENTRATION_HIGH = Decimal("0.50")
_HIGH_VALUE = Decimal("100000000")  # 10 crore INR
_CLUSTER_WINDOW_DAYS = 30
_SUSPICIOUS_AWARD_DAYS = 3
_MIN_ABNORMAL_SAMPLE = 5

# Missing-award as-of-time gate (auditor C3). Awards are published after a tender
# closes, following evaluation/approval; an *absence* of an award is only an
# anomaly once the expected award-publication window has elapsed. This grace
# period is a conservative default heuristic for Indian public procurement and is
# configurable. Below it, "no award" means "award pending", not "award withheld".
_AWARD_GRACE_DAYS = 45


def _as_of_date(pkg: InvestigationPackage) -> date | None:
    """Reproducible investigation as-of date = the latest data-retrieval timestamp.

    Uses the immutable ``retrieved_at`` stored on each record (raw-data field), NOT
    wall-clock ``today`` — so the time gate is deterministic and the Evidence Packet
    reproduces exactly. Returns ``None`` when no record carries a retrieval time.
    """
    stamps: list[date] = []
    for record in pkg.records:
        ts = record.tender.metadata.retrieved_at
        if ts is not None:
            stamps.append(ts.date() if hasattr(ts, "date") else ts)
    return max(stamps) if stamps else None


def award_timing_status(pkg: InvestigationPackage, grace_days: int = _AWARD_GRACE_DAYS) -> dict:
    """Deterministic as-of assessment of award-lifecycle timing (auditor C3).

    Partitions closed, award-less tenders into ``overdue`` (past the grace window —
    a genuine gap), ``pending`` (closed recently — award not yet due), and
    ``indeterminate`` (elapsed time cannot be established). "Missing Award" is only
    ``active`` when at least three tenders are overdue. Shared by the detector and
    the Evidence Packet so the packet can explain WHY the typology is or isn't active.
    """
    as_of = _as_of_date(pkg)
    closed_no_award = [
        r for r in pkg.records if r.tender.closing_date is not None and not r.awards
    ]
    overdue: list[InvestigationProcurementRecord] = []
    pending: list[InvestigationProcurementRecord] = []
    indeterminate: list[InvestigationProcurementRecord] = []
    elapsed: list[int] = []
    for record in closed_no_award:
        if as_of is None:
            indeterminate.append(record)
            continue
        days = (as_of - record.tender.closing_date).days
        elapsed.append(days)
        (overdue if days >= grace_days else pending).append(record)
    return {
        "as_of": as_of,
        "grace_days": grace_days,
        "closed_no_award": closed_no_award,
        "overdue": overdue,
        "pending": pending,
        "indeterminate": indeterminate,
        "median_elapsed": (sorted(elapsed)[len(elapsed) // 2] if elapsed else None),
        "active": len(overdue) >= 3,
    }


def build_indicators(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    indicators: list[InvestigationProcurementIndicator] = []
    indicators.extend(_single_bidder(pkg))
    indicators.extend(_repeat_supplier(pkg))
    indicators.extend(_buyer_concentration(pkg))
    indicators.extend(_supplier_concentration(pkg))
    indicators.extend(_high_value(pkg))
    indicators.extend(_abnormal_value(pkg))
    indicators.extend(_award_clustering(pkg))
    indicators.extend(_suspicious_timing(pkg))
    indicators.extend(_duplicate_descriptions(pkg))
    indicators.extend(_missing_award(pkg))
    return sorted(indicators, key=lambda indicator: (indicator.score, indicator.confidence), reverse=True)


# --------------------------------------------------------------------------- helpers


def _tender_timeline(record: InvestigationProcurementRecord) -> list[RiskTimelineEvent]:
    """Dated events for a single tender: publication, closing, and awards."""
    events: list[RiskTimelineEvent] = []
    tender = record.tender
    if tender.published_date is not None:
        events.append(
            RiskTimelineEvent(
                label=f"Tender published: {tender.reference_number}",
                event_date=tender.published_date,
                related_tender=tender.reference_number,
            )
        )
    if tender.closing_date is not None:
        events.append(
            RiskTimelineEvent(
                label=f"Tender closed: {tender.reference_number}",
                event_date=tender.closing_date,
                related_tender=tender.reference_number,
            )
        )
    for award in record.awards:
        if award.award_date is not None:
            events.append(
                RiskTimelineEvent(
                    label=f"Award to {award.company_name}",
                    event_date=award.award_date,
                    related_tender=tender.reference_number,
                    related_entity=award.company_name,
                )
            )
    return events


def _sorted_timeline(events: list[RiskTimelineEvent]) -> list[RiskTimelineEvent]:
    return sorted(events, key=lambda event: event.event_date)


# --------------------------------------------------------------------------- document taxonomy

# Strict evidence taxonomy shared by the packet, analyst report, evidence engine,
# and risk engine so all four classify documents identically. A portal "source
# notice" is the tender listing entry itself — NOT a primary procurement document
# (NIT, BoQ, corrigendum, tender PDF, award letter). Only primary documents count
# toward "document availability"; source notices are counted, and reported, separately.
_SOURCE_NOTICE_DOC_TYPES = {"source_notice", "source notice", ""}


def is_source_notice(doc_type: str | None) -> bool:
    return (doc_type or "").strip().casefold() in _SOURCE_NOTICE_DOC_TYPES


def is_primary_document(doc_type: str | None) -> bool:
    """True for a primary procurement document; False for a portal source notice."""
    return not is_source_notice(doc_type)


def record_has_primary_document(record: InvestigationProcurementRecord) -> bool:
    return any(is_primary_document(d.document_type) for d in record.documents)


def _document_titles(records: list[InvestigationProcurementRecord]) -> list[str]:
    titles: list[str] = []
    for record in records:
        for document in record.documents:
            if document.title and document.title not in titles:
                titles.append(document.title)
    return titles[:25]


# --------------------------------------------------------------------------- detectors


def _single_bidder(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    out = []
    for record in pkg.records:
        suppliers = {award.company_name for award in record.awards}
        if len(suppliers) == 1 and record.awards:
            supplier = next(iter(suppliers))
            buyer = record.tender.procuring_entity or "Unknown"
            out.append(
                InvestigationProcurementIndicator(
                    type="single_bidder",
                    severity="high",
                    title="Single Bidder Award",
                    summary=f"Tender {record.tender.reference_number} was awarded with only one recorded supplier.",
                    score=80,
                    confidence=0.75 if record.tender.closing_date else 0.6,
                    reason=(
                        f"Only {supplier} is recorded against tender {record.tender.reference_number}, "
                        f"indicating an absence of competition for this award by {buyer}."
                    ),
                    evidence=[
                        "Recorded suppliers: 1",
                        f"Supplier: {supplier}",
                        f"Buyer: {buyer}",
                    ],
                    related_tenders=[record.tender.reference_number],
                    related_entities=[supplier],
                    supporting_buyers=[buyer] if record.tender.procuring_entity else [],
                    supporting_suppliers=[supplier],
                    supporting_documents=_document_titles([record]),
                    timeline=_sorted_timeline(_tender_timeline(record)),
                )
            )
    return out


def _repeat_supplier(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    pairs: dict[tuple[str, str], list[InvestigationProcurementRecord]] = defaultdict(list)
    for record in pkg.records:
        buyer = (record.tender.procuring_entity or "unknown").strip()
        for award in record.awards:
            pairs[(buyer.casefold(), award.company_name)].append(record)
    out = []
    for (buyer_key, supplier), records in pairs.items():
        unique_records = {r.tender.reference_number: r for r in records}
        refs = sorted(unique_records)
        if len(refs) >= 2:
            buyer_display = next(
                (r.tender.procuring_entity for r in unique_records.values() if r.tender.procuring_entity),
                buyer_key,
            )
            score = min(100, 55 + (len(refs) - 1) * 12)
            timeline: list[RiskTimelineEvent] = []
            for record in unique_records.values():
                timeline.extend(
                    e for e in _tender_timeline(record) if e.related_entity == supplier
                )
            out.append(
                InvestigationProcurementIndicator(
                    type="repeat_supplier",
                    severity="high" if len(refs) >= 3 else "medium",
                    title="Repeat Supplier",
                    summary=f"{supplier} won {len(refs)} tenders from the same buyer.",
                    score=score,
                    confidence=min(0.9, 0.55 + (len(refs) - 2) * 0.1),
                    reason=(
                        f"{supplier} was awarded {len(refs)} distinct tenders by {buyer_display}. "
                        "Repeated awards to the same supplier from one buyer can indicate a "
                        "preferential relationship that warrants review."
                    ),
                    evidence=[f"Awards from buyer: {len(refs)}", f"Supplier: {supplier}", f"Buyer: {buyer_display}"],
                    related_tenders=refs,
                    related_entities=[supplier],
                    supporting_buyers=[buyer_display],
                    supporting_suppliers=[supplier],
                    supporting_documents=_document_titles(list(unique_records.values())),
                    timeline=_sorted_timeline(timeline),
                )
            )
    return out


def _buyer_concentration(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    buyer_awards: dict[str, list[tuple[str, InvestigationProcurementRecord]]] = defaultdict(list)
    for record in pkg.records:
        buyer = (record.tender.procuring_entity or "").strip()
        if not buyer:
            continue
        for award in record.awards:
            buyer_awards[buyer].append((award.company_name, record))
    out = []
    for buyer, awards in buyer_awards.items():
        if len(awards) < 3:
            continue
        by_supplier: dict[str, int] = defaultdict(int)
        for supplier, _ in awards:
            by_supplier[supplier] += 1
        top_supplier, top_count = max(by_supplier.items(), key=lambda item: item[1])
        share = Decimal(top_count) / Decimal(len(awards))
        if share >= _CONCENTRATION_HIGH:
            records = [record for _, record in awards]
            out.append(
                InvestigationProcurementIndicator(
                    type="buyer_concentration",
                    severity="high" if share >= Decimal("0.7") else "medium",
                    title="Buyer Concentration",
                    summary=f"{buyer} directed {share:.0%} of recorded awards to {top_supplier}.",
                    score=min(100, int(share * 100)),
                    confidence=min(0.9, 0.5 + (len(awards) - 3) * 0.05),
                    reason=(
                        f"{buyer} concentrated {share:.0%} of its {len(awards)} recorded awards on a single "
                        f"supplier, {top_supplier}. High buyer concentration reduces competitive tension."
                    ),
                    evidence=[
                        f"Buyer awards: {len(awards)}",
                        f"Top supplier share: {share:.0%}",
                        f"Top supplier: {top_supplier}",
                    ],
                    related_tenders=sorted({record.tender.reference_number for record in records}),
                    related_entities=[buyer, top_supplier],
                    supporting_buyers=[buyer],
                    supporting_suppliers=sorted(by_supplier),
                    supporting_documents=_document_titles(records),
                    timeline=_sorted_timeline(
                        [e for record in records for e in _tender_timeline(record) if e.related_entity == top_supplier]
                    ),
                )
            )
    return out


def _supplier_concentration(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    supplier_buyers: dict[str, set[str]] = defaultdict(set)
    supplier_records: dict[str, list[InvestigationProcurementRecord]] = defaultdict(list)
    for record in pkg.records:
        buyer = (record.tender.procuring_entity or "unknown").strip()
        for award in record.awards:
            supplier_buyers[award.company_name].add(buyer.casefold())
            supplier_records[award.company_name].append(record)
    out = []
    for supplier, buyers in supplier_buyers.items():
        records = {r.tender.reference_number: r for r in supplier_records[supplier]}
        if len(records) >= 3 and len(buyers) == 1:
            buyer_display = next(
                (r.tender.procuring_entity for r in records.values() if r.tender.procuring_entity), "a single buyer"
            )
            out.append(
                InvestigationProcurementIndicator(
                    type="supplier_concentration",
                    severity="medium",
                    title="Supplier Single-Buyer Dependence",
                    summary=f"{supplier} won {len(records)} tenders all from a single buyer.",
                    score=min(100, 50 + len(records) * 8),
                    confidence=min(0.85, 0.5 + (len(records) - 3) * 0.07),
                    reason=(
                        f"All {len(records)} of {supplier}'s recorded wins come from {buyer_display}. "
                        "A supplier dependent on one buyer can signal a captive procurement relationship."
                    ),
                    evidence=[f"Tenders won: {len(records)}", "Distinct buyers: 1"],
                    related_tenders=sorted(records),
                    related_entities=[supplier],
                    supporting_buyers=[buyer_display],
                    supporting_suppliers=[supplier],
                    supporting_documents=_document_titles(list(records.values())),
                    timeline=_sorted_timeline(
                        [e for r in records.values() for e in _tender_timeline(r) if e.related_entity == supplier]
                    ),
                )
            )
    return out


def _high_value(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    out = []
    for record in pkg.records:
        value = record.tender.estimated_value
        if value is None or value < _HIGH_VALUE:
            continue
        suppliers = {award.company_name for award in record.awards}
        direct = len(suppliers) == 1 and bool(record.awards)
        buyer = record.tender.procuring_entity or "Unknown"
        out.append(
            InvestigationProcurementIndicator(
                type="high_value_direct_award" if direct else "high_value",
                severity="high" if direct else "medium",
                title="High-Value Direct Award" if direct else "High-Value Tender",
                summary=(
                    f"Tender {record.tender.reference_number} ({value:,.0f} {record.tender.currency}) "
                    + ("was awarded to a single supplier." if direct else "is a high-value procurement.")
                ),
                score=78 if direct else 60,
                confidence=0.7 if direct else 0.6,
                reason=(
                    f"Tender {record.tender.reference_number} carries an estimated value of "
                    f"{value:,.0f} {record.tender.currency}"
                    + (
                        f", awarded to a single supplier ({next(iter(suppliers))}). High-value awards without "
                        "competition carry elevated procurement risk."
                        if direct
                        else ", placing it in the high-value band that mandates additional oversight."
                    )
                ),
                evidence=[f"Estimated value: {value:,.0f} {record.tender.currency}"]
                + ([f"Recorded suppliers: 1 ({next(iter(suppliers))})"] if direct else []),
                related_tenders=[record.tender.reference_number],
                related_entities=[record.tender.procuring_entity] if record.tender.procuring_entity else [],
                supporting_buyers=[buyer] if record.tender.procuring_entity else [],
                supporting_suppliers=sorted(suppliers),
                supporting_documents=_document_titles([record]),
                timeline=_sorted_timeline(_tender_timeline(record)),
            )
        )
    return out


def _abnormal_value(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    """Flag award values that are statistical outliers within the package.

    Uses a robust median + MAD (median absolute deviation) test so a single
    extreme value cannot mask the rest. Requires a minimum sample so the
    baseline is meaningful — otherwise emits nothing rather than guess.
    """
    valued: list[tuple[Decimal, InvestigationProcurementRecord, str]] = []
    for record in pkg.records:
        for award in record.awards:
            if award.award_value is not None and award.award_value > 0:
                valued.append((award.award_value, record, award.company_name))
    if len(valued) < _MIN_ABNORMAL_SAMPLE:
        return []

    values = sorted(v for v, _, _ in valued)
    median = _median(values)
    if median <= 0:
        return []
    deviations = sorted(abs(v - median) for v in values)
    mad = _median(deviations)

    out = []
    for value, record, supplier in valued:
        if mad > 0:
            # Modified z-score; 3.5 is the conventional outlier threshold.
            modified_z = (Decimal("0.6745") * (value - median)) / mad
        else:
            # MAD collapses to 0 when most award values are identical. Fall back
            # to a median-ratio test so a lone extreme value is still caught, and
            # express it on the same z-scale so scoring/messaging stay consistent.
            ratio = value / median
            modified_z = Decimal("3.5") * ratio if ratio >= 3 else Decimal("0")
        if modified_z >= Decimal("3.5"):
            buyer = record.tender.procuring_entity or "Unknown"
            out.append(
                InvestigationProcurementIndicator(
                    type="abnormal_value",
                    severity="high" if modified_z >= Decimal("6") else "medium",
                    title="Abnormal Contract Value",
                    summary=(
                        f"Award to {supplier} on {record.tender.reference_number} "
                        f"({value:,.0f} {record.tender.currency}) is a statistical outlier."
                    ),
                    score=min(100, 60 + int(modified_z)),
                    confidence=min(0.85, 0.5 + float(modified_z) / 20),
                    reason=(
                        f"The award value {value:,.0f} {record.tender.currency} is {modified_z:.1f} robust "
                        f"deviations above the median award value ({median:,.0f}) across "
                        f"{len(valued)} awards reviewed — an abnormal contract value."
                    ),
                    evidence=[
                        f"Award value: {value:,.0f} {record.tender.currency}",
                        f"Median award value: {median:,.0f}",
                        f"Modified z-score: {modified_z:.1f}",
                        f"Sample size: {len(valued)} awards",
                    ],
                    related_tenders=[record.tender.reference_number],
                    related_entities=[supplier],
                    supporting_buyers=[buyer] if record.tender.procuring_entity else [],
                    supporting_suppliers=[supplier],
                    supporting_documents=_document_titles([record]),
                    timeline=_sorted_timeline(_tender_timeline(record)),
                )
            )
    return out


def _award_clustering(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    """Repeated awards to one supplier inside a short window (temporal clustering)."""
    supplier_dates: dict[str, list[tuple[date, InvestigationProcurementRecord]]] = defaultdict(list)
    for record in pkg.records:
        for award in record.awards:
            if award.award_date is not None:
                supplier_dates[award.company_name].append((award.award_date, record))
    out = []
    for supplier, dated in supplier_dates.items():
        if len(dated) < 3:
            continue
        dated.sort(key=lambda item: item[0])
        window = timedelta(days=_CLUSTER_WINDOW_DAYS)
        # Sliding window: largest count of awards within any N-day span.
        best_cluster: list[tuple[date, InvestigationProcurementRecord]] = []
        start = 0
        for end in range(len(dated)):
            while dated[end][0] - dated[start][0] > window:
                start += 1
            if end - start + 1 > len(best_cluster):
                best_cluster = dated[start : end + 1]
        if len(best_cluster) >= 3:
            records = [record for _, record in best_cluster]
            span_start, span_end = best_cluster[0][0], best_cluster[-1][0]
            buyers = sorted({r.tender.procuring_entity for r in records if r.tender.procuring_entity})
            out.append(
                InvestigationProcurementIndicator(
                    type="award_clustering",
                    severity="high" if len(best_cluster) >= 4 else "medium",
                    title="Award Clustering in Short Period",
                    summary=(
                        f"{supplier} received {len(best_cluster)} awards within "
                        f"{(span_end - span_start).days} days."
                    ),
                    score=min(100, 60 + (len(best_cluster) - 3) * 10),
                    confidence=min(0.85, 0.55 + (len(best_cluster) - 3) * 0.08),
                    reason=(
                        f"{supplier} was awarded {len(best_cluster)} tenders between "
                        f"{span_start.isoformat()} and {span_end.isoformat()} "
                        f"({(span_end - span_start).days} days) — an unusually rapid award cadence."
                    ),
                    evidence=[
                        f"Awards in window: {len(best_cluster)}",
                        f"Window: {span_start.isoformat()} → {span_end.isoformat()}",
                        f"Span (days): {(span_end - span_start).days}",
                    ],
                    related_tenders=sorted({r.tender.reference_number for r in records}),
                    related_entities=[supplier],
                    supporting_buyers=buyers,
                    supporting_suppliers=[supplier],
                    supporting_documents=_document_titles(records),
                    timeline=_sorted_timeline(
                        [e for r in records for e in _tender_timeline(r) if e.related_entity == supplier]
                    ),
                )
            )
    return out


def _suspicious_timing(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    """Award landing implausibly soon after publication (compressed process)."""
    out = []
    for record in pkg.records:
        published = record.tender.published_date
        if published is None:
            continue
        for award in record.awards:
            if award.award_date is None:
                continue
            gap = (award.award_date - published).days
            if 0 <= gap <= _SUSPICIOUS_AWARD_DAYS:
                buyer = record.tender.procuring_entity or "Unknown"
                out.append(
                    InvestigationProcurementIndicator(
                        type="suspicious_timing",
                        severity="high" if gap <= 1 else "medium",
                        title="Suspicious Procurement Timing",
                        summary=(
                            f"Tender {record.tender.reference_number} was awarded to {award.company_name} "
                            f"{gap} day(s) after publication."
                        ),
                        score=min(100, 82 - gap * 6),
                        confidence=0.7 if gap <= 1 else 0.6,
                        reason=(
                            f"Only {gap} day(s) separated publication ({published.isoformat()}) and award "
                            f"({award.award_date.isoformat()}) for tender {record.tender.reference_number} — "
                            "too short for a competitive bidding window."
                        ),
                        evidence=[
                            f"Published: {published.isoformat()}",
                            f"Awarded: {award.award_date.isoformat()}",
                            f"Gap (days): {gap}",
                        ],
                        related_tenders=[record.tender.reference_number],
                        related_entities=[award.company_name],
                        supporting_buyers=[buyer] if record.tender.procuring_entity else [],
                        supporting_suppliers=[award.company_name],
                        supporting_documents=_document_titles([record]),
                        timeline=_sorted_timeline(_tender_timeline(record)),
                    )
                )
    return out


def _duplicate_descriptions(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    """Near-identical tender text across distinct tenders (copy-paste specs)."""
    buckets: dict[str, list[InvestigationProcurementRecord]] = defaultdict(list)
    for record in pkg.records:
        fingerprint = _text_fingerprint(record.tender.description or record.tender.title)
        if fingerprint:
            buckets[fingerprint].append(record)
    out = []
    for records in buckets.values():
        distinct = {r.tender.reference_number: r for r in records}
        if len(distinct) >= 2:
            recs = list(distinct.values())
            buyers = sorted({r.tender.procuring_entity for r in recs if r.tender.procuring_entity})
            suppliers = sorted({a.company_name for r in recs for a in r.awards})
            out.append(
                InvestigationProcurementIndicator(
                    type="duplicate_description",
                    severity="medium",
                    title="Duplicate Tender Descriptions",
                    summary=f"{len(distinct)} tenders share near-identical descriptions/specifications.",
                    score=min(100, 50 + (len(distinct) - 2) * 10),
                    confidence=min(0.8, 0.5 + (len(distinct) - 2) * 0.1),
                    reason=(
                        f"{len(distinct)} distinct tenders share the same normalized description text. "
                        "Reused specifications across tenders can indicate tailored or recycled requirements."
                    ),
                    evidence=[f"Tenders sharing text: {len(distinct)}"]
                    + [f"Tender: {ref}" for ref in sorted(distinct)][:6],
                    related_tenders=sorted(distinct),
                    related_entities=suppliers,
                    supporting_buyers=buyers,
                    supporting_suppliers=suppliers,
                    supporting_documents=_document_titles(recs),
                    timeline=_sorted_timeline([e for r in recs for e in _tender_timeline(r)]),
                )
            )
    return out


def _missing_award(pkg: InvestigationPackage) -> list[InvestigationProcurementIndicator]:
    # As-of-time gate (auditor C3): only tenders that closed BEYOND the expected
    # award-publication window count as a genuine missing-award gap. Tenders that
    # closed recently are "award pending", not "award withheld", and must not fire.
    status = award_timing_status(pkg)
    overdue = status["overdue"]
    if len(overdue) < 3:
        return []
    grace, as_of = status["grace_days"], status["as_of"]
    buyers = sorted({r.tender.procuring_entity for r in overdue if r.tender.procuring_entity})
    return [
        InvestigationProcurementIndicator(
            type="missing_award_data",
            severity="low",
            title="Award Data Gap",
            summary=f"{len(overdue)} tenders closed over {grace} days ago with no recorded award — transparency gap.",
            score=30,
            confidence=0.5,
            reason=(
                f"{len(overdue)} tenders closed more than {grace} days before the data snapshot "
                f"({as_of}) with no recorded award — an award-transparency gap beyond the expected "
                "award-publication window (competition/transparency gap in the available records)."
            ),
            evidence=[
                f"Tenders overdue for an award (> {grace} days since close): {len(overdue)}",
                f"As-of date (data snapshot): {as_of}",
            ],
            related_tenders=[record.tender.reference_number for record in overdue][:25],
            supporting_buyers=buyers,
            supporting_documents=_document_titles(overdue),
            timeline=_sorted_timeline([e for r in overdue for e in _tender_timeline(r)]),
        )
    ]


# --------------------------------------------------------------------------- math/text utils


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / Decimal("2")


def _text_fingerprint(text: str | None) -> str:
    """Normalize tender text to a comparable fingerprint (lowercased alnum tokens).

    Short/empty text yields an empty fingerprint so trivial titles never collide.
    """
    if not text:
        return ""
    tokens = re.findall(r"[a-z0-9]+", text.casefold())
    if len(tokens) < 5:
        return ""
    return " ".join(tokens)
