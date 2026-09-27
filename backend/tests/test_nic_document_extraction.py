from unittest import TestCase

from app.connectors.common.envelope import _extract_nic_documents


class NicDocumentExtractionTests(TestCase):
    def test_extracts_nit_and_work_item_documents(self) -> None:
        html = """
        <a id="docDownoad" href="/nicgep/app?component=docDownoad&page=FrontEndTenderDetails&service=direct&session=T">
          Tendernotice_1.pdf
        </a>
        <div id="workItemDocumenttable">
          <table>
            <tr id="informal_0">
              <td>01</td>
              <td>BOQ</td>
              <td><span>BOQ_1.pdf</span></td>
              <td><a href="/nicgep/app?component=docDownoad_0&page=FrontEndTenderDetails&service=direct&session=T">Download</a></td>
            </tr>
          </table>
        </div>
        """
        docs = _extract_nic_documents(html, "https://tendersodisha.gov.in/nicgep/app")
        self.assertEqual(
            [
                ("Tendernotice_1.pdf", "nit"),
                ("BOQ_1.pdf", "boq"),
            ],
            [(doc["title"], doc["document_type"]) for doc in docs],
        )
        self.assertTrue(docs[0]["url"].startswith("https://tendersodisha.gov.in/"))
        self.assertTrue(docs[1]["url"].startswith("https://tendersodisha.gov.in/"))

    def test_deduplicates_repeated_nit_anchor(self) -> None:
        html = """
        <a id="docDownoad" href="/doc/1">Tendernotice_1.pdf</a>
        <a id="docDownoad_0" href="/doc/1">Tendernotice_1.pdf</a>
        """
        docs = _extract_nic_documents(html, "https://example.gov")
        self.assertEqual(1, len(docs))


if __name__ == "__main__":
    import unittest
    unittest.main()
