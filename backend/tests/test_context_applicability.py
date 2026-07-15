"""Applicability evaluation tests — the analyzer is evidence-driven.

Problems under test (production-readiness review):
  P1 — a card is shown only when the retrieved facts pass its applicability check;
  P2 — facts inconsistent with guidance ⇒ card withheld with a NEUTRAL note;
  P3 — dynamic mapping: unrelated findings stop receiving the same generic cards;
  P4 — deterministic applicability classification (no scores, no probabilities).
"""

from __future__ import annotations

import unittest
from datetime import date
from types import SimpleNamespace

from app.verified_context import (
    APPLICABILITY_NOT_ESTABLISHED_MESSAGE,
    ContextFacts,
    FactRecord,
    ProcurementContextAnalyzer,
)


def _finding(fid="award_clustering", name="Rapid Repeat Procurement"):
    return SimpleNamespace(id=fid, name=name)


def _march_facts() -> ContextFacts:
    return ContextFacts(records=[
        FactRecord(reference_number=f"T-{i}", title=f"Road package {i}",
                   procuring_entity="NHAI", suppliers=["L&T"],
                   award_dates=[date(2026, 3, 1 + i)])
        for i in range(3)
    ], as_of=date(2026, 7, 8))


def _july_facts() -> ContextFacts:
    return ContextFacts(records=[
        FactRecord(reference_number=f"T-{i}", title=f"Road package {i}",
                   procuring_entity="NHAI", suppliers=["L&T"],
                   award_dates=[date(2026, 7, 1 + i)])
        for i in range(3)
    ], as_of=date(2026, 8, 8))


class P1ApplicabilityGatingTest(unittest.TestCase):
    def test_fy_end_guidance_shown_only_when_dates_support_it(self) -> None:
        analyzer = ProcurementContextAnalyzer()
        march = analyzer.analyze(_finding(), facts=_march_facts())
        refs = " ".join(g.reference for g in march.guidance)
        self.assertIn("even phasing", refs)  # year-end guidance shown

        july = analyzer.analyze(_finding(), facts=_july_facts())
        refs_july = " ".join(g.reference for g in july.guidance)
        self.assertNotIn("even phasing", refs_july)  # withheld — facts fail the check

    def test_emergency_guidance_withheld_without_emergency_language(self) -> None:
        # single_bidder retrieves single-bid + emergency guidance; without any
        # emergency language only the procedural single-bid card survives.
        analysis = ProcurementContextAnalyzer().analyze(
            _finding("single_bidder", "Single Bidder"), facts=_july_facts()
        )
        refs = " ".join(g.reference for g in analysis.guidance)
        self.assertIn("Manual for Procurement", refs)
        self.assertNotIn("emergency", refs.lower())
        self.assertTrue(any("could not be established" in n for n in analysis.applicability_notes))

    def test_emergency_guidance_shown_when_language_present(self) -> None:
        facts = ContextFacts(records=[FactRecord(
            reference_number="T-1", title="Emergency flood relief works", suppliers=[],
        )])
        analysis = ProcurementContextAnalyzer().analyze(
            _finding("single_bidder", "Single Bidder"), facts=facts
        )
        refs = " ".join(g.reference for g in analysis.guidance)
        self.assertIn("emergency", refs.lower())
        item = next(g for g in analysis.guidance if "emergency" in g.reference.lower())
        self.assertEqual(item.applicability_status, "Directly supported by retrieved evidence")
        self.assertIn("Emergency/urgency language", item.applicability_evidence)


class P2CrossFactValidationTest(unittest.TestCase):
    def test_contradicted_guidance_gets_neutral_note_never_conflict(self) -> None:
        july = ProcurementContextAnalyzer().analyze(_finding(), facts=_july_facts())
        self.assertTrue(july.applicability_notes)
        for note in july.applicability_notes:
            self.assertIn("could not be established from the available evidence", note)
            for banned in ("contradict", "false", "wrong", "inconsistent"):
                self.assertNotIn(banned, note.lower())

    def test_all_candidates_failing_returns_neutral_statement(self) -> None:
        # missing_award_data guidance requires the award window to hold; overdue
        # facts contradict it → nothing shown, neutral overall statement.
        overdue = ContextFacts(
            records=[FactRecord(reference_number="T-1", title="Works",
                                closing_date=date(2026, 1, 1), award_dates=[])],
            as_of=date(2026, 7, 1),  # ~180 days past closing — outside the window
        )
        analysis = ProcurementContextAnalyzer().analyze(
            _finding("missing_award_data", "Missing Award"), facts=overdue
        )
        self.assertFalse(analysis.guidance_available)
        self.assertEqual(analysis.potential_context, APPLICABILITY_NOT_ESTABLISHED_MESSAGE)
        self.assertEqual(analysis.guidance, [])


