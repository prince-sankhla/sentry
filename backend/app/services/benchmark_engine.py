"""Contextual Procurement Benchmark Engine.

Computes and caches comparable tender population statistics (median, P25, P75, IQR)
for use in contextual risk detection. A benchmark represents the statistical baseline
for a specific population (e.g., "Construction tenders by Maharashtra PWD valued
between 1M-10M INR"). Observed values are compared against these baselines to
identify genuine anomalies vs. normal market behavior.

Design principles:
* Deterministic — same population definition produces same benchmark_key
* Cacheable — benchmarks stored in DB, reused across investigations
* Transparent — population definition + sample tender IDs provide audit trail
* Safe — explicit insufficient-sample state when population too small
* Reproducible — source_query_hash enables verification

Value bands (configurable):
* "0-1M": 0 to 999,999.99
* "1M-10M": 1,000,000 to 9,999,999.99
* "10M-100M": 10,000,000 to 99,999,999.99
* "100M+": >= 100,000,000

Refresh policy:
* Benchmarks older than 7 days are stale
* Stale benchmarks rebuilt on next get_benchmark() call
* No automatic background refresh (future P1)
"""

from __future__ import annotations

import hashlib
import json
import statistics
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.award import Award
from app.models.benchmark import Benchmark
from app.models.tender import Tender
from app.schemas.benchmark import BenchmarkComparison, BenchmarkDimensions, BenchmarkResult

# Minimum sample size for a benchmark to be considered statistically sufficient
MIN_SAMPLE_SIZE = 5

# Benchmark freshness: benchmarks older than this are rebuilt
BENCHMARK_REFRESH_DAYS = 7

# Value band boundaries (INR) — configurable comparison buckets for dimensioning
# benchmarks by value range. These are NOT procurement-risk thresholds; they
# partition tenders into comparable value scales. Bands optimized for Indian
# public procurement scale (1M INR ≈ $12k USD, 10M ≈ $120k, 100M ≈ $1.2M).
VALUE_BANDS = [
    (Decimal("0"), Decimal("1000000"), "0-1M"),
    (Decimal("1000000"), Decimal("10000000"), "1M-10M"),
    (Decimal("10000000"), Decimal("100000000"), "10M-100M"),
    (Decimal("100000000"), Decimal("999999999999"), "100M+"),
]


def _classify_value_band(value: Decimal | None) -> str | None:
    """Classify a monetary value into a band for benchmark dimensioning.

    Returns band label (e.g., "1M-10M") or None if value is None/negative.
    """
    if value is None or value < 0:
        return None
    for lower, upper, label in VALUE_BANDS:
        if lower <= value < upper:
            return label
    return VALUE_BANDS[-1][2]  # "100M+"


