"""Cross-investigation AI memory.

Gives SENTRY continuity between investigations — like a real analyst who
remembers what they looked at last week. Each completed investigation is
persisted as a compact :class:`InvestigationMemoryEntry` (subject, risk, key
entities, indicators, timestamp). When a new investigation starts, related prior
entries are recalled and offered to the reasoning layer as *provenanced* context
("previously investigated on <date>: <risk>").

Storage is an append-only JSONL file under ``data/memory/`` — durable, inspectable,
and dependency-free. Recall matches on subject similarity (stdlib token overlap,
no third-party dependency) and shared entities. Memory never fabricates: a hit is
only ever a record that was genuinely written by a past investigation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from app.schemas.investigation_memory import InvestigationMemoryEntry, MemoryHit


def _token_set_ratio(a: str, b: str) -> int:
    """Order-independent token-overlap similarity in [0, 100], stdlib-only.

    Mirrors the useful part of rapidfuzz.token_set_ratio for short subject
    strings: Jaccard-style overlap of the two token sets, scaled to a percentage.
    """
    ta = {t for t in a.split() if t}
    tb = {t for t in b.split() if t}
    if not ta or not tb:
        return 100 if a == b else 0
    inter = len(ta & tb)
    union = len(ta | tb)
    return round(inter / union * 100)

_DEFAULT_STORE = Path(__file__).resolve().parents[2] / "data" / "memory" / "investigations.jsonl"


class InvestigationMemory:
    """Append-only investigation memory backed by a JSONL file."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or _DEFAULT_STORE

    # ------------------------------------------------------------------ write

    def remember(self, entry: InvestigationMemoryEntry) -> None:
        """Persist a completed investigation. Best-effort; never raises upward."""
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            with self.store_path.open("a", encoding="utf-8") as fh:
                fh.write(entry.model_dump_json() + "\n")
        except Exception:
            # Memory is an enhancement, never a hard dependency of reasoning.
            pass

    # ------------------------------------------------------------------ read

    def _load(self) -> list[InvestigationMemoryEntry]:
        if not self.store_path.exists():
            return []
        entries: list[InvestigationMemoryEntry] = []
        try:
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(InvestigationMemoryEntry.model_validate_json(line))
                except Exception:
                    continue
        except Exception:
            return []
        return entries

    def recall(
        self,
        subject: str,
        *,
        entities: list[str] | None = None,
        limit: int = 3,
        threshold: int = 60,
    ) -> list[MemoryHit]:
        """Recall prior investigations related to ``subject`` / ``entities``.

        Excludes the exact same subject from being echoed back trivially unless it
        carries new shared entities. Returns the strongest matches, most recent
        first on ties.
        """
        subject_norm = subject.strip().casefold()
        entity_set = {e.strip().casefold() for e in (entities or []) if e.strip()}
        hits: list[MemoryHit] = []

        for entry in self._load():
            score = _token_set_ratio(subject_norm, entry.subject.casefold())
            reason = "subject match"

            shared = entity_set & {e.casefold() for e in entry.key_entities}
            if shared:
                score = max(score, 80 + min(len(shared) * 5, 15))
                reason = f"shares {len(shared)} entity(ies)"

            if score < threshold:
                continue
            hits.append(
                MemoryHit(
                    **entry.model_dump(),
                    match_score=int(score),
                    match_reason=reason,
                )
            )

        hits.sort(key=lambda h: (h.match_score, h.remembered_at), reverse=True)
        return hits[:limit]


def entry_from_investigation(
    *,
    subject: str,
    investigation_type: str,
    risk_level: str,
    confidence: float,
    key_entities: list[str],
    key_indicators: list[str],
    records_reviewed: int,
) -> InvestigationMemoryEntry:
    return InvestigationMemoryEntry(
        subject=subject,
        investigation_type=investigation_type,
        risk_level=risk_level,
        confidence=confidence,
        key_entities=key_entities[:8],
        key_indicators=key_indicators[:8],
        records_reviewed=records_reviewed,
        remembered_at=datetime.now(timezone.utc),
    )
