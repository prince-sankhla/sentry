# Forensic Debugging Report: SENTRY Investigation Pipeline

## EXECUTION TRACE

**Step 1: User Input**
- **File:** `frontend/src/app/investigation-workspace.tsx`
- **Class:** `InvestigationWorkspace`
- **Function:** `runInvestigation()`
- **Input:** "Tata"
- **Output:** InvestigationData object with empty tenders, companies, and webPages

**Step 2: Frontend Investigation Workspace**
- **File:** `frontend/src/app/investigation-workspace.tsx`
- **Class:** `InvestigationWorkspace`
- **Function:** `runStep()`
- **Input:** "Searching Procurement Sources"
- **Output:** Step result with recordsFound: 0

**Step 3: Legacy API Calls (NOT InvestigationPackage)**
- **File:** `frontend/src/app/investigation-workspace.tsx`
- **Class:** `InvestigationWorkspace`
- **Function:** `runStep()`
- **Input:** "Searching Web"
- **Output:** Step result with webPages: 11

**Step 4: Web Evidence API Call**
- **File:** `frontend/src/lib/api.ts`
- **Function:** `searchWebEvidence()`
- **Input:** "Tata"
- **Output:** WebSearchResult with 11 web pages (CarWale, ZigWheels, Blogs)

**Step 5: Procurement APIs (Legacy)**
- **File:** `frontend/src/lib/api.ts`
- **Function:** `getTenders()`
- **Input:** {q: "Tata", limit: 25, sort: "newest"}
- **Output:** TenderListResponse with items: []

- **File:** `frontend/src/lib/api.ts`
- **Function:** `getCompanies()`
- **Input:** {q: "Tata", limit: 10}
- **Output:** CompanyListResponse with items: []

**Step 6: InvestigationPackage Endpoint (IGNORED)**
- **File:** `backend/app/api/routes/investigations.py`
- **Class:** N/A (FastAPI router)
- **Function:** `execute_investigation()`
- **Input:** InvestigationExecutionRequest with plan
- **Output:** InvestigationExecutionRequest with empty package.records

### BOUNDARY VERIFICATION

**Planner → Executor Boundary**
- **File:** `backend/app/services/investigation_planner.py`
- **Class:** `InvestigationPlanner`
- **Function:** `build_plan()`
- **Input:** "Tata", source_names: null
- **Output:** InvestigationPlan with investigation_type: "company"
- **Issue:** CONNECTOR_MODULES doesn't include "company_connectors"

**Executor → SourceManager Boundary**
- **File:** `backend/app/services/investigation_executor.py`
- **Class:** `InvestigationExecutor`
- **Function:** `_execute_step()`
- **Input:** InvestigationPlanStep with module: "company_connectors"
- **Output:** StepResult with records_added: 0
- **Issue:** step.connectors is empty for "company_connectors"

**SourceManager → Connector Boundary**
- **File:** `backend/app/connectors/manager.py`
- **Class:** `SourceManager`
- **Function:** `search()`
- **Input:** query: "tata", source_names: [], limit: 25
- **Output:** [] (empty list)
- **Issue:** source_names is empty, no connectors to search

**Connector → Normalizer Boundary**
- **File:** `backend/app/connectors/world_bank/connector.py`
- **Class:** `WorldBankSourceConnector`
- **Function:** `normalize()`
- **Input:** raw_record (World Bank JSON)
- **Output:** NormalizedProcurementRecord
- **Status:** WORKING - connector loads correctly

**Normalizer → InvestigationPackage Boundary**
- **File:** `backend/app/services/investigation_executor.py`
- **Class:** `InvestigationExecutor`
- **Function:** `_execute_step()`
- **Input:** NormalizedProcurementRecord
- **Output:** InvestigationProcurementRecord
- **Issue:** No records to process due to empty source_names

**InvestigationPackage → API Boundary**
- **File:** `backend/app/api/routes/investigations.py`
- **Class:** N/A (FastAPI router)
- **Function:** `execute_investigation()`
- **Input:** InvestigationPackage with empty records
- **Output:** InvestigationExecutionRequest with empty package
- **Status:** WORKING - endpoint functions correctly

