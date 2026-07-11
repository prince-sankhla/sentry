"""Unit tests for the deterministic procurement taxonomy classifiers."""

from __future__ import annotations

from datetime import date

from app.services import procurement_taxonomy as tax


class TestStateClassifier:
    def test_direct_state_name(self) -> None:
        assert tax.state_of("Government of Kerala") == "Kerala"
        assert tax.state_of("PWD", "Road works in Tamil Nadu") == "Tamil Nadu"

    def test_alias(self) -> None:
        assert tax.state_of("UP Rural Works Dept") == "Uttar Pradesh"
        assert tax.state_of("New Delhi Municipal Council") == "Delhi"

    def test_unattributed(self) -> None:
        assert tax.state_of("World Bank", "Global procurement") == tax.UNATTRIBUTED


class TestMinistryClassifier:
    def test_ministry_extraction(self) -> None:
        assert tax.ministry_of("Ministry of Health and Family Welfare") == "Ministry Of Health And Family Welfare"

    def test_department_extraction(self) -> None:
        assert tax.ministry_of("Department of Roads, State X").startswith("Department Of Roads")

    def test_unattributed(self) -> None:
        assert tax.ministry_of("Some Local Body") == tax.UNATTRIBUTED
        assert tax.ministry_of(None) == tax.UNATTRIBUTED


class TestCategoryClassifier:
    def test_categories(self) -> None:
        assert tax.category_of("Construction of rural road") == "Construction & Roads"
        assert tax.category_of("Supply of hospital medicine") == "Medical & Health"
        assert tax.category_of("Procurement of laptops and servers") == "IT & Software"

    def test_other(self) -> None:
        assert tax.category_of("Miscellaneous zzz") == tax.OTHER


class TestMethodClassifier:
    def test_methods(self) -> None:
        assert tax.procurement_method_of("Open tender for road works") == "Open Tender"
        assert tax.procurement_method_of("Single tender direct award") == "Single / Direct"
        assert tax.procurement_method_of("Request for Proposal (RFP)") == "Request for Proposal"

    def test_unspecified(self) -> None:
        assert tax.procurement_method_of("Supply of goods") == tax.UNSPECIFIED


class TestYearClassifier:
    def test_year(self) -> None:
        assert tax.year_of(date(2026, 3, 1)) == "2026"
        assert tax.year_of(None) == tax.UNSPECIFIED
