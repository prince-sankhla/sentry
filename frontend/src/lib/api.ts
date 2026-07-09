export type Pagination = {
  limit: number;
  offset: number;
  total: number;
};

export type TenderSummary = {
  id: string;
  reference_number: string;
  title: string;
  procuring_entity: string | null;
  published_date: string | null;
  closing_date: string | null;
  estimated_value: string | null;
  currency: string;
  created_at: string;
  updated_at: string;
};

export type CompanySummary = {
  id: string;
  name: string;
  registration_number: string | null;
};

export type CompanySearchSummary = CompanySummary & {
  created_at: string;
  updated_at: string;
};

export type CompanyListResponse = {
  items: CompanySearchSummary[];
  pagination: Pagination;
};

export type AwardSummary = {
  id: string;
  award_date: string | null;
  award_value: string | null;
  currency: string;
  company: CompanySummary;
};

export type ProcurementIntelligenceSignal = {
  type: "single_bidder" | "repeat_supplier" | "buyer_supplier_relationship";
  severity: "low" | "medium" | "high";
  title: string;
  summary: string;
  score: number;
  evidence: string[];
  tender_id: string | null;
  company_id: string | null;
  buyer: string | null;
};

export type BuyerSupplierRelationshipScore = {
  buyer: string | null;
  supplier_id: string;
  supplier_name: string;
  score: number;
  awards_to_supplier: number;
  total_buyer_awards: number;
  supplier_award_share: string;
  total_award_value: string;
  latest_award_date: string | null;
};

export type ProcurementIntelligence = {
  signals: ProcurementIntelligenceSignal[];
  relationship_scores: BuyerSupplierRelationshipScore[];
};

export type TenderListResponse = {
  items: TenderSummary[];
  pagination: Pagination;
};

export type TenderSort = "newest" | "published_date" | "value" | "title";

export type TenderListParams = {
  limit?: number;
  offset?: number;
  q?: string;
  sort?: TenderSort;
};

/** A single structured value extracted from a tender document, with provenance. */
export type ExtractedField = {
  name: string;
  value: string;
  confidence: number;
  /** The literal text span the value was read from — the proof. */
  source_span: string;
  method: string;
};

/** Deterministic, grounded structured intelligence extracted from a tender document. */
export type TenderDocumentExtraction = {
  tender_reference: ExtractedField | null;
  title: ExtractedField | null;
  procuring_entity: ExtractedField | null;
  estimated_value: ExtractedField | null;
  emd_amount: ExtractedField | null;
  tender_fee: ExtractedField | null;
  bid_submission_end: ExtractedField | null;
  bid_opening_date: ExtractedField | null;
  category: ExtractedField | null;
  bidders_count: ExtractedField | null;
  fields: ExtractedField[];
  /** Extraction coverage 0..1 (fields found / fields attempted). */
  coverage: number;
  /** True when the text yielded no structured procurement signal at all. */
  empty: boolean;
  char_count: number;
};

export type TenderDetail = TenderSummary & {
  description: string | null;
  buyer: {
    name: string | null;
  };
  awards: AwardSummary[];
  participating_companies: CompanySummary[];
  intelligence: ProcurementIntelligence;
  pdf_intelligence: TenderDocumentExtraction | null;
};

export type DashboardSummary = {
  total_tenders: number;
  total_companies: number;
  total_awards: number;
  total_procurement_value: string;
  average_tender_value: string;
  latest_import_date: string | null;
};

export type DashboardAward = {
  id: string;
  award_date: string | null;
  award_value: string | null;
  currency: string;
  created_at: string;
  company: CompanySummary;
  tender: Pick<TenderSummary, "id" | "reference_number" | "title">;
};

export type DashboardCompany = CompanySummary & {
  created_at: string;
};

export type DashboardTender = Pick<
  TenderSummary,
  "id" | "reference_number" | "title" | "procuring_entity" | "published_date" | "estimated_value" | "currency" | "created_at"
