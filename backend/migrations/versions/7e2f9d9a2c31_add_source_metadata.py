"""add source metadata

Revision ID: 7e2f9d9a2c31
Revises: 21484c14a7cf
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "7e2f9d9a2c31"
down_revision: str | None = "21484c14a7cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("tenders", "companies", "awards"):
        op.add_column(table_name, sa.Column("source_name", sa.String(length=100), nullable=True))
        op.add_column(table_name, sa.Column("source_record_id", sa.String(length=255), nullable=True))
        op.add_column(table_name, sa.Column("source_url", sa.Text(), nullable=True))
        op.add_column(table_name, sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True))
        op.create_index(op.f(f"ix_{table_name}_source_name"), table_name, ["source_name"], unique=False)
        op.create_index(op.f(f"ix_{table_name}_source_record_id"), table_name, ["source_record_id"], unique=False)


def downgrade() -> None:
    for table_name in ("awards", "companies", "tenders"):
        op.drop_index(op.f(f"ix_{table_name}_source_record_id"), table_name=table_name)
        op.drop_index(op.f(f"ix_{table_name}_source_name"), table_name=table_name)
        op.drop_column(table_name, "retrieved_at")
        op.drop_column(table_name, "source_url")
        op.drop_column(table_name, "source_record_id")
        op.drop_column(table_name, "source_name")
