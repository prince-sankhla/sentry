# Phase 4 — Buyer Intelligence

Status: COMPLETE

## Scope delivered

- Dedicated buyer Kundali endpoint: `GET /api/buyers/kundali?buyer=<name>`
- Buyer longitudinal profile from indexed Indian procurement records
- Tender volume and awarded-tender coverage
- Supplier concentration and supplier relationship history
- Category, geography, and procurement-method distributions
- Tender-value P25 / median / P75 contextual baseline
- Publication-to-closing submission-window statistics
- Award-to-estimate ratio context where both values exist
- Monthly buyer activity timeline
- Review-lead signals for repeat suppliers, concentration, method concentration, short windows, and award/estimate context
- Data-quality coverage panel and explicit `INSUFFICIENT_DATA` / `NOT_INDEXED` states
- Buyer Kundali frontend at `/buyers?name=<exact buyer name>`

## Integrity boundaries

- Only Indian procurement records are included; international-procurement sources remain excluded through the existing scope filter.
- Awarded suppliers are not treated as a bidder population.
- Bidder participation, bid-price behaviour, withdrawal patterns, and cancellation/re-tender frequency are not asserted when the current Indian corpus does not expose the required fields.
- Concentration and award-rate metrics are descriptive investigation leads, not findings of wrongdoing.
- Value distributions are contextual baselines, not statutory thresholds.
- Buyer identity currently uses the stored `Tender.procuring_entity` value with case-insensitive normalization; future entity-resolution work can promote government organizations into canonical buyer entities.

## Validation

`backend/tests/test_buyer_kundali.py` covers benchmark quantiles, missing submission dates, unknown distribution dimensions, and award/estimate ratio availability.
