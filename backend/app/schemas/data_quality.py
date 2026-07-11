"""Schemas for procurement data-quality reports.

Every metric is computed directly from the imported ingestion tables
(Tender / Company / Award / Document) — there are no placeholder values. See
:mod:`app.services.data_quality`.
"""

from __future__ import annotations

from pydantic import BaseModel


class QualityIssue(BaseModel):
    """One category of data-quality defect."""

    code: str
    label: str
    count: int
    total: int = 0
    ratio: float = 0.0
    severity: str = "info"  # info | warning | critical
    examples: list[str] = []


class CoverageMetric(BaseModel):
    """A completeness ratio (how much of the dataset satisfies a property)."""

    code: str
    label: str
    covered: int
    total: int
    ratio: float


class DataQualityReport(BaseModel):
    generated_at: str
    total_tenders: int
    total_companies: int
    total_awards: int
    total_documents: int
    issues: list[QualityIssue]
    normalization_coverage: list[CoverageMetric]
    evidence_completeness: list[CoverageMetric]
    quality_score: float = 0.0
    critical_issues: int = 0
    warning_issues: int = 0

    @property
    def critical_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "critical")
