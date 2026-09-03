from __future__ import annotations

import statistics
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tender import Tender
from app.services.procurement_scope import INTERNATIONAL_PROCUREMENT_SOURCES
from app.schemas.phase6_benchmark import (
    BenchmarkPopulation,
    BenchmarkStats,
    TenderBenchmarkComparison,
)

MIN_SAMPLE_SIZE = 5
VALUE_BANDS = (
    (Decimal("0"), Decimal("1000000"), "0-1M"),
    (Decimal("1000000"), Decimal("10000000"), "1M-10M"),
    (Decimal("10000000"), Decimal("100000000"), "10M-100M"),
    (Decimal("100000000"), Decimal("999999999999999999"), "100M+"),
)


def _value_band(value: Decimal | None) -> str | None:
    if value is None or value < 0:
        return None
    for lower, upper, label in VALUE_BANDS:
        if lower <= value < upper:
            return label
    return "100M+"


def _percentile(values: list[Decimal], observed: Decimal) -> int:
    if not values:
        return 50
    below = sum(1 for value in values if value < observed)
    equal = sum(1 for value in values if value == observed)
    return int(round((below + equal * Decimal("0.5")) / len(values) * 100))


def _stats(values: list[Decimal], observed: Decimal | None) -> BenchmarkStats:
    if not values or len(values) < MIN_SAMPLE_SIZE:
        return BenchmarkStats(minimum=min(values) if values else None, maximum=max(values) if values else None)
    ordered = sorted(values)
    p25, median, p75 = statistics.quantiles(ordered, n=4, method="inclusive")[0], statistics.median(ordered), statistics.quantiles(ordered, n=4, method="inclusive")[2]
    iqr = p75 - p25
    deviation = None if iqr == 0 or observed is None else max(Decimal("-5"), min(Decimal("5"), (observed - median) / iqr))
    return BenchmarkStats(
        minimum=ordered[0],
        p25=p25,
        median=median,
        mean=statistics.mean(ordered),
        p75=p75,
        maximum=ordered[-1],
        iqr=iqr,
        percentile=_percentile(ordered, observed) if observed is not None else None,
        deviation_iqr=deviation,
    )


def _levels(tender: Tender) -> list[tuple[str, list[Tender], dict[str, str]]]:
    filters = [Tender.deleted_at.is_(None), Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES), Tender.estimated_value.isnot(None), Tender.estimated_value > 0]
    scope = select(Tender).where(*filters)
    result: list[tuple[str, list[Tender], dict[str, str]]] = []

    dimensions = [
        ("buyer-category-method-geography-band", {
            "buyer": tender.procuring_entity or "",
            "category": tender.category or "",
            "procurement_method": tender.procurement_method or "",
            "geography": tender.geography or "",
            "value_band": _value_band(tender.estimated_value) or "",
        }),
        ("buyer-category-method-geography", {
            "buyer": tender.procuring_entity or "",
            "category": tender.category or "",
            "procurement_method": tender.procurement_method or "",
            "geography": tender.geography or "",
        }),
        ("buyer-category-method", {
            "buyer": tender.procuring_entity or "",
            "category": tender.category or "",
            "procurement_method": tender.procurement_method or "",
        }),
        ("buyer-category", {
            "buyer": tender.procuring_entity or "",
            "category": tender.category or "",
        }),
        ("category-method", {
            "category": tender.category or "",
            "procurement_method": tender.procurement_method or "",
        }),
        ("category", {"category": tender.category or ""}),
        ("global", {}),
    ]
    return result, scope, dimensions


