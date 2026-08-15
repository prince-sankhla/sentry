# SENTRY — India Data Audit (Sprint 1, Task 1.1)

**Author:** Data Platform (Principal)
**Date:** 2026-07-11
**Scope:** audit only. No code was modified. Architecture is locked.
**Method:** live registry (`discover_connectors`) + live PostgreSQL counts + raw-fixture
inspection + evidence-provenance spot checks.

---

## 0. Summary

- **22 connectors registered** (7 named sources + 14 NIC state-portal connectors + 1 international bank feed already counted).
- **467 tenders / 142 awards / 673 documents** in the DB across 14 sources with data.
- **Only ONE connector produces reproducible, provenance-clean award+supplier data at depth: `world_bank`.**
- **Two connectors carry seeded / non-reproducible award rows** (`cppp`, `gem`) — their awards are **not** in raw storage and their `source_url`s are synthetic. **Do not demo these awards.**
- **Four connectors are pure scaffolding** (no raw dir, zero records ever): `adb`, `cag`, `datagovin`, `un_procurement`.
- **Missing category:** no **Indian Corporate** connector exists (MCA/CIN registry) — the biggest capability gap for entity-level investigation.

---

## 1. Classification (six buckets)

| Bucket | Connectors |
|---|---|
| **Indian Procurement** | `cppp`, `gem`, + 14 `eproc_*` state portals |
| **Indian Oversight** | `cag` |
| **Indian Corporate** | *(none — capability gap)* |
| **International** | `world_bank`, `prozorro` |
| **Experimental** | `adb`, `un_procurement`, `datagovin` |
| **Deprecated** | *(none)* |

> Note on placement: `datagovin` is an Indian-government source by origin but is
> classified **Experimental** by maturity — it has never imported a record (needs an
> API key + resource ids). `adb`/`un_procurement` are international by origin but are
> non-functional scaffolding, so their dominant characteristic is Experimental.

---

## 2. Connector-by-connector audit

### 2.1 Indian Procurement

#### `cppp` — Central Public Procurement Portal
- **Status:** Active scraper (NIC Tapestry HTML). 32 raw fixtures; 10 historical import runs (a legacy batch of 10 failures, since superseded).
- **Records:** 45 tenders · **13 awards** · 123 documents.
- **Data quality:** Good tender-level parsing (buyer, value, dates). Reference identity fixed to the unique NIC Tender ID.
- **Evidence quality:** Tender documents are real. ⚠️ **Award rows are NOT reproducible** — the winners (L&T, Afcons, BEL, NBCC…) appear in **zero** raw fixtures, and their `source_url`s are constructed query strings (`eprocure.gov.in/…?tender=NHAI/2026/…`). These awards were **seeded**, not scraped.
- **Procurement usefulness:** High for Indian *tender-stage* data; **award layer untrusted**.
- **Recommendation:** **KEEP** the connector. **FREEZE/QUARANTINE the seeded award rows** until re-derived from a real award page.

#### `gem` — Government e-Marketplace
- **Status:** **Blocked at source** (bot protection). Placeholder endpoint. **No raw dir** on disk.
- **Records:** 7 tenders · 7 awards · 14 documents (all legacy/seeded).
- **Data quality:** Mapper is complete; no live data.
- **Evidence quality:** ⚠️ Same problem as CPPP — award `source_url`s are synthetic `eprocure.gov.in?tender=RAILTEL/2026/…`; winners not in any raw fixture. **Seeded.**
- **Procurement usefulness:** Potentially the **highest** in India (largest marketplace) — but currently inaccessible and untrusted.
- **Recommendation:** **FREEZE.** Keep the connector for the day official access is granted; do not demo current rows.

#### `eproc_*` — 14 NIC State eProcurement portals
- **Status:** Active NIC scraper (reuses the CPPP mapper). 10 portals have data; 4 are dormant (registered, ready, no fixtures yet).
- **Records (tenders):**

  | Portal | Tenders | Docs | Portal | Tenders | Docs |
  |---|---:|---:|---|---:|---:|
  | eproc_odisha | 28 | 62 | eproc_delhi | 10 | 10 |
  | eproc_kerala | 25 | 63 | eproc_haryana | 10 | 10 |
  | eproc_maharashtra | 25 | 56 | eproc_punjab | 10 | 10 |
  | eproc_westbengal | 25 | 42 | eproc_tamilnadu | 10 | 10 |
  | eproc_rajasthan | 21 | 21 | eproc_uttarpradesh | 10 | 10 |
  | **Dormant (0 records):** eproc_andhrapradesh, eproc_gujarat, eproc_karnataka, eproc_telangana | | | | | |