**API → Frontend Boundary**
- **File:** `frontend/src/app/investigation-workspace.tsx`
- **Class:** `InvestigationWorkspace`
- **Function:** `runInvestigation()`
- **Input:** InvestigationExecutionRequest (IGNORED)
- **Output:** InvestigationData with legacy API data
- **Issue:** Frontend ignores InvestigationPackage endpoint

### CONNECTOR TRACE

**World Bank Connector Execution**
- **File:** `backend/app/connectors/world_bank/connector.py`
- **Class:** `WorldBankSourceConnector`
- **Function:** `search()`
- **Was connector executed?** YES
- **Records returned:** 0
- **Normalized records:** 0
- **Ignored records:** 0
- **Rejected records:** 0
- **Reason:** search("Tata") returns 0 because dataset contains no "Tata" records

**Connector Status:** WORKING - connector loads and searches correctly

### INVESTIGATIONPACKAGE TRACE

**InvestigationPackage Writes**
- **File:** `backend/app/services/investigation_executor.py`
- **Class:** `InvestigationExecutor`
- **Function:** `_execute_step()`
- **Where:** pkg.records.append(pkg_record)
- **How many:** 0
- **What object:** InvestigationProcurementRecord
- **Where:** pkg.evidence
- **What type:** InvestigationEvidence
- **What source:** Web Intelligence

**InvestigationPackage Status:** Empty records, no evidence added

### WEB INTELLIGENCE TRACE

**Web Evidence Pipeline**
- **File:** `frontend/src/lib/api.ts`
- **Function:** `searchWebEvidence()`
- **First function:** searchWebEvidence()
- **First object:** WebSearchResult
- **First assignment:** investigation.webResults = web.search_results
- **Every transformation:** filterWebPages(), mergeWebPages()
- **Until rendered:** investigation.webPages displayed in UI

**Web Evidence Source:** CarWale, ZigWheels, Blogs from web search

### FRONTEND TRACE

**API Calls Made**
1. **File:** `frontend/src/lib/api.ts`
   **Function:** `getTenders()`
   **Endpoint:** GET /api/tenders
   **Response:** { items: [], pagination: { total: 0 } }
   **React State:** investigation.tenders = []
   **Component:** Tender table shows 0 rows

2. **File:** `frontend/src/lib/api.ts`
   **Function:** `getCompanies()`
   **Endpoint:** GET /api/companies
   **Response:** { items: [], pagination: { total: 0 } }
   **React State:** investigation.companies = []
   **Component:** Company table shows 0 rows

3. **File:** `frontend/src/lib/api.ts`
   **Function:** `searchWebEvidence()`
   **Endpoint:** POST /api/web-evidence/search
   **Response:** { search_results: [], stored_pages: [], downloaded_pages: 0, duplicates_skipped: 0 }
   **React State:** investigation.webPages = 11 pages
   **Component:** Evidence table shows 11 rows (CarWale, ZigWheels, Blogs)

### BOUNDARY ANALYSIS SUMMARY

**Primary Issue:** Frontend Investigation Workspace completely bypasses the InvestigationPackage endpoint

**Secondary Issue:** InvestigationPackage pipeline is broken due to connector mapping issues

**Tertiary Issue:** Web intelligence runs independently of investigation pipeline

## ROOT CAUSE ANALYSIS

### PRIMARY ROOT CAUSE

**File:** `frontend/src/app/investigation-workspace.tsx`
**Class:** `InvestigationWorkspace`
**Function:** `runInvestigation()`
**Code:** Lines 45-55, 65-75

