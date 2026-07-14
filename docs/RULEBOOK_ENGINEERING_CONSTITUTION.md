# SENTRY Procurement Intelligence Rulebook

## Book II — Engineering Constitution (v1.0, Final Constitutional Review)

> **Status of this Book.** Book I (Philosophy, Oversight Mandate, Evidence
> Hierarchy, and the Indicator Framework) is *already ratified* and is **not**
> restated here. This Book completes the missing engineering specifications
> required to freeze Rulebook v1.0. It is the deterministic, auditable, legally
> defensible substrate on which Book I's indicators operate. Where this Book and
> the shipped engine (`app/services/risk_engine.py`,
> `app/services/investigation_indicators.py`) disagree, the *engine constants
> quoted here are canonical* — this Book was reconciled against them during the
> final review.

### Provenance legend

Every non-trivial claim in this Book is tagged so auditors can separate law from
architecture. **We never present an architectural choice as a legal
requirement.**

| Tag | Meaning |
|-----|---------|
| `[BP]`   | Universally accepted procurement best practice |
| `[INTL]` | Internationally recognized framework (OECD Integrity, World Bank / ADB Procurement Frameworks, UNCITRAL Model Law, UN Procurement) |
| `[IN]`   | India-specific practice (GFR 2017, CVC guidance, MCA/DIN, GST/GSTIN, CPPP/GeM) |
| `[ARCH]` | SENTRY architectural recommendation (this platform's design, not a legal norm) |

### First principles that bind every section below

1. **Oversight, never adjudication.** `[ARCH]` The engine surfaces *integrity
   indicators*. It never declares fraud, corruption, bid-rigging, or collusion.
   Every output terminates in `"Requires Investigator Review"`
   (`REVIEW_NOTE`) and carries `OVERSIGHT_DISCLAIMER`.
2. **Determinism over intelligence.** `[ARCH]` Risk and confidence are computed
   by pure functions of the evidence. The LLM *narrates* the structure the
   engine proves; it never computes, ranks, or invents a score, a pattern, or a
   recommendation.
3. **No fact without a source.** `[BP]` A detector that cannot ground a signal in
   a real record emits nothing. Unverifiable signals are capped, never
   amplified.
4. **False-positive suppression outranks detection.** `[BP]` When in doubt,
   *reduce interpretation severity* — never fabricate a finding to raise recall.
5. **Reproducibility.** `[ARCH]` Same package + same rule version ⇒ byte-identical
   assessment. No wall-clock, no randomness, no network in the scoring path.

---

## 1. Rule Identification System (RIS)

**Purpose.** A permanent, immutable naming standard so that every rule,
indicator, pattern, context modifier, confidence dimension, recommendation, and
governance clause has a stable public identifier that engineers, auditors,
investigators, courts, and future AI systems can cite for the next decade.

### 1.1 Identifier grammar

```
<DOMAIN>-<NNN>[.<variant>]        canonical rule ID
<DOMAIN>-<NNN>@<major.minor>      version-pinned citation
```

* `DOMAIN` — a fixed three/four-letter namespace (table below). Immutable.
* `NNN` — zero-padded ordinal, assigned once, **never reused, never
  renumbered**, even after deprecation.
* `.variant` — optional sub-rule (e.g. `TIME-001.a`) for jurisdictional or
  band variants that share the same detector semantics.
* `@major.minor` — the rule-version the citation refers to (see §1.4). A bare
  ID always means "latest active version".

**Golden rule `[ARCH]`: an ID, once issued, is frozen forever.** Renaming the
human-facing label is permitted; changing the ID is prohibited. This is what
makes a five-year-old audit report still resolvable.

### 1.2 Domain namespaces

| Domain | Meaning | Governs |
|--------|---------|---------|
| `COMP` | Competition & transparency indicators | single-bidder, direct award, award-data gaps |
| `FIN`  | Financial / value indicators | high value, value spikes, award-vs-estimate |
| `TIME` | Temporal indicators | compressed timelines, award clustering |
| `REL`  | Relationship / related-party indicators | repeat supplier, concentration, GST/director/address overlap, buyer≡supplier |
| `DOC`  | Document integrity & process indicators | missing documents, duplicated specifications |
| `CTX`  | Context modifiers (Layer 2) | emergency, disaster, correction, PSU-internal |
| `PAT`  | Deterministic patterns (Layer 4) | rule-combination patterns |
| `CONF` | Confidence dimensions (Layer 5) | the confidence-model weights |
| `EXP`  | Explainability contract | the audit-trail node schema |
| `REC`  | Recommendation rules | evidence-backed next actions |
| `THR`  | Threshold parameters | configurable numeric limits |
| `JUR`  | Jurisdiction profiles | India / World Bank / ADB / UN / future |
| `FP`   | False-positive suppression rules | benign-explanation handling |
| `GOV`  | Engineering governance clauses | lifecycle, review, migration |
| `ONT`  | Ontology mapping contracts | rule→entity bindings |

### 1.3 Canonical registry (frozen assignment)

These IDs are bound to the **existing** detectors and rules already shipped in
the engine. This table *is* the binding; the detector `type` strings in code are
the internal keys, the IDs below are the immutable public citations.

| ID | Internal key (`type`) | Human label | Book I category |
|----|-----------------------|-------------|-----------------|
| `COMP-001` | `single_bidder` | Single Bidder | competition |
| `COMP-002` | `high_value_direct_award` | High-Value Direct Award | competition |
| `COMP-003` | `missing_award_data` | Award Data Gap | competition/transparency |
| `FIN-001`  | `high_value` | High-Value Tender | value |
| `FIN-002`  | `abnormal_value` | Abnormal Value Spike | value |
| `FIN-003`  | `award_value_exceeds_tender` | Award Value Exceeds Tender | value |
| `TIME-001` | `suspicious_timing` | Award Timing Anomaly | timing |
| `TIME-002` | `award_clustering` | Rapid Repeat Procurement | timing |
| `REL-001`  | `repeat_supplier` | Repeated Winner | concentration |
| `REL-002`  | `buyer_concentration` | Buyer Concentration | concentration |
| `REL-003`  | `supplier_concentration` | Supplier Single-Buyer Dependence | concentration |
| `REL-004`  | `gst_overlap` | GST Overlap | relationship |
| `REL-005`  | `director_overlap` | Director Overlap | relationship |
| `REL-006`  | `address_overlap` | Address Overlap | relationship |
| `REL-007`  | `buyer_equals_supplier` | Buyer Equals Supplier | relationship |
| `DOC-001`  | `missing_documents` | Missing Documents | process |
| `DOC-002`  | `duplicate_description` | Tender Copy Pattern | process |
| `CTX-001`  | emergency | Emergency Procurement Context | context |
| `CTX-002`  | disaster | Disaster / Relief Context | context |
| `CTX-003`  | correction_notice | Correction / Corrigendum Context | context |
| `CTX-004`  | psu_present | PSU-Internal Procurement Context | context |

Pattern, confidence, recommendation, threshold, jurisdiction and governance IDs
are assigned in their own sections below (`PAT-*` §3, `CONF-*` §5, `REC-*` §7,
`JUR-*` §8, `THR-*` §9, `FP-*` §10, `GOV-*` §13, `ONT-*` §12).

**Reserved ranges `[ARCH]`.** Within each domain, `NNN` `001–899` is for
production rules; `900–998` is reserved for experimental/candidate rules (must
never appear in a frozen assessment); `999` is reserved for the domain's
"catch-all / manual" pseudo-rule.

### 1.4 Versioning

Rules use **two-part semantic versioning** `major.minor`, independent of the
Rulebook document version.

* **`minor`** bump — the detector's *thresholds, wording, or evidence list*
  change but its **meaning and ID are unchanged**. Old assessments remain
  interpretable. Example: tightening `TIME-001`'s suspicious-award window from 3
  to 2 days is `TIME-001@1.0 → TIME-001@1.1`.
* **`major`** bump — the detector's *detection logic or semantics* change such
  that a finding under the new version is **not comparable** to the old. Example:
  moving `FIN-002` from median+MAD to a percentile model is
  `FIN-002@1.x → FIN-002@2.0`.
* Every frozen `RiskAssessment` **must** record the rule-version set
  (`ruleset_version` + per-rule `@major.minor`) so an assessment can always be
  replayed against the exact logic that produced it. `[ARCH]`

### 1.5 Deprecation policy

A rule is **never deleted**. It transitions through a fixed lifecycle:

```
ACTIVE ──▶ DEPRECATED ──▶ RETIRED
                └──▶ SUPERSEDED-BY(<new-id>)
```

* **DEPRECATED** — still evaluated, still emitted, but flagged
  `deprecated=true` with a `deprecation_reason` and a `sunset_version`. UIs must
  visibly mark it. Minimum deprecation window: **two minor Rulebook releases**
  `[ARCH]`.
* **RETIRED** — no longer evaluated. The ID and its full history are retained in
  the registry forever so historical assessments remain resolvable. A retired ID
  is **never reissued**.
* **SUPERSEDED-BY** — a special deprecation that names the replacement ID, so
  automated migration (§13.6) can re-map historic findings.

---

## 2. Indicator Dependency Matrix (IDM)

**Principle `[ARCH]`.** Individual indicators carry a *base* severity (Book I).
Their *investigative meaning* escalates deterministically when they **co-occur on
the same entity/tender cluster**. The IDM specifies this escalation without any
arithmetic summation — escalation is expressed as a **severity band on the
ordinal lattice** `low(1) < medium(2) < high(3) < critical(4)`, matching
`_SEVERITY_ORDER` in the engine.

### 2.1 The canonical worked example, formalized

| Co-occurring indicators | Resulting severity | Rationale |
|-------------------------|--------------------|-----------|
| `COMP-001` alone | **low–medium** interpretation | Single bidder can be benign (niche market, emergency). |
| `COMP-001` + `REL-005` (single bidder **&** shared director) | **high** | Absence of competition *plus* a related-party link. |
| `COMP-001` + `REL-005` + `REL-004` (…**&** shared GST) | **critical** | Distinct-vendor fiction collapses; the "competitors" are one legal person. |

> Note the base detector `COMP-001` fires at `high` in isolation in the current
> engine; the IDM governs the **combination's** severity, which is realized as a
> `PAT-*` pattern in §3, not by mutating the base indicator. The IDM is the
> *specification*; §3 is its *executable form*.

### 2.2 Dependency semantics

Each dependency edge is a triple:

```
DEP(trigger_set → escalated_severity | scope)
```

* **`trigger_set`** — the set of indicator IDs that must **all** be present.
* **`scope`** — the join key over which co-occurrence is required. Legal scopes
  `[ARCH]`: `same_tender`, `same_buyer_supplier_pair`, `same_supplier_cluster`
  (entities resolved to one canonical company), `same_award`. Co-occurrence
  across *unrelated* records is **not** a dependency and must not escalate.
* **`escalated_severity`** — the ceiling severity for the combination, on the
  ordinal lattice.

### 2.3 Deterministic dependency table (v1.0)

| DEP ID | Trigger set | Scope | Escalation |
|--------|-------------|-------|------------|
| `DEP-01` | `COMP-001` + `REL-004` | supplier_cluster | → **critical** |
| `DEP-02` | `REL-005` + `REL-006` + `REL-004` | supplier_cluster | → **critical** |
| `DEP-03` | `COMP-001` + `REL-001` + `REL-002` | same_buyer_supplier_pair | → **critical** |
| `DEP-04` | `REL-001` + `REL-003` | same_buyer_supplier_pair | → **high** |
| `DEP-05` | `TIME-002` + `REL-001` | same_supplier_cluster | → **high** |
| `DEP-06` | `FIN-002` + `FIN-003` | same_award | → **high** |
| `DEP-07` | `COMP-001` + `REL-002` | same_buyer | → **medium** |
| `DEP-08` | `TIME-001` (no `CTX-003`) | same_tender | → **critical** |
| `DEP-09` | `REL-007` (no `CTX-004`) | same_award | → **critical** |

Each `DEP-*` maps 1:1 onto a `PAT-*` rule in §3, which is where it executes.
The IDM exists so that the *reasoning* ("why did two mediums become a critical?")
is documented independently of the code that runs it.

### 2.4 Non-escalation guarantees (false-positive protection)

`[ARCH]` The IDM **only escalates**; it never invents. Three hard invariants:

1. **No cross-scope leakage.** Two indicators on different tenders with no shared
   entity never combine.
2. **Evidence gate precedes escalation.** If any indicator in a `trigger_set`
   has `evidence_status = unknown`, the combination cannot exceed **medium**
   (mirrors the engine's evidence cap: unknown evidence with severity > medium is
   capped to medium).
3. **Context can veto.** A `CTX-*` modifier listed as an exception (e.g.
   `CTX-003` on `DEP-08`, `CTX-004` on `DEP-09`) suppresses the escalation to a
   reviewable, non-critical band.

---

## 3. Pattern Interaction Matrix (PIM)

Patterns are the executable form of §2. A pattern is a **named deterministic
rule combination** (`RiskPattern`), *never* an arithmetic sum. Overall severity
is `max(pattern severities)`, else `max(indicator severities)` — exactly as the
engine's `_classify` / `assess_risk_v2` compute it.

### 3.1 Pattern definition contract

Every pattern **must** declare all six fields:

| Field | Meaning |
|-------|---------|
| `id` / `name` | Immutable `PAT-*` ID and human label |
| `required_indicators` | IDs that must **all** be present (AND) |
| `optional_indicators` | IDs that, if present, strengthen the narrative but are not required |
| `minimum_evidence` | The weakest `evidence_status` that still lets the pattern hold its severity |
| `confidence_adjustment` | How the pattern shifts the *narrative* confidence (never the risk score) |
| `severity` / `recommendation` | Ceiling severity and the bound `REC-*` action |

### 3.2 Canonical pattern catalogue (frozen, mapped to shipped rules)

| ID | Pattern (name) | Required | Optional | Min evidence | Severity | Recommendation |
|----|----------------|----------|----------|--------------|----------|----------------|
| `PAT-001` | Systemic Competition-Suppression | `COMP-001` + `REL-001` + `REL-002` | `COMP-003`, `DOC-002` | probable | critical | `REC-COMP` |
| `PAT-002` | Vendor Lock-in | `REL-001` + `REL-003` | `FIN-001`, `DOC-002` | probable | high | `REC-LOCKIN` |
| `PAT-003` | Related-Party (Critical) | `REL-005` + `REL-006` + `REL-004` | `REL-007` | probable | critical | `REC-REL` |
| `PAT-004` | Related-Party via Single Bidder | `COMP-001` + `REL-004` | `REL-005` | probable | critical | `REC-REL` |
| `PAT-005` | Award-Timing | `TIME-001` | `COMP-001` | verified¹ | critical | `REC-TIME` |
| `PAT-006` | Buyer-Supplier Identity | `REL-007` | — | verified | critical | `REC-REL` |
| `PAT-007` | Rapid Repeat Procurement | `TIME-002` + `REL-001` | `FIN-002` | probable | high | `REC-LOCKIN` |
| `PAT-008` | Financial Manipulation | `FIN-002` + `FIN-003` | `FIN-001` | probable | high | `REC-FIN` |
| `PAT-009` | Concentration | `COMP-001` + `REL-002` | `REL-003` | probable | medium | `REC-CONC` |
| `PAT-010` | Document Integrity | `DOC-002` | `DOC-001`, `COMP-003` | probable | medium | `REC-DOC` |
| `PAT-011` | Transparency Gap | `COMP-003` + `DOC-001` | — | probable | medium | `REC-DOC` |

¹ `PAT-005` holds **critical** only absent `CTX-003` (correction notice); with a
corrigendum present it is banded down to reviewable (mirrors `_apply_context`).

> **Bid Rotation** is intentionally listed as a **candidate** pattern
> (`PAT-9xx`, experimental range) and is **not** frozen in v1.0: robust rotation
> detection requires a multi-tender temporal sequence model and losing-bidder
> data that the current package schema does not guarantee. Emitting it now would
> manufacture false positives, violating First Principle 4. It is specified for a
> future major release under §13. `[ARCH]`

### 3.3 Pattern evaluation order

`[ARCH]` Patterns are evaluated **strongest-first** (critical → medium), and
**all** matching patterns are emitted (a package can exhibit several). Overall
severity is the **maximum** pattern severity — never a count, never a sum.
This preserves the invariant that adding more evidence can only *raise or hold*
severity, never dilute it (the failure mode of averaged/additive scoring).

### 3.4 Confidence adjustment rule

A pattern's `confidence_adjustment` acts **only** on the *narrative* confidence
band shown to the analyst, and only *downward* when `minimum_evidence` is not
met. It can **never** raise the §5 confidence score, which is computed
independently from evidence quality. This firewall (risk ⟂ confidence) is
constitutional.

---

## 4. Mathematical Risk Model (MRM)

**This section formalizes the model the engine already implements; it does not
introduce weighted summation.** SENTRY deliberately uses an **ordinal
severity-lattice (max-plus) model**, *not* an additive score, because additive
scoring dilutes a single critical signal among many weak ones and is not legally
defensible ("why is 0.62 the threshold?"). The lattice model is explainable to a
court: *"the award severity equals the strongest proven pattern."*

### 4.1 Domains

Let the ordinal severity lattice be

```
S = { low, medium, high, critical },   rank: low=1, medium=2, high=3, critical=4
```

with the display score map (from `_SEVERITY_SCORE`, canonical):

```
σ(low)=25   σ(medium)=50   σ(high)=72   σ(critical)=92
```

`σ` is a **presentation projection only** (0–100 for UI/API). It is *not* summed.

### 4.2 Layered pipeline (matches L1–L6)

For a package `P`:

```
1. Detect        I  = { (id, base_sev(id)) : detector fires on P }         (L1)
2. Contextualize sev'(id) = clamp₁₄( rank(base_sev(id)) + Δctx(id, P) )     (L2)
3. Validate      e(id) ∈ {verified, probable, unknown}                     (L3)
                 sev''(id) = cap(sev'(id), e(id))
4. Classify      Π = { pat ∈ PIM : required(pat) ⊆ present(I) }            (L4)
5. Aggregate     overall_sev = max_rank( { sev(pat) : pat ∈ Π }
                                       ∪ { sev''(id) : id ∈ I } )
6. Project       overall_score = σ(overall_sev)
```

### 4.3 The five formal operators

**(a) Indicator severity.** Base severity is a constant per rule (Book I /
registry). No arithmetic.

**(b) Context modifier `Δctx` (band shift).** A context rule shifts an
indicator's rank by an integer, clamped to `[1,4]`:

```
clamp₁₄(x) = min(4, max(1, x))
Δctx ∈ { -1, 0, +1 }   per (indicator, context) rule
```

Realized exactly by `_band_up` / `_band_down`. Examples (from `_apply_context`):
`CTX-001` on `COMP-001/COMP-002` ⇒ `Δ = -1`; `CTX-002` on `TIME-001` ⇒ `Δ = -1`;
`TIME-001` with **no** `CTX-003` ⇒ pinned to `critical`.

**(c) Evidence strength cap.** Evidence can only **lower** a severity, never
raise it:

```
cap(sev, unknown)  = min_rank(sev, medium)     # unknown ⇒ ≤ medium
cap(sev, probable) = sev
cap(sev, verified) = sev
```

This is the engine's rule: *"Unknown evidence caps severity — an unverifiable
indicator cannot be critical."*

**(d) Pattern multiplier — replaced by lattice join.** There is **no numeric
multiplier**. A pattern contributes its own declared severity to the `max`. This
is the "multiplier" in spirit (a combination outranks its parts) without the
non-defensibility of a magic number.

**(e) Confidence penalty.** Confidence (§5) is computed **separately** and
**never** modifies `overall_score`. The only coupling permitted is
presentational: a low-confidence critical is rendered as *"critical (low
confidence — preliminary)"*.

