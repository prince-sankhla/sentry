# SENTRY — Deterministic Typology Calibration Report

> **Status:** Audit only — *no code changed by this document.* Produced for the
> Investigation Calibration phase. Every threshold cited is read from the live
> code: `app/services/investigation_indicators.py` (legacy detectors) and
> `app/services/risk_engine.py` (Risk Engine V2 registry, context, evidence
> validation, patterns). Grounded in the CASE #001 corpus (Indian public
> procurement; currently tender-stage Odisha/CPPP/GeM records).

---

## 0. How to read this report (shared calibration facts)

**Two severity sources exist and can diverge.** Each legacy detector sets a
per-instance `severity` (e.g. `single_bidder` → high), but the **authoritative V2
verdict uses `INDICATOR_REGISTRY[...].base_severity`**. Where they disagree, the
packet can show one severity in the finding and another in the typology table.
We already fixed one such divergence (`missing_award_data`). **Remaining known
divergences are flagged per typology below** — these are the cheapest calibration
wins.

**Severity → score is a flat band map** (`_SEVERITY_SCORE`): low 25 · medium 50 ·
high 72 · critical 92. Overall severity = strongest *pattern*, else strongest
*indicator* — **never a sum**.

**Three confidence numbers, by design:**
1. *Indicator confidence* (legacy, per detector) — e.g. more repeat awards → higher.
2. *V2 indicator confidence* — evidence-derived: `verified 0.8 / probable 0.6 / unknown 0.3`.
3. *Package confidence* (L5, `_confidence`) — coverage-based: URLs, documents,
   award completeness, timeline completeness, entity-resolution quality. **This is
   the headline confidence and is independent of the risk score.**

**Evidence validator (L3, `_validate_evidence`)** grades each indicator's supporting
records: **verified** (a document is attached), **probable** (a source URL but no
document), **unknown** (no record resolves). *Unknown caps severity at medium* —
an unverifiable indicator can never be critical.

**Context layer (L2, `_apply_context`)** suppresses/holds severity for emergency,
disaster, correction-notice, and PSU-internal situations.

**Reference frameworks used below** (established public red-flag literature; cited
by framework, not page): World Bank *Fraud & Corruption* red flags; Open
Contracting Partnership *Red Flags for Integrity*; Fazekas & Tóth *Corruption Risk
Index / elementary indicators* (DIGIWHIST / opentender.eu); EU *ARACHNE*; India
*CVC / GFR 2017 / Manual for Procurement of Works*.

**Readiness legend:** ✅ demo-ready · ⚠️ usable with caveat · ⛔ hold for demo.

---

## 1. Executive summary — readiness matrix

| # | Typology | Cat | Base sev (V2) | Evidence needed present in corpus? | FP risk | Verdict |
|--:|---|---|---|---|---|---|
| 1 | contract_fragmentation | process | medium | **yes** (tender-stage) | med | ✅ **CASE #001 anchor** |
| 2 | missing_award_data | process | low *(fixed)* | yes | low-as-signal | ✅ (as coverage note) |
| 3 | abnormal_value | value | high | needs ≥5 award values | low | ✅ (when award data exists) |
| 4 | award_value_exceeds_tender | value | high | needs estimate+award | low | ✅ (when award data exists) |
| 5 | buyer_equals_supplier | relationship | critical | needs resolved awardee | med | ⚠️ ER-dependent |
| 6 | suspicious_timing | timing | critical | needs published+award dates | **high** | ⛔ over-fires; auto-critical |
| 7 | single_bidder | competition | high | **mislabeled** (no bid count) | **very high** | ⛔ rename + regate |
| 8 | repeat_supplier | concentration | medium | needs ≥2 awards same pair | med | ⚠️ |
| 9 | buyer_concentration | concentration | medium | needs ≥3 awards/buyer | med | ⚠️ |
| 10 | supplier_concentration | concentration | medium | needs ≥3 records, 1 buyer | med-high | ⚠️ |
| 11 | award_clustering | timing | high | needs ≥3 award dates | med | ⚠️ |
| 12 | high_value / high_value_direct_award | value | medium/high | needs value ≥ ₹10 cr | med | ⚠️ threshold is global |
| 13 | duplicate_description | process | medium | needs ≥5-token text | med | ⚠️ |
| 14 | missing_documents | process | low | yes | low | ✅ (as coverage note) |
| 15–17 | gst / director / address_overlap | relationship | critical/high | **NO entity data in corpus** | n/a | ⛔ inert (cannot fire) |

