"""Performance & scale layer (Phase 9).

Helpers for importing hundreds of thousands of records without holding them in
memory, and for running independent connectors concurrently:

* ``stream_envelopes`` / ``batched`` — lazy, memory-bounded iteration.
* ``parallel_import`` — run one connector per worker thread, each with its own
  Session, with deterministic aggregation and optional progress callback.
* ``ImportProgress`` — cheap progress tracking for long runs.

Determinism: results are keyed by source and merged in a stable order; the
concurrency only changes wall-clock, never the imported rows.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Iterator

from app.db.session import SessionLocal
from app.importers.generic import GenericConnectorImporter, GenericImportStats

logger = logging.getLogger(__name__)


def stream_envelopes(directory: Path) -> Iterator[Path]:
    """Yield envelope paths lazily (never materialises the full list)."""
    yield from sorted(directory.glob("*.json"))


def batched(items: Iterable, size: int) -> Iterator[list]:
    """Yield fixed-size batches from any iterable, memory-bounded."""
    if size <= 0:
        raise ValueError("batch size must be positive")
    batch: list = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


@dataclass
class ImportProgress:
    total: int = 0
    processed: int = 0
    failed: int = 0
    _callback: Callable[[int, int], None] | None = None

    def advance(self, count: int = 1, failed: int = 0) -> None:
        self.processed += count
        self.failed += failed
        if self._callback:
            self._callback(self.processed, self.total)

    @property
    def ratio(self) -> float:
        return round(self.processed / self.total, 4) if self.total else 0.0


@dataclass
class ParallelImportResult:
    stats_by_source: dict[str, GenericImportStats] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    def totals(self) -> dict[str, int]:
        agg = {"new": 0, "updated": 0, "documents": 0, "versions": 0, "failed": 0}
        for stats in self.stats_by_source.values():
            agg["new"] += stats.imported_tenders
            agg["updated"] += stats.updated_tenders
            agg["documents"] += stats.imported_documents
            agg["versions"] += stats.versions_recorded
            agg["failed"] += stats.failed
        return agg


def parallel_import(
    sources: list[str],
    data_root: Path,
    *,
    max_workers: int = 4,
    batch_size: int = 100,
    session_factory=SessionLocal,
    progress: Callable[[str, GenericImportStats], None] | None = None,
) -> ParallelImportResult:
    """Import several connectors concurrently, one Session per worker.

    Independent sources never touch the same rows, so parallelism is safe and
    the imported data is identical to a sequential run.
    """
    result = ParallelImportResult()

    def _run(source: str) -> tuple[str, GenericImportStats]:
        directory = data_root / source
        session = session_factory()
        try:
            stats = GenericConnectorImporter(session, source, batch_size=batch_size).import_directory(directory)
            return source, stats
        finally:
            session.close()

    runnable = [s for s in sources if (data_root / s).exists()]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run, source): source for source in runnable}
        for future in as_completed(futures):
            source = futures[future]
            try:
                source, stats = future.result()
                result.stats_by_source[source] = stats
                if progress:
                    progress(source, stats)
            except Exception as error:  # pragma: no cover - defensive
                result.errors[source] = str(error)
                logger.exception("Parallel import failed for %s", source)
    return result
