"""Schemas for evidence-integrity reports (Phase 4)."""

from __future__ import annotations

from pydantic import BaseModel


class IntegrityCheck(BaseModel):
    code: str
    label: str
    present: int
    total: int
    ratio: float
    complete: bool


class IntegrityViolation(BaseModel):
    code: str
    label: str
    count: int
    severity: str = "warning"
    examples: list[str] = []


class EvidenceIntegrityReport(BaseModel):
    generated_at: str
    total_tenders: int
    total_documents: int
    total_source_versions: int
    provenance_checks: list[IntegrityCheck]
    violations: list[IntegrityViolation]
    evidence_quality_score: float
    evidence_integrity_score: float
    evidence_completeness_score: float
    integrity_score: float
    fully_traceable_tenders: int
    fully_traceable_ratio: float
