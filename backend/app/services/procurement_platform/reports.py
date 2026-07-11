"""Consolidated platform reporting orchestrator.

Runs every deterministic engine against the live database and returns one
report object. This is the single entry point the CLI / API can call to get the
full picture: statistics, quality, coverage (both engines), evidence integrity
and connector health.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.services.coverage_engine import build_coverage_engine_report
from app.services.coverage_report import build_coverage_report
from app.services.data_quality import build_data_quality_report
from app.services.evidence_integrity import build_evidence_integrity_report
from app.services.import_statistics import build_import_statistics
from app.services.procurement_platform.health import build_connector_dashboard


def build_platform_report(db: Session) -> dict:
    """Return the full platform report as a serialisable dict."""
    return {
        "generated_at": now_utc().isoformat(),
        "statistics": build_import_statistics(db).model_dump(),
        "data_quality": build_data_quality_report(db).model_dump(),
        "coverage_dimensions": build_coverage_engine_report(db).model_dump(),
        "coverage_connectors": build_coverage_report(db).model_dump(),
        "evidence_integrity": build_evidence_integrity_report(db).model_dump(),
        "connector_dashboard": build_connector_dashboard(db).model_dump(),
    }