**Bottom line for the demo:** exactly **one** typology is fully calibrated and
carries CASE #001 — `contract_fragmentation` — supported by `missing_award_data`
and `missing_documents` as honest coverage notes. The **critical/high** typologies
(`suspicious_timing`, `single_bidder`, the overlaps) are the ones an auditor would
attack; none of them is needed for CASE #001, and two (`suspicious_timing`,
`single_bidder`) are miscalibrated enough to be liabilities if they ever fire on
demo data. Recommended calibration order is in §4.

---

## 2. Per-typology calibration

### 1. contract_fragmentation  — *CASE #001 anchor*
1. **Purpose:** detect one buyer issuing many tenders as a single same-day batch — a possible requirement-splitting / threshold-avoidance signature.
2. **Required evidence:** `buyer`, `tender_reference`, `estimated_value`; identical `published_date` + `closing_date` across the batch.
3. **False positives:** lawful municipal ward-works bundled in one NIT; annual/quarterly budget-cycle batch releases; lot-based tendering (encouraged to widen competition). *This is the dominant risk — municipal batching is common and legal.*
4. **False negatives:** splitting spread across several days (evades same-day grouping); splitting across sibling buyer units; batch below `_FRAGMENTATION_MIN=5`.
5. **Evidence quality:** tender-stage sufficient; strengthened by identical-value pairs (now counted precisely: "N tenders in M identical-value groups"). Does **not** need award data.
6. **Minimum data:** ≥5 tenders, same buyer, same (published, closing) pair, values present.
7. **Severity — medium:** correct. A lead, not a conclusion; batching is often lawful, so never high/critical on tender-stage evidence alone.
8. **Confidence:** V2 `verified` (0.8) when notices attach; package confidence pulled down by award completeness 0/16 → 0.60 moderate. Honest.
9. **Reference:** World Bank & OCP "splitting of contracts / bid-splitting"; CVC guidance on splitting to avoid tender thresholds; Fazekas & Tóth (single-lot vs. splitting signals).
10. **Hackathon-ready:** ✅ **Yes.** Conservative threshold, defensible framing, full counter-hypotheses in the packet. The one to lead with.

### 2. missing_award_data
1. **Purpose:** flag closed tenders with no award notice on record (transparency/coverage gap).
2. **Required evidence:** `tender_reference`, `closing_date`; absence of awards.
3. **False positives:** award published on a separate results page the connector doesn't ingest (the CASE #001 reality); genuinely unconcluded/cancelled tenders; feed latency.
4. **False negatives:** award silently backfilled later; tenders with a stub award row but no real winner.
5. **Evidence quality:** low — it asserts an *absence*, which our own ingestion coverage can manufacture.
6. **Minimum data:** ≥3 closed, award-less tenders.
7. **Severity — low (just corrected from medium):** correct. It is a coverage/transparency gap, not a peer of competition/value anomalies; must not rival `contract_fragmentation`.
8. **Confidence:** intentionally modest; also already surfaced as a §11 *missing-evidence* item, so it should not double-count as a risk peer.
9. **Reference:** OCP transparency/publication-completeness indicators.
10. **Hackathon-ready:** ✅ as a **coverage note**, not a red flag. Framing now defensible.

