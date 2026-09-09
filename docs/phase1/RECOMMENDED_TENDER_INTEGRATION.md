# Phase 1 — Recommended Tender → Investigation Entry

Goal: carry one concrete tender lead from the live procurement database into the existing investigation pipeline using a stable tender identifier. No physical verification, rover, GPS, or field workflow belongs in this phase.

The existing priority queue already surfaces direct `FIELD:` and CAG tender leads from the current PostgreSQL database and labels them as review leads without inventing a risk score. The existing investigation workspace then accepts a query string and runs entity resolution before retrieval. Phase 1 must remove the identity ambiguity between those two surfaces.

Acceptance criteria:

1. Queue item exposes stable tender identity: database UUID, source record id, title, and source URL when available.
2. Clicking a direct tender lead opens `/investigate` with the canonical tender identity, not a buyer-only or title-only query.
3. Investigation planning recognizes a tender identifier as `investigation_type=tender`.
4. Retrieval is scoped to the exact tender record before any broader related-record analysis.
5. The resulting investigation package contains the selected tender as a source-backed procurement record.
6. Existing evidence, indicator, graph, timeline, and reasoning outputs continue to work unchanged.
7. Frontend and backend share the same tender identity throughout the run.
8. End-to-end verification must exercise browser → backend → Neon → investigation executor → SSE → frontend result state.
9. Frontend typecheck/build must pass before the phase is closed.

Current known mismatch:

- `PriorityQueueItem` currently does not expose tender identity fields even though the backend queue already creates direct tender leads from database rows.
- The queue UI's `onOpen` accepts only a string subject, so a direct tender lead currently launches by title text instead of stable tender ID.
- The generic investigation executor deliberately resolves entities first and retrieves by query; it does not yet have an exact-tender retrieval path.

These are the Phase 1 implementation targets.
