"use client";

/**
 * AI Investigation Status — Command Center read-out of the reasoning layer.
 *
 * Reports which grounded reasoning engine is live (Claude / OpenRouter / OpenAI
 * / Gemini) or the deterministic composer fallback, plus the configured
 * fall-through order. Provenance-first: SENTRY is always explicit about which
 * engine phrased a conclusion. Consumes GET /api/investigations/providers.
 */

import { useEffect, useState } from "react";
import { Cpu, ShieldCheck } from "lucide-react";
import { getLLMProviders, type LLMProviderStatus } from "@/lib/api";
import { providerDisplayName } from "@/components/intel/provider-badge";

export function AiStatus() {
  const [status, setStatus] = useState<LLMProviderStatus | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    getLLMProviders()
      .then((s) => alive && setStatus(s))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, []);

  if (failed) {
    return <p className="text-sm text-faint">Reasoning engine status unavailable.</p>;
  }
  if (!status) {
    return (
      <div className="space-y-2.5">
        <div className="shimmer h-14 rounded-xl" />
        <div className="shimmer h-9 rounded-lg" />
      </div>
    );
  }

  const live = status.mode === "llm";
  const primary = status.providers[0];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 rounded-xl border border-border bg-bg-2/50 p-3.5">
        <span
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg border ${
            live
              ? "border-accent/30 bg-accent/[0.08] text-accent"
              : "border-border-strong bg-surface-2 text-muted"
          }`}
        >
          {live ? <ShieldCheck className="h-5 w-5" /> : <Cpu className="h-5 w-5" />}
        </span>
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-text">
            {live ? providerDisplayName(primary) : "Deterministic Composer"}
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-faint">
            <span
              className={`relative h-1.5 w-1.5 rounded-full ${live ? "bg-success" : "bg-warning"}`}
            >
              {live && <span className="absolute inset-0 rounded-full bg-success pulse-live" />}
            </span>
            {live ? "Grounded reasoning online" : "Evidence-only fallback active"}
          </div>
        </div>
      </div>

      <div>
        <div className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
          Reasoning fallback order
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {status.fallback_order.map((p, i) => {
            const active = status.providers.includes(p);
            return (
              <span key={p} className="flex items-center gap-1.5">
                {i > 0 && <span className="text-border-strong">›</span>}
                <span
                  className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                    active
                      ? "border-accent/30 bg-accent/10 text-accent"
                      : "border-border bg-bg-2 text-faint"
                  }`}
                >
                  {providerDisplayName(p)}
                </span>
              </span>
            );
          })}
        </div>
      </div>

      <p className="text-[11px] leading-relaxed text-faint">
        Conclusions are derived from the evidence ledger; the engine only phrases findings the
        backend has already proven.
      </p>
    </div>
  );
}
