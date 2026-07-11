"""Advanced incremental synchronization engine (Phase 6).

Adds enterprise sync semantics on top of the generic importer, all
deterministic and history-preserving:

* **Delta detection** — classify a directory of envelopes against the DB into
  new / updated / unchanged / deleted, WITHOUT importing (a dry-run plan).
* **Soft deletes** — mark tenders absent from a source's latest sync with
  ``deleted_at`` (and un-delete ones that reappear); rows are never removed.
* **Rollback** — restore a tender's fields from any prior
  ``SourceRecordVersion`` snapshot.
* **Retry queue** — deterministic bounded retry of failed files.
* **Conflict resolution** — latest-retrieved-wins, deterministic.

No record is ever duplicated; version history is always preserved.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.connectors.registry import discover_connectors
from app.importers.generic import _record_content_hash
from app.models import SourceRecordVersion, Tender

logger = logging.getLogger(__name__)


@dataclass
class DeltaPlan:
    source: str
    total_files: int = 0
    new: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        return {
            "total_files": self.total_files,
            "new": len(self.new),
            "updated": len(self.updated),
            "unchanged": len(self.unchanged),
            "deleted": len(self.deleted),
            "invalid": len(self.invalid),
        }


def plan_delta(db: Session, source: str, directory: Path) -> DeltaPlan:
    """Dry-run: classify each envelope vs the current DB state (no writes)."""
    connector = discover_connectors().get(source)
    if connector is None:
        raise ValueError(f"No connector registered for source '{source}'.")

    plan = DeltaPlan(source=source)
    seen_source_ids: set[str] = set()
    # Known content hashes for this source -> unchanged detection.
    known_hashes = {
        (row.source_record_id, row.content_hash)
        for row in db.execute(
            select(SourceRecordVersion.source_record_id, SourceRecordVersion.content_hash).where(
                SourceRecordVersion.source_name == source
            )
        )
    }
    known_ids = {sid for sid, _ in known_hashes}

    for path in sorted(directory.glob("*.json")):
        plan.total_files += 1
        try:
            with path.open("r", encoding="utf-8") as handle:
                envelope = json.load(handle)
            record = connector.normalize(envelope)
        except Exception:
            plan.invalid.append(path.name)
            continue
        source_id = record.tender.metadata.source_record_id
        seen_source_ids.add(source_id)
        record_hash = _record_content_hash(record)
        if (source_id, record_hash) in known_hashes:
            plan.unchanged.append(source_id)
        elif source_id in known_ids:
            plan.updated.append(source_id)
        else:
            plan.new.append(source_id)

    # Deleted = source records previously imported but absent from this sync.
    db_ids = {
        row[0]
        for row in db.execute(
            select(Tender.source_record_id).where(
                Tender.source_name == source, Tender.source_record_id.is_not(None), Tender.deleted_at.is_(None)
            )
        )
    }
    plan.deleted = sorted(db_ids - seen_source_ids)
    return plan


def synchronize_deletions(db: Session, source: str, present_source_ids: set[str], *, commit: bool = True) -> dict[str, int]:
    """Soft-delete tenders absent from ``present_source_ids``; un-delete returnees."""
    now = now_utc()
    soft_deleted = 0
    restored = 0
    for tender in db.scalars(
        select(Tender).where(Tender.source_name == source, Tender.source_record_id.is_not(None))
    ):
        present = tender.source_record_id in present_source_ids
        if not present and tender.deleted_at is None:
            tender.deleted_at = now
            soft_deleted += 1
        elif present and tender.deleted_at is not None:
            tender.deleted_at = None
            restored += 1
    if commit:
        db.commit()
    return {"soft_deleted": soft_deleted, "restored": restored}


def rollback_to_version(db: Session, version_id, *, commit: bool = True) -> bool:
    """Restore a tender's mutable fields from a prior version snapshot."""
    version = db.get(SourceRecordVersion, version_id)
    if version is None or not isinstance(version.snapshot_json, dict):
        return False
    snapshot = version.snapshot_json.get("tender") if version.snapshot_json else None
    if not snapshot:
        return False
    tender = db.scalar(
        select(Tender).where(
            Tender.source_name == version.source_name,
            Tender.source_record_id == version.source_record_id,
        )
    )
    if tender is None:
        return False
    if snapshot.get("title"):
        tender.title = snapshot["title"]
    if snapshot.get("buyer") is not None:
        tender.procuring_entity = snapshot["buyer"]
    if snapshot.get("currency"):
        tender.currency = snapshot["currency"]
    if commit:
        db.commit()
    return True


def resolve_conflict(existing_retrieved_at, incoming_retrieved_at) -> str:
    """Deterministic conflict policy: newer retrieval wins; ties -> incoming."""
    if existing_retrieved_at is None:
        return "incoming"
    if incoming_retrieved_at is None:
        return "existing"
    return "incoming" if incoming_retrieved_at >= existing_retrieved_at else "existing"


@dataclass
class RetryQueue:
    """Deterministic bounded retry queue for failed import items."""

    max_retries: int = 3
    _queue: deque = field(default_factory=deque)
    _attempts: dict = field(default_factory=dict)
    dropped: list = field(default_factory=list)

    def add(self, item: str) -> None:
        self._queue.append(item)
        self._attempts.setdefault(item, 0)

    def __len__(self) -> int:
        return len(self._queue)

    def next(self):
        return self._queue.popleft() if self._queue else None

    def mark_failed(self, item: str) -> bool:
        """Record a failure; re-enqueue if under the retry cap. Returns True if re-queued."""
        self._attempts[item] = self._attempts.get(item, 0) + 1
        if self._attempts[item] < self.max_retries:
            self._queue.append(item)
            return True
        self.dropped.append(item)
        return False

    def attempts(self, item: str) -> int:
        return self._attempts.get(item, 0)
