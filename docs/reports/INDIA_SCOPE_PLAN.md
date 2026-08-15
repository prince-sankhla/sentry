# SENTRY — India-First Scope Plan (Sprint 1, Task 1.2)

**Author:** Data Platform (Principal)
**Date:** 2026-07-11
**Goal:** prepare the repo for an India-first hackathon build — international connectors
disabled by default — **without deleting anything, breaking anything, or changing the
frontend/API/architecture.**

---

## Decision: registry-based classification (NOT physical file moves)

The task allowed either moving connectors into `/connectors/india|international|experimental`
**or** "an equivalent registry-based classification." I chose the **registry-based
classification**, deliberately.

**Why not move files:** the connector registry auto-discovers packages via
`pkgutil.iter_modules` over `app/connectors/*`, and connectors import each other
(state portals reuse the CPPP mapper; several share `common/`). Physically relocating
packages would churn every import path, the discovery walk, and `raw_directory`
resolution — high risk of breakage for zero functional gain. A classification layer
achieves the same scoping with none of that risk and is trivially reversible.

**Result:** every connector stays exactly where it is and stays registered. A thin
classification decides which ones are *enabled by default*. Nothing is removed.

---

## What changed (exactly)

### 1. New file — `backend/app/connectors/classification.py`
A pure, dependency-free classification layer:

- `ConnectorClass` enum — the six audit buckets: `INDIA_PROCUREMENT`,
  `INDIA_OVERSIGHT`, `INDIA_CORPORATE`, `INTERNATIONAL`, `EXPERIMENTAL`, `DEPRECATED`.
- `classify(name)` — maps every connector to one class (state portals `eproc_*` by
  prefix → Indian Procurement; unknown/new connectors default to `EXPERIMENTAL` so
  the India scope is never silently widened).
- `is_enabled_by_default(name)` — India classes are enabled; International and
  Experimental are **disabled by default**.
- `default_enabled_names(...)`, `classification_summary()` — helpers for filtering
  and reporting.

Classification (matches `INDIA_DATA_AUDIT.md`):

| Class | Enabled by default | Connectors |
|---|:--:|---|
| India Procurement | ✅ | `cppp`, `gem`, `eproc_*` (14 state portals) |
| India Oversight | ✅ | `cag` |
| India Corporate | ✅ | *(none yet)* |
| International | ❌ | `world_bank`, `prozorro` |
| Experimental | ❌ | `datagovin`, `adb`, `un_procurement` |
| Deprecated | ❌ | *(none)* |

### 2. Edited — `backend/app/connectors/manager.py` (2 small changes)
`SourceManager.connectors()` — when called with **no explicit source list** (the
default, unscoped live search), it now yields only connectors enabled by default,
then applies the existing India-first ranking:

```python
if not source_names:
    connectors = [c for c in self.registry.all(...) if is_enabled_by_default(c.metadata.name)]
    return sorted(connectors, key=lambda c: source_rank(c.metadata.name))
```

**Only the default path changed.** Explicit `connectors([...])`, `fetchTender`,
`fetchAwards`, `fetchDocuments` with a named source are untouched — a named connector
(including a disabled one) is always honoured.

### Environment overrides (no code change needed to reverse)
- `SENTRY_ENABLE_ALL_SOURCES=1` → enable every connector (pre-Sprint-1 behaviour).
- `SENTRY_ENABLE_INTERNATIONAL=1` → additionally enable International connectors.

---

## Why this breaks nothing (verified)

- **Registry unchanged.** `registry.all()` / `registry.names()` still return all **22**
  connectors, so the connector dashboard, `connector_validation`, `coverage_report`,
  `health`, and the `validators.py` "dashboard count == registry count" assertion all
  keep working. Confirmed: `registry.all()` → 22.
- **Reporting/importers unaffected.** Every importer and report uses
  `discover_connectors().get(name)` (explicit) or `registry.all()` — none rely on the
  `SourceManager` default enumeration.
- **The verified Case #001 is unaffected.** Investigations run in **DB mode**
  (`DatabaseRecordSource`, a Postgres session) and bypass `SourceManager` entirely.
  World Bank data is already imported into Postgres and is read from there, not via
  live connector enumeration. Disabling `world_bank` from *default live search* has
  **zero** effect on the demo.
- **Explicit reachability preserved.** `SourceManager().connectors(['world_bank'])`
  still returns World Bank — nothing is lost, only de-prioritised from the default.
- **Full test suite: 225 passed**, no regressions.

Verification snapshot:
```
DEFAULT enumeration (India-first): 17  -> cppp, gem, cag, eproc_* ×14
international/experimental leaked into default: NONE
explicit ['world_bank'] reachable: ['world_bank']
registry.all(): 22 connectors (reporting intact)
SENTRY_ENABLE_ALL_SOURCES=1 -> 22 connectors
```

---

## Reconciling "international disabled" with "World Bank is the Case #001 dataset"

These do not conflict. "Disabled by default" applies to **live connector
enumeration** (scraping/search when no source is named). Case #001 uses World Bank
data that is **already in the database**, queried directly by the DB executor and
addressable by name. So:

- India-first is honoured: default search is India-only.
- The flagship investigation still runs on the verified World Bank corpus.

If a future flow needs live World Bank search, it either names the source explicitly
or sets `SENTRY_ENABLE_INTERNATIONAL=1`.

---

## What did NOT change
- No frontend. No API routes/schemas. No risk engine, entity resolution, or
  investigation logic. No architecture. No files moved or deleted. No connector code
  behaviour beyond the default-enumeration filter.

## Next step (optional, out of this task's scope)
Surface `classify()` in the connector dashboard so the UI/report can show each
source's class and enabled state — pure additive reporting, no behaviour change.
