"use client";

import { motion } from "framer-motion";
import { Activity, Award, Bell, Building2, ChevronsLeft, FileCheck2, FileText, Flag, FolderSearch, GitBranch, Inbox, LayoutDashboard, Map as MapIcon, Menu, Radar, Search, Settings, Clock, UserCircle, Command, Zap, ClipboardCheck, BriefcaseBusiness } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { StatusChip } from "@/components/ui/chip";
import { Wordmark } from "@/components/ui/logo";
import { EASE, SPRING } from "@/lib/motion";
import { CommandPalette } from "./command-palette";
import { PageTransition } from "./page-transition";
import { getStoredWorkspaceRole, WorkspaceRoleSwitcher, WORKSPACE_ROLES, type WorkspaceRole } from "./workspace-role";

const navGroups: { label: string; items: { href: string; icon: typeof LayoutDashboard; label: string; roles?: WorkspaceRole[] }[] }[] = [
  { label: "Intelligence", items: [
    { href: "/", icon: LayoutDashboard, label: "Command Center" },
    { href: "/investigations", icon: FolderSearch, label: "Investigation Workspace", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/research", icon: Search, label: "Guided Research", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/verification", icon: FileCheck2, label: "Evidence Verification", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/review", icon: ClipboardCheck, label: "Official Review", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/review/inbox", icon: Inbox, label: "Review Inbox", roles: ["government_audit"] },
    { href: "/cases", icon: BriefcaseBusiness, label: "Case Management", roles: ["government_audit"] },
    { href: "/buyers", icon: Building2, label: "Buyer Intelligence", roles: ["journalist_researcher", "government_audit"] },
    { href: "/graph", icon: GitBranch, label: "Relationship Graph", roles: ["journalist_researcher", "government_audit"] },
    { href: "/risk", icon: Radar, label: "Risk Assessment", roles: ["journalist_researcher", "government_audit"] },
    { href: "/red-flags", icon: Flag, label: "Red-flag Screening", roles: ["government_audit", "journalist_researcher"] }
  ]},
  { label: "Records", items: [
    { href: "/tenders", icon: FileText, label: "Tender Records" },
    { href: "/companies", icon: Building2, label: "Supplier Records" },
    { href: "/awards", icon: Award, label: "Award Records" }
  ]},
  { label: "Analysis", items: [
    { href: "/timeline", icon: Clock, label: "Timeline", roles: ["journalist_researcher", "government_audit"] },
    { href: "/map", icon: MapIcon, label: "Geography", roles: ["journalist_researcher", "government_audit"] },
    { href: "/reports", icon: Activity, label: "Portfolio Reports", roles: ["journalist_researcher", "government_audit"] }
  ]},
  { label: "System", items: [
    { href: "/profile", icon: UserCircle, label: "Analyst Profile" },
    { href: "/settings", icon: Settings, label: "Settings" }
  ]}
];

