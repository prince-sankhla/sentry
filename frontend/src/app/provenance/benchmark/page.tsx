"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, XCircle, ShieldCheck, Gauge, Target } from "lucide-react";

type Row = { case_id: string; mutation: string; verdict: string; primary_violation: { family: string; step_id: string } | null; top_step: { step_id: string; step: string; score: number } | null };
type Result = { cases: Row[]; total: number; failure_families_covered: number };
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";

export default function BenchmarkPage() {
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch(`${BACKEND_URL}/api/provenance/benchmark`, { cache: "no-store" })
      .then(r => { if (!r.ok) throw new Error(String(r.status)); return r.json(); })
      .then(setResult)
      .catch(e => setError(e instanceof Error ? e.message : "Unable to load benchmark"));
  }, []);
  const passed = result?.cases.filter(r => r.verdict === "PASS").length ?? 0;
  return <main className="min-h-screen bg-bg px-4 py-8 text-text sm:px-6 lg:px-10"><div className="mx-auto max-w-6xl">
    <Link href="/provenance" className="inline-flex items-center gap-2 text-sm text-muted hover:text-text"><ArrowLeft className="h-4 w-4" /> Back to control room</Link>
    <header className="mt-7"><div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[.16em] text-accent"><ShieldCheck className="h-4 w-4" /> CY-03 benchmark</div><h1 className="mt-2 text-3xl font-semibold tracking-tight">Verification benchmark</h1><p className="mt-2 max-w-3xl text-sm leading-6 text-muted">Six deterministic cases exercise the clean chain and all five required failure families. Artifacts remain metadata-only.</p></header>
    {error && <div className="mt-5 rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">{error}</div>}
    <div className="mt-6 grid gap-4 sm:grid-cols-3"><Metric icon={<Target />} label="Cases" value={String(result?.total ?? "—")} /><Metric icon={<CheckCircle2 />} label="Clean / pass" value={String(passed)} /><Metric icon={<Gauge />} label="Failure families" value={String(result?.failure_families_covered ?? "—")} /></div>
    <section className="mt-5 overflow-hidden rounded-3xl border border-border bg-surface"><div className="border-b border-border px-5 py-4"><div className="text-xs font-semibold uppercase tracking-wider text-accent">Case matrix</div><div className="mt-1 text-xs text-muted">Expected result: clean = PASS; each mutation = FAIL with a localized primary violation.</div></div><div className="divide-y divide-border">{result?.cases.map(row => <div key={row.case_id} className="grid gap-3 px-5 py-4 md:grid-cols-[1.1fr_.9fr_.8fr_1fr]"><div><div className="font-mono text-xs text-faint">{row.case_id}</div><div className="mt-1 text-sm font-semibold capitalize">{row.mutation.replaceAll("_", " ")}</div></div><div className="flex items-center gap-2 text-sm">{row.verdict === "PASS" ? <CheckCircle2 className="h-4 w-4 text-success" /> : <XCircle className="h-4 w-4 text-danger" />}<span>{row.verdict}</span></div><div className="text-sm text-muted">{row.primary_violation ? `${row.primary_violation.family.replaceAll("_", " ")} · ${row.primary_violation.step_id}` : "No violation"}</div><div className="text-sm">{row.top_step ? <span>Top: <b>{row.top_step.step}</b> <span className="font-mono text-xs text-accent">{row.top_step.score.toFixed(2)}</span></span> : "—"}</div></div>)}</div></section>
  </div></main>;
}
function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="rounded-2xl border border-border bg-surface p-4"><div className="flex items-center gap-2 text-faint">{icon}<span className="text-[10px] font-semibold uppercase tracking-wider">{label}</span></div><div className="mt-2 text-lg font-semibold">{value}</div></div>; }
