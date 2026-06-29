"""initial schema

Revision ID: 21484c14a7cf
Revises: 
Create Date: 2026-06-29 18:44:36.078595
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '21484c14a7cf'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("registration_number"),
    )
    op.create_index(op.f("ix_companies_name"), "companies", ["name"], unique=True)
    op.create_index(
        op.f("ix_companies_registration_number"),
        "companies",
        ["registration_number"],
        unique=True,
    )

    op.create_table(
        "tenders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("procuring_entity", sa.String(length=255), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("closing_date", sa.Date(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_number"),
    )
    op.create_index(op.f("ix_tenders_reference_number"), "tenders", ["reference_number"], unique=True)

    op.create_table(
        "awards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("award_date", sa.Date(), nullable=True),
        sa.Column("award_value", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tender_id", "company_id", name="uq_awards_tender_company"),
    )
    op.create_index(op.f("ix_awards_company_id"), "awards", ["company_id"], unique=False)
    op.create_index(op.f("ix_awards_tender_id"), "awards", ["tender_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_awards_tender_id"), table_name="awards")
    op.drop_index(op.f("ix_awards_company_id"), table_name="awards")
    op.drop_table("awards")
    op.drop_index(op.f("ix_tenders_reference_number"), table_name="tenders")
    op.drop_table("tenders")
    op.drop_index(op.f("ix_companies_registration_number"), table_name="companies")
    op.drop_index(op.f("ix_companies_name"), table_name="companies")
    op.drop_table("companies")
