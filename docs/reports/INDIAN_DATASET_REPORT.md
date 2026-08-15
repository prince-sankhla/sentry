# SENTRY — Indian Dataset Audit Report (Sprint 1, Task 1.3)

**Author:** Data Platform (Principal)
**Date:** 2026-07-11
**Source:** live PostgreSQL `sentry` database.
**Scope:** **Indian connectors only** — `cppp`, `gem`, and the 14 `eproc_*` NIC state
portals (per the classification in `INDIA_SCOPE_PLAN.md`). International sources
(`world_bank`, `prozorro`) are excluded by design.
**Method:** direct SQL + the existing deterministic taxonomy classifiers
(`app/services/procurement_taxonomy.py`) run read-only. **No code was changed.**

---

## 1. Totals (Indian corpus)

| Metric | Count |
|---|---:|
| **Indian tenders** | **226** |
| Total awards | 20 ⚠️ *(all seeded — see §7)* |
| Total buyers (distinct procuring entities) | 121 |
| Total suppliers (distinct, in awards) | 9 ⚠️ *(all seeded)* |
| Total companies (Indian-source rows) | 9 ⚠️ *(all seeded)* |
| Total documents (evidence) | 431 |

> Only 12 of the 14 Indian portals hold data; `eproc_andhrapradesh`, `eproc_gujarat`,
> `eproc_karnataka`, `eproc_telangana`, plus `cag`/`datagovin`, are registered but
> empty and therefore contribute 0 to every figure.

---

## 2. Coverage by source

| Source | Tenders | With value | With closing date |
|---|---:|---:|---:|
| cppp (national) | 45 | 35 | 45 |
| eproc_odisha | 28 | 27 | 28 |
| eproc_westbengal | 25 | 21 | 25 |
| eproc_maharashtra | 25 | 15 | 25 |
| eproc_kerala | 25 | 21 | 25 |
| eproc_rajasthan | 21 | 20 | 21 |
| eproc_haryana | 10 | 10 | 10 |
| eproc_delhi | 10 | 5 | 10 |
| eproc_punjab | 10 | 5 | 10 |
| eproc_uttarpradesh | 10 | 10 | 10 |
| eproc_tamilnadu | 10 | 1 | 10 |
| gem (national) | 7 | 7 | 7 |
| **Total** | **226** | **177** | **226** |

---

## 3. Coverage by state

Two views are given because the deterministic classifier and the source portal
disagree, and the disagreement is itself a finding.

**3a. By source portal (authoritative — a state portal *is* its state):**

| State / scope | Tenders |
|---|---:|
| National (CPPP) | 45 |
| Odisha | 28 |
| Kerala | 25 |
| Maharashtra | 25 |
| West Bengal | 25 |
| Rajasthan | 21 |
| Delhi | 10 |
| Haryana | 10 |
| Punjab | 10 |
| Tamil Nadu | 10 |
| Uttar Pradesh | 10 |
| National (GeM) | 7 |

**3b. By taxonomy classifier (`state_of(buyer, title)`):**

| State | Tenders | | State | Tenders |
|---|---:|---|---|---:|
| **Unattributed** | **159** | | West Bengal | 3 |
| Delhi | 23 | | Tamil Nadu / Rajasthan | 2 each |
| Uttar Pradesh | 14 | | Uttarakhand / Odisha / Telangana | 1 each |
| Kerala / Haryana | 10 each | | | |

> **Finding:** the text classifier leaves **70% (159/226) unattributed** because NIC
> buyer/title strings rarely name the state, and it does not consult the source
> portal. State coverage is effectively **100%** when derived from the portal (3a).
> *Improvement (not applied — audit only): fold the connector's portal into
> `state_of` so state-portal tenders attribute deterministically.*

---

## 4. Coverage by ministry

| Ministry | Tenders |
|---|---:|
| **Unattributed** | **226 (100%)** |

> **Finding:** `ministry_of` attributes **nothing**. State procurement is executed by
> state departments/PSUs, not Union ministries, so the Union-ministry classifier is a
> structural mismatch for this corpus. Ministry coverage is genuinely ~0 for Indian
> state data; a *department/authority* dimension would be the meaningful cut.

---

## 5. Coverage by procurement method

