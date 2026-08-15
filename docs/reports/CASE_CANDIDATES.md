# SENTRY — Investigation Case Candidates (Sprint 1, Task 1.4)

**Author:** Data Platform (Principal)
**Date:** 2026-07-11
**Scope:** shortlist only, from the **Indian** procurement corpus in the live DB.
**This document does NOT generate an investigation** — it ranks the strongest leads.
**No code changed.**

---

## Method & scoring

Every candidate is scored 1–5 on the seven required dimensions. For **False-positive
probability**, the raw score is inverted to *FP-resistance* (5 = very unlikely to be a
false alarm) so all dimensions point the same way. Weights reflect what a **verified,
evidence-backed** investigation needs first — you cannot win a hackathon on a signal a
judge cannot click through and confirm:

| Dimension | Weight |
|---|---:|
| Evidence quality (reproducible + real source URL) | ×3 |
| Manual verification potential | ×3 |
| Explainability (one-sentence, evidence-anchored) | ×2 |
| Risk indicators (strength of the anomaly) | ×2 |
| False-positive resistance | ×2 |
| Timeline completeness | ×1 |
| Documents | ×1 |

Max composite = 70.

> **The single most important filter:** the Indian *award* layer is entirely **seeded**
> (synthetic `eprocure.gov.in?tender=…` URLs; winners absent from raw storage — see
> `INDIAN_DATASET_REPORT.md` §8, `INDIA_DATA_AUDIT.md`). The flashiest signals
> (buyer==supplier, ₹-billion concentration) therefore score near-zero on evidence and
> verification and are **disqualified** despite dramatic numbers. The strongest *real*
> candidates are **tender-stage leads** from the NIC state portals, each backed by a
> live government URL.

---

## Ranked shortlist (Top 10)

| # | Candidate | Signal type | Evid | Verif | Expl | Risk | FP-res | Time | Docs | **Total** |
|---:|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|--:|
| 1 | **Dharmagarh NAC (Odisha) — 16-tender fragmentation** | Contract splitting | 5 | 5 | 5 | 4 | 3 | 4 | 3 | **61** |
| 2 | **Delhi Jal Board — "Short NIT" cluster** | Short bidding window | 5 | 5 | 4 | 4 | 3 | 4 | 3 | **59** |
| 3 | **Maharashtra RDD Yavatmal — 1-day window** | Extreme short window | 5 | 5 | 5 | 4 | 3 | 3 | 2 | **59** |
| 4 | **CE RW I Balasore (Odisha) — split + high value** | Splitting + value | 5 | 5 | 4 | 4 | 3 | 4 | 3 | **59** |
| 5 | **Irrigation & Waterways Dept (W. Bengal) — 8 tenders** | Contract splitting | 5 | 5 | 4 | 3 | 3 | 4 | 3 | **57** |
| 6 | **Travancore Devaswom Board (Kerala) — 3-day windows** | Short window | 5 | 5 | 4 | 3 | 3 | 3 | 4 | **57** |
| 7 | **Anandapur Barrage Project (Odisha) — ₹141.6M single** | Mega single-value | 5 | 5 | 4 | 3 | 2 | 4 | 4 | **56** |
| 8 | **MSME & Export Promotion (UP) — 7-tender split** | Contract splitting | 5 | 5 | 3 | 3 | 3 | 4 | 3 | **55** |
| 9 | ⚠️ **BEL self-award ₹176 cr (buyer==supplier)** | Self-dealing | 1 | 1 | 5 | 5 | 1 | 3 | 2 | **33** |
| 10 | ⚠️ **L&T / NHAI concentration ₹8.79B** | Supplier capture | 1 | 1 | 4 | 5 | 1 | 2 | 2 | **30** |

---

## Candidate detail cards

### 1 — Dharmagarh NAC (Odisha): contract fragmentation ⭐ top pick
- **Pattern:** one municipal body (`Municipal Bodies || Dharmagarh NAC`) ran **16 tenders**
  (~₹13.2M) under a single base tender id **`2026_ORULB_132524`**, split into lots
  `_6/_7/_8/_9…`, **two of them at the *identical* value ₹16,94,915** (`_6` and `_8`),
  same publish/close dates.
- **Why it's strong:** reproducible from raw storage; real Odisha portal URLs
  (`tendersodisha.gov.in`); duplicate-value lots are a classic requirement-splitting /
  threshold-avoidance signature that a reviewer can see instantly.
- **False-positive risk (honest):** municipal bodies legitimately issue many small works;
  lot-splitting can be lawful packaging. This is a *lead requiring review*, not proof.
