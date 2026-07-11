# SENTRY — Case #001: Dharmagarh NAC Tender Fragmentation

**Status:** Verified oversight lead — **NOT an allegation of wrongdoing.**
**Produced by:** the existing SENTRY investigation pipeline (planner → DB executor →
deterministic Risk Engine V2) run against the live Indian corpus. No conclusion of
corruption is drawn anywhere in this document.
**Subject (buyer):** `Municipal Bodies || Dharmagarh NAC` — Dharmagarh Notified Area
Council, Kalahandi district, Odisha.
**Generated:** 2026-07-11 · **Data source:** Odisha eProcurement (`tendersodisha.gov.in`).
**Evidence First:** every claim below resolves to a public government URL and
regenerates deterministically from raw storage.

---

## 0. What the platform detected (one paragraph)

A single procuring entity — the Dharmagarh Notified Area Council — issued **16 works
tenders as one same-day batch** (all published **2026-06-22**, all closing
**2026-07-08**) under a single NIT batch id **`2026_ORULB_132524`**, together worth
**₹1,32,45,762** (~₹1.32 crore). The tenders are small ward-level road and drain works,
several priced near common competitive-bidding thresholds, and **two pairs carry
identical estimated values**. The deterministic engine flagged this as
**Contract Fragmentation (medium)** plus **Missing Award (medium)** — an *oversight
lead requiring manual review*, not evidence of an offence.

---

## 1. Every related tender (16)

All 16 share buyer **Dharmagarh NAC**, publication **2026-06-22**, closing **2026-07-08**,
currency **INR**, source **eproc_odisha**. Each `#` links to its official notice in §6.

