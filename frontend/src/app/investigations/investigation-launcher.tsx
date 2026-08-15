"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function InvestigationLauncher({ suggestions }: { suggestions: string[] }) {
  const router = useRouter();
  const [value, setValue] = useState("");

  function launch(q: string) {
    const query = q.trim();
    if (query) router.push(`/investigate?q=${encodeURIComponent(query)}`);
  }

  return (
    <div className="panel relative overflow-hidden p-8 md:p-10">
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent/10 blur-3xl" />
      <div className="relative">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent">
          <Sparkles className="h-3.5 w-3.5" />
          New investigation
        </div>
        <h2 className="text-xl font-semibold tracking-[-0.01em] text-text">
          Investigate any buyer, supplier, tender, or contract
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          SENTRY plans connectors, executes against the local database, resolves entities, builds the
          relationship graph, and surfaces risk indicators — all from a single query.
        </p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            launch(value);
          }}
          className="mt-7 flex flex-col gap-2.5 sm:flex-row"
        >
          <Input
            fieldSize="lg"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. Tata Projects, Ministry of Railways, tender reference…"
            className="flex-1"
          />
          <Button
            variant="primary"
            size="lg"
            type="submit"
            className="px-6"
            trailing={<ArrowRight className="h-4 w-4" />}
          >
            Run investigation
          </Button>
        </form>

        {suggestions.length > 0 && (
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="text-xs text-faint">Quick start:</span>
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => launch(s)}
                className="rounded-full border border-border bg-surface px-3 py-1 text-xs text-muted transition-colors duration-200 hover:border-accent/40 hover:text-accent"
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