>;

export type DashboardRecent = {
  latest_tenders: DashboardTender[];
  latest_awarded_companies: DashboardCompany[];
  latest_awards: DashboardAward[];
};

export type CompanyOverview = {
  company: DashboardCompany & {
    address: string | null;
    updated_at: string;
  };
  registration_identifier: string | null;
  address: string | null;
  total_tenders: number;
  total_awards_won: number;
  total_procurement_value: string;
  average_award_value: string;
  first_procurement_date: string | null;
  latest_procurement_date: string | null;
  intelligence: ProcurementIntelligence;
};

export type CompanyTenderSort = "latest" | "published_date" | "value" | "title" | "award_value";

export type CompanyTendersParams = {
  limit?: number;
  offset?: number;
  q?: string;
  sort?: CompanyTenderSort;
};

export type CompanyTenderHistoryItem = {
  id: string;
  reference_number: string;
  title: string;
  tender_value: string | null;
  currency: string;
  publication_date: string | null;
  procurement_status: string | null;
  buyer: string | null;
  award_amount: string | null;
  award_date: string | null;
};

export type CompanyTenderHistoryResponse = {
  items: CompanyTenderHistoryItem[];
  pagination: Pagination;
};

export type CompanyAwardHistoryItem = {
  id: string;
  award_amount: string | null;
  award_date: string | null;
  currency: string;
  tender_id: string;
  tender_title: string;
  tender_reference_number: string;
};

export type CompanyAwardHistoryResponse = {
  items: CompanyAwardHistoryItem[];
  pagination: Pagination;
};

export type GraphNodeType =
  | "company"
  | "tender"
  | "award"
  | "buyer"
  | "indicator"
  | "evidence"
  | "document"
  | "web_evidence"
  | "organization"
  | "category";

export type GraphEdgeType =
  | "company_tender"
  | "tender_award"
  | "award_company"
  | "buyer_tender"
  | "buyer_company"
  | "tender_indicator"
  | "company_indicator"
  | "evidence_indicator"
  | "tender_evidence"
  | "web_evidence_company"
  | "web_evidence_tender"
  | "web_evidence_award"
  | "document_tender"
  | "category_tender"
  | "organization_evidence";

export type RelationshipGraphNode = {
  id: string;
  type: GraphNodeType;
  label: string;
  data: Record<string, unknown>;
};

export type RelationshipGraphEdge = {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  label: string;
  data: Record<string, unknown>;
};

export type RelationshipGraph = {
  nodes: RelationshipGraphNode[];
  edges: RelationshipGraphEdge[];
};

export type WebSearchResult = {
  title: string;
  url: string;
  snippet: string | null;
  source: string;
  provider: string;
  domain: string;
  published_date: string | null;
};

export type WebEvidenceExtraction = {
  company_mentions: string[];
  organization_names: string[];
  government_entities: string[];
  urls: string[];
  emails: string[];
  phone_numbers: string[];
  dates: string[];
};

export type StoredWebPage = {
  id: string;
  query: string;
  url: string;
  title: string | null;
  source: string;
  retrieved_at: string;
  content_hash: string;
  extraction: WebEvidenceExtraction;
  procurement_evidence: ProcurementEvidence | null;
};

export type WebSearchResponse = {
  search_results: WebSearchResult[];
  downloaded_pages: number;
  stored_pages: StoredWebPage[];
  duplicates_skipped: number;
};

export type ProcurementEvidence = {
  id: string;
  web_evidence_id: string;
  tender_id: string | null;
  company_id: string | null;
  award_id: string | null;
  company_name: string | null;
  normalized_company_name: string | null;
  government_buyer: string | null;
  tender_title: string | null;
  contract_title: string | null;
  contract_value: string | null;
  currency: string | null;
  tender_category: string | null;
  procurement_sector: string | null;
  country: string | null;
  publication_date: string | null;
  award_date: string | null;
  contract_number: string | null;
  tender_number: string | null;
  organization: string | null;
  people_mentioned: string[];
  related_companies: string[];
  raw_signals: Record<string, unknown>;
};

