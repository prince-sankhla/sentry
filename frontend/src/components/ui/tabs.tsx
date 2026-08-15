"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { SPRING } from "@/lib/motion";

/**
 * Tabs.
 *
 * The active indicator is a shared `layoutId` pill, so switching tabs slides
 * rather than blinks. Two shapes:
 *   `segmented`  enclosed control — view switchers, small option sets
 *   `underline`  editorial rail — page-level sections
 *
 * Controlled only: the caller owns `value`, so tab state can live in a URL
 * param or a parent reducer without this component fighting it.
 */

export type TabItem<T extends string = string> = {
  value: T;
  label: ReactNode;
  icon?: ReactNode;
  /** Trailing count or badge. */
  meta?: ReactNode;
  disabled?: boolean;
};

export function Tabs<T extends string>({
  items,
  value,
  onChange,
  variant = "segmented",
  /** Distinguishes the layoutId when several tab sets share a page. */
  id = "tabs",
  className = ""
}: {
  items: TabItem<T>[];
  value: T;
  onChange: (next: T) => void;
  variant?: "segmented" | "underline";
  id?: string;
  className?: string;
}) {
  if (variant === "underline") {
    return (
      <div
        role="tablist"
        className={`flex items-center gap-1 border-b border-border ${className}`}
      >
        {items.map((item) => {
          const active = item.value === value;
          return (
            <button
              key={item.value}
              role="tab"
              type="button"
              aria-selected={active}
              disabled={item.disabled}
              onClick={() => onChange(item.value)}
              className={`relative flex items-center gap-2 px-4 py-3 text-[13px] font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${
                active ? "text-text" : "text-muted hover:text-text"
              }`}
            >
              {item.icon}
              {item.label}
              {item.meta}
              {active && (
                <motion.span
                  layoutId={`${id}-underline`}
                  transition={SPRING}
                  className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent"
                />
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div
      role="tablist"
      className={`inline-flex items-center gap-1 rounded-xl border border-border bg-bg-2/60 p-1 ${className}`}
    >
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            type="button"
            aria-selected={active}
            disabled={item.disabled}
            onClick={() => onChange(item.value)}
            className={`relative flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${
              active ? "text-text" : "text-muted hover:text-text"
            }`}
          >
            {active && (
              <motion.span
                layoutId={`${id}-pill`}
                transition={SPRING}
                className="absolute inset-0 rounded-lg border border-border-strong/70 bg-surface-2 elevate"
              />
            )}
            <span className="relative z-10 flex items-center gap-1.5">
              {item.icon}
              {item.label}
              {item.meta}
            </span>
          </button>
        );
      })}
    </div>
  );
}
