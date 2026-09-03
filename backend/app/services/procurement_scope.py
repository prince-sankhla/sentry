from __future__ import annotations

# Sources that are not Indian procurement systems. They remain in the database for
# provenance/reference, but the default product intelligence surface is India-only.
INTERNATIONAL_PROCUREMENT_SOURCES = frozenset({
    "world_bank",
    "adb",
    "un_procurement",
    "prozorro",
})


def is_indian_source(source_name: str | None) -> bool:
    return (source_name or "").strip().casefold() not in INTERNATIONAL_PROCUREMENT_SOURCES
