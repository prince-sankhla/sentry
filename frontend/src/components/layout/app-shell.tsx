"use client";

import { motion } from "framer-motion";
import { Activity, Award, Bell, BookOpenCheck, Building2, ChevronsLeft, FileCheck2, FileText, Flag, FolderSearch, GitBranch, Globe2, Inbox, LayoutDashboard, ListChecks, Map as MapIcon, Menu, Radar, Search, Settings, Clock, UserCircle, Command, Zap, ClipboardCheck, BriefcaseBusiness, RadioTower, ShieldCheck } from "lucide-react";
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
  { label: "Overview", items: [
    { href: "/", icon: LayoutDashboard, label: "Command Center" },
    { href: "/demo", icon: BookOpenCheck, label: "Demo Runbook", roles: ["public_investigator", "journalist_researcher", "government_audit"] }
  ]},
  { label: "Work Queues", items: [
    { href: "/flagged-tenders", icon: Flag, label: "Flagged Tenders", roles: ["government_audit", "journalist_researcher"] },
    { href: "/recommended-tenders", icon: ListChecks, label: "Recommended Tenders", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/field", icon: RadioTower, label: "Physical Verification", roles: ["government_audit", "journalist_researcher"] },
    { href: "/tenders", icon: FileText, label: "All Tenders" }
  ]},
  { label: "Investigation", items: [
    { href: "/investigations", icon: FolderSearch, label: "Investigation Workspace", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/provenance", icon: ShieldCheck, label: "Provenance Verification", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/research", icon: Search, label: "Guided Research", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/context", icon: Globe2, label: "Open-source Context", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/verification", icon: FileCheck2, label: "Evidence Verification", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/review", icon: ClipboardCheck, label: "Official Review", roles: ["public_investigator", "journalist_researcher", "government_audit"] },
    { href: "/review/inbox", icon: Inbox, label: "Review Inbox", roles: ["government_audit"] },
    { href: "/cases", icon: BriefcaseBusiness, label: "Case Management", roles: ["government_audit"] }
  ]},
  { label: "Review Tools", items: [
    { href: "/risk", icon: Radar, label: "Risk Assessment", roles: ["journalist_researcher", "government_audit"] },
    { href: "/red-flags", icon: Flag, label: "Red-flag Engine", roles: ["government_audit", "journalist_researcher"] },
    { href: "/monitoring", icon: RadioTower, label: "Live Monitoring", roles: ["government_audit", "journalist_researcher"] }
  ]},
  { label: "Records & Analysis", items: [
    { href: "/companies", icon: Building2, label: "Supplier Records" },
    { href: "/buyers", icon: Building2, label: "Buyer Intelligence", roles: ["journalist_researcher", "government_audit"] },
    { href: "/awards", icon: Award, label: "Award Records" },
    { href: "/graph", icon: GitBranch, label: "Relationship Graph", roles: ["journalist_researcher", "government_audit"] },
    { href: "/timeline", icon: Clock, label: "Timeline", roles: ["journalist_researcher", "government_audit"] },
    { href: "/map", icon: MapIcon, label: "Geography", roles: ["journalist_researcher", "government_audit"] },
    { href: "/reports", icon: Activity, label: "Portfolio Reports", roles: ["journalist_researcher", "government_audit"] }
  ]},
  { label: "System", items: [
    { href: "/profile", icon: UserCircle, label: "Analyst Profile" },
    { href: "/settings", icon: Settings, label: "Settings" }
  ]}
];
