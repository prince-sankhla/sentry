# Engineering Audit Report

# Executive Summary

The SENTRY Investigation Workspace suffers from a critical architectural disconnect. The backend's comprehensive `InvestigationPackage` is only partially populated due to unimplemented modules in the `InvestigationExecutor` and a mapping issue in the `InvestigationPlanner`. Simultaneously, the frontend completely bypasses the `InvestigationPackage`, opting for a legacy multi-API fetching strategy. This results in an inconsistent data flow and the observed "0 tenders, 0 awards, 0 companies, 11 web pages" UI state, as the web evidence is fetched through a separate, non-integrated channel.

# Investigation Execution Flow

This report traces the complete execution flow from `InvestigationPlanner.build_plan()` to the final API response returned to the frontend, identifying data flow, transformations, losses, unfinished modules, and conditions for empty results.

---

### 1. InvestigationPlan Creation

**Starting Point:** User initiates an investigation (e.g., via `/api/investigations/plan` endpoint).

**File:** `backend/app/api/routes/investigations.py`
**Class:** N/A (FastAPI router)
**Function:** `plan_investigation` (lines 9-14)
**Input:** `InvestigationPlanRequest` (e.g., `query="Tata"`, `source_names=None`)
**Output:** `InvestigationPlan`
**Returned object:** `InvestigationPlan`
**Important fields:** `query`, `investigation_type`, `connectors`, `modules`, `steps`
**Next function called:** `InvestigationPlanner().build_plan()`

---

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `build_plan` (lines 72-91)
**Input:** `query` (str), `source_names` (list[str] | None)
**Output:** `InvestigationPlan`
**Returned object:** `InvestigationPlan` (fully constructed)
**Next function called:**

1. `_clean_query()` (internal, for query normalization)
2. `detect_type()`
3. `_select_connectors()`
4. `_build_steps()`

---

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `detect_type` (lines 93-118)
**Input:** `query` (normalized string, e.g., "tata")
**Output:** `tuple[InvestigationType, float]` (e.g., ("company", 0.45))
**Returned object:** `InvestigationType` and `confidence` score
**Data transformation:** Query is lowercased. Scores are assigned based on keywords.
**Next function called:** None

