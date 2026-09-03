# SENTRY — Procurement Integrity Investigation Platform

SENTRY is a deterministic investigation platform for public-procurement oversight.
It ingests official government procurement records, screens them with rule-based
integrity indicators, organizes the evidence the way a senior investigator would —
what supports a finding, what argues against it, and what is still missing — and
exports a print-ready, fully cited Evidence Packet.

SENTRY is an oversight tool. It surfaces **leads for human review**; it never
declares wrongdoing, and every figure it shows traces to an official source record.

---

## Problem Statement

Public-procurement data is published, but rarely *investigable*. Records are
scattered across portals, anomaly detection tools behave like black boxes, and
"risk scores" without evidence force investigators to reassemble the story by
hand. Tools that only accuse — without surfacing the routine-procurement
explanations — produce false positives that waste investigator time and erode
trust.

## Solution

SENTRY treats investigation as evidence organization, not verdict generation:

1. **Ingest** official procurement records through per-portal connectors into a
   normalized schema with full provenance (source URL, retrieval time, documents).
2. **Screen** deterministically: rule-based indicators (single bidder, contract
   fragmentation, award clustering, repeat winner, …) combined into named
   patterns by an explainable risk engine — no model decides risk.
3. **Challenge**: every finding is immediately paired with the evidence-backed
   legitimate explanations that could also explain it, and the exact evidence
   that would distinguish routine procurement from procurement requiring
   escalation.
4. **Contextualize**: a Verified Context Engine retrieves procurement guidance
   from trusted authorities only (GFR, CVC, CAG, OCP, World Bank, OECD, ADB) and
   shows it only when the retrieved facts actually support its applicability.
5. **Deliver**: an investigator workspace of per-finding case files, and a
   self-contained Evidence Packet (print → PDF) with citations, alternative
   explanations, verification questions, and an auditable analyst trace.

---

## Production deployment

The production deployment uses Next.js for the SENTRY frontend and FastAPI on Vercel Python functions for the API layer, with Neon PostgreSQL as the database.
