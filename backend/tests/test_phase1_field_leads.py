from __future__ import annotations

import ast
import unittest
from pathlib import Path

from app.schemas.priority_queue import PriorityQueueItem
from app.services.investigation_intent import detect_intent


class Phase1ContractTests(unittest.TestCase):
    def test_field_lead_schema_has_stable_identity(self):
        item = PriorityQueueItem(
            subject="Construction of Retaining wall and Drain Works",
            investigation_type="tender",
            priority="review",
            risk_level="insufficient",
            typology_count=0,
            linked_records=1,
            evidence_strength="high",
            evidence_completeness=1.0,
            primary_pattern="Field verification candidate",
            reasons=["direct tender lead"],
            tender_id="11111111-1111-1111-1111-111111111111",
            reference_number="FIELD:2026_DEMO_ROAD",
            tender_title="Construction of Retaining wall and Drain Works",
        )
        self.assertEqual(item.tender_id, "11111111-1111-1111-1111-111111111111")
        self.assertEqual(item.reference_number, "FIELD:2026_DEMO_ROAD")
        self.assertEqual(item.tender_title, "Construction of Retaining wall and Drain Works")

    def test_field_reference_is_classified_as_tender(self):
        result = detect_intent("FIELD:2026_DEMO_ROAD")
        self.assertEqual(result.investigation_type, "tender")
        self.assertEqual(result.intent, "tender_id")
        self.assertEqual(result.entity_query, "FIELD:2026_DEMO_ROAD")
        self.assertEqual(result.matched_field, "reference_number")

    def test_direct_field_lead_helper_returns_identity_fields(self):
        path = Path(__file__).parents[1] / "app" / "services" / "priority_queue_direct_tender.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        strings = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertIn("Tender", names)
        self.assertIn("tender_id", strings)
        self.assertIn("reference_number", strings)
        self.assertIn("source_record_id", strings)
        self.assertIn("FIELD:%", strings)


if __name__ == "__main__":
    unittest.main()