def _build_benchmark_key(dimensions: BenchmarkDimensions, metric: str) -> str:
    """Deterministic hash of (dimensions + metric) for caching/lookup.

    Same dimensions + metric always produce same key, enabling cache hits.
    """
    # Serialize dimensions to canonical JSON (sorted keys)
    dim_dict = dimensions.model_dump(exclude_none=True)
    if "date_range" in dim_dict and dim_dict["date_range"]:
        # Convert date tuple to ISO strings for JSON serialization
        dim_dict["date_range"] = [d.isoformat() for d in dim_dict["date_range"]]
    canonical = json.dumps({"dimensions": dim_dict, "metric": metric}, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _build_query_hash(sql_str: str) -> str:
    """Hash of the SQL query for reproducibility verification."""
    return hashlib.sha256(sql_str.encode()).hexdigest()


def _compute_percentile(values: list[Decimal], observed: Decimal) -> int:
    """Compute percentile rank of observed value in population (0-100).

    Uses linear interpolation for percentile calculation.
    """
    if not values:
        return 50  # default to median if no population
    sorted_vals = sorted(values)
    count_below = sum(1 for v in sorted_vals if v < observed)
    count_equal = sum(1 for v in sorted_vals if v == observed)
    # Percentile = (count_below + 0.5 * count_equal) / total * 100
    percentile = (count_below + 0.5 * count_equal) / len(sorted_vals) * 100
    return int(round(percentile))


def _compute_deviation(observed: Decimal, median: Decimal, iqr: Decimal) -> Decimal | None:
    """Compute deviation in IQR units: (observed - median) / IQR.

    Returns None if IQR is zero (no dispersion in population).
    Clamped to [-5, 5] to avoid extreme outliers dominating.
    """
    if iqr == 0:
        return None
    deviation = (observed - median) / iqr
    return max(Decimal("-5"), min(Decimal("5"), deviation))


def get_benchmark(
    db: Session,
    dimensions: BenchmarkDimensions,
    metric: str,
) -> BenchmarkResult | None:
    """Retrieve or build a benchmark for the given dimensions + metric.

    Returns cached benchmark if fresh, rebuilds if stale or missing, or None if
    population is empty after applying filters.

    Args:
        db: Database session
        dimensions: Population dimensions (buyer, category, value_band, etc.)
        metric: Metric to benchmark ("estimated_value" or "award_value")

    Returns:
        BenchmarkResult with statistics, or None if population empty
    """
    benchmark_key = _build_benchmark_key(dimensions, metric)

    # Check cache: is there a fresh benchmark?
    cached = db.scalar(
        select(Benchmark).where(
            Benchmark.benchmark_key == benchmark_key,
            Benchmark.refresh_at > func.now(),
        )
    )

    if cached:
        return _benchmark_to_result(cached, dimensions)

    # Cache miss or stale: build new benchmark
    return build_benchmark(db, dimensions, metric)


def build_benchmark(
    db: Session,
    dimensions: BenchmarkDimensions,
    metric: str,
) -> BenchmarkResult | None:
    """Build a new benchmark by querying the tender/award population.

    Computes statistics (median, P25, P75, IQR) from the population defined by
    dimensions, stores in DB for caching, and returns result.

    Args:
        db: Database session
        dimensions: Population dimensions
        metric: "estimated_value" or "award_value"

    Returns:
        BenchmarkResult with computed statistics, or None if population empty
    """
    benchmark_key = _build_benchmark_key(dimensions, metric)

    # Build query based on metric
    if metric == "estimated_value":
        query = _build_tender_query(dimensions)
        value_col = Tender.estimated_value
        id_col = Tender.reference_number
    elif metric == "award_value":
        query = _build_award_query(dimensions)
        value_col = Award.award_value
        id_col = Tender.reference_number
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    # Fetch population: (value, tender_reference) pairs
    # Exclude NULL values, zero, and negative (invalid for monetary metrics)
    population = db.execute(
        query.where(value_col.isnot(None), value_col > 0)
        .with_only_columns(value_col, id_col)
        .order_by(value_col)
    ).all()

    if not population:
        return None  # Empty population

    values = [Decimal(str(row[0])) for row in population]
    tender_ids = [str(row[1]) for row in population]
    sample_size = len(values)

    # Compute statistics
    sufficient = sample_size >= MIN_SAMPLE_SIZE
    median_val = Decimal(str(statistics.median(values))) if sufficient else None
    p25_val = Decimal(str(statistics.quantiles(values, n=4)[0])) if sufficient and sample_size >= 2 else None
    p75_val = Decimal(str(statistics.quantiles(values, n=4)[2])) if sufficient and sample_size >= 2 else None
    iqr_val = (p75_val - p25_val) if p25_val and p75_val else None
    mean_val = Decimal(str(statistics.mean(values))) if sufficient else None
    stddev_val = Decimal(str(statistics.stdev(values))) if sufficient and sample_size >= 2 else None
    min_val = min(values)
    max_val = max(values)

    # Query hash for reproducibility
    query_str = str(query.compile(compile_kwargs={"literal_binds": True}))
    query_hash = _build_query_hash(query_str)

    # Store benchmark in DB (update if exists, insert if new)
    now = datetime.now(timezone.utc)
    refresh_at = now + timedelta(days=BENCHMARK_REFRESH_DAYS)

    # Check if benchmark already exists
    from sqlalchemy import select
    existing = db.scalar(select(Benchmark).where(Benchmark.benchmark_key == benchmark_key))

    if existing:
        # Update existing benchmark
        existing.population_definition = dimensions.model_dump(exclude_none=True)
        existing.dimensions = list(dimensions.model_dump(exclude_none=True).keys())
        existing.metric = metric
        existing.sample_size = sample_size
        existing.median = float(median_val) if median_val else None
        existing.p25 = float(p25_val) if p25_val else None
        existing.p75 = float(p75_val) if p75_val else None
        existing.iqr = float(iqr_val) if iqr_val else None
        existing.mean = float(mean_val) if mean_val else None
        existing.stddev = float(stddev_val) if stddev_val else None
        existing.min_value = float(min_val)
        existing.max_value = float(max_val)
        existing.sample_tender_ids = tender_ids[:100]
        existing.source_query_hash = query_hash
        existing.sufficient_sample = sufficient
        existing.refresh_at = refresh_at
        db.commit()
        db.refresh(existing)
        return _benchmark_to_result(existing, dimensions)
    else:
        # Insert new benchmark
        benchmark = Benchmark(
            benchmark_key=benchmark_key,
            population_definition=dimensions.model_dump(exclude_none=True),
            dimensions=list(dimensions.model_dump(exclude_none=True).keys()),
            metric=metric,
            sample_size=sample_size,
            median=float(median_val) if median_val else None,
            p25=float(p25_val) if p25_val else None,
            p75=float(p75_val) if p75_val else None,
            iqr=float(iqr_val) if iqr_val else None,
            mean=float(mean_val) if mean_val else None,
            stddev=float(stddev_val) if stddev_val else None,
            min_value=float(min_val),
            max_value=float(max_val),
            sample_tender_ids=tender_ids[:100],
            source_query_hash=query_hash,
            sufficient_sample=sufficient,
            refresh_at=refresh_at,
        )
        try:
            db.add(benchmark)
            db.commit()
            db.refresh(benchmark)
            return _benchmark_to_result(benchmark, dimensions)
        except Exception as e:
            # Handle concurrent insert (duplicate benchmark_key)
            if "unique constraint" in str(e).lower() or "duplicate key" in str(e).lower():
                db.rollback()
                # Fetch the just-inserted benchmark from concurrent process
                existing = db.scalar(select(Benchmark).where(Benchmark.benchmark_key == benchmark_key))
                if existing:
                    return _benchmark_to_result(existing, dimensions)
            # Re-raise if not a duplicate-key error
            raise


def _build_tender_query(dimensions: BenchmarkDimensions):
    """Build SQLAlchemy query for tender-based metrics (estimated_value).

    Filters by dimensions: buyer, category, procurement_method, geography,
    value_band, date_range. Excludes soft-deleted tenders.
    """
    query = select(Tender).where(Tender.deleted_at.is_(None))

    if dimensions.buyer:
        query = query.where(Tender.procuring_entity == dimensions.buyer)

    if dimensions.category:
        query = query.where(Tender.category == dimensions.category)

    if dimensions.procurement_method:
        query = query.where(Tender.procurement_method == dimensions.procurement_method)

    if dimensions.geography:
        query = query.where(Tender.geography == dimensions.geography)

    if dimensions.value_band:
        lower, upper = _value_band_bounds(dimensions.value_band)
        query = query.where(
            Tender.estimated_value >= lower,
            Tender.estimated_value < upper,
        )

    if dimensions.date_range:
        start_date, end_date = dimensions.date_range
        query = query.where(
            Tender.published_date >= start_date,
            Tender.published_date <= end_date,
        )

    return query


def _build_award_query(dimensions: BenchmarkDimensions):
    """Build SQLAlchemy query for award-based metrics (award_value).

    Joins Award -> Tender, filters by tender dimensions.
    """
    query = (
        select(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .where(Tender.deleted_at.is_(None))
    )

    if dimensions.buyer:
        query = query.where(Tender.procuring_entity == dimensions.buyer)

    if dimensions.category:
        query = query.where(Tender.category == dimensions.category)

    if dimensions.procurement_method:
        query = query.where(Tender.procurement_method == dimensions.procurement_method)

    if dimensions.geography:
        query = query.where(Tender.geography == dimensions.geography)

    if dimensions.value_band:
        lower, upper = _value_band_bounds(dimensions.value_band)
        # For award_value metric, filter by award value not tender value
        query = query.where(
            Award.award_value >= lower,
            Award.award_value < upper,
        )

    if dimensions.date_range:
        start_date, end_date = dimensions.date_range
        query = query.where(
            Tender.published_date >= start_date,
            Tender.published_date <= end_date,
        )

    return query


def _value_band_bounds(band: str) -> tuple[Decimal, Decimal]:
    """Return (lower, upper) bounds for a value band label."""
    for lower, upper, label in VALUE_BANDS:
        if label == band:
            return lower, upper
    raise ValueError(f"Unknown value band: {band}")


def _benchmark_to_result(benchmark: Benchmark, dimensions: BenchmarkDimensions) -> BenchmarkResult:
    """Convert Benchmark DB model to BenchmarkResult schema."""
    return BenchmarkResult(
        benchmark_key=benchmark.benchmark_key,
        dimensions=dimensions,
        metric=benchmark.metric,
        sample_size=benchmark.sample_size,
        sufficient_sample=benchmark.sufficient_sample,
        median=Decimal(str(benchmark.median)) if benchmark.median else None,
        p25=Decimal(str(benchmark.p25)) if benchmark.p25 else None,
        p75=Decimal(str(benchmark.p75)) if benchmark.p75 else None,
        iqr=Decimal(str(benchmark.iqr)) if benchmark.iqr else None,
        mean=Decimal(str(benchmark.mean)) if benchmark.mean else None,
        stddev=Decimal(str(benchmark.stddev)) if benchmark.stddev else None,
        min_value=Decimal(str(benchmark.min_value)) if benchmark.min_value else None,
        max_value=Decimal(str(benchmark.max_value)) if benchmark.max_value else None,
        sample_tender_ids=benchmark.sample_tender_ids,
        source_query_hash=benchmark.source_query_hash,
        created_at=benchmark.created_at,
        refresh_at=benchmark.refresh_at,
    )


def compare_to_benchmark(
    observed: Decimal,
    benchmark: BenchmarkResult,
) -> BenchmarkComparison:
    """Compare an observed value against a benchmark population.

    Computes deviation (in IQR units), approximate percentile rank, and
    contextual severity. Percentile is estimated via linear interpolation
    between population min/median/max (±5-10 point accuracy for explanation
    purposes only).

    Args:
        observed: Observed value to compare
        benchmark: Benchmark population statistics

    Returns:
        BenchmarkComparison with deviation, percentile, severity, and explanation
    """
    if not benchmark.sufficient_sample or not benchmark.median:
        return BenchmarkComparison(
            observed_value=observed,
            benchmark=benchmark,
            deviation=None,
            percentile=None,
            severity=None,
            explanation=f"Insufficient benchmark sample (n={benchmark.sample_size}, minimum {MIN_SAMPLE_SIZE} required).",
        )

    median = benchmark.median
    iqr = benchmark.iqr

    # Compute deviation
    deviation = _compute_deviation(observed, median, iqr) if iqr and iqr > 0 else None

    # Compute percentile (requires rebuilding value list from sample)
    # Note: This is approximate since we don't store full population
    # For exact percentile, would need to query population again
    percentile = None
    if benchmark.min_value and benchmark.max_value:
        # Approximate percentile using linear interpolation between min/max
        if observed <= benchmark.min_value:
            percentile = 0
        elif observed >= benchmark.max_value:
            percentile = 100
        elif benchmark.median:
            # Linear interpolation: below median vs above median
            if observed < median:
                percentile = int(50 * (observed - benchmark.min_value) / (median - benchmark.min_value))
            else:
                percentile = 50 + int(50 * (observed - median) / (benchmark.max_value - median))

    # Contextual severity based on deviation
    severity = None
    if deviation is not None:
        if abs(deviation) < Decimal("1.0"):
            severity = "normal"
        elif abs(deviation) < Decimal("2.0"):
            severity = "moderate"
        elif abs(deviation) < Decimal("3.0"):
            severity = "high"
        else:
            severity = "critical"

    # Explanation
    direction = "above" if observed > median else "below"
    explanation = (
        f"Observed {observed:,.0f} is {direction} benchmark median {median:,.0f} "
        f"(n={benchmark.sample_size} comparable tenders)"
    )
    if deviation is not None:
        explanation += f", deviation {deviation:.2f} IQR"
    if percentile is not None:
        explanation += f", ~{percentile}th percentile"

    return BenchmarkComparison(
        observed_value=observed,
        benchmark=benchmark,
        deviation=deviation,
        percentile=percentile,
        severity=severity,
        explanation=explanation,
    )


def refresh_stale_benchmarks(db: Session, limit: int = 100) -> int:
    """Refresh stale benchmarks (older than BENCHMARK_REFRESH_DAYS).

    Args:
        db: Database session
        limit: Maximum number of benchmarks to refresh in one call

    Returns:
        Number of benchmarks refreshed
    """
    stale = db.scalars(
        select(Benchmark)
        .where(Benchmark.refresh_at <= func.now())
        .order_by(Benchmark.refresh_at)
        .limit(limit)
    ).all()

    refreshed = 0
    for benchmark in stale:
        # Rebuild benchmark with same dimensions + metric
        dim_dict = benchmark.population_definition
        # Convert date_range back from ISO strings if present
        if "date_range" in dim_dict and dim_dict["date_range"]:
            dim_dict["date_range"] = tuple(date.fromisoformat(d) for d in dim_dict["date_range"])
        dimensions = BenchmarkDimensions(**dim_dict)

        result = build_benchmark(db, dimensions, benchmark.metric)
        if result:
            refreshed += 1

    return refreshed
