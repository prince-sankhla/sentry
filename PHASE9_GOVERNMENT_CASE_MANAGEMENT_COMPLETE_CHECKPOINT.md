# SENTRY — Phase 9 Government Case Management Checkpoint

**Status:** COMPLETE (product-surface implementation)

This checkpoint follows the current execution roadmap where Phase 9 is **Government Case Management**. The repository also contains an older `PHASE9_COMPLETE_CHECKPOINT.md` for the historical ecosystem-graph milestone; that document is intentionally preserved as historical context.

## Delivered

- Government-only Case Management workspace at `/cases`.
- Explicit human workflow states: Open, Under review, Evidence requested, Monitoring, Escalated, Closed.
- Search and status filtering across cases.
- Case priority, finding count, evidence count, and outstanding-evidence request summaries.
- Direct drill-down from a case to the underlying investigation.
- Controlled workflow advancement with visible state transitions.
- Role-gated navigation: Case Management appears only for `government_audit`.
- Local browser persistence for the demo workflow surface.
- Clear separation between case workflow state and deterministic risk assessment.

## Integrity boundaries

- Case workflow state never changes Risk Engine V2 indicators, scores, severity, or evidence status.
- Advancing a case does not imply substantiation, guilt, enforcement, or adjudication.
- No automatic submission to a government system was introduced.
- No shared multi-user government backend is claimed by this phase; local persistence is explicitly disclosed.
- Existing investigation evidence and provenance remain the underlying source of truth.

## Acceptance criteria

- [x] Government-only case management surface exists.
- [x] Human-review lifecycle is explicit.
- [x] Cases are searchable and filterable.
- [x] Cases link back to investigations.
- [x] Workflow changes are separated from risk calculations.
- [x] Navigation respects workspace role.

## Validation note

The phase was implemented after auditing the existing review, verification, investigation, ecosystem, and role-navigation surfaces. Fresh full-suite/production execution was not performed from this chat session, so this checkpoint does not claim a fresh CI pass or production readiness.
