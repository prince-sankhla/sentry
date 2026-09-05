"use client";

import { ExternalLink, FileText, Link2, Plus, Search, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { searchWebEvidence, type StoredWebPage } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Section } from "@/components/ui/card";
import { Chip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/states";

type ResearchItem = {
  id: string;
  title: string;
  url: string;
  source: string;
  note: string;
  addedAt: string;
};

const STORAGE_KEY = "sentry.guided-research.v1";

const STARTER_TASKS = [
  "Locate the official tender notice and corrigenda.",
  "Obtain the award / letter of award and evaluation record.",
  "Check the approval, sanction, and committee records relevant to the review signal.",
  "Look for an independent primary source that can corroborate or challenge the observed pattern."
];

export function GuidedResearch({ initialQuery }: { initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [searching, setSearching] = useState(false);
  const [pages, setPages] = useState<StoredWebPage[]>([]);
  const [items, setItems] = useState<ResearchItem[]>([]);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [note, setNote] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw) setItems(JSON.parse(raw) as ResearchItem[]);
    } catch {
      setItems([]);
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Local draft persistence is best effort.
    }
  }, [items]);

  async function runSearch() {
    const subject = query.trim();
    if (!subject) return;
    setSearching(true);
    setNotice(null);
    try {
      const response = await searchWebEvidence(subject);
      setPages(response.stored_pages);
      setNotice(
        response.stored_pages.length
          ? `${response.stored_pages.length} source pages available for review.`
          : "No source pages were returned. Use an official source URL below or broaden the research question."
      );
    } catch {
      setNotice("Source search could not be completed. You can still add a primary-source URL manually.");
    } finally {
      setSearching(false);
    }
  }

  function addItem(next: Omit<ResearchItem, "id" | "addedAt">) {
    const cleanUrl = next.url.trim();
    if (!cleanUrl) return;
    const exists = items.some((item) => item.url === cleanUrl);
    if (exists) {
      setNotice("That source is already in this research ledger.");
      return;
    }
    setItems((current) => [
      {
        ...next,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        addedAt: new Date().toISOString()
      },
      ...current
    ]);
    setTitle("");
    setUrl("");
    setNote("");
    setNotice("Source added to the research ledger. It remains an uncorroborated research item until verified.");
  }

  const officialCount = useMemo(() => pages.filter((page) => /gov|nic|gem|cppp|etenders|gov\.in/i.test(page.url)).length, [pages]);

  return (
    <div className="space-y-5">
      <Section eyebrow="Phase 4 · Guided research" title="Turn evidence gaps into research actions" action={<Chip tone="neutral">Research draft</Chip>}>
        <p className="max-w-3xl text-sm leading-6 text-muted">
          Start from a specific investigation subject, review suggested source material, and record the primary-source evidence you still need. Research entries stay separate from verified case evidence until corroboration.
        </p>

        <div className="mt-5 flex flex-col gap-2.5 sm:flex-row">
          <div className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-border bg-bg-2 px-3.5">
            <Search className="h-4 w-4 shrink-0 text-faint" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void runSearch();
              }}
              placeholder="Investigation subject or evidence question"
              className="h-11 min-w-0 flex-1 bg-transparent text-sm text-text outline-none placeholder:text-faint"
              aria-label="Investigation subject"
            />
          </div>
          <Button variant="primary" onClick={() => void runSearch()} disabled={!query.trim() || searching}>
            {searching ? "Searching…" : "Find sources"}
          </Button>
        </div>

        {notice && <p className="mt-3 text-xs text-faint">{notice}</p>}
      </Section>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Section
          eyebrow="Research plan"
          title="Evidence gaps to close"
          action={<span className="text-xs text-faint">{STARTER_TASKS.length} starting tasks</span>}
        >
          <div className="space-y-2.5">
            {STARTER_TASKS.map((task, index) => (
              <div key={task} className="flex items-start gap-3 rounded-xl border border-border bg-surface/50 px-3.5 py-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-accent/25 bg-accent/[0.07] text-[11px] font-semibold text-accent tabular">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1 text-[13px] leading-relaxed text-text">{task}</span>
                <Link2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-faint" />
              </div>
            ))}
          </div>
        </Section>

        <Section eyebrow="Evidence standard" title="What belongs in the ledger">
          <div className="space-y-3 text-[12.5px] leading-relaxed text-muted">
            <div className="flex gap-3"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" /><span>Prefer official procurement portals, notices, contracts, evaluation records, sanctions, and committee documents.</span></div>
            <div className="flex gap-3"><FileText className="mt-0.5 h-4 w-4 shrink-0 text-accent" /><span>Keep the source URL and an investigator note so the evidence can be corroborated later.</span></div>
            <div className="flex gap-3"><ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-faint" /><span>Secondary reporting can provide context, but it does not replace primary procurement evidence.</span></div>
          </div>
        </Section>
      </div>

      <Section
        eyebrow="Suggested sources"
        title="Search results available for review"
        action={<span className="text-xs text-faint">{officialCount} likely official · {pages.length} total</span>}
      >
        {pages.length === 0 ? (
          <EmptyState icon={<Search className="h-5 w-5" />} title="No source results yet" message="Search an investigation subject above to retrieve stored web evidence, or add a primary-source URL manually." />
        ) : (
          <div className="grid gap-2.5 lg:grid-cols-2">
            {pages.slice(0, 10).map((page) => (
              <article key={page.id} className="rounded-xl border border-border bg-surface/50 p-3.5">
                <div className="flex items-start gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent"><FileText className="h-4 w-4" /></span>
                  <div className="min-w-0 flex-1">
                    <a href={page.url} target="_blank" rel="noreferrer" className="block truncate text-[13px] font-semibold text-text hover:text-accent">{page.title || page.url}</a>
                    <div className="mt-1 text-[10.5px] text-faint">{page.source} · retrieved {new Date(page.retrieved_at).toLocaleDateString()}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => addItem({ title: page.title || page.url, url: page.url, source: page.source, note: "Retrieved through SENTRY source search; corroboration pending." })}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/[0.07] px-2.5 py-1.5 text-[11px] font-semibold text-accent hover:bg-accent/10"
                      >
                        <Plus className="h-3 w-3" /> Add to ledger
                      </button>
                      <a href={page.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-[11px] font-medium text-muted hover:bg-surface">
                        Open source <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </Section>

      <Section eyebrow="Investigator ledger" title="Research evidence captured by the investigator" action={<span className="text-xs text-faint">{items.length} draft item{items.length === 1 ? "" : "s"}</span>}>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Evidence title" className="h-10 rounded-lg border border-border bg-bg-2 px-3 text-xs text-text outline-none placeholder:text-faint md:col-span-1" />
          <input value={url} onChange={(event) => setUrl(event.target.value)} placeholder="Primary source URL" className="h-10 rounded-lg border border-border bg-bg-2 px-3 text-xs text-text outline-none placeholder:text-faint md:col-span-2" />
          <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Why this source matters / what it is expected to verify" className="min-h-20 rounded-lg border border-border bg-bg-2 px-3 py-2 text-xs text-text outline-none placeholder:text-faint md:col-span-2" />
          <Button variant="subtle" onClick={() => addItem({ title: title.trim() || url.trim(), url, source: "Investigator supplied", note })} disabled={!url.trim()} icon={<Plus className="h-3.5 w-3.5" />}>
            Add evidence item
          </Button>
        </div>

        {items.length === 0 ? (
          <div className="mt-4 rounded-xl border border-dashed border-border px-4 py-5 text-center text-xs text-faint">No research items captured yet.</div>
        ) : (
          <div className="mt-4 space-y-2">
            {items.map((item) => (
              <div key={item.id} className="flex items-start gap-3 rounded-xl border border-border bg-surface/40 px-3.5 py-3">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-accent"><Link2 className="h-4 w-4" /></span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-3">
                    <a href={item.url} target="_blank" rel="noreferrer" className="truncate text-[13px] font-semibold text-text hover:text-accent">{item.title}</a>
                    <button type="button" onClick={() => setItems((current) => current.filter((entry) => entry.id !== item.id))} className="shrink-0 rounded-md p-1 text-faint hover:bg-surface hover:text-danger" aria-label="Remove research item"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                  <div className="mt-0.5 truncate text-[10.5px] text-faint">{item.source} · {item.url}</div>
                  {item.note && <p className="mt-2 text-xs leading-relaxed text-muted">{item.note}</p>}
                  <span className="mt-2 inline-flex rounded-full border border-warning/30 bg-warning/[0.06] px-2 py-0.5 text-[10px] font-medium text-warning">Pending corroboration</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>
    </div>
  );
}
