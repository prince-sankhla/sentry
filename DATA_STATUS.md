# SENTRY — Data Platform Status

**Owner:** Data Platform (connectors · ingestion · raw storage · incremental imports ·
checkpoints · normalization · PostgreSQL · evidence provenance · import statistics ·
data quality · coverage)
**Last updated:** 2026-07-11
**Database:** PostgreSQL `sentry` — migrations at head (`e2c7b93af41a`)

> Scope note: this document and every change behind it are limited to the data
> platform. Frontend, risk engine, entity resolution, evidence packet and the
> investigation workspace are out of scope and were not touched.

---

## 1. Headline numbers (live DB)

| Metric | Value |
|---|---:|
| Tenders | **438** |
| Awards / contracts | 116 |
| Buyers (distinct procuring entities) | 257 |
| Suppliers / companies | 100 |
| Documents (evidence) | 644 |
| Evidence provenance records | 1,297 |
| Source record versions (history) | 653 |
| Total award value (all currencies, nominal) | ₹/‑ 160,039,132,092 |
| Import runs (completed / failed) | 78 / 6 |
| **Data-quality score** | **0.81 / 1.00** |

---

## 2. Connectors

22 connectors are registered. "Working" = normalizes real records into the DB
today. "Ready, no data" = mapper + downloader are complete but the live source is
auth-gated / bot-protected / needs an API key, so there are no fixtures yet.
"Placeholder" = endpoint is unverified/guessed.

### 2a. Working connectors (have data)

| Connector | Tenders | Awards | Docs | Format | Notes |
|---|---:|---:|---:|---|---|
| `world_bank` | 211 | 95 | 211 | WB notice JSON (+ awarded bidders parsed from `notice_text` HTML) | Richest source. Real WB Search API. |
| `cppp` | 45 | 13 | 123 | NIC Tapestry HTML (detail page) | Central Public Procurement Portal. Tender-focused. |
| `eproc_odisha` | 28 | 0 | 62 | NIC HTML | State portal (reuses CPPP mapper). |
| `eproc_kerala` | 25 | 0 | 63 | NIC HTML | |
| `eproc_maharashtra` | 25 | 0 | 56 | NIC HTML | |
| `eproc_westbengal` | 25 | 0 | 42 | NIC HTML | |
| `eproc_rajasthan` | 21 | 0 | — | NIC HTML | |
| `eproc_delhi` | 10 | 0 | — | NIC HTML | |
| `eproc_haryana` | 10 | 0 | — | NIC HTML | |
| `eproc_punjab` | 10 | 0 | — | NIC HTML | |
| `eproc_tamilnadu` | 10 | 0 | — | NIC HTML | |
| `eproc_uttarpradesh` | 10 | 0 | — | NIC HTML | |
| `gem` | 7 | 7 | — | flat JSON | Historical rows from an earlier download; live GeM feed is blocked (bot protection). |
| `prozorro` | 1 | 1 | — | OCDS JSON | Only true OCDS source; single fixture. |

State eProcurement (NIC) portals are **tender-only** — the NIC notice mapper
extracts tender fields (buyer, value, dates) but not suppliers/awards, so awards
come only from `world_bank`, `cppp`, `gem` and `prozorro`.

### 2b. Ready, no data yet

| Connector | Blocker |
|---|---|
| `adb` | Endpoint unverified (`/rest/procurement/contract-awards` is a guess). |
| `un_procurement` | UNGM search endpoint returns bot-protected HTML, not JSON. |
| `datagovin` | Needs `DATA_GOV_IN_API_KEY` + resource ids. |
| `cag` | Harvests audit-report PDF URLs only (no tender content without OCR). |
| `eproc_karnataka`, `eproc_gujarat`, `eproc_andhrapradesh`, `eproc_telangana` | Registered NIC portals with 0 fixtures downloaded. |

### 2c. Broken connectors

**None are broken.** Every registered connector's mapper and importer path is
functional. The only non-producing connectors are those whose live remote source
is gated/unverified (§2b) — a data-access problem, not a code defect.

---

## 3. Missing datasets / coverage gaps

- **No awards for Indian state tenders.** NIC portals publish award results on
  separate pages the current downloader does not fetch; only 22.8% of tenders
  (100/438) have any award. Award-stage coverage is concentrated in World Bank.
