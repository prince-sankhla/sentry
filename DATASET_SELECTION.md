# SENTRY — Primary Dataset Selection for Case #001

**Author:** Data Platform (Principal)
**Date:** 2026-07-11
**Decision:** **World Bank Procurement Notices** is the primary dataset for Sprint 1 / Case #001.
**Scope:** data platform only — no frontend, risk engine, entity resolution, or investigation UI was touched.

---

## TL;DR

I audited all 22 registered sources against the only question that matters for an
**evidence-centric** platform: *can every claim in the investigation be regenerated
from a public source URL?* Exactly one dataset passes that test at usable depth,
with named suppliers, award values, and legally unimpeachable provenance:
**World Bank Procurement Notices.** I then fixed a silent identity-collision bug in
that connector that was destroying the very signal Case #001 depends on, and
re-imported. The result is a verified, fully-cited flagship finding:

> **LUXMI HARDWARE & MOTOR STORES won 9 World Bank-funded contracts (~US$5.19M)
> from Sri Lanka's Ministry of Agriculture under a single project — four of them
> as separate lots of one solicitation (LK-MOA-448081) — every award traceable to
> a distinct World Bank procurement-detail URL.**

---

## 1. The audit (brutally honest)

| Source | Tenders | Awards | Suppliers | Awards reproducible from raw? | Legal access | Verdict for Case #001 |
|---|---:|---:|---:|---|---|---|
| **world_bank** | **240** | **121** | **90** | **Yes — parsed from `notice_text` in every fixture** | World Bank Open Data API (gold standard) | ✅ **SELECTED** |
| cppp | 45 | 13 | 8 | **No — winners (L&T, Afcons…) appear in NO raw fixture; seeded elsewhere** | NIC portal ToS grey area | ❌ Provenance broken |
| state_eproc (10 portals) | 183 | **0** | 0 | Tender-only (NIC notice pages carry no award) | NIC portal ToS grey area | ❌ No award/supplier layer |
| prozorro | 1 | 1 | 1 | Yes (true OCDS) | Fully open API | ❌ Depth = 1 record |
| gem | 7 | 7 | 4 | No (source blocked; rows are legacy) | Bot-protected | ❌ Not reproducible / blocked |
| adb, un_procurement, datagovin, cag | 0 | 0 | 0 | — | gated / unverified endpoints | ❌ No data |

### Why the runners-up lose

- **CPPP is disqualifying, and dangerous.** It shows the most *dramatic* numbers
  (L&T ₹8.79B, Afcons ₹6.2B on NHAI contracts). But grepping every raw CPPP
  fixture for those winners returns **nothing** — the award rows were seeded, not
  scraped, and their `source_url`s are constructed (`…?tender=NHAI/2…`). On an
  evidence platform, a headline finding a judge cannot click through to a real
  public page is not an asset — it is the fastest way to lose. **Recommendation:
  do not demo CPPP awards; treat them as untrusted until re-derived from a real
  source.**
- **State eProcurement portals** have the richest *tender* data (buyer, value,
  dates, documents) and are genuinely Indian, but publish **no award/supplier
  data** on the pages we ingest. You cannot investigate "who won" — only
  tender-stage anomalies. Good breadth, wrong stage for a corruption narrative.
- **ProZorro** has the best schema on earth for this problem (true OCDS: bids,
  disqualifications, complaints, EDRPOU supplier codes) and a fully-open API — but
  we hold **one** record. It is the right *future* bet, not the Sprint-1 bet.
- **GeM / ADB / UN / data.gov.in** are inaccessible (bot protection, unverified
  endpoints, or API-key gating). Zero rows.

### Why World Bank wins

1. **Every claim regenerates from a public URL.** Each award is parsed
   deterministically from the `notice_text` of a fixture on disk, and each carries
   a real `https://projects.worldbank.org/.../procurement-detail/{id}` link. Under
   judge scrutiny, this is the single most important property, and only WB has it.
