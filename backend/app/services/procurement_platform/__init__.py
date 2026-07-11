"""SENTRY Procurement Data Platform — unified deterministic engine package.

Single import surface for the whole procurement data platform. Existing service
modules remain in place for backward compatibility; this package is the
canonical facade that groups them with the new engines:

    taxonomy · normalization · quality · coverage · statistics · evidence ·
    integrity · health · checkpoints (incremental) · acquisition ·
    performance · validators · reports

Public names are resolved lazily (PEP 562) so importing the package never
triggers an import cycle with the underlying service modules. Nothing here
fabricates data — every builder reads the live database.
"""

from __future__ import annotations

import importlib
from typing import Any

# Public name -> (module path, attribute). Resolved on first access.
_EXPORTS: dict[str, tuple[str, str]] = {
    # report builders
    "build_data_quality_report": ("app.services.data_quality", "build_data_quality_report"),
    "build_import_statistics": ("app.services.import_statistics", "build_import_statistics"),
    "build_coverage_engine_report": ("app.services.coverage_engine", "build_coverage_engine_report"),
    "build_coverage_report": ("app.services.coverage_report", "build_coverage_report"),
    "build_evidence_integrity_report": ("app.services.evidence_integrity", "build_evidence_integrity_report"),
    "build_connector_dashboard": ("app.services.procurement_platform.health", "build_connector_dashboard"),
    "build_platform_report": ("app.services.procurement_platform.reports", "build_platform_report"),
    "run_validation": ("app.services.procurement_platform.validators", "run_validation"),
    "ValidationResult": ("app.services.procurement_platform.validators", "ValidationResult"),
    # evidence engine
    "EvidenceScores": ("app.services.procurement_platform.evidence", "EvidenceScores"),
    "backfill_evidence": ("app.services.procurement_platform.evidence", "backfill_evidence"),
    "evidence_field_hash": ("app.services.procurement_platform.evidence", "evidence_field_hash"),
    "evidence_scores": ("app.services.procurement_platform.evidence", "evidence_scores"),
    # incremental / sync engine
    "DeltaPlan": ("app.services.procurement_platform.incremental", "DeltaPlan"),
    "RetryQueue": ("app.services.procurement_platform.incremental", "RetryQueue"),
    "plan_delta": ("app.services.procurement_platform.incremental", "plan_delta"),
    "resolve_conflict": ("app.services.procurement_platform.incremental", "resolve_conflict"),
    "rollback_to_version": ("app.services.procurement_platform.incremental", "rollback_to_version"),
    "synchronize_deletions": ("app.services.procurement_platform.incremental", "synchronize_deletions"),
    # performance
    "ImportProgress": ("app.services.procurement_platform.performance", "ImportProgress"),
    "ParallelImportResult": ("app.services.procurement_platform.performance", "ParallelImportResult"),
    "batched": ("app.services.procurement_platform.performance", "batched"),
    "parallel_import": ("app.services.procurement_platform.performance", "parallel_import"),
    "stream_envelopes": ("app.services.procurement_platform.performance", "stream_envelopes"),
    # acquisition
    "AcquisitionResult": ("app.services.procurement_platform.acquisition", "AcquisitionResult"),
    "PRIORITY_SOURCES": ("app.services.procurement_platform.acquisition", "PRIORITY_SOURCES"),
    "acquire": ("app.services.procurement_platform.acquisition", "acquire"),
    "acquire_all": ("app.services.procurement_platform.acquisition", "acquire_all"),
    "probe_source": ("app.services.procurement_platform.acquisition", "probe_source"),
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:  # PEP 562 lazy attribute resolution
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    return getattr(module, target[1])


def __dir__() -> list[str]:
    return sorted(__all__)
