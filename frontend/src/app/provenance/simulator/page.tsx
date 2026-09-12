"use client";

import { useState } from "react";
import Link from "next/link";
import { FlaskConical, ShieldCheck, ArrowLeft } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";
const MUTATIONS = ["clean", "missing_step", "hash_mismatch", "unauthorized_signer", "unexpected_product", "wrong_order"];

type Result = { case: { case_id: string; steps: Array<Record<string, unknown>> }; verification: { verdict: string; explanation: string; suspicious_steps: Array<{ step_id: string; step: string; score: number }>; primary_violation: { family: string; invariant: string } | null } };

export default function ProvenanceSimulatorPage() {
  const [mutation, setMutation] = useState("hash_mismatch");
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  async function run() {
    setBusy(true);
    try { const r = await fetch(`${BACKEND_URL}/api/provenance/demo${mutation === "clean" ? "" : `?mutation=${mutation}`}`, { cache: "no-store" }); if (!r.ok) throw new Error(String(r.status)); setResult(await r.json()); } finally { setBusy(false); }
  }
  return <main className="min-h-screen bg-bg px-4 py-8 text-text sm:px-6 lg:px-10"><div className="mx-auto max-w-5xl"><Link href="/provenance" className="inline-flex items-center gap-2 text-sm text-muted hover:text-text"><ArrowLeft className="h-4 w-4" /> Back to control room</Link><div className="mt-7 flex items-start gap-4"><div className="grid h-12 w-12 place-items-center rounded-2xl border border-accent/25 bg-accent/10 text-accent"><FlaskConical /></div><div><div className="text-[11px] font-semibold uppercase tracking-[.16em] text-accent">CY-03 laboratory</div><h1 className="mt-1 text-3xl font-semibold">Mutation simulator</h1><p className="mt-2 text-sm text-muted">Generate a deterministic clean or mutated provenance case and inspect how SENTRY localizes the fault.</p></div></div><section className="mt-7 rounded-3xl border border-border bg-surface p-5"><div className="flex flex-col gap-3 sm:flex-row"><select value={mutation} onChange={e => setMutation(e.target.value)} className="h-11 flex-1 rounded-xl border border-border bg-bg-2 px-3 text-sm">{MUTATIONS.map(m => <option key={m} value={m}>{m.replaceAll("_", " ")}</option>)}</select><button onClick={run} disabled={busy} className="h-11 rounded-xl bg-accent px-5 text-sm font-semibold text-bg disabled:opacity-50">{busy ? "Verifying…" : "Run mutation"}</button></div></section>{result && <section className="mt-5 grid gap-5 lg:grid-cols-2"><div className="rounded-3xl border border-border bg-surface p-5"><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-accent"><ShieldCheck className="h-4 w-4" /> Result</div><div className="mt-4 text-2xl font-semibold">{result.verification.verdict}</div><p className="mt-2 text-sm leading-6 text-muted">{result.verification.explanation}</p>{result.verification.primary_violation && <div className="mt-4 rounded-2xl border border-danger/20 bg-danger/5 p-4"><div className="text-xs font-semibold uppercase text-danger">Primary violation</div><div className="mt-1 font-semibold">{result.verification.primary_violation.family.replaceAll("_", " ")}</div><p className="mt-1 text-xs leading-5 text-muted">{result.verification.primary_violation.invariant}</p></div>}</div><div className="rounded-3xl border border-border bg-surface p-5"><div className="text-xs font-semibold uppercase tracking-wider text-accent">Ranked suspicious steps</div><div className="mt-3 space-y-2">{result.verification.suspicious_steps.length ? result.verification.suspicious_steps.map((s, i) => <div key={s.step_id} className="flex items-center gap-3 rounded-xl border border-border bg-bg-2 px-3 py-3"><span className="font-mono text-xs text-faint">#{i + 1}</span><span className="flex-1 text-sm font-medium">{s.step}</span><span className="font-mono text-xs text-accent">{s.score.toFixed(2)}</span></div>) : <p className="text-sm text-muted">Clean case — no suspicious steps.</p>}</div></div></section>}</div></main>;
}
