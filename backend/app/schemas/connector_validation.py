"""Schemas for connector validation / health reports (Phase 6)."""

from __future__ import annotations

from pydantic import BaseModel


class ConnectorValidation(BaseModel):
    name: str
    label: str
    is_indian: bool
    priority_rank: int
    # current state
    tenders: int
    awards: int
    companies: int
    documents: int
    versions: int
    # capability (from metadata)
    import_mechanism: str
    last_update_capability: str
    normalization_quality_declared: str
    supported_entities: list[str]
    raw_directory: str | None
    # measured normalization quality (0-1)
    normalization_score: float
    award_coverage: float          # awards / tenders for this source
    document_coverage: float       # tenders with >=1 doc / tenders
    # verdict
    import_capability: str         # "verified" | "capable_no_data" | "registered_only"
    health: str                    # active | stale | no_data
    known_limitations: list[str]


class ConnectorHealthReport(BaseModel):
    generated_at: str
    connectors_registered: int
    connectors_with_data: int
    indian_connectors: int
    connectors: list[ConnectorValidation]
