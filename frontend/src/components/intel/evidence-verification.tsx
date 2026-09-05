"use client";

import { CheckCircle2, CircleHelp, ExternalLink, FileCheck2, MessageSquareText, RotateCcw, ShieldAlert, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { streamInvestigation, type InvestigationReasoning, type InvestigationPackage, type ReasoningCitation } from "@/lib/api";
import { Section } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Chip } from "@/components/ui/chip";
import { ErrorState, EmptyState } from "@/components/ui/states";

export type EvidenceReviewStatus =
  | "unreviewed"
  | "corroborated"
  | "requires_verification"
  | "insufficient_data"
  | "contradictory";

type ReviewState = {
  status: EvidenceReviewStatus;
  note: string;
  alternativeExplanation: string;
};

const STATUS_META: Record<EvidenceReviewStatus, { label: string; tone: "neutral" | "success" | "warning" | "danger" | "info" }> = {
  unreviewed: { label: "Unreviewed", tone: "neutral" },
  corroborated: { label: "Corroborated", tone: "success" },
  requires_verification: { label: "Requires verification", tone: "warning" },
  insufficient_data: { label: "Insufficient data", tone: "neutral" },
  contradictory: { label: "Contradictory", tone: "danger" }
};

const STORAGE_PREFIX = "sentry.evidence-review.v1:";

function evidenceKey(c: ReasoningCitation, index: number): string {
  return `${c.source_name}:${c.source_record_id ?? "no-record"}:${c.related_tender ?? "no-tender"}:${index}`;
}

function loadReviews(storageKey: string): Record<string, ReviewState> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_PREFIX + storageKey);
    return raw ? (JSON.parse(raw) as Record<string, ReviewState>) : {};
  } catch {
    return {};
  }
}

function saveReviews(storageKey: string, reviews: Record<string, ReviewState>) {
  try {
    window.localStorage.setItem(STORAGE_PREFIX + storageKey, JSON.stringify(reviews));
  } catch {
    /* local-only review draft */
  }
}

