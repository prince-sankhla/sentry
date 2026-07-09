from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.webintel.evidence_taxonomy import classify_evidence
from app.webintel.intelligence import build_intelligence, build_intelligence_item, confidence_for
from app.webintel.source_authority import classify_source


class SourceAuthorityTest(unittest.TestCase):
    def test_government_portal_admitted(self) -> None:
        c = classify_source("https://eprocure.gov.in/cppp/tender/123")
        self.assertTrue(c.admissible)
        self.assertEqual(c.source_type, "government_portal")

    def test_gem_admitted(self) -> None:
        self.assertTrue(classify_source("https://gem.gov.in/bid/456").admissible)

    def test_state_eproc_nic_admitted(self) -> None:
        self.assertTrue(classify_source("https://mahatenders.gov.in/nicgep/app").admissible)

    def test_cag_is_oversight(self) -> None:
        c = classify_source("https://cag.gov.in/en/audit-report/details/2024")
        self.assertTrue(c.admissible)
        self.assertEqual(c.source_type, "oversight_body")

    def test_cvc_is_oversight(self) -> None:
        self.assertEqual(classify_source("https://cvc.gov.in/notice").source_type, "oversight_body")

    def test_court_judgment_is_judicial(self) -> None:
        c = classify_source("https://indiankanoon.org/doc/123456/")
        self.assertTrue(c.admissible)
        self.assertEqual(c.source_type, "judicial")

    def test_sebi_is_regulator(self) -> None:
        self.assertEqual(classify_source("https://www.sebi.gov.in/filings/x.html").source_type, "regulator")

    def test_official_pdf_on_gov_host_boosted(self) -> None:
        page = classify_source("https://cag.gov.in/reports/audit-2024.pdf")
        self.assertTrue(page.admissible)
        # PDF boost pushes an oversight PDF above the bare oversight weight.
        self.assertGreater(page.authority, classify_source("https://cag.gov.in/x").authority)

    # --- rejections ---
    def test_wikipedia_rejected(self) -> None:
        self.assertFalse(classify_source("https://en.wikipedia.org/wiki/Tata").admissible)

    def test_shopping_rejected(self) -> None:
        self.assertFalse(classify_source("https://www.amazon.in/dp/B0/tender-book").admissible)
        self.assertFalse(classify_source("https://www.indiamart.com/proddetail/tender").admissible)

    def test_blog_path_rejected(self) -> None:
        self.assertFalse(classify_source("https://example.com/blog/best-tenders").admissible)

    def test_marketing_utm_rejected(self) -> None:
        self.assertFalse(classify_source("https://acme.com/landing?utm_source=google").admissible)

    def test_generic_company_homepage_rejected(self) -> None:
        self.assertFalse(classify_source("https://www.tcs.com/").admissible)

    def test_linkedin_rejected(self) -> None:
        self.assertFalse(classify_source("https://www.linkedin.com/company/infosys").admissible)


class EvidenceTaxonomyTest(unittest.TestCase):
    def _src(self, url: str):
        return classify_source(url)

    def test_award_notice_in_contracts(self) -> None:
        src = self._src("https://eprocure.gov.in/x")
        ev = classify_evidence(src, title="Notification of Award to ABC Ltd", url="https://eprocure.gov.in/x", text="letter of award")
        self.assertEqual(ev.evidence_type, "award_notice")
        self.assertEqual(ev.cluster, "contracts")

    def test_debarment_in_compliance(self) -> None:
        src = self._src("https://cvc.gov.in/x")
        ev = classify_evidence(src, title="Firm debarred for 2 years", url="https://cvc.gov.in/x", text="the firm is debarred and banned")
        self.assertEqual(ev.evidence_type, "debarment")
        self.assertEqual(ev.cluster, "compliance")

    def test_blacklisting_in_compliance(self) -> None:
        src = self._src("https://nic.in/x")
        ev = classify_evidence(src, title="Vendor blacklisted", url="https://nic.in/x", text="put on hold and blacklisted")
        self.assertEqual(ev.cluster, "compliance")

    def test_audit_finding_in_audit(self) -> None:
        src = self._src("https://cag.gov.in/x")
        ev = classify_evidence(src, title="Performance Audit Report", url="https://cag.gov.in/x", text="audit observation and audit para")
        self.assertEqual(ev.cluster, "audit")

    def test_court_judgment_in_litigation(self) -> None:
        src = self._src("https://indiankanoon.org/doc/1/")
        ev = classify_evidence(src, title="ABC Ltd vs Union of India", url="https://indiankanoon.org/doc/1/", text="hon'ble high court writ petition")
        self.assertEqual(ev.cluster, "litigation")

    def test_arbitration_in_litigation(self) -> None:
        src = self._src("https://livelaw.in/x")
        ev = classify_evidence(src, title="Arbitral award challenged", url="https://livelaw.in/x", text="section 34 arbitration tribunal award")
        self.assertEqual(ev.evidence_type, "arbitration")

    def test_sebi_filing_in_financial(self) -> None:
        src = self._src("https://sebi.gov.in/x")
        ev = classify_evidence(src, title="Disclosure under Regulation 30", url="https://sebi.gov.in/x", text="sebi disclosure listing obligation")
        self.assertEqual(ev.cluster, "financial")

    def test_default_government_when_no_signal(self) -> None:
        src = self._src("https://eprocure.gov.in/x")
        ev = classify_evidence(src, title="Portal", url="https://eprocure.gov.in/x", text="homepage")
        self.assertEqual(ev.cluster, "government")


