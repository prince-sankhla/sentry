"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, CircleDot, GitBranch, LockKeyhole, RefreshCw, ShieldCheck, XCircle } from "lucide-react";
import ReactFlow, { Background, Controls, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://127.0.0.1:8000";
const CHAIN = ["fetch", "deps", "compile", "test", "package", "scan", "sign", "publish"];
const MUTATIONS = ["clean", "missing_step", "hash_mismatch", "unauthorized_signer", "unexpected_product", "wrong_order"];

type Verification = {
  verdict: "PASS" | "FAIL";
  suspicious_steps: Array<{ step_id: string; step: string; score: number }>;
  primary_violation: { family: string; invariant: string; step_id: string; evidence: Record<string, unknown> } | null;
  step_results: Array<{ step_id: string; name: string; status: string; reasons: string[] }>;
  violations: Array<{ family: string; step_id: string; invariant: string; evidence: Record<string, unknown>; score: number }>;
  explanation: string;
};

type Payload = { case: { case_id: string; steps: Array<Record<string, unknown>> }; verification: Verification };

export default function ProvenancePage() {
  const [mutation, setMutation] = useState("clean");
  const [payload, setPayload] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(selected: string = mutation) {
    setLoading(true); setError(null);
    try {
      const q = selected === "clean" ? "" : `?mutation=${selected}`;
      const response = await fetch(`${BACKEND_URL}/api/provenance/demo${q}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      setPayload(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to reach provenance engine");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  const nodes = useMemo<Node[]>(() => (payload?.case.steps ?? []).map((step, index) => ({
    id: String(step.id), position: { x: index * 190, y: 60 },
    data: { label: <div className="min-w-[150px]"><div className="text-[10px] uppercase tracking-wider text-faint">{String(step.id)}</div><div className="mt-1 font-semibold">{String(step.name)}</div><div className="mt-1 font-mono text-[9px] text-faint">{String(step.product_hash).slice(0, 12)}…</div></div> },
    className: "rounded-2xl border border-border bg-surface px-3 py-3 text-text shadow-sm",
  })), [payload]);

  const edges = useMemo<Edge[]>(() => nodes.slice(0, -1).map((n, i) => ({ id: `${n.id}-${nodes[i + 1].id}`, source: n.id, target: nodes[i + 1].id, animated: false })), [nodes]);

  return (
    <main className="min-h-screen bg-bg px-4 py-6 text-text sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1500px]">
        <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-accent"><ShieldCheck className="h-4 w-4" /> CY-03 · Provenance Verification</div>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Supply-chain evidence control room</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">Verify the canonical 8-step build chain without executing artifacts, then rank the most suspicious provenance step and expose the violated invariant.</p>
          </div>
          <div className="flex gap-2">
            <select value={mutation} onChange={(e) => { setMutation(e.target.value); void load(e.target.value); }} className="h-10 rounded-xl border border-border bg-surface px-3 text-sm outline-none">
              {MUTATIONS.map((item) => <option key={item} value={item}>{item.replaceAll("_", " ")}</option>)}
            </select>
            <button onClick={() => void load()} className="inline-flex h-10 items-center gap-2 rounded-xl border border-border bg-surface px-3 text-sm font-medium hover:bg-surface-2"><RefreshCw className="h-4 w-4" /> Verify</button>
          </div>
        </header>

        {error ? <div className="mb-5 rounded-2xl border border-danger/30 bg-danger/5 p-4 text-sm text-danger">{error}. Set NEXT_PUBLIC_BACKEND_URL to the deployed FastAPI origin.</div> : null}

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={payload?.verification.verdict === "PASS" ? <CheckCircle2 /> : <XCircle />} label="Verdict" value={loading ? "…" : payload?.verification.verdict ?? "—"} danger={payload?.verification.verdict === "FAIL"} />
          <Metric icon={<AlertTriangle />} label="Violations" value={String(payload?.verification.violations.length ?? 0)} />
          <Metric icon={<CircleDot />} label="Top suspicious step" value={payload?.verification.suspicious_steps[0]?.step ?? "None"} />
          <Metric icon={<LockKeyhole />} label="Signature policy" value="HMAC / Ed25519" />
        </div>

        <section className="mt-5 overflow-hidden rounded-3xl border border-border bg-surface">
          <div className="flex items-center justify-between border-b border-border px-5 py-4"><div><div className="text-xs font-semibold uppercase tracking-wider text-accent">Provenance chain</div><div className="mt-1 text-sm text-muted">{CHAIN.join(" → ")}</div></div><GitBranch className="h-5 w-5 text-faint" /></div>
          <div className="h-[270px] bg-bg-2/40">
            <ReactFlow nodes={nodes} edges={edges} fitView fitViewOptions={{ padding: 0.12 }} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false}><Background /><Controls /></ReactFlow>
          </div>
        </section>

        <div className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
          <section className="rounded-3xl border border-border bg-surface p-5">
            <div className="text-xs font-semibold uppercase tracking-wider text-accent">Primary invariant</div>
            <h2 className="mt-2 text-lg font-semibold">{payload?.verification.primary_violation?.family?.replaceAll("_", " ") ?? "All invariants verified"}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{payload?.verification.primary_violation?.invariant ?? "The 8 required steps, deterministic artifact hashes, products, signer authorization and signatures are consistent."}</p>
            <div className="mt-4 rounded-2xl border border-border bg-bg-2 p-4 font-mono text-xs leading-6 text-muted">{payload?.verification.explanation ?? ""}</div>
          </section>
          <section className="rounded-3xl border border-border bg-surface p-5">
            <div className="text-xs font-semibold uppercase tracking-wider text-accent">Fault localization</div>
            <div className="mt-3 space-y-2">
              {payload?.verification.suspicious_steps.length ? payload.verification.suspicious_steps.map((step, index) => <div key={step.step_id} className="flex items-center gap-3 rounded-xl border border-border bg-bg-2 px-3 py-2.5"><span className="font-mono text-xs text-faint">#{index + 1}</span><span className="flex-1 text-sm font-medium">{step.step}</span><span className="font-mono text-xs text-accent">{step.score.toFixed(2)}</span></div>) : <div className="text-sm text-muted">No suspicious steps — clean case.</div>}
            </div>
          </section>
        </div>

        <section className="mt-5 rounded-3xl border border-border bg-surface p-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-accent">Step-level evidence</div>
          <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
            {(payload?.verification.step_results ?? []).map((step) => <div key={step.step_id} className="rounded-2xl border border-border bg-bg-2 p-3"><div className="flex items-center justify-between"><span className="font-mono text-xs text-faint">{step.step_id}</span>{step.status === "pass" ? <CheckCircle2 className="h-4 w-4 text-success" /> : <XCircle className="h-4 w-4 text-danger" />}</div><div className="mt-2 text-sm font-semibold">{step.name}</div><div className="mt-2 text-xs leading-5 text-muted">{step.reasons.length ? step.reasons.join(" · ") : "All checks passed"}</div></div>)}
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ icon, label, value, danger = false }: { icon: React.ReactNode; label: string; value: string; danger?: boolean }) {
  return <div className={`rounded-2xl border p-4 ${danger ? "border-danger/30 bg-danger/5" : "border-border bg-surface"}`}><div className="flex items-center gap-2 text-faint">{icon}<span className="text-[10px] font-semibold uppercase tracking-wider">{label}</span></div><div className="mt-2 text-lg font-semibold">{value}</div></div>;
}
