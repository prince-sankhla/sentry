# SENTRY live procurement monitoring

SENTRY uses a scheduled GitHub Actions worker to poll official Indian procurement sources without routing the monitor through Vercel.

## Sources

- CPPP/eProcurement homepage: `https://www.eprocure.gov.in/eprocure/app?page=Home&service=page`
- GeM BidPlus listing: `https://bidplus-global.gem.gov.in/`

Both are official government procurement surfaces. CPPP is the Government of India's eProcurement system, and its public portal provides active tender, award, archive and status views. GeM's public BidPlus listing states that newly published or modified bids can take up to 15 minutes to appear. citeturn0search0turn0search1turn1search0

## Schedule

`.github/workflows/live-procurement-monitor.yml` runs every 15 minutes and can also be triggered manually from GitHub Actions.

## Configuration

Set one GitHub Actions repository secret:

`DATABASE_URL`

It must be a write-capable PostgreSQL/Neon connection string for the SENTRY database. The worker connects directly to the database; no Vercel endpoint and no `SENTRY_MONITOR_TOKEN` are required.

## What happens on each run

1. Fetch the official CPPP and GeM public listing pages.
2. Discover official tender/bid detail URLs only; non-government hosts are rejected.
3. Fetch each discovered detail page.
4. Normalize the records **in memory** using the existing SENTRY source adapters.
5. Run the deterministic Risk Engine V2 over the current candidate batch.
6. Determine which tender references are actually attached to triggered indicators.
7. Persist **only those flagged records** through the existing idempotent importer, preserving source URL, documents and provenance.
8. Discard unflagged candidates from the worker process without inserting them into the canonical procurement tables.

This means the monitor database grows from **findings**, not from every tender encountered by the 15-minute crawler.

## Important scope boundary

This is scheduled source polling, not a guaranteed sub-minute real-time stream. Source-side publication delay, rate limiting, CAPTCHA, HTML changes, network failures, or temporary portal unavailability can delay an individual record. The current automated coverage is CPPP/eProcurement and GeM BidPlus; it does not claim to cover every Indian government procurement portal.

The GeM listing is rendered dynamically by the public site. If its HTML stops exposing bid links, the worker safely discovers fewer records until the source adapter is updated.