2. **Legally bulletproof.** World Bank Open Data is the reference corpus the entire
   open-contracting field (OCP, the Bank's own integrity unit) publishes analytics
   on. No scraping-legality question.
3. **It carries the full evidence stack.** 240 notices → **144 Contract Award
   notices**, of which 103 expose a structured bidder block: **75 name evaluated /
   rejected bidders (winners *and* losers with prices); 28 name only the awarded
   bidder (a single-bidder red flag).**
4. **Deepenable on demand.** The live API reports **410,998 notices** available
   through the existing downloader — depth is a download away, not a capability
   gap. (Not needed for Case #001; noted for later sprints.)

---

## 2. Current records (post-fix, live DB)

| Metric | Value |
|---|---:|
| World Bank tenders | **240** |
| World Bank awards | **121** |
| Distinct WB suppliers | 90 |
| WB documents (evidence) | 240 (1 source-notice URL each) |
| Awards with a value | 116 / 121 (95.9%) |
| Tenders / awards with a source URL | 100% |
| Notice types | 144 Contract Award · 48 Invitation for Bids · 48 EOI |

## 3. Data quality

- **Provenance:** 100% of WB tenders and awards carry a source URL + retrieval
  timestamp; every record has a `SourceRecordVersion` content-hash snapshot and is
  reproducible from raw storage.
- **Deduplication:** cross-page duplicate notices are collapsed by content hash on
  import; **identity is now keyed on the globally-unique notice `id`** (see §6),
  so no two distinct award notices collide.
- **Supplier normalization:** winner names are canonicalized (`normalize_org_name`
  / `org_match_key`), so repeat winners aggregate to one supplier rather than
  splitting across spelling variants — this is what makes the concentration count
  trustworthy.
- **Known semantic quirk (documented, not a bug):** for Contract Award notices,
  `noticedate` (→ `published_date`) is the *award-notice* date, so
  `award_date < published_date` is expected. A `TODO(risk-engine owner)` is left in
  the WB mapper so this is not scored as an anomaly. The data platform does not
  fabricate a synthetic publication date.

## 4. Missing fields

- **Estimated (pre-award) value:** WB award notices publish the *awarded* value,
  not a pre-tender estimate, so tender-level `estimated_value` is sparse by nature.
  Award values (the number that matters for concentration) are 95.9% present.
- **Bidder count / losing bidders:** present in `notice_text` but **not yet a
  stored field** (see §7 limitations). Currently exploited at analysis time, not
  persisted, to avoid a schema change on a locked architecture.

## 5. Typologies supported

| Typology | Support | Basis |
|---|---|---|
| **Supplier concentration / repeat winner** | ✅ Strong, DB-backed | 121 awards → LUXMI 9×, GLOBAL ENGINEERING 4×, several 3× |
| **Requirement / lot splitting** | ✅ Now visible after fix | 4 awards share solicitation `LK-MOA-448081`, queryable via `reference_number LIKE 'WB:LK-MOA-448081%'` |
| **Single-bidder / no-competition award** | ◑ Extractable | 28/103 award notices name only one bidder (Madagascar 60%, Indonesia 71%, El Salvador 100%) — in `notice_text`, not yet persisted |
| **Bid-spread / cover bidding** | ◑ Extractable | 75 notices carry evaluated/rejected bidders + prices |
| **Buyer-supplier capture** | ✅ | concentration scoped to one buyer/project (LUXMI ↔ Climate Smart Irrigated Agriculture Project) |

## 6. The fix that made Case #001 possible

The WB connector keyed each tender's unique `reference_number` on
`bid_reference_no`. But a single solicitation is routinely split into many lots
that **share** that reference (`LK-MOA-448081` covers 4 separate contract awards).
Because `reference_number` is `UNIQUE`, those lots collapsed into one row, and the
`(tender_id, company_id)` award-dedup then collapsed a supplier's multiple lot-wins
into one award. Net effect: **29 award notices silently lost, and LUXMI's 9 wins
shown as 4** — erasing exactly the concentration and lot-splitting signal an
investigation needs.

Fix (data-only, `backend/app/connectors/world_bank/mapper.py`): bind identity to
the globally-unique notice `id`, while keeping the solicitation reference as a
queryable prefix. Re-import recovered **WB 211→240 tenders, 95→121 awards, LUXMI
4→9 wins ($5.19M)**, zero failures. This is the same bug class already fixed for
the NIC state portals — non-unique human references must never be the identity key.

## 7. Limitations (say it plainly)

- **The finding is a *pattern*, not a conviction.** LUXMI winning 9 small-goods
  RFQs may be a legitimate niche local supplier. SENTRY's value is *detecting and
  fully evidencing* the concentration + lot-splitting pattern — not asserting
  fraud. Frame Case #001 as "here is a pattern worth investigating, and here is
  every source." That honesty is a strength, not a weakness.
- **Small absolute values.** LUXMI's contracts are US$175K–857K. The story is the
  *pattern*, not the sum.
- **Single-bidder is not yet persisted.** The evidence is on disk; wiring it into a
  stored field would strengthen the systemic view but needs a (small) schema
  addition the locked architecture discourages, plus risk-engine consumption
  (out of scope). Left as the top scoped next-step.
- **World Bank ≠ India.** Judges expecting an India story should be told up front
  why WB was chosen: it is the only source where the evidence chain holds. Indian
  award data (state portals) has no supplier layer, and CPPP's is untrusted.

## 8. Expected investigation quality

A single, self-contained, unforgettable evidence packet:

- **Subject:** LUXMI HARDWARE & MOTOR STORES (supplier), Sri Lanka.
- **Buyer:** Ministry of Agriculture — Climate Smart Irrigated Agriculture Project.
- **Pattern:** 9 awards / US$5,188,500; 4 lots of one solicitation; RFQ
  (limited-competition) method throughout.
- **Evidence:** 9 distinct World Bank procurement-detail URLs, each independently
  clickable; every value, date, and party regenerates from raw storage.
- **Portfolio context:** the platform can additionally report single-bidder rates
  by country (Madagascar 60%, Indonesia 71%) — showing it computes integrity
  metrics, not just one anecdote.

This is one verified finding, fully cited, defensible under scrutiny — worth more
than a thousand unverifiable features.

## 9. Recommended next steps (data platform, in priority order)

1. **Persist bidder count + losing bidders** from `notice_text` (unlocks
   single-bidder and cover-bidding as first-class, stored signals).
2. **Targeted WB acquisition** (one country/sector) to harden portfolio statistics.
3. **Re-derive or retire CPPP awards** — either scrape real award pages or remove
   the seeded rows so nothing untrusted can reach a demo.
4. **Descriptive WB document titles** to remove the weak `duplicate_documents`
   signal noted in `DATA_STATUS.md`.
