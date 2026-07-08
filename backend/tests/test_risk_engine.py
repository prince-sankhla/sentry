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
) -> InvestigationProcurementRecord:
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=ref,
            title=f"Tender {ref}",
            description=description,
            procuring_entity=buyer,
            published_date=published,
            closing_date=None,
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

    def test_supporting_sets_populated(self) -> None:
        records = [
            _record("T-1", "PWD", ["Acme"], award_date=date(2026, 1, 1)),
            _record("T-2", "PWD", ["Acme"], award_date=date(2026, 1, 2)),
        ]
        repeat = next(i for i in build_indicators(_package(records)) if i.type == "repeat_supplier")
        self.assertIn("Acme", repeat.supporting_suppliers)
        self.assertIn("PWD", repeat.supporting_buyers)


if __name__ == "__main__":
    unittest.main()
