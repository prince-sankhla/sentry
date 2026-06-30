"""add import engine state

Revision ID: b72f2f91d4a6
Revises: 9c0d12f67b44
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b72f2f91d4a6"
down_revision: str | None = "9c0d12f67b44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "import_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("last_processed_page", sa.String(length=255), nullable=True),
        sa.Column("last_processed_record", sa.String(length=500), nullable=True),
        sa.Column("last_successful_import_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_imported", sa.Integer(), nullable=False),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False),
        sa.Column("failed_imports", sa.Integer(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", name="uq_import_checkpoints_source"),
    )
    op.create_index(op.f("ix_import_checkpoints_source"), "import_checkpoints", ["source"], unique=False)

    op.create_table(
        "import_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_page", sa.String(length=255), nullable=True),
        sa.Column("current_record", sa.String(length=500), nullable=True),
        sa.Column("total_records", sa.Integer(), nullable=True),
        sa.Column("processed_records", sa.Integer(), nullable=False),
        sa.Column("downloaded_records", sa.Integer(), nullable=False),
        sa.Column("imported_tenders", sa.Integer(), nullable=False),
        sa.Column("imported_companies", sa.Integer(), nullable=False),
        sa.Column("imported_awards", sa.Integer(), nullable=False),
        sa.Column("duplicates_skipped", sa.Integer(), nullable=False),
        sa.Column("failed_imports", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_import_runs_source"), "import_runs", ["source"], unique=False)
    op.create_index(op.f("ix_import_runs_status"), "import_runs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_import_runs_status"), table_name="import_runs")
    op.drop_index(op.f("ix_import_runs_source"), table_name="import_runs")
    op.drop_table("import_runs")
    op.drop_index(op.f("ix_import_checkpoints_source"), table_name="import_checkpoints")
    op.drop_table("import_checkpoints")
