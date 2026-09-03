"""add tender enrichment fields

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-15 16:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6g7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenders", sa.Column("procurement_method", sa.String(length=100), nullable=True))
    op.add_column("tenders", sa.Column("geography", sa.String(length=100), nullable=True))
    op.add_column("tenders", sa.Column("category", sa.String(length=100), nullable=True))
    op.create_index("ix_tenders_procurement_method", "tenders", ["procurement_method"], unique=False)
    op.create_index("ix_tenders_geography", "tenders", ["geography"], unique=False)
    op.create_index("ix_tenders_category", "tenders", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tenders_category", table_name="tenders")
    op.drop_index("ix_tenders_geography", table_name="tenders")
    op.drop_index("ix_tenders_procurement_method", table_name="tenders")
    op.drop_column("tenders", "category")
    op.drop_column("tenders", "geography")
    op.drop_column("tenders", "procurement_method")
