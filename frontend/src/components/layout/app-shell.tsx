"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Award,
  BarChart3,
  Bell,
  Building2,
  ChevronLeft,
  ChevronRight,
  FileText,
  FolderSearch,
  GitBranch,
  LayoutDashboard,
  Menu,
  Search,
  Settings,
  Shield,
  UserCircle
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { FormEvent, ReactNode } from "react";
import { useState } from "react";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/graph", icon: GitBranch, label: "Graph" },
  { href: "/tenders", icon: FileText, label: "Tenders" },
  { href: "/companies", icon: Building2, label: "Companies" },
  { href: "/awards", icon: Award, label: "Awards" },
  { href: "/investigations", icon: FolderSearch, label: "Investigations" },
  { href: "/reports", icon: BarChart3, label: "Reports" },
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
    <div className="min-h-screen bg-[#0B0F14] text-[#E6E8EB]">
      <header className="fixed left-0 right-0 top-0 z-40 flex h-14 items-center border-b border-[#2A3441] bg-[#0B0F14]">
        <button className="mx-3 text-[#9AA4AF] lg:hidden" onClick={() => setMobileOpen((value) => !value)} type="button" aria-label="Toggle navigation">
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex h-full min-w-0 flex-1 items-center gap-4 px-4">
          <div className="hidden items-center gap-2 text-sm font-semibold text-[#E6E8EB] sm:flex">
            <Shield className="h-4 w-4 text-[#C58B2A]" />
            {title}
          </div>
          <form className="relative max-w-2xl flex-1" onSubmit={onSearch}>
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9AA4AF]" />
            <input
              className="h-9 w-full border border-[#2A3441] bg-[#121821] pl-9 pr-3 text-sm text-[#E6E8EB] outline-none placeholder:text-[#6f7a86] focus:border-[#C58B2A]"
              name="globalSearch"
              placeholder="Global search company, tender, buyer, award"
              type="search"
            />
          </form>
          <button className="border border-[#2A3441] bg-[#121821] p-2 text-[#9AA4AF] hover:text-[#E6E8EB]" type="button" aria-label="Notifications">
            <Bell className="h-4 w-4" />
          </button>
          <button className="hidden items-center gap-2 border border-[#2A3441] bg-[#121821] px-3 py-2 text-sm text-[#E6E8EB] md:flex" type="button">
            <UserCircle className="h-4 w-4 text-[#9AA4AF]" />
            Analyst
          </button>
        </div>
      </header>

      <AnimatePresence>
        {(mobileOpen || true) && (
          <motion.aside
            animate={{ width: collapsed ? 72 : 232 }}
            className={`fixed bottom-0 left-0 top-14 z-30 border-r border-[#2A3441] bg-[#0B0F14] ${mobileOpen ? "block" : "hidden lg:block"}`}
            initial={false}
            transition={{ duration: 0.16 }}
          >
            <div className="flex h-full flex-col">
              <div className="flex items-center justify-between border-b border-[#2A3441] p-3">
                {!collapsed ? <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#9AA4AF]">Navigation</div> : null}
                <button className="border border-[#2A3441] p-1 text-[#9AA4AF] hover:text-[#E6E8EB]" onClick={() => setCollapsed((value) => !value)} type="button" aria-label="Collapse sidebar">
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
                          ? "border-[#C58B2A] bg-[#171F2A] text-[#E6E8EB]"
                          : "border-transparent text-[#9AA4AF] hover:border-[#2A3441] hover:bg-[#121821] hover:text-[#E6E8EB]"
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