### 4.4 Bounds & normalization

* **Maximum score** = `σ(critical) = 92`. There is deliberately **no 100**: a
  deterministic oversight signal is never "100% certain fraud". `[ARCH]`
* **Minimum non-empty score** = `σ(low) = 25`.
* **Insufficient** = a distinct terminal state (`overall_severity =
  "insufficient"`, `score = 0`) when `P` has zero records — *never* rendered as
  "low risk", because absence of evidence is not evidence of integrity.
* **Normalization** for cross-jurisdiction comparison uses the **rank**, not
  `σ`: report `rank/4`. `σ` values are for a single UI and are not comparable
  across differently-configured thresholds.

### 4.5 Determinism obligations

`[ARCH]` The scoring path must contain: no floating-point accumulation of
severities (only integer rank arithmetic), no `random`, no wall-clock, no
network, no LLM. `Decimal` is used for all monetary math (as in the detectors)
to avoid float drift. Any violation is a `GOV-*` release blocker (§13.8).

---

## 5. Mathematical Confidence Model (MCM)

Confidence answers a *different* question from risk: **"how much do we trust
that we have enough good evidence to make any claim at all?"** It is a weighted
mean of independent, bounded dimensions, each in `[0,1]`. It is **orthogonal to
risk** (First Principles / §4.3e).

