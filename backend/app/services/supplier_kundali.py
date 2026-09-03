from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from statistics import median
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Award, Company, Tender
from app.schemas.supplier_kundali import (
    SupplierConcentration,
    SupplierDataQuality,
    SupplierKundaliMetric,
    SupplierKundaliProfile,
    SupplierKundaliResponse,
    SupplierSignal,
    SupplierTimelinePoint,
    SupplierValueBenchmark,
)
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES


def build_supplier_kundali(db: Session, company_id: UUID) -> SupplierKundaliResponse | None:
    company = db.get(Company, company_id)
    if company is None:
        return None

    awards = db.execute(
        select(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(
            Award.company_id == company_id,
            Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES),
        )
        .options(joinedload(Award.tender))
        .order_by(Award.award_date.asc().nullslast(), Award.created_at.asc(), Award.id.asc())
    ).unique().scalars().all()

    records = [award for award in awards if award.tender is not None]
    distinct_tenders = {award.tender_id for award in records}
    values = [award.award_value for award in records if award.award_value is not None]
    currencies = {award.currency for award in records if award.currency}
    currency = next(iter(currencies)) if len(currencies) == 1 else None

    buyer_concentration = _concentration(records, lambda a: a.tender.procuring_entity if a.tender else None, "Buyer")
    category_concentration = _concentration(records, lambda a: a.tender.category if a.tender else None, "Category")
    geography_concentration = _concentration(records, lambda a: a.tender.geography if a.tender else None, "Geography")
    method_concentration = _concentration(records, lambda a: a.tender.procurement_method if a.tender else None, "Method")

    relationships = [
        {
            "buyer": item.name,
            "awards": item.count,
            "share": float(item.share),
            "award_value": str(item.value),
            "repeat": item.count >= 2,
        }
        for item in buyer_concentration[:10]
    ]

    repeat_buyer_count = sum(1 for item in buyer_concentration if item.count >= 2)
    max_buyer_share = max((item.share for item in buyer_concentration), default=Decimal("0"))
    max_buyer = buyer_concentration[0].name if buyer_concentration else None
    latest_award_date = max((a.award_date for a in records if a.award_date), default=None)
    first_award_date = min((a.award_date for a in records if a.award_date), default=None)

    value_benchmark = _value_benchmark(values, currency)
    timeline = _timeline(records)
    signals = _build_signals(
        records=records,
        buyer_concentration=buyer_concentration,
        category_concentration=category_concentration,
        geography_concentration=geography_concentration,
        method_concentration=method_concentration,
    )

    sourced_records = sum(1 for award in records if award.tender.source_name)
    source_url_records = sum(1 for award in records if award.tender.source_url or award.source_url)
    retrieved_records = sum(
        1
        for award in records
        if award.tender.retrieved_at is not None or award.retrieved_at is not None
    )

    metrics = [
        SupplierKundaliMetric(label="Awards indexed", value=str(len(records))),
        SupplierKundaliMetric(label="Tenders", value=str(len(distinct_tenders))),
        SupplierKundaliMetric(
            label="Total awarded value",
            value=_format_decimal(sum(values, Decimal("0"))),
            detail=currency or "Mixed/unknown currency",
        ),
        SupplierKundaliMetric(
            label="Average award",
            value=_format_decimal(sum(values, Decimal("0")) / Decimal(len(values))) if values else "Not available",
            detail=currency or "Mixed/unknown currency",
        ),
        SupplierKundaliMetric(
            label="Buyer concentration",
            value=f"{max_buyer_share:.0%}" if buyer_concentration else "Not available",
            detail=f"Highest share: {max_buyer}" if max_buyer else "Buyer not stored",
        ),
        SupplierKundaliMetric(
            label="Repeat buyer relationships",
            value=str(repeat_buyer_count),
            detail="Buyers with 2+ recorded awards",
        ),
        SupplierKundaliMetric(
            label="Participation rate",
            value="Unknown",
            detail="Indian sources currently expose award/winner records, not complete bidder participation.",
            availability="insufficient_data",
        ),
        SupplierKundaliMetric(
            label="Debarment status",
            value="Not indexed",
            detail="No authoritative debarment record is linked to this company profile yet.",
            availability="not_indexed",
        ),
    ]

    notes = [
        "Tender history is derived from Indian procurement award records linked to this company.",
        "A recorded award is treated as a win, but absence from the dataset is not treated as a loss.",
        "Bidder participation and bid-price behaviour remain unavailable unless an Indian source exposes bidder-level records.",
    ]
    data_quality = SupplierDataQuality(
        award_records=len(records),
        tender_records=len(distinct_tenders),
        sourced_records=sourced_records,
        records_with_source_url=source_url_records,
        records_with_retrieval_timestamp=retrieved_records,
        participation_status="insufficient_data",
        bidder_level_status="insufficient_data",
        debarment_status="not_indexed",
        notes=notes,
    )

    repeat_winner = {
        "repeat_buyer_relationships": repeat_buyer_count,
        "highest_buyer_share": max_buyer_share,
        "highest_buyer": max_buyer,
        "max_consecutive_awards_at_buyer": _max_consecutive_awards(records),
        "interpretation": "Repeat awards are a review lead and require contextual comparison; they are not proof of misconduct.",
    }

    limitations = [
        "The current Indian procurement corpus is award-centric; complete supplier participation history is not available.",
        "Bid-price similarity, withdrawal, ranking, and competitor-conditioned participation cannot be asserted without bidder-level Indian records.",
        "Debarment/eligibility status is shown as not indexed unless linked to an authoritative source.",
        "Concentration metrics are descriptive context and should be compared with an appropriate market population before drawing conclusions.",
    ]

    return SupplierKundaliResponse(
        profile=SupplierKundaliProfile(
            id=company.id,
            name=company.name,
            registration_number=company.registration_number,
            source_name=company.source_name,
            source_record_id=company.source_record_id,
            source_url=company.source_url,
            retrieved_at=company.retrieved_at,
        ),
        metrics=metrics,
        buyer_concentration=buyer_concentration,
        category_concentration=category_concentration,
        geography_concentration=geography_concentration,
        method_concentration=method_concentration,
        value_benchmark=value_benchmark,
        timeline=timeline,
        buyer_relationships=relationships,
        repeat_winner=repeat_winner,
        signals=signals,
        data_quality=data_quality,
        limitations=limitations,
        generated_at=datetime.utcnow(),
    )


