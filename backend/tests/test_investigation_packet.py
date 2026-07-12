"""Evidence Packet tests — the 15-section auditor deliverable + HTML export.

Builds synthetic packages (no DB), assembles the packet through the real
builder, and asserts every required section is grounded, the HTML export is
self-contained/print-ready, and untrusted text is escaped (no injection).
"""

from __future__ import annotations

import re
import unittest
from datetime import datetime, timezone

from app.services.investigation_packet import build_packet_document, render_packet_html
from app.services.investigation_reasoning import build_reasoning
from app.services.risk_engine import assess_risk_v2

from tests.test_investigation_quality import _package, _record

_WHEN = datetime(2026, 7, 11, tzinfo=timezone.utc)


def _packet_for(records, subject="Acme Corp"):
    pkg = _package(records)
    pkg.risk_assessment_v2 = assess_risk_v2(pkg)
    reasoning = build_reasoning(pkg, subject)
    return build_packet_document(pkg, reasoning, subject=subject, generated_at=_WHEN), pkg, reasoning


class PacketSectionsTest(unittest.TestCase):
    def setUp(self) -> None:
        records = [_record(f"T-{i}", "Public Works Dept", ["Acme Ltd"], value="200000000",
                           published=None, docs=True) for i in range(4)]
        self.doc, self.pkg, self.reasoning = _packet_for(records)

    def test_identity_sections_present(self) -> None:  # 1,2,3
        self.assertTrue(self.doc.title)
        self.assertTrue(self.doc.investigation_id.startswith("SENTRY-CASE-"))
        self.assertEqual(self.doc.generated_at, "2026-07-11")

    def test_methodology_and_typologies(self) -> None:  # 4,6
        self.assertGreaterEqual(len(self.doc.methodology), 5)
        self.assertTrue(self.doc.typologies)

    def test_tenders_documents_urls(self) -> None:  # 7,8,9
        self.assertEqual(len(self.doc.tenders), 4)
        self.assertTrue(self.doc.documents)
        self.assertTrue(self.doc.source_urls)
        # Every tender is traceable to a source URL.
        self.assertTrue(all(t.source_url for t in self.doc.tenders))

    def test_confidence_and_alternatives_and_checklist(self) -> None:  # 10,12,13
        self.assertGreaterEqual(self.doc.confidence_pct, 0)
        self.assertTrue(self.doc.alternative_explanations)  # every typology gets a benign counter-hypothesis
        self.assertTrue(self.doc.verification_checklist)

    def test_verification_level_is_verified_with_documents(self) -> None:
        self.assertEqual(self.doc.verification_level, "VERIFIED")

    def test_buyer_hierarchy_shows_specific_unit(self) -> None:
        # A pipe-delimited ``category||unit`` buyer must not collapse to the generic
        # first segment — the specific procuring body must stay visible (CASE #001:
        # "Municipal Bodies||Dharmagarh NAC" must not render as just "Municipal Bodies").
        doc, *_ = _packet_for(
            [_record("T-9", "Municipal Bodies||Dharmagarh NAC", ["Acme Ltd"],
                     value="200000000", docs=True)],
            subject="Dharmagarh NAC",
        )
        self.assertTrue(doc.tenders)
        buyer = doc.tenders[0].buyer
        self.assertIn("Dharmagarh NAC", buyer)
        self.assertNotEqual(buyer, "Municipal Bodies")

    def test_packet_id_is_deterministic(self) -> None:
        doc2, *_ = _packet_for([_record(f"T-{i}", "Public Works Dept", ["Acme Ltd"],
                                        value="200000000", docs=True) for i in range(4)])
        self.assertEqual(self.doc.investigation_id, doc2.investigation_id)


class PacketHtmlExportTest(unittest.TestCase):
    def test_html_is_self_contained_and_print_ready(self) -> None:
        doc, *_ = _packet_for([_record("T-1", "PWD", ["Acme Ltd"], value="200000000", docs=True)])
        html = render_packet_html(doc)
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("@media print", html)          # print support
        self.assertIn("window.print()", html)         # one-click print/PDF
        # Self-contained: no external stylesheet/script/image references.
        self.assertNotIn("<link ", html)
        self.assertNotIn("<script src", html)
        self.assertNotIn('src="http', html)
        # Numbered content sections 4..15 all render.
        nums = sorted({int(n) for n in re.findall(r'class="num">(\d+)</span>', html)})
        self.assertEqual(nums, list(range(4, 16)))
        # Oversight disclaimer is present.
        self.assertIn("oversight tool", html.lower())

    def test_untrusted_text_is_escaped(self) -> None:
        # A malicious supplier name must never reach the HTML unescaped.
        evil = 'Acme <script>alert(1)</script> Ltd'
        doc, *_ = _packet_for([_record("T-1", "PWD", [evil], value="200000000", docs=True)])
        html = render_packet_html(doc)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class PacketInsufficientEvidenceTest(unittest.TestCase):
    def test_empty_package_does_not_crash(self) -> None:
        doc, *_ = _packet_for([], subject="Nobody")
        self.assertEqual(doc.verification_level, "UNVERIFIED")
        html = render_packet_html(doc)
        self.assertIn("<!DOCTYPE html>", html)  # still renders a valid document


if __name__ == "__main__":
    unittest.main()