### 5.1 Formula

```
Confidence(P) = Σ_d  w_d · x_d(P) ,      Σ_d w_d = 1 ,   x_d ∈ [0,1]
```

### 5.2 The ten dimensions, weights, and rationale

| ID | Dimension | `w` | `x_d` measurement | Why this weight |
|----|-----------|-----|-------------------|-----------------|
| `CONF-001` | Evidence Coverage | **0.18** | fraction of records with a resolvable source URL/document | Highest weight: nothing else matters if the underlying records aren't verifiable. Implemented today as `with_url/n`, `with_docs/n`. |
| `CONF-002` | Source Reliability | **0.14** | mean tier-weight of contributing sources (official portal > aggregator > scraped) | A finding is only as trustworthy as its weakest cited source. |
| `CONF-003` | Cross-Source Agreement | **0.12** | fraction of key facts corroborated by ≥2 independent sources | Independent corroboration is the strongest defense against single-source error. `[BP]` |
| `CONF-004` | Entity Resolution | **0.14** | fraction of canonical companies with resolution confidence ≥ 0.6 | Related-party logic is worthless on mis-resolved entities; ties with source reliability. Implemented as `resolved_ok/canonical`. |
| `CONF-005` | Grounding | **0.10** | fraction of findings whose citations resolve to real records (grounding guard pass rate) | Guards against LLM/narrative drift; a fact must trace to a record. |
| `CONF-006` | Timeline Completeness | **0.08** | fraction of records with a usable published/closing date | Timing indicators are void without dates. Implemented as `dated/n`. |
| `CONF-007` | Award Completeness | **0.10** | fraction of closed tenders with award data | Competition/concentration logic depends on award records. Implemented as `with_awards/n`. |
| `CONF-008` | Document Integrity | **0.06** | fraction of tenders with attached procurement documents | Documents raise a finding from *probable* to *verified*. |
| `CONF-009` | Relationship Density | **0.04** | availability of director/GST/address attributes on the entities in scope | Low weight: rich for `REL-*`, irrelevant for `FIN-*`; kept small so its absence doesn't unfairly sink confidence. |
| `CONF-010` | Graph Completeness | **0.04** | fraction of expected buyer↔supplier↔document edges actually materialized | Forward-looking (ontology, §12); low weight until the graph is fully populated. |

