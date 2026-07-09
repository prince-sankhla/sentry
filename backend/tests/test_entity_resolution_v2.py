"""Entity Resolution V2 regression tests — investigation correctness.

Locks the retrieval-contamination fixes: intent detection separates entity from
modifier, the planner receives the clean entity + correct type, aliases are
distinct (BEL ≠ BHEL), and entity retrieval is precision + Indian-only with NO
broad-synonym fallback (so "Archaeological Survey of India" can never pull in
NHAI / RailTel / World Bank / foreign entities).
"""

from __future__ import annotations

import unittest

from app.services.investigation_intent import detect_intent
from app.services.investigation_planner import InvestigationPlanner


class IntentDetectionTest(unittest.TestCase):
    def test_authority_is_not_company(self) -> None:
        it = detect_intent("Archaeological Survey of India")
        self.assertEqual(it.investigation_type, "buyer")
        self.assertEqual(it.intent, "authority")

    def test_director_modifier_stripped_and_typed(self) -> None:
        it = detect_intent("Archaeological Survey of India directors")
        self.assertEqual(it.investigation_type, "director")
        self.assertEqual(it.entity_query, "Archaeological Survey of India")
        self.assertNotIn("director", it.entity_query.lower())

    def test_director_never_becomes_company(self) -> None:
        for q in ("Tata Projects directors", "NHAI board", "L&T owners"):
            self.assertEqual(detect_intent(q).investigation_type, "director", q)

    def test_supplier_modifier_targets_buyer(self) -> None:
        it = detect_intent("NHAI suppliers")
        self.assertEqual(it.investigation_type, "buyer")
        self.assertEqual(it.entity_query, "NHAI")

    def test_tender_id_detected(self) -> None:
        it = detect_intent("BEL/2026/RADAR/040")
        self.assertEqual(it.investigation_type, "tender")
        self.assertEqual(it.intent, "tender_id")
        self.assertEqual(it.matched_field, "reference_number")

    def test_cin_detected(self) -> None:
        it = detect_intent("L28920MH1945PLC004520")
        self.assertEqual(it.intent, "cin")
        self.assertEqual(it.matched_field, "cin")

    def test_ministry_detected(self) -> None:
        self.assertEqual(detect_intent("Ministry of Defence").investigation_type, "ministry")

    def test_plain_company_name(self) -> None:
        it = detect_intent("Tata Projects")
        self.assertEqual(it.investigation_type, "company")
        self.assertEqual(it.entity_query, "Tata Projects")


class PlannerReceivesResolvedEntityTest(unittest.TestCase):
    def _planner(self):
        # SourceManager reads no DB for planning; safe to construct.
        return InvestigationPlanner()

    def test_planner_uses_clean_entity_query_not_raw_text(self) -> None:
        plan = self._planner().build_plan("Archaeological Survey of India directors")
        self.assertEqual(plan.query, "Archaeological Survey of India")
        self.assertEqual(plan.investigation_type, "director")

    def test_authority_query_is_buyer_investigation(self) -> None:
        plan = self._planner().build_plan("Archaeological Survey of India")
        self.assertEqual(plan.investigation_type, "buyer")

    def test_tender_id_is_tender_investigation(self) -> None:
        plan = self._planner().build_plan("BEL/2026/RADAR/040")
        self.assertEqual(plan.investigation_type, "tender")


class AliasDistinctnessTest(unittest.TestCase):
    def test_bel_and_bhel_map_to_distinct_entities(self) -> None:
        from app.services.entity_resolution_service import _ACRONYM_ALIASES, _query_forms
        self.assertIn("bel", _ACRONYM_ALIASES)
        self.assertIn("bhel", _ACRONYM_ALIASES)
        self.assertIn("Bharat Electronics", _query_forms("BEL"))
        self.assertIn("Bharat Heavy Electricals", _query_forms("BHEL"))
        # The two acronyms must never expand to the same canonical form.
        self.assertNotEqual(_ACRONYM_ALIASES["bel"], _ACRONYM_ALIASES["bhel"])

    def test_asi_and_gem_aliases_present(self) -> None:
        from app.services.entity_resolution_service import _ACRONYM_ALIASES
        self.assertEqual(_ACRONYM_ALIASES["asi"], "Archaeological Survey of India")
        self.assertIn("gem", _ACRONYM_ALIASES)


class CountryIsolationTest(unittest.TestCase):
    def test_indian_only_clause_excludes_international_sources(self) -> None:
        # The repository builds an India-only WHERE clause for entity retrieval.
        from app.services.investigation_repository import _INTERNATIONAL_SOURCES
        for src in ("world_bank", "adb", "un_procurement", "prozorro"):
            self.assertIn(src, _INTERNATIONAL_SOURCES)

    def test_executor_entity_search_has_no_broad_fallback(self) -> None:
        # Regression: the broad-synonym fallback (the contamination source) is gone
        # from the entity-investigation retrieval path.
        import inspect
        from app.services.investigation_executor import InvestigationExecutor
        src = inspect.getsource(InvestigationExecutor._search)
        self.assertIn("indian_only=True", src)
        self.assertIn("precision=True", src)
        # No unconditional broad fallback after the precision branch.
        self.assertNotIn("fall back to broad retrieval", src)


if __name__ == "__main__":
    unittest.main()
