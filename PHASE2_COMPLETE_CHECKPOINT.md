# Phase 2 — Tender Kundali / Deep Tender Intelligence

Status: COMPLETE

Implemented:
- Dedicated `/api/tenders/{id}/kundali` intelligence endpoint.
- Live tender facts, lifecycle status, procurement method/category/geography fields when present.
- Latest source snapshot provenance with content hash and retrieval timestamp.
- Tender document docket with document type, source URL, content/evidence hashes and availability.
- Award/supplier history across the Indian procurement database.
- Historical comparable Indian tenders using buyer/category/method/value similarity.
- Descriptive P25/median/P75 and percentile benchmark context from the comparable sample.
- Tender-level review leads for supported value/document conditions.
- Explicit limitations preventing unsupported bidder/bid-price claims.
- Tender detail UI now presents the full Kundali alongside existing risk, award, graph and evidence surfaces.

Integrity contract:
- International-financier/foreign sources are excluded from the Indian Kundali.
- Benchmarks are contextual, not statutory thresholds.
- A recorded awardee is never treated as a bidder count.
- Findings remain investigation leads and require investigator review.