export type ProcurementEvidenceResponse = {
  items: StoredWebPage[];
};

export type CanonicalCompany = {
  id: string;
  canonical_name: string;
  aliases: string[];
  matched_sources: Array<{
    source_type: string;
    source_id: string;
    alias: string;
    confidence: string;
    match_reason: string;
  }>;
  confidence: string;
  linked_company_ids: string[];
  linked_procurement_companies: Array<{
    id: string;
    name: string;
    registration_number: string | null;
    source_name: string | null;
    source_record_id: string | null;
  }>;
  linked_web_evidence: Array<{
    id: string;
    url: string;
    title: string | null;
    source: string;
    retrieved_at: string;
    company_name: string | null;
    tender_id: string | null;
    award_id: string | null;
  }>;
  linked_tenders: TenderSummary[];
  linked_awards: Array<{
    id: string;
    tender_id: string;
    company_id: string;
    award_date: string | null;
    award_value: string | null;
    currency: string;
  }>;
};

export type GraphParams = {
  companyId?: string;
  tenderId?: string;
  depth?: number;
};

export type InvestigationPlanRequest = {
  query: string;
  source_names?: string[] | null;
};

export type InvestigationPlanStep = {
  order: number;
  module: string;
  action: string;
  connectors: string[];
  inputs: Record<string, string>;
  depends_on: string[];
  status: "planned";
};

export type InvestigationPlan = {
  query: string;
  investigation_type: "company" | "supplier" | "buyer" | "tender" | "director" | "contract" | "ministry" | "location";
  confidence: number;
  connectors: string[];
  modules: string[];
  steps: InvestigationPlanStep[];
};

export type InvestigationSourceMetadata = {
  source_name: string;
  source_record_id: string;
  source_url: string | null;
  retrieved_at: string | null;
};

export type InvestigationTenderResult = {
  reference_number: string;
  title: string;
  description: string | null;
  procuring_entity: string | null;
  published_date: string | null;
  closing_date: string | null;
  estimated_value: string | null;
  currency: string;
  metadata: InvestigationSourceMetadata;
};

export type InvestigationCompanyResult = {
  name: string;
  registration_number: string | null;
  tax_id: string | null;
  company_identifier: string | null;
  address: string | null;
  website: string | null;
  canonical_company_id: string | null;
  metadata: InvestigationSourceMetadata;
};

export type InvestigationAwardResult = {
  tender_reference_number: string;
  company_name: string;
  company_registration_number: string | null;
  company_tax_id: string | null;
  company_identifier: string | null;
  company_address: string | null;
  company_website: string | null;
  canonical_company_id: string | null;
  award_date: string | null;
  award_value: string | null;
  currency: string;
  metadata: InvestigationSourceMetadata;
};

export type InvestigationDocumentResult = {
  title: string;
  url: string | null;
  document_type: string;
  metadata: InvestigationSourceMetadata;
};

export type InvestigationProcurementRecord = {
  tender: InvestigationTenderResult;
  companies: InvestigationCompanyResult[];
  awards: InvestigationAwardResult[];
  documents: InvestigationDocumentResult[];
  canonical_company_ids: string[];
};

export type InvestigationCanonicalCompany = {
  id: string;
  canonical_name: string;
  aliases: string[];
  confidence: number;
  matched_sources: Array<{
    source_type: string;
    source_id: string;
    source_name: string;
    source_record_id: string;
    alias: string;
    confidence: number;
    match_reason: string;
    tender_reference_number: string | null;
  }>;
  matched_procurement_records: string[];
};

export type InvestigationStepResult = {
  order: number;
  module: string;
  action: string;
  connectors: string[];
  records_added: number;
  entities_added: number;
  evidence_added: number;
  status: string;
};

