"""add entity resolution

Revision ID: e7b63e2f4f91
Revises: b72f2f91d4a6
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e7b63e2f4f91"
down_revision: str | None = "b72f2f91d4a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canonical_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_name", sa.String(length=500), nullable=False),
        sa.Column("canonical_key", sa.String(length=500), nullable=False),
        sa.Column("aliases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("matched_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("linked_company_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_key", name="uq_canonical_companies_canonical_key"),
    )
    op.create_index("ix_canonical_companies_canonical_key", "canonical_companies", ["canonical_key"], unique=False)
    op.create_index("ix_canonical_companies_canonical_name", "canonical_companies", ["canonical_name"], unique=False)

    op.create_table(
        "canonical_company_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("alias", sa.String(length=500), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("match_reason", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_company_id"], ["canonical_companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_canonical_company_links_company_id"),
        sa.UniqueConstraint("source_type", "source_id", name="uq_canonical_company_links_source"),
    )
    op.create_index(op.f("ix_canonical_company_links_canonical_company_id"), "canonical_company_links", ["canonical_company_id"], unique=False)
    op.create_index(op.f("ix_canonical_company_links_company_id"), "canonical_company_links", ["company_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_canonical_company_links_company_id"), table_name="canonical_company_links")
    op.drop_index(op.f("ix_canonical_company_links_canonical_company_id"), table_name="canonical_company_links")
    op.drop_table("canonical_company_links")
    op.drop_index("ix_canonical_companies_canonical_name", table_name="canonical_companies")
    op.drop_index("ix_canonical_companies_canonical_key", table_name="canonical_companies")
    op.drop_table("canonical_companies")
