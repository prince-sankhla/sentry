"""Phase 3 — Procurement Context Analyzer tests.

Contract: fixed presentation sections; guidance selected only when its declared
applicability covers the finding; authority/document/citation fields preserved
verbatim; the fixed no-guidance message when nothing relevant exists (never
fabricated context); deterministic; read-only over findings; nothing persisted.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.verified_context import (
    NO_GUIDANCE_MESSAGE,
    ContextCard,
    ContextStore,
    LocalStoreProvider,
    ProcurementContextAnalyzer,
    TrustedRetrievalProvider,
    VerifiedContextEngine,
)


def _finding(fid="award_clustering", name="Rapid Repeat Procurement"):
    return SimpleNamespace(id=fid, name=name)


def _analyzer(store: ContextStore | None = None) -> ProcurementContextAnalyzer:
    store = store or ContextStore(Path(tempfile.mkdtemp()) / "cards.json")
    return ProcurementContextAnalyzer(
        VerifiedContextEngine([LocalStoreProvider(store), TrustedRetrievalProvider()])
    )


class SectionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.analysis = _analyzer().analyze(_finding())

    def test_all_required_sections_present(self) -> None:
        a = self.analysis
        self.assertEqual(a.finding_name, "Rapid Repeat Procurement")
        self.assertTrue(a.guidance_available)
        self.assertTrue(a.potential_context)                       # Potential Procurement Context
        for item in a.guidance:
            self.assertTrue(item.supporting_guidance)              # Supporting Guidance
            self.assertTrue(item.supporting_sources)               # Supporting Sources
            self.assertTrue(item.source_type)                      # Source Type
            self.assertTrue(item.authority)                        # Authority
            self.assertTrue(item.reference)                        # Reference
            self.assertTrue(item.applicability)                    # Applicability
        self.assertIn("plausible administrative explanation", a.current_assessment)  # Current Assessment
        self.assertTrue(a.additional_evidence_required)            # Additional Evidence Required

    def test_award_clustering_surfaces_fy_end_guidance_with_gfr_authority(self) -> None:
        refs = " ".join(i.reference for i in self.analysis.guidance)
        self.assertIn("General Financial Rules", refs)
        types = {i.source_type for i in self.analysis.guidance}
        self.assertIn("Government Procurement Rule", types)

    def test_no_opinions_or_conclusions(self) -> None:
        blob = (self.analysis.potential_context + self.analysis.current_assessment).lower()
        for banned in ("corruption", "wrongdoing", "this is normal", "innocent", "guilty"):
            self.assertNotIn(banned, blob)
        self.assertIn("does not, by itself, confirm or exclude", self.analysis.current_assessment)


class NoGuidanceTest(unittest.TestCase):
    def test_fixed_message_when_no_relevant_guidance(self) -> None:
        a = _analyzer().analyze(_finding("gst_overlap", "GST Overlap"))
        self.assertFalse(a.guidance_available)
        self.assertEqual(a.potential_context, NO_GUIDANCE_MESSAGE)
        self.assertEqual(a.current_assessment, NO_GUIDANCE_MESSAGE)
        self.assertEqual(a.guidance, [])
        self.assertEqual(a.additional_evidence_required, [])


class PreservationTest(unittest.TestCase):
    def test_verified_library_card_fields_pass_through_verbatim(self) -> None:
        store = ContextStore(Path(tempfile.mkdtemp()) / "cards.json")
        store.upsert(ContextCard(
            card_id="v-1", title="CVC Circular 4/3/07", status="verified",
            summary="Works must not be split to avoid higher sanction.",
            applies_to_indicators=["contract_fragmentation"],
            verification_questions=["Was aggregate sanction taken?"],
            sources=[{"title": "CVC Circular 4/3/07", "url": "https://cvc.gov.in",
                      "publisher": "Central Vigilance Commission"}],
        ))
        a = _analyzer(store).analyze(_finding("contract_fragmentation", "Potential Contract Fragmentation"))
        self.assertEqual(a.resolved_by, "local_store")             # library first
        item = a.guidance[0]
        self.assertEqual(item.supporting_guidance, "Works must not be split to avoid higher sanction.")
        self.assertEqual(item.reference, "CVC Circular 4/3/07")    # document reference verbatim
        self.assertEqual(item.authority, "Central Vigilance Commission")
        self.assertEqual(item.source_type, "Vigilance Guidance")
        self.assertEqual(item.card_status, "verified")
        self.assertEqual(a.additional_evidence_required, ["Was aggregate sanction taken?"])


class ReadOnlyAndDeterminismTest(unittest.TestCase):
    def test_finding_object_is_never_mutated(self) -> None:
        finding = _finding()
        before = dict(vars(finding))
        _analyzer().analyze(finding)
        self.assertEqual(vars(finding), before)

    def test_nothing_is_persisted(self) -> None:
        store = ContextStore(Path(tempfile.mkdtemp()) / "cards.json")
        _analyzer(store).analyze(_finding())
        self.assertEqual(store.load(), [])                         # no caching, no saving

    def test_analysis_is_deterministic(self) -> None:
        a1 = _analyzer().analyze(_finding())
        a2 = _analyzer().analyze(_finding())
        self.assertEqual(a1.model_dump(), a2.model_dump())


class EndpointTest(unittest.TestCase):
    def test_read_only_endpoint(self) -> None:
        import warnings

        warnings.filterwarnings("ignore")
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        res = client.get(
            "/api/investigations/context-analysis",
            params={"finding_id": "single_bidder", "finding_name": "Single Bidder"},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["guidance_available"])
        self.assertTrue(all(g["card_status"] == "draft" for g in body["guidance"]))

        missing = client.get(
            "/api/investigations/context-analysis", params={"finding_id": "gst_overlap"}
        ).json()
        self.assertEqual(missing["potential_context"], NO_GUIDANCE_MESSAGE)


if __name__ == "__main__":
    unittest.main()
