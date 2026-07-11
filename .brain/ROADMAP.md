# SENTRY Roadmap — v1.0 (LOCKED)

> Status: **LOCKED** as of 2026-07-11.
> Layers 1–3 are permanent. Layer 4 is adaptive (priorities locked, details flexible).
> No architecture discussions until the first verified finding + evidence packet exists.

---

## North Star

**SENTRY is not built to detect corruption. It is built to produce defensible, evidence-backed procurement findings that investigators can verify and act upon.**

---

## Layer 1 — Constitution (Permanent)

Mission: Build the world's most trusted evidence-centric procurement intelligence platform.

Principles:
1. AI never declares corruption.
2. Deterministic software performs investigations.
3. Evidence before conclusions.
4. Every finding must be reproducible.
5. Raw data is immutable.
6. Every conclusion links to source evidence.
7. Human investigator is always the final authority.

---

## Layer 2 — Stable Architecture (Stable)

```
Public Sources
      ↓
Acquisition
      ↓
Raw Data Lake
      ↓
Normalization (OCDS)
      ↓
Entity Resolution
      ↓
Canonical Entity Store
      ↓
Knowledge Graph
      ↓
Typology Library
      ↓
Risk Assessment
      ↓
Evidence Validation
      ↓
Investigation Workspace
      ↓
Evidence Packet
      ↓
LLM Narrative
```

No redesign without a compelling reason.

---

## Layer 3 — Engineering Philosophy (Permanent)

### Definition of Done

- ❌ Code compiled
- ❌ Feature completed
- ❌ UI finished
- ✅ **Verified evidence-backed finding produced**

Every sprint is judged by this metric.

### Weekly Rule

Every sprint starts with one question:

> Does this sprint improve our ability to produce a better evidence-backed finding?

If the answer is "No, but it makes the architecture cleaner" — it waits.

### Demo Rule (Constitution-level)

Every demo follows the same flow:

```
Real Procurement Data
        ↓
Investigation
        ↓
Risk Flag
        ↓
Evidence Timeline
        ↓
Official Source PDF
        ↓
Evidence Packet Export
        ↓
AI Summary (optional)
```

Judges never see architecture first. They see the finding first.

---

## Layer 4 — Execution Roadmap (Adaptive)

### Sprint 1 — Vertical Slice (Highest Priority)

Goal: End-to-end working investigation.

Deliverables:
- One portal (best available data after audit)
- Raw ingestion
- OCDS normalization
- Basic ER
- 3–5 deterministic typologies
- One verified finding
- One evidence packet
- Working demo

**Success criterion: a judge can click from a finding to the official source document.**

### Sprint 2 — Data Expansion

Only after Sprint 1 succeeds. More records, more states, better normalization, better quality. Target clean, usable coverage — not arbitrary record counts.

### Sprint 3 — Entity Resolution Validation

Measured ER, not "better ER":
- 100–200 manually labeled pairs (hackathon)
- Precision / Recall / F1
- Later: 500+ pairs for enterprise evaluation

### Sprint 4 — Typology Library

Start with:
- Shared infrastructure
- Single bidder
- Win concentration
- Short tender window
- Award before close

Each typology must include: rule, evidence required, false-positive conditions, references (where applicable).

### Sprint 5 — Real Investigation Sprint

1 verified finding → 3 verified findings → 10 verified findings. Every finding manually reviewed.

### Sprint 6 — Evidence Packets

Every investigation exports: timeline, evidence, documents, sources, typologies triggered, methodology, AI summary. This is what users actually consume.

### Sprint 7 — Demo Polish

No new features. Only: faster UX, better visuals, offline demo, one-click export, LLM On/Off toggle, stable presentation.

---

## Enterprise Roadmap (After Hackathons)

Only then: more connectors, more typologies, case management, collaboration, alerts, monitoring, APIs.

---

## Things We Explicitly Will NOT Build Yet

- RAG
- AI agents
- Multi-agent workflows
- Chatbot
- Ontology V2
- Knowledge Graph V3
- Recommendation AI

Until real investigations prove the platform.
