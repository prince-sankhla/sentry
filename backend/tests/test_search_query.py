from __future__ import annotations

import unittest

from app.services.search_query import _entity_terms, expand_terms


class EntityPrecisionTokenTest(unittest.TestCase):
    """P0 precision regression — "Tata Projects" must not collapse to "tata".

    "projects"/"project" are identifying parts of a company name, not stopwords.
    If they are stripped, a supplier query degenerates to the bare group token
    ("tata") and matches any tender whose BUYER or TITLE merely mentions the
    group (e.g. "Tata Memorial Centre" buyer, or a "Tata Tiago" car in a title).
    """

    def test_tata_projects_keeps_projects_token(self) -> None:
        tokens = _entity_terms("Tata Projects Limited")
        self.assertIn("tata", tokens)
        self.assertIn("projects", tokens)  # must NOT be stopworded away
        self.assertNotIn("limited", tokens)  # legal designator still dropped

    def test_multiword_entity_not_reduced_to_single_group_token(self) -> None:
        # The failure mode was a 3-word company reducing to ONE identifying token.
        self.assertGreaterEqual(len(_entity_terms("Tata Projects Limited")), 2)

    def test_legal_designators_still_dropped(self) -> None:
        self.assertEqual(_entity_terms("Acme Ltd Pvt"), ["acme"])


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
