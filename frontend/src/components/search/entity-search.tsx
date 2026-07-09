"use client";

/**
 * Enterprise entity-search experience.
 *
 * Investigations must never start from arbitrary free text — only from a
 * verified canonical procurement entity. This component resolves what the user
 * types against POST /api/investigations/resolve-entity (debounced), presents
 * ranked suggestions, and keeps the Investigate action disabled until one
 * suggestion is explicitly selected and locked.
 *
 * It also persists local search history: recent searches, recent investigations
 * and pinned entities. It renders no investigation data and calls only the
 * existing resolve-entity API — it is pure search UX.
 */

import {
  ArrowRight,
  Building2,
  Check,
  Gavel,
  Landmark,
  Loader2,
  Pin,
  PinOff,
  RotateCcw,
  Search,
  Sparkles,
  X
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { resolveEntity, type EntityCandidate, type EntityResolutionResult } from "@/lib/api";

/* ------------------------------------------------------------------ history */

const RECENT_SEARCHES_KEY = "sentry.recent_searches";
const RECENT_INVESTIGATIONS_KEY = "sentry.recent_investigations";
const PINNED_ENTITIES_KEY = "sentry.pinned_entities";
const MAX_RECENT = 8;

export type PinnedEntity = {
  entity_id: string;
  canonical_name: string;
  entity_type: string;
  registration_number: string | null;
};

function readList<T>(key: string): T[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T[]) : [];
  } catch {
    return [];
  }
}

function writeList<T>(key: string, list: T[]): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(key, JSON.stringify(list));
  } catch {
    /* storage may be unavailable (private mode / quota) — degrade silently */
  }
}

function useSearchHistory() {
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [recentInvestigations, setRecentInvestigations] = useState<PinnedEntity[]>([]);
  const [pinned, setPinned] = useState<PinnedEntity[]>([]);

  useEffect(() => {
    setRecentSearches(readList<string>(RECENT_SEARCHES_KEY));
    setRecentInvestigations(readList<PinnedEntity>(RECENT_INVESTIGATIONS_KEY));
    setPinned(readList<PinnedEntity>(PINNED_ENTITIES_KEY));
  }, []);

  const pushRecentSearch = useCallback((term: string) => {
    const clean = term.trim();
    if (clean.length < 2) return;
    setRecentSearches((prev) => {
      const next = [clean, ...prev.filter((s) => s.toLowerCase() !== clean.toLowerCase())].slice(0, MAX_RECENT);
      writeList(RECENT_SEARCHES_KEY, next);
      return next;
    });
  }, []);

  const pushRecentInvestigation = useCallback((entity: EntityCandidate) => {
    const item = toPinned(entity);
    setRecentInvestigations((prev) => {
      const next = [item, ...prev.filter((e) => e.entity_id !== item.entity_id)].slice(0, MAX_RECENT);
      writeList(RECENT_INVESTIGATIONS_KEY, next);
      return next;
    });
  }, []);

  const togglePinned = useCallback((entity: EntityCandidate | PinnedEntity) => {
    const item = "match_type" in entity ? toPinned(entity) : entity;
    setPinned((prev) => {
      const exists = prev.some((e) => e.entity_id === item.entity_id);
      const next = exists ? prev.filter((e) => e.entity_id !== item.entity_id) : [item, ...prev].slice(0, 24);
      writeList(PINNED_ENTITIES_KEY, next);
      return next;
    });
  }, []);

  const isPinned = useCallback((entityId: string) => pinned.some((e) => e.entity_id === entityId), [pinned]);

  const clearRecentSearches = useCallback(() => {
    setRecentSearches([]);
    writeList(RECENT_SEARCHES_KEY, []);
  }, []);

  return {
    recentSearches,
    recentInvestigations,
    pinned,
    pushRecentSearch,
    pushRecentInvestigation,
    togglePinned,
    isPinned,
    clearRecentSearches
  };
}

function toPinned(entity: EntityCandidate): PinnedEntity {
  return {
    entity_id: entity.entity_id,
    canonical_name: entity.canonical_name,
    entity_type: entity.entity_type,
    registration_number: entity.registration_number
  };
}

/* ------------------------------------------------------------------ helpers */

