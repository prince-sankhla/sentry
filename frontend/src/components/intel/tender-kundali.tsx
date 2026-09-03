import Link from "next/link";

import { EmptyState } from "@/components/ui/states";

export type TenderKundaliData = {
  tender_id: string;
  reference_number: string;
  title: string;
  status: string;
  as_of: string | null;
  buyer: string | null;
  procurement_method: string | null;
  category: string | null;
  geography: string | null;
  estimated_value: string | null;
  currency: string;
  published_date: string | null;
  closing_date: string | null;
  source: { source_name: string; source_record_id: string; source_url: string | null; content_hash: string | null; retrieved_at: string | null; action: string | null };
  documents: Array<{ id: string; title: string; document_type: string; url: string | null; retrieved_at: string | null; content_hash: string | null; evidence_hash: string | null; available: boolean }>;
  document_summary: Record<string, number>;
  awards: Array<{ id: string; supplier_id: string; supplier_name: string; award_date: string | null; award_value: string | null; currency: string; source_name: string | null; source_url: string | null }>;
  comparable_tenders: Array<{ id: string; reference_number: string; title: string; buyer: string | null; category: string | null; procurement_method: string | null; published_date: string | null; estimated_value: string | null; currency: string; similarity_reasons: string[]; award_supplier: string | null; award_value: string | null }>;
  benchmark: { sample_size: number; median: string | null; p25: string | null; p75: string | null; min_value: string | null; max_value: string | null; tender_percentile: number | null; position: string; basis: string[] };
  supplier_history: Array<{ supplier_id: string; supplier_name: string; award_count: number; total_award_value: string; buyer_count: number; buyer_names: string[]; first_award_date: string | null; latest_award_date: string | null; tender_references: string[] }>;
  signals: Array<{ type: string; severity: string; title: string; summary: string; evidence: string[]; supported_by: string[]; review_required: boolean }>;
  evidence_summary: Record<string, number>;
  limitations: string[];
};

function money(value: string | null, currency: string) {
  if (!value) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return `${value} ${currency}`;
  return `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(n)} ${currency}`;
}

