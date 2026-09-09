# Phase 1 — Recommended Tender → Investigation Entry

Status: **Implementation in progress**

## Goal

Create one deterministic, end-to-end entry path from the live procurement database's recommended tender lead into the existing core investigation pipeline.

The phase must not invent a risk score for a direct field-ready tender. The queue should identify a concrete tender lead, preserve its canonical database identity, and open the investigation against that exact tender record rather than an ambiguous free-text subject.

## Golden path

`Priority Investigation Queue → Recommended Tender → Start Investigation → Canonical Tender Identity → Investigation Stream → Evidence-backed Investigation Package`

## Acceptance criteria

- The recommended card is backed by a current database tender record.
- The card carries a stable tender identity (database tender id and/or source record id), not only a display title.
- Clicking the card starts investigation on that exact tender identity.
- Entity-resolution ambiguity cannot silently replace the selected tender with another entity.
- The investigation UI retains the selected tender context while the stream executes.
- Backend/API/database wiring is exercised end-to-end.
- No mock success state is used as proof of completion.
- The phase is only closed after frontend typecheck/build and a live API integration check against the connected Neon database.

## Non-goals

- Physical verification dispatch.
- Mobile GPS.
- Rover integration.
- Contract-vs-reality aggregation.
- Final AI field assessment.

Those belong to later phases.
