from __future__ import annotations

import unittest

from app.services.pdf_intelligence import extract_tender_fields, parse_indian_amount


_SAMPLE = """
NOTICE INVITING TENDER
Tender Reference No: RJ/PWD/2026/0456
Name of Work: Construction of rural road in Jaipur district
Estimated Cost: Rs. 2.5 Crore
Tender Value: Rs. 2,50,00,000
EMD: Rs. 5,00,000
Tender Fee: Rs. 5000
Department: Public Works Department
Location: Jaipur, Rajasthan
BOQ No: BOQ/2026/0456
Eligibility Criteria: Class A contractor with 5 years experience and turnover of 3 crore
Last Date of Submission: 15-Feb-2026 17:00
Bid Opening Date: 16-Feb-2026 11:00
Category: Civil Works
No. of Bids Received: 1
Awarded to M/s Acme Infra Pvt Ltd
Accepted Value: Rs. 2.48 Crore
"""


class PdfIntelligenceTest(unittest.TestCase):
    def test_reference_not_fragmented(self) -> None:
        r = extract_tender_fields(_SAMPLE)
        self.assertIsNotNone(r.tender_reference)
        self.assertEqual(r.tender_reference.value, "RJ/PWD/2026/0456")

    def test_new_fields_extracted(self) -> None:
        r = extract_tender_fields(_SAMPLE)
        self.assertEqual(r.department.value, "Public Works Department")
        self.assertEqual(r.location.value, "Jaipur, Rajasthan")
        self.assertEqual(r.boq_reference.value, "BOQ/2026/0456")
        self.assertIsNotNone(r.eligibility)
        self.assertIn("Class A", r.eligibility.value)
        self.assertIn("Acme", r.awarded_to.value)
        self.assertIsNotNone(r.award_value)

    def test_every_field_keeps_source_span(self) -> None:
        r = extract_tender_fields(_SAMPLE)
        for field in r.fields:
            self.assertTrue(field.source_span, field.name)

    def test_empty_text(self) -> None:
        r = extract_tender_fields("")
        self.assertTrue(r.empty)
        self.assertEqual(r.coverage, 0.0)

    def test_parse_indian_amount(self) -> None:
        self.assertEqual(parse_indian_amount("Rs. 2.5 Crore"), 25000000)
        self.assertEqual(parse_indian_amount("5 Lakh"), 500000)


if __name__ == "__main__":
    unittest.main()
