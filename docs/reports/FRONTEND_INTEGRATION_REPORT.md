# SENTRY — Frontend Integration Report

> **Mandate:** everything the backend investigation engine knows, the investigator
> must be able to see. Backend, investigation logic, layout, and animations are
> **frozen**. This audit maps every field the Investigation API returns to where
> it renders in the workspace, and closes the gaps by reusing existing components —
> no new APIs, no layout redesign, no duplication.
>
> **Method:** the backend Pydantic schemas are treated as the source of truth —
> `investigation_risk.py`, `investigation_reasoning.py`, `investigation_executor.py`.
> Every field was traced to a concrete render site in `frontend/src` (or confirmed absent).

---

## 1. Verdict on the 12 required items

| # | Item | Backend field(s) | Displayed? | Where | Trust |
|--:|---|---|:--:|---|:--:|
| 1 | **Typologies** | `risk_assessment_v2.indicators[]`, `reasoning.findings[]` | ✅ | "The finding — Risk indicators" | ✅ |
| 2 | **Severity** | `indicator.severity`, `reasoning.risk_level` | ✅ | Severity pills + verdict header badge | ✅ |
| 3 | **Confidence** | `reasoning.confidence`, `confidence_assessment.dimensions[]` | ✅ | Verdict header, AI panel meter, GroundingCard, Confidence-assessment card (8 dimensions) | ✅ |
| 4 | **Evidence Strength** | `indicator.evidence_status`, `grounding`, `citation.quality_tier`/`quality` | ✅ | Indicator `status` chip, Grounding card, Evidence Ledger ★-tier | ✅ |
| 5 | **Missing Evidence** | `analyst_report.missing_evidence[]`, `indicator.required_evidence[]` | ✅ | "Missing evidence" card **+ per-flag "To confirm, obtain" (newly exposed)** | ✅ |
| 6 | **Alternative Explanations** | packet `BENIGN_EXPLANATIONS` rubric | ✅ (packet) | Evidence Packet export — §12 of the dossier | ✅ |
| 7 | **Manual Verification Checklist** | packet `VERIFICATION` rubric | ✅ (packet) | Evidence Packet export — §13 of the dossier | ✅ |
| 8 | **Investigation Timeline** | `package.timeline[]`, `analyst_report.timeline_analysis` | ✅ | "Procurement timeline" + Timeline analysis card | ✅ |
| 9 | **Evidence Sources** | `reasoning.evidence_ledger[]` | ✅ | Evidence Ledger (tier, ★, confidence, dates, Cite) | ✅ |
| 10 | **Official URLs** | `citation.source_url`, `tender.metadata.source_url` | ✅ | Ledger "Original" **+ per-flag "View official record" (prior commit)** | ✅ |
| 11 | **Risk Justification** | `reasoning.risk_rationale[]`, `indicator.reason`/`context_notes`, `risk_assessment_v2.summary` | ✅ | AI-panel "Analyst reasoning" chips, indicator `reason`, **`context_notes` + assessment `summary` (newly exposed)** | ✅ |
| 12 | **Investigation Summary** | `reasoning.executive_summary` | ✅ | AI Investigation panel | ✅ |

**All 12 items are now visible to the investigator.** Items 5, 10, and 11 were
strengthened this session; the rest were already surfaced by the existing components.

---

## 2. Gaps found and closed this session

Three fields were flowing in the `/stream` report payload but silently **dropped**
by the frontend (confirmed: 0 references outside `lib/api.ts`). All are now surfaced
**in place** on the existing "Risk indicators" section — reusing its card and text
styles, adding no panel, no API, no layout change, no duplicate of existing data.

| Field | What it is | How it's now shown | Why it increases trust |
|---|---|---|---|
| `RiskIndicatorV2.context_notes[]` | The engine's deterministic context rules — *why* a severity was held/capped/suppressed | Muted bullet lines under each flag | Shows the engine *reasons about context*, not just fires |
| `RiskIndicatorV2.required_evidence[]` | The evidence the validator needs to confirm this flag | A "To confirm, obtain …" chip row per flag | Honest, per-flag missing evidence — the opposite of a black box |
| `RiskIndicatorV2.review_note` | Human-review guidance | Tooltip on the "Requires review" badge | Names the next human action |
| `risk_assessment_v2.summary` | The engine's one-line justification for the overall verdict | Lead sentence above the indicator grid | A plain-language "here's why, in one line" |

All render **conditionally** (only when the backend provides a value), so they
degrade safely and **any future backend enrichment appears automatically** — which
is the whole point of this mandate.

---

## 3. Full field-by-field coverage (source of truth → render site)

**`InvestigationPackage`** (`investigation_executor.py`)
- `records[]` (tender, companies, awards, documents, metadata.source_url) → ✅ Tender records / Awards sections; source_url now on flags + ledger
- `timeline[]` → ✅ Procurement timeline
- `indicators[]` (legacy) → ✅ fallback in Risk indicators
- `canonical_companies[]` → ✅ Resolved companies
- `risk_assessment_v2` → ✅ (see below)
- `graph` → ✅ Investigation graph + full-screen
- `resolved_entities` → ✅ Entity candidates panel

**`RiskAssessmentV2`** (`investigation_risk.py`)
- `overall_severity` / `overall_score` → ✅ verdict header + severity pills
- `indicators[]` → ✅ Risk indicators
  - `name, severity, score, evidence_status, reason, supporting_records, review_required` → ✅
  - `context_notes, required_evidence, review_note` → ✅ **(newly exposed)**
  - `confidence` (per-indicator), `base_severity`, `status`, `category` → ⚠️ not individually shown (severity+score cover it; low value)
