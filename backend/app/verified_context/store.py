"""Context Store — durable, inspectable persistence for Context Cards.

JSON-file backed (one file, list of cards), matching SENTRY's existing
dependency-free storage style (cf. investigation memory). The store is the
single source of truth for the Verified Context Library:

  * Phase 1 — ships empty; reads return nothing.
  * Phase 2 — Draft cards land here after trusted retrieval.
  * Phase 3 — verification flips ``status`` to ``verified``; only verified
    cards are served to investigations.

The store is deliberately dumb: querying/filtering intelligence lives in the
providers, review workflows live in future phases.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.verified_context.schema import ContextCard

_DEFAULT_STORE = Path(__file__).resolve().parents[2] / "data" / "context" / "context_cards.json"


class ContextStore:
    """JSON-file backed Context Card store."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or _DEFAULT_STORE

    # ------------------------------------------------------------------ read

    def load(self) -> list[ContextCard]:
        """All cards, regardless of status. Missing/corrupt file ⇒ empty list."""
        if not self.store_path.exists():
            return []
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if not isinstance(payload, list):
            return []
        cards: list[ContextCard] = []
        for entry in payload:
            try:
                cards.append(ContextCard.model_validate(entry))
            except Exception:
                continue  # a malformed card never breaks the library
        return cards

    def get(self, card_id: str) -> ContextCard | None:
        return next((c for c in self.load() if c.card_id == card_id), None)

    # ----------------------------------------------------------------- write

    def upsert(self, card: ContextCard) -> None:
        """Insert or replace a card by ``card_id`` (atomic rewrite)."""
        cards = [c for c in self.load() if c.card_id != card.card_id]
        cards.append(card)
        self._write(cards)

    def _write(self, cards: list[ContextCard]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [json.loads(c.model_dump_json()) for c in cards]
        tmp = self.store_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.store_path)