export type InvestigationTimelineEvent = {
  label: string;
  event_date: string;
  source_name: string;
  source_record_id: string;
  related_tender: string | null;
  related_entity: string | null;
};

export type InvestigationGraphSeed = {
  source: string;
  target: string;
  relationship: string;
  source_name: string;
  source_record_id: string;
};

export type InvestigationPackage = {
  plan: InvestigationPlan;
  records: InvestigationProcurementRecord[];
  // Canonical entity resolution of the investigation subject (companies AND
  // government buyers), computed before retrieval. Present from the backend
  // /execute + /stream report package.
  resolved_entities: EntityResolutionResult | null;
  records_from_resolved_entity: boolean;
  canonical_companies: InvestigationCanonicalCompany[];
  entities: unknown[];
  evidence: unknown[];
  timeline: InvestigationTimelineEvent[];
  graph_seeds: InvestigationGraphSeed[];
  // Complete typed graph of the whole package. The backend node/edge shape is
  // structurally identical to RelationshipGraph, so it renders directly.
  graph: RelationshipGraph;
  indicators: InvestigationProcurementIndicator[];
  step_results: InvestigationStepResult[];
};

/* -------------------------------------------------- canonical entity resolution */

export type EntityCandidate = {
  entity_id: string;
  canonical_name: string;
  entity_type: string;
  registration_number: string | null;
  aliases: string[];
  match_type: string;
  match_reason: string;
  score: number;
  confidence: number;
  tender_count: number;
  award_count: number;
  sources: string[];
};

export type EntityResolutionResult = {
  query: string;
  resolved: boolean;
  requires_disambiguation: boolean;
  candidates: EntityCandidate[];
  selected_entity_id: string | null;
  reason: string;
};

/**
 * Resolve free text to ranked canonical procurement entities.
 *
 * Backs the entity-search experience: investigations must start from a verified
 * entity, never arbitrary text, so the UI resolves suggestions against this
 * endpoint and only enables "Investigate" once one candidate is selected.
 */
export function resolveEntity(query: string, signal?: AbortSignal): Promise<EntityResolutionResult> {
  return apiPost<EntityResolutionResult>("/api/investigations/resolve-entity", { query }, signal);
}

export type InvestigationProcurementIndicator = {
  type: string;
  severity: "low" | "medium" | "high";
  title: string;
  summary: string;
  score: number;
  evidence: string[];
  related_tenders: string[];
  related_entities: string[];
};

export type InvestigationExecutionRequest = {
  plan: InvestigationPlan;
  limit_per_connector: number;
  package: InvestigationPackage | null;
};

/* -------------------------------------------------- AI reasoning layer */

export type EvidenceQualityTier = "primary" | "corroborating" | "weak" | "unverified";

export type ReasoningCitation = {
  label: string;
  source_name: string;
  source_record_id: string | null;
  source_url: string | null;
  document_url: string | null;
  document_type: string | null;
  retrieved_at: string | null;
  published_date: string | null;
  confidence: number;
  related_tender: string | null;
  related_entity: string | null;
  evidence_type: string;
  citation: string;
  quality: number;
  quality_tier: EvidenceQualityTier;
};

export type ReasoningFinding = {
  title: string;
  detail: string;
  severity: "low" | "medium" | "high";
  score: number;
  citations: ReasoningCitation[];
  evidence_backed: boolean;
};

export type FollowUpSuggestion = {
  label: string;
  query: string;
  rationale: string;
};

/** One step of the grounded multi-step analyst trace. */
export type AnalystStep = {
  order: number;
  tool: string;
  input: string;
  observation: string;
  citations: ReasoningCitation[];
};

/** Audit proving the narrative is anchored to verifiable evidence. */
export type GroundingReport = {
  total_findings: number;
  evidence_backed_findings: number;
  total_citations: number;
  records_reviewed: number;
  documents_available: number;
  fully_grounded: boolean;
};