Weights sum to **1.00**. The **five bold-implemented** dimensions
(`CONF-001,004,006,007` and coverage) are exactly the ones the shipped
`_confidence()` averages today (`with_url`, `with_docs`, `with_awards`, `dated`,
entity-resolution) — this section **specifies the target v1.0 model** and the
remaining five dimensions are the ratified backlog for implementation under §13,
not a rewrite of what exists.

### 5.3 Level bands (canonical, from the engine)

```
high     : score ≥ 0.70
moderate : 0.45 ≤ score < 0.70
low      : 0.25 ≤ score < 0.45
very_low : score < 0.25
```

### 5.4 Interaction with per-indicator confidence

Each indicator also carries a local confidence seeded by evidence status
(`verified=0.8`, `probable=0.6`, `unknown=0.3` in the engine). These are
**inputs** to `CONF-005/008`, not substitutes for the package-level model. The
**headline confidence is the single MCM number** — no second, divergent
confidence may override it (the engine explicitly enforces this: the weighted
integrity model and analyst-report confidence are *breakdowns*, never the
verdict).

### 5.5 Weight-change governance

`[ARCH]` The weight vector is itself a versioned rule (`CONF-000@major.minor`).
Any weight change is a **minor** release requiring the §13 review and a
back-test showing the level-band distribution shift on the regression corpus.

