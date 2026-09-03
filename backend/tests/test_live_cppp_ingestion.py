from __future__ import annotations

import unittest

from app.services.live_cppp_ingestion import LiveCPPPIngestion, LiveCPPPIngestionError


class LiveCPPPValidationTest(unittest.TestCase):
    def test_accepts_official_cppp_url(self) -> None:
        service = LiveCPPPIngestion()
        url = "https://eprocure.gov.in/eprocure/app?component=%24DirectLink_0&page=Home&service=direct&sp=abc"
        self.assertEqual(service._validate_url(url), url)

    def test_rejects_non_cppp_host(self) -> None:
        service = LiveCPPPIngestion()
        with self.assertRaises(LiveCPPPIngestionError):
            service._validate_url("https://example.com/tender")

    def test_extracts_tender_id_from_html(self) -> None:
        service = LiveCPPPIngestion()
        html = "<td class='td_caption'>Tender ID</td><td class='td_field'>2026_REIL_917353_1</td>"
        self.assertEqual(service._extract_tender_id(html), "2026_REIL_917353_1")

    def test_extracts_tender_id_from_reference_text(self) -> None:
        service = LiveCPPPIngestion()
        self.assertEqual(service._extract_tender_id("Tender ID: 2026_DIT_918004_1"), "2026_DIT_918004_1")


if __name__ == "__main__":
    unittest.main()
