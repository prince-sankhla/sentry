"""Structured analyst-report tests: grounded sections, contradictions, confidence.

DB-free synthetic packages exercise the deterministic report builder across the
required scenarios (supplier / buyer / company / tender / missing evidence /
conflicting evidence).
"""

from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from app.schemas.investigation_executor import (
    InvestigationAwardResult,
    InvestigationDocumentResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan
from app.schemas.investigation_reasoning import GroundingReport
from app.services.investigation_executor import _build_entities, _build_evidence, _build_timeline
from app.services.investigation_indicators import build_indicators
from app.services.investigation_report import build_analyst_report


def _meta(rid: str, src: str = "cppp") -> InvestigationSourceMetadata:
    return InvestigationSourceMetadata(source_name=src, source_record_id=rid, source_url="https://x/" + rid, retrieved_at=None)


def _rec(ref, buyer, suppliers, *, value=None, pub=None, close=None, awd=None, docs=False, src="cppp", est=None):
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=ref, title=f"Work {ref}", description=None, procuring_entity=buyer,
            published_date=pub, closing_date=close,
            estimated_value=Decimal(est) if est is not None else (Decimal(value) if value else None),
            currency="INR", metadata=_meta(ref, src),
        ),
        awards=[
            InvestigationAwardResult(
                tender_reference_number=ref, company_name=s, company_registration_number=None,
                award_date=awd, award_value=Decimal(value) if value else None, currency="INR", metadata=_meta(f"{ref}:{s}", src),
            )
            for s in suppliers
        ],
        documents=[InvestigationDocumentResult(title=f"Doc {ref}", url="https://x/d/" + ref, document_type="pdf", metadata=_meta("d" + ref, src))] if docs else [],
    )


def _pkg(records, itype="supplier"):
    plan = InvestigationPlan(query="x", investigation_type=itype, confidence=0.8, connectors=["cppp"], modules=[], steps=[])
    pkg = InvestigationPackage(plan=plan, records=records)
    pkg.evidence = _build_evidence(pkg)
    pkg.entities = _build_entities(pkg)
    pkg.timeline = _build_timeline(pkg)
    pkg.indicators = build_indicators(pkg)
    return pkg


def _report(pkg):
    return build_analyst_report(pkg, GroundingReport())


class SupplierScenarioTest(unittest.TestCase):
    def test_supplier_single_buyer_dependence(self) -> None:
        pkg = _pkg([_rec(f"T-{i}", "NHAI", ["Acme"], value="50000000", pub=date(2026, 1, i + 1), awd=date(2026, 1, i + 10)) for i in range(1, 4)])
        rep = _report(pkg)
        acme = next(s for s in rep.supplier_analysis if s.name == "Acme")
        self.assertTrue(acme.single_buyer_dependence)
        self.assertEqual(acme.award_count, 3)


class BuyerScenarioTest(unittest.TestCase):
    def test_buyer_concentration_note(self) -> None:
        pkg = _pkg([_rec(f"T-{i}", "CPWD", ["OneVendor"], value="20000000", awd=date(2026, 2, i + 1)) for i in range(1, 5)])
        rep = _report(pkg)
        cpwd = next(b for b in rep.buyer_analysis if b.name == "CPWD")
        self.assertEqual(cpwd.concentration_pct, 100)
        self.assertIn("concentration", cpwd.note.lower())


class CompanyScenarioTest(unittest.TestCase):
    def test_award_and_timeline_sections(self) -> None:
        pkg = _pkg([
            _rec("T-1", "BHEL", ["Larsen"], value="90000000", pub=date(2026, 1, 1), close=date(2026, 1, 20), awd=date(2026, 2, 1), docs=True),
            _rec("T-2", "BHEL", ["Larsen"], value="10000000", pub=date(2026, 3, 1), close=date(2026, 3, 20), awd=date(2026, 4, 1), docs=True),
        ], itype="company")
        rep = _report(pkg)
        self.assertIsNotNone(rep.award_analysis)
        self.assertEqual(rep.award_analysis.total_awards, 2)
        self.assertEqual(rep.award_analysis.largest_award_supplier, "Larsen")
        self.assertIsNotNone(rep.timeline_analysis)
        self.assertGreater(rep.timeline_analysis.event_count, 0)


class TenderScenarioTest(unittest.TestCase):
    def test_single_tender_report_is_grounded(self) -> None:
        pkg = _pkg([_rec("NIT-99", "DMRC", ["Siemens"], value="500000000", pub=date(2026, 5, 1), close=date(2026, 5, 25), awd=date(2026, 6, 10), docs=True)], itype="tender")
        rep = _report(pkg)
        self.assertEqual(rep.award_analysis.total_awards, 1)
        self.assertTrue(rep.confidence_assessment)