- **Awards:** **0** across all portals — NIC notice pages carry no award/supplier data.
- **Data quality:** Good (buyer 100%, value/closing well-populated). Reference-collision bug fixed — every fixture now yields a distinct tender.
- **Evidence quality:** Real, reproducible documents; genuine portal `source_url`s.
- **Procurement usefulness:** Strong Indian **tender-stage** corpus; **cannot support "who won"** typologies without an award layer.
- **Recommendation:** **KEEP** the 10 with data (core India corpus). **KEEP (dormant)** the 4 empty portals — one download from working, same proven parser.

#### `datagovin` — data.gov.in Procurement Datasets *(classified Experimental, see §2.3)*

### 2.2 Indian Oversight

#### `cag` — Comptroller and Auditor General
- **Status:** Scaffolding. **No raw dir**, 0 records. Harvester captures audit-report **PDF URLs** only.
- **Records:** 0.
- **Data quality / Evidence quality:** N/A (no tender content without OCR).
- **Procurement usefulness:** Strategic (audit findings corroborate procurement leads) but not usable as structured data yet.
- **Recommendation:** **FREEZE.** High future value; needs a PDF/OCR layer.

### 2.3 Experimental

#### `datagovin` — data.gov.in
- **Status:** Non-operational — needs `DATA_GOV_IN_API_KEY` + configured resource ids. **No raw dir**, 0 records.
- **Records:** 0. **Evidence/quality:** N/A.
- **Procurement usefulness:** Medium-high if wired (official Indian open data), but unproven.
- **Recommendation:** **FREEZE** (Indian source; revisit when credentials/resources are provisioned).

#### `adb` — Asian Development Bank
- **Status:** Scaffolding. Endpoint is a **guess** (docstring admits it). **No raw dir**, 0 records.
- **Records:** 0. **Evidence/quality:** N/A.
- **Procurement usefulness:** Low for India-first; international.
- **Recommendation:** **FREEZE** (remove-candidate; retained per no-delete policy).

#### `un_procurement` — UNGM
- **Status:** Scaffolding. Endpoint returns **bot-protected HTML**, not JSON. **No raw dir**, 0 records.
- **Records:** 0. **Evidence/quality:** N/A.
- **Procurement usefulness:** Low for India-first; international.
- **Recommendation:** **FREEZE** (remove-candidate; retained per no-delete policy).

### 2.4 International

#### `world_bank` — World Bank Procurement Notices ✅
- **Status:** **Fully operational.** Real Search API (410,998 notices available). 240 fixtures, 11 import runs, 0 failures.
- **Records:** **240 tenders · 121 awards · 240 documents · 90 distinct suppliers.**
- **Data quality:** Highest in the repo. 116/121 awards valued; 100% source-URL coverage; identity keyed on the unique notice id (reference-collision bug fixed → recovered 29 notices).
- **Evidence quality:** **Best in class.** Every award parsed deterministically from `notice_text`; every record carries a real `projects.worldbank.org/.../procurement-detail/{id}` URL and regenerates from raw storage.
- **Procurement usefulness:** The **only** source that supports award-stage typologies (supplier concentration, lot-splitting, single-bidder) with reproducible evidence. Basis of the verified Case #001 (LUXMI, 9 awards / $5.19M).
- **Recommendation:** **KEEP** — verified flagship dataset. (International by origin; disabled from *default live enumeration* under India-first scope, but reachable by name and already imported to the DB — see `INDIA_SCOPE_PLAN.md`.)

#### `prozorro` — ProZorro (Ukraine)
- **Status:** Operational OCDS connector (open API). 1 fixture.
- **Records:** 1 tender · 1 award · 2 documents.
- **Data quality / Evidence quality:** Excellent schema (true OCDS: bids, disqualifications, supplier codes), fully reproducible — but depth = 1.
- **Procurement usefulness:** Best *future* schema for integrity analytics; useless at current depth.
- **Recommendation:** **FREEZE** for the hackathon (disable by default); revisit as the strategic OCDS bet.

