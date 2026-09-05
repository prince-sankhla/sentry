# SENTRY — Web Intelligence & Live Demo Reliability Checkpoint

## Status
**IMPLEMENTED**

## Investigation web-research flow
When an investigation starts with a query, SENTRY now launches a parallel web-intelligence pass alongside the structured procurement investigation.

Research lanes:
- Tender / award / contract history
- Current + past procurement reporting
- Litigation / court / tribunal context
- Audit / vigilance / debarment signals

The UI visibly shows queued, searching, completed and failed lanes, progress, item counts, and retained context cards so the investigator can see that web research is actually running.

## Context boundary
Open-web material is explicitly classified as **context**, not authoritative procurement evidence. Context may:
- corroborate a timeline;
- surface prior reporting or a government statement;
- locate a contract, court or audit document;
- challenge a possible explanation.

Context does **not** alter the deterministic procurement risk assessment and is not treated as proof of wrongdoing.

## Source-session reliability
Each stored web page has a SENTRY-captured database snapshot with retrieval timestamp and SHA-256 hash. The new archive routes serve the captured copy independently of the live source page, so a source session expiring or a page changing does not erase the investigation trail.

Every web EvidenceCard can derive a durable SENTRY snapshot link from its original source URL.

## Search / storage architecture
- Existing DuckDuckGo HTML search provider is used for discovery.
- Authoritative-source and content-relevance gates run before storage.
- Context searches store `WebEvidence` without creating `WebProcurementEvidence` links.
- Existing procurement evidence path remains unchanged.

## Integrity constraints
- News is contextual, not proof.
- Missing or unavailable pages are not converted into positive evidence.
- A source URL remaining reachable is not required for the captured snapshot to remain reviewable.
- Risk Engine V2 remains the authoritative deterministic screening layer.
- Indian procurement records remain distinct from international methodology/context.

## Key implementation files
- `backend/app/api/routes/web_archive.py`
- `backend/app/api/routes/web_context.py`
- `frontend/src/components/intel/investigation-web-research.tsx`
- `frontend/src/components/intel/evidence-card.tsx`
- `frontend/src/app/investigate/page.tsx`
- `backend/app/main.py`

## Validation note
A fresh full frontend/backend test suite was not executed from the chat environment after these edits, so no new CI or deployment success is claimed here.