### 3. abnormal_value
1. **Purpose:** award value that is a statistical outlier within the retrieved set.
2. **Required evidence:** ≥5 award values (`_MIN_ABNORMAL_SAMPLE`), a positive median.
3. **False positives:** a legitimately larger-scope lot mixed with small ones; heterogeneous categories in one package; small-sample artefacts.
4. **False negatives:** collusive values clustered *near* the median; outliers hidden when the whole package is high-value.
5. **Evidence quality:** robust — median + MAD, modified z ≥ 3.5 (high ≥ 6); degrades gracefully to a median-ratio test when MAD = 0.
6. **Minimum data:** ≥5 awards *with values* — **absent in the tender-stage CASE #001 corpus.**
7. **Severity — high:** justified for a ≥3.5σ robust outlier; medium below 6σ. Reasonable.
8. **Confidence:** scales with z and sample size; sound.
9. **Reference:** DIGIWHIST/Fazekas price-outlier indicators; ARACHNE value-anomaly.
10. **Hackathon-ready:** ✅ **when award-value data is present.** Cannot fire on the current corpus (no awards). Statistically the strongest-built detector.

### 4. award_value_exceeds_tender
1. **Purpose:** awarded value materially exceeds the tender estimate (>2×).
2. **Required evidence:** `estimated_value` **and** `award_value` on the same tender.
3. **False positives:** lawful scope revision/variation; conservative estimate; price-discovery outcome.
4. **False negatives:** overruns between 1×–2×; overruns hidden in later contract amendments not ingested.
5. **Evidence quality:** high when both figures are primary-source; the 2× gate is deliberately conservative.
6. **Minimum data:** one tender with both estimate and award value — **absent in CASE #001.**
7. **Severity — high:** justified; a >2× overrun is a strong, specific signal.
8. **Confidence:** high when both values are present and sourced.
9. **Reference:** World Bank cost-overrun red flags; ARACHNE contract-modification indicators.
10. **Hackathon-ready:** ✅ when award data exists; inert on current corpus.