class P3DynamicMappingTest(unittest.TestCase):
    def test_unrelated_findings_no_longer_share_generic_guidance(self) -> None:
        analyzer = ProcurementContextAnalyzer()
        facts = _july_facts()  # no emergency language, no FY-end dates
        clustering = analyzer.analyze(_finding(), facts=facts)
        single = analyzer.analyze(_finding("single_bidder", "Single Bidder"), facts=facts)
        refs_a = {g.reference for g in clustering.guidance}
        refs_b = {g.reference for g in single.guidance}
        self.assertEqual(refs_a & refs_b, set())  # no repeated generic context

    def test_supported_guidance_ranks_before_procedural(self) -> None:
        analysis = ProcurementContextAnalyzer().analyze(
            _finding("repeat_supplier", "Repeated Winner"),
            facts=ContextFacts(records=[
                FactRecord(reference_number="T-1", title="A", procuring_entity="NHAI",
                           suppliers=["L&T"], award_dates=[date(2026, 3, 1)]),
                FactRecord(reference_number="T-2", title="B", procuring_entity="CPWD",
                           suppliers=["L&T"], award_dates=[date(2026, 3, 2)]),
            ]),
        )
        statuses = [g.applicability_status for g in analysis.guidance]
        self.assertEqual(statuses, sorted(statuses, key=lambda s: 0 if s.startswith("Directly") else 1))
        self.assertEqual(statuses[0], "Directly supported by retrieved evidence")


class P4ClassificationTest(unittest.TestCase):
    def test_classification_uses_fixed_vocabulary_no_scores(self) -> None:
        analysis = ProcurementContextAnalyzer().analyze(_finding(), facts=_march_facts())
        allowed = {
            "Directly supported by retrieved evidence",
            "Potentially applicable based on retrieved evidence",
            "Applicability cannot be established from available evidence",
        }
        for g in analysis.guidance:
            self.assertIn(g.applicability_status, allowed)
            self.assertNotRegex(g.applicability_status, r"\d")  # no scores/probabilities

    def test_without_facts_guidance_is_honestly_labeled(self) -> None:
        analysis = ProcurementContextAnalyzer().analyze(_finding())  # legacy path
        self.assertTrue(analysis.guidance_available)
        for g in analysis.guidance:
            self.assertEqual(
                g.applicability_status,
                "Applicability cannot be established from available evidence",
            )

    def test_deterministic(self) -> None:
        a1 = ProcurementContextAnalyzer().analyze(_finding(), facts=_march_facts())
        a2 = ProcurementContextAnalyzer().analyze(_finding(), facts=_march_facts())
        self.assertEqual(a1.model_dump(), a2.model_dump())


class EndpointFactsTest(unittest.TestCase):
    def test_post_endpoint_evaluates_facts(self) -> None:
        import warnings

        warnings.filterwarnings("ignore")
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        res = client.post("/api/investigations/context-analysis", json={
            "finding_id": "award_clustering",
            "finding_name": "Rapid Repeat Procurement",
            "facts": {
                "records": [
                    {"reference_number": "T-1", "title": "Road package 1",
                     "award_dates": ["2026-03-01"]},
                    {"reference_number": "T-2", "title": "Road package 2",
                     "award_dates": ["2026-03-05"]},
                ],
                "as_of": "2026-07-08",
            },
        })
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["guidance_available"])
        self.assertEqual(
            body["guidance"][0]["applicability_status"],
            "Directly supported by retrieved evidence",
        )


if __name__ == "__main__":
    unittest.main()
