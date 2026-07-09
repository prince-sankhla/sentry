"""add full-text search + trigram fuzzy search on tenders

Enables high-quality retrieval:
* ``pg_trgm`` extension for fuzzy / typo-tolerant matching.
* A generated ``search_vector`` tsvector on tenders (title + description +
  procuring_entity + reference) with a GIN index for ranked full-text search.
* GIN trigram indexes on title and procuring_entity so ``ILIKE '%q%'`` and
  similarity() are index-backed instead of sequential scans.

Backwards-compatible: the column is GENERATED ALWAYS so it needs no application
writes, and the DB search falls back to ILIKE where FTS yields nothing.

Revision ID: f4a2c8d15e30
Revises: c3f1a9b47e20
"""

from __future__ import annotations

from alembic import op

revision = "f4a2c8d15e30"
down_revision = "c3f1a9b47e20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Generated tsvector: weighted so title/reference outrank description/buyer.
    op.execute(
        """
        ALTER TABLE tenders
        ADD COLUMN IF NOT EXISTS search_vector tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A')
            || setweight(to_tsvector('english', coalesce(reference_number, '')), 'A')
            || setweight(to_tsvector('english', coalesce(procuring_entity, '')), 'B')
            || setweight(to_tsvector('english', coalesce(description, '')), 'C')
        ) STORED
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_tenders_search_vector ON tenders USING gin (search_vector)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenders_title_trgm ON tenders USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tenders_entity_trgm ON tenders USING gin (procuring_entity gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_companies_name_trgm ON companies USING gin (name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_companies_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tenders_entity_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tenders_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_tenders_search_vector")
    op.execute("ALTER TABLE tenders DROP COLUMN IF EXISTS search_vector")
    # Leave pg_trgm installed; other objects may depend on it.
