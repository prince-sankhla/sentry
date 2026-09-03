# SENTRY Phase 1 — Live Indian Procurement Ingestion

Status: COMPLETE

Phase 1 establishes the live-ingestion foundation for Indian public procurement.

## Implemented

- Official CPPP direct tender URL ingestion.
- Official GeM BidPlus direct bid/document URL ingestion where the public page is accessible.
- Host allowlisting prevents arbitrary external URL fetches.
- Live pages are preserved with source URL, retrieval timestamp, content hash, and source-record identity.
- Existing generic importer is reused for normalization, idempotency, provenance, source-record versioning, company/award/document upserts, and checkpoints.
- GeM HTML bid metadata is normalized into the existing Tender model without inventing bidder-level facts.
- Investigation UI detects CPPP vs GeM URLs and routes them to the matching live-ingestion endpoint.
- Unsupported or blocked portal flows return explicit errors rather than fabricated records or CAPTCHA bypasses.

## Data integrity rules

- Live ingestion never synthesizes bidder_count, bid amounts, withdrawals, co-bidding, or other bid-level facts unless the source actually exposes them.
- A GeM/CPPP live bid page is treated as first-party procurement evidence; open-web discovery is not substituted for the official record.
- Historical international fixtures remain available for methodology/supporting context but are not used as Indian procurement case evidence.

## Phase 1 boundary

CPPP is the primary live tender-detail source. GeM direct public BidPlus pages are supported when reachable without authentication or CAPTCHA bypass. GeM authenticated-only/search flows remain explicitly unavailable until an authorized public feed or access mechanism is provided.

Next: Phase 2 — Tender Kundali / Deep Tender Intelligence.
