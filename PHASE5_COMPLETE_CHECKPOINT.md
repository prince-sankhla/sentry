# SENTRY — Phase 5 Complete Checkpoint

**Phase:** 5 — Anomaly / Red-Flag Engine  
**Status:** COMPLETE (implementation checkpoint)  
**Repository:** `prince-sankhla/sentry`  
**Branch:** `main`

## Delivered

### 1. Deterministic integrity screening
The investigation pipeline now carries the deterministic Risk Engine V2 assessment as the authoritative integrity-screening output. It separates indicator detection, context interpretation, evidence validation, named pattern classification, confidence, and explainability rather than using an opaque aggregate score.

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
Each V2 indicator carries:

- stable identifier and human-readable name
- base and final severity
- deterministic score
- evidence status (`verified`, `probable`, `unknown`)
- confidence independent from risk severity
- supporting record references
- required evidence still needed for confirmation
- deterministic context notes
- mandatory investigator-review status

Missing evidence never becomes a positive finding. Unsupported bidder-level claims are gated instead of inferred from winner/award records.

### 4. Context-aware severity
The engine applies explicit deterministic context rules for emergency/disaster procurement, correction/corrigendum context, and PSU/internal-procurement context. Context can suppress or cap an indicator but cannot invent supporting facts.

### 5. Named multi-signal patterns
Risk classification uses explicit rule combinations such as rapid-repeat + repeated supplier, related-party overlap combinations, award-timing patterns, buyer-supplier identity, and value anomalies. Patterns are named findings, not arithmetic additions of indicator points.

### 6. Dedicated Phase 5 UI
`/red-flags` provides:

- screening launcher
- overall deterministic V2 assessment
- evidence-completeness/confidence summary
- named pattern cards
- expandable indicator cards
- evidence status
- supporting records
- context adjustments
- confirmation requirements
- explainability tree
- investigator-review disclaimer

### 7. Phase 5 contract tests
Added `backend/tests/test_phase5_registry_contract.py` to lock the Phase 5 registry, explicit bidder-data gating, deterministic empty-package behaviour, and investigator-review contract.

The existing `backend/tests/test_risk_engine.py` already covers explainability, timing anomalies, abnormal values, clustering, duplicate descriptions, high-value direct awards, contract fragmentation, buyer/supplier identity, award-vs-estimate anomalies, named patterns, and severity bounds.

## Integrity boundaries retained

1. SENTRY surfaces review leads; it does not adjudicate fraud, corruption, or collusion.
2. Indian procurement records remain the evidence boundary for Indian cases.
3. Historical benchmarks remain contextual, not statutory thresholds.
4. Bidder-count, bid-price, bid-rotation, and competitor-conditioned claims remain unavailable when reliable bidder-level evidence is absent.
5. Single red flags do not constitute proof of wrongdoing.
6. Source provenance remains attached to the evidence chain.

## Validation note

The Phase 5 implementation and test contracts are committed to `main`. CI/runtime execution for this exact checkpoint was not independently run from this chat session; deployment status must be verified separately in Vercel before claiming production readiness.