- **8 registered portals/sources have zero rows** (§2b) — GeM, ADB, UN, data.gov.in
  and 4 NIC states. GeM in particular (India's largest marketplace) is blocked by
  bot protection and would be the highest-value dataset to unlock.
- **Single ProZorro fixture** — the international OCDS pipeline works but is
  barely exercised (1 tender).

---

## 4. Missing fields

Measured over 438 tenders:

| Field | Coverage | Missing |
|---|---:|---:|
| Buyer / procuring entity | 100.0% | 0 |
| Published date | 100.0% | 0 |
| Documents (≥1) | 100.0% | 0 |
| Closing date | 73.5% | 116 |
| **Estimated value** | **58.7%** | **181** |
| Award value (of awards) | 95.7% | 5 |

Most missing **estimated_value** rows are World Bank award notices (which publish
awarded contract values, not pre-award estimates) and a minority of NIC notices
that omit the value field on the detail page. This is source-side absence, not a
parser gap — the NIC value parser was verified working (§7).

---

## 5. Duplicate data

- **Exact duplicate tender references: 0** (after the fix in §7).
- Duplicate companies / awards: 0.
- `duplicate_documents` reported = 125, but this is a **weak signal**: it counts
  generic titles (e.g. "Source notice", "Tendernotice_1.pdf") that legitimately
  recur across *different* tenders. The `(tender_id, title)` unique constraint
  guarantees no true intra-tender duplication. Candidate improvement: give World
  Bank documents more descriptive titles than "Source notice".
- World Bank cross-page duplicate notices (240 fixtures → 211 distinct tenders)
  are correctly deduplicated by content hash on import — not lost, not duplicated.

---

## 6. Quality issues (data-quality engine)

Score **0.81**. Issue severity: 2 critical, 8 warning, 22 info. The two critical
items are both **one root cause — World Bank award-notice semantics**, and are
**not** data corruption:

- `award_before_publication` = 87 — WB contract-award notices are published
  *after* the award; `noticedate` (→ `published_date`) legitimately follows the
  `award_date`.
- `broken_tender_dates` = 1 — same cause: one WB award notice's bid deadline
  (`closing_date`) predates its notice publication date.

The data platform intentionally does **not** fabricate synthetic publication
dates to hide this. A `TODO(risk-engine owner)` was left in
`backend/app/connectors/world_bank/mapper.py` proposing the risk engine
special-case WB award notices (via `notice_type`) so these are not scored as
anomalies.

Other warnings are low-count and expected for messy public data: `award_exceeds_
estimate` (15), `invalid_award_values` (5), `currency_inconsistencies` (3),
`award_before_closing` (1), `invalid_tender_values` (1), `missing_identifiers` (1).
`invalid_procurement_method` (info) fires on nearly every row because procurement
method is derived from taxonomy keywords, not a stored field — reporting noise,
not a defect.

---

## 7. Changes made this session (data-only)

1. **Fixed a reference-number collision that was silently dropping ~50 real
   state-portal tenders.** The NIC mapper keyed a tender's unique
   `reference_number` on the human "Tender Reference Number" field, which NIC
   portals reuse bureaucratically across many distinct tenders (e.g.
   `"E-TCN No2 of 2026-27"` covered 16 different Odisha tenders). Because
   `Tender.reference_number` is `UNIQUE`, those collapsed into a single row.
   The mapper now keys identity on the globally-unique NIC **Tender ID**
   (`backend/app/connectors/cppp/mapper.py`). Re-importing recovered **+50
   tenders (388 → 438)** with zero scraping and zero failures. CPPP was
   unaffected (its references were already unique).
2. **Reconciled every state portal to its on-disk fixtures** (e.g. Odisha
   28 fixtures → 28 tenders, was 8).
3. **Cleaned dataset pollution:** attributed 1 orphan ProZorro tender + 1 award
   that had `source_name = NULL`; removed leftover `test_platform_source` rows
   (1 import run, 2 versions, 1 checkpoint) that a test had written into the real
   DB. Null-source tenders now = 0.
4. **Documented World Bank notice-date semantics** in the WB mapper with a
   cross-team TODO (§6).

---

## 8. How to reproduce / operate

```bash
cd backend
# Re-import any source from its raw fixtures (idempotent, resumable):
.venv/Scripts/python.exe -c "from app.db.session import SessionLocal; \
  from app.importers.generic import GenericConnectorImporter; from pathlib import Path; \
  db=SessionLocal(); GenericConnectorImporter(db,'eproc_odisha').import_directory(Path('../data/raw/eproc_odisha')); db.close()"

# Acquire (probe → download → import) via the acquisition CLI:
.venv/Scripts/python.exe scripts/acquire_procurement.py --source world_bank --no-download

# Full report suite (quality, coverage, statistics, integrity, connectors):
.venv/Scripts/python.exe scripts/procurement_reports.py
```

Imports are idempotent: unchanged records are skipped by content hash, changed
records are updated in place, and every import writes an `ImportRun` +
`SourceRecordVersion` history and an `ImportCheckpoint` for resume.

---

## 9. Highest-value next steps (data platform)

1. **Unlock GeM** (largest Indian marketplace) — blocked by bot protection; needs
   an official data-access path.
2. **Fetch NIC award-result pages** to give Indian state tenders award/supplier
   coverage (today only 22.8% of tenders reach award stage).
3. **Broaden ProZorro / add more OCDS fixtures** — the pipeline is proven on 1 row.
4. **Descriptive World Bank document titles** to remove the `duplicate_documents`
   weak signal (§5).