- **Verify by:** opening the four `132524_*` notices and confirming identical scope/value.

### 2 — Delhi Jal Board: "Short NIT" short-window cluster
- **Pattern:** ≥5 tenders by Delhi Jal Board, several literally titled **"Short NIT"**, with
  compressed 5-day publish→close windows (e.g. `Short NIT No.25`, ₹10.5L; `NIT No.6`, ₹13.5L).
- **Why it's strong:** real `govtprocurement.delhi.gov.in` URLs; short bidding windows are a
  well-recognised competition-restriction flag; the buyer's own naming makes it explainable.
- **FP risk:** "Short NIT" is a legitimate NIC procedure for small/urgent works.

### 3 — Maharashtra RDD Yavatmal: 1-day bidding window
- **Pattern:** `Kalsa/Digras/2025-26` (RDD-CEO Yavatmal) — published 2026-07-07, closing
  2026-07-08 — a **single-day** window.
- **Why it's strong:** starkest single anomaly in the corpus; real `mahatenders.gov.in` URL;
  trivially explainable.
- **FP risk (honest):** missing estimated value; could be a corrigendum/re-tender extension.
  Needs the notice opened to confirm it is an original solicitation.

### 4 — CE RW I Balasore (Odisha): splitting + high value
- **Pattern:** Water-resources circle with **6 tenders (~₹10M)** plus a **₹76.6M** single
  award — concentration of works in one circle.
- **Why it's strong:** reproducible; mixes fragmentation with a genuinely large value.

### 5 — Irrigation & Waterways Dept (W. Bengal): 8-tender split
- **Pattern:** one directorate, 8 tenders (~₹3.55M), all distinct small values. Reproducible
  (`wbtenders`-class portal URLs).

### 6 — Travancore Devaswom Board (Kerala): 3-day windows
- **Pattern:** ≥2 tenders (`TDB/EEK/ET-…`) with 3-day windows; document-rich. Real Kerala
  portal URLs.

### 7 — Anandapur Barrage Project (Odisha): ₹141.6M single tender
- **Pattern:** the **largest reproducible Indian tender** (`CCEABP-03 of 2026-27`), 19-day
  window, evidence-rich.
- **FP risk (honest):** large barrage works are legitimately large — value alone is weak;
  best used to demonstrate high-value evidence handling, not as a corruption thesis.

### 8 — MSME & Export Promotion (UP): 7-tender split
- **Pattern:** one department, 7 tenders (~₹6.9M), distinct values. Reproducible.

### 9 — ⚠️ BEL self-award (buyer==supplier, ₹176 cr) — DISQUALIFIED for verified use
- **Signal:** `Bharat Electronics Limited` as **both** procuring entity and sole awarded
  supplier on `BEL/2026/RADAR/040` — the single strongest *risk* signal in the DB.
- **Why disqualified:** the record is **seeded**. "Bharat Electronics" appears in **no raw
  fixture**; the award `source_url` is a synthetic `eprocure.gov.in?tender=BEL/2026/RADAR/040`
  that does not resolve to a real award page. A judge clicking it sees fabricated evidence —
  fatal for a trust platform. Listed only to document why the obvious pick must be rejected.

### 10 — ⚠️ L&T / NHAI supplier concentration (₹8.79B) — DISQUALIFIED
- **Signal:** L&T 4 wins / ₹8.79B, plus NHAI mega-tenders (₹6.4B) — dramatic concentration.
- **Why disqualified:** the underlying CPPP tenders **and** awards are non-reproducible
  (`repro=False`, synthetic URLs; blue-chip contractors are expected winners → high FP even
  if real).

---

## Recommendation (shortlist only — no investigation generated)

- **Pursue from #1–#4** for the first Indian verified lead. **Dharmagarh NAC (#1)** is the
  best balance of a clean, reproducible, explainable pattern with real government URLs; the
  duplicate-value lots give a reviewer something concrete to confirm.
- **Frame any of these as an "oversight lead requiring review," never an allegation** — they
  are tender-stage patterns without an award layer, so they identify *where to look*, not
  *who did wrong*.
- **Do not build on #9–#10.** Their evidence is fabricated; using them is the highest
  hackathon-loss risk on the board.
- **Structural caveat:** the strongest *possible* Indian cases (favoured-supplier, cover
  bidding) require a real award/supplier layer the corpus does not yet have. Until then, the
  most defensible verified investigation remains the World Bank LUXMI concentration case
  (`DATASET_SELECTION.md`); the Indian leads above are the best *reproducible Indian* options.
