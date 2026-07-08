"use client";

import { motion } from "framer-motion";
import {
  Activity,
  Award,
  Bell,
  Building2,
  ChevronsLeft,
  FileText,
  FolderSearch,
  GitBranch,
  LayoutDashboard,
  Map as MapIcon,
  Menu,
  Radar,
  Search,
  Settings,
  Shield,
  Clock,
  UserCircle,
  Command,
  Zap
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { CommandPalette } from "./command-palette";
import { PageTransition } from "./page-transition";

const navGroups: {
  label: string;
  items: { href: string; icon: typeof LayoutDashboard; label: string }[];
}[] = [
  {
    label: "Intelligence",
    items: [
      { href: "/", icon: LayoutDashboard, label: "Command Center" },
      { href: "/investigations", icon: FolderSearch, label: "Investigations" },
      { href: "/graph", icon: GitBranch, label: "Graph Explorer" },
      { href: "/risk", icon: Radar, label: "Risk Monitor" }
    ]
  },
  {
    label: "Records",
    items: [
      { href: "/tenders", icon: FileText, label: "Tenders" },
      { href: "/companies", icon: Building2, label: "Companies" },
      { href: "/awards", icon: Award, label: "Awards" }
    ]
  },
  {
    label: "Analysis",
    items: [
      { href: "/timeline", icon: Clock, label: "Timeline" },
      { href: "/map", icon: MapIcon, label: "Geography" },
      { href: "/reports", icon: Activity, label: "Reports" }
    ]
  },
  {
    label: "System",
    items: [
      { href: "/profile", icon: UserCircle, label: "Analyst Profile" },
      { href: "/settings", icon: Settings, label: "Settings" }
    ]
  }
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // close mobile drawer on route change
  useEffect(() => setMobileOpen(false), [pathname]);

  const width = collapsed ? 76 : 248;

  return (
    <div className="min-h-screen bg-bg text-text">
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />

      {/* ---------------- Header ---------------- */}
      <header className="fixed inset-x-0 top-0 z-40 flex h-14 items-center gap-3 border-b border-border bg-bg-2/80 px-3 backdrop-blur-xl">
        <button
          className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-surface-2 hover:text-text lg:hidden"
          onClick={() => setMobileOpen((v) => !v)}
          type="button"
          aria-label="Toggle navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        <Link href="/" className="group flex items-center gap-2.5 pl-1 pr-2">
          <span className="relative grid h-8 w-8 place-items-center overflow-hidden rounded-lg border border-accent/25 bg-accent/[0.08] text-accent transition-colors group-hover:border-accent/40">
            <Shield className="h-[18px] w-[18px]" />
          </span>
          <span className="hidden leading-none sm:block">
            <span className="block text-[15px] font-semibold tracking-tight">SENTRY</span>
            <span className="mt-0.5 block text-[8px] font-semibold uppercase tracking-[0.22em] text-faint">
              Evidence · Intelligence · Impact
            </span>
          </span>
        </Link>

        <button
          onClick={() => setPaletteOpen(true)}
          className="group ml-2 flex h-9 max-w-xl flex-1 items-center gap-2 rounded-lg border border-border bg-bg/60 px-3 text-left text-sm text-faint transition hover:border-border-strong hover:bg-surface"
          type="button"
        >
          <Search className="h-4 w-4 text-muted transition-colors group-hover:text-accent" />
          <span className="flex-1 truncate">
            Search companies, buyers, tenders, awards…
          </span>
          <kbd className="hidden items-center gap-0.5 rounded border border-border bg-bg-2 px-1.5 py-0.5 text-[10px] font-medium text-muted sm:flex">
            ⌘K
          </kbd>
        </button>

        <div className="ml-auto flex items-center gap-2">
          {/* Single, quiet system-status chip — colour reserved for meaning */}
          <span className="hidden items-center gap-2 rounded-full border border-border bg-surface/70 px-3 py-1 text-[11px] font-medium text-muted xl:flex">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full rounded-full bg-success pulse-live" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
            </span>
            <span className="text-text">Operational</span>
            <span className="text-faint">·</span>
            <span>Live data</span>
          </span>

          <div className="mx-0.5 hidden h-5 w-px bg-border xl:block" />

          <button
            className="relative grid h-9 w-9 place-items-center rounded-lg border border-border bg-surface text-muted transition hover:border-border-strong hover:text-text"
            type="button"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-danger ring-2 ring-bg-2" />
          </button>
          <Link
            href="/profile"
            className="flex items-center gap-2 rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-text transition hover:border-border-strong md:pl-2 md:pr-2.5"
          >
            <span className="grid h-6 w-6 place-items-center rounded-md bg-accent/12 text-accent">
              <UserCircle className="h-4 w-4" />
            </span>
            <span className="hidden md:block">Analyst</span>
          </Link>
        </div>
      </header>

      {/* ---------------- Sidebar ---------------- */}
      <motion.aside
        animate={{ width }}
        initial={false}
        transition={{ duration: 0.18, ease: [0.2, 0.7, 0.2, 1] }}
        className={`fixed bottom-0 left-0 top-14 z-30 border-r border-border bg-bg-2/80 backdrop-blur-xl ${
          mobileOpen ? "block" : "hidden lg:block"
        }`}
      >
        <div className="flex h-full flex-col overflow-y-auto px-3 py-4">
          <nav className="flex-1 space-y-5">
            {navGroups.map((group) => (
              <div key={group.label}>
                {!collapsed && (
                  <div className="px-2 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">
                    {group.label}
                  </div>
                )}
                <div className="space-y-0.5">
                  {group.items.map((item) => {
                    const Icon = item.icon;
                    const active =
                      pathname === item.href ||
                      (item.href !== "/" && pathname.startsWith(item.href));
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        title={collapsed ? item.label : undefined}
                        className={`group relative flex h-9 items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-150 ${
                          active
                            ? "font-medium text-text"
                            : "text-muted hover:bg-surface/60 hover:text-text"
                        }`}
                      >
                        {active && (
                          <motion.span
                            layoutId="nav-active"
                            transition={{ type: "spring", stiffness: 420, damping: 34 }}
                            className="absolute inset-0 rounded-lg border border-border-strong/70 bg-surface-2"
                          />
                        )}
                        {active && (
                          <span className="absolute inset-y-1.5 left-0 z-10 w-0.5 rounded-full bg-accent" />
                        )}
                        <Icon
                          className={`relative z-10 h-[18px] w-[18px] shrink-0 transition-colors ${
                            active ? "text-accent" : "group-hover:text-text"
                          }`}
                        />
                        {!collapsed && (
                          <span className="relative z-10 truncate">{item.label}</span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </nav>

          {!collapsed && (
            <div className="mt-4 rounded-xl border border-border bg-surface/70 p-3.5 elevate">
              <div className="flex items-center gap-2 text-sm font-semibold text-text">
                <span className="grid h-6 w-6 place-items-center rounded-md border border-accent/25 bg-accent/[0.08] text-accent">
                  <Zap className="h-3.5 w-3.5" />
                </span>
                New Investigation
              </div>
              <p className="mt-1.5 text-[11px] leading-snug text-muted">
                Launch an AI investigation from a single prompt.
              </p>
              <Link
                href="/investigations"
                className="group mt-3 flex h-9 items-center justify-center gap-1.5 rounded-lg bg-accent text-sm font-semibold text-bg transition-colors hover:bg-accent-hi"
              >
                Start
                <Command className="h-3.5 w-3.5 opacity-70 transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
          )}

          <button
            onClick={() => setCollapsed((v) => !v)}
            className="mt-3 hidden h-9 items-center gap-2 rounded-lg px-3 text-xs text-faint transition hover:bg-surface-2 hover:text-text lg:flex"
            type="button"
          >
            <ChevronsLeft
              className={`h-4 w-4 transition-transform ${collapsed ? "rotate-180" : ""}`}
            />
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </motion.aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 top-14 z-20 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* ---------------- Main ---------------- */}
      <motion.main
        animate={{ paddingLeft: width }}
        initial={false}
        transition={{ duration: 0.18, ease: [0.2, 0.7, 0.2, 1] }}
        className="min-h-screen pt-14 max-lg:!pl-0"
      >
        <PageTransition>{children}</PageTransition>
      </motion.main>
    </div>
  );
}