function entityTypeLabel(type: string): string {
  switch (type) {
    case "company":
      return "Company";
    case "government_buyer":
      return "Buyer";
    case "organization":
      return "Organization";
    case "authority":
      return "Authority";
    default:
      return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

function EntityTypeIcon({ type, className }: { type: string; className?: string }) {
  if (type === "government_buyer" || type === "authority") return <Landmark className={className} />;
  if (type === "organization") return <Gavel className={className} />;
  return <Building2 className={className} />;
}

const DEBOUNCE_MS = 280;

/* ------------------------------------------------------------------ component */

export function EntitySearch({
  running,
  activeQuery,
  onInvestigate,
  onReset,
  providerBadge
}: {
  running: boolean;
  activeQuery: string;
  onInvestigate: (entity: PinnedEntity) => void;
  onReset: () => void;
  providerBadge?: React.ReactNode;
}) {
  const history = useSearchHistory();

  const [term, setTerm] = useState("");
  const [result, setResult] = useState<EntityResolutionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [selected, setSelected] = useState<EntityCandidate | PinnedEntity | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const candidates = result?.candidates ?? [];
  const showEmptyState = open && term.trim().length >= 2 && !loading && candidates.length === 0;

  // Debounced resolution. A fresh keystroke aborts the in-flight request so only
  // the latest query resolves — no races, no stale suggestions.
  const runResolve = useCallback((value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    const clean = value.trim();
    if (clean.length < 2) {
      abortRef.current?.abort();
      setResult(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const res = await resolveEntity(clean, controller.signal);
        setResult(res);
        setActiveIndex(res.candidates.length > 0 ? 0 : -1);
      } catch (err) {
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          setResult({
            query: clean,
            resolved: false,
            requires_disambiguation: false,
            candidates: [],
            selected_entity_id: null,
            reason: "resolution_failed"
          });
        }
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      abortRef.current?.abort();
    };
  }, []);

  // Close the dropdown on an outside click.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const handleChange = (value: string) => {
    setTerm(value);
    setSelected(null); // typing invalidates any locked selection
    setOpen(true);
    runResolve(value);
  };

  const selectCandidate = useCallback((candidate: EntityCandidate | PinnedEntity) => {
    setSelected(candidate);
    setTerm(candidate.canonical_name);
    setOpen(false);
    if ("match_type" in candidate) history.pushRecentSearch(candidate.canonical_name);
    inputRef.current?.blur();
  }, [history]);

  const investigate = useCallback(
    (candidate: EntityCandidate | PinnedEntity | null) => {
      if (!candidate || running) return;
      if ("match_type" in candidate) history.pushRecentInvestigation(candidate);
      onInvestigate(toPinnedLike(candidate));
      setOpen(false);
    },
    [running, onInvestigate, history]
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, candidates.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selected) {
        investigate(selected);
      } else if (activeIndex >= 0 && candidates[activeIndex]) {
        selectCandidate(candidates[activeIndex]);
      }
    }
  };

  const reset = () => {
    setTerm("");
    setSelected(null);
    setResult(null);
    setOpen(false);
    onReset();
  };

  const canInvestigate = selected != null && !running;
  const suggestionsVisible = open && term.trim().length >= 2 && (loading || candidates.length > 0 || showEmptyState);
  const historyVisible = open && term.trim().length < 2 && !selected;

  return (
    <div ref={rootRef} className="animate-rise">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          <Sparkles className="h-3.5 w-3.5" /> AI Investigation Workspace
        </div>
        {providerBadge}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <div className="relative flex-1">
          {loading ? (
            <Loader2 className="pointer-events-none absolute left-4 top-[26px] h-4 w-4 -translate-y-1/2 animate-spin text-accent" />
          ) : (
            <Search className="pointer-events-none absolute left-4 top-[26px] h-4 w-4 -translate-y-1/2 text-muted" />
          )}
          <input
            ref={inputRef}
            value={term}
            onChange={(e) => handleChange(e.target.value)}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
            role="combobox"
            aria-expanded={suggestionsVisible}
            aria-controls="entity-suggestions"
            aria-autocomplete="list"
            aria-activedescendant={activeIndex >= 0 ? `entity-option-${activeIndex}` : undefined}
            placeholder="Search a verified entity — company, buyer, authority or registration no."
            className="h-12 w-full rounded-xl border border-border bg-surface pl-11 pr-10 text-sm text-text outline-none transition placeholder:text-faint focus:border-accent/60"
            spellCheck={false}
            autoComplete="off"
          />
          {selected && (
            <Check className="pointer-events-none absolute right-4 top-[26px] h-4 w-4 -translate-y-1/2 text-success" />
          )}

          {suggestionsVisible && (
            <SuggestionDropdown
              candidates={candidates}
              loading={loading}
              showEmptyState={showEmptyState}
              activeIndex={activeIndex}
              term={term}
              onHover={setActiveIndex}
              onSelect={selectCandidate}
              isPinned={history.isPinned}
              onTogglePin={history.togglePinned}
            />
          )}

          {historyVisible && (
            <HistoryDropdown
              recentSearches={history.recentSearches}
              recentInvestigations={history.recentInvestigations}
              pinned={history.pinned}
              onPickSearch={(s) => handleChange(s)}
              onPickEntity={(entity) => {
                setSelected(entity);
                setTerm(entity.canonical_name);
                setOpen(false);
              }}
              onClearRecent={history.clearRecentSearches}
              onUnpin={history.togglePinned}
            />
          )}
        </div>

        <button
          type="button"
          onClick={() => investigate(selected)}
          disabled={!canInvestigate}
          title={selected ? "Start investigation" : "Select a verified entity first"}
          className="flex h-12 items-center justify-center gap-2 rounded-xl bg-accent px-6 text-sm font-semibold text-bg transition hover:bg-accent-hi disabled:cursor-not-allowed disabled:opacity-45"
        >
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
          {running ? "Investigating" : "Investigate"}
        </button>

        {(activeQuery || selected) && (
          <button
            type="button"
            onClick={reset}
            aria-label="Reset investigation"
            title="Reset"
            className="flex h-12 items-center justify-center rounded-xl border border-border bg-surface px-4 text-sm text-muted transition hover:text-text"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Locked selection / active investigation subject */}
      {(selected || activeQuery) && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          {selected ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-success/30 bg-success/10 px-3 py-1 text-success">
              <Check className="h-3.5 w-3.5" />
              <span className="font-medium">{selected.canonical_name}</span>
              <span className="text-[11px] uppercase tracking-wide text-success/80">
                {entityTypeLabel(selected.entity_type)} · locked
              </span>
              <button type="button" onClick={reset} aria-label="Clear selection">
                <X className="h-3 w-3" />
              </button>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-accent">
              {activeQuery}
              <button type="button" onClick={reset} aria-label="Clear">
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
          {!selected && !activeQuery && (
            <span className="text-xs text-faint">Select a suggestion to enable Investigate.</span>
          )}
        </div>
      )}

      <div className="rule mt-5" />
    </div>
  );
}

