"""Verified Context Engine — Phase 1 foundation tests.

The Phase 1 contract: local Context Store first; empty/no-match ⇒ "Context
unavailable"; only verified cards are ever served; providers are pluggable and
never invent; the subsystem changes no existing behaviour.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.verified_context import (
    CONTEXT_UNAVAILABLE,
    ContextCard,
    ContextProvider,
    ContextQuery,
    ContextResolution,
    ContextStore,
    LocalStoreProvider,
    VerifiedContextEngine,
)


def _tmp_store() -> ContextStore:
    return ContextStore(Path(tempfile.mkdtemp()) / "context_cards.json")


def _card(card_id="gfr-single-bid-retender", status="verified", **kw) -> ContextCard:
    defaults = dict(
        title="Single bid acceptable after re-tender (GFR)",
        summary="GFR 2017 permits accepting a single responsive bid when the tender was re-floated.",
        applies_to_indicators=["single_bidder"],
        verification_questions=["Was the tender re-floated before award?"],
    )
    defaults.update(kw)
    return ContextCard(card_id=card_id, status=status, **defaults)


class EmptyLibraryTest(unittest.TestCase):
    def test_empty_store_returns_context_unavailable(self) -> None:
        engine = VerifiedContextEngine([LocalStoreProvider(_tmp_store())])
        res = engine.resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertFalse(res.available)
        self.assertEqual(res.message, CONTEXT_UNAVAILABLE)
        self.assertEqual(res.cards, [])

    def test_default_store_missing_file_is_safe(self) -> None:
        store = ContextStore(Path(tempfile.mkdtemp()) / "does-not-exist.json")
        self.assertEqual(store.load(), [])


class LocalStoreProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _tmp_store()
        self.engine = VerifiedContextEngine([LocalStoreProvider(self.store)])

    def test_verified_card_is_served_for_its_indicator(self) -> None:
        self.store.upsert(_card())
        res = self.engine.resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertTrue(res.available)
        self.assertEqual(res.cards[0].card_id, "gfr-single-bid-retender")
        self.assertEqual(res.provider, "local_store")

    def test_draft_and_retired_cards_are_never_served(self) -> None:
        self.store.upsert(_card("draft-card", status="draft"))
        self.store.upsert(_card("retired-card", status="retired"))
        res = self.engine.resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertFalse(res.available)
        self.assertEqual(res.message, CONTEXT_UNAVAILABLE)

    def test_indicator_mismatch_is_unavailable(self) -> None:
        self.store.upsert(_card())
        res = self.engine.resolve(ContextQuery(indicator_id="contract_fragmentation"))
        self.assertFalse(res.available)

    def test_jurisdiction_scoping(self) -> None:
        self.store.upsert(_card(jurisdictions=["IN-OD"]))
        self.assertTrue(self.engine.resolve(ContextQuery(indicator_id="single_bidder", jurisdiction="IN-OD")).available)
        self.assertFalse(self.engine.resolve(ContextQuery(indicator_id="single_bidder", jurisdiction="IN-KA")).available)
        # Unscoped query matches a scoped card is NOT allowed to fail silently:
        # a card with declared scope still serves an unscoped query.
        self.assertTrue(self.engine.resolve(ContextQuery(indicator_id="single_bidder")).available)

    def test_upsert_replaces_by_card_id(self) -> None:
        self.store.upsert(_card(summary="v1"))
        self.store.upsert(_card(summary="v2"))
        cards = self.store.load()
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].summary, "v2")


class ProviderPluginTest(unittest.TestCase):
    def test_providers_run_in_priority_order_first_available_wins(self) -> None:
        class StubProvider(ContextProvider):
            def __init__(self, name, priority, available):
                self.name, self.priority, self._available = name, priority, available
            def resolve(self, query):
                if self._available:
                    return ContextResolution(available=True, cards=[_card()], provider=self.name)
                return ContextResolution(available=False, message=CONTEXT_UNAVAILABLE, provider=self.name)

        engine = VerifiedContextEngine([
            StubProvider("second", 10, True),
            StubProvider("first", 0, False),   # library first, finds nothing
        ])
        res = engine.resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertTrue(res.available)
        self.assertEqual(res.provider, "second")  # fell through to the next provider

    def test_failing_provider_never_breaks_resolution(self) -> None:
        class BrokenProvider(ContextProvider):
            name, priority = "broken", 0
            def resolve(self, query):
                raise RuntimeError("boom")

        engine = VerifiedContextEngine([BrokenProvider(), LocalStoreProvider(_tmp_store())])
        res = engine.resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertFalse(res.available)
        self.assertEqual(res.message, CONTEXT_UNAVAILABLE)


class NoBehaviourChangeTest(unittest.TestCase):
    def test_subsystem_is_not_wired_into_the_investigation_pipeline(self) -> None:
        # Phase 1 is foundation only: nothing in the reasoning/risk pipeline
        # imports the verified-context subsystem yet.
        import app.services.investigation_reasoning as reasoning
        import app.services.risk_engine as risk
        import inspect

        for module in (reasoning, risk):
            self.assertNotIn("verified_context", inspect.getsource(module))


if __name__ == "__main__":
    unittest.main()
