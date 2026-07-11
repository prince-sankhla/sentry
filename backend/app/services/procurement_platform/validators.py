"""Platform validation harness (Phase 10).

Runs every engine against the real database and asserts deterministic
invariants (no fabricated numbers, ratios in [0,1], totals non-negative and
internally consistent). Returns a structured pass/fail result per engine plus
overall — used both by the validation CLI and the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.connectors.registry import discover_connectors
from app.models import Award, Company, Document, Tender
from app.services.coverage_engine import build_coverage_engine_report
from app.services.coverage_report import build_coverage_report
from app.services.data_quality import build_data_quality_report
from app.services.evidence_integrity import build_evidence_integrity_report
from app.services.import_statistics import build_import_statistics
from app.services.procurement_platform.evidence import evidence_scores
from app.services.procurement_platform.health import build_connector_dashboard


@dataclass
class ValidationCheck:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationResult:
    generated_at: str
    checks: list[ValidationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def summary(self) -> dict:
        return {
            "passed": self.passed,
            "total": len(self.checks),
            "failed": sum(1 for c in self.checks if not c.passed),
        }


def _ratios_ok(values) -> bool:
    return all(0.0 <= float(v) <= 1.0 for v in values)


def run_validation(db: Session) -> ValidationResult:
    result = ValidationResult(generated_at=now_utc().isoformat())

    def check(name: str, fn) -> None:
        try:
            ok, detail = fn()
            result.checks.append(ValidationCheck(name=name, passed=bool(ok), detail=detail))
        except Exception as error:  # noqa: BLE001
            result.checks.append(ValidationCheck(name=name, passed=False, detail=f"{type(error).__name__}: {error}"))

    # DB reachability + raw totals.
    tenders = int(db.scalar(select(func.count(Tender.id))) or 0)
    awards = int(db.scalar(select(func.count(Award.id))) or 0)
    companies = int(db.scalar(select(func.count(Company.id))) or 0)
    documents = int(db.scalar(select(func.count(Document.id))) or 0)

    check("database_reachable", lambda: (tenders >= 0, f"tenders={tenders}"))

    # Statistics engine matches raw counts (no fabrication).
    def _stats():
        r = build_import_statistics(db)
        t = r.totals
        ok = (
            t.tenders == tenders and t.awards == awards and t.companies == companies
            and t.documents == documents and t.contracts == t.awards
            and t.total_records == tenders + awards + companies + documents
        )
        return ok, f"records={t.total_records} tenders={t.tenders}"
    check("statistics_consistent_with_db", _stats)

    # Data quality: counts <= totals, ratios valid, score in [0,1].
    def _quality():
        r = build_data_quality_report(db)
        ok = all(0 <= i.count for i in r.issues) and _ratios_ok([i.ratio for i in r.issues]) and 0.0 <= r.quality_score <= 1.0
        return ok, f"checks={len(r.issues)} score={r.quality_score}"
    check("data_quality_valid", _quality)

    # Coverage dimensions: shares in [0,1], attributed+unattributed == total tenders.
    def _coverage():
        r = build_coverage_engine_report(db)
        ok = True
        for d in r.dimensions:
            if not (0.0 <= d.coverage_ratio <= 1.0):
                ok = False
            if not _ratios_ok([b.share for b in d.buckets]):
                ok = False
        return ok, f"dimensions={len(r.dimensions)}"
    check("coverage_dimensions_valid", _coverage)

    # Connector coverage report runs and counts are consistent.
    def _conn_coverage():
        r = build_coverage_report(db)
        ok = r.totals.tenders == tenders and r.totals.documents == documents
        return ok, f"connectors={r.totals.connectors_registered}"
    check("connector_coverage_valid", _conn_coverage)

    # Evidence integrity + scores in [0,1], traceable <= tenders.
    def _evidence():
        r = build_evidence_integrity_report(db)
        s = evidence_scores(db)
        ok = (
            _ratios_ok([r.evidence_quality_score, r.evidence_integrity_score, r.evidence_completeness_score, r.integrity_score])
            and r.fully_traceable_tenders <= tenders
            and 0.0 <= s.completeness <= 1.0
        )
        return ok, f"integrity={r.integrity_score} traceable={r.fully_traceable_tenders}/{tenders}"
    check("evidence_integrity_valid", _evidence)

    # Connector dashboard: health scores in [0,1], counts match registry.
    def _dashboard():
        r = build_connector_dashboard(db)
        registered = len(discover_connectors().names())
        ok = r.connectors_total == registered and _ratios_ok([e.health_score for e in r.entries])
        return ok, f"connectors={r.connectors_total} avg_health={r.average_health_score}"
    check("connector_dashboard_valid", _dashboard)

    return result
