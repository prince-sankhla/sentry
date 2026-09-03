from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from statistics import median
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Award, Document, Tender
from app.schemas.buyer_kundali import (
    BuyerDataQuality,
    BuyerDistributionRow,
    BuyerKundaliResponse,
    BuyerProfile,
    BuyerSignal,
    BuyerSubmissionWindow,
    BuyerSupplierRow,
    BuyerTimelinePoint,
    BuyerValueBenchmark,
)
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES


def build_buyer_kundali(db: Session, buyer: str) -> BuyerKundaliResponse | None:
    requested = buyer.strip()
    if not requested:
        return None
    buyer_key = requested.casefold()

    tenders = db.scalars(
        select(Tender)
        .where(
            Tender.procuring_entity.is_not(None),
            Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES),
        )
        .options(joinedload(Tender.awards).joinedload(Award.company))
        .order_by(Tender.published_date.asc().nullslast(), Tender.created_at.asc(), Tender.id.asc())
    ).unique().all()
    matching = [t for t in tenders if (t.procuring_entity or "").strip().casefold() == buyer_key]
    if not matching:
        return None

    tender_ids = {t.id for t in matching}
    awards = [a for t in matching for a in t.awards if a.company is not None]
    awarded_tenders = {a.tender_id for a in awards}
    tender_values = [t.estimated_value for t in matching if t.estimated_value is not None]
    tender_currency = _single_currency([t.currency for t in matching if t.currency])

    supplier_rows = _supplier_relationships(awards)
    supplier_concentration = [
        BuyerDistributionRow(
            dimension="Supplier",
            name=row.supplier_name,
            count=row.award_count,
            share=row.award_share,
            value=row.award_value,
            rank=index,
            population_count=len(awards),
        )
        for index, row in enumerate(supplier_rows[:10], start=1)
    ]

    category_distribution = _tender_distribution(matching, "category", "Category")
    geography_distribution = _tender_distribution(matching, "geography", "Geography")
    method_distribution = _tender_distribution(matching, "procurement_method", "Method")

    value_benchmark = _value_benchmark(tender_values, tender_currency)
    submission_window = _submission_window(matching)
    timeline = _timeline(matching)
    award_estimate = _award_estimate_distribution(matching)
    signals = _build_signals(
        matching,
        supplier_rows,
        method_distribution,
        submission_window,
        award_estimate,
    )

    source_urls = sum(1 for t in matching if t.source_url)
    with_method = sum(1 for t in matching if t.procurement_method)
    with_category = sum(1 for t in matching if t.category)
    with_geography = sum(1 for t in matching if t.geography)
    with_deadline = sum(1 for t in matching if t.closing_date)
    with_award_value = sum(1 for a in awards if a.award_value is not None)

    document_count = 0
    corrigendum_count = 0
    if tender_ids:
        documents = db.scalars(select(Document).where(Document.tender_id.in_(tender_ids))).all()
        document_count = len(documents)
        corrigendum_count = sum(1 for d in documents if _is_corrigendum(d.document_type, d.title))

    dates = [d for t in matching for d in [t.published_date] if d]
    first_date = min(dates) if dates else None
    latest_date = max(dates) if dates else None

    metrics = [
        {"label": "Tenders indexed", "value": str(len(matching))},
        {"label": "Awards recorded", "value": str(len(awards))},
        {"label": "Award rate", "value": _pct(len(awarded_tenders), len(matching))},
        {"label": "Suppliers awarded", "value": str(len(supplier_rows))},
        {"label": "Total tender value", "value": _money(sum(tender_values, Decimal("0")), tender_currency)},
        {"label": "Average tender value", "value": _money(value_benchmark.median or Decimal("0"), tender_currency)},
        {"label": "Top supplier share", "value": _pct(supplier_rows[0].award_share * 100 if supplier_rows else Decimal("0"), Decimal("100"))},
        {"label": "Repeat suppliers", "value": str(sum(1 for row in supplier_rows if row.award_count >= 2))},
    ]

    data_quality = BuyerDataQuality(
        tender_records=len(matching),
        awarded_tenders=len(awarded_tenders),
        records_with_method=with_method,
        records_with_category=with_category,
        records_with_geography=with_geography,
        records_with_deadline=with_deadline,
        records_with_award_value=with_award_value,
        records_with_source_url=source_urls,
        bidder_level_status="insufficient_data",
        cancellation_status="not_indexed",
        corrigendum_status="available" if document_count else "insufficient_data",
        notes=[
            "Buyer identity is derived from the canonical procuring_entity text currently stored on Indian tender records.",
            "Bidder-level participation is not inferred from awards; the current Indian corpus is predominantly tender/award-centric.",
            f"Indexed tender documents: {document_count}; detected corrigendum/amendment documents: {corrigendum_count}.",
        ],
    )

    limitations = [
        "Buyer history reflects records indexed in the current Indian procurement corpus; absence of a record is not evidence that no procurement occurred.",
        "Bidder distribution, withdrawal patterns, and bid-price behaviour remain insufficient-data without bidder-level Indian source records.",
        "Cancellation/re-tender frequency is not calculated because a canonical cancellation field is not currently stored on Tender.",
        "Concentration and award-rate metrics are descriptive context, not proof of preferential treatment or misconduct.",
    ]

    return BuyerKundaliResponse(
        profile=BuyerProfile(
            name=requested,
            normalized_name=buyer_key,
            tender_count=len(matching),
            awarded_tender_count=len(awarded_tenders),
            first_tender_date=first_date.isoformat() if first_date else None,
            latest_tender_date=latest_date.isoformat() if latest_date else None,
        ),
        metrics=metrics,
        supplier_concentration=supplier_concentration,
        category_distribution=category_distribution,
        geography_distribution=geography_distribution,
        method_distribution=method_distribution,
        supplier_relationships=supplier_rows[:20],
        value_benchmark=value_benchmark,
        submission_window=submission_window,
        timeline=timeline,
        award_estimate_distribution=award_estimate,
        signals=signals,
        data_quality=data_quality,
        limitations=limitations,
        generated_at=datetime.utcnow(),
    )