---

## 6. Explainability Tree (XT)

**Constitutional guarantee:** *every* score traces, mechanically, from the
headline number down to a source record. If any node in the chain is missing,
the finding is not emittable. This is the `RiskExplainabilityNode` contract made
normative.

### 6.1 The mandatory chain

```
Overall Severity/Score
   └─▶ Pattern            (PAT-*: which rule combination fired, and its rule text)
         └─▶ Indicators   (COMP/FIN/TIME/REL/DOC-*: base_severity → context → final)
               └─▶ Evidence   (verified | probable | unknown, + the applied caps)
                     └─▶ Documents   (attached procurement docs / award notices)
                           └─▶ Source   (source_name, source_url, ingest lineage)
```

### 6.2 Per-node required fields (`EXP-001` contract)

Each node **must** carry: `indicator_id`, `name`, `base_severity`, `base_score`,
`rule_triggered`, `evidence[]` (concrete `RiskEvidenceRef`s), `evidence_status`,
`context_applied[]` (the exact `CTX-*` notes), `score_contribution`,
`final_severity`, and `reason`. This is precisely the shipped
`RiskExplainabilityNode`; §6 freezes it as the audit contract.

### 6.3 Invariants

1. **No orphan scores `[ARCH]`.** `overall_score = σ(overall_severity)` and
   `overall_severity = max(...)` over nodes that each terminate at ≥1
   `RiskEvidenceRef`. A score with no backing node is a release blocker.
2. **Context transparency.** Every band shift (`Δctx`) and every evidence cap
   must appear as a human-readable line in `context_applied` — the analyst sees
   *why* a critical was reduced to medium.
3. **LLM is read-only over the tree.** The narrator converts nodes to prose and
   may not add, drop, or reweight a node. The grounding guard rejects any
   narrative asserting a quantity absent from the tree.
4. **Replayability.** Given the tree + the rule-version set, the headline score
   is recomputable by hand. `[BP]` (auditability)

---

## 7. Recommendation Matrix (RM)

**Constitutional rule:** LLMs never invent recommendations. Every recommendation
is a **deterministic function of which patterns/indicators fired**, is
**evidence-backed**, and points to a **verifiable next investigative action** —
not a conclusion.

### 7.1 Recommendation contract

```
REC(trigger → ordered_actions[] , evidence_requirement , stop_condition)
```

* `trigger` — a `PAT-*` or indicator ID set.
* `ordered_actions` — the investigator workflow, in sequence.
* `evidence_requirement` — the record type each action must attach.
* `stop_condition` — the benign explanation that closes the thread (ties to §10).

### 7.2 Canonical recommendation catalogue

| ID | Trigger | Ordered actions | Evidence to attach |
|----|---------|-----------------|--------------------|
| `REC-REL` | `REL-005` / `PAT-003/004/006` | 1) Pull each supplier's DIN → 2) Inspect MCA filings → 3) Compare directors & shareholding → 4) Compare registered addresses & GSTIN | MCA master data, DIN records, GST registration `[IN]` |
| `REC-COMP` | `PAT-001` / `COMP-001` | 1) Read tender eligibility clauses for restrictive criteria → 2) Compare with comparable tenders → 3) Check corrigendum history → 4) Identify excluded/absent bidders | Tender document, comparable tenders, corrigenda |
| `REC-LOCKIN` | `PAT-002/007` | 1) Timeline the buyer↔supplier award history → 2) Benchmark share vs peer buyers → 3) Test for renewal-without-retender | Award history, peer-buyer awards |
| `REC-FIN` | `PAT-008` / `FIN-002/003` | 1) Recompute value vs estimate & vs median → 2) Obtain BoQ / rate justification → 3) Check for scope-creep amendments | Award value, estimate, BoQ, amendments |
| `REC-TIME` | `PAT-005` / `TIME-001/002` | 1) Reconstruct publish→close→award timeline → 2) Verify statutory minimum tender window for the method → 3) Check for a corrigendum explaining compression | Dated notices, corrigenda, method rule (`JUR-*`) |
| `REC-CONC` | `PAT-009` / `REL-002/003` | 1) Compute the concentration share → 2) Establish the relevant market → 3) Test genuine-shortage vs preferential allocation | Award shares, market comparators |
| `REC-DOC` | `PAT-010/011` / `DOC-*` / `COMP-003` | 1) Request missing award notices / documents → 2) Re-run detection once obtained → 3) Do not conclude on the gap alone | Source portal record requests |

### 7.3 Guarantees

