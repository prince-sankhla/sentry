from __future__ import annotations

import unittest

from app.services.search_query import expand_terms


class SearchSynonymTest(unittest.TestCase):
    def test_query_tokens_preserved(self) -> None:
        self.assertIn("road", expand_terms("road"))

    def test_road_expands_to_highway(self) -> None:
        terms = expand_terms("road")
        self.assertIn("highway", terms)
        self.assertIn("street", terms)

    def test_highway_expands_to_road(self) -> None:
        self.assertIn("road", expand_terms("highway"))

    def test_medical_and_hospital_share_group(self) -> None:
        self.assertIn("hospital", expand_terms("medical"))
        self.assertIn("medical", expand_terms("hospital"))

    def test_railway_synonyms(self) -> None:
        terms = expand_terms("railway")
        self.assertIn("rail", terms)
        self.assertIn("train", terms)

    def test_multiword_query(self) -> None:
        terms = expand_terms("solar power plant")
        self.assertIn("solar", terms)
        self.assertIn("photovoltaic", terms)  # solar synonym
        self.assertIn("power", terms)

    def test_short_tokens_dropped(self) -> None:
        # single chars are noise; ensure they are not emitted
        self.assertEqual(expand_terms("a"), [])

    def test_empty(self) -> None:
        self.assertEqual(expand_terms(""), [])


if __name__ == "__main__":
    unittest.main()
