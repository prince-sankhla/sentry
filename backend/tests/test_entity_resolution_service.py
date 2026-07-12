from __future__ import annotations

import unittest
from uuid import uuid4

from app.services.entity_resolution_service import _decide, _score_candidate
from app.entity_resolution.normalizer import company_tokens, normalize_company_name


class _FakeCompany:
    """Minimal stand-in for a Company row (no DB)."""

    def __init__(self, name: str, registration_number: str | None = None, source_name: str | None = "cppp"):
        self.id = uuid4()
        self.name = name
        self.registration_number = registration_number
        self.source_name = source_name


def _score(query: str, company: _FakeCompany):
    return _score_candidate(query, normalize_company_name(query), company_tokens(query), company)


class ScoreCandidateTest(unittest.TestCase):
    def test_exact_name_scores_top(self) -> None:
        c = _score("Tata Steel Ltd", _FakeCompany("Tata Steel Ltd"))
        self.assertIsNotNone(c)
        self.assertEqual(c.match_type, "exact")
        self.assertEqual(c.score, 100)

    def test_official_name_prefix_match(self) -> None:
        # "Tata Projects" ⊆ "Tata Projects Ltd" -> official_name
        c = _score("Tata Projects", _FakeCompany("Tata Projects Ltd"))
        self.assertIsNotNone(c)
        self.assertIn(c.match_type, {"official_name", "exact", "alias"})

    def test_registration_match(self) -> None:
        c = _score("L28920MH1945PLC004520", _FakeCompany("Tata Steel Ltd", "L28920MH1945PLC004520"))
        self.assertIsNotNone(c)
        self.assertEqual(c.match_type, "registration")

    def test_unrelated_company_does_not_match(self) -> None:
        # Query "Tata" must not match an unrelated company.
        self.assertIsNone(_score("Tata", _FakeCompany("Reliance Industries Ltd")))

    def test_partial_family_name_matches_each_member(self) -> None:
        # "Tata" should match each Tata* entity (so they can be disambiguated).
        for name in ("Tata Steel Ltd", "Tata Motors Ltd", "Tata Power Ltd"):
            self.assertIsNotNone(_score("Tata", _FakeCompany(name)), name)

    def test_singular_query_resolves_to_plural_name(self) -> None:
        # BUG 1 regression: "Tata Project" (singular) must resolve to
        # "Tata Projects Ltd", not return zero candidates.
        c = _score("Tata Project", _FakeCompany("Tata Projects Ltd"))
        self.assertIsNotNone(c)
        self.assertIn(c.match_type, {"official_name", "alias", "exact"})

    def test_singular_query_does_not_match_unrelated_tata(self) -> None:
        # "Tata Project" must NOT pull in Tata Steel / Tata Motors.
        self.assertIsNone(_score("Tata Project", _FakeCompany("Tata Steel Ltd")))
        self.assertIsNone(_score("Tata Project", _FakeCompany("Tata Motors Ltd")))

    def test_plural_query_reaches_singular_name(self) -> None:
        # Symmetric: "Tata Projects" should still match a singular official name.
        c = _score("Tata Projects", _FakeCompany("Tata Project Ltd"))
        self.assertIsNotNone(c)


class DecideTest(unittest.TestCase):
    def _cands(self, query: str, names: list[str]):
        cands = []
        for n in names:
            c = _score(query, _FakeCompany(n))
            if c is not None:
                cands.append(c)
        cands.sort(key=lambda c: (c.score, c.confidence), reverse=True)
        return cands

    def test_ambiguous_family_requires_disambiguation(self) -> None:
        cands = self._cands("Tata", ["Tata Steel Ltd", "Tata Motors Ltd", "Tata Power Ltd", "Tata Projects Ltd"])
        result = _decide("Tata", normalize_company_name("Tata"), cands)
        self.assertTrue(result.requires_disambiguation)
        self.assertFalse(result.resolved)
        self.assertGreaterEqual(len(result.candidates), 3)

    def test_exact_single_match_resolves(self) -> None:
        cands = self._cands("Tata Steel Ltd", ["Tata Steel Ltd", "Tata Motors Ltd"])
        result = _decide("Tata Steel Ltd", normalize_company_name("Tata Steel Ltd"), cands)
        self.assertTrue(result.resolved)
        self.assertFalse(result.requires_disambiguation)
        self.assertIsNotNone(result.selected_entity_id)

    def test_never_merges_unrelated_entities(self) -> None:
        # The candidates must remain separate entities, never merged into one.
        cands = self._cands("Tata", ["Tata Steel Ltd", "Tata Motors Ltd"])
        result = _decide("Tata", normalize_company_name("Tata"), cands)
        ids = {c.entity_id for c in result.candidates}
        self.assertEqual(len(ids), len(result.candidates))


