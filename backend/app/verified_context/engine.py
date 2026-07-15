"""Verified Context Engine — resolve legitimate procurement context for a finding.

Phase 1 behaviour, in full:

    query → local Context Store (via LocalStoreProvider)
          → verified cards found?  yes → return them
          →                        no  → "Context unavailable"

The engine is provider-agnostic: it walks its providers in priority order and
returns the first available resolution. Adding Phase 2 (trusted retrieval →
Draft cards) or any future source means registering another provider — the
engine itself never changes.

Nothing here touches the investigation engine, indicators, severities, or
scores; no existing pipeline calls this subsystem yet.
"""

from __future__ import annotations

from app.verified_context.providers import ContextProvider, LocalStoreProvider
from app.verified_context.schema import (
    CONTEXT_UNAVAILABLE,
    ContextQuery,
    ContextResolution,
)


class VerifiedContextEngine:
    """Consults context providers in priority order; never invents context."""

    def __init__(self, providers: list[ContextProvider] | None = None) -> None:
        # Phase 1 default: the local library is the only provider.
        self.providers = sorted(
            providers if providers is not None else [LocalStoreProvider()],
            key=lambda p: (p.priority, p.name),
        )

    def resolve(self, query: ContextQuery) -> ContextResolution:
        """First available resolution wins; otherwise honestly unavailable."""
        for provider in self.providers:
            try:
                resolution = provider.resolve(query)
            except Exception:
                continue  # a failing provider never breaks resolution
            if resolution.available:
                return resolution
        return ContextResolution(
            available=False,
            message=CONTEXT_UNAVAILABLE,
            provider=self.providers[-1].name if self.providers else "",
        )
