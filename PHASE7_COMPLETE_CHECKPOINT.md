# Phase 7 — Evidence + Official Context

**Status:** COMPLETE (implementation + integration checkpoint)

## Audit-first result

Phase 7 was completed by auditing the existing SENTRY implementation first and formalizing the already-built evidence/provenance and official-context capability. No duplicate evidence engine or parallel context system was introduced.

## Scope delivered

- Evidence Engine remains the provenance backbone for investigation reasoning.
- Important citations preserve source name, source record, source URL, retrieval time, related tender, document metadata, evidence type, and quality tier where available.
- Evidence ledger de-duplicates records by source identity before packet assembly.
- Deterministic evidence-quality scoring distinguishes primary, corroborating, weak, and unverified evidence.
- Primary procurement documents are distinguished from portal source notices.
- Ephemeral/session-scoped procurement URLs are identified rather than presented as permanent evidence.
- Consolidated Evidence Packet already carries official source URLs, supporting documents, missing evidence, alternative explanations, and manual verification requirements.
- Verified Context Engine uses a curated corpus and a hard allowlist of trusted authorities/domains.
- Trusted retrieval returns guidance as draft context; it is not auto-verified or silently persisted as authoritative law.
- Applicability is evaluated deterministically from retrieved facts where the guidance premise is checkable.
- Unsupported applicability remains explicitly indeterminate rather than inferred.
- Context analysis is read-only and does not alter deterministic risk findings or severity.
- Existing investigation API exposes GET/POST `/api/investigations/context-analysis`.
- Existing `FindingCaseFile` integrates the Procurement Context block with source/authority/applicability presentation.

## Existing validation coverage audited

- `backend/tests/test_verified_context.py`
- `backend/tests/test_trusted_retrieval.py`
- `backend/tests/test_context_applicability.py`
- `backend/tests/test_context_analyzer.py`
- `backend/tests/test_investigation_evidence_packet.py`

These contracts cover deterministic retrieval, trusted-domain allowlisting, provenance preservation, draft-only retrieval, applicability gating, neutral no-guidance behaviour, read-only analysis, evidence verification, and packet assembly.

## Integrity boundaries retained

1. Official Indian procurement sources remain the highest-authority evidence layer for Indian cases.
2. International guidance is clearly classified and is never silently promoted to Indian law.
3. News and other contextual material are not converted into automatic risk merely because they exist.
4. Missing evidence reduces what SENTRY can establish; it does not become a positive finding.
5. A citation alone does not make a finding verified; required evidence must be present for a verified status.
6. Official context can explain or challenge a finding but cannot adjudicate guilt or rewrite the deterministic risk engine.
7. Entity-resolution uncertainty, unsupported bidder-level claims, and unavailable applicability remain explicit uncertainty states.

## Repository integration points

- `backend/app/services/investigation_evidence.py`
- `backend/app/services/investigation_packet.py`
- `backend/app/verified_context/`
- `backend/app/api/routes/investigations.py`
- `frontend/src/components/intel/finding-case-file.tsx`

## Validation note

The repository-level implementation and test contracts were audited from the current `main` branch. The exact current `main` test suite was not executed from this chat session, so this checkpoint does not claim a fresh full-suite pass. Vercel production status is also intentionally not claimed here.

## Next phase

**Phase 8 — Investigation Engine 2.0**
