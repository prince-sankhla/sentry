# Phase 4 — Mobile GPS Integration Checkpoint

Status: READY FOR VALIDATION

## Acceptance

- Phone/browser geolocation is the Phase 4 GPS source.
- A GPS sample carries latitude, longitude, accuracy and device capture timestamp.
- Mobile GPS telemetry is accepted only for an authorised, exact tender + mission + requirement.
- GPS context is visible through the live gateway status without fabricated coordinates.
- GPS state returns to unavailable when the mission is stopped or no live sample exists.
- The operator UI exposes live coordinates, accuracy and capture time.

## Validation

- Dedicated Phase 4 contract tests cover unauthorised telemetry, exact mission linkage, wrong tender context, stale/future timestamps and stop/revocation.
- Phase 3 gateway regression remains in the same CI job.
- Frontend production build runs in the Phase 4 workflow.

## Runtime boundary

CI can validate the browser application and gateway contract, but it cannot grant the operator phone's geolocation permission. A real-device acceptance check still requires opening the deployed/local Field UI on a phone, authorising the exact mission, enabling mobile GPS and observing real coordinates plus accuracy.

No fake coordinates are used as physical-runtime proof.

## Scope boundary

Persistent mission evidence aggregation, expected-vs-observed discrepancy analysis, AI investigation and final case closure remain later phases.
