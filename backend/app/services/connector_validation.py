"""Connector validation & health engine (Phase 6).

Validates every registered connector by joining its declared metadata against
what it has actually imported, and measuring — from the stored rows — its
normalization quality, award coverage and document coverage. Known limitations
are the concrete, audited gaps per connector (documented, not guessed).

Import-capability verdict:
  * ``verified``        — the connector has imported rows in the database
  * ``capable_no_data`` — registered with a raw directory but no rows yet
  * ``registered_only`` — registered without a file-backed raw directory
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.parse import now_utc
from app.connectors.common.source_priority import is_indian_source, source_rank
from app.connectors.registry import discover_connectors
from app.models import Award, Company, Document, SourceRecordVersion, Tender
from app.normalization import normalize_org_name
from app.schemas.connector_validation import ConnectorHealthReport, ConnectorValidation

_STALE_DAYS = 30

# Audited, connector-specific known limitations (deterministic; from the
# procurement connector audit). Sources not listed have no material gap.
_KNOWN_LIMITATIONS: dict[str, list[str]] = {
    "cppp": [
        "NIC HTML notices are tender-only: awards/companies are not extracted from the notice body.",
    ],
    "gem": [
        "Flat mapper captures only the first supplier/award per row (one-award-per-record feeds only).",
    ],
    "world_bank": [
        "Award parsing depends on the notice_text HTML block; malformed notices yield tender-only records.",
    ],
    "cag": [
        "Audit-report source rarely carries supplier/award data; primarily tender + document coverage.",
    ],
    "datagovin": [
        "Column shapes vary per dataset; generic hints may miss non-standard award columns.",
    ],
    "prozorro": [
        "Ukrainian (non-Indian) source; retained for methodology validation, not Indian coverage.",
    ],
    "adb": ["Multilateral (non-Indian) source; USD-denominated."],
    "un_procurement": ["Multilateral (non-Indian) source; USD-denominated."],
}

# State NIC portals share the CPPP HTML limitation on their HTML path.
_STATE_LIMITATION = (
    "NIC HTML path is tender-only (no awards); flat/JSON exports do carry awards."
)


def build_connector_health_report(db: Session) -> ConnectorHealthReport:
    registry = discover_connectors()
    connectors_meta = {c.metadata.name: c.metadata for c in registry.all()}

    tenders_by_source = _count(db, Tender.source_name, Tender.id)
    awards_by_source = _count(db, Award.source_name, Award.id)
    companies_by_source = _count(db, Company.source_name, Company.id)
    documents_by_source = _count(db, Document.source_name, Document.id)
    versions_by_source = _count(db, SourceRecordVersion.source_name, SourceRecordVersion.id)
    tenders_with_docs = _tenders_with_docs_by_source(db)
    freshness = _freshness(db)
    now = now_utc()

    validations: list[ConnectorValidation] = []
    for name, meta in sorted(connectors_meta.items(), key=lambda kv: source_rank(kv[0])):
        tenders = tenders_by_source.get(name, 0)
        awards = awards_by_source.get(name, 0)
        docs = documents_by_source.get(name, 0)
        retrieved_at = freshness.get(name)
        freshness_days = (now - retrieved_at).days if retrieved_at else None

        if tenders == 0:
            capability = "capable_no_data" if meta.raw_directory else "registered_only"
            health = "no_data"
        elif freshness_days is not None and freshness_days > _STALE_DAYS:
            capability, health = "verified", "stale"
        else:
            capability, health = "verified", "active"

        limitations = list(_KNOWN_LIMITATIONS.get(name, []))
        if name.startswith("eproc_"):
            limitations.append(_STATE_LIMITATION)
            if source_rank(name) >= 200:
                limitations.append("Portal not yet ranked in source_priority (Indian-unknown bucket).")

        validations.append(
            ConnectorValidation(
                name=name,
                label=meta.label,
                is_indian=is_indian_source(name),
                priority_rank=source_rank(name),
                tenders=tenders,
                awards=awards,
                companies=companies_by_source.get(name, 0),
                documents=docs,
                versions=versions_by_source.get(name, 0),
                import_mechanism=meta.import_mechanism,
                last_update_capability=meta.last_update_capability,
                normalization_quality_declared=meta.normalization_quality,
                supported_entities=list(meta.supported_entities),
                raw_directory=meta.raw_directory,
                normalization_score=_normalization_score(db, name),
                award_coverage=round(awards / tenders, 4) if tenders else 0.0,
                document_coverage=round(tenders_with_docs.get(name, 0) / tenders, 4) if tenders else 0.0,
                import_capability=capability,
                health=health,
                known_limitations=limitations,
            )
        )

    return ConnectorHealthReport(
        generated_at=now.isoformat(),
        connectors_registered=len(connectors_meta),
        connectors_with_data=sum(1 for v in validations if v.tenders > 0),
        indian_connectors=sum(1 for v in validations if v.is_indian),
        connectors=validations,
    )


def _count(db: Session, source_column, id_column) -> dict[str, int]:
    return {
        name: int(count)
        for name, count in db.execute(
            select(source_column, func.count(id_column))
            .where(source_column.is_not(None))
            .group_by(source_column)
        ).all()
    }


def _tenders_with_docs_by_source(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Tender.source_name, func.count(func.distinct(Tender.id)))
        .select_from(Tender)
        .join(Document, Document.tender_id == Tender.id)
        .where(Tender.source_name.is_not(None))
        .group_by(Tender.source_name)
    ).all()
    return {name: int(count) for name, count in rows}


def _freshness(db: Session) -> dict:
    rows = db.execute(
        select(Tender.source_name, func.max(Tender.retrieved_at))
        .where(Tender.source_name.is_not(None), Tender.retrieved_at.is_not(None))
        .group_by(Tender.source_name)
    ).all()
    return {name: retrieved for name, retrieved in rows if retrieved is not None}


def _normalization_score(db: Session, source_name: str) -> float:
    """Measured normalization quality for a source: share of buyer + supplier
    names already in canonical form."""
    buyers = [
        buyer
        for (buyer,) in db.execute(
            select(Tender.procuring_entity)
            .where(Tender.source_name == source_name, Tender.procuring_entity.is_not(None))
            .distinct()
        ).all()
    ]
    companies = [
        name
        for (name,) in db.execute(
            select(Company.name).where(Company.source_name == source_name)
        ).all()
    ]
    values = buyers + companies
    if not values:
        return 0.0
    normalized = sum(1 for value in values if value and normalize_org_name(value) == value)
    return round(normalized / len(values), 4)