function roleDefinition(role: WorkspaceRole) { return WORKSPACE_ROLES.find((item) => item.id === role) ?? WORKSPACE_ROLES[0]; }

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [role, setRole] = useState<WorkspaceRole>("public_investigator");
  const isMarketing = pathname === "/";

  useEffect(() => {
    setRole(getStoredWorkspaceRole());
    function onRoleChange(event: Event) { const next = (event as CustomEvent<WorkspaceRole>).detail; if (WORKSPACE_ROLES.some((item) => item.id === next)) setRole(next); }
    window.addEventListener("sentry:workspace-role", onRoleChange);
    return () => window.removeEventListener("sentry:workspace-role", onRoleChange);
  }, []);
  useEffect(() => { function onKey(e: KeyboardEvent) { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPaletteOpen((v) => !v); } } window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); }, []);
  useEffect(() => setMobileOpen(false), [pathname]);

  const width = collapsed ? 76 : 248;
  const currentRole = useMemo(() => roleDefinition(role), [role]);
  if (isMarketing) return <div className="min-h-screen">{children}</div>;

  return <div className="min-h-screen bg-bg text-text">
    <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center gap-3 border-b border-border bg-bg-2/80 px-4 backdrop-blur-xl">
      <Button variant="ghost" size="sm" iconOnly className="lg:hidden" onClick={() => setMobileOpen((v) => !v)} aria-label="Toggle navigation" icon={<Menu className="h-5 w-5" />} />
      <Link href="/" className="group flex items-center gap-2.5 pl-1 pr-2" aria-label="SENTRY home"><Wordmark tagline="Evidence over assumptions" size="sm" /></Link>
      <button onClick={() => setPaletteOpen(true)} className="group ml-3 flex h-10 max-w-xl flex-1 items-center gap-2.5 rounded-xl border border-border bg-bg/50 px-3.5 text-left text-sm text-faint transition-all duration-200 hover:border-border-strong hover:bg-surface/60" type="button"><Search className="h-4 w-4 text-muted group-hover:text-accent" /><span className="flex-1 truncate">Search companies, buyers, tenders, awards…</span><kbd className="hidden rounded-md border border-border bg-bg-2 px-1.5 py-0.5 text-[10px] font-medium text-muted sm:flex">⌘K</kbd></button>
      <div className="ml-auto flex items-center gap-2.5"><WorkspaceRoleSwitcher /><span className="hidden xl:block"><StatusChip label={currentRole.shortLabel} detail="Workspace" pulse /></span><div className="mx-0.5 hidden h-5 w-px bg-border xl:block" /><Button variant="subtle" iconOnly aria-label="Notifications" className="relative" icon={<><Bell className="h-4 w-4" /><span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-danger ring-2 ring-bg-2" /></>} /><Link href="/profile" className="flex items-center gap-2 rounded-xl border border-border bg-surface/60 px-2 py-1.5 text-sm text-text transition-all hover:border-border-strong md:pr-3"><span className="grid h-6 w-6 place-items-center rounded-lg bg-accent/12 text-accent"><UserCircle className="h-4 w-4" /></span><span className="hidden md:block">Analyst</span></Link></div>
    </header>
    <motion.aside animate={{ width }} initial={false} transition={{ duration: 0.18, ease: EASE }} className={`fixed bottom-0 left-0 top-16 z-30 border-r border-border bg-bg-2/70 backdrop-blur-xl ${mobileOpen ? "block" : "hidden lg:block"}`}>
      <div className="flex h-full flex-col overflow-y-auto px-3 py-5"><nav className="flex-1 space-y-6">{navGroups.map((group) => { const visibleItems = group.items.filter((item) => !item.roles || item.roles.includes(role)); if (!visibleItems.length) return null; return <div key={group.label}>{!collapsed && <div className="t-label px-2 pb-2.5">{group.label}</div>}<div className="space-y-0.5">{visibleItems.map((item) => { const Icon = item.icon; const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href)); return <Link key={item.href} href={item.href} title={collapsed ? item.label : undefined} className={`group relative flex h-10 items-center gap-3 rounded-xl px-3 text-[13.5px] transition-colors duration-150 ${active ? "font-medium text-text" : "text-muted hover:bg-surface/50 hover:text-text"}`}>{active && <motion.span layoutId="nav-active" transition={SPRING} className="absolute inset-0 rounded-xl border border-border-strong/60 bg-surface-2" />}{active && <span className="absolute inset-y-2 left-0 z-10 w-0.5 rounded-full bg-accent" />}<Icon className={`relative z-10 h-[18px] w-[18px] shrink-0 ${active ? "text-accent" : "group-hover:text-text"}`} />{!collapsed && <span className="relative z-10 truncate">{item.label}</span>}</Link>; })}</div></div>; })}</nav>
        {!collapsed && <div className="mt-5 rounded-2xl border border-border bg-surface/60 p-4 elevate"><div className="flex items-center gap-2 text-[13.5px] font-semibold text-text"><span className="grid h-6 w-6 place-items-center rounded-lg border border-accent/25 bg-accent/[0.08] text-accent"><Zap className="h-3.5 w-3.5" /></span>New Investigation</div><p className="mt-2 text-[11.5px] leading-relaxed text-muted">{currentRole.description}</p><Button href="/investigations" variant="primary" size="sm" fullWidth className="mt-3.5" trailing={<Command className="h-3.5 w-3.5 opacity-70" />}>Start</Button></div>}
        <Button variant="ghost" size="sm" onClick={() => setCollapsed((v) => !v)} className="mt-3 hidden justify-start lg:flex" icon={<ChevronsLeft className={`h-4 w-4 transition-transform duration-200 ${collapsed ? "rotate-180" : ""}`} />}>{!collapsed && "Collapse"}</Button>
      </div>
    </motion.aside>
    {mobileOpen && <div className="fixed inset-0 top-16 z-20 bg-bg/60 backdrop-blur-sm lg:hidden" onClick={() => setMobileOpen(false)} />}
    <motion.main animate={{ paddingLeft: width }} initial={false} transition={{ duration: 0.18, ease: EASE }} className="min-h-screen pt-16 max-lg:!pl-0"><PageTransition>{children}</PageTransition></motion.main>
  </div>;
}