---

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_select_connectors` (lines 120-126)
**Input:** `source_names` (list[str] | None, typically `None` from `plan_investigation`)
**Output:** `list[str]` (e.g., `["cppp", "prozorro", "world_bank"]`)
**Returned object:** `list[str]` containing actual registered connector names.
**Next function called:** `self.source_manager.connector_names()`

---

**File:** `backend/app/connectors/manager.py`
**Class:** `SourceManager`
**Function:** `connector_names` (lines 69-70)
**Input:** None
**Output:** `list[str]`
**Returned object:** `list[str]` (e.g., `["cppp", "prozorro", "world_bank"]`)
**Next function called:** `self.registry.names()`

---

**File:** `backend/app/connectors/registry.py`
**Class:** `ConnectorRegistry`
**Function:** `names` (lines 28-29)
**Input:** None
**Output:** `list[str]`
**Returned object:** Sorted list of registered connector names (e.g., `["cppp", "prozorro", "world_bank"]`)
**Data Source:** `self._connector_classes` dictionary, populated during `discover_connectors()` (called on module import).
**Next function called:** None

---

**Back to `backend/app/services/investigation_planner.py`**
**Class:** `InvestigationPlanner`
**Function:** `_build_steps` (lines 128-149)
**Input:**

- `query`: "tata"
- `investigation_type`: "company"
- `modules`: `MODULE_ORDER["company"]` (e.g., `["company_connectors", "awards", "tenders", "suppliers", "buyers", "graph", "timeline", "procurement_intelligence", "evidence"]`)
- `connectors`: `["cppp", "prozorro", "world_bank"]` (from `_select_connectors`)
  **Output:** `list[InvestigationPlanStep]`
  **Returned object:** A list of `InvestigationPlanStep` objects.
  **Important fields:** `step.connectors`. This is where `step_connectors = connectors if module in CONNECTOR_MODULES else []` is evaluated.
- For `module="company_connectors"`, `step.connectors` becomes `["cppp", "prozorro", "world_bank"]` because "company_connectors" is in `CONNECTOR_MODULES`.
- For other modules like "awards", "tenders", "suppliers", "buyers", "graph", "timeline", "procurement_intelligence", "evidence", their `step.connectors` list becomes `[]` because they are NOT in `CONNECTOR_MODULES`.
  **Data transformation:** Maps a list of module names to `InvestigationPlanStep` objects, assigning relevant connectors based on `CONNECTOR_MODULES`.
  **Next function called:** None (returns to `build_plan`)

---

### 2. InvestigationPlan Execution

**File:** `backend/app/api/routes/investigations.py`
**Class:** N/A (FastAPI router)
**Function:** `execute_investigation` (lines 17-25)
**Input:** `InvestigationExecutionRequest` (contains the `InvestigationPlan` from `plan_investigation`)
**Output:** `InvestigationExecutionRequest` (with `package` populated)
**Returned object:** `InvestigationExecutionRequest`
**Next function called:** `InvestigationExecutor().execute(request)`

---

**File:** `backend/app/services/investigation_executor.py`
**Class:** `InvestigationExecutor`
**Function:** `execute` (lines 39-48)
**Input:** `request: InvestigationExecutionRequest`
**Output:** `InvestigationPackage`
**Returned object:** `InvestigationPackage` (populated with `step_results` and `records`).
**Next function called:** `self._execute_step()` for each step in `request.plan.steps`.

---

**File:** `backend/app/services/investigation_executor.py`
**Class:** `InvestigationExecutor`
**Function:** `_execute_step` (lines 50-163)
**Input:**

- `pkg: InvestigationPackage` (mutable object being built)
- `step: InvestigationPlanStep` (current step from the plan)
- `limit_per_connector: int`
  **Output:** `InvestigationStepResult`
  **Returned object:** `InvestigationStepResult`
  **Important fields:**
- `step.module`: Determines the logic path.
- `step.connectors`: The list of connector names to iterate over for search.

**Execution Path for Procurement Connectors (e.g., `step.module = "company_connectors"`):**

1. **Condition Check:** `if step.module in {"company_connectors", "tender_connectors", "buyer_connectors", "source_connectors"}:` (Line 78) - This condition is **TRUE** for "company_connectors".
2. **Connector Iteration:** `for connector_name in step.connectors:` (Line 79)
   - `step.connectors` will be `["cppp", "prozorro", "world_bank"]` (from `InvestigationPlanner._build_steps`).
   - The loop will iterate three times, with `connector_name` being "cppp", then "prozorro", then "world_bank".
3. **SourceManager Search:** `records = self.source_manager.search(...)` (Line 80)
   - `query`: `step.inputs["query"]` (e.g., "tata")
   - `source_names`: `[connector_name]` (e.g., `["world_bank"]`)
   - `limit`: `limit_per_connector`
4. **Record Normalization & Appending:** The loop `for record in records:` (Line 86) then iterates over the `NormalizedProcurementRecord` objects returned by `self.source_manager.search()`.
   - Each `NormalizedProcurementRecord` is transformed into an `InvestigationProcurementRecord` (Lines 87-159).
   - `pkg.records.append(pkg_record)` (Line 160) - adds the transformed record to the `InvestigationPackage`.
   - `step_result.records_added += 1` (Line 161) - updates count.

**Execution Path for Other Modules (e.g., "awards", "tenders", "evidence"):**

1. **Condition Check:** `if step.module in {"company_connectors", "tender_connectors", "buyer_connectors", "source_connectors"}:` (Line 78) - This condition is **FALSE** for modules like "awards", "tenders", "evidence".
2. **Data Loss/Unfinished Module:** The code then falls through to the "Placeholder for other modules" section (Lines 163-165).
   ```python
           # Placeholder for other modules
           # TODO: Implement logic for other modules (graph, timeline, entity_resolution, etc.)
   ```

   - This explicitly marks these modules as **unfinished**.
   - Data for these modules (e.g., direct awards/tenders if they were to be fetched, or web evidence) is **NOT** processed or added to `pkg`.

---

**File:** `backend/app/connectors/manager.py`
**Class:** `SourceManager`
**Function:** `search` (lines 37-47)
**Input:** `query` (str), `source_names` (list[str] | None), `limit` (int)
**Output:** `list[NormalizedProcurementRecord]`
**Returned object:** A list of `NormalizedProcurementRecord`.
**Next function called:** `self.connectors(source_names)` and `connector.search()` on each.

---

**File:** `backend/app/connectors/base.py`
**Class:** `FileBackedSourceConnector`
**Function:** `search` (lines 148-168)
**Input:** `query` (str, e.g., "tata"), `limit` (int)
**Output:** `list[NormalizedProcurementRecord]`
**Returned object:** A list of `NormalizedProcurementRecord` objects that match the query.
**Next function called:**

1. `self._iter_raw_records()`
2. `self.normalize(raw_record)` (implemented by concrete connectors like `WorldBankSourceConnector`)
3. `self._matches(record, normalized_query)`

---

**File:** `backend/app/connectors/world_bank/connector.py` (example concrete connector)
**Class:** `WorldBankSourceConnector`
**Function:** `normalize` (lines 26-36)
**Input:** `raw_record: dict[str, Any]` (raw JSON content of a World Bank file)
**Output:** `NormalizedProcurementRecord`
**Data transformation:** Maps raw JSON data into the standardized `NormalizedProcurementRecord` schema.
**Next function called:** `map_notice()` (from `mapper.py`)

---

**File:** `backend/app/connectors/base.py`
**Class:** `FileBackedSourceConnector`
**Function:** `_matches` (lines 206-218)
**Input:** `record: NormalizedProcurementRecord`, `query: str`
**Output:** `bool`
**Returned object:** `True` if a match is found, `False` otherwise.
**Fields searched:**

- `record.tender.reference_number`
- `record.tender.title`
- `record.tender.description`
- `record.tender.procuring_entity`
- `company.name` (for each company in `record.companies`)
- `company.registration_number` (for each company in `record.companies`)
  **Search characteristics:**
- Case-insensitive (`.casefold()`)
- Substring search (`query in haystack`)

---

### 3. Final API Response

**File:** `backend/app/api/routes/investigations.py`
**Class:** N/A (FastAPI router)
**Function:** `execute_investigation` (lines 17-25)
**Input:** `request: InvestigationExecutionRequest` (after `executor.execute` has run)
**Output:** `InvestigationExecutionRequest`
**Returned object:** `InvestigationExecutionRequest` containing the `InvestigationPackage` (which has `plan`, `records`, `entities`, `evidence`, `timeline`, `graph_seeds`, `step_results`).

---

### Unfinished Modules & Placeholders

The `InvestigationExecutor._execute_step` (lines 163-165) explicitly contains:

```python
        # Placeholder for other modules
        # TODO: Implement logic for other modules (graph, timeline, entity_resolution, etc.)