/** A prior related investigation recalled from cross-investigation memory. */
export type MemoryHit = {
  subject: string;
  investigation_type: string;
  risk_level: string;
  confidence: number;
  key_entities: string[];
  key_indicators: string[];
  records_reviewed: number;
  remembered_at: string;
  match_score: number;
  match_reason: string;
};

export type InvestigationRiskLevel = "low" | "medium" | "high" | "critical" | "insufficient";

export type InvestigationReasoning = {
  subject: string;
  investigation_type: string;
  generated_by: "llm" | "deterministic";
  provider: string | null;
  model: string | null;
  fallback_reason: "no_provider" | "provider_error" | "grounding_guard" | null;
  executive_summary: string;
  risk_level: InvestigationRiskLevel;
  risk_rationale: string[];
  confidence: number;
  findings: ReasoningFinding[];
  recommendations: string[];
  follow_ups: FollowUpSuggestion[];
  evidence_ledger: ReasoningCitation[];
  grounding: GroundingReport;
  analyst_trace: AnalystStep[];
  prior_investigations: MemoryHit[];
  analyst_report: AnalystReport | null;
  insufficient_evidence: boolean;
};

/* -------------------------------------------------- structured analyst report */

export type ConfidenceDimension = {
  key: string;
  label: string;
  score: number;
  detail: string;
};

export type ConfidenceAssessment = {
  score: number;
  level: "high" | "moderate" | "low" | "very_low";
  dimensions: ConfidenceDimension[];
  explanation: string;
};

export type Contradiction = {
  type: string;
  severity: "low" | "medium" | "high";
  summary: string;
  detail: string;
  related_tenders: string[];
  related_entities: string[];
};

export type BuyerInsight = {
  name: string;
  tender_count: number;
  award_count: number;
  total_award_value: string | null;
  currency: string | null;
  top_suppliers: string[];
  concentration_pct: number | null;
  note: string;
};

export type SupplierInsight = {
  name: string;
  award_count: number;
  total_award_value: string | null;
  currency: string | null;
  buyers: string[];
  single_buyer_dependence: boolean;
  note: string;
};

export type AwardAnalysis = {
  total_awards: number;
  valued_awards: number;
  total_value: string | null;
  currency: string | null;
  largest_award_value: string | null;
  largest_award_supplier: string | null;
  largest_award_tender: string | null;
  note: string;
};

export type TimelineAnalysis = {
  event_count: number;
  first_event: string | null;
  last_event: string | null;
  span_days: number | null;
  fast_awards: number;
  note: string;
};

export type ProcurementPattern = {
  pattern: string;
  detail: string;
  supporting_tenders: string[];
};

export type AnalystReport = {
  procurement_patterns: ProcurementPattern[];
  buyer_analysis: BuyerInsight[];
  supplier_analysis: SupplierInsight[];
  award_analysis: AwardAnalysis | null;
  timeline_analysis: TimelineAnalysis | null;
  contradictions: Contradiction[];
  missing_evidence: string[];
  confidence_assessment: ConfidenceAssessment | null;
};

export type InvestigationReport = {
  package: InvestigationPackage;
  reasoning: InvestigationReasoning;
};

/** Live status of the multi-provider LLM chain. */
export type LLMProviderStatus = {
  mode: "llm" | "deterministic";
  providers: string[];
  fallback_order: string[];
};

export function getLLMProviders(): Promise<LLMProviderStatus> {
  return apiGet<LLMProviderStatus>("/api/investigations/providers");
}

/* SSE frames emitted by POST /api/investigations/stream */
export type InvestigationStreamStep = {
  key: string;
  status: "running" | "complete" | "error";
  label: string;
  detail?: string;
};