def _concentration(
    awards: list[Award],
    key_fn,
    dimension: str,
) -> list[SupplierConcentration]:
    grouped: dict[str, list[Award]] = defaultdict(list)
    unknown_count = 0
    unknown_value = Decimal("0")
    for award in awards:
        key = key_fn(award)
        if not key or not key.strip():
            unknown_count += 1
            unknown_value += award.award_value or Decimal("0")
            continue
        grouped[key.strip()].append(award)

    if unknown_count:
        grouped["Unknown / not stored"] += [None] * unknown_count  # type: ignore[list-item]

    total_count = len(awards)
    result: list[SupplierConcentration] = []
    for name, items in grouped.items():
        concrete = [item for item in items if item is not None]
        count = len(concrete)
        if name == "Unknown / not stored":
            value = unknown_value
        else:
            value = sum((a.award_value for a in concrete if a.award_value is not None), Decimal("0"))
        result.append(
            SupplierConcentration(
                dimension=dimension,
                name=name,
                count=count,
                share=Decimal(count) / Decimal(total_count) if total_count else Decimal("0"),
                value=value,
                rank=0,
                population_count=total_count,
            )
        )

    result.sort(key=lambda row: (row.count, row.value), reverse=True)
    for index, row in enumerate(result, start=1):
        row.rank = index
    return result[:10]


def _value_benchmark(values: list[Decimal], currency: str | None) -> SupplierValueBenchmark:
    ordered = sorted(values)
    if not ordered:
        return SupplierValueBenchmark(
            sample_size=0,
            minimum=None,
            p25=None,
            median=None,
            p75=None,
            maximum=None,
            currency=currency,
            method="No award values available",
        )

    return SupplierValueBenchmark(
        sample_size=len(ordered),
        minimum=ordered[0],
        p25=_quantile(ordered, 0.25),
        median=Decimal(str(median(ordered))),
        p75=_quantile(ordered, 0.75),
        maximum=ordered[-1],
        currency=currency,
        method="Nearest-rank interpolation over recorded award values",
    )


def _quantile(values: list[Decimal], q: float) -> Decimal:
    if len(values) == 1:
        return values[0]
    position = Decimal(str(q)) * Decimal(len(values) - 1)
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - Decimal(lower)
    return values[lower] + (values[upper] - values[lower]) * fraction