| Method | Tenders |
|---|---:|
| **Unspecified** | **226 (100%)** |

> **Finding:** `procurement_method_of` classifies nothing from Indian titles/descriptions.
> NIC notice pages do carry a method field (open/limited/EOI/GeM-bid) that the current
> mapper does not extract into a structured column, so method is 0% covered. This is the
> single largest *structured-field* gap for Indian data.

---

## 6. Coverage by year

| Year | Tenders |
|---|---:|
| 2026 | 226 (100%) |

> The Indian corpus is a single-year snapshot (2026). **No historical depth** — every
> Indian tender was published in 2026, so time-series / trend typologies are not yet
> possible on Indian data.

---

## 7. Missing fields

Of 226 Indian tenders:

| Field | Missing | % |
|---|---:|---:|
| estimated_value | 49 | 22% |
| closing_date | 0 | 0% |
| published_date | 0 | 0% |
| procuring_entity (buyer) | 0 | 0% |
| title | 0 | 0% |
| description | 0 | 0% |
| source_url | 0 | 0% |
| source_record_id | 0 | 0% |

**Structured fields not modelled at all (0% coverage):** procurement method (§5),
award/supplier layer for state portals (§8), department/authority.

---

## 8. Award provenance (critical integrity finding)

| Awards | Count | Trust |
|---|---:|---|
| Total Indian awards | 20 | — |
| from `cppp` | 13 | ⚠️ **seeded** |
| from `gem` | 7 | ⚠️ **seeded** |
| from state portals (`eproc_*`) | **0** | — |
| with synthetic `eprocure.gov.in?tender=…` URL | **20 / 20** | ⚠️ **not reproducible** |

> **All 20 Indian awards are seeded and carry synthetic source URLs; none derive from a
> scraped award page, and the 14 state portals produce no awards at all.** The Indian
> corpus has **no trustworthy award/supplier layer**. Suppliers (9) and companies (9)
> are entirely a product of these seeded rows. This is the defining limitation of the
> Indian dataset and must not be demoed as verified evidence (cross-ref
> `INDIA_DATA_AUDIT.md`, `DATASET_SELECTION.md`).

---

## 9. Duplicate records

| Check | Count |
|---|---:|
| Duplicate `reference_number` | **0** |
| Duplicate `(source_name, source_record_id)` | **0** |
| Duplicate documents `(tender_id, title)` | **0** |
| Recurring buyer names (distinct buyers appearing >1×) | 42 *(expected — buyers legitimately recur across tenders)* |

> Tender-level de-duplication is clean after the Sprint-1 reference-collision fix.
> The 42 recurring buyers are not duplicates — they are the same procuring entities
> running multiple tenders (a signal, not a defect).

---

## 10. Broken references

| Check | Count |
|---|---:|
| Awards → missing tender | **0** |
| Awards → missing company | **0** |
| Documents with null `tender_id` | **0** |
| Documents → missing tender | **0** |

> **Referential integrity is intact** across the Indian corpus — every award and
> document resolves to a real parent row. (The award *provenance* problem in §8 is a
> data-authenticity issue, not a broken-reference issue.)

---

## 11. Verdict (brutally honest)

**Strengths**
- 226 tenders across 11 Indian jurisdictions with **100% buyer/date/URL/reference
  integrity** and clean de-duplication.
- Rich tender-stage evidence: 431 documents, real portal source URLs.

**Weaknesses (in priority order)**
1. **No trustworthy Indian award/supplier layer** (§8) — the corpus cannot support
   "who won" typologies with reproducible evidence. This is the #1 blocker.
2. **No procurement-method field** (§5) — 0% covered though NIC pages carry it.
3. **State attribution depends on the portal, not the data** (§3) — deterministic but
   not yet wired into the classifier.
4. **No historical depth** (§6) — single 2026 snapshot; no trend analysis.
5. **22% of tenders lack an estimated value** (§7).

**Bottom line:** the Indian dataset is an excellent, clean **tender-discovery** corpus
but is **not** yet an award-grade investigation corpus. Its integrity is real; its
award layer is not. Highest-value next data work: extract the NIC method field, wire
portal→state attribution, and source a *real* Indian award/supplier feed (or an MCA/CIN
corporate registry) — not more portals.