| # | Lot reference | Work | Estimated value (₹) |
|--:|---|---|--:|
| [1](#u1) | 2026_ORULB_132524_3 | Drain w/ cover slab — Pabitra→Sanjib Bania house | 8,55,932 |
| [2](#u2) | 2026_ORULB_132524_4 | Paver road — Ranjit Panda→Sarat Mund house | 8,00,847 |
| [3](#u3) | 2026_ORULB_132524_5 | Paver road — Women's College→canal, Ward 8 | 5,08,475 |
| [4](#u4) | 2026_ORULB_132524_6 | Road — PWD road→New Kalyani Mandap (MPH) | **16,94,915** |
| [5](#u5) | 2026_ORULB_132524_7 | Drain — Markand Mahananda house→park backside | 10,23,729 |
| [6](#u6) | 2026_ORULB_132524_8 | Road — Bridge→Ratanpur connecting road, Ward 12 | **16,94,915** |
| [7](#u7) | 2026_ORULB_132524_9 | Guardwall + road — RD road→Smasan | 11,66,949 |
| [8](#u8) | 2026_ORULB_132524_15 | Road — Main road→Biki Hati house, Ward 12 | 2,54,237 |
| [9](#u9) | 2026_ORULB_132524_16 | Road — Alishan Restaurant→Behera Babu house | 7,62,712 |
| [10](#u10) | 2026_ORULB_132524_17 | CC drain w/ road — Siba Naik house→banyan tree | **8,47,458** |
| [11](#u11) | 2026_ORULB_132524_20 | Road — Main road→Dillip Joshi house, Ward 7 | **8,47,458** |
| [12](#u12) | 2026_ORULB_132524_21 | Repair of Bhandaragharani market complex | 3,88,136 |
| [13](#u13) | 2026_ORULB_132524_22 | Road — PWD road→Mahipal Mahananda house, Ward 11 | 4,21,186 |
| [14](#u14) | 2026_ORULB_132524_25 | Paver road — Nandi Kisore Majhi→Labaram Bania house | 3,85,593 |
| [15](#u15) | 2026_ORULB_132524_27 | Road w/ drain — NH→Jaising Naik house, Ward 3 | 5,76,271 |
| [16](#u16) | DHM/03/2026-27 | Road — Biswajit Ghosh→Keshari Naik house | 10,16,949 |
| | | **TOTAL (16 tenders)** | **1,32,45,762** |

**Structural observations (deterministic, from the data):**
- **One buyer, one batch, one day:** all 16 share NIT base id `2026_ORULB_132524`
  (lots 3–27, non-contiguous) except one legacy-formatted reference (`DHM/03/2026-27`).
- **Identical-value pairs:** lots `_6` and `_8` are both ₹16,94,915; lots `_17` and `_20`
  are both ₹8,47,458. Note ₹16,94,915 = exactly **2 × ₹8,47,458**.
- **All below ₹17 lakh:** the largest is ₹16.95 lakh; 14 of 16 are under ₹12 lakh —
  the value band where limited/quotation procedures are typically permissible.

---

## 2. Complete investigation timeline

| Date | Event | Evidence |
|---|---|---|
| **2026-06-22** | All 16 tenders **published** simultaneously by Dharmagarh NAC under NIT `2026_ORULB_132524`. | 16 notices (§6) |
| 2026-06-22 → 07-08 | 16-day open bidding window (standard length — *not* a short-window flag). | published/closing dates |
| **2026-07-08** | All 16 tenders **close** on the same day. | 16 notices (§6) |
| 2026-07-08 → present | **No award, no supplier, no bid record** published on the ingested notice pages for any of the 16. | `missing_award_data` (§4) |
| 2026-07-11 | SENTRY ingest + deterministic assessment: **Contract Fragmentation (medium)**. | this case file |

> The timeline is **tender-stage only**. There is no award, contract-signing, or
> payment event in the data — a material evidence gap (§/Missing Evidence).

---

## 3. Evidence chain

```
Odisha eProc portal (tendersodisha.gov.in)
   └─ NIT batch 2026_ORULB_132524  (Dharmagarh NAC)
        ├─ 16 tender notices  ──►  raw envelope (data/raw/eproc_odisha/*.json, content-hashed)
        │                              └─ SourceRecordVersion snapshot (reproducible)
        ├─ normalized Tender rows (buyer, value, dates, source_url)  ── 16
        ├─ Document rows (source_notice, 1 per tender)               ── 16
        └─ Deterministic Risk Engine V2
               ├─ contract_fragmentation  [medium · evidence: verified · 16 records]
               └─ missing_award_data       [medium · evidence: verified · 16 records]
```
Every link is content-hashed and regenerable: the same raw files reproduce the same
16 tenders, the same values, and the same two indicators.

---

## 4. Triggered typologies (deterministic — actual engine output)

Run: `assess_risk_v2()` over the 16-record package (also reproduced via
`POST /api/investigations/execute`). **Overall severity: MEDIUM (score 50).
Confidence: moderate (0.60). No critical pattern.**

| Indicator | Severity | Evidence | Records | Why it fired |
|---|---|---|--:|---|
| **contract_fragmentation** | medium | verified | 16 | 16 tenders from one buyer share a single publication + closing date, ₹1.32 cr total, 2 identical-value pairs — a possible requirement-splitting pattern. |
| **missing_award_data** | medium | verified | 16 | All 16 have passed their closing date with no recorded award — a competition/transparency gap in the available records. |

**Typologies that were tested and did NOT fire** (honest negative space):
`single_bidder`, `buyer_equals_supplier`, `repeat_supplier`, `buyer_concentration`,
`abnormal_value`, `suspicious_timing`, `award_value_exceeds_tender`, `gst/director/
address_overlap` — **all require award or entity data this tender-stage corpus does not
have.** Their absence is *not* exoneration; it is missing evidence (§/Missing Evidence).

---

## 5. Why this became suspicious (the case FOR review)

1. **Fragmentation signature.** Splitting one programme of works into many small,
   same-day contracts is the textbook mechanism for keeping each package below the
   threshold that would trigger open competitive tendering or higher approval — a
   recognised red flag (World Bank, OCP, CVC guidance on "splitting of works").
2. **Simultaneity.** 16 tenders published and closing on the exact same two dates under
   one NIT id is consistent with a single underlying requirement packaged into lots.
3. **Identical-value pairs + a 2× relationship** (₹16,94,915 = 2 × ₹8,47,458) suggest a
   common unit-rate/estimation template rather than independently scoped works.
4. **Sub-threshold clustering.** Every value sits in the band where lighter procurement
   procedures are permissible; none crosses into the highest-scrutiny bracket.
5. **No award transparency.** None of the 16 shows a published award/supplier, limiting
   external verification of who ultimately won the bundle.

---

## 6. Every official source URL (16)

Live Odisha government procurement notices — each independently clickable and verifiable.

<a id="u1"></a>1. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=S4VLHe8c2enJOZd9oUWZe9Q%3D%3D
<a id="u2"></a>2. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SBv3Sdz8%2Fiql2vkLfsSDQSg%3D%3D
<a id="u3"></a>3. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SCBX7E9wNaRKsFmF3Kd4O3g%3D%3D
<a id="u4"></a>4. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SD1kwlHVaxU2Oqwz6rgQ2LA%3D%3D
<a id="u5"></a>5. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SFM%2BuufSgGqP7KaZPV5Yy8Q%3D%3D
<a id="u6"></a>6. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=S9zpZqQTq2azX8wBl7ZK2AA%3D%3D
<a id="u7"></a>7. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SgTFoDKNHj7OQMUx7%2FWND5Q%3D%3D
<a id="u8"></a>8. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SzstJjcKpWbPkPS5108exWw%3D%3D
<a id="u9"></a>9. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SA2QBRRAlm5icUklC%2FtxKYw%3D%3D
<a id="u10"></a>10. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=S76EA9oVHe0Y1zGLo6%2FGhMQ%3D%3D
<a id="u11"></a>11. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=S3wJZbFFZAI9V5WB4MuKAZg%3D%3D
<a id="u12"></a>12. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SjW8ll1fEUrT2K24maYZilA%3D%3D
<a id="u13"></a>13. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=S21NjxUT1Zwq2iEHLpEJsdg%3D%3D
<a id="u14"></a>14. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SEUNjn4elRpvPRS5vv5dkWw%3D%3D
<a id="u15"></a>15. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=SDjftyCMzR8OdKC7jb3wOSQ%3D%3D
<a id="u16"></a>16. https://tendersodisha.gov.in/nicgep/app?component=%24DirectLink&page=FrontEndListTendersbyDate&service=direct&session=T&sp=Smn6xJatB%2BY%2BBQ4%2FVVo2NyA%3D%3D

---

## 7. Every supporting document

| Tender | Document | Type | Link |
|---|---|---|---|
| all 16 | "Source notice" | source_notice | the 16 URLs in §6 (one per tender) |

> **Evidence-quality caveat (honest):** the only document preserved per tender is the
> **source notice** itself. No Bill of Quantities, technical spec, corrigendum, bidder
> list, or award letter is present in the ingested data. Evidence is *authentic but
> thin* — sufficient to establish the fragmentation pattern, insufficient to explain it.

---

## 8. Every possible innocent explanation (the case AGAINST alarm)

This pattern is **routinely lawful**. A reviewer must weigh all of the following:

1. **Standard municipal ward-works budgeting.** Urban local bodies routinely float all
   ward-level development works for a budget cycle in a **single consolidated NIT**;
   one publish/close date is administratively normal, not evasive.
2. **Distinct, genuinely separate works.** Each lot is a *different* road/drain in a
   *different* ward — these are legitimately separate physical works, not one contract
   artificially sliced.
3. **Lot-based tendering is legal and encouraged.** Packaging a programme into lots can
   *increase* competition by letting small local contractors bid per lot.
4. **Identical values are expected** when works use the same **Schedule of Rates (SoR)**
   and similar dimensions; ₹8,47,458 recurring reflects a common unit-rate estimate, and
   a 2× value simply means "twice the length/area."
5. **Sub-threshold values may be genuine.** Small ward works are inherently low-value;
   staying under a threshold can be the honest size of the work, not manipulation.
6. **Missing award ≠ no award.** Awards are often published on a *separate* results page
   the current connector does not ingest; absence in our data is a coverage gap, not
   proof of a withheld award.
7. **Open 16-day window.** The bidding window is a normal length — there is **no**
   short-window competition-restriction signal here.

**Because of 1–7, this case NEVER concludes corruption. It is a lead for verification.**

---

## 9. Evidence strength

| Dimension | Rating | Basis |
|---|---|---|
| Source authenticity | **High** | 16 live `tendersodisha.gov.in` notices; reproducible from raw storage |
| Pattern determinism | **High** | fragmentation computed deterministically; identical inputs → identical result |
| Timeline completeness | **Low–Medium** | publish + close present; **no** award/contract/payment stage |
| Document depth | **Low** | source notice only; no BOQ/spec/award letter |
| Entity resolution | **None** | no suppliers named (tender-stage) |
| False-positive probability | **Medium–High** | municipal batch tendering is commonly lawful (§8) |
| **Overall evidentiary weight** | **Medium** | a credible, well-evidenced *lead* — not a finding |

---

## 10. Investigation Summary

Dharmagarh Notified Area Council published **16 ward-level works tenders (₹1.32 crore)**
as a **single same-day batch** under one NIT id, with two identical-value pairs and all
values in the sub-threshold band. SENTRY's deterministic engine surfaces this as
**Contract Fragmentation (medium)** with a co-occurring **Missing Award (medium)** gap.
The evidence is **authentic and reproducible but thin and tender-stage-only**. The
pattern is consistent *both* with lawful municipal ward-works budgeting *and* with
requirement-splitting to avoid competitive thresholds — SENTRY **cannot and does not
distinguish between them from the available data**. This is an **oversight lead requiring
manual verification, not an allegation.**

## Evidence Timeline
2026-06-22 (16 tenders published, one NIT) → 2026-06-22…07-08 (16-day window) →
2026-07-08 (16 tenders close) → post-close (no award data ingested) → 2026-07-11
(deterministic flag: Contract Fragmentation, medium). *Award/contract/payment stages: absent.*

## Triggered Typologies
- **contract_fragmentation** — medium — verified — 16 records.
- **missing_award_data** — medium — verified — 16 records.
- Overall: MEDIUM (50/100); confidence moderate (0.60); no critical pattern.

## Evidence Strength
**Medium.** High source authenticity and determinism; low timeline/document depth; no
entity data; medium–high false-positive probability. A strong *lead*, not a finding.

## Missing Evidence
1. **Award / winning-bidder data** for all 16 (who won each lot, at what value).
2. **Number of bidders per lot** (single-bidder would sharply raise concern).
3. **Bills of Quantities / technical specs** to confirm the works are genuinely distinct.
4. **The consolidated NIT document** and any corrigenda.
5. **Odisha's applicable threshold rules** for open tendering vs. limited/quotation.
6. **Prior-year NAC tenders** to establish whether this batch size is routine or anomalous.

## Recommended Manual Verification
1. Open the four `2026_ORULB_132524_6/_8/_17/_20` notices (§6) and confirm the identical
   values correspond to genuinely different works.
2. On the Odisha portal, pull the **award/results** page for NIT `2026_ORULB_132524` and
   record winners + bidder counts per lot.
3. Check whether the 16 lots were awarded to **one contractor or a few** (concentration).
4. Compare the ₹16.95 lakh top value against **Odisha's competitive-tender threshold**.
5. Retrieve the consolidated NIT to confirm a single underlying requirement.

## Next Evidence Required
- **Highest priority:** ingest the Odisha portal's **award-results pages** so single-bidder,
  buyer-concentration, and repeat-supplier typologies can run on this exact batch.
- Ingest **tender attachments** (BOQ/NIT PDF) to move document depth from Low to High.
- Add **prior-cycle NAC history** to test whether same-day 16-lot batches are the norm.

---
*This document is an automated oversight lead generated by SENTRY's deterministic
pipeline. It identifies where to look; it does not conclude that any wrongdoing occurred.
Every figure and link regenerates from public sources and raw storage.*