export type InvestigationStreamHandlers = {
  onStep?: (step: InvestigationStreamStep) => void;
  onPlan?: (plan: InvestigationPlan) => void;
  // Canonical entity candidates resolved before retrieval (SSE "candidates" frame).
  onCandidates?: (resolution: EntityResolutionResult) => void;
  onReport?: (report: InvestigationReport) => void;
  onError?: (message: string) => void;
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, {
    cache: "no-store",
    headers: {
      Accept: "application/json"
    }
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("not_found");
    }

    throw new Error(`Backend request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

async function apiPost<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body),
    signal
  });

  if (!response.ok) {
    throw new Error(`Backend request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function getTenders({
  limit = 25,
  offset = 0,
  q,
  sort = "newest"
}: TenderListParams = {}): Promise<TenderListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort
  });
  if (q) {
    params.set("q", q);
  }

  return apiGet<TenderListResponse>(`/api/tenders?${params.toString()}`);
}

export function getTender(tenderId: string): Promise<TenderDetail> {
  return apiGet<TenderDetail>(`/api/tenders/${tenderId}`);
}

export function getCompanies({ limit = 25, offset = 0, q }: { limit?: number; offset?: number; q?: string } = {}): Promise<CompanyListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  if (q) {
    params.set("q", q);
  }

  return apiGet<CompanyListResponse>(`/api/companies?${params.toString()}`);
}

export function getDashboardSummary(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>("/api/dashboard/summary");
}

export function getDashboardRecent(limit = 5): Promise<DashboardRecent> {
  const params = new URLSearchParams({ limit: String(limit) });
  return apiGet<DashboardRecent>(`/api/dashboard/recent?${params.toString()}`);
}

export function getCompanyOverview(companyId: string): Promise<CompanyOverview> {
  return apiGet<CompanyOverview>(`/api/companies/${companyId}/overview`);
}

export function getCompanyTenders(
  companyId: string,
  { limit = 25, offset = 0, q, sort = "latest" }: CompanyTendersParams = {}
): Promise<CompanyTenderHistoryResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort
  });
  if (q) {
    params.set("q", q);
  }

  return apiGet<CompanyTenderHistoryResponse>(`/api/companies/${companyId}/tenders?${params.toString()}`);
}

export function getCompanyAwards(
  companyId: string,
  limit = 25,
  offset = 0
): Promise<CompanyAwardHistoryResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  return apiGet<CompanyAwardHistoryResponse>(`/api/companies/${companyId}/awards?${params.toString()}`);
}

export function getRelationshipGraph({ companyId, tenderId, depth = 2 }: GraphParams = {}): Promise<RelationshipGraph> {
  const params = new URLSearchParams({ depth: String(depth) });
  if (companyId) {
    params.set("company_id", companyId);
  }
  if (tenderId) {
    params.set("tender_id", tenderId);
  }

  return apiGet<RelationshipGraph>(`/api/graph?${params.toString()}`);
}

export function planInvestigation(request: InvestigationPlanRequest): Promise<InvestigationPlan> {
  return apiPost<InvestigationPlan>("/api/investigations/plan", request);
}

export function executeInvestigation(plan: InvestigationPlan, limitPerConnector = 25): Promise<InvestigationExecutionRequest> {
  return apiPost<InvestigationExecutionRequest>("/api/investigations/execute", {
    plan,
    limit_per_connector: limitPerConnector,
    package: null
  });
}

/**
 * Run a full AI investigation from a single prompt, streaming live progress.
 *
 * Uses a POST + ReadableStream reader (EventSource only supports GET) to parse
 * Server-Sent Event frames from /api/investigations/stream. Returns an abort
 * function so callers can cancel an in-flight investigation.
 */
