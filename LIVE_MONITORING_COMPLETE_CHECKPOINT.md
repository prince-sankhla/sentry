# SENTRY — Automated Live Procurement Monitoring Checkpoint

Status: IMPLEMENTED

## Delivered

- Protected `POST /api/monitoring/poll` endpoint.
- Scheduled GitHub Actions worker every 15 minutes.
- Official CPPP/eProcurement listing discovery.
- Official GeM BidPlus listing discovery with safe best-effort parsing for dynamically rendered bid listings.
- Reuse of existing CPPP and GeM live ingestion services for normalization, provenance and idempotent persistence.
- Monitoring UI now distinguishes database refresh cadence from upstream source polling and exposes current deterministic review signals.
- Live Monitoring is exposed in the government/audit and researcher navigation surfaces.

## Runtime flow

Official source listing → discovered tender/bid URLs → existing live ingestion → normalized SENTRY record → deterministic screening → Monitoring review-signal feed.

## Schedule boundary

Polling cadence is 15 minutes. This is aligned with the public source pages' stated listing propagation behaviour. It is not a sub-minute real-time feed and source-side delay or failure can affect freshness.

## Configuration required

Set `SENTRY_MONITOR_TOKEN` in both:

1. GitHub Actions repository secrets.
2. Backend deployment environment.

The workflow sends the token as `Authorization: Bearer ...` to `/api/monitoring/poll`.

## Integrity boundaries

- Only official CPPP/GeM hosts are accepted by live ingestion.
- Existing deterministic Risk Engine semantics are unchanged.
- Missing evidence is not converted into positive risk.
- Monitoring signals remain review leads, not adjudications.
- The system does not claim that every government portal is covered; the implemented automated sources are CPPP/eProcurement and GeM BidPlus.
- Deployment success and successful first scheduled run are not claimed from this chat because the production environment and GitHub Actions secret configuration were not independently executed here.

## References

- `backend/app/services/live_monitoring.py`
- `backend/app/api/routes/monitoring.py`
- `backend/app/main.py`
- `.github/workflows/live-procurement-monitor.yml`
- `frontend/src/components/intel/live-monitoring.tsx`
- `frontend/src/components/layout/app-shell.tsx`
- `docs/LIVE_MONITORING_SETUP.md`
