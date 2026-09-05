# Phase 1 — Investigation-First Frontend Checkpoint

**Status:** Active / frontend polish in progress

## Current checkpoint

The investigation-first frontend pass is now centered on the investigator workflow rather than generic dashboard navigation.

### Completed surfaces

- Command Center — investigation-oriented headline metrics, review-signal distribution, priority entry points and reasoning status.
- Investigation Workspace entry — verified-entity-first launch, four-stage investigation flow, evidence standard, source/provenance expectations and latest procurement entry points.
- Investigation execution view — live streamed pipeline, entity-resolution state, investigation replay and result assembly.
- Relationship Investigation — connected buyers, suppliers, tenders, awards, indicators, documents and evidence.
- Buyer Intelligence — entity-first lookup and investigation entry.
- Tender Intelligence — lifecycle, buyer, awards, documents, benchmark context and evidence limitations.
- Award Records / Supplier Records / Reports — terminology and empty/error states aligned to evidence-aware review language.
- Navigation — grouped around Intelligence, Records, Analysis and System with India-scope operational status.

## Product language guardrails

SENTRY UI must preserve these distinctions:

- Review signals are prioritisation leads, not determinations of misconduct.
- Missing bidder-level information is reported as unavailable; bidder participation is never inferred from winner-only award data.
- Evidence completeness is distinct from truth probability or misconduct likelihood.
- Indian authoritative procurement sources take precedence for Indian case evidence.
- International methodology or contextual material is not presented as Indian law.
- Source provenance remains visible wherever SENTRY presents an investigative claim.
- AI narrative remains source-grounded and secondary to deterministic evidence and human review.

## Verification

Latest frontend checkpoint commit before this documentation checkpoint:

`024df3721d64d5ec67a7d31dd6b6c6e915f8fa21` — `Polish investigation workspace entry experience`

Vercel status for that commit: **success**.

## Next implementation target

Continue polishing the post-run Investigation Results surface so the first screen an investigator sees after execution has a clear hierarchy:

1. subject + investigation status,
2. principal review lead(s),
3. evidence completeness / provenance,
4. corroboration and competing explanations,
5. relationship and timeline context,
6. analyst next actions / human decision boundary.

No new backend inference should be introduced as part of this frontend phase.
