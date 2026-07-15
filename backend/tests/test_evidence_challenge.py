"""Evidence Challenge tests — SENTRY challenges its own findings.

Critical rule under test: the challenge NEVER changes indicator severity, risk
score, or deterministic findings. Explanations appear ONLY with in-package
evidence; every question eliminates one explanation; the decision boundary is
fixed and verdict-free.
"""

from __future__ import annotations

import unittest
from datetime import date

from app.schemas.evidence_challenge import CURRENT_POSITION
from app.services.evidence_challenge import build_evidence_challenge
from app.services.risk_engine import assess_risk_v2

from tests.test_investigation_quality import _package, _record


def _challenged(records):
    pkg = _package(records)
    pkg.risk_assessment_v2 = assess_risk_v2(pkg)
    before = [(i.id, i.severity, i.score) for i in pkg.risk_assessment_v2.indicators]
    score_before = pkg.risk_assessment_v2.overall_score
    challenge = build_evidence_challenge(pkg)
    after = [(i.id, i.severity, i.score) for i in pkg.risk_assessment_v2.indicators]
    return challenge, pkg, before == after and score_before == pkg.risk_assessment_v2.overall_score


class InvarianceTest(unittest.TestCase):
    def test_challenge_never_changes_findings_severity_or_score(self) -> None:
        records = [
            _record(f"T-{i}", "NHAI", ["L&T"], value="90000000",
                    published=date(2026, 2, 1), award_date=date(2026, 3, 1 + i), docs=True)
            for i in range(3)
        ]
        challenge, pkg, unchanged = _challenged(records)
        self.assertTrue(unchanged)          # the critical rule
        self.assertTrue(challenge.challenges)

    def test_every_triggered_indicator_is_challenged(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        challenge, pkg, _ = _challenged(records)
        challenged_ids = {c.finding_id for c in challenge.challenges}
        indicator_ids = {i.id for i in pkg.risk_assessment_v2.indicators}
        self.assertEqual(challenged_ids, indicator_ids)


class EvidenceBackedExplanationTest(unittest.TestCase):
    def test_fy_end_explanation_only_when_dates_support_it(self) -> None:
        # March awards → FY-end explanation listed for clustering.
        march = [
            _record(f"T-{i}", "NHAI", ["L&T"], value="90000000",
                    published=date(2026, 2, 1), award_date=date(2026, 3, 1 + i), docs=True)
            for i in range(3)
        ]
        challenge, _, _ = _challenged(march)
        clustering = next(c for c in challenge.challenges if c.finding_id == "award_clustering")
        self.assertTrue(any("year-end" in e.explanation for e in clustering.explanations))

        # July awards → the same finding gets NO fy-end explanation (never invented).
        july = [
            _record(f"T-{i}", "NHAI", ["L&T"], value="90000000",
                    published=date(2026, 6, 1), award_date=date(2026, 7, 1 + i), docs=True)
            for i in range(3)
        ]
        challenge2, _, _ = _challenged(july)
        clustering2 = next(c for c in challenge2.challenges if c.finding_id == "award_clustering")
        self.assertFalse(any("year-end" in e.explanation for e in clustering2.explanations))

    def test_fragmentation_distinct_scopes_yield_works_programme_explanation(self) -> None:
        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        records = [
            _record(f"LOT-{i}", "Dharmagarh NAC", [], value="800000", published=pub, closing=close)
            for i in range(6)
        ]
        # _record generates distinct titles per reference → distinct scopes.
        challenge, _, _ = _challenged(records)
        frag = next(c for c in challenge.challenges if c.finding_id == "contract_fragmentation")
        self.assertTrue(any("works programme" in e.explanation for e in frag.explanations))
        # The works-programme explanation brings the discriminating questions.
        questions = {q.question for q in frag.questions}
        self.assertIn("Same funding source?", questions)
        self.assertIn("Same evaluation committee?", questions)

    def test_every_question_targets_an_explanation(self) -> None:
        records = [
            _record(f"T-{i}", "NHAI", ["L&T"], value="90000000",
                    published=date(2026, 2, 1), award_date=date(2026, 3, 1 + i), docs=True)
            for i in range(3)
        ]
        challenge, _, _ = _challenged(records)
        for c in challenge.challenges:
            for q in c.questions:
                self.assertTrue(q.eliminates)  # every question eliminates something


class DecisionBoundaryTest(unittest.TestCase):
    def test_position_is_fixed_and_verdict_free(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        challenge, _, _ = _challenged(records)
        for c in challenge.challenges:
            self.assertEqual(c.position, CURRENT_POSITION)
        blob = " ".join(
            e.explanation + q.question
            for c in challenge.challenges
            for e in c.explanations
            for q in c.questions
        ).lower()
        for banned in ("corruption", "this is normal", "guilty", "fraud"):
            self.assertNotIn(banned, blob)

    def test_deterministic(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme Ltd"], value="200000000", docs=True) for i in range(4)]
        c1, _, _ = _challenged(records)
        c2, _, _ = _challenged(records)
        self.assertEqual(c1.model_dump(), c2.model_dump())


if __name__ == "__main__":
    unittest.main()
