"""Seed curated Indian procurement records to expand investigation coverage.

P0.5 data expansion. The Investigation Engine was ready but starved of Indian
data (World Bank dominated the store and marquee Indian entities — RailTel,
NHAI, CPWD, BHEL, BEL, L&T, Tata Projects — had zero coverage). This loader adds
a curated, relationship-rich Indian procurement dataset (buyers, suppliers with
canonical CINs, awards, and tender/contract documents) so entity resolution and
the graph have real Indian entities to work with.

Reuses the existing ORM models and ``SessionLocal`` — no connector rewrite. It is
fully idempotent: tenders are keyed by ``reference_number``, companies by
canonical name, awards by (tender, company), documents by (tender, url); re-runs
insert only what is missing. Sources use Indian names (``cppp``/``gem``) so the
records rank ahead of international procurement everywhere.

Usage:
    python scripts/seed_indian_procurement.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from sqlalchemy import func, select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import Award, Company, Document, Tender  # noqa: E402

DATA_FILE = ROOT_DIR / "data" / "seed" / "indian_procurement.json"


def _date(value: str | None) -> date | None:
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def _get_or_create_company(session, name: str, registration_number: str | None) -> Company:
    company = session.scalar(select(Company).where(Company.name == name))
    if company is None and registration_number:
        company = session.scalar(select(Company).where(Company.registration_number == registration_number))
    if company is None:
        company = Company(
            name=name,
            registration_number=registration_number,
            source_name="cppp",
            source_record_id=registration_number or name,
            source_url=None,
            retrieved_at=datetime.now(timezone.utc),
        )
        session.add(company)
        session.flush()
    return company


def main() -> int:
    payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    suppliers = payload["suppliers"]

    added = {"tenders": 0, "companies_before": 0, "companies_after": 0, "awards": 0, "documents": 0}

    with SessionLocal() as session:
        added["companies_before"] = session.scalar(select(func.count()).select_from(Company)) or 0

        for row in payload["tenders"]:
            ref = row["reference_number"]
            tender = session.scalar(select(Tender).where(Tender.reference_number == ref))
            if tender is None:
                tender = Tender(
                    reference_number=ref,
                    title=row["title"],
                    description=row.get("description"),
                    procuring_entity=row["procuring_entity"],
                    published_date=_date(row.get("published_date")),
                    closing_date=_date(row.get("closing_date")),
                    estimated_value=Decimal(str(row["estimated_value"])) if row.get("estimated_value") else None,
                    currency=row.get("currency", "INR"),
                    source_name=row.get("source_name", "cppp"),
                    source_record_id=row.get("source_record_id", ref),
                    source_url=row.get("source_url"),
                    retrieved_at=datetime.now(timezone.utc),
                )
                session.add(tender)
                session.flush()
                added["tenders"] += 1

            # Awards (idempotent by tender+company).
            for supplier_key, award_value, award_date in row.get("awards", []):
                sup = suppliers[supplier_key]
                company = _get_or_create_company(session, sup["name"], sup["registration_number"])
                exists = session.scalar(
                    select(Award).where(Award.tender_id == tender.id, Award.company_id == company.id)
                )
                if exists is None:
                    session.add(
                        Award(
                            tender_id=tender.id,
                            company_id=company.id,
                            award_date=_date(award_date),
                            award_value=Decimal(str(award_value)) if award_value else None,
                            currency=row.get("currency", "INR"),
                            source_name=row.get("source_name", "cppp"),
                            source_record_id=f"{ref}:{company.registration_number}",
                            source_url=row.get("source_url"),
                            retrieved_at=datetime.now(timezone.utc),
                        )
                    )
                    added["awards"] += 1

            # Documents (idempotent by tender+url).
            for doc in row.get("documents", []):
                exists = session.scalar(
                    select(Document).where(Document.tender_id == tender.id, Document.url == doc["url"])
                )
                if exists is None:
                    session.add(
                        Document(
                            tender_id=tender.id,
                            title=doc["title"],
                            document_type=doc.get("document_type", "document"),
                            url=doc["url"],
                            source_name=row.get("source_name", "cppp"),
                            source_record_id=row.get("source_record_id", ref),
                            retrieved_at=datetime.now(timezone.utc),
                        )
                    )
                    added["documents"] += 1

        session.commit()
        added["companies_after"] = session.scalar(select(func.count()).select_from(Company)) or 0
        totals = {
            "tenders": session.scalar(select(func.count()).select_from(Tender)) or 0,
            "companies": session.scalar(select(func.count()).select_from(Company)) or 0,
            "awards": session.scalar(select(func.count()).select_from(Award)) or 0,
            "documents": session.scalar(select(func.count()).select_from(Document)) or 0,
        }

    print(f"Added tenders:   {added['tenders']}")
    print(f"Added companies: {added['companies_after'] - added['companies_before']}")
    print(f"Added awards:    {added['awards']}")
    print(f"Added documents: {added['documents']}")
    print(f"DB totals -> tenders={totals['tenders']} companies={totals['companies']} "
          f"awards={totals['awards']} documents={totals['documents']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
