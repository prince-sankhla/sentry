"""Schemas for procurement ingestion coverage reports.

See :mod:`app.services.coverage_report`. Every number is read from the
ingestion tables or the connector registry — nothing is fabricated.
"""

from __future__ import annotations

from pydantic import BaseModel


class ConnectorHealth(BaseModel):
    name: str
    label: str
    registered: bool
    has_raw_directory: bool
    is_indian: bool
    priority_rank: int
    tenders: int
    companies: int
    awards: int
    documents: int
    versions: int
    last_import_status: str | None = None
    last_import_at: str | None = None
    last_retrieved_at: str | None = None
    freshness_days: int | None = None
    health: str = "no_data"  # active | stale | no_data


class ProvenanceStats(BaseModel):
    import_runs: int
    completed_runs: int
    failed_runs: int
    source_record_versions: int
    checkpoints: int
    imported_action_versions: int
    updated_action_versions: int


class CoverageTotals(BaseModel):
    connectors_registered: int
    connectors_active: int
    tenders: int
    companies: int
    awards: int
    documents: int
    distinct_buyers: int
    mapped_canonical_companies: int


class CoverageReport(BaseModel):
    generated_at: str
    totals: CoverageTotals
    provenance: ProvenanceStats
    connectors: list[ConnectorHealth]
    unsupported_portals: list[str]