class MissingEvidenceScenarioTest(unittest.TestCase):
    def test_missing_awards_and_docs_reported(self) -> None:
        # Closed tenders (relative to dataset) with no awards + no docs + no values.
        pkg = _pkg([
            _rec("T-1", "NHAI", [], pub=date(2026, 1, 1), close=date(2026, 1, 20)),
            _rec("T-2", "NHAI", [], pub=date(2026, 2, 1), close=date(2026, 2, 20)),
            _rec("T-3", "NHAI", ["Acme"], pub=date(2026, 6, 1), close=date(2026, 6, 20), awd=date(2026, 6, 25)),  # unvalued award
        ])
        rep = _report(pkg)
        gaps = " ".join(rep.missing_evidence).lower()
        self.assertIn("award notice", gaps)
        self.assertIn("document", gaps)
        # missing_award contradiction fires for the closed, award-less tenders.
        self.assertTrue(any(c.type == "missing_award" for c in rep.contradictions))

    def test_no_records_states_insufficient_evidence(self) -> None:
        pkg = _pkg([])
        rep = _report(pkg)
        self.assertIn("Insufficient evidence", " ".join(rep.missing_evidence))
        self.assertEqual(rep.confidence_assessment.level, "very_low")


class ConflictingEvidenceScenarioTest(unittest.TestCase):
    def test_award_before_publication_is_high_severity(self) -> None:
        pkg = _pkg([_rec("T-1", "NHAI", ["Acme"], value="50000000", pub=date(2026, 2, 1), awd=date(2026, 1, 15))])
        rep = _report(pkg)
        c = next(c for c in rep.contradictions if c.type == "date_inconsistency")
        self.assertEqual(c.severity, "high")
        self.assertIn("T-1", c.related_tenders)

    def test_value_inconsistency_detected(self) -> None:
        pkg = _pkg([_rec("T-1", "NHAI", ["Acme"], value="55000000", est="10000000", pub=date(2026, 1, 1), awd=date(2026, 2, 1))])
        rep = _report(pkg)
        self.assertTrue(any(c.type == "value_inconsistency" for c in rep.contradictions))

    def test_conflicting_suppliers_detected(self) -> None:
        pkg = _pkg([_rec("T-1", "NHAI", ["Acme", "Beta"], value="10000000", awd=date(2026, 2, 1))])
        rep = _report(pkg)
        self.assertTrue(any(c.type == "conflicting_supplier" for c in rep.contradictions))

    def test_contradictions_lower_cross_source_consistency(self) -> None:
        clean = _report(_pkg([_rec("T-1", "NHAI", ["Acme"], value="10000000", pub=date(2026, 1, 1), awd=date(2026, 2, 1))]))
        conflicted = _report(_pkg([_rec("T-1", "NHAI", ["Acme"], value="10000000", pub=date(2026, 2, 1), awd=date(2026, 1, 1))]))
        clean_dim = next(d for d in clean.confidence_assessment.dimensions if d.key == "cross_source_consistency")
        conf_dim = next(d for d in conflicted.confidence_assessment.dimensions if d.key == "cross_source_consistency")
        self.assertGreater(clean_dim.score, conf_dim.score)


class ConfidenceAssessmentTest(unittest.TestCase):
    def test_eight_dimensions_and_explanation(self) -> None:
        pkg = _pkg([_rec("T-1", "NHAI", ["Acme"], value="10000000", pub=date(2026, 1, 1), awd=date(2026, 2, 1), docs=True)])
        ca = _report(pkg).confidence_assessment
        self.assertEqual(len(ca.dimensions), 8)
        self.assertTrue(ca.explanation)
        self.assertTrue(0.0 <= ca.score <= 1.0)

    def test_reliable_source_scores_higher_than_unknown(self) -> None:
        reliable = _report(_pkg([_rec("T-1", "NHAI", ["Acme"], value="1", pub=date(2026, 1, 1), awd=date(2026, 2, 1), docs=True, src="cppp")]))
        unknown = _report(_pkg([_rec("T-1", "NHAI", ["Acme"], value="1", pub=date(2026, 1, 1), awd=date(2026, 2, 1), docs=True, src="world_bank")]))
        r = next(d for d in reliable.confidence_assessment.dimensions if d.key == "source_reliability")
        u = next(d for d in unknown.confidence_assessment.dimensions if d.key == "source_reliability")
        self.assertGreater(r.score, u.score)


if __name__ == "__main__":
    unittest.main()