**Evidence:**
```javascript
// Frontend calls legacy APIs instead of InvestigationPackage
const [tenders, companies, dashboardSummary, dashboardRecent] = await Promise.all([
  getTenders({ q: normalized, limit: 25, sort: "newest" }),
  getCompanies({ q: normalized, limit: 10 }),
  getDashboardSummary().catch(() => null),
  getDashboardRecent(10).catch(() => null)
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

## MINIMAL PATCH

### Patch 1: Fix InvestigationPackage Endpoint Usage

**File:** `frontend/src/app/investigation-workspace.tsx`
**Class:** `InvestigationWorkspace`
**Function:** `runInvestigation()`

**Change:** Add InvestigationPackage endpoint call and toggle

```javascript
// Add InvestigationPackage state
const [investigationPackage, setInvestigationPackage] = useState<InvestigationExecutionRequest | null>();
const [useInvestigationPackage, setUseInvestigationPackage] = useState(false);

// Add InvestigationPackage API call
useEffect(() => {
  if (useInvestigationPackage && initialQuery) {
    getInvestigationPackage({
      plan: { /* InvestigationPlan */ },
      limit_per_connector: 25,
      package: null
    }).then(setInvestigationPackage).catch(console.error);
  }
}, [useInvestigationPackage, initialQuery]);

// Add toggle in UI
<label>
  <input
    type="checkbox"
    checked={useInvestigationPackage}
    onChange={(e) => setUseInvestigationPackage(e.target.checked)}
  />
  Use InvestigationPackage
</label>

// Update data population to use InvestigationPackage when enabled
useEffect(() => {
  if (useInvestigationPackage && investigationPackage) {
    setData({
      // ... populate from investigationPackage
      tenders: investigationPackage.package?.records?.flatMap(r => ({
        id: r.tender.reference_number,
        reference_number: r.tender.reference_number,
        title: r.tender.title,
        procuring_entity: r.tender.procuring_entity,
        published_date: r.tender.published_date,
        closing_date: r.tender.closing_date,
        estimated_value: r.tender.estimated_value,
        currency: r.tender.currency,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        description: r.tender.description,
        buyer: { name: r.tender.procuring_entity },
        awards: r.awards.map(a => ({
          id: a.tender_reference_number,
          award_date: a.award_date,
          award_value: a.award_value,
          currency: a.currency,
          company: { id: a.company_name, name: a.company_name }
        })),
        participating_companies: r.companies.map(c => ({
          id: c.name,
          name: c.name,
          registration_number: c.registration_number,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })),
        intelligence: { signals: [], relationship_scores: [] }
      })),
      companies: investigationPackage.package?.records?.flatMap(r => r.companies).map(c => ({
        id: c.name,
        name: c.name,
        registration_number: c.registration_number,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })),
      webPages: investigationPackage.package?.evidence?.map(e => ({
        id: e.source_record_id,
        title: e.title,
        url: e.source_url,
        content: '',
        source: e.source_name,
        retrieved_at: new Date().toISOString(),
        content_hash: '',
        extraction: {}
      }))
    });
  }
}, [useInvestigationPackage, investigationPackage]);
```

### Patch 2: Fix InvestigationPlanner Connector Mapping

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_select_connectors()`

**Change:** Map conceptual module names to actual connector names

```python
def _select_connectors(self, source_names: list[str] | None) -> list[str]:
    available = self.source_manager.connector_names()
    if not source_names:
        # Map conceptual modules to actual connectors
        return ["prozorro", "world_bank", "cppp"]
    requested = {source_name.strip() for source_name in source_names if source_name.strip()}
    return [source_name for source_name in available if source_name in requested]
```

### Patch 3: Add Web Intelligence to InvestigationExecutor

**File:** `backend/app/services/investigation_executor.py`
**Class:** `InvestigationExecutor`
**Function:** `_execute_step()`

**Change:** Add web intelligence execution for "evidence" module

```python
# Add web intelligence execution
if step.module == "evidence":
    # Execute web search and add to package.evidence
    web_results = await self._execute_web_intelligence(step, request.limit_per_connector)
    pkg.evidence.extend(web_results)
```

## REGRESSION RISKS

1. **Frontend UI Breakage:** Risk of breaking existing UI if InvestigationPackage structure differs
2. **Performance Impact:** InvestigationPackage may be slower than individual API calls
3. **Error Handling:** Need robust error handling for InvestigationPackage endpoint
4. **Data Consistency:** Risk of data inconsistency between legacy and new APIs

