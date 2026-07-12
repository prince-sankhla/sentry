from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan
from app.services.investigation_indicators import build_indicators
from app.services.risk_engine import assess_risk_v2


def _meta(rid: str) -> InvestigationSourceMetadata:
    return InvestigationSourceMetadata(source_name="cppp", source_record_id=rid, source_url=None, retrieved_at=None)


def _record(
    ref: str,
    buyer: str,
    suppliers: list[str],
    *,
    value: Decimal | None = None,
    published: date | None = None,
    award_date: date | None = None,
    description: str | None = None,
    closing: date | None = None,
) -> InvestigationProcurementRecord:
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=ref,
            title=f"Tender {ref}",
            description=description,
            procuring_entity=buyer,
            published_date=published,
            closing_date=closing,
            estimated_value=value,
            currency="INR",
            metadata=_meta(ref),
        ),
        awards=[
            InvestigationAwardResult(
                tender_reference_number=ref,
                company_name=s,
                company_registration_number=None,
                award_date=award_date,
                award_value=value,
                currency="INR",
                metadata=_meta(f"{ref}:{s}"),
            )
            for s in suppliers
        ],
    )


def _package(records: list[InvestigationProcurementRecord]) -> InvestigationPackage:
    plan = InvestigationPlan(
        query="x", investigation_type="buyer", confidence=0.8, connectors=["cppp"], modules=[], steps=[]
    )
    return InvestigationPackage(plan=plan, records=records)


class RiskEngineTest(unittest.TestCase):
    def test_every_indicator_is_explainable(self) -> None:
        records = [
            _record("T-1", "PWD", ["Acme"], value=Decimal("5000000"), published=date(2026, 1, 1), award_date=date(2026, 1, 2)),
            _record("T-2", "PWD", ["Acme"], value=Decimal("6000000"), published=date(2026, 1, 5), award_date=date(2026, 1, 10)),
            _record("T-3", "PWD", ["Acme"], value=Decimal("7000000"), published=date(2026, 1, 8), award_date=date(2026, 1, 20)),
        ]
        indicators = build_indicators(_package(records))
        self.assertTrue(indicators)
        for indicator in indicators:
            # Explainability contract: reason + confidence + evidence always set.
            self.assertTrue(indicator.reason, indicator.type)
            self.assertGreater(indicator.confidence, 0.0)
            self.assertLessEqual(indicator.confidence, 1.0)
            self.assertTrue(indicator.evidence, indicator.type)

    def test_suspicious_timing_detected(self) -> None:
        records = [
            _record("T-1", "PWD", ["Acme"], published=date(2026, 1, 1), award_date=date(2026, 1, 1)),
        ]
        types = {i.type for i in build_indicators(_package(records))}
        self.assertIn("suspicious_timing", types)

    def test_abnormal_value_outlier(self) -> None:
        records = [
            _record(f"T-{i}", "PWD", [f"S{i}"], value=Decimal("1000000"), award_date=date(2026, 1, i + 1))
            for i in range(6)
        ]
        records.append(_record("T-BIG", "PWD", ["Whale"], value=Decimal("900000000"), award_date=date(2026, 2, 1)))
        indicators = build_indicators(_package(records))
        abnormal = [i for i in indicators if i.type == "abnormal_value"]
        self.assertTrue(abnormal)
        self.assertIn("Whale", abnormal[0].related_entities)

    def test_award_clustering(self) -> None:
        records = [
            _record("T-1", "PWD", ["Acme"], award_date=date(2026, 1, 1)),
            _record("T-2", "PWD", ["Acme"], award_date=date(2026, 1, 5)),
            _record("T-3", "PWD", ["Acme"], award_date=date(2026, 1, 10)),
        ]
        types = {i.type for i in build_indicators(_package(records))}
        self.assertIn("award_clustering", types)

    def test_duplicate_descriptions(self) -> None:
        shared = "supply and installation of solar street lights across the district area"
        records = [
            _record("T-1", "PWD", ["Acme"], description=shared),
            _record("T-2", "KSEB", ["Beta"], description=shared),
        ]
        types = {i.type for i in build_indicators(_package(records))}
        self.assertIn("duplicate_description", types)

    def test_high_value_direct_award(self) -> None:
        records = [_record("T-1", "PWD", ["Acme"], value=Decimal("200000000"))]
        indicators = build_indicators(_package(records))
        types = {i.type for i in indicators}
        self.assertIn("high_value_direct_award", types)

    def test_contract_fragmentation_detected(self) -> None:
        # One buyer issuing a single same-day batch of small tenders (no awards) —
        # the deterministic fragmentation signal used by Case #001 (Dharmagarh NAC).
        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        records = [
            _record(f"LOT-{i}", "Dharmagarh NAC", [], value=Decimal("800000"), published=pub, closing=close)
            for i in range(6)
        ]
        assessment = assess_risk_v2(_package(records))
        ids = {i.id for i in assessment.indicators}
        self.assertIn("contract_fragmentation", ids)
        frag = next(i for i in assessment.indicators if i.id == "contract_fragmentation")
        self.assertEqual(frag.severity, "medium")  # a lead, never a conclusion
        self.assertEqual(len(frag.supporting_records), 6)

    def test_contract_fragmentation_reports_identical_value_pairs(self) -> None:
        # Dharmagarh signature: a same-day batch with two identical-value PAIRS —
        # 4 colliding tenders across 2 value groups. The reason must count colliding
        # tenders and distinct groups precisely (not `len - set`, which returns 2).
        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        vals = ["1694915", "1694915", "847458", "847458", "508475", "254237"]
        records = [
            _record(f"LOT-{i}", "Dharmagarh NAC", [], value=Decimal(v), published=pub, closing=close)
            for i, v in enumerate(vals)
        ]
        frag = next(i for i in assess_risk_v2(_package(records)).indicators
                    if i.id == "contract_fragmentation")
        self.assertEqual(len(frag.supporting_records), 6)
        self.assertIn("4 tenders fall into 2 identical-value groups", frag.reason)

    def test_contract_fragmentation_not_triggered_below_threshold(self) -> None:
        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        records = [
            _record(f"LOT-{i}", "Small NAC", [], value=Decimal("800000"), published=pub, closing=close)
            for i in range(3)
        ]
        ids = {i.id for i in assess_risk_v2(_package(records)).indicators}
        self.assertNotIn("contract_fragmentation", ids)

    def test_supporting_sets_populated(self) -> None:
        records = [
            _record("T-1", "PWD", ["Acme"], award_date=date(2026, 1, 1)),
            _record("T-2", "PWD", ["Acme"], award_date=date(2026, 1, 2)),
        ]
        repeat = next(i for i in build_indicators(_package(records)) if i.type == "repeat_supplier")
        self.assertIn("Acme", repeat.supporting_suppliers)
        self.assertIn("PWD", repeat.supporting_buyers)


