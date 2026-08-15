"use client";

import { AnimatePresence, motion, useMotionValueEvent, useScroll } from "framer-motion";
import Link from "next/link";
import { useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";

import { Logo } from "./logo";

const NAV_ITEMS = ["Product", "Solutions", "Resources", "Company"] as const;

/**
 * Minimal floating navbar. Sits over the hero; grows slightly more transparent
 * and gains a hairline border once the page scrolls.
 */
export function Navbar() {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useMotionValueEvent(scrollY, "change", (y) => setScrolled(y > 24));

  return (
    <motion.header
      initial={{ y: -24, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4"
    >
      <nav
        className={`flex w-full max-w-6xl items-center gap-6 rounded-2xl px-4 py-2.5 transition-all duration-300 ${
          scrolled
            ? "mkt-glass mkt-glass-hi border-border"
            : "border border-transparent bg-transparent"
        }`}
      >
        <Link href="/" className="flex items-center gap-2.5">
          <Logo className="h-8 w-8" />
          <span className="flex flex-col leading-none">
            <span className="text-[15px] font-semibold tracking-tight text-text">SENTRY</span>
            <span className="mt-0.5 text-[8px] font-semibold uppercase tracking-[0.2em] text-muted">
              Evidence Over Assumptions
            </span>
          </span>
        </Link>

        <div className="mx-auto hidden items-center gap-1 lg:flex">
          {NAV_ITEMS.map((item) => (
            <button
              key={item}
              type="button"
              className="flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:text-text"
            >
              {item}
              <ChevronDown className="h-3.5 w-3.5 opacity-60" />
            </button>
          ))}
        </div>

        <div className="ml-auto hidden items-center gap-2 lg:flex">
          <button
            type="button"
            className="rounded-lg px-3.5 py-2 text-sm font-medium text-text transition-colors hover:text-accent-hi"
          >
            Book Demo
          </button>
          <Link
            href="/investigate"
            className="group rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-bg transition-all hover:bg-accent-hi"
          >
            Start Investigation
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setMobileOpen((v) => !v)}
          className="ml-auto grid h-9 w-9 place-items-center rounded-lg text-muted hover:text-text lg:hidden"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute inset-x-4 top-20 mkt-glass mkt-glass-hi rounded-2xl p-4 lg:hidden"
          >
            <div className="flex flex-col gap-1">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item}
                  type="button"
                  className="rounded-lg px-3 py-2.5 text-left text-sm font-medium text-muted hover:bg-surface/60 hover:text-text"
                >
                  {item}
                </button>
              ))}
              <div className="mt-2 flex flex-col gap-2 border-t border-border pt-3">
                <button className="rounded-lg px-3 py-2.5 text-left text-sm font-medium text-text">
                  Book Demo
                </button>
                <Link
                  href="/investigate"
                  className="rounded-lg bg-accent px-4 py-2.5 text-center text-sm font-semibold text-bg"
                >
                  Start Investigation
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}
