"""Schemas for the connector health dashboard (Phase 5)."""

from __future__ import annotations

from pydantic import BaseModel


class ConnectorDashboardEntry(BaseModel):
    name: str
    label: str
    status: str                       # active | stale | no_data
    is_indian: bool
    record_count: int
    total_runs: int
    import_success_rate: float
    failure_rate: float
    average_import_time_seconds: float
    average_download_time_seconds: float
    retry_count: int
    freshness_days: int | None
    last_successful_sync: str | None
    last_failed_sync: str | None
    checkpoint_status: str            # tracked | none
    last_checkpoint_record: str | None
    incremental_support: bool
    normalization_coverage: float
    data_quality_score: float
    evidence_coverage: float
    missing_required_fields: int
    duplicate_rate: float
    health_score: float


class ConnectorDashboard(BaseModel):
    generated_at: str
    connectors_total: int
    connectors_active: int
    connectors_stale: int
    connectors_no_data: int
    average_health_score: float
    entries: list[ConnectorDashboardEntry]
