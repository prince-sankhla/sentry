# Phase 3 Recommendation + Investigation Workflow Fix

## Goal
Make field-verification-ready tenders and pothole-relevant tenders first-class recommendations on the SENTRY frontend, while preserving exact tender identity through the investigation pipeline.

## Requirements
- Field-verification-ready tenders are surfaced in a dedicated frontend recommendation section, separate from generic buyer/company queue items.
- Every core tender tagged/identified as field-verification-ready uses its stable UUID/reference identity.
- Pothole-relevant tender records are discovered from the core tender database, not from a static frontend list.
- Pothole recommendations open the exact tender investigation using its reference number/UUID.
- `?case=` audit routes do not pass CAG prose titles into generic entity investigation. They use explicit audit case handling.
- Physical verification handoff is shown only when the selected exact tender has a registered field profile.
- No title-based field selection.
- Failure paths remain explicit and do not silently downgrade a tender investigation into a company investigation.

## Acceptance
- Dedicated recommendation cards for Field Verification and Pothole tenders exist on the investigation landing page.
- Selecting any recommendation preserves exact tender identity.
- A tender/reference query is classified as `tender` and stays a tender investigation end-to-end.
- Audit case aliases remain dedicated case routes.
- Physical verification planning is keyed from the actual tender record/reference, not a free-form audit description.
- Frontend typecheck/build and backend contract tests pass.
