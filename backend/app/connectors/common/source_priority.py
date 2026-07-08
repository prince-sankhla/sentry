"""Indian-procurement-first source ranking.

SENTRY's mission ranks Indian government procurement above international data in
every surface that orders records: global search, autocomplete, and the
investigation retrieval path. This module is the single source of truth for that
ordering so search, the DB record source, and the SourceManager all agree.

Priority (spec order, lower rank = shown first):
    1. GeM              2. CPPP             3. NIC eProcurement (state portals)
    4. Rajasthan        5. Maharashtra      6. Kerala
    7. Odisha           8. West Bengal      9. CAG
    10. data.gov.in     — then international (World Bank, ADB, UN, Prozorro).

Unknown Indian-looking sources sort ahead of known international sources but
behind the explicitly ranked Indian sources. Everything unrecognised sorts last.
"""

from __future__ import annotations

# Explicit rank per connector source_name. Gaps are intentional so new Indian
# portals can slot in without renumbering.
_SOURCE_RANK: dict[str, int] = {
    "gem": 10,
    "cppp": 20,
    # NIC eProcurement state portals (share the CPPP/NIC markup + mapper).
    "eproc_rajasthan": 40,
    "eproc_maharashtra": 50,
    "eproc_kerala": 60,
    "eproc_odisha": 70,
    "eproc_westbengal": 80,
    "eproc_karnataka": 90,
    "cag": 100,
    "datagovin": 110,
    # International — always secondary to any Indian source.
    "world_bank": 500,
    "adb": 510,
    "un_procurement": 520,
    "prozorro": 530,
}

# Sources known to be Indian government procurement (used for the Indian-first
# tie-break and for search-quality boosts even when a source is unranked).
_INDIAN_SOURCES: frozenset[str] = frozenset(
    {
        "gem",
        "cppp",
        "cag",
        "datagovin",
        "eproc_rajasthan",
        "eproc_maharashtra",
        "eproc_kerala",
        "eproc_odisha",
        "eproc_westbengal",
        "eproc_karnataka",
    }
)

# Any source whose name starts with this prefix is an NIC state eProcurement
# portal, hence Indian, even if it is not individually ranked yet.
_INDIAN_PREFIXES: tuple[str, ...] = ("eproc_",)

_UNKNOWN_INDIAN_RANK = 200
_UNKNOWN_RANK = 900


def is_indian_source(source_name: str | None) -> bool:
    """True when a source is Indian government procurement."""
    if not source_name:
        return False
    name = source_name.strip().casefold()
    if name in _INDIAN_SOURCES:
        return True
    return name.startswith(_INDIAN_PREFIXES)


def source_rank(source_name: str | None) -> int:
    """Return the sort rank for a source (lower ranks first).

    Indian sources always rank ahead of international ones. Unrecognised Indian
    portals sort just behind the explicitly ranked Indian sources; everything
    else sorts last.
    """
    if not source_name:
        return _UNKNOWN_RANK
    name = source_name.strip().casefold()
    if name in _SOURCE_RANK:
        return _SOURCE_RANK[name]
    if is_indian_source(name):
        return _UNKNOWN_INDIAN_RANK
    return _UNKNOWN_RANK


def prioritize_source_names(source_names: list[str]) -> list[str]:
    """Order connector names Indian-first, then by rank, then alphabetically."""
    return sorted(source_names, key=lambda name: (source_rank(name), name))


def indian_first_key(source_name: str | None) -> tuple[int, int]:
    """Sort key placing Indian sources first, then by explicit rank.

    Returns ``(indian_bucket, rank)`` where ``indian_bucket`` is 0 for Indian
    sources and 1 otherwise — so callers can stable-sort an already
    relevance-ordered list without losing the Indian-first guarantee.
    """
    return (0 if is_indian_source(source_name) else 1, source_rank(source_name))
