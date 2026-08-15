"use client";

import { Check, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Toggle } from "@/components/ui/input";

/**
 * Local-only analyst preferences. Persisted to localStorage — the backend has
 * no settings endpoint, so these are client-side workspace defaults that other
 * client components can read (key: "sentry.prefs").
 */
type Prefs = {
  resultLimit: number;
  autoWebEvidence: boolean;
  graphDepth: number;
};

const DEFAULTS: Prefs = { resultLimit: 25, autoWebEvidence: false, graphDepth: 2 };
const KEY = "sentry.prefs";

export function SettingsPreferences() {
  const [prefs, setPrefs] = useState<Prefs>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setPrefs({ ...DEFAULTS, ...JSON.parse(raw) });
    } catch {
      /* ignore corrupt storage */
    }
  }, []);

  function update<K extends keyof Prefs>(key: K, value: Prefs[K]) {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
      setSaved(true);
      setTimeout(() => setSaved(false), 1400);
    } catch {
      /* ignore */
    }
  }

  function reset() {
    setPrefs(DEFAULTS);
    try {
      localStorage.setItem(KEY, JSON.stringify(DEFAULTS));
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="space-y-5">
      <Row
        label="Default result limit"
        hint="Records fetched per connector when running an investigation."
      >
        <select
          value={prefs.resultLimit}
          onChange={(e) => update("resultLimit", Number(e.target.value))}
          className="h-10 rounded-xl border border-border bg-bg-2 px-3 text-sm text-text outline-none transition-all duration-200 focus:border-accent/60 focus:ring-4 focus:ring-accent/10"
        >
          {[10, 25, 50, 100].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </Row>

      <Row label="Default graph depth" hint="Relationship hops expanded in the graph explorer.">
        <select
          value={prefs.graphDepth}
          onChange={(e) => update("graphDepth", Number(e.target.value))}
          className="h-10 rounded-xl border border-border bg-bg-2 px-3 text-sm text-text outline-none transition-all duration-200 focus:border-accent/60 focus:ring-4 focus:ring-accent/10"
        >
          {[1, 2, 3].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </Row>

      <Row
        label="Auto-collect web evidence"
        hint="Run open-source web search automatically with each investigation."
      >
        <Toggle
          checked={prefs.autoWebEvidence}
          onChange={(next) => update("autoWebEvidence", next)}
          label="Auto-collect web evidence"
        />
      </Row>

      <div className="flex items-center justify-between border-t border-border pt-5">
        <span className="flex items-center gap-1.5 text-xs text-success">
          {saved && (
            <>
              <Check className="h-3.5 w-3.5" /> Saved locally
            </>
          )}
        </span>
        <Button
          variant="subtle"
          size="sm"
          onClick={reset}
          icon={<RotateCcw className="h-3.5 w-3.5" />}
        >
          Reset to defaults
        </Button>
      </div>
    </div>
  );
}

function Row({
  label,
  hint,
  children
}: {
  label: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <div className="text-sm font-medium text-text">{label}</div>
        <div className="mt-0.5 text-xs text-faint">{hint}</div>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}
