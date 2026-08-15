import {
  Award,
  Building2,
  FileSignature,
  FileText,
  Landmark,
  ScrollText,
  UserRound
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * The seven entity types SENTRY resolves and connects. Shared across the
 * marketing hero graph, the "why" section, and the sources grid so the
 * vocabulary stays consistent with the investigation workspace.
 */
export type NodeKind =
  | "buyer"
  | "supplier"
  | "company"
  | "director"
  | "award"
  | "document"
  | "tender";

export const NODE_TYPES: Record<NodeKind, { label: string; icon: LucideIcon }> = {
  buyer: { label: "Buyers", icon: Landmark },
  supplier: { label: "Suppliers", icon: Building2 },
  company: { label: "Companies", icon: Building2 },
  director: { label: "Directors", icon: UserRound },
  award: { label: "Awards", icon: Award },
  document: { label: "Documents", icon: FileText },
  tender: { label: "Tenders", icon: ScrollText }
};

export const NODE_ORDER: NodeKind[] = [
  "buyer",
  "supplier",
  "company",
  "director",
  "award",
  "document",
  "tender"
];

export const CONTRACT_ICON = FileSignature;
