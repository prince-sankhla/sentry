from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Benchmark(Base):
    """Contextual procurement benchmark — comparable tender population statistics.

    A benchmark captures statistics (median, P25, P75, IQR) for a specific
    comparable tender population defined by dimensions (buyer, category, value_band,
    date_range). The same population definition + metric always produces the same
    benchmark_key, enabling caching and reproducibility.

    Benchmarks are built on-demand and refreshed when stale (>7 days old).
    """

    __tablename__ = "benchmarks"
    __table_args__ = (
        UniqueConstraint("benchmark_key", name="uq_benchmarks_benchmark_key"),
        Index("ix_benchmarks_dimensions", "dimensions", postgresql_using="gin"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Deterministic hash of (population_definition + metric) for caching/lookup
    benchmark_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Population definition: which tenders were included in this benchmark
    population_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Which dimensions were used (subset of population_definition keys)
    dimensions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    # Metric being benchmarked
    metric: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Population statistics
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    median: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    p25: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    p75: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    iqr: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    mean: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    stddev: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    min_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_value: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Provenance: sample tender IDs for audit trail (first 100)
    sample_tender_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    # Provenance: hash of the SQL query used (reproducibility proof)
    source_query_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Quality: True if sample_size >= minimum threshold
    sufficient_sample: Mapped[bool] = mapped_column(nullable=False)

    # Freshness
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    refresh_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
