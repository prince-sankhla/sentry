"""Verified Context Engine — SENTRY's curated procurement-context subsystem.

SENTRY detects procurement anomalies deterministically. This subsystem answers
the follow-up question: *is there a legitimate procurement context that could
explain the finding?* — without thousands of hardcoded rules and without AI
inventing procurement knowledge.

It does so through a gradually-built **Verified Context Library**:

  Phase 1 (this code)  — foundation: schema, store, provider interface, engine.
                         The engine checks the local Context Store first; when
                         nothing is found it honestly reports the context as
                         unavailable. Nothing more.
  Phase 2 (future)     — trusted retrieval: when local context is unavailable,
                         retrieve guidance ONLY from trusted sources and return
                         it as a Draft Context Card. (A provider plugin; the
                         engine does not change.)
  Phase 3 (future)     — verification: approved Draft cards become permanent,
                         reusable knowledge in the library.

The subsystem is standalone: it does not modify the investigation engine and no
existing pipeline calls it yet.
"""

from app.verified_context.engine import VerifiedContextEngine
from app.verified_context.providers import ContextProvider, LocalStoreProvider
from app.verified_context.schema import (
    CONTEXT_UNAVAILABLE,
    ContextCard,
    ContextQuery,
    ContextResolution,
)
from app.verified_context.analyzer import (
    APPLICABILITY_NOT_ESTABLISHED_MESSAGE,
    NO_GUIDANCE_MESSAGE,
    GuidanceItem,
    ProcurementContextAnalysis,
    ProcurementContextAnalyzer,
)
from app.verified_context.applicability import (
    APPLICABILITY_LABELS,
    Applicability,
    ContextFacts,
    FactRecord,
)
from app.verified_context.store import ContextStore
from app.verified_context.trusted import (
    TRUSTED_AUTHORITIES,
    TrustedRetrievalProvider,
    build_default_engine,
    is_trusted_domain,
)

__all__ = [
    "APPLICABILITY_LABELS",
    "APPLICABILITY_NOT_ESTABLISHED_MESSAGE",
    "Applicability",
    "CONTEXT_UNAVAILABLE",
    "ContextFacts",
    "FactRecord",
    "NO_GUIDANCE_MESSAGE",
    "ContextCard",
    "ContextProvider",
    "ContextQuery",
    "ContextResolution",
    "ContextStore",
    "GuidanceItem",
    "LocalStoreProvider",
    "ProcurementContextAnalysis",
    "ProcurementContextAnalyzer",
    "TRUSTED_AUTHORITIES",
    "TrustedRetrievalProvider",
    "VerifiedContextEngine",
    "build_default_engine",
    "is_trusted_domain",
]
