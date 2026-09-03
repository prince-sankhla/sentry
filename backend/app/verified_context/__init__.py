"""Verified Context + Official Procurement Context subsystem.

SENTRY detects procurement anomalies deterministically. This subsystem provides
an evidence-safe follow-up layer for legitimate procurement context: curated
procurement guidance, trusted-source retrieval, and deterministic applicability
analysis. It never invents procurement knowledge and never adjudicates wrongdoing.

Current runtime flow:

  Local Context Store
        |
        +-- hit --> verified / reusable context card
        |
        +-- miss --> trusted allowlisted guidance as Draft Context Card
        |
        v
  Fact-gated applicability analysis
        |
        v
  Investigator-facing context only

The subsystem is integrated through the investigation context-analysis API and
the FindingCaseFile UI. It is read-only over findings and does not modify the
risk engine, risk severity, or evidence-verification verdicts.
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
