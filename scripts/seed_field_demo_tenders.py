"""Idempotently seed field-demo tender profiles into the core SENTRY tenders table.

The field-specific requirement/capability mapping stays in
`sentry_field/data/demo_tenders.json`; this script makes the tender records
available in the existing procurement database as well.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.tender import Tender

DATA = ROOT / "sentry_field" / "data" / "demo_tenders.json"


def main() -> None:
    rows = json.loads(DATA.read_text(encoding="utf-8"))
    created = updated = 0
    with SessionLocal() as db:
        for row in rows:
            reference = row["reference_number"]
            tender = db.scalar(select(Tender).where(Tender.reference_number == reference))
            description = (
                f"SENTRY FIELD demo profile. Official source: {row['source_name']}. "
                f"Contract location: {row['contract_location']}. "
                f"Field demo site: {row['demo_site']}. "
                f"Verification policy: {row['verification_notes']}"
            )
            if tender is None:
                tender = Tender(reference_number=reference)
                db.add(tender)
                created += 1
            else:
                updated += 1
            tender.title = row["title"][:500]
            tender.description = description
            tender.procuring_entity = row["source_name"]
            tender.category = row["category"]
            tender.geography = row["contract_location"][:100]
            tender.source_name = row["source_name"]
            tender.source_record_id = row["tender_id"]
            tender.source_url = row["source_url"]
            tender.currency = "INR"
        db.commit()
    print(f"Seeded SENTRY FIELD demo tenders: created={created}, updated={updated}")


if __name__ == "__main__":
    main()
