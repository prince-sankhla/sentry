"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ClipboardCheck, FileText, Send, ShieldCheck } from "lucide-react";
import { Section } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { InvestigationPackage, InvestigationReasoning } from "@/lib/api";

export type ReviewHandoffDraft = { subject: string; review_reason: string; findings: string[]; evidence_count: number; outstanding_evidence: string[]; alternative_explanations: string[]; reviewer_note: string };
const STORAGE_KEY = "sentry.review-handoff";
export function ReviewHandoff({ pkg, reasoning }: { pkg: InvestigationPackage; reasoning: InvestigationReasoning }) {
  const [reviewerNote, setReviewerNote] = useState(""); const [submitted, setSubmitted] = useState(false);
  const draft = useMemo<ReviewHandoffDraft>(() => {
    const findings = (reasoning.findings ?? []).map((f) => f.title).filter(Boolean);
    const outstanding = (pkg.risk_assessment_v2?.indicators ?? []).flatMap((i) => i.required_evidence ?? []).filter(Boolean);
    const explanations = (reasoning.evidence_challenge?.challenges ?? []).flatMap((c) => c.explanations ?? []).map((e) => e.explanation).filter(Boolean);
    return { subject: reasoning.subject || pkg.plan.query, review_reason: "Request official review of the evidence assembled by SENTRY. This handoff is a review lead, not an allegation or adjudication.", findings, evidence_count: reasoning.evidence_ledger.length, outstanding_evidence: Array.from(new Set(outstanding)), alternative_explanations: Array.from(new Set(explanations)), reviewer_note: reviewerNote.trim() };
  }, [pkg, reasoning, reviewerNote]);
  function saveDraft() { try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...draft, saved_at: new Date().toISOString() })); } finally { setSubmitted(true); } }
  function exportJson() { const blob = new Blob([JSON.stringify(draft, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const anchor = document.createElement("a"); anchor.href = url; anchor.download = `sentry-review-handoff-${slugify(draft.subject)}.json`; anchor.click(); URL.revokeObjectURL(url); }
  return <Section eyebrow="Official review" title="Prepare review handoff" action={<ShieldCheck className="h-4 w-4 text-accent" />}>
    <div className="rounded-xl border border-border bg-bg-2/40 p-4"><div className="flex items-start gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-accent/25 bg-accent/10 text-accent"><ClipboardCheck className="h-4 w-4" /></span><div className="min-w-0"><div className="text-sm font-semibold text-text">{draft.subject}</div><p className="mt-1 text-xs leading-relaxed text-muted">{draft.review_reason}</p></div></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3"><Stat label="Findings" value={draft.findings.length} /><Stat label="Evidence items" value={draft.evidence_count} /><Stat label="Open evidence requests" value={draft.outstanding_evidence.length} /></div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2"><ReviewList title="Observed review leads" items={draft.findings} empty="No findings are currently recorded." /><ReviewList title="Evidence still required" items={draft.outstanding_evidence} empty="No additional evidence requests were generated." /></div>
      <textarea value={reviewerNote} onChange={(e) => setReviewerNote(e.target.value)} placeholder="Reviewer note" className="mt-4 min-h-24 w-full rounded-xl border border-border bg-bg-2 p-3 text-xs text-text outline-none" />
      <div className="mt-4 flex flex-wrap gap-2"><Button onClick={saveDraft}><Send className="mr-1.5 h-3.5 w-3.5" /> {submitted ? "Saved locally" : "Save review draft"}</Button><Button variant="ghost" onClick={exportJson}><FileText className="mr-1.5 h-3.5 w-3.5" /> Export JSON</Button></div>
    </div><div className="mt-3 flex gap-2 rounded-xl border border-warning/20 bg-warning/[0.04] p-3 text-[11px] text-muted"><CheckCircle2 className="h-4 w-4 shrink-0 text-warning" />This workflow prepares a human-review lead only. It does not submit to a government system or adjudicate wrongdoing.</div>
  </Section>;
}
function Stat({label,value}:{label:string;value:number}) { return <div className="rounded-xl border border-border bg-surface px-3 py-2"><div className="text-[9px] uppercase tracking-wide text-faint">{label}</div><div className="mt-1 text-sm font-semibold tabular text-text">{value}</div></div>; }
function ReviewList({title,items,empty}:{title:string;items:string[];empty:string}) { return <div className="rounded-xl border border-border bg-surface p-3"><div className="text-xs font-semibold text-text">{title}</div>{items.length ? <ul className="mt-2 space-y-1.5">{items.slice(0,8).map((item,index)=><li key={`${item}-${index}`} className="text-[11px] leading-relaxed text-muted">• {item}</li>)}</ul> : <div className="mt-2 text-[11px] text-faint">{empty}</div>}</div>; }
function slugify(value:string) { return value.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,60) || "case"; }