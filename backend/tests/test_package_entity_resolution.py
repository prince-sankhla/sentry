from __future__ import annotations

import unittest

from app.entity_resolution.package_resolver import InvestigationEntityResolver
from app.schemas.investigation_executor import (
    InvestigationCompanyResult,
    InvestigationPackage,
    InvestigationProcurementRecord,
    InvestigationSourceMetadata,
    InvestigationTenderResult,
)
from app.schemas.investigation_planner import InvestigationPlan


class InvestigationEntityResolverTest(unittest.TestCase):
    def test_merges_companies_by_registration_number(self) -> None:
        package = _package(
            [
                _record("T-1", _company("Acme Private Limited", registration_number="IN-123")),
                _record("T-2", _company("ACME Pvt Ltd", registration_number="IN123")),
            ]
        )

        resolved = InvestigationEntityResolver().resolve_package(package)

        self.assertEqual(len(resolved.canonical_companies), 1)
        canonical = resolved.canonical_companies[0]
        self.assertEqual(canonical.confidence, 1.0)
        self.assertEqual({source.match_reason for source in canonical.matched_sources}, {"seed", "registration_number"})
        self.assertEqual(resolved.records[0].canonical_company_ids, [canonical.id])
        self.assertEqual(resolved.records[1].canonical_company_ids, [canonical.id])
        self.assertEqual(resolved.records[0].companies[0].canonical_company_id, canonical.id)

    def test_merges_companies_by_fuzzy_name_and_address(self) -> None:
        package = _package(
            [
                _record("T-1", _company("North River Technologies Limited", address="10 Market Road, Mumbai")),
                _record("T-2", _company("North River Technology Ltd.", address="10 Market Rd Mumbai")),
            ]
        )

        resolved = InvestigationEntityResolver().resolve_package(package)

        self.assertEqual(len(resolved.canonical_companies), 1)
        self.assertIn("fuzzy_name_address", {source.match_reason for source in resolved.canonical_companies[0].matched_sources})

    def test_keeps_conflicting_registration_numbers_separate(self) -> None:
        package = _package(
            [
                _record("T-1", _company("Acme Private Limited", registration_number="IN-123")),
                _record("T-2", _company("Acme Private Limited", registration_number="IN-999")),
            ]
        )

        resolved = InvestigationEntityResolver().resolve_package(package)

        self.assertEqual(len(resolved.canonical_companies), 2)
        self.assertNotEqual(resolved.records[0].canonical_company_ids, resolved.records[1].canonical_company_ids)


def _package(records: list[InvestigationProcurementRecord]) -> InvestigationPackage:
    return InvestigationPackage(
        plan=InvestigationPlan(
            query="acme",
            investigation_type="company",
            confidence=0.8,
            connectors=["test"],
            modules=["company_connectors", "graph"],
            steps=[],
        ),
        records=records,
    )


def _record(reference_number: str, company: InvestigationCompanyResult) -> InvestigationProcurementRecord:
    return InvestigationProcurementRecord(
        tender=InvestigationTenderResult(
            reference_number=reference_number,
            title=f"Tender {reference_number}",
            description=None,
            procuring_entity=None,
            published_date=None,
            closing_date=None,
            estimated_value=None,
            currency="USD",
            metadata=_metadata(reference_number),
        ),
        companies=[company],
    )


def _company(
    name: str,
    *,
    registration_number: str | None = None,
    tax_id: str | None = None,
    company_identifier: str | None = None,
    address: str | None = None,
    website: str | None = None,
) -> InvestigationCompanyResult:
    return InvestigationCompanyResult(
        name=name,
        registration_number=registration_number,
        tax_id=tax_id,
        company_identifier=company_identifier,
        address=address,
        website=website,
        metadata=_metadata(f"company:{name}"),
    )


def _metadata(source_record_id: str) -> InvestigationSourceMetadata:
    return InvestigationSourceMetadata(
        source_name="test",
        source_record_id=source_record_id,
        source_url=None,
        retrieved_at=None,
    )


if __name__ == "__main__":
    unittest.main()
