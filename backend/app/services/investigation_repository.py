"""Database-backed record source for investigations.

Returns the same ``NormalizedProcurementRecord`` shape the file-backed
connectors produce, so the InvestigationExecutor and all package projections
(entities, evidence, timeline, graph) work unchanged — but sourced from the
real imported PostgreSQL data instead of raw files on disk.
"""

from __future__ import annotations

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.connectors.base import (
    NormalizedAward,
    NormalizedCompany,
    NormalizedDocument,
    NormalizedProcurementRecord,
    NormalizedSourceMetadata,
    NormalizedTender,
)
from app.connectors.common.source_priority import _SOURCE_RANK, _UNKNOWN_RANK
from app.models import Award, Company, Document, Tender


class DatabaseRecordSource:
    """Exposes ``.search(query, source_names, limit)`` matching SourceManager."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        query: str,
        *,
        source_names: list[str] | None = None,
        limit: int = 25,
    ) -> list[NormalizedProcurementRecord]:
        term = f"%{query.strip()}%"
        if not query.strip():
            return []

        company_tender_ids = (
            select(Award.tender_id).join(Company, Award.company_id == Company.id).where(Company.name.ilike(term))
        )
        conditions = or_(
            Tender.title.ilike(term),
            Tender.procuring_entity.ilike(term),
            Tender.reference_number.ilike(term),
            Tender.description.ilike(term),
            Tender.id.in_(company_tender_ids),
        )
        statement = (
            select(Tender)
            .where(conditions)
            .options(
                selectinload(Tender.awards).joinedload(Award.company),
                selectinload(Tender.documents),
            )
            # Indian procurement first: rank Indian sources ahead of international
            # ones, then fall back to recency. This is the primary investigation
            # retrieval path, so every package is Indian-weighted by construction.
            .order_by(
                _source_rank_ordering().asc(),
                Tender.published_date.desc().nullslast(),
                Tender.created_at.desc(),
            )
            .limit(limit)
        )
        if source_names:
            statement = statement.where(Tender.source_name.in_(source_names))

        return [self._to_record(tender) for tender in self.session.scalars(statement).unique()]

    def _to_record(self, tender: Tender) -> NormalizedProcurementRecord:
        tender_meta = self._metadata(tender.source_name, tender.source_record_id, tender.source_url, tender)
        normalized_tender = NormalizedTender(
            reference_number=tender.reference_number,
            title=tender.title,
            description=tender.description,
            procuring_entity=tender.procuring_entity,
            published_date=tender.published_date,
            closing_date=tender.closing_date,
            estimated_value=tender.estimated_value,
            currency=tender.currency,
            metadata=tender_meta,
        )

        companies: list[NormalizedCompany] = []
        awards: list[NormalizedAward] = []
        seen_companies: set[str] = set()
        for award in tender.awards:
            company = award.company
            if company is None:
                continue
            if company.id.hex not in seen_companies:
                seen_companies.add(company.id.hex)
                companies.append(
                    NormalizedCompany(
                        name=company.name,
                        registration_number=company.registration_number,
                        metadata=self._metadata(
                            company.source_name, company.source_record_id, company.source_url, company
                        ),
                    )
                )
            awards.append(
                NormalizedAward(
                    tender_reference_number=tender.reference_number,
                    company_name=company.name,
                    company_registration_number=company.registration_number,
                    award_date=award.award_date,
                    award_value=award.award_value,
                    currency=award.currency,
                    metadata=self._metadata(award.source_name, award.source_record_id, award.source_url, award),
                )
            )

        documents = [
            NormalizedDocument(
                title=document.title,
                url=document.url or document.local_path,
                document_type=document.document_type,
                metadata=self._metadata(
                    document.source_name, document.source_record_id, document.url, document
                ),
            )
            for document in tender.documents
        ]

        return NormalizedProcurementRecord(
            tender=normalized_tender,
            companies=companies,
            awards=awards,
            documents=documents,
        )

    @staticmethod
    def _metadata(source_name, source_record_id, source_url, row) -> NormalizedSourceMetadata:
        return NormalizedSourceMetadata(
            source_name=source_name or "database",
            source_record_id=source_record_id or (row.reference_number if isinstance(row, Tender) else str(row.id)),
            source_url=source_url,
            retrieved_at=getattr(row, "retrieved_at", None),
        )


def _source_rank_ordering():
    """SQL CASE expression mapping ``Tender.source_name`` to its Indian-first rank.

    Mirrors ``source_priority.source_rank`` for the ranked sources so the DB can
    order Indian procurement ahead of international data in a single query.
    Unranked sources fall to the default bucket and then to recency ordering.
    """
    return case(
        {name: rank for name, rank in _SOURCE_RANK.items()},
        value=Tender.source_name,
        else_=_UNKNOWN_RANK,
    )
