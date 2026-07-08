"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Building2,
  CornerDownLeft,
  FileText,
  Landmark,
  Loader2,
  Search,
  SearchX
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { globalSearch, type SearchHit } from "@/lib/api";

type Flat = SearchHit & { group: "Tenders" | "Companies" | "Buyers" };

const GROUP_ICON = {
  Tenders: FileText,
  Companies: Building2,
  Buyers: Landmark
} as const;

function hrefFor(hit: Flat): string {
  if (hit.group === "Tenders") return `/tenders/${hit.id}`;
  if (hit.group === "Companies") return `/companies/${hit.id}`;
  return `/?q=${encodeURIComponent(hit.label)}`;
}

export function CommandPalette({
  open,
  onClose
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [hits, setHits] = useState<Flat[]>([]);
  const [searched, setSearched] = useState(false);
  const [active, setActive] = useState(0);

  // reset on open
  useEffect(() => {
    if (open) {
      setQuery("");
      setHits([]);
      setSearched(false);
      setActive(0);
      const t = setTimeout(() => inputRef.current?.focus(), 40);
      return () => clearTimeout(t);
    }
  }, [open]);

  // debounced live search
  useEffect(() => {
    if (!open) return;
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setHits([]);
      setSearched(false);
      setLoading(false);
      return;
    }
    setLoading(true);
    const handle = setTimeout(async () => {
      try {
        const res = await globalSearch(trimmed, 8);
        const flat: Flat[] = [
          ...res.tenders.map((h) => ({ ...h, group: "Tenders" as const })),
          ...res.companies.map((h) => ({ ...h, group: "Companies" as const })),
          ...res.buyers.map((h) => ({ ...h, group: "Buyers" as const }))
        ];
        setHits(flat);
        setActive(0);
        setSearched(true);
      } catch {
        setHits([]);
        setSearched(true);
      } finally {
        setLoading(false);
      }
    }, 180);
    return () => clearTimeout(handle);
  }, [query, open]);

  const go = useCallback(
    (hit: Flat) => {
      onClose();
      router.push(hrefFor(hit));
    },
    [onClose, router]
  );

  const grouped = useMemo(() => {
    const order: Flat["group"][] = ["Companies", "Buyers", "Tenders"];
    return order
      .map((g) => ({ group: g, items: hits.filter((h) => h.group === g) }))
      .filter((s) => s.items.length > 0);
  }, [hits]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => Math.min(i + 1, hits.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (hits[active]) go(hits[active]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.14 }}
        >
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            className="glass relative w-full max-w-2xl overflow-hidden rounded-2xl shadow-2xl"
            initial={{ opacity: 0, y: -12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ duration: 0.16, ease: [0.2, 0.7, 0.2, 1] }}
          >
            <div className="flex items-center gap-3 border-b border-border px-4">
              {loading ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-accent" />
              ) : (
                <Search className="h-4 w-4 shrink-0 text-muted" />
              )}
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Search companies, buyers, tenders, awards…"
                className="h-14 w-full bg-transparent text-[15px] text-text outline-none placeholder:text-faint"
              />
              <kbd className="hidden rounded border border-border bg-bg-2 px-1.5 py-0.5 text-[10px] font-medium text-faint sm:block">
                ESC
              </kbd>
            </div>

            <div className="max-h-[52vh] overflow-y-auto p-2">
              {query.trim().length < 2 && (
                <div className="px-3 py-8 text-center text-sm text-faint">
                  Type at least 2 characters to search the local investigation
                  database.
                </div>
              )}

              {query.trim().length >= 2 &&
                searched &&
                hits.length === 0 &&
                !loading && (
                  <div className="flex flex-col items-center gap-2 px-3 py-10 text-center">
                    <SearchX className="h-6 w-6 text-faint" />
                    <p className="text-sm font-medium text-text">
                      Not in the local investigation database
                    </p>
                    <p className="max-w-sm text-xs text-muted">
                      “{query.trim()}” is not available among imported buyers,
                      companies, tenders, or awards. Import the entity to
                      investigate it.
                    </p>
                  </div>
                )}

              {grouped.map((section) => {
                const Icon = GROUP_ICON[section.group];
                return (
                  <div key={section.group} className="mb-1">
                    <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">
                      {section.group}
                    </div>
                    {section.items.map((hit) => {
                      const idx = hits.indexOf(hit);
                      const isActive = idx === active;
                      return (
                        <button
                          key={`${hit.group}-${hit.id}`}
                          onMouseEnter={() => setActive(idx)}
                          onClick={() => go(hit)}
                          className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition ${
                            isActive
                              ? "bg-accent/12 text-text"
                              : "text-muted hover:bg-surface-2"
                          }`}
                        >
                          <span
                            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border ${
                              isActive
                                ? "border-accent/40 bg-accent/10 text-accent"
                                : "border-border bg-bg-2 text-muted"
                            }`}
                          >
                            <Icon className="h-4 w-4" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-sm font-medium text-text">
                              {hit.label}
                            </span>
                            {hit.sublabel && (
                              <span className="block truncate text-xs text-faint">
                                {hit.sublabel}
                              </span>
                            )}
                          </span>
                          {isActive && (
                            <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-accent" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-between border-t border-border bg-bg-2/50 px-4 py-2 text-[11px] text-faint">
              <span className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-border px-1">↑</kbd>
                  <kbd className="rounded border border-border px-1">↓</kbd>
                  navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="rounded border border-border px-1">↵</kbd>
                  open
                </span>
              </span>
              <span>Local investigation database</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
