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

export type TenderDetail = TenderSummary & {
  description: string | null;
  buyer: {
    name: string | null;
  };
  awards: AwardSummary[];
  participating_companies: CompanySummary[];
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

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
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
