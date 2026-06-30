"""add web evidence

Revision ID: 4b8fd7b7a1d2
Revises: 7e2f9d9a2c31
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4b8fd7b7a1d2"
down_revision: str | None = "7e2f9d9a2c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.String(length=300), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_web_evidence_content_hash"),
    )
    op.create_index("ix_web_evidence_query", "web_evidence", ["query"], unique=False)
    op.create_index("ix_web_evidence_url", "web_evidence", ["url"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_web_evidence_url", table_name="web_evidence")
    op.drop_index("ix_web_evidence_query", table_name="web_evidence")
    op.drop_table("web_evidence")
