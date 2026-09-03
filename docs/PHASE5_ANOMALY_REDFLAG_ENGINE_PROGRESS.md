# SENTRY Phase 5 — Anomaly / Red-Flag Engine

## Status

**IN PROGRESS — core engine already implemented; dedicated investigator surface added in this phase.**

Phase 5 is the anomaly / red-flag layer between deterministic procurement data and investigator review. The current Risk Engine V2 is the authoritative risk implementation: indicators are deterministic, patterns are named rule combinations, confidence is independent from severity, and every output remains a review lead rather than a finding of wrongdoing.

## What is now exposed

- `/red-flags` provides a dedicated investigator-facing red-flag explorer.
- Each returned indicator shows severity, score, evidence status, confidence, supporting records, context adjustments, and evidence still required.
- Named multi-signal patterns are rendered separately from individual indicators.
- The explainability tree exposes rule → evidence status → context → final severity.
- The screen reuses the existing `/api/investigations/stream` pipeline, so it evaluates the same package and Risk Engine V2 output as the main investigation workspace.

## Current deterministic coverage

The live V2 registry includes competition, value, concentration, timing, process, and relationship indicators such as repeated supplier, buyer/supplier concentration, abnormal value, award clustering, suspicious timing, duplicate tender text, missing award data, award-vs-estimate anomaly, buyer-equals-supplier, missing documents, contract fragmentation, and relationship-overlap indicators.

## Integrity boundaries

- Indian procurement source evidence remains the primary basis for the assessment.
- Missing bidder-level data is not converted into a single-bidder finding. Current Indian coverage is winner/award-centric where bidder participation is unavailable.
- A single indicator does not prove fraud, corruption, collusion, or bid rigging.
- Historical benchmarks and concentration signals are contextual review leads, not statutory thresholds.
- Missing evidence lowers evidentiary status; it does not become a positive risk signal.
- Context such as emergency/disaster/corrigendum conditions can suppress or qualify a signal deterministically.
- AI narration is downstream of the deterministic assessment and does not calculate risk.

## Remaining Phase 5 work

The next implementation increment should expand the P0 registry only where the source data supports it, especially submission-window peer comparison and other benchmark-conditioned signals. Bid-price equality/rotation and bidder-conditioned competition signals remain gated until reliable bidder-level records are present.
