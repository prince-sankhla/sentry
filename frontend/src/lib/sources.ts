/**
 * Indian-procurement-first source registry.
 *
 * SENTRY is primarily an Indian procurement intelligence platform. Indian
 * connectors (GeM, CPPP, NIC eProcurement portals) must be surfaced above
 * supplementary international sources (World Bank) everywhere: dashboards,
 * tables, reports, source lists. This module is the single source of truth
 * for a source's display label, priority rank, and region flag.
 */

export type SourceMeta = {
  key: string;
  label: string;
  short: string;
  /** Lower = higher priority (Indian sources first). */
  priority: number;
  indian: boolean;
};

const REGISTRY: Record<string, SourceMeta> = {
  gem: { key: "gem", label: "GeM (Government e-Marketplace)", short: "GeM", priority: 0, indian: true },
  cppp: { key: "cppp", label: "CPPP (Central Public Procurement)", short: "CPPP", priority: 1, indian: true },
  datagovin: { key: "datagovin", label: "data.gov.in", short: "data.gov.in", priority: 2, indian: true },
  eproc_maharashtra: { key: "eproc_maharashtra", label: "Maharashtra eProcurement", short: "Maharashtra", priority: 3, indian: true },
  eproc_kerala: { key: "eproc_kerala", label: "Kerala eProcurement", short: "Kerala", priority: 4, indian: true },
  eproc_odisha: { key: "eproc_odisha", label: "Odisha eProcurement", short: "Odisha", priority: 5, indian: true },
  eproc_westbengal: { key: "eproc_westbengal", label: "West Bengal eProcurement", short: "West Bengal", priority: 6, indian: true },
  eproc_karnataka: { key: "eproc_karnataka", label: "Karnataka eProcurement", short: "Karnataka", priority: 7, indian: true },
  state_eproc: { key: "state_eproc", label: "NIC State eProcurement", short: "NIC State", priority: 8, indian: true },
  adb: { key: "adb", label: "Asian Development Bank", short: "ADB", priority: 20, indian: false },
  un_procurement: { key: "un_procurement", label: "UN Procurement", short: "UN", priority: 21, indian: false },
  world_bank: { key: "world_bank", label: "World Bank Procurement", short: "World Bank", priority: 30, indian: false },
  prozorro: { key: "prozorro", label: "ProZorro (Ukraine)", short: "ProZorro", priority: 31, indian: false }
};

const FALLBACK: SourceMeta = { key: "unknown", label: "Other Source", short: "Other", priority: 50, indian: false };

export function sourceMeta(key: string | null | undefined): SourceMeta {
  if (!key) return FALLBACK;
  const normalized = key.toLowerCase().trim();
  return REGISTRY[normalized] ?? { ...FALLBACK, key: normalized, label: prettify(normalized), short: prettify(normalized) };
}

export function sourceLabel(key: string | null | undefined): string {
  return sourceMeta(key).short;
}

export function isIndianSource(key: string | null | undefined): boolean {
  return sourceMeta(key).indian;
}

/** Sort any list by Indian-first source priority. */
export function bySourcePriority<T>(items: T[], getKey: (item: T) => string | null | undefined): T[] {
  return [...items].sort((a, b) => sourceMeta(getKey(a)).priority - sourceMeta(getKey(b)).priority);
}

function prettify(key: string): string {
  return key
    .replace(/^eproc_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
