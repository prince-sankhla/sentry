from __future__ import annotations

import unittest

from app.schemas.investigation_executor import InvestigationPackage
from app.schemas.investigation_planner import InvestigationPlan
from app.services.risk_engine import INDICATOR_REGISTRY, assess_risk_v2


class Phase5RegistryContractTest(unittest.TestCase):
    """Release-contract tests for Phase 5 anomaly/red-flag screening."""

    REQUIRED = {
        "high_value_direct_award",
        "high_value",
        "repeat_supplier",
        "buyer_concentration",
        "supplier_concentration",
        "abnormal_value",
        "award_clustering",
        "suspicious_timing",
        "duplicate_description",
        "missing_award_data",
        "award_value_exceeds_tender",
        "buyer_equals_supplier",
        "missing_documents",
        "contract_fragmentation",
    }

    def test_registry_contains_current_data_supported_phase5_detectors(self) -> None:
        self.assertTrue(self.REQUIRED.issubset(INDICATOR_REGISTRY))
        for indicator_id in self.REQUIRED:
            definition = INDICATOR_REGISTRY[indicator_id]
            self.assertTrue(definition.name)
            self.assertTrue(definition.category)
            self.assertIn(definition.base_severity, {"low", "medium", "high", "critical"})
            self.assertTrue(definition.required_evidence)
            self.assertTrue(definition.description)

    def test_bidder_conditioned_detector_is_explicitly_gated(self) -> None:
        # Current Indian package data is winner/award-centric. V2 must not
        # manufacture a bidder-level claim from winner count.
        self.assertIn("single_bidder", INDICATOR_REGISTRY)
        assessment = assess_risk_v2(
            InvestigationPackage(
                plan=InvestigationPlan(
                    query="x",
                    investigation_type="buyer",
                    confidence=0.8,
                    connectors=["cppp"],
                    modules=[],
                    steps=[],
                ),
                records=[],
            )
        )
        self.assertEqual(assessment.overall_severity, "insufficient")
        self.assertEqual(assessment.overall_score, 0)

    def test_every_triggered_v2_indicator_requires_review(self) -> None:
        # Empty package is deterministic and contains no fabricated findings.
        assessment = assess_risk_v2(
            InvestigationPackage(
                plan=InvestigationPlan(
                    query="x",
                    investigation_type="buyer",
                    confidence=0.8,
                    connectors=["cppp"],
                    modules=[],
                    steps=[],
                ),
                records=[],
            )
        )
        self.assertFalse(assessment.indicators)
        self.assertIn("Requires Investigator Review", assessment.disclaimer)


if __name__ == "__main__":
    unittest.main()
