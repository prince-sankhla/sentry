"""add web procurement evidence

Revision ID: 9c0d12f67b44
Revises: 4b8fd7b7a1d2
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9c0d12f67b44"
down_revision: str | None = "4b8fd7b7a1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_procurement_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("web_evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("award_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("company_name", sa.String(length=500), nullable=True),
        sa.Column("normalized_company_name", sa.String(length=500), nullable=True),
        sa.Column("government_buyer", sa.String(length=500), nullable=True),
        sa.Column("tender_title", sa.Text(), nullable=True),
        sa.Column("contract_title", sa.Text(), nullable=True),
        sa.Column("contract_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("tender_category", sa.String(length=255), nullable=True),
        sa.Column("procurement_sector", sa.String(length=255), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("award_date", sa.Date(), nullable=True),
        sa.Column("contract_number", sa.String(length=255), nullable=True),
        sa.Column("tender_number", sa.String(length=255), nullable=True),
        sa.Column("organization", sa.String(length=500), nullable=True),
        sa.Column("people_mentioned", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("related_companies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["award_id"], ["awards.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["web_evidence_id"], ["web_evidence.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("web_evidence_id", name="uq_web_procurement_evidence_web_evidence_id"),
    )
    op.create_index(op.f("ix_web_procurement_evidence_award_id"), "web_procurement_evidence", ["award_id"], unique=False)
    op.create_index(op.f("ix_web_procurement_evidence_company_id"), "web_procurement_evidence", ["company_id"], unique=False)
    op.create_index("ix_web_procurement_evidence_government_buyer", "web_procurement_evidence", ["government_buyer"], unique=False)
    op.create_index("ix_web_procurement_evidence_normalized_company_name", "web_procurement_evidence", ["normalized_company_name"], unique=False)
    op.create_index(op.f("ix_web_procurement_evidence_tender_id"), "web_procurement_evidence", ["tender_id"], unique=False)
    op.create_index("ix_web_procurement_evidence_tender_number", "web_procurement_evidence", ["tender_number"], unique=False)
    op.create_index(op.f("ix_web_procurement_evidence_web_evidence_id"), "web_procurement_evidence", ["web_evidence_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_web_procurement_evidence_web_evidence_id"), table_name="web_procurement_evidence")
    op.drop_index("ix_web_procurement_evidence_tender_number", table_name="web_procurement_evidence")
    op.drop_index(op.f("ix_web_procurement_evidence_tender_id"), table_name="web_procurement_evidence")
    op.drop_index("ix_web_procurement_evidence_normalized_company_name", table_name="web_procurement_evidence")
    op.drop_index("ix_web_procurement_evidence_government_buyer", table_name="web_procurement_evidence")
    op.drop_index(op.f("ix_web_procurement_evidence_company_id"), table_name="web_procurement_evidence")
    op.drop_index(op.f("ix_web_procurement_evidence_award_id"), table_name="web_procurement_evidence")
    op.drop_table("web_procurement_evidence")
