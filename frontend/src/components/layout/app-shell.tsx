"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Award,
  Bell,
  BookOpen,
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  FolderSearch,
  GitBranch,
  Landmark,
  Library,
  Menu,
  PackageOpen,
  Search,
  Settings,
  Shield,
  SlidersHorizontal,
  UserCircle
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { FormEvent, ReactNode } from "react";
import { useState } from "react";

const navItems = [
  { href: "/", icon: FolderSearch, label: "Workspace" },
  { href: "/investigations", icon: BookOpen, label: "Investigations" },
  { href: "/companies", icon: Building2, label: "Companies" },
  { href: "/tenders", icon: FileText, label: "Tenders" },
  { href: "/buyers", icon: Landmark, label: "Buyers" },
  { href: "/documents", icon: Library, label: "Documents" },
  { href: "/graph", icon: GitBranch, label: "Graph" },
  { href: "/evidence", icon: Shield, label: "Evidence" },
  { href: "/sources", icon: PackageOpen, label: "Sources" },
  { href: "/imports", icon: Award, label: "Imports" },
  { href: "/settings", icon: Settings, label: "Settings" }
];

export function AppShell({
  children,
  title = "SENTRY Workspace"
}: {
  children: ReactNode;
  title?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const query = String(formData.get("globalSearch") ?? "").trim();
    if (query) {
      router.push(`/?q=${encodeURIComponent(query)}`);
    }
  }

  return (
    <div className="min-h-screen bg-[#090909] text-[#F7F7F7]">
      <header className="fixed left-0 right-0 top-0 z-40 flex h-14 items-center border-b border-[#2A2A2A] bg-[#090909]">
        <button className="mx-3 text-[#A3A3A3] lg:hidden" onClick={() => setMobileOpen((value) => !value)} type="button" aria-label="Toggle navigation">
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex h-full min-w-0 flex-1 items-center gap-4 px-4">
          <div className="hidden items-center gap-2 text-sm font-semibold text-[#F7F7F7] sm:flex">
            <Shield className="h-4 w-4 text-[#A3A3A3]" />
            {title}
          </div>
          <form className="relative max-w-2xl flex-1" onSubmit={onSearch}>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#737373]" />
            <input
              className="h-9 w-full border border-[#2A2A2A] bg-[#111111] pl-9 pr-3 text-sm text-[#F7F7F7] outline-none placeholder:text-[#737373] focus:border-[#B59A5B]"
              name="globalSearch"
              placeholder="Global search company, tender, buyer, award"
              type="search"
            />
          </form>
          <button className="border border-[#2A2A2A] bg-[#111111] p-2 text-[#A3A3A3] hover:text-[#F7F7F7]" type="button" aria-label="Filters">
            <SlidersHorizontal className="h-4 w-4" />
          </button>
          <button className="border border-[#2A2A2A] bg-[#111111] p-2 text-[#A3A3A3] hover:text-[#F7F7F7]" type="button" aria-label="Notifications">
            <Bell className="h-4 w-4" />
          </button>
          <button className="hidden items-center gap-2 border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-[#F7F7F7] md:flex" type="button">
            <UserCircle className="h-4 w-4 text-[#A3A3A3]" />
            Analyst
          </button>
        </div>
      </header>

      <AnimatePresence>
        {(mobileOpen || true) && (
          <motion.aside
            animate={{ width: collapsed ? 72 : 232 }}
            className={`fixed bottom-0 left-0 top-14 z-30 border-r border-[#2A2A2A] bg-[#090909] ${mobileOpen ? "block" : "hidden lg:block"}`}
            initial={false}
            transition={{ duration: 0.16, ease: "easeOut" }}
          >
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-[#2A2A2A] p-3">
                {!collapsed ? <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#737373]">Navigation</div> : null}
                <button className="border border-[#2A2A2A] p-1 text-[#A3A3A3] hover:text-[#F7F7F7]" onClick={() => setCollapsed((value) => !value)} type="button" aria-label="Collapse sidebar">
                  {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
                </button>
              </div>
              <nav className="flex-1 space-y-1 p-2">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                  return (
                    <Link
                      className={`flex h-10 items-center gap-3 border px-3 text-sm transition ${
                        active
                          ? "border-[#2A2A2A] bg-[#181818] text-[#F7F7F7]"
                          : "border-transparent text-[#A3A3A3] hover:border-[#2A2A2A] hover:bg-[#111111] hover:text-[#F7F7F7]"
                      }`}
                      href={item.href}
                      key={item.href}
                      title={collapsed ? item.label : undefined}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      {!collapsed ? <span>{item.label}</span> : null}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <motion.main animate={{ paddingLeft: collapsed ? 72 : 232 }} className="min-h-screen pt-14 transition-[padding] max-lg:pl-0">
        {children}
      </motion.main>
    </div>
  );
}
