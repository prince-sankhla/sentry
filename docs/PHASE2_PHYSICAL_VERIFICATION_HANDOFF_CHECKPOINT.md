# Phase 2 — Physical Verification Handoff Checkpoint

Status: READY FOR MERGE

## Acceptance

- Exact core tender resolves by stable UUID.
- Core tender reference resolves to exactly one tender; ambiguous references fail closed.
- Registered physical verification profile is required before field launch.
- Profile exposes executable requirements, capability, expected quantity, machine and site.
- Investigation page surfaces `Physical verification required` only when a registered field profile exists.
- Field launch carries an exact field profile key and requirement id.
- Field console loads the exact field tender and requirement and does not use title search.
- Dispatch validates tender, requirement, capability and machine before authorization.
- Dispatch state persists tender id, requirement id and mission id in the gateway state.
- Capability mismatch is rejected with HTTP 400.

## Validation

- Phase 2 backend contract tests: PASS.
- Phase 1 backend regression contract for this head: PASS.
- Frontend typecheck + Next production build: PASS.
- Vercel preview deployment: READY.

## Scope boundary

Phone/browser GPS, live camera streaming, AI detections, evidence aggregation and contract-vs-reality discrepancy analysis are intentionally deferred to later phases.
