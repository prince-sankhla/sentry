"""add source record versions

Revision ID: d1f6a42d9b55
Revises: f4a2c8d15e30
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d1f6a42d9b55"
down_revision: str | None = "f4a2c8d15e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_record_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False),
        sa.Column("source_record_id", sa.String(length=500), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False, server_default="imported"),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_name",
            "source_record_id",
            "content_hash",
            name="uq_source_record_versions_source_record_hash",
        ),
    )
    op.create_index(op.f("ix_source_record_versions_action"), "source_record_versions", ["action"], unique=False)
    op.create_index(op.f("ix_source_record_versions_content_hash"), "source_record_versions", ["content_hash"], unique=False)
    op.create_index(op.f("ix_source_record_versions_reference_number"), "source_record_versions", ["reference_number"], unique=False)
    op.create_index(op.f("ix_source_record_versions_source_name"), "source_record_versions", ["source_name"], unique=False)
    op.create_index(op.f("ix_source_record_versions_source_record_id"), "source_record_versions", ["source_record_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_source_record_versions_source_record_id"), table_name="source_record_versions")
    op.drop_index(op.f("ix_source_record_versions_source_name"), table_name="source_record_versions")
    op.drop_index(op.f("ix_source_record_versions_reference_number"), table_name="source_record_versions")
    op.drop_index(op.f("ix_source_record_versions_content_hash"), table_name="source_record_versions")
    op.drop_index(op.f("ix_source_record_versions_action"), table_name="source_record_versions")
    op.drop_table("source_record_versions")
