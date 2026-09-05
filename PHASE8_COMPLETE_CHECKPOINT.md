# SENTRY — Phase 8 Complete Checkpoint

## Phase
**Phase 8 — Public / Journalist → Government Review Pipeline**

## Status
**COMPLETE — review handoff and government intake experience implemented**

## Scope delivered

Phase 8 connects a completed investigation to a structured human-review handoff without changing the deterministic evidence or risk engines.

### Investigator / Researcher side
- Dedicated `GET /review?q=<investigation subject>` review-handoff route.
- Review handoff composes the investigation subject, observed review leads, evidence count, outstanding evidence requests, evidence-backed alternative explanations, and a submitter/reviewer note.
- Handoff draft can be saved locally for continuation and exported as JSON for external review workflows.
- Explicit non-adjudication language is shown at the handoff boundary.

### Government / Audit side
- Dedicated `GET /review/inbox` intake route.
- Review Inbox is visible only in the Government / Audit workspace navigation.
- Intake displays the prepared review lead, evidence volume, outstanding evidence, submitter note, and `Pending human review` state.
- Government intake is intentionally separated from automated risk calculation and enforcement.

### Navigation / role integration
- Public Investigator, Journalist / Researcher, and Government / Audit all receive the Official Review entry point.
- Government / Audit additionally receives the Review Inbox.
- Existing role-aware navigation remains presentation-only; it does not alter evidence retrieval, indicator calculations, severity, or risk scoring.

## Integrity boundaries retained

1. A review handoff is a request for human examination, not an allegation or finding of wrongdoing.
2. SENTRY does not submit automatically to a government case-management system; the current handoff is an explicit local/export workflow boundary.
3. Missing evidence is surfaced as outstanding evidence; it is never converted into a positive finding.
4. Evidence-backed alternative explanations remain visible to the reviewer.
5. Risk Engine V2 remains the authoritative deterministic screening layer.
6. Indian procurement evidence remains distinct from international context.

## Repository integration points

- `frontend/src/components/intel/review-handoff.tsx`
- `frontend/src/components/intel/review-handoff-page.tsx`
- `frontend/src/components/intel/review-inbox.tsx`
- `frontend/src/app/review/page.tsx`
- `frontend/src/app/review/inbox/page.tsx`
- `frontend/src/components/layout/app-shell.tsx`

## Validation note

The implementation was added after auditing the existing Investigation Workspace, Evidence Verification, Evidence Ledger, Risk Engine payloads, and role-aware navigation. A fresh full CI/test execution was not performed from this chat session, so no new test-suite or Vercel success is claimed here.

## Next phase
**Phase 9 — Government Case Management**

Target: give Government / Audit reviewers a formal human-review case lifecycle with assignment, review state, decision history, actions, and auditability while keeping SENTRY advisory and evidence-driven.