def _supplier_relationships(awards: list[Award]) -> list[BuyerSupplierRow]:
    grouped: dict[UUID, list[Award]] = defaultdict(list)
    for award in awards:
        grouped[award.company_id].append(award)
    total = len(awards)
    rows: list[BuyerSupplierRow] = []
    for company_id, items in grouped.items():
        company = items[0].company
        value = sum((a.award_value for a in items if a.award_value is not None), Decimal("0"))
        latest = max((a.award_date for a in items if a.award_date), default=None)
        rows.append(
            BuyerSupplierRow(
                supplier_id=str(company_id),
                supplier_name=company.name if company else "Unknown supplier",
                award_count=len(items),
                award_share=Decimal(len(items)) / Decimal(total) if total else Decimal("0"),
                award_value=value,
                latest_award_date=latest.isoformat() if latest else None,
            )
        )
    return sorted(rows, key=lambda row: (row.award_count, row.award_value), reverse=True)


def _tender_distribution(tenders: list[Tender], attribute: str, dimension: str) -> list[BuyerDistributionRow]:
    grouped: dict[str, list[Tender]] = defaultdict(list)
    unknown: list[Tender] = []
    for tender in tenders:
        value = getattr(tender, attribute, None)
        if not value:
            unknown.append(tender)
        else:
            grouped[str(value).strip()].append(tender)
    if unknown:
        grouped["Unknown / not stored"] = unknown
    total = len(tenders)
    rows: list[BuyerDistributionRow] = []
    for name, items in grouped.items():
        value = sum((t.estimated_value for t in items if t.estimated_value is not None), Decimal("0"))
        rows.append(
            BuyerDistributionRow(
                dimension=dimension,
                name=name,
                count=len(items),
                share=Decimal(len(items)) / Decimal(total) if total else Decimal("0"),
                value=value,
                rank=0,
                population_count=total,
            )
        )
    rows.sort(key=lambda row: (row.count, row.value), reverse=True)
    for index, row in enumerate(rows, start=1):
        row.rank = index
    return rows[:10]


def _value_benchmark(values: list[Decimal], currency: str | None) -> BuyerValueBenchmark:
    ordered = sorted(values)
    if not ordered:
        return BuyerValueBenchmark(sample_size=0, minimum=None, p25=None, median=None, p75=None, maximum=None, currency=currency, method="No tender values available")
    return BuyerValueBenchmark(
        sample_size=len(ordered), minimum=ordered[0], p25=_quantile(ordered, 0.25), median=Decimal(str(median(ordered))), p75=_quantile(ordered, 0.75), maximum=ordered[-1], currency=currency, method="Nearest-rank interpolation over recorded tender estimated values",
    )


def _submission_window(tenders: list[Tender]) -> BuyerSubmissionWindow:
    windows: list[float] = []
    unknown = 0
    for tender in tenders:
        if tender.published_date and tender.closing_date:
            windows.append(float((tender.closing_date - tender.published_date).days))
        else:
            unknown += 1
    return BuyerSubmissionWindow(
        sample_size=len(windows), minimum_days=min(windows) if windows else None, median_days=median(windows) if windows else None, p75_days=_quantile_float(windows, 0.75) if windows else None, maximum_days=max(windows) if windows else None, unknown_count=unknown,
    )


