"use client";

import { useState } from "react";
import { ExternalLink, Globe2, Loader2, Newspaper, Search, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/card";

type ContextItem = {
  title: string;
  url: string;
  snippet: string | null;
  source: string;
  provider: string;
  domain: string;
  published_date: string | null;
};

type ContextResponse = {
  query: string;
  focus: string;
  search_query: string;
  search_results: ContextItem[];
  downloaded_pages: number;
  stored_pages: Array<{ id: string; title: string | null; url: string; source: string; retrieved_at: string }>;
  rejected_non_context: number;
};

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

export function OpenSourceContext({ initialQuery }: { initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContextResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    const subject = query.trim();
    if (!subject) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${backendUrl}/api/web/context-search`, {
        method: "POST",
        cache: "no-store",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          query: subject,
          focus: "tender contract procurement news audit investigation history",
          limit: 8
        })
      });
      const payload = (await response.json()) as ContextResponse & { detail?: string };
      if (!response.ok) throw new Error(payload.detail || `Context search failed (${response.status})`);
      setResult(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Context search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-5">
      <Section
        eyebrow="Supplementary intelligence"
        title="Open-source context"
        action={<span className="inline-flex items-center gap-1.5 text-[11px] text-faint"><ShieldAlert className="h-3.5 w-3.5 text-warning" /> Not used as proof or risk score</span>}
      >
        <div className="rounded-2xl border border-border bg-surface/70 p-5">
          <div className="flex items-start gap-3">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-accent/25 bg-accent/[0.08] text-accent"><Globe2 className="h-4 w-4" /></span>
            <div>
              <h2 className="text-sm font-semibold text-text">Past reporting, contract references and surrounding context</h2>
              <p className="mt-1.5 text-xs leading-5 text-muted">SENTRY keeps this material separate from authoritative procurement evidence. It can help an investigator decide what to verify next, but it does not substantiate wrongdoing on its own.</p>
            </div>
          </div>
          <div className="mt-5 flex flex-col gap-2.5 sm:flex-row">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void search(); }} placeholder="Company, buyer, tender or contract" className="h-10 w-full rounded-xl border border-border bg-bg-2/50 pl-9 pr-3 text-sm text-text outline-none focus:border-accent/50" />
            </div>
            <Button onClick={() => void search()} disabled={loading || !query.trim()} icon={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}>
              {loading ? "Searching…" : "Search context"}
            </Button>
          </div>
          {error ? <div className="mt-3 rounded-xl border border-danger/20 bg-danger/[0.04] px-3 py-2.5 text-xs text-danger">{error}</div> : null}
        </div>
      </Section>

      {result ? (
        <Section eyebrow="Context feed" title={`Results for ${result.query}`} action={<span className="text-[11px] text-faint">{result.search_results.length} returned · {result.downloaded_pages} pages read</span>}>
          {result.search_results.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-8 text-center text-sm text-faint">No relevant open-source context was found.</div>
          ) : (
            <div className="grid gap-3.5 lg:grid-cols-2">
              {result.search_results.map((item, index) => (
                <article key={`${item.url}-${index}`} className="rounded-2xl border border-border bg-surface/60 p-4 transition hover:border-border-strong">
                  <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-accent"><Newspaper className="h-3.5 w-3.5" /> {item.domain || item.source}</div>
                  <h3 className="mt-2 text-sm font-semibold leading-snug text-text">{item.title}</h3>
                  {item.snippet ? <p className="mt-2 line-clamp-4 text-xs leading-5 text-muted">{item.snippet}</p> : <p className="mt-2 text-xs leading-5 text-faint">No search excerpt available; inspect the source directly.</p>}
                  <div className="mt-3 flex items-center justify-between gap-3 border-t border-border/60 pt-3">
                    <span className="text-[10.5px] text-faint">{item.published_date ? new Date(item.published_date).toLocaleDateString("en-IN") : "Date not established"}</span>
                    <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/60 px-2.5 py-1.5 text-[11px] font-medium text-muted hover:border-accent/40 hover:text-accent"><ExternalLink className="h-3 w-3" /> Inspect source</a>
                  </div>
                </article>
              ))}
            </div>
          )}
          <div className="mt-4 rounded-xl border border-warning/20 bg-warning/[0.04] px-3.5 py-3 text-[11px] leading-relaxed text-muted">
            Context is intentionally non-adjudicative: it is a research lead. SENTRY does not promote news coverage or open-source reporting into an official procurement finding without corroborating authoritative evidence.
          </div>
        </Section>
      ) : null}
    </div>
  );
}
