"""Investigator Review tests — evidence organized, never judged.

The review must: (1) restate deterministic findings as objective supporting
evidence, (2) present competing routine-procurement evidence WITHOUT removing
or weakening any indicator, and (3) always tell the investigator what evidence
is still required. No probabilities, no verdict language.
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from app.services.investigator_review import build_investigator_review
from app.services.risk_engine import assess_risk_v2

from tests.test_investigation_quality import _package, _record


def _review_for(records):
    pkg = _package(records)
    pkg.risk_assessment_v2 = assess_risk_v2(pkg)
    return build_investigator_review(pkg), pkg


class SupportingEvidenceTest(unittest.TestCase):
    def test_indicators_become_supporting_evidence(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        review, pkg = _review_for(records)
        self.assertTrue(review.supporting)
        # Every triggered indicator is restated with its records.
        indicator_bases = {i.basis for i in review.supporting if i.basis.startswith("risk_engine:")}
        self.assertTrue(indicator_bases)

    def test_fragmentation_batch_yields_cluster_and_identifier_facts(self) -> None:
        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        records = [
            _record(f"2026_ORULB_132524_{i}", "Dharmagarh NAC", [], value="800000",
                    published=pub, closing=close)
            for i in range(2, 8)
        ]
        review, _ = _review_for(records)
        bases = {i.basis for i in review.supporting}
        self.assertIn("records:cluster", bases)          # large linked cluster
        self.assertIn("records:identical_values", bases)  # shared exact values

    def test_supporting_contains_no_verdict_language(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        review, _ = _review_for(records)
        blob = " ".join(i.statement.lower() for i in review.supporting)
        for banned in ("corrupt", "fraud", "guilty", "wrongdoing"):
            self.assertNotIn(banned, blob)


class RoutineEvidenceTest(unittest.TestCase):
    def test_routine_evidence_never_removes_indicators(self) -> None:
        # A package with emergency language still keeps every indicator; the
        # context appears as competing evidence, not as suppression of the list.
        records = [
            _record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True)
            for i in range(4)
        ]
        review, pkg = _review_for(records)
        self.assertTrue(pkg.risk_assessment_v2.indicators)  # findings intact
        # Supporting section restates every indicator despite any routine evidence.
        engine_items = [i for i in review.supporting if i.basis.startswith("risk_engine:")]
        self.assertGreaterEqual(
            len(engine_items), len(pkg.risk_assessment_v2.indicators)
        )

    def test_fy_end_award_clustering_is_surfaced_as_routine(self) -> None:
        records = [
            _record(f"T-{i}", "NHAI", ["L&T"], value="90000000",
                    published=date(2026, 2, 1), award_date=date(2026, 3, 1 + i), docs=True)
            for i in range(3)
        ]
        review, _ = _review_for(records)
        self.assertTrue(any(i.basis == "records:award_dates_fy_end" for i in review.routine))

    def test_multi_buyer_supplier_breadth_is_routine_evidence(self) -> None:
        records = [
            _record("T-1", "NHAI", ["L&T"], value="90000000", award_date=date(2026, 1, 5), docs=True),
            _record("T-2", "CPWD", ["L&T"], value="80000000", award_date=date(2026, 1, 6), docs=True),
        ]
        review, _ = _review_for(records)
        self.assertTrue(any(i.basis == "records:supplier_breadth" for i in review.routine))


class RequiredEvidenceTest(unittest.TestCase):
    def test_required_evidence_always_present_when_indicators_fire(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        review, pkg = _review_for(records)
        self.assertTrue(pkg.risk_assessment_v2.indicators)
        self.assertTrue(review.required)  # the most important section is never empty

    def test_fragmentation_asks_discriminating_questions(self) -> None:
        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        records = [
            _record(f"LOT-{i}", "Dharmagarh NAC", [], value="800000", published=pub, closing=close)
            for i in range(6)
        ]
        review, _ = _review_for(records)
        blob = " ".join(i.statement for i in review.required)
        self.assertIn("funding source", blob)
        self.assertIn("Detailed Project Report", blob)
        self.assertIn("evaluation committee", blob)


class ReviewPrincipleTest(unittest.TestCase):
    def test_principle_disclaims_judgment(self) -> None:
        review, _ = _review_for([_record("T-1", "PWD", ["Acme"], value="200000000", docs=True)])
        self.assertIn("does not determine wrongdoing", review.principle)

    def test_review_is_deterministic(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        r1, _ = _review_for(records)
        r2, _ = _review_for(records)
        self.assertEqual(r1.model_dump(), r2.model_dump())


if __name__ == "__main__":
    unittest.main()