1. **Evidence-first `[BP]`.** No recommendation asserts wrongdoing; each asks
   the investigator to *fetch a specific record*. The shipped
   `_recommendations()` already emits exactly this style ("Cross-check … against
   director and ownership records", "Request the missing award notices …").
2. **Deterministic mapping.** Same fired-set ⇒ same recommendation set, ordered
   identically.
3. **Fallbacks are bounded.** When high/critical risk fires but no specific
   `REC-*` matches, emit exactly one escalation action; when nothing fires, emit
   exactly one "widen coverage" action (as the engine does).

---

## 8. Jurisdiction Rules (JR)

**Principle `[ARCH]`.** No India-only value may be hardcoded in a detector.
Every legally-defined number lives in a **jurisdiction profile** (`JUR-*`)
loaded at assessment time. Detectors read parameters; they do not embed law.

### 8.1 Jurisdiction profile schema

A `JUR-<code>` profile declares five independent blocks so that changing a
country never touches detector code:

| Block | Contents (all values are `THR-*` parameters, §9) |
|-------|--------------------------------------------------|
| **Legal thresholds** | value bands that trigger higher oversight, direct-award ceilings, approval tiers |
| **Tender windows** | statutory minimum publish→close days *per procurement method* |
| **Emergency rules** | what qualifies as emergency, and which indicators `CTX-001/002` may suppress |
| **Framework agreements** | call-off vs new-tender semantics; expected single-supplier behavior |
| **Procurement methods** | the legal method taxonomy (open / limited / single-source / framework / e-reverse-auction) and each method's expectations |

### 8.2 Registered profiles (v1.0)

| ID | Jurisdiction | Notes |
|----|--------------|-------|
| `JUR-IN` | India | `[IN]` GFR 2017 / CVC guidance / GeM & CPPP conventions; MCA-DIN & GSTIN power `REL-*`. Values are **operator-configured**, not asserted by this Book. |
| `JUR-WB` | World Bank | `[INTL]` World Bank Procurement Framework (open competition, prior/post review thresholds are Bank-set). |
| `JUR-ADB` | Asian Development Bank | `[INTL]` ADB Procurement Policy. |
| `JUR-UN` | UN Procurement | `[INTL]` UN Procurement Manual conventions. |
| `JUR-UNCITRAL` | UNCITRAL Model Law baseline | `[INTL]` Neutral default for jurisdictions without a bespoke profile. |
| `JUR-DEFAULT` | Neutral fallback | `[ARCH]` Conservative windows; suppresses jurisdiction-specific patterns rather than risk false positives. |

### 8.3 Rules of jurisdiction resolution

1. A package declares its jurisdiction (or inherits it from the source
   connector). Missing ⇒ `JUR-DEFAULT`. `[ARCH]`
2. **We never invent a legal threshold.** If a profile lacks a value, the
   dependent detector runs in *evidence-only* mode (structural signal, no
   legal-band interpretation) and the confidence for that finding is reduced,
   not fabricated.
3. Cross-jurisdiction aggregation compares **ranks** (§4.4), never raw `σ` or
   raw currency.
4. Adding a country = adding a `JUR-*` profile + `THR-*` values. **Zero detector
   code changes.** This is the extensibility test for §13 sign-off.

---

## 9. Procurement Threshold Library (PTL)

Every numeric limit is a **named, versioned, jurisdiction-scoped parameter**
(`THR-*`). Detectors reference `THR-*` by ID; they never contain literals. The
current engine constants below are the **`JUR-DEFAULT` / India-dev defaults**
and are explicitly marked as operator-overridable.

### 9.1 Parameter registry (defaults = shipped constants)

| ID | Parameter | Default (source) | Scope | Consumed by |
|----|-----------|------------------|-------|-------------|
| `THR-HV-001` | High-value band | `100,000,000` INR (`_HIGH_VALUE`, 10 cr) | per `JUR` | `FIN-001`, `COMP-002` |
| `THR-BID-001` | Minimum competitive bidders | `2` (single-bidder ⇒ `<2`) | per `JUR`×method | `COMP-001` |
| `THR-TIME-001` | Suspicious award-after-publish window | `3` days (`_SUSPICIOUS_AWARD_DAYS`) | per `JUR`×method | `TIME-001` |
| `THR-TIME-002` | Award-clustering window | `30` days (`_CLUSTER_WINDOW_DAYS`) | per `JUR` | `TIME-002` |
| `THR-TIME-003` | Min awards to call a cluster | `3` | per `JUR` | `TIME-002` |
| `THR-CONC-001` | High concentration share | `0.50` (`_CONCENTRATION_HIGH`) | per `JUR` | `REL-002`, `REL-003` |
| `THR-CONC-002` | Critical concentration share | `0.70` | per `JUR` | `REL-002` |
| `THR-VAL-001` | Value-spike outlier threshold | modified-z `3.5` | global (statistical) | `FIN-002` |
| `THR-VAL-002` | Severe value-spike threshold | modified-z `6.0` | global | `FIN-002` |
| `THR-VAL-003` | Min sample for outlier test | `5` (`_MIN_ABNORMAL_SAMPLE`) | global | `FIN-002` |
| `THR-VAL-004` | Award-exceeds-estimate multiple | `2.0×` | per `JUR` | `FIN-003` |
| `THR-FW-001` | Framework call-off exemption | method-flag (bool) | per `JUR` | §10 `FP-*` |
| `THR-EMG-001` | Emergency-language lexicon | term list (`_EMERGENCY_TERMS`) | per `JUR` | `CTX-001` |

### 9.2 Configuration rules

1. **Everything configurable `[ARCH]`.** Each `THR-*` is overridable per
   jurisdiction and per procurement method; defaults are conservative.
2. **Statistical vs legal thresholds are separated.** `THR-VAL-*` are
   *statistical* (median/MAD, jurisdiction-independent) and must **not** be
   presented as legal limits. `THR-HV/BID/TIME` are *legal/method* and must come
   from a `JUR-*` profile.
3. **Changing a threshold is a versioned rule change** (§1.4 minor) and triggers
   a §13 back-test. A threshold change that alters ≥X% of regression outcomes is
   escalated to full review. `[ARCH]`
4. **No silent literals.** A grep-level `GOV` test (§13.8) fails the build if a
   detector contains a bare numeric limit not sourced from `THR-*`.

---

## 10. False-Positive Framework (FPF)

**Constitutional rule (the most important in this Book):** *We never suppress an
indicator. We only reduce its interpretation severity, with a stated,
evidence-backed reason.* The raw indicator remains visible and auditable; only
its **band** and **narrative** soften. This is exactly the engine's Layer-2
behavior (`_apply_context` band-shifts and annotates; it never deletes).

### 10.1 The suppression contract

```
FP(context → { indicators_affected , max_reduction , required_evidence , note })
```

* `max_reduction` — capped at **one band** per context rule (composable to at
  most the floor of `medium` for structural signals; never to zero).
* `required_evidence` — the benign explanation must itself be grounded (an
  emergency claim needs emergency language/flag on the record).
* `note` — the exact human-readable reason, surfaced in `context_applied`.

### 10.2 Benign-context catalogue

| FP ID | Benign context | Indicators softened | Reduction | Required evidence |
|-------|----------------|---------------------|-----------|-------------------|
| `FP-01` | Emergency procurement `[BP]` | `COMP-001`, `COMP-002` | −1 band | `CTX-001` terms / emergency flag |
| `FP-02` | Disaster / relief `[BP]` | `TIME-001`, short-window | −1 band | `CTX-002` terms |
| `FP-03` | Correction / corrigendum | `TIME-001` | −1 band (off critical-pin) | `CTX-003` notice present |
| `FP-04` | PSU-internal procurement `[IN]` | `REL-007` (buyer≡supplier) | → medium (review, not adverse) | `CTX-004` buyer is a PSU |
| `FP-05` | Framework agreement call-off `[INTL]` | `COMP-001`, `REL-001` | −1 band | `THR-FW-001` method flag |
| `FP-06` | Rate contract / DGS&D-style panel `[IN]` | `REL-001`, `REL-003` | −1 band | rate-contract method flag |
| `FP-07` | Nomination basis (legally permitted single-source) `[INTL]` | `COMP-001`, `COMP-002` | −1 band | single-source method + justification doc |
| `FP-08` | Strategic / national-security procurement | `COMP-*`, `TIME-*` | −1 band **+ manual-review lock** | classified/strategic flag |

### 10.3 Hard invariants

1. **Indicator persistence.** The suppressed indicator is still emitted with its
   `base_severity` recorded; only `final_severity` moves. An auditor can always
   see what was softened and why. `[ARCH]`
2. **One-band floor.** No stack of contexts can erase a signal — a critical can
   fall to high/medium, never to nothing. This protects against
   "explain-away" abuse.
3. **National-security & strategic contexts never auto-clear.** `FP-08` reduces
   the band **but forces manual review** — the platform must not silently
   greenlight a sensitive procurement.
4. **Suppression is evidence-gated.** If the benign context itself is
   unverifiable, the reduction does not apply (symmetry with §2.4).

---

## 11. Investigation Playbooks

Each major pattern ships an **investigator workflow**: the deterministic,
repeatable sequence an analyst follows to move a *signal* toward a *finding*.
Playbooks are the human-facing companion to §7's `REC-*`. Common spine `[BP]`:

```
Evidence collection → Verification → Cross-check → Documents → Next investigation
```

### 11.1 Conflict of Interest / Related Party (`PAT-003/004/006`)

1. **Collect** — every supplier's DIN, GSTIN, registered address, directors.
2. **Verify** — pull MCA master data & DIN filings; confirm the overlap is a
   true shared legal person, not a namesake. `[IN]`
3. **Cross-check** — shareholding, common signatories, shared bank/contact.
4. **Documents** — incorporation docs, GST registration, award letters.
5. **Next** — investigate each linked director/company as a fresh subject.
6. **Stop condition** — overlap disproven (distinct DIN/GSTIN) ⇒ downgrade per §10.

### 11.2 Vendor Lock-in (`PAT-002/007`)

Collect the full buyer↔supplier award history → verify each award is a real
retender (not an auto-renewal) → benchmark the supplier's share against peer
buyers → documents: contracts, renewal notes → next: audit the specification
authorship for supplier fingerprints. **Stop:** genuine market monopoly proven.

### 11.3 Bid Rotation *(candidate — not frozen v1.0)*

Specified for a future major release (§3.2): requires losing-bidder identities
and a multi-tender sequence model. Until the schema guarantees that data, this
playbook runs in **manual-only** mode and emits no automated pattern. `[ARCH]`

### 11.4 Financial Anomalies (`PAT-008`, `FIN-*`)

Recompute value vs estimate and vs package median → verify against BoQ / rate
justification → cross-check for scope-creep amendments inflating value →
documents: award value, estimate, BoQ, change orders → next: compare unit rates
across the buyer's portfolio. **Stop:** documented, justified rate variance.

### 11.5 Timeline Manipulation (`PAT-005`, `TIME-*`)

Reconstruct publish→close→award timeline → verify against the statutory minimum
window for the method (`JUR-*`) → cross-check corrigendum history → documents:
dated notices → next: examine other tenders by the same buyer for the same
compression. **Stop:** corrigendum or lawful expedited method explains it.

### 11.6 Related Parties (concentration) (`PAT-009`, `REL-002/003`)

Compute concentration share → establish the relevant market → verify whether
scarcity is genuine → documents: award shares, comparators → next: investigate
the dominant counterparty. **Stop:** genuine sole-capable-supplier market.

### 11.7 Transparency Gaps (`PAT-011`, `COMP-003`, `DOC-001`)

Enumerate closed-without-award and document-less tenders → request the missing
records from the source portal → **do not conclude on the gap alone** → re-run
detection once obtained. **Stop:** records supplied and clean.

### 11.8 Document Manipulation (`PAT-010`, `DOC-002`)

Cluster near-identical specifications → verify the reuse spans distinct
buyers/tenders (not lawful templating) → cross-check authorship metadata →
documents: the duplicated specs → next: check whether the same supplier won the
duplicated set. **Stop:** lawful standard-template use proven.

> Every playbook **ends in a verifiable action or a stop condition** — never in
> an allegation. This is the operational face of the oversight mandate. `[BP]`

---

## 12. Ontology Mapping

**Scope guard:** this section does **not** design the ontology. It only fixes the
**binding contract** so every rule remains compatible with a future entity graph.
Each rule declares which ontology entities its evidence attaches to (`ONT-*`).

### 12.1 Entity binding table

| Rule family | Binds to ontology entities |
|-------------|----------------------------|
| `COMP-*` | Tender, Award, Buyer, Supplier |
| `FIN-*`  | Tender, Award, Supplier |
| `TIME-*` | Tender, Award, (dated) Event |
| `REL-*`  | Supplier, Company, Director, GSTIN, Address, Buyer |
| `DOC-*`  | Tender, Document |
| `PAT-*`  | Pattern → (its constituent Indicators → their entities) |
| `REC-*`  | Recommendation → Evidence → Document → Source |
| `CTX-*`  | Context → Tender/Buyer attributes |

### 12.2 Binding invariants

1. **Every indicator resolves to ≥1 first-class entity.** A signal that cannot
   name its Tender/Award/Supplier is not emittable (aligns with §6.3.1). `[ARCH]`
2. **Evidence is an edge, not a node property.** Each `RiskEvidenceRef`
   (kind ∈ {tender, award, document, entity, buyer, supplier}) is a typed edge
   to a source-backed node, preserving provenance in the future graph.
3. **Stable keys.** Ontology join keys (DIN, GSTIN, tender reference,
   canonical-company ID) are the same keys the IDM (§2) uses for scope — so the
   graph and the dependency matrix agree by construction.
4. **Forward compatibility only.** No rule may depend on an ontology feature not
   yet built; `CONF-010` (Graph Completeness) measures the gap so confidence
   honestly reflects it.

---

## 13. Engineering Governance

The rules by which rules change. `GOV-*` clauses are themselves versioned.

### 13.1 Rule lifecycle (`GOV-001`)

```
DRAFT → CANDIDATE (900-range, shadow-only) → ACTIVE → DEPRECATED → RETIRED
```

A candidate rule runs in **shadow mode** (computed, logged, never surfaced in a
frozen assessment) for at least one release before promotion. `[ARCH]`

### 13.2 Approval process (`GOV-002`)

A new/changed rule requires: (a) a written spec entry in this Book, (b) a
deterministic reference implementation, (c) a regression back-test, (d) sign-off
from **two** roles — an **engineer** and a **procurement/domain reviewer**. Legal
threshold changes additionally require a **jurisdiction owner** sign-off.

### 13.3 Version control (`GOV-003`)

Rulebook version (`vMAJOR.MINOR`) is distinct from per-rule versions (§1.4).
Every frozen assessment persists `{rulebook_version, ruleset_version,
per-rule @versions, JUR profile version, THR snapshot}` so it is exactly
replayable. `[BP]`

### 13.4 Rule review (`GOV-004`)

Every active rule is **re-reviewed at least annually** against: false-positive
rate on the regression corpus, investigator feedback, and any jurisdiction legal
change. Findings feed §13.1 transitions.

### 13.5 Backward compatibility (`GOV-005`)

* A **minor** rule change must keep historic assessments *interpretable*
  (same ID, comparable meaning).
* A **major** change must ship a **migration note** (§13.6) and must not
  silently re-score historic assessments — old assessments are immutable
  records of what the engine concluded *at the time*.

### 13.6 Migration policy (`GOV-006`)

On a `major` change or `SUPERSEDED-BY`, ship a migration mapping
(`old-id@ver → new-id@ver`) and a one-way re-classification script. Migrations
are **append-only**: they produce a *new* assessment version; they never mutate a
frozen one. `[ARCH]`

### 13.7 Deprecation policy (`GOV-007`)

Per §1.5: minimum two-minor-release deprecation window, visible flagging,
IDs never reused, full history retained forever.

### 13.8 Testing requirements (`GOV-008`) — release blockers

A build **fails** (cannot freeze) if any hold:

1. **Determinism test** — same package hashed twice ⇒ identical assessment
   (no `random`/clock/network/float-accumulation in the scoring path).
2. **No-orphan-score test** — every headline score traces to ≥1
   `RiskEvidenceRef` via a full XT chain (§6.3.1).
3. **No-literal-threshold test** — no detector contains a bare numeric limit not
   sourced from a `THR-*` parameter (§9.2.4).
4. **Evidence-cap test** — an `unknown`-evidence indicator can never be emitted
   above `medium` (§4.3c).
5. **Suppression-floor test** — no `FP-*` stack reduces a signal below its
   one-band floor or removes it (§10.3.2).
6. **Grounding-guard test** — the narrator cannot introduce a quantity absent
   from the XT; violations fall back to the deterministic composer.
7. **Regression-corpus test** — golden packages produce their pinned
   assessments; any diff requires a signed rationale (§13.2).
8. **ID-immutability test** — no previously-issued ID changes meaning or
   disappears from the registry.

---

## Expert Addenda (beyond the requested sections)

Ratified during final review because a decade-scale, court-facing platform is
incomplete without them.

### A. Temporal integrity of rules (`GOV-009`) `[ARCH]`

An assessment is always evaluated with the **ruleset that was active at ingest /
assessment time**, and that pin is stored. Re-running an old case with new rules
produces a *new, separately-versioned* assessment — the original is never
overwritten. This is the difference between "what we knew then" and "what we
would conclude now," and it is decisive for legal defensibility.

### B. Data-quality preconditions (`GOV-010`) `[BP]`

A detector must declare its **minimum viable data** (e.g. `FIN-002` needs
`THR-VAL-003` = 5 award values; `TIME-002` needs ≥3 dated awards). Below the
minimum it emits **nothing** rather than a weak guess — encoded already in the
detectors and hereby made a governance obligation, not an implementation detail.

### C. Adversarial-robustness note (`GOV-011`) `[ARCH]`

Because gaming procurement disclosures is itself a red flag, detectors must be
**evasion-aware**: normalize entity names before comparison (the engine's
`casefold`/fingerprint steps), treat *missing* data as a signal to investigate
(`COMP-003`, `DOC-001`) rather than as "clean", and never let absence of a field
*raise* confidence.

### D. Human-in-the-loop supremacy (`GOV-012`) `[BP]`

No SENTRY output is a determination. Every assessment carries
`OVERSIGHT_DISCLAIMER` and terminates each finding in `REVIEW_NOTE`. The engine
may *rank* investigator attention; it may never *replace* investigator judgment.
`FP-08` (strategic/national-security) additionally forces manual review.

### E. Privacy, proportionality & bias (`GOV-013`) `[BP]` / `[INTL]`

Related-party detection touches personal identifiers (directors, addresses).
Their use is confined to the **stated oversight purpose**, logged, and
proportionate. Detectors must be periodically tested for structural bias against
small/new suppliers (a first-time single bidder is not inherently suspect —
which is *why* `COMP-001` alone is not critical and only escalates under §2/§3).

### F. Ratification checklist for freezing v1.0

- [ ] Every §1.3 ID bound to a shipped detector, immutable.
- [ ] §3 patterns match `_PATTERN_RULES`; Bid Rotation held as candidate.
- [ ] §4 operators match `_SEVERITY_SCORE`, `_band_up/down`, evidence cap.
- [ ] §5 five implemented dimensions match `_confidence()`; five specified for backlog.
- [ ] §9 `THR-*` defaults match engine constants; no bare literals remain.
- [ ] §13.8 release-blocker suite green on the regression corpus.

*End of Book II. This Book, once frozen, is versioned and amended only under §13.*
```
