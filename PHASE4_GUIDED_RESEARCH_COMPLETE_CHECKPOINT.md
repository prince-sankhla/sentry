# Guided Research & Evidence Collection — Phase 4 (Frontend Roadmap)

Status: COMPLETE

## Delivered

- Added `/research` as a dedicated Guided Research workspace.
- Added investigation-subject source retrieval using the existing SENTRY web-evidence search path.
- Surfaced practical evidence-gap tasks focused on primary procurement records.
- Added suggested-source review with source provenance and direct source links.
- Added investigator-supplied evidence capture with title, URL, and rationale note.
- Added duplicate protection and removal for captured research items.
- Added an explicit `Pending corroboration` state so research material is not presented as verified case evidence.
- Added best-effort local draft persistence for the research ledger without modifying backend evidence or risk calculations.
- Added `Guided Research` to the role-aware navigation for all three workspace roles.

## Integrity boundaries preserved

- Research material remains separate from verified case evidence until corroboration.
- Primary/official procurement sources are preferred.
- Secondary reporting is contextual and cannot replace primary procurement evidence.
- No deterministic indicator, risk score, severity, or adjudication logic is modified by this phase.

## Next phase

Phase 5 — Evidence Verification & Reasoning 2.0.
