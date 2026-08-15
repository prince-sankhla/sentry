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
   explanations, and a manual verification checklist.

## Key Features

- **Deterministic investigation pipeline** — entity resolution → precision
  retrieval → integrity indicators → explainable risk assessment (patterns,
  context rules, per-indicator evidence validation).
- **Investigator Review** — every investigation answers three questions:
  evidence supporting the finding, evidence supporting routine procurement,
  evidence still required.
- **Evidence Challenge** — per-finding falsification: evidence-backed benign
  explanations plus the verification questions that would eliminate each one.
- **Verified Context Engine** — pluggable context providers; local verified
  library first, curated trusted-authority guidance second; deterministic
  applicability evaluation before anything is shown.
- **Priority Investigation Queue** — ranks procuring entities in the live
  database by findings, linked records, and evidence completeness, so an
  investigator knows where to start today.
- **Evidence Packet export** — 15-section, court-style HTML document; every
  claim linked to an official source; honest about missing evidence.
- **Finding case files UI** — each finding answers five questions (detected /
  supporting evidence / legitimate explanations / evidence required /
  recommended next investigation) and closes at a fixed, verdict-free position.
- **Optional LLM narration** — a multi-provider chain (Anthropic / OpenRouter /
  OpenAI / Gemini) may *phrase* the summary, gated by a deterministic grounding
  guard; with no key configured the platform runs fully offline and unchanged.

## Architecture Overview

```
                   ┌────────────────────────────────────────────────┐
 Official portals  │                 Backend (FastAPI)              │
 CPPP · GePNIC ×14 │                                                │
 data.gov.in · CAG │  Connectors → Normalized records (PostgreSQL)  │
 GeM · World Bank  │        │                                       │
 ADB · UN · Prozorro        ▼                                       │
                   │  Investigation Engine (deterministic)          │
                   │   entity resolution → precision retrieval      │
                   │   → indicators → Risk Engine V2 (patterns,     │
                   │     context rules, evidence validation)        │
                   │        │                                       │
                   │        ▼                                       │
                   │  Reasoning layer                               │
                   │   Investigator Review · Evidence Challenge     │
                   │   (context plugins) · Evidence Packet          │
                   │        │                                       │
                   │        ▼                                       │
                   │  Verified Context Engine                       │
                   │   context store → trusted retrieval →          │
                   │   Procurement Context Analyzer (applicability) │
                   └────────┬───────────────────────────────────────┘
                            │ REST / SSE
                   ┌────────▼───────────────────────────────────────┐
                   │        Frontend (Next.js + React)              │
                   │  Priority Queue · Investigation Workspace      │
                   │  Finding Case Files · Graph · Evidence Ledger  │
                   │  Evidence Packet export (print → PDF)          │
                   └────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.13, FastAPI, SQLAlchemy, Pydantic v2, Alembic |
| Database | PostgreSQL (psycopg) |
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS, ECharts, Framer Motion |
| Data | Per-portal connectors (NIC CPPP / GePNIC state portals, data.gov.in, CAG, GeM, World Bank, ADB, UN procurement, Prozorro) |
| LLM (optional) | Anthropic SDK / OpenAI-compatible REST / Gemini REST, behind a grounding guard |
| Testing | pytest (300+ backend tests) |

## Project Structure

```
sentry/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # REST + SSE endpoints
│   │   ├── connectors/        # per-portal ingestion (normalized envelope)
│   │   ├── core/              # settings
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # investigation engine, risk engine, reasoning,
│   │   │   └── context_plugins/   #   evidence-challenge context plugins
│   │   ├── verified_context/  # context store, trusted retrieval, analyzer
│   │   └── webintel/          # web-evidence enrichment
│   ├── migrations/            # Alembic
│   ├── scripts/               # data acquisition / reporting CLIs
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/               # Next.js routes (workspace, tenders, graph, …)
│       ├── components/        # dashboard, intel, ui component libraries
│       └── lib/               # typed API client
├── data/                      # raw + seed procurement data (git-tracked demo corpus)
├── docs/                      # engineering constitution, ontology, reports/
└── scripts/                   # repository-level data download/import scripts
```

## Installation

Prerequisites: Python 3.12+, Node.js 20+, PostgreSQL 15+.

```bash
git clone https://github.com/prince-sankhla/sentry.git
cd sentry
cp .env.example .env          # then edit values (at minimum DATABASE_URL)

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

# Frontend
cd ../frontend
npm install
```

## Environment Variables

All variables are documented in [`.env.example`](.env.example). Summary:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | yes | PostgreSQL connection string |
| `APP_ENV` | no | `development` / `staging` / `production` |
| `BACKEND_CORS_ORIGINS` | no | comma-separated allowed origins |
| `NEXT_PUBLIC_BACKEND_URL` | yes (frontend) | backend base URL |
| `LLM_PROVIDER_ORDER`, `LLM_MAX_TOKENS`, `LLM_TIMEOUT_SECONDS` | no | narration chain tuning |
| `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` (+ `*_MODEL`, `*_BASE_URL`) | no | optional narration providers — unset ⇒ fully offline deterministic mode |

## Running Locally

```bash
# 1. Backend API  (http://127.0.0.1:8000, docs at /docs)
cd backend && uvicorn app.main:app --reload

# 2. Frontend     (http://localhost:3000)
cd frontend && npm run dev

# 3. (optional) import procurement data
python scripts/import_cppp.py            # and other scripts/ importers
```

Run the test suites:

```bash
cd backend && python -m pytest -q        # backend
cd frontend && npx tsc --noEmit && npm run build   # frontend typecheck + build
```

## Deployment

SENTRY is a standard FastAPI + Next.js pair:

- **Backend** — any ASGI host (`uvicorn`/`gunicorn` behind a reverse proxy) with
  a PostgreSQL instance; run `alembic upgrade head` on release.
- **Frontend** — `npm run build && npm start`, or any Next.js-compatible host;
  set `NEXT_PUBLIC_BACKEND_URL` to the deployed API.

Container/orchestration manifests are not yet included (see Roadmap).

## Screenshots

> _Placeholder — add screenshots of the Priority Investigation Queue, a finding
> case file, and an exported Evidence Packet._

## Future Roadmap

- Crawl-time archival of primary procurement documents (PDF/A preservation
  store with provenance) — currently documents are identified and linked, not
  stored.
- Phase-3 review workflow for the Verified Context Library (human approval of
  retrieved guidance into permanent verified cards).
- Docker / docker-compose for one-command local setup.
- Broader portal coverage and incremental sync scheduling.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: branch from `main`
(`area/short-description`), keep changes deterministic and tested
(`pytest`, `tsc`), and never commit credentials or scraped personal data.

## License

No license has been selected yet — until one is added, all rights are reserved.
(For an open-source release, add a `LICENSE` file — MIT or Apache-2.0 are the
usual choices for this kind of platform.)
