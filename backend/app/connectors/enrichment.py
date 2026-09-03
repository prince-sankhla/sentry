"""Tender enrichment helpers — apply taxonomy classifiers to normalized records.

Enriches NormalizedTender records with derived dimensions (procurement_method,
geography, category) using deterministic keyword-based taxonomy classifiers.

These enrichments enable contextual benchmarking but are NOT authoritative
classifications — they are heuristic, derived from title/description/buyer text.
"""

from __future__ import annotations

from app.connectors.base import NormalizedTender, NormalizedSourceMetadata
from app.services.procurement_taxonomy import (
    OTHER,
    UNATTRIBUTED,
    UNSPECIFIED,
    category_of,
    procurement_method_of,
    state_of,
)


def enrich_tender(tender: NormalizedTender) -> NormalizedTender:
    """Apply taxonomy classifiers to derive enrichment fields.

    Returns a new NormalizedTender with enrichment fields populated.
    Preserves original tender if enrichment fields already set.
    """
    # If already enriched, return as-is
    if tender.procurement_method or tender.geography or tender.category:
        return tender

    # Derive enrichment fields
    method = procurement_method_of(tender.title, tender.description)
    geo = state_of(tender.procuring_entity, tender.title)
    cat = category_of(tender.title, tender.description)

    # Convert sentinel values to None (prefer explicit NULL over "Unspecified")
    method = None if method in (UNSPECIFIED, OTHER) else method
    geo = None if geo in (UNATTRIBUTED, OTHER) else geo
    cat = None if cat in (OTHER, UNSPECIFIED) else cat

    # Return enriched tender
    return NormalizedTender(
        reference_number=tender.reference_number,
        title=tender.title,
        description=tender.description,
        procuring_entity=tender.procuring_entity,
        published_date=tender.published_date,
        closing_date=tender.closing_date,
        estimated_value=tender.estimated_value,
        currency=tender.currency,
        metadata=tender.metadata,
        procurement_method=method,
        geography=geo,
        category=cat,
    )