- `summary` → ✅ **(newly exposed)**
- `confidence` (`RiskConfidence.explanation`) → ⚠️ engine's own confidence explanation not shown (reasoning-level confidence + explanation *is* shown)
- `patterns[]` → ❌ not rendered (empty for CASE #001; see §5)
- `explainability[]` → ❌ not rendered (deep audit trail; see §5)
- `disclaimer` → ⚠️ workspace shows an equivalent oversight disclaimer (paraphrase); not duplicated

**`InvestigationReasoning`** (`investigation_reasoning.py`)
- `executive_summary` → ✅ AI panel
- `risk_level` → ✅ header + AI panel
- `risk_rationale[]` → ✅ AI panel "Analyst reasoning"
- `confidence` → ✅ header, AI panel, grounding
- `findings[]` (+ citations, verification, occurrences) → ✅ Findings & evidence (citations open by default)
- `recommendations[]` → ✅ Recommendations
- `follow_ups[]` → ✅ Suggested investigations
- `evidence_ledger[]` → ✅ Evidence Ledger
- `grounding` → ✅ Grounding card + AI panel
- `analyst_trace[]` → ✅ Analyst trace
- `prior_investigations[]` → ✅ AI memory
- `analyst_report` (patterns, buyer/supplier/award/timeline, contradictions, **missing_evidence**, confidence_assessment) → ✅ AnalystReportSections (all sub-sections)
- `generated_by / provider / model / fallback_reason` → ✅ Provider badge + AI panel provenance line
- `integrity_assessment` (weighted factors) → ❌ not rendered / not typed in api.ts (see §5)
- `evidence_packet` (consolidated bundle) → ⚠️ overlaps Evidence Ledger + Grounding; not separately rendered (would duplicate)
- `insufficient_evidence` → ✅ Insufficient-evidence empty state

---

## 4. Items 6 & 7 — why they live in the packet, not inline

Alternative explanations and the manual verification checklist are **not part of the
`/stream` payload** — they are deterministic rubrics assembled only by the Evidence
Packet builder (`investigation_packet.py`, §12–§13 of the 15-section dossier). They
are fully visible to the investigator via the **"Export evidence packet"** button
(an existing capability, one click). Rendering them inline would require duplicating
packet content in the workspace, which the mandate forbids ("do not duplicate"). They
are therefore counted as **displayed (via packet)** and left there by design.

---

## 5. Deliberately-deferred fields (documented, not force-fitted)

These backend fields have **no** frontend render. Exposing them well would mean a new
panel or a new type binding — which crosses "do not add features / do not redesign
layout." They are recorded here as the honest remaining surface, with a recommendation,
rather than bolted on:

| Field | Why deferred | Recommendation |
|---|---|---|
| `integrity_assessment` (weighted `factors[]` with weight/strength/contribution) | Not typed in `api.ts`; a proper render is a new weighted-factors panel. Its qualitative twin — `risk_rationale` — is already shown. | **Top follow-up** if a "risk justification" panel is later in-scope. Highest-value deferred field. |
| `risk_assessment_v2.patterns[]` | Empty for CASE #001 (patterns need cross-indicator combinations / entity data). | Add a "Patterns" card (mirror of the analyst PatternsCard) when the engine starts emitting them. |
| `risk_assessment_v2.explainability[]` | Per-indicator audit trail (base→rule→evidence→context→score). Deep/technical; overlaps context_notes now shown. | Expose behind a per-flag "audit trail" disclosure if judges ask "show the math." |
| `evidence_packet` (structured) | Overlaps Evidence Ledger + Grounding totals. | Leave — rendering it duplicates existing surfaces. |
| `RiskConfidence.explanation`, per-indicator `confidence` | Reasoning-level confidence + explanation already shown. | Low value; skip. |

None of these block the demo or hide anything the current CASE #001 finding depends on.

---

## 6. Verification

| Gate | Result |
|---|---|
| `tsc --noEmit` | ✅ clean |
| `next build` | ✅ exit 0 |
| Commit | ✅ `718ddee` (this change) · builds on `aa1576d` |

**CASE #001 field-population check (backend confirmed, read-only):** the exposed
fields are genuinely populated for the Dharmagarh flags — every indicator carries
`required_evidence` (`risk_engine.py:478`) and `context_notes` (`:479`), and `summary`
is always set (`:504`). So the new "To confirm, obtain", context bullets, and the
assessment lead sentence **will render** on `contract_fragmentation` and
`missing_award_data`.

**Honest limitation:** the full stack cannot be run in this environment (the backend
needs Postgres with the imported Odisha data, absent from this checkout). Verification
is therefore a clean typecheck + production build + confirmation that (a) the backend
populates the fields and (b) every new render is conditional and null-safe. Live
click-through remains the pre-flight item on the demo machine.

**Note on backend drift (proof the integration works):** the risk engine now defines
`missing_award_data` at base severity **"low"** (`risk_engine.py:103`), where
`CASE_001.md` recorded "medium." The frontend renders whatever the backend returns —
so this backend evolution is *already* reflected without any frontend change. That is
exactly the outcome this mandate asks for.

---

## 7. Bottom line

Everything the investigation engine currently knows and returns in its live payload is
now visible to the investigator — including the per-flag reasoning and per-flag missing
evidence that were previously dropped. New backend fields that arrive in existing
structures (indicator context, required evidence, assessment summary, timeline events,
analyst sections) will surface automatically. The only backend knowledge not shown
in-workspace is (a) the packet-only rubrics, which are one click away via export, and
(b) a small set of deep/weighted structures deferred to respect the "no new panel /
no redesign" freeze — each documented above with a recommendation.

*Backend, investigation logic, layout, and animations were not modified. Only the
connection between the two was tightened.*
