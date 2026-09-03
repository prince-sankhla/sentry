# SENTRY — Phase 8 Complete Checkpoint

## Phase
**Phase 8 — Investigation Engine 2.0**

## Status
**COMPLETE — integrated into the existing investigation pipeline**

## Audit-first decision
Phase 8 was implemented by auditing the existing investigation stack before adding duplicate orchestration. The current `main` branch already contains the substantive Investigation Engine 2.0 capabilities, so this phase formalizes and validates that integrated surface rather than introducing a parallel engine.

## Investigation journey
The live investigation pipeline now exposes the intended analyst journey:

1. **Detect** — deterministic indicators + Risk Engine V2 patterns.
2. **Contextualize** — trusted procurement-context analysis and competing evidence.
3. **Connect** — canonical entity resolution, buyer/supplier relationships and typed graph.
4. **Compare** — benchmark context and historical/comparable procurement data.
5. **Challenge** — Evidence Challenge asks what evidence could prove each finding wrong.
6. **Corroborate** — source-attributed evidence ledger, documents, timeline and graph relationships.
7. **Verify** — evidence-status validation, grounding checks and provenance.
8. **Prioritize** — deterministic priority queue and risk/confidence output for human review.

## Existing integrated components audited
- `backend/app/api/routes/investigations.py`
  - `/api/investigations/stream`
  - entity resolution
  - investigation planning/execution
  - evidence-packet export
  - trusted context-analysis endpoints
  - priority investigation queue
- `backend/app/services/investigation_executor.py`
  - canonical resolution before retrieval
  - precision retrieval for entity investigations
  - Indian-only entity retrieval
  - package finalization
  - deterministic indicators + Risk Engine V2
  - complete investigation graph
- `backend/app/services/investigation_reasoning.py`
  - grounded analyst reasoning
  - Investigator Review
  - Evidence Challenge
  - evidence ledger / packet
  - analyst trace/report
  - investigation memory
- `backend/app/services/investigator_review.py`
  - supporting evidence
  - routine-procurement competing evidence
  - evidence still required
- `backend/app/services/evidence_challenge.py`
  - evidence-backed legitimate explanations
  - verification questions
  - fixed non-verdict decision boundary
- `frontend/src/app/investigation-workspace.tsx`
  - live streamed pipeline
  - entity resolution state
  - investigation replay
  - graph/evidence/analyst surfaces
  - provider provenance
  - follow-up investigation flow

## Integrity boundaries
- Risk remains deterministic and explainable.
- Investigation Review and Evidence Challenge are read-only organizational layers; they do not modify indicators, scores or severity.
- LLM output is grounded in the executed evidence package and has deterministic fallback behavior.
- No finding is presented as proof of wrongdoing.
- Missing evidence remains missing; the system does not manufacture bidder-level facts.
- Official procurement provenance remains attached to evidence.
- Entity investigations use precision retrieval to avoid contaminating a case with unrelated records.
- Indian procurement scope remains distinct from international procurement sources.

## Phase 8 acceptance criteria
- [x] One investigation pipeline orchestrates planning, retrieval, entity resolution, detection, evidence, grounding and reasoning.
- [x] Canonical entity resolution precedes entity-specific retrieval.
- [x] Findings are linked to provenance-backed evidence.
- [x] Competing/routine explanations are surfaced without cancelling findings.
- [x] Every major finding can be challenged with verification questions.
- [x] Complete typed investigation graph is generated from the package.
- [x] Investigation replay exposes how the system reached its output.
- [x] Priority queue supports human-review prioritization.
- [x] Evidence Packet export is available in structured JSON and print-ready HTML.
- [x] LLM reasoning cannot become the source of truth for risk.

## Known validation limitation
This checkpoint records code-level integration based on repository inspection. A fresh full CI/test run and production deployment verification were not performed as part of this checkpoint, so neither is claimed here.

## Next phase
**Phase 9 — Graph / Ecosystem Intelligence**

Target: turn the existing typed investigation graph into a deeper ecosystem-level intelligence layer covering Buyer ↔ Tender ↔ Supplier ↔ Award ↔ Document ↔ Evidence ↔ Related Entity relationships, with deterministic relationship signals and investigation-grade graph explanations.