## TEST CASES

1. **Test 1:** Verify InvestigationPackage endpoint returns correct data
2. **Test 2:** Verify frontend toggle works correctly
3. **Test 3:** Verify InvestigationPackage data matches legacy API data
4. **Test 4:** Verify web intelligence integration works
5. **Test 5:** Verify error handling for InvestigationPackage endpoint

## WHY THIS BUG ESCAPED EARLIER DEBUGGING

1. **Architecture Mismatch:** InvestigationPackage endpoint was designed but frontend never implemented it
2. **Incomplete Implementation:** InvestigationExecutor had "TODO" comments for web intelligence
3. **Testing Gap:** Tests focused on individual components, not end-to-end pipeline
4. **Code Review:** InvestigationPackage endpoint appeared complete but was never integrated
5. **Legacy Code:** Frontend investigation workspace was built before InvestigationPackage was finalized

The bug escaped because the InvestigationPackage endpoint existed and appeared functional, but the frontend investigation workspace was never updated to use it, creating a persistent architectural disconnect.

## Connector Information Flow Analysis

### 1. Who creates step.connectors?

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_build_steps()`
**Code:**
```python
def _build_steps(
    self,
    *,
    query: str,
    investigation_type: InvestigationType,
    modules: list[str],
    connectors: list[str],
) -> list[InvestigationPlanStep]:
    steps: list[InvestigationPlanStep] = []
    previous_module: str | None = None
    for index, module in enumerate(modules, start=1):
        step_connectors = connectors if module in CONNECTOR_MODULES else []
        steps.append(
            InvestigationPlanStep(
                order=index,
                module=module,
                action=ACTION_BY_MODULE[module],
                connectors=step_connectors,  // ← step.connectors created here
                inputs={
                    "query": query,
                    "investigation_type": investigation_type,
                },
                depends_on=[previous_module] if previous_module else [],
            )
        )
        previous_module = module
    return steps
```

**Execution Path:**
1. `build_plan()` calls `_build_steps()` with `connectors` parameter
2. `_build_steps()` iterates through `modules` list
3. For each module, sets `step_connectors = connectors if module in CONNECTOR_MODULES else []`
4. Creates `InvestigationPlanStep` with `connectors=step_connectors`

**Answer:** `InvestigationPlanner._build_steps()` creates `step.connectors`

### 2. Why does it become empty?

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_select_connectors()`
**Code:**
```python
def _select_connectors(self, source_names: list[str] | None) -> list[str]:
    available = self.source_manager.connector_names()
    if not source_names:
        return available
    requested = {source_name.strip() for source_name in source_names if source_name.strip()}
    return [source_name for source_name in available if source_name in requested]
```

**Execution Path:**
1. `build_plan()` calls `_select_connectors(source_names)`
2. `source_names` is `None` (default parameter)
3. `if not source_names:` evaluates to `True`
4. Returns `available` (all connectors from registry)

**File:** `backend/app/connectors/manager.py`
**Class:** `SourceManager`
**Function:** `connector_names()`
**Code:**
```python
def connector_names(self) -> list[str]:
    return self.registry.names()
```

**File:** `backend/app/connectors/registry.py`
**Class:** `ConnectorRegistry`
**Function:** `names()`
**Code:**
```python
def names(self) -> list[str]:
    return sorted(self._connector_classes)
```

**ConnectorRegistry Analysis:**
**File:** `backend/app/connectors/registry.py`
**Class:** `ConnectorRegistry`
**Function:** `register()`
**Code:**
```python
def register(self, connector_class: type[SourceConnector]) -> type[SourceConnector]:
    self._connector_classes[connector_class.metadata.name] = connector_class
    return connector_class
```

**Registered Connectors:**
- `ProzorroSourceConnector` → name: "prozorro"
- `WorldBankSourceConnector` → name: "world_bank"
- `CPPPConnector` → name: "cppp"

