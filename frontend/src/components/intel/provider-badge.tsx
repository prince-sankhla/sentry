"use client";

/**
 * ProviderBadge — live attribution of which reasoning engine answered.
 *
 * SENTRY is always transparent about provenance: a live LLM (Claude / OpenRouter
 * / OpenAI / Gemini) or the deterministic composer. This badge renders that state
 * compactly with an online/fallback pulse, and doubles as the Provider Status
 * chip fed by the /providers endpoint.
 */

import { motion } from "framer-motion";
import { Cpu, Sparkles } from "lucide-react";

/** Map a raw backend provider key to an analyst-facing display name. */
export function providerDisplayName(provider: string | null | undefined, model?: string | null): string {
  const key = (provider ?? "").toLowerCase();
  const label =
    key.includes("anthropic") || key.includes("claude")
      ? "Claude"
      : key.includes("openrouter")
        ? "OpenRouter"
        : key.includes("openai") || key.includes("gpt")
          ? "OpenAI"
          : key.includes("gemini") || key.includes("google")
            ? "Gemini"
            : provider
              ? provider.charAt(0).toUpperCase() + provider.slice(1)
              : "Deterministic";
  if (model && label !== "Deterministic") {
    // Trim provider prefixes / long ids to a readable model name.
    const short = model.split("/").pop() ?? model;
    return `${label} ${short}`;
  }
  return label;
}

export function ProviderBadge({
  generatedBy,
  provider,
  model,
  size = "sm"
}: {
  generatedBy: "llm" | "deterministic";
  provider?: string | null;
  model?: string | null;
  size?: "sm" | "md";
}) {
  const live = generatedBy === "llm";
  const label = live ? providerDisplayName(provider, model) : "Deterministic";
  const state = live ? "ONLINE" : "FALLBACK ACTIVE";
  const pad = size === "md" ? "px-3 py-1.5 text-xs" : "px-2.5 py-1 text-[11px]";

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.94 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={`inline-flex items-center gap-2 rounded-full border font-medium ${pad} ${
        live ? "border-accent/40 bg-accent/[0.08] text-accent" : "border-border-strong bg-surface-2 text-muted"
      }`}
    >
      <span className="relative grid place-items-center">
        {live ? <Sparkles className="h-3.5 w-3.5" /> : <Cpu className="h-3.5 w-3.5" />}
      </span>
      <span className="truncate">{label}</span>
      <span className="inline-flex items-center gap-1 border-l border-current/20 pl-2 text-[9px] font-semibold uppercase tracking-wide opacity-80">
        <span className={`relative h-1.5 w-1.5 rounded-full ${live ? "bg-success" : "bg-warning"}`}>
          {live && <span className="absolute inset-0 rounded-full bg-success pulse-live" />}
        </span>
        {state}
      </span>
    </motion.span>
  );
}
