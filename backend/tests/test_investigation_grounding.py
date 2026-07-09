from __future__ import annotations

import unittest

from app.services.investigation_grounding import (
    numeric_atoms,
    verify_summary,
)


class NumericAtomsTest(unittest.TestCase):
    def test_plain_integers(self) -> None:
        self.assertEqual(numeric_atoms("reviewed 12 records"), {"12"})

    def test_grouping_commas_normalized(self) -> None:
        # Indian and western grouping both reduce to the bare number.
        self.assertEqual(numeric_atoms("₹5,00,000 award"), {"500000"})
        self.assertEqual(numeric_atoms("1,200 tenders"), {"1200"})

    def test_percentage_reduces_to_number(self) -> None:
        self.assertEqual(numeric_atoms("60% share"), {"60"})

    def test_decimal_zero_fraction_normalized(self) -> None:
        # "5.0x" and "5x" are the same asserted quantity.
        self.assertEqual(numeric_atoms("5.0x the mean"), numeric_atoms("5x the mean"))

    def test_spelled_numbers_counted(self) -> None:
        self.assertIn("7", numeric_atoms("seven awards"))
        self.assertIn("2", numeric_atoms("two repeat suppliers"))

    def test_no_numbers(self) -> None:
        self.assertEqual(numeric_atoms("risk is elevated"), set())


class VerifySummaryTest(unittest.TestCase):
    def _context(self) -> str:
        return (
            "Subject: Acme Corp (type: supplier)\n"
            "Procurement records: 12\n"
            "Resolved entities: 3\n"
            "- [high/85] Buyer Concentration: Acme wins 60% of tenders (tenders: T-1, T-2)\n"
            "Highest-value tender is 5x the mean estimated value."
        )

    def test_grounded_summary_passes(self) -> None:
        summary = (
            "Investigation of Acme Corp reviewed 12 records across 3 entities. "
            "Risk is HIGH: the buyer awards 60% of its tenders to Acme, and the "
            "top tender is 5x the mean value."
        )
        verdict = verify_summary(summary, self._context())
        self.assertTrue(verdict.grounded, verdict.reason)
        self.assertEqual(verdict.ungrounded_numbers, [])

    def test_fabricated_value_is_rejected(self) -> None:
        # ₹90,00,000 never appears in the context — classic hallucinated figure.
        summary = (
            "Acme Corp received awards totalling ₹90,00,000 across 12 records, "
            "indicating HIGH risk."
        )
        verdict = verify_summary(summary, self._context())
        self.assertFalse(verdict.grounded)
        self.assertIn("9000000", verdict.ungrounded_numbers)

    def test_fabricated_percentage_is_rejected(self) -> None:
        summary = "Acme wins 95% of all tenders in the region, a HIGH risk."
        verdict = verify_summary(summary, self._context())
        self.assertFalse(verdict.grounded)
        self.assertIn("95", verdict.ungrounded_numbers)

    def test_ubiquitous_one_allowed(self) -> None:
        # "a single bidder" / "1" is generic prose, not an evidence claim.
        summary = "Risk is HIGH because this looks like a single-bidder pattern."
        self.assertTrue(verify_summary(summary, self._context()).grounded)

    def test_prose_without_numbers_passes(self) -> None:
        summary = "The assessment is preliminary; evidence is thin but adverse."
        self.assertTrue(verify_summary(summary, self._context()).grounded)

    def test_empty_summary_is_not_grounded(self) -> None:
        self.assertFalse(verify_summary("   ", self._context()).grounded)

    def test_spelled_number_must_trace(self) -> None:
        # "twenty entities" contradicts "3 entities" in context -> rejected.
        summary = "The investigation spans twenty resolved entities at HIGH risk."
        verdict = verify_summary(summary, self._context())
        self.assertFalse(verdict.grounded)
        self.assertIn("20", verdict.ungrounded_numbers)


if __name__ == "__main__":
    unittest.main()
