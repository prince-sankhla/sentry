# Contributing to SENTRY

Thanks for helping improve procurement oversight tooling. A few ground rules
keep the platform trustworthy.

## Principles

1. **Determinism first.** The investigation engine, indicators, risk scoring,
   and all reasoning layers must stay deterministic and evidence-grounded. An
   LLM may phrase text; it may never decide, score, or invent facts.
2. **Never assert wrongdoing.** SENTRY produces leads and organizes evidence.
   User-facing language must stay verdict-free (see the fixed "current
   position" wording in the workspace and Evidence Packet).
3. **Provenance everywhere.** Every record, document, and guidance card
   carries its source. Don't add data paths that lose citations.

## Workflow

- Branch from `main` using `area/short-description`
  (e.g. `data-platform/recover-state-tenders`, `fix/entity-precision`).
- Keep commits focused; use conventional prefixes where natural
  (`feat:`, `fix:`, `docs:`, `data:`, `chore:`).
- Before opening a PR:
  - `cd backend && python -m pytest -q` — all tests green
  - `cd frontend && npx tsc --noEmit && npm run build`
  - New behaviour needs tests (backend suites live in `backend/tests/`).

## Security & data hygiene

- Never commit credentials, tokens, or `.env` files (`.env.example` only).
- Never commit scraped personal data beyond what official portals publish.
- Respect portal access rules — no session circumvention, no bulk scraping
  outside the connectors' documented behaviour.

## Adding common extension points

- **New procurement context (Evidence Challenge):** one plugin file in
  `backend/app/services/context_plugins/` implementing `ContextPlugin`.
- **New trusted guidance:** extend the curated corpus in
  `backend/app/verified_context/trusted.py` — allowlisted authorities only,
  citations required, plus an applicability evaluator in `applicability.py`
  when the guidance premise is checkable from record facts.
- **New data source:** a connector package under `backend/app/connectors/`
  producing the normalized envelope (see `connectors/base.py`).