export function EvidenceVerification({ initialQuery = "" }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reasoning, setReasoning] = useState<InvestigationReasoning | null>(null);
  const [pkg, setPkg] = useState<InvestigationPackage | null>(null);
  const [reviews, setReviews] = useState<Record<string, ReviewState>>({});
  const [selected, setSelected] = useState<string | null>(null);

  const citations = reasoning?.evidence_ledger ?? [];
  const reviewKey = useMemo(() => (query.trim() ? query.trim().toLowerCase() : "empty"), [query]);

  useEffect(() => {
    setReviews(loadReviews(reviewKey));
  }, [reviewKey]);

  useEffect(() => {
    if (!initialQuery.trim()) return;
    run(initialQuery.trim());
    // Initial query is intentionally one-shot for the page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateReview(key: string, patch: Partial<ReviewState>) {
    setReviews((current) => {
      const next = {
        ...current,
        [key]: {
          status: "unreviewed",
          note: "",
          alternativeExplanation: "",
          ...current[key],
          ...patch
        }
      };
      saveReviews(reviewKey, next);
      return next;
    });
  }

  function resetReviews() {
    setReviews({});
    try {
      window.localStorage.removeItem(STORAGE_PREFIX + reviewKey);
    } catch {
      /* ignore */
    }
  }

  function run(target: string) {
    setQuery(target);
    setRunning(true);
    setError(null);
    setReasoning(null);
    setPkg(null);
    setSelected(null);

    streamInvestigation(target, {
      onStep: () => undefined,
      onCandidates: () => undefined,
      onReport: (report) => {
        setPkg(report.package);
        setReasoning(report.reasoning);
        setRunning(false);
      },
      onError: (message) => {
        setError(message);
        setRunning(false);
      }
    });
  }

  const counts = useMemo(() => {
    const out = { unreviewed: 0, corroborated: 0, requires_verification: 0, insufficient_data: 0, contradictory: 0 } as Record<EvidenceReviewStatus, number>;
    citations.forEach((c, index) => {
      const key = evidenceKey(c, index);
      const status = reviews[key]?.status ?? "unreviewed";
      out[status] += 1;
    });
    return out;
  }, [citations, reviews]);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-surface/70 p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <div className="min-w-0 flex-1">
            <div className="t-label text-accent">Phase 5 · Evidence verification</div>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-text">Corroborate the evidence before assessment.</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
              Review each cited item against its original source. Record a human review state, the reason for it, and any alternative explanation without changing SENTRY's deterministic risk assessment.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            {(Object.keys(STATUS_META) as EvidenceReviewStatus[]).map((status) => (
              <div key={status} className="rounded-xl border border-border bg-bg-2/50 px-3 py-2">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-faint">{STATUS_META[status].label}</div>
                <div className="mt-1 text-lg font-semibold tabular text-text">{counts[status]}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && query.trim()) run(query.trim());
            }}
            placeholder="Enter a verified company, buyer, or tender"
            className="h-10 flex-1 rounded-xl border border-border bg-bg px-3.5 text-sm text-text outline-none placeholder:text-faint focus:border-accent/50"
          />
          <Button onClick={() => query.trim() && run(query.trim())} loading={running} icon={<FileCheck2 className="h-4 w-4" />}>
            Load evidence
          </Button>
          <Button variant="subtle" onClick={resetReviews} icon={<RotateCcw className="h-4 w-4" />} disabled={!query.trim()}>
            Reset review
          </Button>
        </div>
      </div>

      {error && <ErrorState title="Evidence review could not load" message={error} />}

      {!reasoning && !running && !error && (
        <EmptyState icon={<FileCheck2 className="h-5 w-5" />} title="No investigation loaded" message="Load a verified procurement entity to begin evidence verification." />
      )}

      {running && (
        <Section eyebrow="Verification" title="Loading grounded evidence">
          <div className="space-y-2 text-sm text-muted">
            <div className="h-3 w-2/3 animate-pulse rounded bg-surface-2" />
            <div className="h-3 w-1/2 animate-pulse rounded bg-surface-2" />
            <div className="h-3 w-3/4 animate-pulse rounded bg-surface-2" />
          </div>
        </Section>
      )}

      {reasoning && pkg && (
        <>
          <Section eyebrow="Assessment boundary" title="What this reviewer can change">
            <div className="grid gap-3 md:grid-cols-3">
              <BoundaryCard icon={<CheckCircle2 className="h-4 w-4" />} title="Corroboration" text="Record whether the cited evidence is supported by the original source." />
              <BoundaryCard icon={<CircleHelp className="h-4 w-4" />} title="Open questions" text="Flag evidence that still needs an official document or independent check." />
              <BoundaryCard icon={<ShieldAlert className="h-4 w-4" />} title="No risk override" text="Review annotations never rewrite the deterministic risk engine or create a verdict." />
            </div>
          </Section>

          <Section
            eyebrow="Cited evidence"
            title={`${citations.length} evidence items · ${counts.corroborated} corroborated`}
            action={<Chip tone={counts.contradictory > 0 ? "danger" : counts.requires_verification > 0 ? "warning" : "success"}>{counts.unreviewed > 0 ? `${counts.unreviewed} unreviewed` : "Review pass complete"}</Chip>}
          >
            {citations.length === 0 ? (
              <EmptyState message="The investigation produced no evidence citations to verify." />
            ) : (
              <div className="space-y-3">
                {citations.map((citation, index) => {
                  const key = evidenceKey(citation, index);
                  const review = reviews[key] ?? { status: "unreviewed", note: "", alternativeExplanation: "" };
                  const active = selected === key;
                  return (
                    <article key={key} className={`rounded-2xl border bg-bg-2/40 ${active ? "border-accent/45" : "border-border"}`}>
                      <div className="flex flex-col gap-4 p-4 lg:flex-row lg:items-start">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <Chip tone={STATUS_META[review.status].tone}>{STATUS_META[review.status].label}</Chip>
                            <span className="text-[11px] text-faint">{citation.source_name}</span>
                            {citation.related_tender && <span className="font-mono text-[10px] text-faint">{citation.related_tender}</span>}
                          </div>
                          <h3 className="mt-2 text-[14px] font-semibold text-text">{citation.label}</h3>
                          <div className="mt-2 grid gap-2 sm:grid-cols-3 text-[11px]">
                            <Meta label="Quality" value={`${citation.quality}/100`} />
                            <Meta label="Support" value={`${Math.round(citation.confidence * 100)}%`} />
                            <Meta label="Record" value={citation.source_record_id ?? "Not available"} />
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {(Object.keys(STATUS_META) as EvidenceReviewStatus[]).filter((status) => status !== "unreviewed").map((status) => (
                              <button
                                key={status}
                                type="button"
                                onClick={() => updateReview(key, { status })}
                                className={`rounded-lg border px-2.5 py-1.5 text-[11px] font-medium transition ${review.status === status ? "border-accent/45 bg-accent/[0.08] text-accent" : "border-border bg-surface text-muted hover:border-border-strong hover:text-text"}`}
                              >
                                {STATUS_META[status].label}
                              </button>
                            ))}
                            <button
                              type="button"
                              onClick={() => setSelected(active ? null : key)}
                              className="rounded-lg border border-border bg-surface px-2.5 py-1.5 text-[11px] font-medium text-muted hover:border-border-strong hover:text-text"
                            >
                              {active ? "Close review" : "Add reviewer note"}
                            </button>
                            {(citation.source_url || citation.document_url) && (
                              <a
                                href={citation.source_url ?? citation.document_url ?? "#"}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 rounded-lg border border-accent/30 bg-accent/[0.06] px-2.5 py-1.5 text-[11px] font-semibold text-accent hover:bg-accent/[0.1]"
                              >
                                <ExternalLink className="h-3 w-3" /> Original source
                              </a>
                            )}
                          </div>
                        </div>

                        {active && (
                          <div className="w-full rounded-xl border border-border bg-surface/60 p-3 lg:max-w-sm">
                            <label className="block text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">Reviewer note</label>
                            <textarea
                              value={review.note}
                              onChange={(event) => updateReview(key, { note: event.target.value })}
                              rows={3}
                              placeholder="What did the original source confirm, leave unclear, or contradict?"
                              className="mt-2 w-full resize-none rounded-lg border border-border bg-bg px-3 py-2 text-xs leading-relaxed text-text outline-none placeholder:text-faint focus:border-accent/50"
                            />
                            <label className="mt-3 block text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">Alternative explanation</label>
                            <textarea
                              value={review.alternativeExplanation}
                              onChange={(event) => updateReview(key, { alternativeExplanation: event.target.value })}
                              rows={3}
                              placeholder="Record a plausible explanation supported by evidence."
                              className="mt-2 w-full resize-none rounded-lg border border-border bg-bg px-3 py-2 text-xs leading-relaxed text-text outline-none placeholder:text-faint focus:border-accent/50"
                            />
                            <div className="mt-3 flex items-center gap-2 text-[10.5px] text-faint">
                              <MessageSquareText className="h-3.5 w-3.5 text-accent" /> Stored locally as a review draft on this device.
                            </div>
                          </div>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </Section>

          <Section eyebrow="Reasoning integrity" title="Evidence → finding boundary">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-surface/50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-text"><CheckCircle2 className="h-4 w-4 text-success" /> Source-grounded</div>
                <p className="mt-2 text-xs leading-relaxed text-muted">{reasoning.grounding.fully_grounded ? "The current reasoning payload is fully grounded in cited evidence." : "The current reasoning payload is not fully grounded; unresolved citations remain visible for review."}</p>
              </div>
              <div className="rounded-xl border border-border bg-surface/50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-text"><XCircle className="h-4 w-4 text-warning" /> Contradictions stay explicit</div>
                <p className="mt-2 text-xs leading-relaxed text-muted">A contradictory review state is preserved as a review outcome; it does not silently delete, downgrade, or rewrite the underlying source record.</p>
              </div>
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

function BoundaryCard({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface/50 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-text">{icon}<span>{title}</span></div>
      <p className="mt-2 text-xs leading-relaxed text-muted">{text}</p>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface/40 px-2.5 py-2">
      <div className="text-[9px] font-semibold uppercase tracking-wide text-faint">{label}</div>
      <div className="mt-1 truncate font-medium text-text">{value}</div>
    </div>
  );
}
