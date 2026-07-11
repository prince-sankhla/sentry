"""add evidence provenance columns and tender soft-delete

Revision ID: e2c7b93af41a
Revises: d1f6a42d9b55
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e2c7b93af41a"
down_revision: str | None = "d1f6a42d9b55"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("connector_name", sa.String(length=100), nullable=True))
    op.add_column("documents", sa.Column("connector_version", sa.String(length=30), nullable=True))
    op.add_column("documents", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("evidence_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "documents",
        sa.Column("evidence_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("documents", sa.Column("import_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("http_status", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("archive_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("mirror_url", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_documents_connector_name"), "documents", ["connector_name"], unique=False)
    op.create_index(op.f("ix_documents_evidence_hash"), "documents", ["evidence_hash"], unique=False)
    op.create_index(op.f("ix_documents_import_run_id"), "documents", ["import_run_id"], unique=False)

    op.add_column("tenders", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_tenders_deleted_at"), "tenders", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tenders_deleted_at"), table_name="tenders")
    op.drop_column("tenders", "deleted_at")

    op.drop_index(op.f("ix_documents_import_run_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_evidence_hash"), table_name="documents")
    op.drop_index(op.f("ix_documents_connector_name"), table_name="documents")
    for column in (
        "verified_at", "mirror_url", "archive_url", "http_status", "import_run_id",
        "evidence_version", "evidence_hash", "source_url", "connector_version", "connector_name",
    ):
        op.drop_column("documents", column)
