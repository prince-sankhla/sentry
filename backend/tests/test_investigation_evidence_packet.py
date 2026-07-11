"""Verified-finding status + consolidated evidence packet tests.

Exercises the two minimum improvements that make findings *verified* (not merely
cited) and consolidate them into one judge-facing proof bundle. Operates on
synthetic packages (no DB), reusing the quality-test builders.
"""

from __future__ import annotations

import unittest

from app.services.investigation_evidence import build_evidence_packet
from app.services.investigation_reasoning import _findings_from_indicators, build_reasoning
from app.services.risk_engine import assess_risk_v2

from tests.test_investigation_quality import _package, _record


def _package_with_risk(records, itype="supplier"):
    """A finalized-enough package: indicators + the deterministic V2 assessment,
    which is where each finding's verification verdict comes from."""
    pkg = _package(records, itype=itype)
    pkg.risk_assessment_v2 = assess_risk_v2(pkg)
    return pkg


class VerifiedFindingTest(unittest.TestCase):
    def test_finding_with_document_is_verified(self) -> None:
        # Documents present -> Risk Engine V2 evidence validator returns "verified".
        records = [_record(f"T-{i}", "PWD", ["Acme"], docs=True) for i in range(3)]
        pkg = _package_with_risk(records)
        findings = _findings_from_indicators(pkg)
        sb = next(f for f in findings if f.indicator_type == "single_bidder")
        self.assertTrue(sb.evidence_backed)
        self.assertEqual(sb.verification, "verified")

    def test_finding_without_document_is_probable_not_verified(self) -> None:
        # A source URL but no attached document -> "probable", never "verified".
        records = [_record(f"T-{i}", "PWD", ["Acme"], docs=False) for i in range(3)]
        pkg = _package_with_risk(records)
        findings = _findings_from_indicators(pkg)
        sb = next(f for f in findings if f.indicator_type == "single_bidder")
        self.assertTrue(sb.evidence_backed)
        self.assertEqual(sb.verification, "probable")

    def test_verification_defaults_without_risk_v2(self) -> None:
        # A package that never ran V2 must not crash; findings stay best-effort.
        records = [_record(f"T-{i}", "PWD", ["Acme"], docs=True) for i in range(3)]
        pkg = _package(records)  # no risk_assessment_v2
        findings = _findings_from_indicators(pkg)
        self.assertTrue(all(f.verification in {"verified", "probable", "unknown", "unverified"} for f in findings))


class EvidencePacketTest(unittest.TestCase):
    def test_packet_consolidates_findings_and_totals(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme"], docs=True) for i in range(3)]
        pkg = _package_with_risk(records)
        findings = _findings_from_indicators(pkg)
        packet = build_evidence_packet(
            pkg, findings, subject="Acme", risk_level="high", generated_by="deterministic",
        )
        self.assertEqual(packet.total_findings, len(findings))
        self.assertEqual(len(packet.items), len(findings))
        # Every finding has documents -> at least one verified finding surfaces.
        self.assertGreaterEqual(packet.verified_findings, 1)
        self.assertGreaterEqual(packet.total_evidence_items, 1)
        self.assertIn("cppp", packet.distinct_sources)
        # cppp is an official primary source -> primary share is meaningful.
        self.assertGreater(packet.primary_source_share, 0.0)
        # Each packet item points back to its provenanced citations.
        for item in packet.items:
            self.assertTrue(item.finding_title)

    def test_packet_attached_by_build_reasoning(self) -> None:
        records = [_record(f"T-{i}", "PWD", ["Acme"], docs=True) for i in range(3)]
        pkg = _package_with_risk(records)
        reasoning = build_reasoning(pkg, "Acme")
        self.assertIsNotNone(reasoning.evidence_packet)
        self.assertEqual(reasoning.evidence_packet.total_findings, len(reasoning.findings))
        # Grounding report carries the verified-finding count too.
        self.assertGreaterEqual(reasoning.grounding.verified_findings, 1)
        self.assertTrue(reasoning.evidence_packet.disclaimer)


if __name__ == "__main__":
    unittest.main()
