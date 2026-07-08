from __future__ import annotations

import unittest

from app.services.investigation_indicators import build_indicators
from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan


def _meta(rid: str) -> InvestigationSourceMetadata:
    return InvestigationSourceMetadata(source_name="cppp", source_record_id=rid, source_url=None, retrieved_at=None)


def _record(ref: str, buyer: str, suppliers: list[str]) -> InvestigationProcurementRecord:
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=ref, title=f"Tender {ref}", description=None, procuring_entity=buyer,
            published_date=None, closing_date=None, estimated_value=None, currency="INR", metadata=_meta(ref),
        ),
        awards=[
            InvestigationAwardResult(
                tender_reference_number=ref, company_name=s, company_registration_number=None,
                award_date=None, award_value=None, currency="INR", metadata=_meta(f"{ref}:{s}"),
            )
            for s in suppliers
        ],
    )


def _package(records: list[InvestigationProcurementRecord]) -> InvestigationPackage:
    plan = InvestigationPlan(query="x", investigation_type="buyer", confidence=0.8, connectors=["cppp"], modules=[], steps=[])
    return InvestigationPackage(plan=plan, records=records)


class IndicatorTest(unittest.TestCase):
    def test_single_bidder_flag(self) -> None:
        indicators = build_indicators(_package([_record("T-1", "PWD", ["Acme"])]))
        self.assertTrue(any(i.type == "single_bidder" and i.related_tenders == ["T-1"] for i in indicators))

    def test_repeat_supplier_and_buyer_concentration(self) -> None:
        records = [
            _record("T-1", "PWD", ["Acme"]),
            _record("T-2", "PWD", ["Acme"]),
            _record("T-3", "PWD", ["Acme"]),
        ]
        indicators = build_indicators(_package(records))
        types = {i.type for i in indicators}
        self.assertIn("repeat_supplier", types)
        self.assertIn("buyer_concentration", types)
        repeat = next(i for i in indicators if i.type == "repeat_supplier")
        self.assertEqual(sorted(repeat.related_tenders), ["T-1", "T-2", "T-3"])


if __name__ == "__main__":
    unittest.main()
