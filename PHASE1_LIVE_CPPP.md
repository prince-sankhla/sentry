# Phase 1 — Live Indian Procurement Ingestion

Implemented the first live-source ingestion path for official CPPP/eProcurement tender detail URLs.

## Flow

Official CPPP tender URL → server fetch → Tender ID extraction → canonical raw envelope → existing CPPP normalization → generic importer → provenance/version snapshot → Tender/Company/Award/Document rows → tender detail page.

## Scope

- Accept only `eprocure.gov.in` CPPP URLs.
- Preserve the original source URL and retrieval timestamp.
- Preserve the full fetched CPPP detail HTML as the raw record payload and content hash.
- Reuse the existing generic importer for idempotent upserts and `source_record_versions`.
- Reuse the existing CPPP document parser so NIT/work-item/corrigendum attachment URLs are retained when present.
- Add a production-facing Investigations entry point for live CPPP URLs.
- Reject non-CPPP hosts rather than fetching arbitrary URLs.
- Do not fabricate bidder counts, bid prices, withdrawals, or co-bidding data from winner-centric award records.

The next Phase 1 increment is direct Tender-ID discovery/search for CPPP where the portal permits it without bypassing CAPTCHA or access controls, followed by GeM live ingestion.