class ConfidenceTest(unittest.TestCase):
    def test_official_source_beats_news(self) -> None:
        gov = classify_source("https://cag.gov.in/x")
        news = classify_source("https://biddetail.com/x")
        ev = classify_evidence(gov, title="", url="https://cag.gov.in/x", text="")
        now = datetime.now(timezone.utc)
        gov_conf, _ = confidence_for(gov, ev, None, has_publication_date=True, retrieved_at=now)
        news_conf, _ = confidence_for(news, ev, None, has_publication_date=True, retrieved_at=now)
        self.assertGreater(gov_conf, news_conf)

    def test_confidence_bounded(self) -> None:
        gov = classify_source("https://cag.gov.in/x.pdf")
        ev = classify_evidence(gov, title="audit report", url="https://cag.gov.in/x.pdf", text="audit observation audit para cag report")
        conf, tier = confidence_for(gov, ev, None, has_publication_date=True, retrieved_at=datetime.now(timezone.utc))
        self.assertLessEqual(conf, 1.0)
        self.assertIn(tier, {"high", "medium", "low", "weak"})


class _FakeEvidence:
    """Minimal stand-in for a WebEvidence row (no DB needed)."""

    def __init__(self, url: str, title: str, content: str, proc=None):
        self.id = url
        self.url = url
        self.title = title
        self.content = content
        self.source = "test"
        self.retrieved_at = datetime.now(timezone.utc)
        self.procurement_evidence = proc


class BuildIntelligenceTest(unittest.TestCase):
    def test_inadmissible_dropped(self) -> None:
        ev = _FakeEvidence("https://en.wikipedia.org/wiki/X", "X", "tender award contract")
        self.assertIsNone(build_intelligence_item(ev))

    def test_admissible_item_has_full_provenance(self) -> None:
        ev = _FakeEvidence(
            "https://eprocure.gov.in/award/1",
            "Notification of Award to ABC Ltd",
            "letter of award; award of contract to ABC Ltd",
        )
        item = build_intelligence_item(ev)
        self.assertIsNotNone(item)
        assert item is not None
        self.assertEqual(item.cluster, "contracts")
        self.assertTrue(item.citation)
        self.assertTrue(item.evidence_summary)
        self.assertTrue(item.url)
        self.assertGreater(item.confidence, 0)

    def test_clusters_grouped_and_nonempty(self) -> None:
        evs = [
            _FakeEvidence("https://cag.gov.in/audit/1", "Audit Report", "audit observation audit para"),
            _FakeEvidence("https://cvc.gov.in/deb/1", "Firm debarred", "debarred and banned firm"),
            _FakeEvidence("https://indiankanoon.org/doc/1/", "A vs B", "high court writ petition"),
            _FakeEvidence("https://amazon.in/dp/1", "Buy now", "tender"),  # dropped
        ]
        result = build_intelligence("acme", evs)
        self.assertEqual(result.total_items, 3)
        clusters = {c.cluster for c in result.clusters}
        self.assertEqual(clusters, {"audit", "compliance", "litigation"})
        for c in result.clusters:
            self.assertGreaterEqual(c.count, 1)


class ProcurementRelevanceGateTest(unittest.TestCase):
    """BUG 3: admissions / college / contact / marketing must be rejected even
    on allow-listed government or educational hosts."""

    def test_admissions_page_rejected(self) -> None:
        from app.webintel.source_authority import classify_source, is_procurement_relevant
        url = "https://du.ac.in/admissions/apply"
        self.assertFalse(classify_source(url).admissible)

    def test_contact_page_on_gov_host_rejected(self) -> None:
        from app.webintel.source_authority import classify_source
        # A contact/about page is not procurement intelligence even on a gov host.
        self.assertFalse(classify_source("https://eprocure.gov.in/contact-us").admissible)
        self.assertFalse(classify_source("https://eprocure.gov.in/about-us").admissible)

    def test_college_content_without_procurement_signal_rejected(self) -> None:
        from app.webintel.source_authority import is_procurement_relevant
        self.assertFalse(is_procurement_relevant(
            "Undergraduate Admissions", "https://college.edu/ug",
            "Apply now. Prospectus, syllabus, hostel, scholarship, faculty, alumni.",
        ))

    def test_marketing_page_rejected(self) -> None:
        from app.webintel.source_authority import is_procurement_relevant
        self.assertFalse(is_procurement_relevant(
            "Buy Pumps Online", "https://vendor.com/products/pump",
            "best price. add to cart. buy now. book now.",
        ))

    def test_university_tender_pdf_admitted(self) -> None:
        # A genuine Delhi University tender PDF IS procurement intelligence.
        from app.webintel.source_authority import classify_source, is_procurement_relevant
        url = "https://du.ac.in/tenders/nit-2026-05.pdf"
        self.assertTrue(classify_source(url).admissible)
        self.assertTrue(is_procurement_relevant(
            "Notice Inviting Tender", url,
            "e-tender for supply of laboratory equipment. EMD, bid submission, corrigendum.",
        ))

    def test_intelligence_item_dropped_when_not_relevant(self) -> None:
        # An admissible host but non-procurement content is dropped by build_intelligence_item.
        ev = _FakeEvidence(
            "https://xyz.gov.in/notice/welcome",
            "Welcome to our department",
            "about us. our team. contact us. photo gallery. events.",
        )
        self.assertIsNone(build_intelligence_item(ev))


if __name__ == "__main__":
    unittest.main()
