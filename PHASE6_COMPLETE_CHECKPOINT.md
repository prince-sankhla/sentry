# SENTRY — Phase 6 Complete Checkpoint

**Phase:** 6 — Investigation Graph & Timeline 2.0  
**Status:** COMPLETE  
**Repository:** `prince-sankhla/sentry`  
**Branch:** `main`

## Delivered

### Investigation Graph 2.0
- Existing relationship graph remains the source-backed investigation surface for buyers, suppliers, tenders, awards, indicators, documents and evidence.
- Added explicit investigation-radius controls: Direct (depth 1), Connected (depth 2), Extended (depth 3).
- Focused supplier/tender context is preserved when changing depth.
- Existing node search, type filtering, horizontal/vertical layout, camera controls, selection/highlighting and full-screen exploration remain intact.
- Graph relationships continue to come from the backend package/API; no client-side relationship inference was introduced.

### Timeline 2.0
- Expanded the timeline retrieval window to 160 events.
- Added event-type filters for all events, tender publication, tender closing and awards.
- Added visible event/day counts so chronology scope is explicit.
- Existing expandable event details and source-linked tender/company navigation remain intact.

### Cross-surface investigation context
- Added reusable `InvestigationContextRail` for connecting records, network, chronology and review-signal surfaces without changing analytical semantics.

## Integrity boundaries retained

- Graph edges represent recorded relationships only; no bidder inference is introduced.
- Timeline is descriptive chronology, not causal inference.
- Risk/review signals remain deterministic review leads and are not converted into findings by graph or timeline UI.
- Indian procurement evidence boundaries and provenance requirements remain unchanged.

## Commits

- `e23f54c` — cross-surface investigation context rail
- `ea5e69a` — graph investigation radius controls
- `5db1135` — timeline event filters
