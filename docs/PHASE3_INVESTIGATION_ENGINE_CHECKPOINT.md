# Phase 3 — Four-Phase Investigation Engine

Status: **Complete**

## Scope

Phase 3 establishes the investigation journey as four explicit, ordered phases:

1. **Intelligence** — assemble known procurement facts, canonical entities, records, relationships, source provenance, screening observations, and evidence coverage.
2. **Evidence gaps** — expose what is missing or weak, the documents/questions required to discriminate routine procurement from escalation, and the next evidence to obtain.
3. **Corroboration** — test additional evidence against official records, existing facts, deterministic indicators, entity relationships, and alternative explanations without treating an unverified submission as proof.
4. **Assessment** — consolidate the evidence-backed current position, limitations, source provenance, alternative explanations, outstanding questions, and recommended human review action.

## Existing engine alignment

The current investigation backend already executes canonical entity resolution, precision retrieval for entity investigations, deterministic indicator generation, Risk Engine V2 assessment, evidence construction, chronology, and investigation-graph construction. The report/reasoning path then grounds the resulting position in the retrieved evidence.

The Phase 3 frontend now makes the four-phase protocol explicit before the investigation workspace so the user understands the journey before interacting with results.

## Evidence standard

- Screening signals are **review leads**, not determinations.
- A single red flag is not proof of wrongdoing.
- Missing or incomplete evidence does not increase risk by itself.
- Winner-only procurement records do not support bidder-count or bid-level conclusions.
- Indian procurement sources remain the authoritative case-data scope; foreign records are not mixed into Indian case evidence.
- Historical benchmarks are contextual rather than statutory thresholds.
- AI-generated narrative is explanatory and source-grounded; deterministic records remain the evidence foundation.

## UI implementation

- Added `frontend/src/components/intel/investigation-phases.tsx`.
- Added the protocol to `frontend/src/app/investigate/page.tsx`.
- The component is presentation-only and does not alter retrieval, risk calculations, entity resolution, or evidence semantics.

## Exit criteria

Phase 3 is considered closed when the investigation workflow is presented consistently as:

`Intelligence → Evidence gaps → Corroboration → Assessment`

with the underlying evidence/risk pipeline preserved and no new unsupported inference introduced.