class RiskEngineV2Test(unittest.TestCase):
    """Deterministic Risk Engine V2 (assess_risk_v2) — L1–L6 behaviour."""

    def test_insufficient_when_no_records(self) -> None:
        assessment = assess_risk_v2(_package([]))
        self.assertEqual(assessment.overall_severity, "insufficient")
        self.assertEqual(assessment.overall_score, 0)
        self.assertEqual(assessment.method, "deterministic_risk_engine_v2")

    def test_assessment_is_fully_explainable(self) -> None:
        # Repeat single-supplier awards to one buyer → indicators + patterns.
        records = [
            _record("T-1", "PWD", ["Acme"], value=Decimal("5000000"), published=date(2026, 1, 1), award_date=date(2026, 1, 2)),
            _record("T-2", "PWD", ["Acme"], value=Decimal("6000000"), published=date(2026, 1, 5), award_date=date(2026, 1, 10)),
            _record("T-3", "PWD", ["Acme"], value=Decimal("7000000"), published=date(2026, 1, 8), award_date=date(2026, 1, 20)),
        ]
        assessment = assess_risk_v2(_package(records))
        self.assertTrue(assessment.indicators)
        self.assertIn(assessment.overall_severity, {"low", "medium", "high", "critical"})
        # Every indicator carries its explainability contract.
        for indicator in assessment.indicators:
            self.assertTrue(indicator.reason, indicator.id)
            self.assertIn(indicator.evidence_status, {"verified", "probable", "unknown"})
            self.assertTrue(indicator.review_required)
        # An explainability node exists for each indicator.
        self.assertEqual(len(assessment.explainability), len(assessment.indicators))
        # Confidence is computed and independent of the risk score.
        self.assertIsNotNone(assessment.confidence)
        self.assertGreaterEqual(assessment.confidence.score, 0.0)
        self.assertLessEqual(assessment.confidence.score, 1.0)

    def test_buyer_equals_supplier_detected(self) -> None:
        # V2-only deterministic detector: awarded supplier == procuring entity.
        records = [_record("T-1", "State Water Authority", ["State Water Authority"], value=Decimal("5000000"))]
        assessment = assess_risk_v2(_package(records))
        ids = {i.id for i in assessment.indicators}
        self.assertIn("buyer_equals_supplier", ids)

    def test_award_value_exceeds_tender_detected(self) -> None:
        record = InvestigationProcurementRecord(
            tender=InvestigationTenderResult(
                reference_number="T-1", title="Tender T-1", description=None,
                procuring_entity="PWD", published_date=None, closing_date=None,
                estimated_value=Decimal("1000000"), currency="INR", metadata=_meta("T-1"),
            ),
            awards=[
                InvestigationAwardResult(
                    tender_reference_number="T-1", company_name="Acme",
                    company_registration_number=None, award_date=None,
                    award_value=Decimal("5000000"), currency="INR", metadata=_meta("T-1:Acme"),
                )
            ],
        )
        assessment = assess_risk_v2(_package([record]))
        ids = {i.id for i in assessment.indicators}
        self.assertIn("award_value_exceeds_tender", ids)

    def test_patterns_are_named_not_summed(self) -> None:
        # Repeat single-bidder awards to one buyer trigger a named pattern rule.
        records = [
            _record(f"T-{i}", "PWD", ["Acme"], value=Decimal("5000000"), award_date=date(2026, 1, i + 1))
            for i in range(4)
        ]
        assessment = assess_risk_v2(_package(records))
        # Patterns reference the indicators that produced them (no arithmetic sum).
        for pattern in assessment.patterns:
            self.assertTrue(pattern.name)
            self.assertTrue(pattern.indicators)
            self.assertTrue(all(ind in {i.id for i in assessment.indicators} for ind in pattern.indicators))

    def test_overall_severity_never_exceeds_strongest(self) -> None:
        records = [_record("T-1", "PWD", ["Acme"], value=Decimal("5000000"))]
        assessment = assess_risk_v2(_package(records))
        order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        strongest = max((order[i.severity] for i in assessment.indicators), default=1)
        self.assertLessEqual(order[assessment.overall_severity], max(strongest, order["low"]))


if __name__ == "__main__":
    unittest.main()
