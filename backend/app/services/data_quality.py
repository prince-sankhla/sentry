"""Deterministic procurement data-quality engine.

Scans the imported ingestion tables and reports, with real counts and concrete
examples, every category of defect that matters before building a procurement
ontology on top. All checks are pure SQL / deterministic normalization — no AI,
no sampling, no fabricated numbers. If the database is empty, every count is
honestly zero.

Checks implemented (Phase 1 full set):
  * missing fields (title / buyer / dates / value / currency)
  * duplicate tenders (same buyer + title + published date)
  * duplicate companies (collapse to one canonical org key)
  * duplicate awards (same tender + company)
  * broken dates (closing before publication)
  * award before publication
  * award before closing
  * invalid values (null / non-positive tender & award values)
  * currency inconsistencies (award currency != tender currency)
  * entity inconsistencies (same registration number, different names)
  * missing buyers / missing suppliers
  * broken references (empty / malformed reference numbers)
  * missing source URLs / missing document URLs / missing evidence
  * corrupted records (award with no tender/company link)
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.connectors.common.envelope import content_hash
from app.connectors.common.parse import now_utc
from app.models import Award, Company, Document, Tender
from app.normalization import normalize_org_name, normalize_reference, org_match_key
from app.schemas.data_quality import CoverageMetric, DataQualityReport, QualityIssue
from app.services import procurement_taxonomy as tax

_EXAMPLE_LIMIT = 10


def build_data_quality_report(db: Session) -> DataQualityReport:
    total_tenders = int(db.scalar(select(func.count(Tender.id))) or 0)
    total_companies = int(db.scalar(select(func.count(Company.id))) or 0)
    total_awards = int(db.scalar(select(func.count(Award.id))) or 0)
    total_documents = int(db.scalar(select(func.count(Document.id))) or 0)

    issues = [
        # missing fields
        _missing_field(db, "missing_titles", "Tenders without a title", Tender.title, total_tenders),
        _missing_buyers(db, total_tenders),
        _missing_published(db, total_tenders),
        _missing_value(db, total_tenders),
        _missing_currency(db, total_tenders),
        _missing_suppliers(db, total_awards),
        # duplicates
        _duplicate_tenders(db),
        _duplicate_companies(db),
        _duplicate_buyers(db),
        _duplicate_awards(db),
        # dates
        _broken_tender_dates(db),
        _award_before_publication(db),
        _award_before_closing(db),
        # values / currency
        _invalid_tender_values(db, total_tenders),
        _invalid_award_values(db, total_awards),
        _award_exceeds_estimate(db),
        _currency_inconsistencies(db),
        # entities
        _entity_inconsistencies(db),
        _registration_conflicts(db),
        _circular_references(db),
        # timelines / methods / locations (Phase 7 advanced)
        _impossible_timelines(db),
        _unclassified_procurement_method(db, total_tenders),
        _location_mismatch(db, total_tenders),
        _negative_values(db),
        # references / provenance / evidence
        _broken_references(db, total_tenders),
        _missing_identifiers(db, total_tenders),
        _missing_source_urls(db, total_tenders),
        _missing_document_urls(db, total_documents),
        _missing_evidence(db, total_tenders),
        _duplicate_documents(db, total_documents),
        _document_checksum_mismatch(db, total_documents),
        _corrupted_awards(db, total_awards),
    ]

    critical = sum(1 for issue in issues if issue.severity == "critical" and issue.count)
    warning = sum(1 for issue in issues if issue.severity == "warning" and issue.count)

    return DataQualityReport(
        generated_at=now_utc().isoformat(),
        total_tenders=total_tenders,
        total_companies=total_companies,
        total_awards=total_awards,
        total_documents=total_documents,
        issues=issues,
        normalization_coverage=_normalization_coverage(db, total_companies),
        evidence_completeness=_evidence_completeness(db, total_tenders, total_documents),
        quality_score=_quality_score(issues),
        critical_issues=critical,
        warning_issues=warning,
    )


# --------------------------------------------------------------------- missing fields


def _missing_field(db: Session, code: str, label: str, column, total: int, severity: str = "warning") -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number).where((column.is_(None)) | (func.trim(column) == ""))
    ).all()
    return _issue(code, label, [r[0] for r in rows], total, severity)


def _missing_buyers(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number).where(
            (Tender.procuring_entity.is_(None)) | (func.trim(Tender.procuring_entity) == "")
        )
    ).all()
    return _issue("missing_buyers", "Tenders with no buyer / procuring entity", [r[0] for r in rows], total, "warning")


def _missing_published(db: Session, total: int) -> QualityIssue:
    rows = db.execute(select(Tender.reference_number).where(Tender.published_date.is_(None))).all()
    return _issue("missing_published_date", "Tenders with no publication date", [r[0] for r in rows], total, "info")


def _missing_value(db: Session, total: int) -> QualityIssue:
    rows = db.execute(select(Tender.reference_number).where(Tender.estimated_value.is_(None))).all()
    return _issue("missing_estimated_value", "Tenders with no estimated value", [r[0] for r in rows], total, "info")


def _missing_currency(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number).where((Tender.currency.is_(None)) | (func.trim(Tender.currency) == ""))
    ).all()
    return _issue("missing_currency", "Tenders with no currency", [r[0] for r in rows], total, "warning")


def _missing_suppliers(db: Session, total: int) -> QualityIssue:
    # Awards whose linked company is missing a name.
    rows = db.execute(
        select(Award.id)
        .join(Company, Award.company_id == Company.id)
        .where((Company.name.is_(None)) | (func.trim(Company.name) == ""))
    ).all()
    return _issue("missing_suppliers", "Awards with no supplier name", [str(r[0]) for r in rows], total, "warning")


# --------------------------------------------------------------------- duplicates


def _duplicate_tenders(db: Session) -> QualityIssue:
    rows = db.execute(
        select(
            Tender.procuring_entity,
            Tender.title,
            Tender.published_date,
            func.count(Tender.id),
        )
        .group_by(Tender.procuring_entity, Tender.title, Tender.published_date)
        .having(func.count(Tender.id) > 1)
    ).all()
    extra = sum(int(count) - 1 for *_, count in rows)
    examples = [f"{title} ({buyer}) x{count}" for buyer, title, _pub, count in rows[:_EXAMPLE_LIMIT]]
    total = int(db.scalar(select(func.count(Tender.id))) or 0)
    return QualityIssue(
        code="duplicate_tenders",
        label="Tenders sharing buyer + title + publication date",
        count=extra,
        total=total,
        ratio=_ratio(extra, total),
        severity="warning" if extra else "info",
        examples=examples,
    )


def _duplicate_companies(db: Session) -> QualityIssue:
    rows = db.execute(select(Company.id, Company.name)).all()
    groups: dict[str, set[str]] = defaultdict(set)
    for _company_id, name in rows:
        key = org_match_key(name)
        if key:
            groups[key].add(name)
    duplicate = {key: names for key, names in groups.items() if len(names) > 1}
    extra = sum(len(names) - 1 for names in duplicate.values())
    examples = [f"{key} <- {sorted(names)}" for key, names in list(duplicate.items())[:_EXAMPLE_LIMIT]]
    return QualityIssue(
        code="duplicate_companies",
        label="Companies that collapse to the same canonical name",
        count=extra,
        total=len(rows),
        ratio=_ratio(extra, len(rows)),
        severity="warning" if extra else "info",
        examples=examples,
    )


def _duplicate_buyers(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Tender.procuring_entity)
        .where(Tender.procuring_entity.is_not(None))
        .distinct()
    ).all()
    groups: dict[str, set[str]] = defaultdict(set)
    for (buyer,) in rows:
        key = org_match_key(buyer)
        if key:
            groups[key].add(buyer)
    duplicate = {key: names for key, names in groups.items() if len(names) > 1}
    extra = sum(len(names) - 1 for names in duplicate.values())
    examples = [f"{key} <- {sorted(names)}" for key, names in list(duplicate.items())[:_EXAMPLE_LIMIT]]
    return QualityIssue(
        code="duplicate_buyers",
        label="Buyer names that collapse to the same canonical name",
        count=extra,
        total=len(rows),
        ratio=_ratio(extra, len(rows)),
        severity="warning" if extra else "info",
        examples=examples,
    )


def _duplicate_awards(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Award.tender_id, Award.company_id, func.count(Award.id))
        .group_by(Award.tender_id, Award.company_id)
        .having(func.count(Award.id) > 1)
    ).all()
    extra = sum(int(count) - 1 for *_, count in rows)
    examples = [f"tender={tid} company={cid} x{count}" for tid, cid, count in rows[:_EXAMPLE_LIMIT]]
    total = int(db.scalar(select(func.count(Award.id))) or 0)
    return QualityIssue(
        code="duplicate_awards",
        label="Awards sharing the same tender + company",
        count=extra,
        total=total,
        ratio=_ratio(extra, total),
        severity="warning" if extra else "info",
        examples=examples,
    )


# --------------------------------------------------------------------- dates


def _broken_tender_dates(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number, Tender.published_date, Tender.closing_date).where(
            Tender.published_date.is_not(None),
            Tender.closing_date.is_not(None),
            Tender.closing_date < Tender.published_date,
        )
    ).all()
    examples = [f"{ref}: published {pub} > closing {close}" for ref, pub, close in rows[:_EXAMPLE_LIMIT]]
    total = int(db.scalar(select(func.count(Tender.id)).where(Tender.closing_date.is_not(None))) or 0)
    return QualityIssue(
        code="broken_tender_dates",
        label="Tenders closing before they were published",
        count=len(rows),
        total=total,
        ratio=_ratio(len(rows), total),
        severity="critical" if rows else "info",
        examples=examples,
    )


def _award_before_publication(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number, Tender.published_date, Award.award_date)
        .join(Tender, Award.tender_id == Tender.id)
        .where(
            Tender.published_date.is_not(None),
            Award.award_date.is_not(None),
            Award.award_date < Tender.published_date,
        )
    ).all()
    examples = [f"{ref}: published {pub} > awarded {award}" for ref, pub, award in rows[:_EXAMPLE_LIMIT]]
    total = int(db.scalar(select(func.count(Award.id)).where(Award.award_date.is_not(None))) or 0)
    return QualityIssue(
        code="award_before_publication",
        label="Awards dated before the tender was published",
        count=len(rows),
        total=total,
        ratio=_ratio(len(rows), total),
        severity="critical" if rows else "info",
        examples=examples,
    )


def _award_before_closing(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number, Tender.closing_date, Award.award_date)
        .join(Tender, Award.tender_id == Tender.id)
        .where(
            Tender.closing_date.is_not(None),
            Award.award_date.is_not(None),
            Award.award_date < Tender.closing_date,
        )
    ).all()
    examples = [f"{ref}: closing {close} > awarded {award}" for ref, close, award in rows[:_EXAMPLE_LIMIT]]
    total = int(db.scalar(select(func.count(Award.id)).where(Award.award_date.is_not(None))) or 0)
    return QualityIssue(
        code="award_before_closing",
        label="Awards dated before the tender closed for bids",
        count=len(rows),
        total=total,
        ratio=_ratio(len(rows), total),
        severity="warning" if rows else "info",
        examples=examples,
    )


# --------------------------------------------------------------------- values


def _invalid_tender_values(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number).where(Tender.estimated_value.is_not(None), Tender.estimated_value <= 0)
    ).all()
    return _issue("invalid_tender_values", "Tenders with a non-positive estimated value", [r[0] for r in rows], total, "warning")


def _invalid_award_values(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Award.id, Award.award_value).where((Award.award_value.is_(None)) | (Award.award_value <= 0))
    ).all()
    examples = [f"award {aid}: value={value}" for aid, value in rows[:_EXAMPLE_LIMIT]]
    return QualityIssue(
        code="invalid_award_values",
        label="Awards with null or non-positive value",
        count=len(rows),
        total=total,
        ratio=_ratio(len(rows), total),
        severity="warning" if rows else "info",
        examples=examples,
    )


def _award_exceeds_estimate(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number, Tender.estimated_value, Award.award_value)
        .join(Tender, Award.tender_id == Tender.id)
        .where(
            Tender.estimated_value.is_not(None),
            Tender.estimated_value > 0,
            Award.award_value.is_not(None),
            Award.award_value > Tender.estimated_value,
        )
    ).all()
    examples = [f"{ref}: awarded {award} > estimate {est}" for ref, est, award in rows[:_EXAMPLE_LIMIT]]
    total = int(
        db.scalar(
            select(func.count(Award.id))
            .select_from(Award)
            .join(Tender, Award.tender_id == Tender.id)
            .where(Tender.estimated_value.is_not(None), Award.award_value.is_not(None))
        )
        or 0
    )
    return QualityIssue(
        code="award_exceeds_estimate",
        label="Awards whose value exceeds the tender's estimated value",
        count=len(rows),
        total=total,
        ratio=_ratio(len(rows), total),
        severity="warning" if rows else "info",
        examples=examples,
    )


def _currency_inconsistencies(db: Session) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number, Tender.currency, Award.currency)
        .join(Tender, Award.tender_id == Tender.id)
        .where(
            Tender.currency.is_not(None),
            Award.currency.is_not(None),
            Award.currency != Tender.currency,
        )
    ).all()
    examples = [f"{ref}: tender {tc} vs award {ac}" for ref, tc, ac in rows[:_EXAMPLE_LIMIT]]
    total = int(db.scalar(select(func.count(Award.id))) or 0)
    return QualityIssue(
        code="currency_inconsistencies",
        label="Awards whose currency differs from the tender currency",
        count=len(rows),
        total=total,
        ratio=_ratio(len(rows), total),
        severity="warning" if rows else "info",
        examples=examples,
    )


# --------------------------------------------------------------------- entities


def _entity_inconsistencies(db: Session) -> QualityIssue:
    """Same registration number attached to materially different company names."""
    rows = db.execute(
        select(Company.registration_number, Company.name).where(Company.registration_number.is_not(None))
    ).all()
    groups: dict[str, set[str]] = defaultdict(set)
    for registration, name in rows:
        groups[registration].add(org_match_key(name) or (name or "").strip().casefold())
    inconsistent = {reg: keys for reg, keys in groups.items() if len(keys) > 1}
    examples = [f"{reg}: {sorted(keys)}" for reg, keys in list(inconsistent.items())[:_EXAMPLE_LIMIT]]
    return QualityIssue(
        code="entity_inconsistencies",
        label="Registration numbers mapped to conflicting company names",
        count=len(inconsistent),
        total=len(groups),
        ratio=_ratio(len(inconsistent), len(groups)),
        severity="critical" if inconsistent else "info",
        examples=examples,
    )


def _registration_conflicts(db: Session) -> QualityIssue:
    """One canonical company name mapped to multiple registration numbers."""
    rows = db.execute(
        select(Company.name, Company.registration_number).where(Company.registration_number.is_not(None))
    ).all()
    groups: dict[str, set[str]] = defaultdict(set)
    for name, registration in rows:
        key = org_match_key(name)
        if key:
            groups[key].add(registration)
    conflicts = {key: regs for key, regs in groups.items() if len(regs) > 1}
    examples = [f"{key}: {sorted(regs)}" for key, regs in list(conflicts.items())[:_EXAMPLE_LIMIT]]
    return QualityIssue(
        code="registration_conflicts",
        label="Company names mapped to conflicting registration numbers",
        count=len(conflicts),
        total=len(groups),
        ratio=_ratio(len(conflicts), len(groups)),
        severity="critical" if conflicts else "info",
        examples=examples,
    )


def _circular_references(db: Session) -> QualityIssue:
    """Tenders whose buyer is (canonically) also the awarded supplier."""
    rows = db.execute(
        select(Tender.reference_number, Tender.procuring_entity, Company.name)
        .select_from(Award)
        .join(Tender, Award.tender_id == Tender.id)
        .join(Company, Award.company_id == Company.id)
        .where(Tender.procuring_entity.is_not(None))
    ).all()
    offenders = [
        ref for ref, buyer, supplier in rows if org_match_key(buyer) and org_match_key(buyer) == org_match_key(supplier)
    ]
    return _issue("circular_references", "Tenders where the buyer is also the awarded supplier", offenders, len(rows), "critical")


def _impossible_timelines(db: Session) -> QualityIssue:
    """Future publication dates, or awards implausibly long after closing."""
    today = now_utc().date()
    rows = db.execute(
        select(Tender.reference_number, Tender.published_date, Tender.closing_date)
    ).all()
    offenders = []
    for ref, published, closing in rows:
        if published and published > today:
            offenders.append(f"{ref}: published in the future ({published})")
        elif published and closing and (closing - published).days > 3650:
            offenders.append(f"{ref}: closing >10y after publication")
    return _issue("impossible_timelines", "Tenders with impossible publication/closing timelines", offenders, len(rows), "warning")


def _unclassified_procurement_method(db: Session, total: int) -> QualityIssue:
    rows = db.execute(select(Tender.reference_number, Tender.title, Tender.description)).all()
    offenders = [
        ref for ref, title, description in rows
        if tax.procurement_method_of(title, description) == tax.UNSPECIFIED
    ]
    return _issue("invalid_procurement_method", "Tenders with an unclassifiable procurement method", offenders, total, "info")


def _location_mismatch(db: Session, total: int) -> QualityIssue:
    """Buyer text implies one state while the title implies a different state."""
    rows = db.execute(
        select(Tender.reference_number, Tender.procuring_entity, Tender.title)
    ).all()
    offenders = []
    for ref, buyer, title in rows:
        buyer_state = tax.state_of(buyer, None)
        title_state = tax.state_of(None, title)
        if buyer_state != tax.UNATTRIBUTED and title_state != tax.UNATTRIBUTED and buyer_state != title_state:
            offenders.append(f"{ref}: buyer={buyer_state} vs title={title_state}")
    return _issue("location_mismatch", "Tenders whose buyer and title imply different states", offenders, total, "info")


def _negative_values(db: Session) -> QualityIssue:
    tender_rows = db.execute(select(Tender.reference_number).where(Tender.estimated_value < 0)).all()
    award_rows = db.execute(select(Award.id).where(Award.award_value < 0)).all()
    offenders = [r[0] for r in tender_rows] + [str(r[0]) for r in award_rows]
    return _issue("negative_values", "Tenders/awards with negative monetary values", offenders, 0, "critical")


def _duplicate_documents(db: Session, total: int) -> QualityIssue:
    """Multiple document rows for the same tender sharing an identical URL."""
    rows = db.execute(
        select(Document.tender_id, Document.url, func.count(Document.id))
        .where(Document.url.is_not(None))
        .group_by(Document.tender_id, Document.url)
        .having(func.count(Document.id) > 1)
    ).all()
    extra = sum(int(count) - 1 for *_, count in rows)
    examples = [f"tender={tid} url={url} x{count}" for tid, url, count in rows[:_EXAMPLE_LIMIT]]
    return QualityIssue(
        code="duplicate_documents",
        label="Documents duplicated within a tender (same URL)",
        count=extra,
        total=total,
        ratio=_ratio(extra, total),
        severity="warning" if extra else "info",
        examples=examples,
    )


def _document_checksum_mismatch(db: Session, total: int) -> QualityIssue:
    """Documents whose stored content_hash does not match a recompute of the URL."""
    rows = db.execute(
        select(Document.id, Document.url, Document.content_hash).where(
            Document.url.is_not(None), Document.content_hash.is_not(None)
        )
    ).all()
    offenders = [str(did) for did, url, stored in rows if content_hash(url) != stored]
    return _issue("document_checksum_mismatch", "Documents whose content hash does not match their URL", offenders, total, "critical")


# --------------------------------------------------------------------- references / provenance


def _broken_references(db: Session, total: int) -> QualityIssue:
    rows = db.execute(select(Tender.id, Tender.reference_number)).all()
    broken = [
        str(ref) or str(tid)
        for tid, ref in rows
        if not ref or not normalize_reference(ref)
    ]
    return _issue("broken_references", "Tenders with empty or malformed reference numbers", broken, total, "critical")


def _missing_identifiers(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number).where(
            (Tender.source_record_id.is_(None)) | (Tender.source_name.is_(None))
        )
    ).all()
    return _issue("missing_identifiers", "Tenders missing a source record id or source name", [r[0] for r in rows], total, "warning")


def _missing_source_urls(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Tender.reference_number).where((Tender.source_url.is_(None)) | (func.trim(Tender.source_url) == ""))
    ).all()
    return _issue("missing_source_urls", "Tenders with no source provenance URL", [r[0] for r in rows], total, "warning")


def _missing_document_urls(db: Session, total: int) -> QualityIssue:
    rows = db.execute(
        select(Document.id).where((Document.url.is_(None)) | (func.trim(Document.url) == ""))
    ).all()
    return _issue("missing_document_urls", "Documents with no resolvable URL", [str(r[0]) for r in rows], total, "warning")


def _missing_evidence(db: Session, total: int) -> QualityIssue:
    with_docs = int(db.scalar(select(func.count(func.distinct(Document.tender_id)))) or 0)
    missing = max(total - with_docs, 0)
    examples = [
        ref
        for (ref,) in db.execute(
            select(Tender.reference_number)
            .outerjoin(Document, Document.tender_id == Tender.id)
            .where(Document.id.is_(None))
            .limit(_EXAMPLE_LIMIT)
        ).all()
    ]
    return QualityIssue(
        code="missing_evidence",
        label="Tenders with no preserved document evidence",
        count=missing,
        total=total,
        ratio=_ratio(missing, total),
        severity="warning" if missing else "info",
        examples=examples,
    )


def _corrupted_awards(db: Session, total: int) -> QualityIssue:
    """Awards whose tender or company foreign key does not resolve."""
    rows = db.execute(
        select(Award.id)
        .outerjoin(Tender, Award.tender_id == Tender.id)
        .outerjoin(Company, Award.company_id == Company.id)
        .where((Tender.id.is_(None)) | (Company.id.is_(None)))
    ).all()
    return _issue("corrupted_awards", "Awards with an unresolved tender/company link", [str(r[0]) for r in rows], total, "critical")


# --------------------------------------------------------------------- coverage


def _normalization_coverage(db: Session, total_companies: int) -> list[CoverageMetric]:
    company_names = [name for (name,) in db.execute(select(Company.name)).all()]
    normalized_companies = sum(1 for name in company_names if name and normalize_org_name(name) == name)

    buyers = [
        buyer
        for (buyer,) in db.execute(
            select(Tender.procuring_entity).where(Tender.procuring_entity.is_not(None)).distinct()
        ).all()
    ]
    normalized_buyers = sum(1 for buyer in buyers if normalize_org_name(buyer) == buyer)

    references = [ref for (ref,) in db.execute(select(Tender.reference_number)).all()]
    normalized_refs = sum(1 for ref in references if ref and normalize_reference(ref) == ref)

    return [
        CoverageMetric(
            code="company_names_normalized",
            label="Company names already in canonical form",
            covered=normalized_companies,
            total=len(company_names),
            ratio=_ratio(normalized_companies, len(company_names)),
        ),
        CoverageMetric(
            code="buyer_names_normalized",
            label="Distinct buyer names already in canonical form",
            covered=normalized_buyers,
            total=len(buyers),
            ratio=_ratio(normalized_buyers, len(buyers)),
        ),
        CoverageMetric(
            code="references_normalized",
            label="Reference numbers already in canonical form",
            covered=normalized_refs,
            total=len(references),
            ratio=_ratio(normalized_refs, len(references)),
        ),
    ]


def _evidence_completeness(db: Session, total_tenders: int, total_documents: int) -> list[CoverageMetric]:
    tenders_with_docs = int(db.scalar(select(func.count(func.distinct(Document.tender_id)))) or 0)
    docs_with_url = int(db.scalar(select(func.count(Document.id)).where(Document.url.is_not(None))) or 0)
    docs_with_hash = int(db.scalar(select(func.count(Document.id)).where(Document.content_hash.is_not(None))) or 0)
    tenders_with_source_url = int(
        db.scalar(select(func.count(Tender.id)).where(Tender.source_url.is_not(None))) or 0
    )
    return [
        CoverageMetric(
            code="tenders_with_documents",
            label="Tenders with at least one preserved document",
            covered=tenders_with_docs,
            total=total_tenders,
            ratio=_ratio(tenders_with_docs, total_tenders),
        ),
        CoverageMetric(
            code="documents_with_url",
            label="Documents with a resolvable URL",
            covered=docs_with_url,
            total=total_documents,
            ratio=_ratio(docs_with_url, total_documents),
        ),
        CoverageMetric(
            code="documents_with_hash",
            label="Documents with a content hash",
            covered=docs_with_hash,
            total=total_documents,
            ratio=_ratio(docs_with_hash, total_documents),
        ),
        CoverageMetric(
            code="tenders_with_source_url",
            label="Tenders with a source provenance URL",
            covered=tenders_with_source_url,
            total=total_tenders,
            ratio=_ratio(tenders_with_source_url, total_tenders),
        ),
    ]


# --------------------------------------------------------------------- helpers


def _issue(code: str, label: str, offenders: list, total: int, severity: str) -> QualityIssue:
    offenders = [str(o) for o in offenders if o is not None]
    count = len(offenders)
    return QualityIssue(
        code=code,
        label=label,
        count=count,
        total=total,
        ratio=_ratio(count, total),
        severity=severity if count else "info",
        examples=offenders[:_EXAMPLE_LIMIT],
    )


def _quality_score(issues: list[QualityIssue]) -> float:
    """A single 0-1 health score: weighted, deterministic penalty from ratios.

    critical issues weigh 3x, warnings 1x. Score = 1 - clamp(sum(weighted ratios)).
    """
    weight = {"critical": 3.0, "warning": 1.0, "info": 0.0}
    penalty = sum(weight.get(issue.severity, 0.0) * issue.ratio for issue in issues)
    normaliser = sum(weight.get(issue.severity, 0.0) for issue in issues if issue.count) or 1.0
    return round(max(0.0, 1.0 - penalty / normaliser), 4)


def _ratio(part: int | Decimal, whole: int | Decimal) -> float:
    whole = int(whole)
    return round(int(part) / whole, 4) if whole else 0.0
