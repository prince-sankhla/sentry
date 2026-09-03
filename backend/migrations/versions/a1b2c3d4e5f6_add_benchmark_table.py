"""add benchmark table

Revision ID: a1b2c3d4e5f6
Revises: f4a2c8d15e30
Create Date: 2026-08-15 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "e2c7b93af41a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_key", sa.String(length=64), nullable=False),
        sa.Column("population_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dimensions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metric", sa.String(length=50), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("median", sa.Numeric(14, 2), nullable=True),
        sa.Column("p25", sa.Numeric(14, 2), nullable=True),
        sa.Column("p75", sa.Numeric(14, 2), nullable=True),
        sa.Column("iqr", sa.Numeric(14, 2), nullable=True),
        sa.Column("mean", sa.Numeric(14, 2), nullable=True),
        sa.Column("stddev", sa.Numeric(14, 2), nullable=True),
        sa.Column("min_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("sample_tender_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_query_hash", sa.String(length=64), nullable=False),
        sa.Column("sufficient_sample", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("refresh_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("benchmark_key", name="uq_benchmarks_benchmark_key"),
    )
    op.create_index("ix_benchmarks_benchmark_key", "benchmarks", ["benchmark_key"], unique=True)
    op.create_index("ix_benchmarks_metric", "benchmarks", ["metric"], unique=False)
    op.create_index("ix_benchmarks_dimensions", "benchmarks", ["dimensions"], unique=False, postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_benchmarks_dimensions", table_name="benchmarks", postgresql_using="gin")
    op.drop_index("ix_benchmarks_metric", table_name="benchmarks")
    op.drop_index("ix_benchmarks_benchmark_key", table_name="benchmarks")
    op.drop_table("benchmarks")