```

This means that for any `step.module` that is _not_ in `{"company_connectors", "tender_connectors", "buyer_connectors", "source_connectors"}`, the `InvestigationPackage`'s `entities`, `evidence`, `timeline`, and `graph_seeds` lists will remain **empty** unless populated by other means (which are not part of this core investigation execution flow).

### Conditions for Empty Investigation Results

1.  **No matching procurement data in connectors:** If `SourceManager.search()` (ultimately `FileBackedSourceConnector.search()` and its `_matches` method) finds no records in the raw data that match the `query`, then `pkg.records` will be empty. (Verified: "Tata" returns 0 records from World Bank connector).
2.  **Mismatched `MODULE_ORDER` and `CONNECTOR_MODULES`:** If an `InvestigationPlanStep.module` (e.g., "awards", "tenders") is in `MODULE_ORDER` but not in `CONNECTOR_MODULES`, then `step.connectors` for that step will be `[]` (empty). This causes `SourceManager.search` to be called with an empty `source_names` list, resulting in no records being fetched.
3.  **Unimplemented Modules in Executor:** Modules like "graph", "timeline", "entity_resolution", and "evidence" are defined in the `InvestigationPlan`'s `MODULE_ORDER` but their processing logic in `InvestigationExecutor._execute_step` is a `TODO`. This means even if data _could_ be generated for these, it's not currently added to the `InvestigationPackage`.

### Data Loss/Unused Fields

- **Web Evidence:** The audit confirms that web evidence (CarWale, ZigWheels, Blogs) does **not** enter the `InvestigationPackage` via this `InvestigationExecutor` pipeline. The `InvestigationPackage.evidence` list remains empty from this flow. The frontend obtains this data from a _separate_ API call to `/api/web-evidence/search`.
- **`InvestigationPackage` data fields:** Because many modules (like "graph", "timeline", "entity_resolution", "evidence") are `TODO`s in the executor, the `InvestigationPackage` fields corresponding to `entities`, `evidence`, `timeline`, and `graph_seeds` are **not populated** by this execution flow and remain empty.

---

# Frontend ↔ Backend Integration Audit

### Frontend-Backend Integration Table

| Frontend Page                                  | API Route                           | Service                                                            | Executor                                      | Database / Connector                                                   | Response Rendered In                                               |
| :--------------------------------------------- | :---------------------------------- | :----------------------------------------------------------------- | :-------------------------------------------- | :--------------------------------------------------------------------- | :----------------------------------------------------------------- |
| `InvestigationWorkspace` (homepage renders it) | `POST /api/investigations/plan`     | `InvestigationPlanner`                                             | N/A                                           | N/A                                                                    | Used as input for `executeInvestigation`                           |
| `InvestigationWorkspace`                       | `POST /api/investigations/execute`  | `InvestigationExecutor`                                            | `SourceManager` / `FileBackedSourceConnector` | `WorldBankSourceConnector`, `ProzorroSourceConnector`, `CPPPConnector` | `investigation.investigationPackage` (ignored by current UI logic) |
| `InvestigationWorkspace`                       | `GET /api/tenders`                  | `TendersService` (assumed)                                         | N/A                                           | Database (Tenders table)                                               | `TenderHistoryTable` (via `data.tenders`)                          |
| `InvestigationWorkspace`                       | `GET /api/companies`                | `CompaniesService` (assumed)                                       | N/A                                           | Database (Companies table)                                             | `ConnectedCompaniesPanel` (via `data.companies`)                   |
| `InvestigationWorkspace`                       | `GET /api/dashboard/summary`        | `DashboardService` (assumed)                                       | N/A                                           | Database                                                               | `StatCard` (Total Tenders, etc.)                                   |
| `InvestigationWorkspace`                       | `GET /api/dashboard/recent`         | `DashboardService` (assumed)                                       | N/A                                           | Database                                                               | `homeRecent` state (used for initial load)                         |
| `InvestigationWorkspace`                       | `POST /api/web-evidence/search`     | `WebIntelService` (assumed, e.g., `webintel/search.py`)            | N/A                                           | Web Search Providers (DuckDuckGo, etc.)                                | `ProcurementEvidenceTable` (via `data.webPages`)                   |
| `InvestigationWorkspace`                       | `GET /api/web-evidence/procurement` | `WebIntelService` (assumed, e.g., `webintel/procurement_store.py`) | N/A                                           | Database (`WebEvidence`, `WebProcurementEvidence`)                     | `ProcurementEvidenceTable` (via `data.webPages`)                   |
| `InvestigationWorkspace`                       | `GET /api/graph`                    | `GraphService` (assumed, e.g., `services/graph.py`)                | N/A                                           | Database                                                               | `RelationshipGraphExplorer` (via `data.graph`)                     |
| `GraphPage`                                    | `GET /api/graph`                    | `GraphService` (assumed, e.g., `services/graph.py`)                | N/A                                           | Database                                                               | `RelationshipGraphExplorer` (`graph` prop)                         |

---

### Identified Specific Issues

1.  **Frontend Ignores `InvestigationPackage`:**
    - **Frontend Page:** `frontend/src/app/investigation-workspace.tsx`
    - **API Route:** `POST /api/investigations/execute`
    - **Backend Object:** `InvestigationExecutionRequest.package`
    - **Issue:** The frontend calls `executeInvestigation` which returns the `InvestigationPackage`, but then proceeds to make _separate_ API calls (`getTenders`, `getCompanies`, `searchWebEvidence`, `getRelationshipGraph`) to fetch the same or related data, effectively ignoring the `InvestigationPackage` as a single source of truth.
    - **Evidence:** `runInvestigation` function explicitly calls these separate APIs after `executeInvestigation` completes.

2.  **Broken Procurement Data in `InvestigationPackage`:**
    - **Backend Service:** `backend/app/services/investigation_planner.py`, `backend/app/services/investigation_executor.py`
    - **Issue:** Due to a mismatch between `InvestigationPlanner`'s `_build_steps` (which assigns actual connector names to `step.connectors`) and `InvestigationExecutor`'s `_execute_step` (which expects module names), the loop to process procurement connectors in `_execute_step` effectively runs on an empty set of source names, leaving `InvestigationPackage.records` empty.
    - **Evidence:** `backend/app/services/investigation_planner.py` lines 128-149, `backend/app/services/investigation_executor.py` lines 78-85.

3.  **Unimplemented Modules in `InvestigationExecutor`:**
    - **Backend Service:** `backend/app/services/investigation_executor.py`
    - **Issue:** `TODO` comments for "graph", "timeline", "entity_resolution", "evidence" modules in `_execute_step` mean that `InvestigationPackage.entities`, `InvestigationPackage.evidence`, `InvestigationPackage.timeline`, and `InvestigationPackage.graph_seeds` are never populated by the core execution flow.
    - **Evidence:** `backend/app/services/investigation_executor.py` lines 163-165.

4.  **Web Evidence Disconnected from `InvestigationPackage` Flow:**
    - **Frontend Page:** `frontend/src/app/investigation-workspace.tsx`
    - **API Route:** `POST /api/web-evidence/search` and `GET /api/web-evidence/procurement`
    - **Issue:** Web search results (CarWale, ZigWheels, Blogs) are fetched and processed via dedicated API calls (`searchWebEvidence`, `getProcurementEvidence`) and directly populate `investigation.webPages` in the frontend state. These results are **not** routed through the `InvestigationExecutor` or added to `InvestigationPackage.evidence`.
    - **Evidence:** `frontend/src/app/investigation-workspace.tsx` lines 312-327.

5.  **Duplicate API Calls for Graph:**
    - **Frontend Page:** `frontend/src/app/investigation-workspace.tsx` and `frontend/src/app/graph/page.tsx`
    - **API Route:** `GET /api/graph`
    - **Issue:** Both the `InvestigationWorkspace` and the dedicated `GraphPage` make independent calls to `getRelationshipGraph`. While this isn't necessarily a "bug" for the `GraphPage`, it highlights the `InvestigationWorkspace`'s bypass of the `InvestigationPackage` which _should_ contain `graph_seeds`.
    - **Evidence:** `frontend/src/app/investigation-workspace.tsx` lines 350-366; `frontend/src/app/graph/page.tsx` lines 17-21.

---

### Summary of Broken Integrations and Legacy Paths

- **Legacy Path:** Frontend `InvestigationWorkspace` uses individual API calls (`getTenders`, `getCompanies`, `searchWebEvidence`, `getRelationshipGraph`).
- **New Path (intended):** Backend `InvestigationExecutor` produces a comprehensive `InvestigationPackage` via `POST /api/investigations/execute`.
- **Divergence Point:**
  - On the **backend**, the `InvestigationPackage` is generated, but the logic to fully populate all its fields (`entities`, `evidence`, `timeline`, `graph_seeds`) is unfinished.
  - On the **frontend**, after receiving the `InvestigationPackage` (which might be partially empty), `InvestigationWorkspace` immediately **diverges** by making separate API calls for data it _should_ retrieve from the `InvestigationPackage`.
- **Where they should reconnect:** The frontend's `InvestigationWorkspace` should be refactored to:
  1.  Call `POST /api/investigations/execute` once.
  2.  Consume the returned `InvestigationPackage` as the single source of truth.
  3.  Populate its internal `InvestigationData` state directly from `InvestigationPackage.records`, `InvestigationPackage.evidence`, `InvestigationPackage.graph_seeds`, etc.
  4.  The backend's `InvestigationExecutor._execute_step` needs to fully implement the logic for populating `entities`, `evidence`, `timeline`, and `graph_seeds` for all `MODULE_ORDER` steps.
  5.  The `InvestigationPlanner._build_steps` needs to correctly map conceptual module names to actual connector names to ensure `InvestigationPackage.records` is populated.

---

# Missing Features Audit

### Category: Live Tender Ingestion

**Feature:** Live Tender Ingestion
**Current status:** NOT IMPLEMENTED
**Files inspected:**

- `backend/app/importers/` (specifically `prozorro.py`)
- `scripts/download_latest_prozorro_tenders.py`
- `backend/app/connectors/prozorro/connector.py`
  **Evidence:**
- The `app/importers/prozorro.py` and `scripts/download_latest_prozorro_tenders.py` suggest a batch-oriented download and import process rather than a live ingestion system.
- There are no API endpoints or backend services dedicated to receiving real-time tender updates (e.g., webhooks from procurement portals).
- No message queue or streaming solution is evident for continuous data flow.
  **Why it is incomplete:** The current implementation relies on scheduled or manual scripts for data acquisition. It lacks the infrastructure for real-time data streaming and processing.
  **Which modules depend on it:**
- **Investigation:** Requires up-to-date data for accurate results.
- **Search:** Depends on current data for comprehensive search.
- **Procurement Intelligence:** Needs fresh data for timely insights.

---

### Category: Import Engine

**Feature:** Import Engine (general data import and processing)
**Current status:** PARTIALLY COMPLETE (File-backed imports exist, but generalized engine/orchestration for various sources seems limited)
**Files inspected:**

- `backend/app/importers/` (e.g., `prozorro.py`)
- `backend/app/connectors/base.py` (`FileBackedSourceConnector`)
- `backend/app/connectors/` (various `connector.py` files)
- `scripts/` (e.g., `import_cppp.py`, `import_prozorro_tenders.py`, `import_world_bank.py`)
  **Evidence:**
- `FileBackedSourceConnector` in `backend/app/connectors/base.py` handles reading from local JSON files.
- Dedicated import scripts (`import_*.py`) suggest a per-source, script-driven import mechanism.
- No central "Import Engine" orchestration logic (e.g., a service that takes a source configuration and manages the import process dynamically) is immediately visible beyond the individual scripts.
  **Why it is incomplete:** While individual connectors and normalization logic exist, a generalized, configurable, and possibly UI-driven import engine that can manage and monitor imports from various sources dynamically is not apparent. The current approach is more script-based.
  **Which modules depend on it:**
- **Investigation:** Feeds the investigation pipeline with data.
- **Search:** Populates the search index.
- **Procurement Intelligence:** Provides the raw data for analysis.
- **Graph/Timeline:** Relies on imported data to build relationships and events.

---

### Category: Investigation

**Feature:** Investigation (full execution of all plan steps)
**Current status:** PARTIALLY COMPLETE (Core plan-execute logic exists, but many steps are `TODO`s)
**Files inspected:**

- `backend/app/services/investigation_planner.py`
- `backend/app/services/investigation_executor.py`
- `backend/app/schemas/investigation_planner.py` (`MODULE_ORDER`)
- `backend/app/schemas/investigation_executor.py` (`InvestigationPackage`)
  **Evidence:**
- `backend/app/services/investigation_executor.py` (`_execute_step` function, lines 163-165):
  ```python
          # Placeholder for other modules
          # TODO: Implement logic for other modules (graph, timeline, entity_resolution, etc.)
  ```
- `MODULE_ORDER` in `backend/app/schemas/investigation_planner.py` includes modules like "awards", "tenders", "suppliers", "buyers", "graph", "timeline", "procurement_intelligence", "evidence", which are not explicitly handled in `InvestigationExecutor._execute_step`'s `if step.module in {...}` block.
  **Why it is incomplete:** The `InvestigationExecutor` has explicit `TODO` placeholders for many of the planned investigation modules. While these modules appear in the plan, their execution logic to populate the `InvestigationPackage` is missing.
  **Which modules depend on it:**
- **Frontend (Investigation Workspace):** Relies on the `InvestigationPackage` to display comprehensive results.
- **Graph/Timeline/Procurement Intelligence:** These are planned modules within the investigation but lack execution.

---

### Category: Procurement Intelligence

**Feature:** Procurement Intelligence (generating signals and relationship scores within InvestigationPackage)
**Current status:** NOT IMPLEMENTED (Logic for `ProcurementIntelligenceSignal` and `BuyerSupplierRelationshipScore` is defined in schemas, but not populated by executor)
**Files inspected:**

- `backend/app/schemas/investigation_executor.py` (defines `ProcurementIntelligenceSignal`, `BuyerSupplierRelationshipScore`)
- `backend/app/services/investigation_executor.py`
- `backend/app/services/procurement_intelligence.py`
  **Evidence:**
- `backend/app/services/investigation_executor.py`: The `_execute_step` function does not contain any code that populates the `signals` or `relationship_scores` of the `InvestigationPackage` from a dedicated procurement intelligence module.
- `backend/app/services/procurement_intelligence.py`: This file exists, but its integration into the main `InvestigationExecutor` is missing (it's part of a `TODO`).
  **Why it is incomplete:** The `InvestigationExecutor` does not call the `ProcurementIntelligence` service to generate and add these signals to the `InvestigationPackage`. The module for procurement intelligence is a `TODO`.
  **Which modules depend on it:**
- **Investigation:** `ProcurementIntelligence` is a planned step in the `InvestigationPlan`.
- **Frontend (Investigation Workspace):** Would display these signals and scores if available.

---

### Category: Search

**Feature:** Search (comprehensive search across procurement and web sources)
**Current status:** PARTIALLY COMPLETE (File-backed procurement search works, web search exists separately, but not integrated into `InvestigationPackage`)
**Files inspected:**

- `backend/app/connectors/base.py` (`FileBackedSourceConnector.search`)
- `backend/app/connectors/manager.py` (`SourceManager.search`)
- `backend/app/webintel/search.py` (`DuckDuckGoSearchProvider`)
- `frontend/src/lib/api.ts` (`getTenders`, `getCompanies`, `searchWebEvidence`)
  **Evidence:**
- `FileBackedSourceConnector.search` implements basic keyword search over predefined fields for procurement records.
- `DuckDuckGoSearchProvider` handles web search.
- The `InvestigationExecutor`'s procurement search calls `SourceManager.search`.
- Web search is directly called by the frontend via `searchWebEvidence` (frontend/src/lib/api.ts), completely bypassing the `InvestigationExecutor` for web results.
  **Why it is incomplete:** Procurement search is functional for file-backed connectors. However, web search is a separate, frontend-driven API call and its results are not integrated into the `InvestigationPackage` by the `InvestigationExecutor`.
  **Which modules depend on it:**
- **Investigation:** Relies on both procurement and web search results.
- **Frontend:** Displays search results.

---

### Category: RAG (Retrieval Augmented Generation)

**Feature:** RAG functionality (e.g., summarizing documents, answering questions from retrieved text)
**Current status:** NOT IMPLEMENTED
**Files inspected:**

- `backend/app/webintel/` (crawler, extractor)
- `backend/app/services/` (no explicit RAG service)
- `backend/app/api/` (no RAG-specific endpoints)
  **Evidence:**
- The `webintel/crawler.py` and `webintel/extractor.py` suggest text retrieval and entity extraction, which are prerequisites for RAG.
- There are no LLM integrations, vector databases, or generation components present in the codebase.
- No API endpoints for RAG operations (e.g., `/api/ask-document`, `/api/summarize-evidence`).
  **Why it is incomplete:** The foundational components for document retrieval and basic extraction exist, but the "augmented generation" part, requiring LLM integration and a knowledge base, is entirely missing.
  **Which modules depend on it:**
- **Investigation:** Would enhance evidence analysis and insights.
- **Frontend:** Could provide interactive Q&A or summarization features.

---

### Category: Entity Resolution

**Feature:** Entity Resolution (identifying and linking the same entities across different sources)
**Current status:** PARTIALLY COMPLETE (Models and basic matching logic exist, but integration into executor is a TODO)
**Files inspected:**

- `backend/app/entity_resolution/` (`matcher.py`, `resolver.py`, `normalizer.py`, `models.py`)
- `backend/app/services/investigation_executor.py`
- `backend/app/schemas/investigation_planner.py` (`MODULE_ORDER` includes "entity_resolution")
  **Evidence:**
- `backend/app/entity_resolution/` contains models, matching, and normalization logic, suggesting an existing capability.
- `MODULE_ORDER` in `InvestigationPlanner` includes `"entity_resolution"` as a step.
- `InvestigationExecutor._execute_step` contains the `TODO` for "entity_resolution" (line 164).
  **Why it is incomplete:** While the core logic for entity resolution exists, its execution within the main `InvestigationExecutor` pipeline is marked as a `TODO`. This means that resolved entities are not consistently being added to the `InvestigationPackage.entities` list during an investigation.
  **Which modules depend on it:**
- **Investigation:** Relies on resolved entities for a unified view.
- **Graph:** Accurate graph relationships depend on resolved entities.
- **Procurement Intelligence:** Better insights with resolved entities.

---

### Category: Graph

**Feature:** Graph (backend generation of `RelationshipGraph` data)
**Current status:** PARTIALLY COMPLETE (API endpoint exists, but the executor does not populate `graph_seeds`)
**Files inspected:**

- `backend/app/services/graph.py`
- `backend/app/schemas/investigation_executor.py` (`InvestigationGraphSeed`)
- `backend/app/services/investigation_executor.py`
- `backend/app/api/routes/graph.py`
  **Evidence:**
- `backend/app/api/routes/graph.py` defines `GET /api/graph` endpoint, which is used by the frontend `GraphPage` and `InvestigationWorkspace`.
- `backend/app/services/graph.py` contains the logic for building the `RelationshipGraph`.
- `InvestigationPackage` has `graph_seeds: list[InvestigationGraphSeed]`, but `InvestigationExecutor._execute_step` has a `TODO` for the "graph" module.
  **Why it is incomplete:** The graph generation logic exists as a separate service and API. However, the `InvestigationExecutor` does not call this service or populate the `InvestigationPackage.graph_seeds` during an investigation. The frontend bypasses the `InvestigationPackage` for graph data.
  **Which modules depend on it:**
- **Investigation:** `graph` is a planned step in the `InvestigationPlan`.
- **Frontend (Investigation Workspace, GraphPage):** Renders the graph.

---

### Category: Timeline

**Feature:** Timeline (backend generation of `InvestigationTimelineEvent` data)
**Current status:** NOT IMPLEMENTED (Schema exists, but no clear service/execution logic in executor)
**Files inspected:**

- `backend/app/schemas/investigation_executor.py` (`InvestigationTimelineEvent`)
- `backend/app/services/investigation_executor.py`
- `backend/app/services/investigation_planner.py` (`MODULE_ORDER` includes "timeline")
  **Evidence:**
- `InvestigationPackage` has `timeline: list[InvestigationTimelineEvent]`.
- `MODULE_ORDER` includes "timeline" as a step.
- `InvestigationExecutor._execute_step` has a `TODO` for the "timeline" module (line 164).
  **Why it is incomplete:** The `InvestigationExecutor` lacks the implementation to gather events and populate the `InvestigationPackage.timeline` list.
  **Which modules depend on it:**
- **Investigation:** `timeline` is a planned step in the `InvestigationPlan`.
- **Frontend (Investigation Workspace):** Would display timeline events.

---

### Category: Frontend

**Feature:** Frontend (full integration with `InvestigationPackage` as single source of truth)
**Current status:** INCOMPLETE (Uses multiple legacy APIs, bypasses `InvestigationPackage`)
**Files inspected:**

- `frontend/src/app/investigation-workspace.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/app/graph/page.tsx`
  **Evidence:**
- `frontend/src/app/investigation-workspace.tsx`: Explicitly calls multiple APIs like `getTenders`, `getCompanies`, `searchWebEvidence`, `getRelationshipGraph` _after_ calling `executeInvestigation`. This bypasses the `InvestigationPackage` returned by `executeInvestigation`.
- `frontend/src/lib/api.ts`: Contains wrapper functions for these individual APIs.
  **Why it is incomplete:** The frontend `InvestigationWorkspace` was designed to consume data from multiple individual API endpoints rather than relying on the single, comprehensive `InvestigationPackage` endpoint. This creates a architectural disconnect.
  **Which modules depend on it:** All backend APIs and data structures, as the frontend is the primary consumer.

---

### Category: API

**Feature:** API (FastAPI endpoints fully connected to services and returning complete data structures)
**Current status:** PARTIALLY COMPLETE (Many endpoints exist, but `POST /api/investigations/execute` returns incomplete `InvestigationPackage` due to executor issues)
**Files inspected:**

- `backend/app/api/routes/investigations.py`
- `backend/app/api/routes/graph.py`
- `backend/app/api/routes/companies.py` (not inspected, inferred from frontend calls)
- `backend/app/api/routes/tenders.py` (not inspected, inferred from frontend calls)
- `backend/app/api/routes/web_evidence.py` (not inspected, inferred from frontend calls)
  **Evidence:**
- `POST /api/investigations/execute`: Returns an `InvestigationExecutionRequest` containing an `InvestigationPackage`. However, the `package.records` are often empty due to planner/executor issues, and `package.entities`, `package.evidence`, `package.timeline`, `package.graph_seeds` are always empty due to unimplemented `TODO`s in `InvestigationExecutor`.
  **Why it is incomplete:** The backend services that populate the `InvestigationPackage` are not fully implemented, leading to incomplete data being returned by the `POST /api/investigations/execute` endpoint. Frontend then ignores this incomplete package.
  **Which modules depend on it:** Frontend.

---

### Category: Authentication

**Feature:** Authentication (user login, session management, authorization)
**Current status:** NOT VERIFIED (No explicit authentication endpoints or logic were inspected.)
**Files inspected:** N/A (not explicitly part of the investigation flow audit)
**Evidence:** NOT VERIFIED
**Why it is incomplete:** NOT VERIFIED
**Which modules depend on it:** NOT VERIFIED

---

### Category: Background Jobs

**Feature:** Background Jobs (asynchronous task execution, e.g., for long-running imports or web crawling)
**Current status:** NOT VERIFIED (No explicit background job framework or task queue was inspected.)
**Files inspected:**

- `scripts/` (manual execution)
  **Evidence:** `scripts/download_cppp.py`, `download_latest_prozorro_tenders.py`, `download_world_bank.py` are manual/scheduled scripts, not integrated into an asynchronous job system.
  **Why it is incomplete:** There's no clear evidence of a dedicated background job system (e.g., Celery, RQ) being used. Long-running tasks like web crawling or large imports appear to be handled by synchronous scripts or would block the main FastAPI process if integrated directly.
  **Which modules depend on it:**
- **Live Tender Ingestion:** Would greatly benefit from asynchronous processing.
- **Web Intelligence:** Crawling and extraction could be background jobs.
- **Import Engine:** Large data imports are typically background tasks.

---

### Category: Scheduler

**Feature:** Scheduler (for recurring tasks like data imports)
**Current status:** NOT VERIFIED (No explicit scheduler implementation found in inspected files)
**Files inspected:**

- `scripts/` (suggests manual/external scheduling)
  **Evidence:** The presence of `download_latest_prozorro_tenders.py` suggests that an external scheduler (like cron or a system scheduler) would be used to trigger these scripts, rather than an integrated Python-based scheduler.
  **Why it is incomplete:** No Python-based scheduling library (e.g., APScheduler, Celery Beat) or related configuration was found during the audit.
  **Which modules depend on it:**
- **Live Tender Ingestion:** Would schedule regular data pulls.
- **Import Engine:** Orchestrates timed imports.

---

### Category: Database

**Feature:** Database (schema completeness, indexing, data integrity for all features)
**Current status:** PARTIALLY COMPLETE (Core schemas exist, but completeness for all features (e.g., full RAG, detailed timeline) is unverified)
**Files inspected:**

- `backend/app/models/` (e.g., `award.py`, `company.py`, `tender.py`, `base.py`)
- `backend/app/webintel/models.py` (`WebEvidence`, `WebProcurementEvidence`)
- `backend/migrations/versions/` (Alembic migration scripts)
  **Evidence:**
- Core procurement models (`Award`, `Company`, `Tender`) exist.
- `WebEvidence` and `WebProcurementEvidence` models exist.
- Migration scripts (`21484c14a7cf_initial_schema.py`, etc.) indicate schema evolution.
- Completeness for all theoretical features (e.g., data structures for advanced RAG, detailed entity relationship tracking beyond current models) cannot be fully verified without the full functional requirements for each.
  **Why it is incomplete:** While the basic database structure is in place, the schemas and indexing for features that are currently `TODO` (like a fully fleshed-out timeline or advanced RAG) may not be entirely complete or optimized.
  **Which modules depend on it:** All backend services that persist or retrieve data.

---

# Final Verified Findings

## ROOT CAUSE ANALYSIS

### PRIMARY ROOT CAUSE

**File:** `frontend/src/app/investigation-workspace.tsx`
**Class:** `InvestigationWorkspace`
**Function:** `runInvestigation()`
**Code:** Lines 45-55, 65-75

**Evidence:**

```javascript
// Frontend calls legacy APIs instead of InvestigationPackage
const [tenders, companies, dashboardSummary, dashboardRecent] =
  await Promise.all([
    getTenders({ q: normalized, limit: 25, sort: "newest" }),
    getCompanies({ q: normalized, limit: 10 }),
    getDashboardSummary().catch(() => null),
    getDashboardRecent(10).catch(() => null),
  ]);