export function TenderKundali({ data }: { data: TenderKundaliData | null }) {
  if (!data) return <EmptyState message="Tender kundali is unavailable." />;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Status" value={data.status} />
        <Metric label="Buyer" value={data.buyer ?? "Unknown"} />
        <Metric label="Method" value={data.procurement_method ?? "Not structured"} />
        <Metric label="Category" value={data.category ?? "Not structured"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Tender facts">
          <Row label="Estimate" value={money(data.estimated_value, data.currency)} />
          <Row label="Published" value={data.published_date ?? "—"} />
          <Row label="Closing" value={data.closing_date ?? "—"} />
          <Row label="Geography" value={data.geography ?? "Not structured"} />
          <Row label="Source" value={data.source.source_name} />
          <Row label="Snapshot" value={data.source.content_hash ? data.source.content_hash.slice(0, 12) + "…" : "Not available"} mono />
        </Card>

        <Card title="Historical benchmark">
          <div className="text-2xl font-semibold text-text">{data.benchmark.position}</div>
          <div className="mt-1 text-xs text-muted">{data.benchmark.sample_size} comparable Indian tenders</div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            <Stat label="P25" value={money(data.benchmark.p25, data.currency)} />
            <Stat label="Median" value={money(data.benchmark.median, data.currency)} />
            <Stat label="P75" value={money(data.benchmark.p75, data.currency)} />
          </div>
          {data.benchmark.tender_percentile != null ? <div className="mt-3 text-xs text-muted">Tender estimate percentile: <span className="font-semibold text-text">{data.benchmark.tender_percentile}th</span></div> : null}
        </Card>

        <Card title="Evidence ledger">
          <div className="grid grid-cols-2 gap-2">
            <Stat label="Snapshots" value={String(data.evidence_summary.source_snapshots ?? 0)} />
            <Stat label="Documents" value={String(data.evidence_summary.documents ?? 0)} />
            <Stat label="Awards" value={String(data.evidence_summary.awards ?? 0)} />
            <Stat label="Comparables" value={String(data.evidence_summary.comparables ?? 0)} />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted">As-of {data.as_of ?? "source retrieval time unavailable"}. Findings remain review leads, not determinations.</p>
        </Card>
      </div>

      <Card title={`Red flags & review leads (${data.signals.length})`}>
        {data.signals.length === 0 ? <EmptyState message="No tender-level review signal was produced from the available evidence." /> : <div className="space-y-3">{data.signals.map((signal) => <div className="rounded-2xl border border-border bg-bg-2 p-4" key={`${signal.type}-${signal.title}`}><div className="flex items-start justify-between gap-3"><div><div className="text-sm font-semibold text-text">{signal.title}</div><p className="mt-1 text-sm leading-6 text-muted">{signal.summary}</p></div><span className="rounded-md border border-border px-2 py-1 text-[11px] font-semibold uppercase text-muted">{signal.severity}</span></div>{signal.evidence.length ? <div className="mt-3 flex flex-wrap gap-1.5">{signal.evidence.map((item) => <span className="rounded-md bg-surface px-2 py-1 text-[11px] text-muted" key={item}>{item}</span>)}</div> : null}</div>)}</div>}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title={`Supplier history (${data.supplier_history.length})`}>
          {data.supplier_history.length === 0 ? <EmptyState message="No recorded award history for this tender's suppliers." /> : <div className="space-y-3">{data.supplier_history.map((supplier) => <div className="rounded-xl border border-border bg-bg-2 p-3" key={supplier.supplier_id}><div className="flex items-start justify-between gap-3"><div><div className="text-sm font-semibold text-text">{supplier.supplier_name}</div><div className="mt-1 text-xs text-muted">{supplier.award_count} awards · {supplier.buyer_count} buyers</div></div><div className="text-sm font-semibold text-accent">{money(supplier.total_award_value, data.currency)}</div></div><div className="mt-2 text-xs text-muted">{supplier.buyer_names.slice(0, 4).join(" · ") || "Buyer history unavailable"}</div></div>)}</div>}
        </Card>

        <Card title={`Comparable tenders (${data.comparable_tenders.length})`}>
          {data.comparable_tenders.length === 0 ? <EmptyState message="No sufficiently similar Indian tender records were found." /> : <div className="space-y-2">{data.comparable_tenders.slice(0, 8).map((item) => <Link key={item.id} href={`/tenders/${item.id}`} className="block rounded-xl border border-border bg-bg-2 p-3 transition hover:border-border-strong"><div className="text-xs font-mono text-faint">{item.reference_number}</div><div className="mt-1 text-sm font-semibold text-text">{item.title}</div><div className="mt-1 text-xs text-muted">{money(item.estimated_value, item.currency)} · {item.similarity_reasons.join(" · ")}</div></Link>)}</div>}
        </Card>
      </div>

      <Card title={`Documents (${data.documents.length})`}>
        {data.documents.length === 0 ? <EmptyState message="No document links are currently indexed for this tender." /> : <div className="grid gap-2 sm:grid-cols-2">{data.documents.map((document) => <a href={document.url ?? "#"} target={document.url ? "_blank" : undefined} rel={document.url ? "noreferrer" : undefined} key={document.id} className="rounded-xl border border-border bg-bg-2 p-3 transition hover:border-border-strong"><div className="text-sm font-semibold text-text">{document.title}</div><div className="mt-1 text-xs text-muted">{document.document_type} · {document.available ? "source-linked" : "metadata only"}</div></a>)}</div>}
      </Card>

      <Card title="Limitations">
        <ul className="space-y-2">{data.limitations.map((item) => <li className="text-xs leading-5 text-muted" key={item}>• {item}</li>)}</ul>
      </Card>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-2xl border border-border bg-surface p-4"><div className="text-xs font-semibold uppercase tracking-[0.08em] text-faint">{title}</div><div className="mt-3">{children}</div></section>;
}
function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-border bg-bg-2 p-3"><div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">{label}</div><div className="mt-1 truncate text-sm font-semibold text-text">{value}</div></div>; }
function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) { return <div className="flex items-start justify-between gap-3 border-b border-border py-2 last:border-b-0"><span className="text-xs text-muted">{label}</span><span className={`text-right text-xs font-semibold text-text ${mono ? "font-mono" : ""}`}>{value}</span></div>; }
function Stat({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-border bg-bg-2/50 p-2"><div className="text-[10px] uppercase tracking-[0.06em] text-faint">{label}</div><div className="mt-1 text-xs font-semibold text-text">{value}</div></div>; }
