# Phase 6 — Benchmark Engine

Status: COMPLETE

## Scope delivered

- Existing benchmark model/engine reviewed before extending functionality.
- Added an India-only contextual benchmark adapter for tender estimated values.
- Comparable-population fallback hierarchy:
  1. buyer + category + procurement method + geography + value band
  2. buyer + category + procurement method + geography
  3. buyer + category + procurement method
  4. buyer + category
  5. category + procurement method
  6. category
  7. global Indian procurement corpus
- Minimum sufficient sample size is 5; insufficient populations never produce inferential benchmark statistics.
- Added percentile rank, P25, median, mean, P75, IQR and bounded IQR deviation.
- Added explicit contextual interpretation; benchmark statistics are not statutory thresholds and are not findings of wrongdoing.
- International sources are excluded through the existing procurement scope contract.
- Added API: `GET /api/benchmarks/tender/{tender_id}`.
- Integrated a premium Market Benchmark panel into the existing tender intelligence page.
- Added Phase 6 test coverage for value-band boundaries, percentile behaviour, insufficient samples and quartile calculations.

## Integrity boundaries

- Benchmarks are descriptive/contextual baselines only.
- Missing estimated value produces `benchmark_available=false` rather than an inferred value.
- Bidder participation is not inferred from awards.
- No statutory procurement threshold is encoded by the benchmark bands.
- The original benchmark engine remains intact; the new adapter is an integration layer so existing Phase 1–5 functionality is preserved.
