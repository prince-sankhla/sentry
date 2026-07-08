from __future__ import annotations

import unittest

from app.connectors.common.source_priority import (
    indian_first_key,
    is_indian_source,
    prioritize_source_names,
    source_rank,
)


class SourcePriorityTest(unittest.TestCase):
    def test_indian_sources_recognised(self) -> None:
        for name in ("gem", "cppp", "cag", "datagovin", "eproc_rajasthan", "eproc_kerala"):
            self.assertTrue(is_indian_source(name), name)
        for name in ("world_bank", "adb", "un_procurement", "prozorro"):
            self.assertFalse(is_indian_source(name), name)

    def test_unknown_state_portal_is_indian(self) -> None:
        # A newly added NIC state portal not yet individually ranked.
        self.assertTrue(is_indian_source("eproc_gujarat"))

    def test_gem_and_cppp_outrank_international(self) -> None:
        self.assertLess(source_rank("gem"), source_rank("world_bank"))
        self.assertLess(source_rank("cppp"), source_rank("adb"))
        self.assertLess(source_rank("datagovin"), source_rank("prozorro"))

    def test_priority_order_is_indian_first(self) -> None:
        mixed = ["world_bank", "gem", "prozorro", "cppp", "adb", "cag", "eproc_kerala"]
        ordered = prioritize_source_names(mixed)
        # Every Indian source appears before every international source.
        indian_positions = [i for i, n in enumerate(ordered) if is_indian_source(n)]
        intl_positions = [i for i, n in enumerate(ordered) if not is_indian_source(n)]
        self.assertTrue(max(indian_positions) < min(intl_positions))
        self.assertEqual(ordered[0], "gem")
        self.assertEqual(ordered[1], "cppp")

    def test_rajasthan_ranks_ahead_of_other_states(self) -> None:
        self.assertLess(source_rank("eproc_rajasthan"), source_rank("eproc_maharashtra"))
        self.assertLess(source_rank("eproc_maharashtra"), source_rank("eproc_kerala"))

    def test_indian_first_key_buckets(self) -> None:
        self.assertEqual(indian_first_key("gem")[0], 0)
        self.assertEqual(indian_first_key("world_bank")[0], 1)


if __name__ == "__main__":
    unittest.main()