---

## 3. Final table

| Connector | Class | Status | Tenders | Awards | Docs | Data quality | Evidence quality | Procurement usefulness | Recommendation |
|---|---|---|---:|---:|---:|---|---|---|---|
| `world_bank` | International | ✅ Operational | 240 | 121 | 240 | High | **Reproducible / real URLs** | **High (award-stage)** | **KEEP (flagship)** |
| `cppp` | India Procurement | Active scraper | 45 | 13 | 123 | Good (tenders) | Tenders real; **awards seeded** | High (tenders) | KEEP; **freeze seeded awards** |
| `eproc_odisha` | India Procurement | Active | 28 | 0 | 62 | Good | Real | Tender-stage only | KEEP |
| `eproc_kerala` | India Procurement | Active | 25 | 0 | 63 | Good | Real | Tender-stage only | KEEP |
| `eproc_maharashtra` | India Procurement | Active | 25 | 0 | 56 | Good | Real | Tender-stage only | KEEP |
| `eproc_westbengal` | India Procurement | Active | 25 | 0 | 42 | Good | Real | Tender-stage only | KEEP |
| `eproc_rajasthan` | India Procurement | Active | 21 | 0 | 21 | Good | Real | Tender-stage only | KEEP |
| `eproc_delhi` | India Procurement | Active | 10 | 0 | 10 | Good | Real | Tender-stage only | KEEP |
| `eproc_haryana` | India Procurement | Active | 10 | 0 | 10 | Good | Real | Tender-stage only | KEEP |
| `eproc_punjab` | India Procurement | Active | 10 | 0 | 10 | Good | Real | Tender-stage only | KEEP |
| `eproc_tamilnadu` | India Procurement | Active | 10 | 0 | 10 | Good | Real | Tender-stage only | KEEP |
| `eproc_uttarpradesh` | India Procurement | Active | 10 | 0 | 10 | Good | Real | Tender-stage only | KEEP |
| `eproc_andhrapradesh` | India Procurement | Dormant | 0 | 0 | 0 | — | — | Ready, no data | KEEP (dormant) |
| `eproc_gujarat` | India Procurement | Dormant | 0 | 0 | 0 | — | — | Ready, no data | KEEP (dormant) |
| `eproc_karnataka` | India Procurement | Dormant | 0 | 0 | 0 | — | — | Ready, no data | KEEP (dormant) |
| `eproc_telangana` | India Procurement | Dormant | 0 | 0 | 0 | — | — | Ready, no data | KEEP (dormant) |
| `gem` | India Procurement | ⚠️ Blocked | 7 | 7 | 14 | No live data | **Seeded / synthetic URLs** | High (if unblocked) | **FREEZE** |
| `cag` | India Oversight | Scaffolding | 0 | 0 | 0 | N/A | PDF URLs only | Strategic (future) | FREEZE |
| `datagovin` | Experimental | Scaffolding | 0 | 0 | 0 | N/A | N/A | Medium (if wired) | FREEZE |
| `prozorro` | International | Operational | 1 | 1 | 2 | Excellent schema | Reproducible | Best future schema | FREEZE |
| `adb` | Experimental | Scaffolding | 0 | 0 | 0 | N/A | N/A | Low (int'l) | FREEZE (remove-candidate) |
| `un_procurement` | Experimental | Scaffolding | 0 | 0 | 0 | N/A | N/A | Low (int'l) | FREEZE (remove-candidate) |

**Totals (with data):** 467 tenders · 142 awards · 673 documents.

---

## 4. Audit conclusions (brutally honest)

1. **World Bank is the only demo-safe award dataset.** Everything else either has no awards (state portals) or seeded awards (cppp, gem).
2. **Purge the seeded-award liability before any demo.** CPPP/GeM award rows with synthetic `eprocure.gov.in?tender=…` URLs will not survive a judge clicking through. (Data-hygiene task, tracked in `DATASET_SELECTION.md`.)
3. **India's structural gap is the award/supplier layer + a corporate registry.** State portals give rich tenders but no winners; there is no Indian Corporate (MCA/CIN) connector to resolve entities. These are the highest-value future builds — not more portals.
4. **Four experimental connectors add registry noise, not data.** Freeze and disable by default (Task 1.2).