def compare_tender_estimate(db: Session, tender_id: str) -> TenderBenchmarkComparison | None:
    try:
        target = db.execute(select(Tender).where(Tender.id == tender_id)).scalar_one_or_none()
    except Exception:
        return None
    if target is None:
        return None

    if target.estimated_value is None or target.estimated_value <= 0:
        population = BenchmarkPopulation(level="unavailable", dimensions={}, sample_size=0, sufficient_sample=False)
        return TenderBenchmarkComparison(
            tender_id=str(target.id), reference_number=target.reference_number, metric="estimated_value",
            observed_value=target.estimated_value, currency=target.currency, benchmark_available=False,
            population=population, statistics=BenchmarkStats(),
            interpretation="Benchmark unavailable because the tender has no valid estimated value.",
            generated_at=datetime.now(timezone.utc),
            methodology=["Deterministic contextual benchmark", "Indian procurement sources only", f"Minimum sample size: {MIN_SAMPLE_SIZE}"],
        )

    base_filters = [Tender.deleted_at.is_(None), Tender.source_name.notin_(INTERNATIONAL_PROCUREMENT_SOURCES), Tender.estimated_value.isnot(None), Tender.estimated_value > 0]
    candidates = db.scalars(select(Tender).where(*base_filters)).all()

    target_band = _value_band(target.estimated_value)
    level_defs = [
        ("buyer-category-method-geography-band", {"buyer": target.procuring_entity, "category": target.category, "procurement_method": target.procurement_method, "geography": target.geography, "value_band": target_band}),
        ("buyer-category-method-geography", {"buyer": target.procuring_entity, "category": target.category, "procurement_method": target.procurement_method, "geography": target.geography}),
        ("buyer-category-method", {"buyer": target.procuring_entity, "category": target.category, "procurement_method": target.procurement_method}),
        ("buyer-category", {"buyer": target.procuring_entity, "category": target.category}),
        ("category-method", {"category": target.category, "procurement_method": target.procurement_method}),
        ("category", {"category": target.category}),
        ("global", {}),
    ]

    selected_level = "global"
    selected_dimensions: dict[str, str] = {}
    selected_values: list[Decimal] = []
    for level, wanted in level_defs:
        values = []
        for candidate in candidates:
            if candidate.id == target.id:
                continue
            if any((getattr(candidate, key, None) if key != "value_band" else _value_band(candidate.estimated_value)) != value for key, value in wanted.items() if value not in (None, "")):
                continue
            values.append(candidate.estimated_value)
        if len(values) >= MIN_SAMPLE_SIZE:
            selected_level, selected_dimensions, selected_values = level, {k: str(v) for k, v in wanted.items() if v not in (None, "")}, values
            break

    stats = _stats(selected_values, target.estimated_value)
    available = len(selected_values) >= MIN_SAMPLE_SIZE and stats.median is not None
    population = BenchmarkPopulation(level=selected_level, dimensions=selected_dimensions, sample_size=len(selected_values), sufficient_sample=available)

    if not available:
        interpretation = f"No statistically sufficient comparable population was available (n={len(selected_values)}; minimum {MIN_SAMPLE_SIZE})."
    else:
        percentile = stats.percentile or 50
        if percentile >= 95:
            interpretation = f"Observed estimate is at approximately the {percentile}th percentile of the selected comparable Indian tender population. Review as contextual outlier, not proof of wrongdoing."
        elif percentile >= 75:
            interpretation = f"Observed estimate is above the population median and sits around the {percentile}th percentile of comparable tenders."
        else:
            interpretation = f"Observed estimate sits around the {percentile}th percentile of the selected comparable tender population."

    return TenderBenchmarkComparison(
        tender_id=str(target.id), reference_number=target.reference_number, metric="estimated_value",
        observed_value=target.estimated_value, currency=target.currency, benchmark_available=available,
        population=population, statistics=stats, interpretation=interpretation,
        generated_at=datetime.now(timezone.utc),
        methodology=[
            "Deterministic contextual benchmark",
            "Indian procurement sources only",
            "Comparable-population fallback hierarchy",
            f"Minimum sufficient sample size: {MIN_SAMPLE_SIZE}",
            "Percentile and IQR are contextual statistics, not statutory thresholds",
        ],
    )