```

**Execution Trace:**

1. User types "Tata"
2. Frontend calls `runInvestigation("Tata")`
3. Frontend calls `getTenders("Tata")` → returns 0 tenders
4. Frontend calls `getCompanies("Tata")` → returns 0 companies
5. Frontend calls `searchWebEvidence("Tata")` → returns 11 web pages
6. Frontend UI shows 0 tenders, 0 companies, 11 web pages

**Confidence:** HIGH

### SECONDARY ROOT CAUSE

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_build_steps()`
**Code:** Lines 95-105

**Evidence:**

```python
step_connectors = connectors if module in CONNECTOR_MODULES else []
```

**Execution Trace:**

1. InvestigationPlanner builds plan for "company" type
2. MODULE_ORDER includes: ["company_connectors", "awards", "tenders", "suppliers", "buyers", ...]
3. CONNECTOR_MODULES = {"buyer_connectors", "company_connectors", "source_connectors", "tender_connectors"}
4. Only "company_connectors" is in CONNECTOR_MODULES
5. So `step_connectors = ["prozorro", "world_bank", "cppp"]` for "company_connectors" module
6. But `InvestigationExecutor._execute_step()` expects `step.connectors` to contain module names like "company_connectors", not actual connector names

**Answer:** step.connectors becomes empty because InvestigationExecutor expects module names but InvestigationPlanner provides actual connector names

### TERTIARY ROOT CAUSE

**File:** `backend/app/services/investigation_executor.py`
**Class:** `InvestigationExecutor`
**Function:** `_execute_step()`
**Code:** Lines 78-85

**Evidence:**

```python
if step.module in {"company_connectors", "tender_connectors", "buyer_connectors", "source_connectors"}:
    for connector_name in step.connectors:  // Empty loop
        records =  self.source_manager.search(
            query=step.inputs["query"],
            source_names=[connector_name],  // Empty list
            limit=limit_per_connector,
        )
```

**Execution Trace:**

1. "company_connectors" module has empty step.connectors
2. for connector_name in [] → loop never executes
3. No records processed
4. pkg.records remains empty
5. InvestigationPackage.records = []

**Confidence:** HIGH
