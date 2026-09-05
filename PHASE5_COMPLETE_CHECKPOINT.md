# SENTRY — Phase 5 Complete Checkpoint

**Phase:** 5 — Evidence Verification & Reasoning 2.0  
**Status:** COMPLETE (implementation checkpoint)  
**Repository:** `prince-sankhla/sentry`  
**Branch:** `main`

## Delivered

### 1. Deterministic integrity screening
The investigation pipeline carries the deterministic Risk Engine V2 assessment as the authoritative integrity-screening output. It separates indicator detection, context interpretation, evidence validation, named pattern classification, confidence, and explainability rather than using an opaque aggregate score.

### 2. Current data-supported indicator catalogue
The Phase 5 registry includes the currently executable / package-supported signals:

- high-value direct award
- high-value tender
- repeated supplier
- buyer concentration
- supplier single-buyer dependence
- abnormal value
- rapid repeat procurement / award clustering
- award timing anomaly
- tender copy / duplicate-description pattern
- missing award data
- award value materially above tender estimate
- buyer equals supplier
- missing procurement documents
- potential contract fragmentation

The registry also declares bidder/entity-overlap indicators where the underlying data may become available later.

### 3. Evidence and provenance contract
Each V2 indicator carries a stable identifier, human-readable name, base and final severity, deterministic score, evidence status, independent confidence, supporting record references, required evidence, deterministic context notes, and mandatory investigator-review status.

Missing evidence never becomes a positive finding. Unsupported bidder-level claims are gated instead of inferred from winner/award records.

### 4. Context-aware severity
The engine applies explicit deterministic context rules for emergency/disaster procurement, correction/corrigendum context, and PSU/internal-procurement context. Context can suppress or cap an indicator but cannot invent supporting facts.

### 5. Named multi-signal patterns
Risk classification uses explicit rule combinations such as rapid-repeat + repeated supplier, related-party overlap combinations, award-timing patterns, buyer-supplier identity, and value anomalies. Patterns are named findings, not arithmetic additions of indicator points.

### 6. Existing deterministic screening UI
`/red-flags` continues to provide the deterministic V2 assessment, evidence completeness/confidence summary, named pattern cards, indicator drill-down, evidence status, supporting records, context adjustments, confirmation requirements, explainability tree, and investigator-review disclaimer.

### 7. Dedicated human Evidence Verification workspace
`/verification` now adds the explicit human-in-the-loop verification layer on top of the grounded investigation output:

- loads the existing investigation pipeline for a verified procurement subject
- presents each reasoning citation with source, record, quality and support metadata
- review states: `Corroborated`, `Requires verification`, `Insufficient data`, `Contradictory`
- reviewer notes and evidence-backed alternative explanations
- direct original-source links
- case-level review counts and completion state
- local review-draft persistence without mutating source records or deterministic risk calculations
- explicit evidence → finding integrity boundary

### 8. Phase 5 contract tests
Existing Phase 5 risk-engine registry tests remain the contract for deterministic screening. The new verification layer is additive and does not replace the backend risk or reasoning source of truth.

## Integrity boundaries retained

1. SENTRY surfaces review leads; it does not adjudicate fraud, corruption, or collusion.
2. Indian procurement records remain the evidence boundary for Indian cases.
3. Historical benchmarks remain contextual, not statutory thresholds.
4. Bidder-count, bid-price, bid-rotation, and competitor-conditioned claims remain unavailable when reliable bidder-level evidence is absent.
5. Single red flags do not constitute proof of wrongdoing.
6. Reviewer annotations cannot override deterministic risk calculations.
7. `Insufficient data` and `Contradictory` remain explicit review outcomes rather than silent risk changes.
8. Source provenance remains attached to the evidence chain.

## Validation note

The implementation is committed to `main`. CI/runtime execution for this exact checkpoint was not independently run from this chat session; deployment status is intentionally not used as a Phase 5 completion criterion.
