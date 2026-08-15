"use client";

import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useRef } from "react";
import { EASE } from "@/lib/motion";
import { Button } from "./button";

/**
 * Modal dialog.
 *
 * A floating glass sheet over a blurred scrim. Handles the accessibility
 * plumbing that hand-rolled modals usually skip: Escape to close, focus moved
 * in on open and restored on close, focus trapped inside while open, and body
 * scroll locked.
 */

const SIZES = {
  sm: "max-w-md",
  md: "max-w-xl",
  lg: "max-w-3xl",
  xl: "max-w-5xl"
} as const;

export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  size = "md",
  /** Hides the corner dismiss button — for flows that must be resolved. */
  hideClose = false
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  size?: keyof typeof SIZES;
  hideClose?: boolean;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const restoreRef = useRef<HTMLElement | null>(null);

  // Escape to dismiss, and trap Tab inside the panel while open.
  useEffect(() => {
    if (!open) return;

    restoreRef.current = document.activeElement as HTMLElement | null;

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;

      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Move focus into the dialog once it has mounted.
    const raf = requestAnimationFrame(() => {
      const target = panelRef.current?.querySelector<HTMLElement>(
        'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'
      );
      target?.focus();
    });

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      cancelAnimationFrame(raf);
      restoreRef.current?.focus?.();
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 pt-[10vh] sm:p-6 sm:pt-[12vh]"
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: EASE }}
            onClick={onClose}
            className="fixed inset-0 bg-bg/70 backdrop-blur-sm"
            aria-hidden
          />

          <motion.div
            ref={panelRef}
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.99 }}
            transition={{ duration: 0.26, ease: EASE }}
            className={`glass glass-hi relative z-10 w-full ${SIZES[size]} overflow-hidden rounded-2xl`}
          >
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div className="min-w-0">
                <h2 className="text-[17px] font-semibold tracking-[-0.014em] text-text">
                  {title}
                </h2>
                {description && (
                  <p className="mt-1.5 text-[13px] leading-relaxed text-muted">
                    {description}
                  </p>
                )}
              </div>
              {!hideClose && (
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  aria-label="Close dialog"
                  onClick={onClose}
                  icon={<X className="h-4 w-4" />}
                />
              )}
            </div>

            <div className="px-6 py-6">{children}</div>

            {footer && (
              <div className="flex items-center justify-end gap-3 border-t border-border bg-bg-2/40 px-6 py-4">
                {footer}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

/**
 * Right-hand slide-over. Same chrome as `Dialog`, anchored to the edge —
 * for inspectors that sit alongside a persistent canvas rather than over it.
 */
export function Drawer({
  open,
  onClose,
  title,
  children,
  width = "max-w-md"
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, ease: EASE }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-bg/60 backdrop-blur-sm"
            aria-hidden
          />
          <motion.aside
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.3, ease: EASE }}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            className={`glass glass-hi fixed inset-y-0 right-0 z-50 w-full ${width} overflow-y-auto`}
          >
            <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-border bg-bg-2/80 px-5 py-4 backdrop-blur-xl">
              <h2 className="text-[15px] font-semibold tracking-[-0.014em] text-text">
                {title}
              </h2>
              <Button
                variant="ghost"
                size="sm"
                iconOnly
                aria-label="Close panel"
                onClick={onClose}
                icon={<X className="h-4 w-4" />}
              />
            </div>
            <div className="px-5 py-5">{children}</div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