class BuyerResolutionTest(unittest.TestCase):
    """A government buyer (procuring_entity) is a valid canonical entity too."""

    def test_buyer_first_segment_strips_pipe_hierarchy(self) -> None:
        from app.services.entity_resolution_service import _buyer_first_segment, _buyer_segments
        self.assertEqual(
            _buyer_first_segment("Delhi University||Central Office - DU||Engineering - DU"),
            "Delhi University",
        )
        self.assertEqual(_buyer_first_segment("Tata Memorial Centre"), "Tata Memorial Centre")
        # Segments expose acronym/department aliases (e.g. "NHAI").
        self.assertEqual(
            _buyer_segments("National Highways Authority of India||NHAI||PIU"),
            ["National Highways Authority of India", "NHAI", "PIU"],
        )

    def test_score_buyer_exact(self) -> None:
        from app.services.entity_resolution_service import _score_buyer
        c = _score_buyer("Delhi University", normalize_company_name("Delhi University"),
                         company_tokens("Delhi University"), "Delhi University", [], 5)
        self.assertIsNotNone(c)
        self.assertEqual(c.entity_type, "government_buyer")
        self.assertEqual(c.match_type, "exact")
        self.assertEqual(c.tender_count, 5)

    def test_score_buyer_matches_acronym_alias(self) -> None:
        # "NHAI" resolves the buyer whose canonical name is the full organisation.
        from app.services.entity_resolution_service import _score_buyer
        c = _score_buyer("NHAI", normalize_company_name("NHAI"), company_tokens("NHAI"),
                         "National Highways Authority of India", ["NHAI", "PIU"], 6)
        self.assertIsNotNone(c)
        self.assertEqual(c.canonical_name, "National Highways Authority of India")
        self.assertEqual(c.entity_type, "government_buyer")

    def test_score_buyer_rejects_unrelated(self) -> None:
        # "Delhi University" must NOT match "University of Calcutta" (shared word only).
        from app.services.entity_resolution_service import _score_buyer
        c = _score_buyer("Delhi University", normalize_company_name("Delhi University"),
                         company_tokens("Delhi University"), "University of Calcutta", [], 3)
        self.assertIsNone(c)

    def test_acronym_query_forms_expand(self) -> None:
        from app.services.entity_resolution_service import _query_forms
        self.assertIn("Bharat Heavy Electricals", _query_forms("BHEL"))
        self.assertIn("National Highways Authority of India", _query_forms("NHAI"))
        # A non-acronym query is returned unchanged (single form).
        self.assertEqual(_query_forms("Tata Projects"), ["Tata Projects"])


class PrecisionPredicateSmokeTest(unittest.TestCase):
    """The precision SQL expressions must compile against the Tender mapping."""

    def test_entity_matches_compiles(self) -> None:
        from sqlalchemy.dialects import postgresql
        from app.services.search_query import entity_matches, entity_relevance_score

        clause = entity_matches("Tata Projects", aliases=["Tata Projects Ltd"])
        sql = str(clause.compile(dialect=postgresql.dialect()))
        self.assertIn("tenders", sql.lower())
        rel = entity_relevance_score("Tata Projects")
        self.assertTrue(str(rel.compile(dialect=postgresql.dialect())))

    def test_entity_matches_has_no_loose_trigram_buyer_guard(self) -> None:
        # BUG 2 regression: the trigram fuzzy buyer guard (procuring_entity % name)
        # dragged in unrelated buyers sharing a common word. It must be gone so
        # precision comes from the direct name match + all-tokens conjunction.
        from sqlalchemy.dialects import postgresql
        from app.services.search_query import entity_matches

        sql = str(
            entity_matches("Delhi University", aliases=["Delhi University"])
            .compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
        )
        # The trigram MATCH operator "%%" (escaped) must not appear as a buyer guard.
        self.assertNotIn("procuring_entity %", sql.replace("%%", "%"))

    def test_large_family_query_examples(self) -> None:
        # Required entities from the mission — resolution scoring must run for each.
        for q in ("Tata", "Tata Projects", "Larsen & Toubro", "NHPC", "BHEL"):
            c = _score(q, _FakeCompany(q if q != "Tata" else "Tata Projects Ltd"))
            self.assertIsNotNone(c, q)


class EntityAliasPrecisionGuardTest(unittest.TestCase):
    """The retrieval alias set must never widen a specific-unit query to a generic
    first-segment *bucket* (CASE #001 regression: "Dharmagarh NAC" resolving to the
    shared "Municipal Bodies" prefix dragged sibling buyers — Chatrapur NAC — into
    the package via ``ilike '%Municipal Bodies%'``)."""

    def _aliases_for(self, query: str, canonical: str, match_type: str = "exact") -> list[str]:
        from app.schemas.entity_resolution import EntityCandidate, EntityResolutionResult
        from app.schemas.investigation_planner import InvestigationPlan
        from app.services.investigation_executor import InvestigationExecutor

        ex = object.__new__(InvestigationExecutor)  # bypass __init__ (needs no session here)
        ex._resolution = EntityResolutionResult(
            query=query, resolved=True, requires_disambiguation=False,
            candidates=[EntityCandidate(
                entity_id=f"buyer:{canonical}", canonical_name=canonical,
                entity_type="government_buyer", match_type=match_type,
                match_reason="", score=100, confidence=1.0,
            )],
        )
        ex._active_plan = InvestigationPlan(
            query=query, investigation_type="buyer", confidence=0.8,
            connectors=[], modules=[], steps=[],
        )
        return ex._entity_aliases()

    def test_generic_bucket_canonical_is_not_folded(self) -> None:
        # "Municipal Bodies" shares no identifying token with "Dharmagarh NAC" and
        # is neither a phrase of it — it must be rejected as a retrieval alias.
        self.assertEqual(self._aliases_for("Dharmagarh NAC", "Municipal Bodies"), [])

    def test_genuine_variant_canonical_is_folded(self) -> None:
        # A canonical sharing an identifying token (or a phrase relationship) is a
        # legitimate identity-variant and IS folded, preserving recall.
        self.assertEqual(
            self._aliases_for("Dharmagarh", "Dharmagarh Notified Area Council"),
            ["Dharmagarh Notified Area Council"],
        )
        self.assertEqual(
            self._aliases_for("Tata Projects", "Tata Projects Limited"),
            ["Tata Projects Limited"],
        )


if __name__ == "__main__":
    unittest.main()
