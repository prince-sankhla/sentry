"""Evidence-integrity engine (Phase 4).

Verifies that every imported record preserves the full provenance chain and
reports the three headline evidence scores (quality / integrity / completeness)
plus deterministic detection of:

    missing evidence · broken document links · missing provenance ·
    hash mismatch · duplicate evidence · orphan evidence · version conflicts

All counts are real; advanced fields the ingestion layer does not populate
(archive/mirror URL, HTTP status) are reported as coverage checks, not hidden.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.envelope import content_hash
from app.connectors.common.parse import now_utc
from app.models import Document, SourceRecordVersion, Tender
from app.schemas.evidence_integrity import (
    EvidenceIntegrityReport,
    IntegrityCheck,
    IntegrityViolation,
)
from app.services.procurement_platform.evidence import evidence_scores

_EXAMPLE_LIMIT = 10


def build_evidence_integrity_report(db: Session) -> EvidenceIntegrityReport:
    total_tenders = int(db.scalar(select(func.count(Tender.id))) or 0)
    total_documents = int(db.scalar(select(func.count(Document.id))) or 0)
    total_versions = int(db.scalar(select(func.count(SourceRecordVersion.id))) or 0)

    checks = [
        _tender_check(db, "source_preserved", "Tenders retaining their source name", Tender.source_name, total_tenders),
        _tender_check(db, "source_identifier", "Tenders retaining a source record id", Tender.source_record_id, total_tenders),
        _tender_check(db, "source_url", "Tenders retaining a source URL", Tender.source_url, total_tenders),
        _tender_check(db, "import_timestamp", "Tenders with an import timestamp", Tender.created_at, total_tenders),
        _tender_check(db, "last_update", "Tenders with a last-update timestamp", Tender.updated_at, total_tenders),
        _tender_check(db, "retrieved_at", "Tenders with a retrieval timestamp", Tender.retrieved_at, total_tenders),
        _doc_check(db, "document_url", "Documents retaining a URL", Document.url, total_documents),
        _doc_check(db, "content_hash", "Documents retaining a content hash", Document.content_hash, total_documents),
        _doc_check(db, "evidence_hash", "Documents retaining an evidence hash", Document.evidence_hash, total_documents),
        _doc_check(db, "connector_name", "Documents retaining a connector name", Document.connector_name, total_documents),
        _doc_check(db, "connector_version", "Documents retaining a connector version", Document.connector_version, total_documents),
        _doc_check(db, "document_type", "Documents retaining a document type", Document.document_type, total_documents),
        _doc_check(db, "verification_timestamp", "Documents with a verification timestamp", Document.verified_at, total_documents),
        _doc_check(db, "import_run_link", "Documents linked to an import run", Document.import_run_id, total_documents),
        _doc_check(db, "archive_url", "Documents with an archive URL", Document.archive_url, total_documents),
        _doc_check(db, "http_status", "Documents with an HTTP status", Document.http_status, total_documents),
        _version_check(db, "version_hash", "Source versions retaining a content hash", SourceRecordVersion.content_hash, total_versions),
    ]

    violations = _violations(db)
    scores = evidence_scores(db)
    fully_traceable = _fully_traceable_count(db)

    return EvidenceIntegrityReport(
        generated_at=now_utc().isoformat(),
        total_tenders=total_tenders,
        total_documents=total_documents,
        total_source_versions=total_versions,
        provenance_checks=checks,
        violations=violations,
        evidence_quality_score=scores.quality,
        evidence_integrity_score=scores.integrity,
        evidence_completeness_score=scores.completeness,
        integrity_score=_score(checks),
        fully_traceable_tenders=fully_traceable,
        fully_traceable_ratio=round(fully_traceable / total_tenders, 4) if total_tenders else 0.0,
    )


def _violations(db: Session) -> list[IntegrityViolation]:
    violations: list[IntegrityViolation] = []

    # missing evidence — tenders with no document.
    with_docs = int(db.scalar(select(func.count(func.distinct(Document.tender_id)))) or 0)
    total_tenders = int(db.scalar(select(func.count(Tender.id))) or 0)
    missing_evidence = max(total_tenders - with_docs, 0)
    violations.append(IntegrityViolation(code="missing_evidence", label="Tenders with no evidence", count=missing_evidence, severity="warning"))

    # broken document links — documents with no URL.
    broken_links = int(db.scalar(select(func.count(Document.id)).where(Document.url.is_(None))) or 0)
    violations.append(IntegrityViolation(code="broken_document_links", label="Documents with no URL", count=broken_links, severity="warning"))

    # missing provenance — tenders lacking source name/url/id.
    missing_prov_rows = db.execute(
        select(Tender.reference_number).where(
            (Tender.source_name.is_(None)) | (Tender.source_url.is_(None)) | (Tender.source_record_id.is_(None))
        )
    ).all()
    violations.append(
        IntegrityViolation(
            code="missing_provenance", label="Tenders missing source name/url/id",
            count=len(missing_prov_rows), severity="critical",
            examples=[r[0] for r in missing_prov_rows[:_EXAMPLE_LIMIT]],
        )
    )

    # hash mismatch — content_hash != recompute(url).
    hash_rows = db.execute(
        select(Document.id, Document.url, Document.content_hash).where(
            Document.url.is_not(None), Document.content_hash.is_not(None)
        )
    ).all()
    mismatches = [str(did) for did, url, stored in hash_rows if content_hash(url) != stored]
    violations.append(
        IntegrityViolation(code="hash_mismatch", label="Documents whose content hash != URL recompute",
                           count=len(mismatches), severity="critical", examples=mismatches[:_EXAMPLE_LIMIT])
    )

    # duplicate evidence — same evidence_hash on multiple document rows.
    dup_rows = db.execute(
        select(Document.evidence_hash, func.count(Document.id))
        .where(Document.evidence_hash.is_not(None))
        .group_by(Document.evidence_hash)
        .having(func.count(Document.id) > 1)
    ).all()
    dup_extra = sum(int(c) - 1 for _, c in dup_rows)
    violations.append(IntegrityViolation(code="duplicate_evidence", label="Evidence rows sharing an evidence hash", count=dup_extra, severity="warning"))

    # orphan evidence — documents whose tender_id does not resolve.
    orphan_rows = db.execute(
        select(Document.id)
        .outerjoin(Tender, Document.tender_id == Tender.id)
        .where(Document.tender_id.is_not(None), Tender.id.is_(None))
    ).all()
    violations.append(IntegrityViolation(code="orphan_evidence", label="Documents with an unresolved tender link", count=len(orphan_rows), severity="critical"))

    # version conflicts — same (source, source_record_id, url) with differing content hashes.
    conflict_rows = db.execute(
        select(Document.source_name, Document.source_record_id, Document.url, Document.content_hash).where(
            Document.url.is_not(None)
        )
    ).all()
    groups: dict[tuple, set] = defaultdict(set)
    for source_name, source_record_id, url, chash in conflict_rows:
        groups[(source_name, source_record_id, url)].add(chash)
    conflicts = sum(1 for hashes in groups.values() if len(hashes) > 1)
    violations.append(IntegrityViolation(code="evidence_version_conflicts", label="Evidence with conflicting content hashes", count=conflicts, severity="warning"))

    return violations


def _fully_traceable_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(func.distinct(Tender.id)))
            .select_from(Tender)
            .join(Document, Document.tender_id == Tender.id)
            .where(
                Tender.source_name.is_not(None),
                Tender.source_record_id.is_not(None),
                Tender.source_url.is_not(None),
                Tender.retrieved_at.is_not(None),
                Document.url.is_not(None),
                Document.content_hash.is_not(None),
                Document.evidence_hash.is_not(None),
            )
        )
        or 0
    )


def _tender_check(db, code, label, column, total) -> IntegrityCheck:
    present = int(db.scalar(select(func.count(Tender.id)).where(column.is_not(None))) or 0)
    return _check(code, label, present, total)


def _doc_check(db, code, label, column, total) -> IntegrityCheck:
    present = int(db.scalar(select(func.count(Document.id)).where(column.is_not(None))) or 0)
    return _check(code, label, present, total)


def _version_check(db, code, label, column, total) -> IntegrityCheck:
    present = int(db.scalar(select(func.count(SourceRecordVersion.id)).where(column.is_not(None))) or 0)
    return _check(code, label, present, total)


def _check(code: str, label: str, present: int, total: int) -> IntegrityCheck:
    ratio = round(present / total, 4) if total else 0.0
    return IntegrityCheck(code=code, label=label, present=present, total=total, ratio=ratio, complete=(present == total and total > 0))


def _score(checks: list[IntegrityCheck]) -> float:
    applicable = [c for c in checks if c.total > 0]
    return round(sum(c.ratio for c in applicable) / len(applicable), 4) if applicable else 0.0
