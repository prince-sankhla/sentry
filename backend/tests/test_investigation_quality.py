"""Backend investigation-quality tests: weighted risk, grouped findings, graph.

These operate on synthetic InvestigationPackages (no DB) so they exercise the
pure projection/assessment logic added for the quality mission.
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
from app.services.investigation_executor import _build_evidence, _build_entities
from app.services.investigation_graph import build_investigation_graph
from app.services.investigation_indicators import build_indicators
from app.services.investigation_integrity import assess_integrity
from app.services.investigation_reasoning import _findings_from_indicators


def _meta(rid: str, source: str = "cppp") -> InvestigationSourceMetadata:
    return InvestigationSourceMetadata(source_name=source, source_record_id=rid, source_url="https://x/" + rid, retrieved_at=None)


def _record(ref, buyer, suppliers, *, value=None, published=None, closing=None, award_date=None, docs=False, source="cppp"):
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=ref, title=f"Tender {ref}", description=None, procuring_entity=buyer,
            published_date=published, closing_date=closing,
            estimated_value=Decimal(value) if value is not None else None,
            currency="INR", metadata=_meta(ref, source),
        ),
        awards=[
            InvestigationAwardResult(
                tender_reference_number=ref, company_name=s, company_registration_number=None,
                award_date=award_date, award_value=Decimal(value) if value is not None else None,
                currency="INR", metadata=_meta(f"{ref}:{s}", source),
            )
            for s in suppliers
        ],
        documents=[
            InvestigationDocumentResult(title=f"Doc {ref}", url="https://x/doc/" + ref, document_type="pdf", metadata=_meta("d" + ref, source))
        ] if docs else [],
    )


def _package(records, itype="supplier"):
    plan = InvestigationPlan(query="x", investigation_type=itype, confidence=0.8, connectors=["cppp"], modules=[], steps=[])
    pkg = InvestigationPackage(plan=plan, records=records)
    pkg.evidence = _build_evidence(pkg)
    pkg.entities = _build_entities(pkg)
    pkg.indicators = build_indicators(pkg)
    return pkg


class IntegrityAssessmentTest(unittest.TestCase):
    def test_no_records_is_insufficient(self) -> None:
        a = assess_integrity(_package([]))
        self.assertEqual(a.level, "insufficient")
        self.assertEqual(a.score, 0)

    def test_score_is_not_indicator_count(self) -> None:
        # One lone high-value tender fires an indicator but must NOT be critical/95.
        pkg = _package([_record("T-1", "PWD", ["Acme"], value="200000000")])
        a = assess_integrity(pkg)
        self.assertLess(a.score, 75)
        self.assertNotEqual(a.level, "critical")

    def test_factors_have_distinct_weights(self) -> None:
        pkg = _package([_record("T-1", "PWD", ["Acme"])])
        a = assess_integrity(pkg)
        weights = {f.key: f.weight for f in a.factors}
        # weights differ across factors (not a flat count)
        self.assertGreater(len(set(weights.values())), 3)
        # total weight sums to ~1.0
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=2)

    def test_systemic_pattern_scores_higher_than_oneoff(self) -> None:
        oneoff = assess_integrity(_package([_record("T-1", "PWD", ["Acme"])]))
        systemic = assess_integrity(_package([
            _record("T-1", "PWD", ["Acme"]),
            _record("T-2", "PWD", ["Acme"]),
            _record("T-3", "PWD", ["Acme"]),
            _record("T-4", "PWD", ["Acme"]),
        ]))
        self.assertGreater(systemic.score, oneoff.score)

    def test_every_factor_is_explainable(self) -> None:
        a = assess_integrity(_package([_record("T-1", "PWD", ["Acme"])]))
        for f in a.factors:
            self.assertTrue(f.detail)
            self.assertGreaterEqual(f.contribution, 0)


class GroupedFindingsTest(unittest.TestCase):
    def test_identical_finding_types_are_grouped_once(self) -> None:
        # Five single-bidder tenders => one grouped "Single Bidder" finding.
        records = [_record(f"T-{i}", "PWD", ["Acme"]) for i in range(5)]
        pkg = _package(records)
        findings = _findings_from_indicators(pkg)
        titles = [f.title for f in findings]
        self.assertEqual(len(titles), len(set(titles)), f"duplicate finding titles: {titles}")
        sb = [f for f in findings if f.indicator_type == "single_bidder"]
        self.assertEqual(len(sb), 1)
        self.assertGreaterEqual(sb[0].occurrences, 5)
        self.assertGreaterEqual(len(sb[0].supporting_records), 5)

    def test_grouped_finding_keeps_citations(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme"], docs=True) for i in range(3)]
        pkg = _package(records)
        findings = _findings_from_indicators(pkg)
        sb = next(f for f in findings if f.indicator_type == "single_bidder")
        self.assertTrue(sb.evidence_backed)
        self.assertTrue(sb.citations)

    def test_v2_only_indicator_becomes_leading_finding(self) -> None:
        # CASE #001 regression: contract_fragmentation is detected ONLY by Risk
        # Engine V2 (not the legacy indicator builder). It must still surface as a
        # first-class, evidence-backed finding — and, at medium severity, lead the
        # low-severity Award Data Gap — rather than living only in the typology table.
        from app.services.risk_engine import assess_risk_v2

        pub, close = date(2026, 6, 22), date(2026, 7, 8)
        records = [
            _record(f"LOT-{i}", "Municipal Bodies||Test NAC", [],
                    value=str(800000 + i), published=pub, closing=close, docs=True)
            for i in range(6)
        ]
        pkg = _package(records, itype="buyer")
        pkg.risk_assessment_v2 = assess_risk_v2(pkg)
        findings = _findings_from_indicators(pkg)
        types = [f.indicator_type for f in findings]
        self.assertIn("contract_fragmentation", types)
        self.assertEqual(findings[0].indicator_type, "contract_fragmentation")
        frag = next(f for f in findings if f.indicator_type == "contract_fragmentation")
        self.assertTrue(frag.evidence_backed)
        self.assertTrue(frag.citations)
        self.assertEqual(frag.severity, "medium")


class CompleteGraphTest(unittest.TestCase):
    def _rich_package(self) -> InvestigationPackage:
        records = [
            _record("T-1", "PWD", ["Acme"], value="200000000", published=date(2026, 1, 1), award_date=date(2026, 1, 2), docs=True),
            _record("T-2", "PWD", ["Acme"], value="5000000", published=date(2026, 2, 1), award_date=date(2026, 2, 2), docs=True),
            _record("T-3", "PWD", ["Acme"], value="6000000", published=date(2026, 3, 1), award_date=date(2026, 3, 2), docs=True),
        ]
        return _package(records)

    def test_graph_contains_all_node_types(self) -> None:
        pkg = self._rich_package()
        graph = build_investigation_graph(pkg)
        types = {n.type for n in graph.nodes}
        self.assertIn("tender", types)
        self.assertIn("buyer", types)
        self.assertIn("company", types)
        self.assertIn("award", types)
        self.assertIn("document", types)
        self.assertIn("evidence", types)

    def test_graph_has_indicator_nodes_when_package_has_indicators(self) -> None:
        pkg = self._rich_package()
        self.assertTrue(pkg.indicators, "precondition: package should have indicators")
        graph = build_investigation_graph(pkg)
        indicator_nodes = [n for n in graph.nodes if n.type == "indicator"]
        self.assertGreater(len(indicator_nodes), 0, "graph must not show zero indicator nodes")

    def test_graph_has_evidence_nodes_when_package_has_evidence(self) -> None:
        pkg = self._rich_package()
        self.assertTrue(pkg.evidence, "precondition: package should have evidence")
        graph = build_investigation_graph(pkg)
        evidence_nodes = [n for n in graph.nodes if n.type == "evidence"]
        self.assertGreater(len(evidence_nodes), 0, "graph must not show zero evidence nodes")

    def test_graph_edges_reference_existing_nodes(self) -> None:
        graph = build_investigation_graph(self._rich_package())
        node_ids = {n.id for n in graph.nodes}
        for edge in graph.edges:
            self.assertIn(edge.source, node_ids)
            self.assertIn(edge.target, node_ids)

    def test_indicator_nodes_linked_to_tenders(self) -> None:
        graph = build_investigation_graph(self._rich_package())
        indicator_ids = {n.id for n in graph.nodes if n.type == "indicator"}
        linked = {e.target for e in graph.edges if e.type == "tender_indicator"}
        self.assertTrue(indicator_ids & linked, "indicators should connect to tenders")

    def test_graph_node_counts_match_package(self) -> None:
        # BUG 4: graph must stay synchronized with the package — one indicator
        # node per indicator and one evidence node per evidence row.
        pkg = self._rich_package()
        graph = build_investigation_graph(pkg)
        indicator_nodes = [n for n in graph.nodes if n.type == "indicator"]
        evidence_nodes = [n for n in graph.nodes if n.type == "evidence"]
        self.assertEqual(len(indicator_nodes), len(pkg.indicators))
        self.assertEqual(len(evidence_nodes), len(pkg.evidence))

    def test_graph_synchronized_when_empty(self) -> None:
        # No records => no evidence/indicators => no such nodes (still consistent).
        pkg = _package([])
        graph = build_investigation_graph(pkg)
        self.assertEqual([n for n in graph.nodes if n.type == "indicator"], [])
        self.assertEqual([n for n in graph.nodes if n.type == "evidence"], [])


if __name__ == "__main__":
    unittest.main()