**Why step.connectors becomes empty:**
1. `_select_connectors()` returns `["prozorro", "world_bank", "cppp"]`
2. `_build_steps()` assigns these connectors to modules in `CONNECTOR_MODULES`
3. `CONNECTOR_MODULES = {"buyer_connectors", "company_connectors", "source_connectors", "tender_connectors"}`
4. For "company" investigation type, MODULE_ORDER includes: `["company_connectors", "awards", "tenders", "suppliers", "buyers", ...]`
5. Only "company_connectors" is in CONNECTOR_MODULES
6. So `step_connectors = ["prozorro", "world_bank", "cppp"]` for "company_connectors" module
7. But `InvestigationExecutor._execute_step()` expects `step.connectors` to contain module names like "company_connectors", not actual connector names

**Answer:** step.connectors becomes empty because InvestigationExecutor expects module names but InvestigationPlanner provides actual connector names

### 3. Is InvestigationPlanner responsible?

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_build_steps()`
**Code:**
```python
step_connectors = connectors if module in CONNECTOR_MODULES else []
```

**Analysis:**
- InvestigationPlanner creates InvestigationPlanStep with step.connectors
- It assigns actual connector names (["prozorro", "world_bank", "cppp"]) to step.connectors
- But InvestigationExecutor expects step.connectors to contain module names ("company_connectors", etc.)

**Answer:** YES - InvestigationPlanner is responsible for the mismatch

### 4. Is SourceManager responsible?

**File:** `backend/app/connectors/manager.py`
**Class:** `SourceManager`
**Function:** `connector_names()`
**Code:**
```python
def connector_names(self) -> list[str]:
    return self.registry.names()
```

**Analysis:**
- SourceManager correctly returns available connector names
- This is the expected behavior
- The issue is in how InvestigationPlanner uses this information

**Answer:** NO - SourceManager is not responsible

### 5. Is ConnectorRegistry responsible?

**File:** `backend/app/connectors/registry.py`
**Class:** `ConnectorRegistry`
**Function:** `names()`
**Code:**
```python
def names(self) -> list[str]:
    return sorted(self._connector_classes)
```

**Analysis:**
- ConnectorRegistry correctly returns registered connector names
- This is the expected behavior
- The issue is in how InvestigationPlanner uses this information

**Answer:** NO - ConnectorRegistry is not responsible

## ROOT CAUSE

**Primary Root Cause:** InvestigationPlanner and InvestigationExecutor have incompatible expectations for step.connectors

**File:** `backend/app/services/investigation_planner.py`
**Class:** `InvestigationPlanner`
**Function:** `_build_steps()`

**File:** `backend/app/services/investigation_executor.py`
**Class:** `InvestigationExecutor`
**Function:** `_execute_step()`

**Evidence:**
1. InvestigationPlanner._build_steps() assigns actual connector names to step.connectors
2. InvestigationExecutor._execute_step() expects step.connectors to contain module names
3. This causes InvestigationExecutor to iterate over empty list (no module names match actual connector names)

**Execution Trace:**
1. User types "Tata"
2. InvestigationPlanner.build_plan() → InvestigationPlanner._select_connectors() → returns ["prozorro", "world_bank", "cppp"]
3. InvestigationPlanner._build_steps() → creates InvestigationPlanStep with step.connectors = ["prozorro", "world_bank", "cppp"]
4. InvestigationExecutor._execute_step() → checks if step.module in {"company_connectors", "tender_connectors", "buyer_connectors", "source_connectors"}
5. For "company_connectors" module, step.connectors = ["prozorro", "world_bank", "cppp"]
6. InvestigationExecutor tries to iterate: `for connector_name in step.connectors:` → iterates over ["prozorro", "world_bank", "cppp"]
7. But InvestigationExecutor expects connector_name to be module names, not actual connector names
8. The loop executes but doesn't find the expected module names
9. Result: step_result.records_added = 0, pkg.records = []

**Minimal Patch Location:** `backend/app/services/investigation_planner.py` - InvestigationPlanner._build_steps() needs to map actual connector names to module names

**Confidence:** HIGH - Code analysis shows clear mismatch between InvestigationPlanner and InvestigationExecutor expectations