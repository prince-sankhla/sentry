# SENTRY live procurement monitoring

SENTRY now has a scheduled polling path for official Indian procurement feeds.

## Sources

- CPPP/eProcurement homepage: `https://www.eprocure.gov.in/eprocure/app?page=Home&service=page`
- GeM BidPlus listing: `https://bidplus.gem.gov.in/all-bids`

The poller discovers official detail links, passes them through the existing live ingestion services, and relies on importer idempotency so unchanged records are not duplicated.

## Schedule

`.github/workflows/live-procurement-monitor.yml` runs every 15 minutes and can also be triggered manually from GitHub Actions.

The 15-minute cadence matches the public source behaviour currently documented on CPPP/ePublishing and GeM, both of which state that newly published/modified records can take around 15 minutes to appear in their listings.

## Security

Set a GitHub Actions repository secret:

`SENTRY_MONITOR_TOKEN`

Set the same value in the backend deployment environment under:

`SENTRY_MONITOR_TOKEN`

The `/api/monitoring/poll` endpoint rejects requests without the configured bearer token.

## What happens on each run

1. Fetch official CPPP and GeM public listing pages.
2. Discover current tender/bid detail URLs.
3. Fetch each discovered official detail page.
4. Normalize and persist the procurement record through the existing live ingestion services.
5. Preserve source URL and retrieval provenance.
6. Reuse existing idempotent import semantics.
7. The Monitoring UI re-reads the database and shows current tender/award activity and deterministic review signals.

## Important scope boundary

This is scheduled source polling, not a guaranteed sub-minute real-time stream. Source-side publication delay, rate limiting, CAPTCHA, HTML changes, network failures, or temporary portal unavailability can delay an individual record. A failed poll is surfaced as a partial result rather than silently treated as success.

The GeM listing is rendered dynamically by the public site; if its HTML stops exposing bid links, the poller will safely discover fewer records until the source adapter is updated.