export function streamInvestigation(
  query: string,
  handlers: InvestigationStreamHandlers,
  options?: { limitPerConnector?: number; sourceNames?: string[] }
): () => void {
  const controller = new AbortController();

  (async () => {
    let response: Response;
    try {
      response = await fetch(`${backendUrl}/api/investigations/stream`, {
        method: "POST",
        signal: controller.signal,
        cache: "no-store",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify({
          query,
          source_names: options?.sourceNames ?? null,
          limit_per_connector: options?.limitPerConnector ?? 25
        })
      });
    } catch (err) {
      if (!controller.signal.aborted) {
        handlers.onError?.(err instanceof Error ? err.message : "Failed to reach investigation engine");
      }
      return;
    }

    if (!response.ok || !response.body) {
      handlers.onError?.(`Investigation engine returned ${response.status}`);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    const dispatch = (frame: string) => {
      const lines = frame.split("\n");
      let event = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
      }
      if (dataLines.length === 0) return;
      let payload: unknown;
      try {
        payload = JSON.parse(dataLines.join("\n"));
      } catch {
        return;
      }
      switch (event) {
        case "step":
          handlers.onStep?.(payload as InvestigationStreamStep);
          break;
        case "plan":
          handlers.onPlan?.(payload as InvestigationPlan);
          break;
        case "candidates":
          handlers.onCandidates?.(payload as EntityResolutionResult);
          break;
        case "report":
          handlers.onReport?.(payload as InvestigationReport);
          break;
        case "error":
          handlers.onError?.((payload as { message?: string }).message ?? "Investigation failed");
          break;
        default:
          break;
      }
    };

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE frames are separated by a blank line.
        let sep: number;
        while ((sep = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          if (frame.trim()) dispatch(frame);
        }
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        handlers.onError?.(err instanceof Error ? err.message : "Investigation stream interrupted");
      }
    }
  })();

  return () => controller.abort();
}

export function searchWebEvidence(query: string): Promise<WebSearchResponse> {
  return apiPost<WebSearchResponse>("/api/web/search", { query });
}

export function getProcurementEvidence(query: string, limit = 25): Promise<ProcurementEvidenceResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiGet<ProcurementEvidenceResponse>(`/api/web/procurement-evidence?${params.toString()}`);
}

export function getCanonicalCompany(companyId: string): Promise<CanonicalCompany> {
  return apiGet<CanonicalCompany>(`/api/entities/company/${companyId}`);
}

// ---- Phase 3: search, autocomplete, and profile endpoints ----

export type SearchHit = {
  type: "tender" | "company" | "buyer";
  id: string;
  label: string;
  sublabel: string | null;
};

export type SearchResponse = {
  query: string;
  tenders: SearchHit[];
  companies: SearchHit[];
  buyers: SearchHit[];
  total: number;
};

export type AutocompleteResponse = {
  query: string;
  suggestions: SearchHit[];
};

export type ProfileOverview = {
  kind: "tender" | "company" | "buyer";
  id: string;
  title: string;
  subtitle: string | null;
  stats: Record<string, unknown>;
};

export type RelatedTender = {
  reference_number: string;
  title: string;
  procuring_entity: string | null;
  published_date: string | null;
  estimated_value: string | null;
  currency: string;
  source_name: string | null;
};

export type RelatedAward = {
  tender_reference_number: string;
  company_name: string;
  award_value: string | null;
  currency: string;
  award_date: string | null;
};

export type RelatedDocument = {
  title: string;
  url: string | null;
  document_type: string;
  related_tender: string | null;
};

export type ProfileResponse = {
  overview: ProfileOverview;
  indicators: InvestigationProcurementIndicator[];
  timeline: InvestigationTimelineEvent[];
  evidence: unknown[];
  relationships: InvestigationGraphSeed[];
  related_tenders: RelatedTender[];
  related_awards: RelatedAward[];
  related_documents: RelatedDocument[];
  graph: RelationshipGraph;
  canonical_companies: InvestigationCanonicalCompany[];
  entities: unknown[];
};

export function globalSearch(query: string, limit = 10): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiGet<SearchResponse>(`/api/search?${params.toString()}`);
}

