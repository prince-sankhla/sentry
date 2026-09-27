# SENTRY — Automated Live Procurement Monitoring Checkpoint

Status: IMPLEMENTED — direct GitHub Actions worker

## Delivered

- GitHub Actions worker runs every 15 minutes.
- Official CPPP/eProcurement listing discovery.
- Official GeM BidPlus listing discovery with safe best-effort parsing for dynamically rendered bid listings.
- Candidates are fetched and normalized in memory first.
- The existing deterministic Risk Engine V2 screens the current candidate batch before persistence.
- Only records referenced by deterministic indicators are persisted through the existing idempotent importer.
- Unflagged candidates are discarded after screening and are not written to the canonical procurement tables.
- No Vercel endpoint or `SENTRY_MONITOR_TOKEN` is required by the scheduled worker.

## Runtime flow

Official source listing → official detail URLs → in-memory normalization → deterministic screening → **flagged records only** → existing normalized SENTRY database + provenance.

## Schedule boundary

Polling cadence is 15 minutes. This is aligned with the public source pages' stated listing propagation behaviour. It is not a sub-minute real-time feed and source-side delay, rate limiting, CAPTCHA, HTML changes, or source failure can affect freshness.

## Configuration required

Set one GitHub Actions repository secret:

`DATABASE_URL`

The secret must be a write-capable PostgreSQL/Neon connection string for the SENTRY database. The scheduled job connects directly to the database; it does not call Vercel.

## Integrity boundaries

- Only official CPPP/GeM hosts are accepted by the live fetcher.
- Existing deterministic Risk Engine semantics are unchanged.
- Missing evidence is not converted into positive risk.
- Monitoring signals remain review leads, not adjudications.
- The system does not claim that every government portal is covered; the implemented automated sources are CPPP/eProcurement and GeM BidPlus.
- Unflagged live candidates are deliberately ephemeral for this monitoring path; flagged records retain normal SENTRY provenance and idempotency.

## References

- `backend/scripts/live_monitor_cycle.py`
- `backend/app/services/live_cppp_ingestion.py`
- `backend/app/services/live_gem_ingestion.py`
- `.github/workflows/live-procurement-monitor.yml`
- `frontend/src/components/intel/live-monitoring.tsx`
- `docs/LIVE_MONITORING_SETUP.md`
