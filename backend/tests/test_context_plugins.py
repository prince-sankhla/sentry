"""Context Plugin architecture tests — the registry contract.

Locks the Sprint 2.8 refactor: plugins self-register via auto-discovery,
expose the common interface, apply only to the indicators they declare, and
the engine consumes them exclusively through the registry.
"""

from __future__ import annotations

import unittest

from app.services.context_plugins import all_plugins, applicable_plugins
from app.services.context_plugins.base import ContextPlugin


class RegistryTest(unittest.TestCase):
    def test_all_seven_contexts_discovered(self) -> None:
        ids = {p.id for p in all_plugins()}
        self.assertEqual(ids, {
            "fy_end", "framework", "national_supplier", "emergency",
            "corrigendum", "works_programme", "award_window",
        })

    def test_common_interface(self) -> None:
        for p in all_plugins():
            self.assertIsInstance(p, ContextPlugin)
            self.assertTrue(p.id and p.name)
            self.assertTrue(p.indicator_priority)          # applicability declared
            self.assertTrue(p.verification_questions())    # questions exist
            self.assertIsInstance(p.references(), list)    # authority references

    def test_applicability_is_scoped(self) -> None:
        # A plugin only applies to the indicators it declares.
        frag = [p.id for p in applicable_plugins("contract_fragmentation")]
        self.assertEqual(frag, ["works_programme", "fy_end"])  # declared order preserved
        self.assertEqual([p.id for p in applicable_plugins("missing_award_data")], ["award_window"])
        self.assertEqual(applicable_plugins("gst_overlap"), [])  # no context claims it

    def test_per_indicator_ordering_preserved(self) -> None:
        # The pre-refactor presentation order per indicator is exactly preserved.
        self.assertEqual(
            [p.id for p in applicable_plugins("award_clustering")],
            ["fy_end", "framework", "national_supplier", "emergency"],
        )
        self.assertEqual(
            [p.id for p in applicable_plugins("repeat_supplier")],
            ["framework", "national_supplier", "fy_end"],
        )
        self.assertEqual(
            [p.id for p in applicable_plugins("single_bidder")],
            ["emergency", "framework"],
        )


if __name__ == "__main__":
    unittest.main()
