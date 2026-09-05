# SENTRY — Web Intelligence Demo Hardening Checkpoint

## Status
**COMPLETE**

## Problem addressed
The investigation demo needed to behave like an actual research operation rather than a static risk report. Source URLs from government/public portals can also be session-bound, changed, or expired during a live presentation.

## Implemented / verified

### 1. Durable SENTRY source snapshots
- Existing `/api/web/archive/{evidence_id}` serves a captured SENTRY copy from the database.
- Existing `/api/web/archive/by-url` serves the latest captured copy for a source URL.
- Web evidence cards expose the SENTRY snapshot before the original source, so an expired session on the originating website does not erase the captured investigation trail.
- Snapshot pages retain retrieval time and SHA-256 provenance.

### 2. Open-web investigation lanes
The investigation page already launches four visible research lanes alongside the procurement investigation:
- Tender / award / contract history
- Current + past procurement reporting
- Litigation / court / tribunal context
- Audit / vigilance / debarment signals

These lanes now have a working backend endpoint:
`POST /api/web/context-search`

The endpoint uses the existing search provider, crawler, authority gate, relevance gate, capture store, and contextual classification pipeline.

### 3. Context is deliberately separate from proof
Historical news, audit, litigation, compliance, and other open-web material is stored with a `context:` namespace and is **not** promoted to `WebProcurementEvidence`. It therefore remains outside the deterministic procurement risk calculation.

The investigation UI labels this material as contextual intelligence, not procurement proof.

### 4. Automatic web search during investigations
The streamed investigation pipeline already runs:
- primary procurement web search for current tender / contract material;
- historical/context search for tender, contract, procurement, news, audit, and investigation history;
- explicit SSE progress messages while those web passes execute.

The visible investigation UI already renders cinematic pipeline progress, including rotating research messages such as portal retrieval, source selection, normalization, grounding, and analyst reasoning. The newly restored context-search endpoint makes the dedicated parallel web research surface operational instead of decorative.

## Demo integrity boundaries
- An original source can still become unavailable; the SENTRY-captured snapshot remains the preferred review copy when available.
- Contextual web material is not treated as an authoritative procurement finding.
- News allegations are contextual signals, not proof.
- Open-web material does not directly modify deterministic risk scoring.
- No claim is made that a government portal is continuously streamed in real time by this web research layer.

## Validation note
This checkpoint is based on repository audit and code integration. A fresh local full test/build run was not executed from the GitHub connector session, so no new CI/build-green claim is made here.
