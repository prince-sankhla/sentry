"""Context Providers — pluggable sources of procurement context.

The engine consults providers in priority order and takes the first available
answer. Phase 1 ships exactly one provider — the local Context Store. Phase 2
adds a trusted-retrieval provider (returning Draft cards) as another plugin;
the engine will not change.

Provider contract:
  * read-only over the investigation (providers receive only the query);
  * never invent — a provider either returns cards that genuinely exist in its
    backing source, or an unavailable resolution;
  * ``name`` gives every resolution its provenance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.verified_context.schema import (
    CONTEXT_UNAVAILABLE,
    ContextQuery,
    ContextResolution,
)
from app.verified_context.store import ContextStore


class ContextProvider(ABC):
    """Interface every context source implements."""

    #: Stable provider name, recorded on every resolution for provenance.
    name: str = ""
    #: Lower runs first when the engine consults multiple providers.
    priority: int = 100

    @abstractmethod
    def resolve(self, query: ContextQuery) -> ContextResolution:
        """Answer the query from this provider's backing source, or report
        unavailability. Must never speculate or fabricate cards."""


class LocalStoreProvider(ContextProvider):
    """Phase 1 provider: the local Verified Context Library.

    Serves ONLY ``verified`` cards (drafts await review; retired cards are
    never returned). Matching is deterministic: the card must declare the
    queried indicator, and any requested jurisdiction/category must be either
    declared by the card or left unscoped by it.
    """

    name = "local_store"
    priority = 0  # the library is always consulted first

    def __init__(self, store: ContextStore | None = None) -> None:
        self.store = store or ContextStore()

    def resolve(self, query: ContextQuery) -> ContextResolution:
        matched = [
            card
            for card in self.store.load()
            if card.status == "verified"
            and query.indicator_id in card.applies_to_indicators
            and _scope_ok(card.jurisdictions, query.jurisdiction)
            and _scope_ok(card.categories, query.category)
        ]
        if matched:
            matched.sort(key=lambda c: c.card_id)  # deterministic order
            return ContextResolution(available=True, cards=matched, provider=self.name)
        return ContextResolution(available=False, message=CONTEXT_UNAVAILABLE, provider=self.name)


def _scope_ok(declared: list[str], requested: str) -> bool:
    """A card matches when it is unscoped, nothing was requested, or the
    requested scope is declared."""
    return not declared or not requested or requested in declared