def _timeline(awards: list[Award]) -> list[SupplierTimelinePoint]:
    grouped: dict[str, list[Award]] = defaultdict(list)
    for award in awards:
        day = award.award_date or (award.tender.published_date if award.tender else None)
        if day:
            grouped[day.strftime("%Y-%m")].append(award)

    return [
        SupplierTimelinePoint(
            period=period,
            awards=len(items),
            value=sum((a.award_value for a in items if a.award_value is not None), Decimal("0")),
        )
        for period, items in sorted(grouped.items())
    ]


def _max_consecutive_awards(awards: list[Award]) -> int:
    by_buyer: dict[str, list[Award]] = defaultdict(list)
    for award in awards:
        buyer = (award.tender.procuring_entity if award.tender else None) or "unknown buyer"
        by_buyer[buyer].append(award)

    best = 0
    for items in by_buyer.values():
        items.sort(key=lambda a: (a.award_date is None, a.award_date, a.created_at, a.id))
        best = max(best, len(items))
    return best


def _build_signals(
    *,
    records: list[Award],
    buyer_concentration: list[SupplierConcentration],
    category_concentration: list[SupplierConcentration],
    geography_concentration: list[SupplierConcentration],
    method_concentration: list[SupplierConcentration],
) -> list[SupplierSignal]:
    signals: list[SupplierSignal] = []

    if len(records) >= 2:
        signals.append(
            SupplierSignal(
                type="repeat_winner",
                severity="informational",
                title="Repeat award history",
                summary=f"The supplier has {len(records)} recorded Indian procurement awards in the indexed dataset.",
                evidence=[f"Award records indexed: {len(records)}"],
                confidence="high",
                review_required=False,
            )
        )

    if buyer_concentration and buyer_concentration[0].share >= Decimal("0.50") and buyer_concentration[0].count >= 2:
        signals.append(
            SupplierSignal(
                type="buyer_concentration",
                severity="medium",
                title="Buyer concentration review lead",
                summary=(
                    f"{buyer_concentration[0].share:.0%} of recorded awards are associated with "
                    f"{buyer_concentration[0].name}."
                ),
                evidence=[
                    f"Awards with top buyer: {buyer_concentration[0].count}",
                    f"Supplier award share: {buyer_concentration[0].share:.0%}",
                ],
                confidence="high",
                review_required=True,
            )
        )

    if category_concentration and category_concentration[0].share >= Decimal("0.75") and len(records) >= 3:
        signals.append(
            SupplierSignal(
                type="category_concentration",
                severity="low",
                title="Category concentration",
                summary=(
                    f"{category_concentration[0].share:.0%} of recorded awards fall in "
                    f"{category_concentration[0].name}."
                ),
                evidence=[
                    f"Category award share: {category_concentration[0].share:.0%}",
                    f"Category awards: {category_concentration[0].count}",
                ],
                confidence="moderate",
                review_required=True,
            )
        )

    if geography_concentration and geography_concentration[0].share >= Decimal("0.75") and len(records) >= 3:
        signals.append(
            SupplierSignal(
                type="geographic_concentration",
                severity="low",
                title="Geographic concentration",
                summary=(
                    f"{geography_concentration[0].share:.0%} of recorded awards map to "
                    f"{geography_concentration[0].name}."
                ),
                evidence=[
                    f"Geographic award share: {geography_concentration[0].share:.0%}",
                    f"Geographic awards: {geography_concentration[0].count}",
                ],
                confidence="moderate",
                review_required=True,
            )
        )

    if method_concentration and method_concentration[0].share >= Decimal("0.75") and len(records) >= 3:
        signals.append(
            SupplierSignal(
                type="method_concentration",
                severity="informational",
                title="Procurement-method concentration",
                summary=(
                    f"{method_concentration[0].share:.0%} of recorded awards use "
                    f"{method_concentration[0].name}."
                ),
                evidence=[
                    f"Method award share: {method_concentration[0].share:.0%}",
                    f"Method awards: {method_concentration[0].count}",
                ],
                confidence="moderate",
                review_required=True,
            )
        )

    signals.append(
        SupplierSignal(
            type="participation_data_gap",
            severity="informational",
            title="Bidder participation data gap",
            summary="Indian procurement sources in the current corpus do not expose complete supplier participation history.",
            evidence=["Awards/wins are available; complete bidder participation is not."],
            confidence="high",
            review_required=False,
        )
    )
    return signals


def _format_decimal(value: Decimal) -> str:
    return f"₹{value:,.2f}"