function toPinnedLike(candidate: EntityCandidate | PinnedEntity): PinnedEntity {
  return {
    entity_id: candidate.entity_id,
    canonical_name: candidate.canonical_name,
    entity_type: candidate.entity_type,
    registration_number: candidate.registration_number
  };
}

/* ------------------------------------------------------------------ dropdown */

function SuggestionDropdown({
  candidates,
  loading,
  showEmptyState,
  activeIndex,
  term,
  onHover,
  onSelect,
  isPinned,
  onTogglePin
}: {
  candidates: EntityCandidate[];
  loading: boolean;
  showEmptyState: boolean;
  activeIndex: number;
  term: string;
  onHover: (i: number) => void;
  onSelect: (c: EntityCandidate) => void;
  isPinned: (id: string) => boolean;
  onTogglePin: (c: EntityCandidate) => void;
}) {
  return (
    <div className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-border-strong bg-surface-2 shadow-2xl shadow-black/40">
      {loading && candidates.length === 0 && (
        <div className="flex items-center gap-2 px-4 py-4 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin text-accent" />
          Resolving verified entities…
        </div>
      )}

      {!loading && showEmptyState && <EmptyState term={term} />}

      {candidates.length > 0 && (
        <ul id="entity-suggestions" role="listbox" className="max-h-[420px] overflow-y-auto py-1">
          {candidates.map((c, i) => (
            <li
              key={c.entity_id}
              id={`entity-option-${i}`}
              role="option"
              aria-selected={i === activeIndex}
              className={`flex items-start gap-2 px-3.5 py-3 transition ${
                i === activeIndex ? "bg-elevated" : "hover:bg-elevated/60"
              }`}
            >
              <button
                type="button"
                onMouseEnter={() => onHover(i)}
                onClick={() => onSelect(c)}
                className="flex min-w-0 flex-1 items-start gap-3 text-left"
              >
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-border bg-surface">
                  <EntityTypeIcon type={c.entity_type} className="h-4 w-4 text-accent" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="truncate text-sm font-semibold text-text">{c.canonical_name}</span>
                    <span className="shrink-0 rounded border border-border bg-surface px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted">
                      {entityTypeLabel(c.entity_type)}
                    </span>
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-faint">
                    {c.registration_number && <span className="font-mono text-muted">{c.registration_number}</span>}
                    <span>{c.tender_count} tenders</span>
                    {c.award_count > 0 && <span>· {c.award_count} awards</span>}
                    <span>· {Math.round(c.confidence * 100)}% confidence</span>
                    <span className="rounded bg-surface px-1.5 py-0.5 text-muted">{c.match_type.replace(/_/g, " ")}</span>
                    {c.sources.length > 0 && <span>· {c.sources.slice(0, 3).join(", ")}</span>}
                  </span>
                  {c.aliases.length > 0 && (
                    <span className="mt-1 block truncate text-[11px] text-faint">
                      aka {c.aliases.slice(0, 4).join(", ")}
                    </span>
                  )}
                </span>
              </button>
              <button
                type="button"
                onClick={() => onTogglePin(c)}
                aria-label={isPinned(c.entity_id) ? "Unpin entity" : "Pin entity"}
                className="mt-0.5 shrink-0 rounded p-1 text-faint transition hover:text-accent"
              >
                <Pin className={`h-3.5 w-3.5 ${isPinned(c.entity_id) ? "fill-accent/25 text-accent" : ""}`} />
              </button>
            </li>
          ))}
        </ul>
      )}

      {candidates.length > 0 && (
        <div className="border-t border-border px-3.5 py-2 text-[11px] text-faint">
          Verified procurement entities · use ↑ ↓ to navigate, Enter to select
        </div>
      )}
    </div>
  );
}

