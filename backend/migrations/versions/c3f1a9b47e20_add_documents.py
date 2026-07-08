"""add documents table

Revision ID: c3f1a9b47e20
Revises: e7b63e2f4f91
Create Date: 2026-07-07 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3f1a9b47e20"
down_revision: str | None = "e7b63e2f4f91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tender_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("document_type", sa.String(length=50), nullable=False, server_default="attachment"),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("file_extension", sa.String(length=20), nullable=True),
        sa.Column("source_name", sa.String(length=100), nullable=True),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("downloaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tender_id", "title", name="uq_documents_tender_title"),
    )
    op.create_index(op.f("ix_documents_tender_id"), "documents", ["tender_id"], unique=False)
    op.create_index(op.f("ix_documents_document_type"), "documents", ["document_type"], unique=False)
    op.create_index(op.f("ix_documents_content_hash"), "documents", ["content_hash"], unique=False)
    op.create_index(op.f("ix_documents_source_name"), "documents", ["source_name"], unique=False)
    op.create_index(op.f("ix_documents_source_record_id"), "documents", ["source_record_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_source_record_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_source_name"), table_name="documents")
    op.drop_index(op.f("ix_documents_content_hash"), table_name="documents")
    op.drop_index(op.f("ix_documents_document_type"), table_name="documents")
    op.drop_index(op.f("ix_documents_tender_id"), table_name="documents")
    op.drop_table("documents")