### 5. buyer_equals_supplier
1. **Purpose:** the awarded supplier resolves to the procuring entity itself.
2. **Required evidence:** resolved buyer identity **and** resolved awardee identity (CIN/normalized name).
3. **False positives:** lawful intra-PSU/inter-unit transfer; entity-resolution collapsing a unit and its parent; shared registration across group units.
4. **False negatives:** self-dealing via a thinly-separate shell (defeats identity match); missing awardee registration.
5. **Evidence quality:** entirely dependent on entity-resolution precision — the highest-variance dependency.
6. **Minimum data:** an award with a resolvable company identity — **absent in CASE #001 (no awards).**
7. **Severity — critical, but L2 downgrades to medium when a PSU buyer is present.** Correct in spirit. **KNOWN DEFECT:** the pattern `buyer_supplier_identity` still classifies *critical* on indicator presence, ignoring the context-adjusted medium — a self-contradiction (fires nowhere in CASE #001, but a calibration item).
8. **Confidence:** should be gated on ER confidence ≥ threshold; currently inherits evidence-status only.
9. **Reference:** OCP conflict-of-interest / related-party; ARACHNE beneficial-owner overlap.
10. **Hackathon-ready:** ⚠️ only with a verified resolved awardee **and** the pattern/context contradiction fixed. Powerful but ER-fragile.

### 6. suspicious_timing  — *auditor magnet*
1. **Purpose:** award landing implausibly soon (0–3 days) after publication.
2. **Required evidence:** `published_date` and `award_date` on the same tender.
3. **False positives:** **high** — emergency/disaster procurement; corrigendum-shortened cycles; pre-qualified/rate-contract call-offs; *and data artefacts where `award_date` is a record-entry date, not the true award date.*
4. **False negatives:** compressed process where dates were back-dated to look normal.
5. **Evidence quality:** weak unless the dates are confirmed to mean publication vs. genuine award (not ingestion timestamps).
6. **Minimum data:** both dates, trustworthy semantics.
7. **Severity — critical (L2 *forces* critical unless a correction notice exists):** **over-aggressive.** Auto-critical on a 0–3-day gap, with only a corrigendum as escape, is the least defensible severity rule in the engine.
8. **Confidence:** 0.6–0.7 regardless of date provenance — too high for a field whose semantics are unverified.
9. **Reference:** Fazekas & Tóth "short decision period"; OCP "abnormally short bidding period." *Note: literature usually flags the **bidding window** (publish→close), not publish→award.*
10. **Hackathon-ready:** ⛔ **Hold.** Do not let it fire in the demo. Recommend: drop the forced-critical rule, cap at high, and require the 0-day case to be evidence-verified.

### 7. single_bidder  — *mislabeled*
1. **Purpose:** intended = only one *bidder* (no competition). **Actual = only one recorded *awardee*.**
2. **Required evidence:** intended needs a *recorded bidder count*; the corpus has none — it only records winners.
3. **False positives:** **very high** — nearly every works/supply contract has one winner, so this fires almost universally and means "was awarded," not "uncompetitive."
4. **False negatives:** true single-bidder cases where multiple awardees are listed for lots.
5. **Evidence quality:** the required field (`recorded_bidders`) does not exist in the data → the indicator cannot mean what it claims.
6. **Minimum data:** a real bid count — **not available.**
7. **Severity — high:** unjustified given the mislabeling; a near-universal condition should not be high.
8. **Confidence:** 0.6–0.75 is far too confident for "one *awardee*."
9. **Reference:** Fazekas & Tóth "single bidder on a competitive market" — the canonical CRI indicator, but it *requires bid counts*.
10. **Hackathon-ready:** ⛔ **Hold.** Rename to `single_recorded_awardee`, drop severity to low/medium, and gate the true single-bidder meaning on a real bid-count field. Not needed for CASE #001.

### 8. repeat_supplier
1. **Purpose:** same supplier repeatedly awarded by the same buyer (preferential relationship).
2. **Required evidence:** `buyer`, `awarded_supplier`, ≥2 distinct awarded tenders for the pair.
3. **False positives:** legitimate specialisation; framework/rate contracts; thin qualified-vendor pool.
4. **False negatives:** favouritism rotated across related shells; awards split so no pair reaches 2.
5. **Evidence quality:** good when awardee identity is resolved; weak if names aren't normalized (misses/merges pairs).
6. **Minimum data:** ≥2 awards, same buyer+supplier — **absent in CASE #001.**
7. **Severity — registry medium (builder: high at ≥3):** **DIVERGENCE** — builder escalates to high at ≥3 awards, but V2 uses registry medium. Calibrate to one scale.
8. **Confidence:** grows with award count; sound.
9. **Reference:** OCP "supplier concentration"; ARACHNE recurrent-awardee.
10. **Hackathon-ready:** ⚠️ with award data + the medium/high divergence resolved.

### 9. buyer_concentration
1. **Purpose:** a buyer routes most awarded value/awards to one supplier (≥50% share, ≥3 awards).
2. **Required evidence:** `buyer`, per-supplier award shares.
3. **False positives:** genuinely thin category market; small sample (3 awards, 50% = 2 awards).
4. **False negatives:** concentration measured by count not value (a few huge awards can hide).
5. **Evidence quality:** medium; count-based share is coarse.
6. **Minimum data:** ≥3 awards for the buyer — **absent in CASE #001.**
7. **Severity — registry medium (builder high at ≥70%):** **DIVERGENCE**; also `score = share×100` in the builder vs. flat band in V2. Pick one.
8. **Confidence:** scales with sample; okay.
9. **Reference:** Fazekas market-concentration (HHI-style); OCP.
10. **Hackathon-ready:** ⚠️ with award data; prefer value-weighted share before enterprise use.

### 10. supplier_concentration
1. **Purpose:** a supplier whose recorded wins (≥3) all come from a single buyer (captive dependence).
2. **Required evidence:** `awarded_supplier`, distinct buyer set.
3. **False positives:** **medium-high** — a specialised vendor lawfully serving one client (defence/railway-specific); small retrieval sample where only one buyer's data was ingested.
4. **False negatives:** dependence masked when the retrieval package spans multiple buyers by chance.
5. **Evidence quality:** *sensitive to retrieval scope* — precision retrieval that returns one buyer's records can manufacture "1 distinct buyer."
6. **Minimum data:** ≥3 records for the supplier — **absent in CASE #001.**
7. **Severity — medium:** reasonable, but the retrieval-scope artefact argues for caution.
8. **Confidence:** should discount when the package itself is single-buyer by construction.
9. **Reference:** OCP supplier-dependence; ARACHNE.
10. **Hackathon-ready:** ⚠️ needs a "package spans ≥N buyers" guard to avoid scope artefacts.

### 11. award_clustering
1. **Purpose:** many awards to one supplier inside a 30-day window (rapid cadence).
2. **Required evidence:** ≥3 award *dates* for the supplier.
3. **False positives:** a large national supplier legitimately winning across unrelated buyers; fiscal-year-end award bursts.
4. **False negatives:** clustering just outside 30 days; award dates missing.
5. **Evidence quality:** depends on trustworthy award-date semantics (same caveat as `suspicious_timing`).
6. **Minimum data:** ≥3 dated awards — **absent in CASE #001.**
7. **Severity — high (≥4) / medium (3):** slightly aggressive for a cadence signal; medium-leaning would be safer.
8. **Confidence:** scales with cluster size; okay.
9. **Reference:** Fazekas timing indicators; ARACHNE.
10. **Hackathon-ready:** ⚠️ with award-date provenance confirmed.

### 12. high_value / high_value_direct_award
1. **Purpose:** flag tenders in the high-value oversight band (≥ ₹10 cr); "direct award" if a single awardee.
2. **Required evidence:** `estimated_value` (+ single awardee for the direct variant).
3. **False positives:** scale ≠ irregularity; large EPC/defence/infra legitimately run to hundreds of crore.
4. **False negatives:** structured splitting keeps each lot below ₹10 cr (exactly the CASE #001 sub-threshold pattern — *value alone misses it; fragmentation catches it*).
5. **Evidence quality:** high for the value fact; low as a *risk* signal on its own.
6. **Minimum data:** a value ≥ ₹10 cr — **CASE #001's largest is ₹16.95 lakh, far below.**
7. **Severity — medium (high if direct):** value-only medium is defensible as "oversight band," not wrongdoing.
8. **Confidence:** high for the number, but it's a band flag, not an anomaly.
9. **Reference:** GFR/CVC value-threshold oversight tiers; World Bank prior-review thresholds.
10. **Hackathon-ready:** ⚠️ the ₹10 cr threshold is a global constant — should be regime/category-relative before it's trustworthy across states.

### 13. duplicate_description
1. **Purpose:** near-identical tender text across distinct tenders (recycled/tailored specs).
2. **Required evidence:** normalized tender text ≥5 tokens (`_text_fingerprint`).
3. **False positives:** standardised/recurring requirements legitimately reuse templates and SoR text.
4. **False negatives:** exact-match fingerprint misses paraphrased or lightly-edited duplicates (no fuzzy/shingle similarity).
5. **Evidence quality:** medium; exact normalized match only — brittle.
6. **Minimum data:** ≥2 tenders with substantive descriptions — CASE #001 titles are distinct works (won't fire).
7. **Severity — medium:** reasonable.
8. **Confidence:** grows with count; okay.
9. **Reference:** DIGIWHIST tender-text similarity; ARACHNE.
10. **Hackathon-ready:** ⚠️ upgrade to shingled/fuzzy similarity before relying on it.

### 14. missing_documents
1. **Purpose:** tender with no attached procurement documents.
2. **Required evidence:** `tender_reference`, document set.
3. **False positives:** portal simply didn't expose the PDF (coverage), not suppression.
4. **False negatives:** documents present but irrelevant/placeholder.
5. **Evidence quality:** low — asserts an absence tied to ingestion coverage.
6. **Minimum data:** tenders present.
7. **Severity — low:** correct (parallels the corrected `missing_award_data`).
8. **Confidence:** modest; a coverage note.
9. **Reference:** OCP documentation-completeness.
10. **Hackathon-ready:** ✅ as a coverage note (not a red flag).

### 15–17. gst_overlap · director_overlap · address_overlap  (related-party)
1. **Purpose:** two ostensibly distinct suppliers share a GSTIN / director / registered address (collusion/related-party).
2. **Required evidence:** supplier-level GSTIN, directors, or registered address.
3. **False positives:** shared business park/secretarial address; independent-director overlaps across groups; branch/division sharing one GSTIN.
4. **False negatives:** the corpus has **no** GSTIN/director/address fields, so these currently **cannot fire at all** (declared only to let patterns reference them).
5. **Evidence quality:** would be high *if* sourced from MCA21/GST portal — not present.
6. **Minimum data:** entity-attribute enrichment that does not exist yet.
7. **Severity — critical (gst) / high (director, address):** justified *in principle*, but inert.
8. **Confidence:** n/a (never triggers).
9. **Reference:** OCP beneficial-ownership; ARACHNE related-party; MCA21/GST cross-checks.
10. **Hackathon-ready:** ⛔ **Inert.** Keep declared for the pattern library; do not present as active capability until entity enrichment lands.

---

## 3. Cross-cutting calibration findings

- **C1 — Severity source divergence.** `repeat_supplier` and `buyer_concentration` escalate to *high* in the legacy builder but are *medium* in the V2 registry; the builder also uses graded scores while V2 uses flat bands. The packet can therefore show inconsistent severities. **Pick the V2 registry as the single source and delete builder-side severity, or reconcile explicitly.**
- **C2 — Pattern ignores context-adjusted severity** (`buyer_supplier_identity`, others): `_classify` keys on indicator *presence*, so a context-downgraded indicator can still raise a critical pattern. Self-contradiction; fix before any relationship typology is demoed.
- **C3 — `suspicious_timing` forced-critical** is the most aggressive, least-defensible rule and rests on unverified date semantics.
- **C4 — `single_bidder` mislabeling** ("awardee" ≠ "bidder") is the highest-volume false-positive source once award data is ingested.
- **C5 — Date/field provenance** (`award_date`, `published_date`) is assumed to be the true event date, not a record-entry timestamp — unverified for timing typologies.
- **C6 — Retrieval-scope artefacts** can manufacture `supplier_concentration` / single-buyer conditions; concentration typologies need a "package spans ≥N buyers" guard.
- **C7 — Global constants** (`_HIGH_VALUE` ₹10 cr, `_CLUSTER_WINDOW_DAYS` 30, `_SUSPICIOUS_AWARD_DAYS` 3) are not regime/category-relative.

## 4. Recommended calibration order (for your approval — no code yet)

1. **`suspicious_timing`** — remove forced-critical, cap at high, require 0-day cases to be evidence-verified. *(highest defensibility risk)*
2. **`single_bidder`** — rename `single_recorded_awardee`, drop to low/medium, gate true single-bidder on a real bid count.
3. **C2 pattern/context contradiction** — make `_classify` consume context-adjusted severity.
4. **C1 severity-source reconciliation** — `repeat_supplier`, `buyer_concentration` onto one scale.
5. **Concentration scope guard** (C6) and **value/timing constants** (C7) — enterprise-hardening, lower demo urgency.

None of items 1–5 affects CASE #001's current output (fragmentation + coverage notes). They harden the library against the moment award/entity data is ingested and protect the demo from an embarrassing critical false positive.

---

*This is a calibration audit, not a code change. Awaiting approval on §4 ordering
before modifying any typology.*