function EmptyState({ term }: { term: string }) {
  return (
    <div className="px-4 py-4">
      <p className="text-sm font-semibold text-text">No verified procurement entity found</p>
      <p className="mt-1 text-xs text-muted">
        “{term.trim()}” does not match any known procurement company, buyer or authority.
      </p>
      <ul className="mt-3 space-y-1.5 text-xs text-faint">
        <li className="flex items-center gap-2">
          <span className="h-1 w-1 rounded-full bg-accent" /> Check the spelling
        </li>
        <li className="flex items-center gap-2">
          <span className="h-1 w-1 rounded-full bg-accent" /> Try the official company name
        </li>
        <li className="flex items-center gap-2">
          <span className="h-1 w-1 rounded-full bg-accent" /> Try the registration number (CIN)
        </li>
      </ul>
    </div>
  );
}

/* ------------------------------------------------------------------ history dropdown */

function HistoryDropdown({
  recentSearches,
  recentInvestigations,
  pinned,
  onPickSearch,
  onPickEntity,
  onClearRecent,
  onUnpin
}: {
  recentSearches: string[];
  recentInvestigations: PinnedEntity[];
  pinned: PinnedEntity[];
  onPickSearch: (s: string) => void;
  onPickEntity: (e: PinnedEntity) => void;
  onClearRecent: () => void;
  onUnpin: (e: PinnedEntity) => void;
}) {
  const empty = recentSearches.length === 0 && recentInvestigations.length === 0 && pinned.length === 0;
  if (empty) return null;

  return (
    <div className="absolute z-30 mt-2 w-full overflow-hidden rounded-xl border border-border-strong bg-surface-2 shadow-2xl shadow-black/40">
      <div className="max-h-[420px] overflow-y-auto p-2">
        {pinned.length > 0 && (
          <Group title="Pinned entities">
            {pinned.map((e) => (
              <EntityRow
                key={e.entity_id}
                entity={e}
                onPick={() => onPickEntity(e)}
                trailing={
                  <button
                    type="button"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      onUnpin(e);
                    }}
                    aria-label="Unpin"
                    className="rounded p-1 text-faint transition hover:text-danger"
                  >
                    <PinOff className="h-3.5 w-3.5" />
                  </button>
                }
              />
            ))}
          </Group>
        )}

        {recentInvestigations.length > 0 && (
          <Group title="Recent investigations">
            {recentInvestigations.map((e) => (
              <EntityRow key={e.entity_id} entity={e} onPick={() => onPickEntity(e)} />
            ))}
          </Group>
        )}

        {recentSearches.length > 0 && (
          <Group
            title="Recent searches"
            action={
              <button type="button" onClick={onClearRecent} className="text-[11px] text-faint transition hover:text-muted">
                Clear
              </button>
            }
          >
            {recentSearches.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onPickSearch(s)}
                className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-sm text-muted transition hover:bg-elevated hover:text-text"
              >
                <Search className="h-3.5 w-3.5 text-faint" />
                <span className="truncate">{s}</span>
              </button>
            ))}
          </Group>
        )}
      </div>
    </div>
  );
}

function Group({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="mb-1 last:mb-0">
      <div className="flex items-center justify-between px-2.5 py-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">{title}</span>
        {action}
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function EntityRow({
  entity,
  onPick,
  trailing
}: {
  entity: PinnedEntity;
  onPick: () => void;
  trailing?: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={onPick}
        className="flex min-w-0 flex-1 items-center gap-2.5 rounded-lg px-2.5 py-2 text-left transition hover:bg-elevated"
      >
        <EntityTypeIcon type={entity.entity_type} className="h-3.5 w-3.5 shrink-0 text-accent" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm text-text">{entity.canonical_name}</span>
          <span className="block text-[11px] text-faint">
            {entityTypeLabel(entity.entity_type)}
            {entity.registration_number ? ` · ${entity.registration_number}` : ""}
          </span>
        </span>
      </button>
      {trailing}
    </div>
  );
}