def _award_estimate_distribution(tenders: list[Tender]) -> BuyerDistributionRow | None:
    ratios: list[Decimal] = []
    for tender in tenders:
        tender_awards = [a for a in tender.awards if a.award_value is not None]
        if not tender.estimated_value or not tender_awards:
            continue
        for award in tender_awards:
            ratios.append(award.award_value / tender.estimated_value)
    if not ratios:
        return None
    avg = sum(ratios, Decimal("0")) / Decimal(len(ratios))
    return BuyerDistributionRow(dimension="Award/estimate ratio", name="Recorded awarded tenders", count=len(ratios), share=Decimal("1"), value=avg, rank=1, population_count=len(ratios))


def _timeline(tenders: list[Tender]) -> list[BuyerTimelinePoint]:
    grouped: dict[str, list[Tender]] = defaultdict(list)
    for tender in tenders:
        if tender.published_date:
            grouped[tender.published_date.strftime("%Y-%m")].append(tender)
    return [
        BuyerTimelinePoint(
            period=period,
            tenders=len(items),
            awards=sum(1 for t in items if t.awards),
            tender_value=sum((t.estimated_value for t in items if t.estimated_value is not None), Decimal("0")),
            award_value=sum((a.award_value for t in items for a in t.awards if a.award_value is not None), Decimal("0")),
        )
        for period, items in sorted(grouped.items())
    ]


def _build_signals(
    tenders: list[Tender], supplier_rows: list[BuyerSupplierRow], method_rows: list[BuyerDistributionRow], window: BuyerSubmissionWindow, award_estimate: BuyerDistributionRow | None,
) -> list[BuyerSignal]:
    signals: list[BuyerSignal] = []
    repeat_supplier_count = sum(1 for row in supplier_rows if row.award_count >= 2)
    if repeat_supplier_count:
        signals.append(BuyerSignal(type="repeat_suppliers", severity="informational", title="Repeat supplier relationships", summary=f"{repeat_supplier_count} suppliers have two or more recorded awards from this buyer.", evidence=[f"Repeat suppliers: {repeat_supplier_count}"], confidence="high", review_required=False))
    if supplier_rows and supplier_rows[0].award_share >= Decimal("0.50") and supplier_rows[0].award_count >= 2:
        signals.append(BuyerSignal(type="supplier_concentration", severity="medium", title="Supplier concentration review lead", summary=f"{supplier_rows[0].supplier_name} accounts for {supplier_rows[0].award_share:.0%} of recorded awards.", evidence=[f"Top supplier: {supplier_rows[0].supplier_name}", f"Share of awards: {supplier_rows[0].award_share:.0%}"], confidence="high", review_required=True))
    if method_rows and method_rows[0].share >= Decimal("0.75") and len(tenders) >= 4:
        signals.append(BuyerSignal(type="method_concentration", severity="low", title="Procurement method concentration", summary=f"{method_rows[0].share:.0%} of indexed tenders use {method_rows[0].name}.", evidence=[f"Method: {method_rows[0].name}", f"Share: {method_rows[0].share:.0%}"], confidence="high", review_required=True))
    if window.sample_size >= 4 and window.median_days is not None and window.median_days < 7:
        signals.append(BuyerSignal(type="short_submission_window_context", severity="medium", title="Short submission-window pattern", summary=f"The median publication-to-closing window is {window.median_days:.1f} days across {window.sample_size} dated tenders.", evidence=[f"Median window: {window.median_days:.1f} days", f"Known windows: {window.sample_size}"], confidence="moderate", review_required=True))
    if award_estimate:
        ratio = award_estimate.value
        if ratio > Decimal("1.10"):
            signals.append(BuyerSignal(type="award_estimate_context", severity="medium", title="Award-to-estimate review lead", summary=f"Recorded awards average {ratio:.0%} of their tender estimates in the indexed sample.", evidence=[f"Average award/estimate ratio: {ratio:.2f}", f"Awarded records with both values: {award_estimate.count}"], confidence="moderate", review_required=True))
    return signals


def _single_currency(values: list[str]) -> str | None:
    distinct = {v.upper() for v in values if v}
    return next(iter(distinct)) if len(distinct) == 1 else None


def _quantile(values: list[Decimal], q: float) -> Decimal:
    if len(values) == 1:
        return values[0]
    position = Decimal(str(q)) * Decimal(len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - Decimal(lower)
    return values[lower] + (values[upper] - values[lower]) * fraction


def _quantile_float(values: list[float], q: float) -> float:
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _pct(numerator: int | Decimal, denominator: int | Decimal) -> str:
    if Decimal(str(denominator)) == 0:
        return "Not available"
    return f"{(Decimal(str(numerator)) / Decimal(str(denominator))) * Decimal('100'):.0f}%"


def _money(value: Decimal, currency: str | None) -> str:
    return f"{value:.2f} {currency}" if currency else f"{value:.2f}"


def _is_corrigendum(document_type: str | None, title: str | None) -> bool:
    text = f"{document_type or ''} {title or ''}".casefold()
    return any(term in text for term in ("corrigendum", "amendment", "addendum", "corrigenda"))
