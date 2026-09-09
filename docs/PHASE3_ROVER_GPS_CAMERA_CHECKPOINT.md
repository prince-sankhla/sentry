# Phase 3 — Rover Mission → Device GPS → Live Camera Checkpoint

Status: READY FOR MERGE

## Acceptance

- Exact Phase 2 tender and requirement remain bound to the Field mission.
- Rover authorization is required before device telemetry is accepted by the Phase 3 UI flow.
- Browser/device geolocation is requested from the real device and forwarded to the existing SENTRY FIELD `/telemetry` endpoint.
- The UI never fabricates latitude or longitude; unavailable GPS remains unavailable.
- Live inspection camera is blocked until mission authorization and live device GPS are present.
- The camera stream carries the mission id, requirement id and selected capability into the existing local vision gateway.
- Live gateway state, GPS state, camera state, detections, evidence count and recent events are rendered from gateway state rather than hard-coded coverage values.
- Mission stop revokes gateway authorization and stops GPS/camera activity.

## Validation

- Phase 3 gateway contract tests: PASS.
- Phase 2 backend regression: PASS.
- Phase 1 backend regression: PASS.
- Frontend TypeScript check + Next production build: PASS.
- Vercel preview deployment for the Phase 3 head: READY.
- Preview `/field?tender=FIELD-DEMO-001&requirement=REQ-CCMS-01` returns HTTP 200 and renders the Phase 3 field entrypoint.

## Physical runtime validation boundary

The CI and Vercel environment can validate the browser application, gateway contracts and deployment, but cannot grant browser geolocation permission or reach the operator's private DroidCam URL. Actual device GPS and camera frames therefore require the local SENTRY FIELD gateway plus the operator device at runtime. No fake GPS/camera values are used to claim this physical test was completed in CI.

## Scope boundary

Evidence aggregation, persistent mission evidence, expected-vs-observed discrepancy analysis, alternative-explanation reasoning and the AI investigator remain subsequent phases.