export function autocomplete(query: string, limit = 10): Promise<AutocompleteResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  return apiGet<AutocompleteResponse>(`/api/search/autocomplete?${params.toString()}`);
}

export function getTenderProfile(tenderId: string): Promise<ProfileResponse> {
  return apiGet<ProfileResponse>(`/api/profiles/tender/${tenderId}`);
}

export function getCompanyProfile(companyId: string): Promise<ProfileResponse> {
  return apiGet<ProfileResponse>(`/api/profiles/company/${companyId}`);
}

export function getBuyerProfile(name: string): Promise<ProfileResponse> {
  const params = new URLSearchParams({ name });
  return apiGet<ProfileResponse>(`/api/profiles/buyer?${params.toString()}`);
}

// ---- Analytics: awards, portfolio overview, risk, timeline, geography ----

export type AwardListItem = {
  id: string;
  award_value: string | null;
  currency: string;
  award_date: string | null;
  company: CompanySummary;
  tender: {
    id: string;
    reference_number: string;
    title: string;
    procuring_entity: string | null;
  };
};

export type AwardListStats = {
  total_awards: number;
  total_value: string;
  average_value: string;
  awarded_suppliers: number;
  awarding_buyers: number;
};

export type AwardSort = "newest" | "amount" | "award_date" | "buyer";

export type AwardListResponse = {
  items: AwardListItem[];
  pagination: Pagination;
  stats: AwardListStats;
};

export function getAwards({
  limit = 25,
  offset = 0,
  q,
  sort = "newest"
}: { limit?: number; offset?: number; q?: string; sort?: AwardSort } = {}): Promise<AwardListResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset), sort });
  if (q) params.set("q", q);
  return apiGet<AwardListResponse>(`/api/analytics/awards?${params.toString()}`);
}

export type AnalyticsOverview = {
  totals: {
    tenders: number;
    companies: number;
    awards: number;
    total_tender_value: string;
    total_awarded_value: string;
    average_tender_value: string;
    single_bidder_tenders: number;
    buyers: number;
  };
  top_buyers: { buyer: string; tenders: number; awards: number; total_value: string }[];
  top_suppliers: { company_id: string; name: string; awards: number; total_value: string }[];
  monthly: { month: string; tenders: number; value: string }[];
  sources: { source_name: string; tenders: number }[];
};

export function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  return apiGet<AnalyticsOverview>("/api/analytics/overview");
}

export type RiskSignal = {
  type: string;
  severity: "low" | "medium" | "high";
  title: string;
  summary: string;
  score: number;
  buyer: string | null;
  supplier_name: string | null;
  supplier_id: string | null;
  tender_id: string | null;
  tender_reference: string | null;
  evidence: string[];
};

export type RiskResponse = {
  summary: {
    total: number;
    high: number;
    medium: number;
    low: number;
    single_bidder_tenders: number;
    flagged_relationships: number;
  };
  signals: RiskSignal[];
};

export function getRisk(): Promise<RiskResponse> {
  return apiGet<RiskResponse>("/api/analytics/risk");
}

export type TimelineEvent = {
  date: string;
  kind: "tender_published" | "tender_closing" | "award";
  title: string;
  subtitle: string | null;
  reference: string | null;
  entity_type: "tender" | "company";
  entity_id: string | null;
};

export type TimelineResponse = { events: TimelineEvent[] };

export function getAnalyticsTimeline(limit = 60): Promise<TimelineResponse> {
  return apiGet<TimelineResponse>(`/api/analytics/timeline?limit=${limit}`);
}

export type GeographyRegion = {
  region: string;
  tenders: number;
  value: string;
  awards: number;
};

export type GeographyResponse = {
  regions: GeographyRegion[];
  matched: number;
  unmatched: number;
  total: number;
};

export function getGeography(): Promise<GeographyResponse> {
  return apiGet<GeographyResponse>("/api/analytics/geography");
}
