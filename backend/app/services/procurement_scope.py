from __future__ import annotations

from sqlalchemy import or_

# Sources that are authoritative Indian procurement / oversight feeds used by
# SENTRY's India-only investigation surfaces. International sources remain in the
# database for provenance/reference, but must not contaminate Indian analytics.
INDIAN_PROCUREMENT_SOURCES = frozenset(
    {
        "gem",
        "cppp",
        "cag",
        "cvc",
        "datagovin",
        "nic",
        "eproc_rajasthan",
        "eproc_maharashtra",
        "eproc_kerala",
        "eproc_odisha",
        "eproc_westbengal",
        "eproc_karnataka",
    }
)

INTERNATIONAL_PROCUREMENT_SOURCES = frozenset(
    {
        "world_bank",
        "adb",
        "un_procurement",
        "prozorro",
    }
)


def is_indian_source(source_name: str | None) -> bool:
    """Return True only for known Indian sources or NIC eProc state portals."""
    if not source_name:
        return False
    name = source_name.strip().casefold()
    return name in INDIAN_PROCUREMENT_SOURCES or name.startswith("eproc_")


def indian_source_clause(column):
    """SQLAlchemy predicate matching the same Indian-source policy."""
    known = [name for name in INDIAN_PROCUREMENT_SOURCES]
    return or_(column.in_(known), column.ilike("eproc_%"))
