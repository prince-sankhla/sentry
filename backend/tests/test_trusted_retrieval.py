"""Phase 2 — Trusted Context Retrieval tests.

Contract under test: local library first; trusted retrieval only on a miss;
results are Draft cards with citations + verification questions; nothing is
persisted or auto-verified; unknown topics stay honestly unavailable (never
invented); retrieval is deterministic; only allowlisted authorities appear.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.verified_context import (
    CONTEXT_UNAVAILABLE,
    ContextCard,
    ContextQuery,
    ContextStore,
    LocalStoreProvider,
    TrustedRetrievalProvider,
    VerifiedContextEngine,
    is_trusted_domain,
)
from app.verified_context.trusted import _GUIDANCE_CORPUS, TRUSTED_AUTHORITIES


def _tmp_store() -> ContextStore:
    return ContextStore(Path(tempfile.mkdtemp()) / "context_cards.json")


def _engine(store: ContextStore) -> VerifiedContextEngine:
    return VerifiedContextEngine([LocalStoreProvider(store), TrustedRetrievalProvider()])


class WorkflowOrderTest(unittest.TestCase):
    def test_verified_local_card_returns_immediately_without_retrieval(self) -> None:
        store = _tmp_store()
        store.upsert(ContextCard(
            card_id="verified-single-bid", title="Verified card", summary="Library knowledge.",
            applies_to_indicators=["single_bidder"], status="verified",
        ))
        res = _engine(store).resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertTrue(res.available)
        self.assertEqual(res.provider, "local_store")           # step 2: returned immediately
        self.assertEqual(res.cards[0].status, "verified")

    def test_local_miss_falls_through_to_trusted_retrieval(self) -> None:
        res = _engine(_tmp_store()).resolve(ContextQuery(indicator_id="single_bidder"))
        self.assertTrue(res.available)
        self.assertEqual(res.provider, "trusted_retrieval")     # steps 3-6
        self.assertTrue(all(c.status == "draft" for c in res.cards))
        self.assertIn("requires verification", res.message)


class DraftCardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _tmp_store()
        self.res = _engine(self.store).resolve(ContextQuery(indicator_id="contract_fragmentation"))

    def test_draft_carries_citations_and_questions(self) -> None:
        self.assertTrue(self.res.available)
        for card in self.res.cards:
            self.assertEqual(card.status, "draft")              # never auto-verified
            self.assertTrue(card.sources)                       # citations preserved
            for src in card.sources:
                self.assertTrue(src.publisher and src.url)
            self.assertTrue(card.verification_questions)        # questions included
            self.assertIsNone(card.verified_at)

    def test_drafts_are_never_persisted(self) -> None:
        self.assertEqual(self.store.load(), [])                 # store untouched

    def test_cvc_guidance_reaches_fragmentation(self) -> None:
        publishers = {s.publisher for c in self.res.cards for s in c.sources}
        self.assertTrue(any("Central Vigilance Commission" in p for p in publishers))


class NeverInventTest(unittest.TestCase):
    def test_unknown_topic_stays_unavailable(self) -> None:
        # No trusted guidance is curated for related-party overlaps → honest miss.
        res = _engine(_tmp_store()).resolve(ContextQuery(indicator_id="gst_overlap"))
        self.assertFalse(res.available)
        self.assertEqual(res.message, CONTEXT_UNAVAILABLE)

    def test_every_corpus_entry_cites_an_allowlisted_authority(self) -> None:
        for entry in _GUIDANCE_CORPUS:
            self.assertIn(entry.authority_key, TRUSTED_AUTHORITIES)
            authority = TRUSTED_AUTHORITIES[entry.authority_key]
            self.assertTrue(is_trusted_domain(authority.url))

    def test_untrusted_domains_are_rejected(self) -> None:
        for url in ("https://random-blog.example.com/gfr", "https://forum.example.org", "https://cvc.gov.in.evil.com"):
            self.assertFalse(is_trusted_domain(url))
        for url in ("https://cvc.gov.in/guidance", "https://standard.open-contracting.org/latest"):
            self.assertTrue(is_trusted_domain(url))


class DeterminismTest(unittest.TestCase):
    def test_retrieval_is_deterministic(self) -> None:
        q = ContextQuery(indicator_id="repeat_supplier")
        r1 = _engine(_tmp_store()).resolve(q)
        r2 = _engine(_tmp_store()).resolve(q)
        strip = lambda r: [c.model_dump(exclude={"created_at"}) for c in r.cards]
        self.assertEqual(strip(r1), strip(r2))
        self.assertEqual([c.card_id for c in r1.cards], sorted(c.card_id for c in r1.cards))


class NoBehaviourChangeTest(unittest.TestCase):
    def test_investigation_pipeline_still_does_not_import_verified_context(self) -> None:
        import inspect

        import app.services.investigation_reasoning as reasoning
        import app.services.risk_engine as risk

        for module in (reasoning, risk):
            self.assertNotIn("verified_context", inspect.getsource(module))


if __name__ == "__main__":
    unittest.main()
