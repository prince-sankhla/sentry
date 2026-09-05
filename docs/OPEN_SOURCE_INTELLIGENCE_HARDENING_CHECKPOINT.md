# SENTRY — Open-source Intelligence Hardening Checkpoint

## Status
Implemented

## What changed

### Automatic web investigation
The streamed investigation now performs an additive open-source intelligence pass automatically after official procurement retrieval and grounding.

The live investigation trace exposes a dedicated `web_search` step covering:
- current tender / procurement / contract web records;
- historical procurement, tender, contract, audit and investigation context;
- explicit completion counts and a visible statement that context does not affect risk scoring.

The existing deterministic Risk Engine remains unchanged and is not fed generic web or news material.

### Historical/news context separation
`POST /api/web/context-search` now treats context as a separate research surface.

Context may include recognised Indian news coverage and authoritative procurement/oversight material. Captured context is stored with a `context:` query namespace but does not receive a `WebProcurementEvidence` linkage, so it cannot enter the authoritative procurement evidence path or deterministic risk calculation.

### Source-link resilience
Web Evidence cards now prefer a stable SENTRY snapshot link over the original external URL. The snapshot route is backed by the captured database record and is therefore independent of the current session state, expiring query parameters, or a portal restart.

The original source link remains available as the provenance destination, but an investigator can use the preserved SENTRY snapshot during a live demo or later review.

## Current investigation experience

`Investigate → official records → entity resolution → indicators → evidence → grounding → open-source search → historical context → analyst reasoning`

The streamed UI already renders each backend SSE step dynamically, so the new `web_search` stage appears in the investigation progress console with live status text.

## Integrity boundaries

- Open-source reporting is a research lead, not proof of wrongdoing.
- News/context does not directly change SENTRY risk severity or score.
- Authoritative procurement records remain the primary evidential basis.
- Missing or contradictory data stays explicit.
- SENTRY preserves the original URL and retrieval timestamp alongside the captured snapshot.

## Validation note

Repository code was audited and the implementation was committed to the main branch. A fresh full frontend build/lint run and external portal end-to-end verification were not executed from this chat session.
