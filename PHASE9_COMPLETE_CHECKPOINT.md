# SENTRY — Phase 9 Complete Checkpoint

Status: COMPLETE

Phase 9 turns the existing procurement relationship graph into an investigation-grade ecosystem intelligence layer without replacing or duplicating the legacy graph.

## Implemented

- New India-scoped ecosystem graph contract in `backend/app/schemas/ecosystem_graph.py`.
- New deterministic ecosystem projection in `backend/app/services/ecosystem_graph.py`.
- New API: `GET /api/ecosystem/graph`.
- Registered route in `backend/app/main.py`.
- Core ecosystem chain represented as:
  - Buyer → Tender
  - Tender → Award
  - Award → Company
  - Document → Tender
  - Evidence → Tender / Company when explicitly linked
  - Category → Tender
  - Buyer → Company relationship when supported by repeated award records
- Deterministic relationship signals for repeat buyer–supplier relationships and supplier award concentration.
- Relationship metadata includes the record basis and counts/shares used to derive the signal.
- Indian procurement scope excludes configured international procurement sources.
- Bidder participation is deliberately not inferred from award records.
- Missing/unlinked evidence is not treated as negative evidence.
- Relationship signals remain review leads, not findings of wrongdoing.

## Compatibility

The existing `/api/graph` relationship graph remains intact. Phase 9 adds a dedicated ecosystem intelligence projection rather than changing the semantics of the existing endpoint.

## Not claimed

- No bidder-level competition conclusion without bidder-level source data.
- No causal or misconduct finding from graph connectivity.
- No production deployment claim until Vercel deployment is independently verified.
