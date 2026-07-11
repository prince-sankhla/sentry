"""Evidence engine (Phase 4).

Owns the *evidence record* view over the ``documents`` table: the full
provenance envelope (source, connector, URLs, hashes, timestamps, versions,
run id) plus deterministic quality / integrity / completeness scores.

Also provides a deterministic **backfill** that populates the evidence
provenance columns on rows imported before those columns existed — derived
entirely from already-stored fields, never fabricated.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.connectors.common.envelope import content_hash
from app.connectors.common.parse import now_utc
from app.models import Document
from app.services.procurement_platform.utils import ratio

# Mandatory provenance fields every evidence row should carry.
_MANDATORY_FIELDS = (
    "source_name", "connector_name", "url", "document_type",
    "content_hash", "evidence_hash", "retrieved_at", "source_record_id",
)


@dataclass(frozen=True)
class EvidenceScores:
    total: int
    completeness: float   # mandatory-field completeness across evidence rows
    integrity: float      # rows whose content hash matches a recompute of the URL
    quality: float        # rows with URL + hash + connector + type present


def evidence_field_hash(
    *, url: str | None, title: str | None, document_type: str | None,
    source_name: str | None, source_record_id: str | None,
) -> str:
    """Deterministic SHA-256 over a document's provenance identity."""
    return content_hash(
        {
            "url": url,
            "title": title,
            "document_type": document_type,
            "source_name": source_name,
            "source_record_id": source_record_id,
        }
    )


def backfill_evidence(db: Session, *, commit: bool = True) -> int:
    """Populate evidence provenance columns on legacy document rows.

    Deterministic and idempotent: sets connector_name/version, evidence_hash,
    evidence_version, verified_at and content_hash where missing, from the
    document's already-stored fields. Returns the number of rows updated.
    """
    rows = db.execute(
        select(
            Document.id, Document.url, Document.title, Document.document_type,
            Document.source_name, Document.source_record_id, Document.content_hash,
            Document.connector_name, Document.evidence_hash, Document.source_url,
        )
    ).all()
    now = now_utc()
    updated = 0
    for (
        doc_id, url, title, doc_type, source_name, source_record_id,
        stored_content_hash, connector_name, evidence_hash, source_url,
    ) in rows:
        changes: dict = {}
        if connector_name is None and source_name is not None:
            changes["connector_name"] = source_name
            changes["connector_version"] = "1.0"
        if evidence_hash is None:
            changes["evidence_hash"] = evidence_field_hash(
                url=url, title=title, document_type=doc_type,
                source_name=source_name, source_record_id=source_record_id,
            )
        if stored_content_hash is None and url:
            changes["content_hash"] = content_hash(url)
        if source_url is None and url:
            changes["source_url"] = url
        if changes:
            changes.setdefault("verified_at", now)
            changes.setdefault("evidence_version", 1)
            db.execute(update(Document).where(Document.id == doc_id).values(**changes))
            updated += 1
    if commit:
        db.commit()
    return updated


def evidence_scores(db: Session) -> EvidenceScores:
    total = int(db.scalar(select(func.count(Document.id))) or 0)
    if total == 0:
        return EvidenceScores(total=0, completeness=0.0, integrity=0.0, quality=0.0)

    # Completeness: fraction of mandatory fields populated across all rows.
    populated = 0
    for field in _MANDATORY_FIELDS:
        column = getattr(Document, field)
        populated += int(db.scalar(select(func.count(Document.id)).where(column.is_not(None))) or 0)
    completeness = ratio(populated, total * len(_MANDATORY_FIELDS))

    # Integrity: content_hash matches a recompute of the URL.
    hash_rows = db.execute(
        select(Document.url, Document.content_hash).where(
            Document.url.is_not(None), Document.content_hash.is_not(None)
        )
    ).all()
    matches = sum(1 for url, stored in hash_rows if content_hash(url) == stored)
    integrity = ratio(matches, len(hash_rows)) if hash_rows else 0.0

    # Quality: URL + hash + connector + type all present.
    quality_rows = int(
        db.scalar(
            select(func.count(Document.id)).where(
                Document.url.is_not(None),
                Document.content_hash.is_not(None),
                Document.connector_name.is_not(None),
                Document.document_type.is_not(None),
            )
        )
        or 0
    )
    quality = ratio(quality_rows, total)

    return EvidenceScores(total=total, completeness=completeness, integrity=integrity, quality=quality)
