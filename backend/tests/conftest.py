"""Pytest bootstrap.

``app.models`` and ``app.webintel.models`` reference each other, a latent circular
that Python resolves cleanly only when ``app.models`` is imported first (as it is
in normal app startup via ``app.main``). A test module that imports a
``app.webintel`` submodule cold would otherwise trip the cycle at collection time.
Importing the model package here — before any test module is collected —
establishes the module graph in the correct order for the whole test session.
"""

from __future__ import annotations

import app.models  # noqa: F401  (import-order side effect: resolves the model cycle)

import pytest
from sqlalchemy.orm import Session

from app.db.session import engine


@pytest.fixture
def db_session():
    """A Session bound to a rolled-back outer transaction.

    Every test runs against the real database schema but commits are captured as
    SAVEPOINTs inside one outer transaction that is rolled back on teardown, so
    tests are fully isolated and never persist rows. Requires a reachable
    database (the ingestion tables must exist).
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
