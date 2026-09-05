"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, RotateCcw } from "lucide-react";
import { Section } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { InvestigationPackage } from "@/lib/api";

// Evidence review state is intentionally local to the analyst workspace.
type ReviewState = {
  status: "unreviewed" | "corroborated" | "requires_verification" | "insufficient_data" | "contradictory";
  note: string;
  alternativeExplanation: string;
};
const STORAGE_PREFIX = "sentry.evidence-reviews:";
function loadReviews(key: string): Record<string, ReviewState> { try { const raw = window.localStorage.getItem(STORAGE_PREFIX + key); return raw ? JSON.parse(raw) : {}; } catch { return {}; } }
function saveReviews(key: string, value: Record<string, ReviewState>) { try { window.localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value)); } catch {} }

export function EvidenceVerification({ data, initialQuery = "" }: { data: InvestigationPackage | null; initialQuery?: string }) {
  const reviewKey = initialQuery.trim() || "current";
  const [reviews, setReviews] = useState<Record<string, ReviewState>>({});
  useEffect(() => { setReviews(loadReviews(reviewKey)); }, [reviewKey]);
  function updateReview(key: string, patch: Partial<ReviewState>) {
    setReviews((current) => {
      const next = { ...current, [key]: { status: "unreviewed", note: "", alternativeExplanation: "", ...(current[key] ?? {}), ...patch } };
      saveReviews(reviewKey, next); return next;
    });
  }
  function resetReviews() { setReviews({}); try { window.localStorage.removeItem(STORAGE_PREFIX + reviewKey); } catch {} }
  const findings = data?.findings ?? [];
  return <Section eyebrow="Human verification" title="Evidence verification & reasoning" action={<Button variant="ghost" size="sm" onClick={resetReviews}><RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Reset</Button>}>
    <div className="mb-4 rounded-xl border border-border bg-bg-2/40 p-3 text-[11px] leading-relaxed text-muted">Review labels are analyst assessments. They do not change deterministic risk calculations.</div>
    <div className="space-y-3">{findings.length ? findings.map((finding, index) => { const key = String(finding.id ?? index); const review = reviews[key] ?? { status: "unreviewed", note: "", alternativeExplanation: "" }; return <article key={key} className="rounded-xl border border-border p-4"><div className="flex gap-3"><span className="mt-0.5 text-accent">{review.status === "corroborated" ? <CheckCircle2 className="h-4 w-4" /> : <CircleAlert className="h-4 w-4" />}</span><div className="min-w-0 flex-1"><div className="text-sm font-semibold text-text">{finding.title}</div><div className="mt-1 text-xs text-muted">{finding.summary}</div><div className="mt-3 flex flex-wrap gap-1.5">{(["corroborated","requires_verification","insufficient_data","contradictory"] as const).map((status) => <button key={status} onClick={() => updateReview(key,{status})} className={`rounded-lg border px-2 py-1 text-[10px] font-medium ${review.status === status ? "border-accent/40 bg-accent/10 text-accent" : "border-border text-faint"}`}>{status.replaceAll("_"," ")}</button>)}</div><textarea value={review.note} onChange={(e) => updateReview(key,{note:e.target.value})} placeholder="Reviewer note" className="mt-3 min-h-16 w-full rounded-lg border border-border bg-bg-2 p-2 text-xs text-text outline-none" /><textarea value={review.alternativeExplanation} onChange={(e) => updateReview(key,{alternativeExplanation:e.target.value})} placeholder="Alternative explanation / limitation" className="mt-2 min-h-16 w-full rounded-lg border border-border bg-bg-2 p-2 text-xs text-text outline-none" /></div></div></article>; }) : <div className="text-sm text-faint">No findings available for verification.</div>}</div>
  </Section>;
}