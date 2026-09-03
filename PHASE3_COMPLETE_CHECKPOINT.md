# Phase 3 — Supplier Intelligence / Supplier Kundali

Status: COMPLETE

Implementation commit: `587fba0a4353c195505d1f67df7a1bd4b276428f`

## Delivered

- Dedicated API: `GET /api/companies/{company_id}/kundali`
- Indian procurement award history only; international-financier sources excluded through the existing procurement scope.
- Supplier profile metadata and provenance fields.
- Award/tender counts and total/average award value.
- Buyer concentration and repeat-buyer relationship metrics.
- Category, geography, and procurement-method concentration views.
- Supplier award-value distribution: minimum, P25, median, P75, maximum and sample size.
- Monthly supplier activity timeline.
- Review-lead signals for repeat award history and concentration patterns.
- Explicit participation/bidder-level data-gap handling; missing participation is not interpreted as a loss.
- Explicit debarment status of `not_indexed` when no authoritative linked record exists.
- Source URL and retrieval-timestamp coverage metrics.
- Supplier Kundali frontend panel with animated loading, metrics, concentration bars, benchmark context, timeline, data-quality state, signals, and limitations.
- Deterministic unit tests for concentration population handling and Decimal-safe benchmark calculations.

## Integrity boundaries

- A recorded award is a win; absence from the corpus is not a recorded loss.
- Participation rate is `INSUFFICIENT_DATA` for the current Indian corpus unless bidder-level records are actually available.
- Bid-price similarity, withdrawal, ranking, and competitor-conditioned participation are not asserted without bidder-level Indian evidence.
- Concentration is contextual review information, not a verdict or legal finding.
- Historical/value distributions are descriptive context and are not statutory thresholds.

## Next phase

Phase 4 — Buyer Intelligence.
