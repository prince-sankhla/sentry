"use client";

import { Activity, BellRing, Clock3, Eye, Play, RefreshCw, ShieldAlert, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { getDashboardRecent, getDashboardSummary, getRisk, type DashboardRecent, type DashboardSummary, type RiskResponse } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { Section } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { Button } from "@/components/ui/button";

const WATCH_KEY = "sentry.monitoring.watchlist";
const UI_REFRESH_MS = 30000;

type WatchItem = { id: string; label: string; query: string; createdAt: string };
type Snapshot = { summary: DashboardSummary | null; recent: DashboardRecent; risk: RiskResponse };

function readWatchlist(): WatchItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(WATCH_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeWatchlist(items: WatchItem[]) {
  try { window.localStorage.setItem(WATCH_KEY, JSON.stringify(items)); } catch { /* local preference only */ }
}

export function LiveMonitoring() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [watchlist, setWatchlist] = useState<WatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [query, setQuery] = useState("");

  const refresh = useCallback(async (silent = false) => {
    if (silent) setRefreshing(true); else setLoading(true);
    setError(null);
    try {
      const [summary, recent, risk] = await Promise.all([getDashboardSummary(), getDashboardRecent(8), getRisk()]);
      setSnapshot({ summary, recent, risk });
      setLastRefresh(new Date());
    } catch {
      setError("SENTRY could not refresh the monitoring snapshot. The current view has not been changed.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    setWatchlist(readWatchlist());
    void refresh();
    const timer = window.setInterval(() => void refresh(true), UI_REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  function addWatch() {
    const normalized = query.trim();
    if (!normalized) return;
    const next: WatchItem = { id: `${Date.now()}-${normalized.toLowerCase()}`, label: normalized, query: normalized, createdAt: new Date().toISOString() };
    const merged = [next, ...watchlist.filter((item) => item.query.toLowerCase() !== normalized.toLowerCase())].slice(0, 12);
    setWatchlist(merged); writeWatchlist(merged); setQuery("");
  }

  function removeWatch(id: string) {
    const next = watchlist.filter((item) => item.id !== id);
    setWatchlist(next); writeWatchlist(next);
  }

  const signals = snapshot?.risk.signals ?? [];
  const recentEvents = useMemo(() => {
    if (!snapshot) return [];
    return [
      ...snapshot.recent.latest_tenders.map((item) => ({ key: `tender-${item.id}`, type: "Tender published", title: item.title, meta: item.procuring_entity ?? "Buyer not available", date: item.published_date, href: `/tenders/${item.id}` })),
      ...snapshot.recent.latest_awards.map((item) => ({ key: `award-${item.id}`, type: "Award recorded", title: item.tender.title, meta: item.company.name, date: item.award_date, href: `/tenders/${item.tender.id}` }))
    ].sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? ""))).slice(0, 8);
  }, [snapshot]);

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-border bg-surface elevate">
        <div className="flex flex-col gap-5 px-5 py-5 sm:px-6 sm:py-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/25 bg-accent/[0.07] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-accent"><span className="h-1.5 w-1.5 rounded-full bg-accent pulse-live" />Live monitoring</span>
              <span className="text-[11px] text-faint">Auto-ingestion every 15 min · UI refresh every 30 sec</span>
            </div>
            <h1 className="text-[28px] font-semibold tracking-[-0.035em] text-text sm:text-[34px]">Watch procurement as it changes.</h1>
            <p className="mt-2.5 max-w-2xl text-sm leading-6 text-muted">SENTRY polls official CPPP and GeM public feeds, ingests newly discovered records idempotently, and surfaces the resulting screening signals here.</p>
          </div>
          <Button variant="subtle" onClick={() => void refresh(false)} icon={<RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />}>Refresh now</Button>
        </div>
        <div className="grid grid-cols-2 border-t border-border bg-bg-2/30 sm:grid-cols-4">
          <MonitorStat label="Tenders" value={formatNumber(snapshot?.summary?.total_tenders ?? 0)} />
          <MonitorStat label="Awards" value={formatNumber(snapshot?.summary?.total_awards ?? 0)} />
          <MonitorStat label="Review signals" value={formatNumber(snapshot?.risk.summary.total ?? 0)} />
          <MonitorStat label="High severity" value={formatNumber(snapshot?.risk.summary.high ?? 0)} />
        </div>
      </div>

      {error ? <ErrorState message={error} /> : null}
      {loading ? <div className="rounded-2xl border border-border bg-surface p-8 text-sm text-faint">Loading monitoring snapshot…</div> : null}

      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Section eyebrow="Priority changes" title="Current review signals" action={<Link href="/risk" className="text-xs font-medium text-accent hover:underline">Open screening →</Link>}>
          {signals.length === 0 ? <EmptyState icon={<ShieldAlert className="h-5 w-5" />} title="No review signals in the current snapshot" message="New screening signals will appear here as the underlying procurement data changes." /> : <div className="space-y-2">{signals.slice(0, 8).map((signal, index) => <Link key={`${signal.title}-${index}`} href={signal.tender_id ? `/tenders/${signal.tender_id}` : signal.supplier_id ? `/companies/${signal.supplier_id}` : "/risk"} className="flex items-center gap-3 rounded-xl border border-transparent px-3 py-3 transition hover:border-border hover:bg-surface-2"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 text-warning"><ShieldAlert className="h-3.5 w-3.5" /></span><span className="min-w-0 flex-1"><span className="block truncate text-[13px] font-medium text-text">{signal.title}</span><span className="mt-0.5 block truncate text-[11px] text-faint">{signal.buyer ?? signal.supplier_name ?? signal.summary}</span></span><span className="shrink-0 rounded-full border border-border px-2 py-1 text-[10px] font-semibold uppercase text-muted">{signal.severity}</span></Link>)}</div>}
        </Section>

        <Section eyebrow="Watchlist" title="Entities to keep in view">
          <div className="flex gap-2"><input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") addWatch(); }} placeholder="Buyer, supplier, or tender reference" className="h-10 min-w-0 flex-1 rounded-xl border border-border bg-bg-2/50 px-3 text-sm text-text outline-none placeholder:text-faint focus:border-accent/50" /><Button onClick={addWatch} icon={<BellRing className="h-4 w-4" />}>Watch</Button></div>
          <div className="mt-4 space-y-2">{watchlist.length === 0 ? <EmptyState icon={<Eye className="h-5 w-5" />} title="No watch items yet" message="Add a procurement entity or reference to keep it visible in this workspace." /> : watchlist.map((item) => <div key={item.id} className="flex items-center gap-3 rounded-xl border border-border bg-bg-2/30 px-3 py-3"><span className="grid h-7 w-7 place-items-center rounded-lg border border-border bg-surface text-accent"><Eye className="h-3.5 w-3.5" /></span><Link href={`/investigate?q=${encodeURIComponent(item.query)}`} className="min-w-0 flex-1 truncate text-[13px] font-medium text-text hover:text-accent">{item.label}</Link><button type="button" onClick={() => removeWatch(item.id)} aria-label={`Remove ${item.label}`} className="rounded-lg p-1.5 text-faint transition hover:bg-surface hover:text-text"><X className="h-3.5 w-3.5" /></button></div>)}</div>
        </Section>
      </div>

      <Section eyebrow="Activity feed" title="Recent procurement changes" action={lastRefresh ? <span className="inline-flex items-center gap-1.5 text-[11px] text-faint"><Clock3 className="h-3.5 w-3.5" />Updated {lastRefresh.toLocaleTimeString()}</span> : null}>
        {recentEvents.length === 0 ? <EmptyState icon={<Activity className="h-5 w-5" />} title="No recent procurement activity" message="The monitoring feed will populate when recent tender or award records are available." /> : <div className="grid gap-2 sm:grid-cols-2">{recentEvents.map((event) => <Link key={event.key} href={event.href} className="rounded-xl border border-border bg-surface/50 px-4 py-3 transition hover:border-border-strong hover:bg-surface-2"><div className="flex items-center justify-between gap-3"><span className="text-[10px] font-semibold uppercase tracking-wide text-accent">{event.type}</span><span className="text-[10px] text-faint">{formatDate(event.date)}</span></div><div className="mt-1.5 line-clamp-2 text-[13px] font-medium leading-snug text-text">{event.title}</div><div className="mt-1 truncate text-[11px] text-faint">{event.meta}</div></Link>)}</div>}
      </Section>

      <div className="flex items-center gap-2 rounded-xl border border-border bg-bg-2/30 px-4 py-3 text-[11px] text-faint"><Play className="h-3.5 w-3.5 text-accent" />Official feed polling is scheduled server-side. The 30-second refresh only re-reads SENTRY's current database snapshot.</div>
    </div>
  );
}

function MonitorStat({ label, value }: { label: string; value: string }) { return <div className="border-r border-border px-4 py-3 last:border-r-0"><div className="t-label">{label}</div><div className="mt-1 text-xl font-semibold tabular text-text">{value}</div></div>; }
