"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function InvestigationLauncher({ suggestions }: { suggestions: string[] }) {
  const router = useRouter();
  const [value, setValue] = useState("");

  function launch(q: string) {
    const query = q.trim();
    if (query) router.push(`/?q=${encodeURIComponent(query)}`);
  }

  return (
    <div className="panel relative overflow-hidden p-6 md:p-8">
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
          <Sparkles className="h-3.5 w-3.5" />
          New investigation
        </div>
        <h2 className="text-lg font-semibold text-text">
          Investigate any buyer, supplier, tender, or contract
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-muted">
          SENTRY plans connectors, executes against the local database, resolves entities, builds the
          relationship graph, and surfaces risk indicators — all from a single query.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            launch(value);
          }}
          className="mt-5 flex flex-col gap-2 sm:flex-row"
        >
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. Tata Projects, Ministry of Railways, tender reference…"
            className="h-12 flex-1 rounded-xl border border-border bg-bg/60 px-4 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/60"
          />
          <button
            type="submit"
            className="flex h-12 items-center justify-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-bg transition hover:bg-accent-hi"
          >
            Run investigation
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        {suggestions.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-faint">Quick start:</span>
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => launch(s)}
                className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted transition hover:border-accent/40 hover:text-accent"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
