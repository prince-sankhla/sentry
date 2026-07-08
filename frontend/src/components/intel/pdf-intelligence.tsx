"use client";

/**
 * PdfIntelligence — structured intelligence pulled from a tender document.
 *
 * Renders the backend `TenderDocumentExtraction` (deterministic, grounded regex
 * extraction). Every field keeps the exact source span it was read from — shown
 * on demand as proof — plus a per-field confidence. Fields absent from the text
 * are simply not shown; when nothing is extractable the panel is hidden entirely.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  Boxes,
  CalendarClock,
  CalendarDays,
  FileScan,
  Hash,
  IndianRupee,
  Layers,
  Quote,
  Receipt,
  ShieldCheck,
  Users
} from "lucide-react";
import { useState } from "react";
import type { ExtractedField, TenderDocumentExtraction } from "@/lib/api";

type FieldSpec = { key: keyof TenderDocumentExtraction; label: string; icon: React.ReactNode };

const FIELDS: FieldSpec[] = [
  { key: "tender_reference", label: "Tender Number", icon: <Hash className="h-3.5 w-3.5" /> },
  { key: "estimated_value", label: "Estimated Value", icon: <IndianRupee className="h-3.5 w-3.5" /> },
  { key: "emd_amount", label: "EMD", icon: <ShieldCheck className="h-3.5 w-3.5" /> },
  { key: "tender_fee", label: "Tender Fee", icon: <Receipt className="h-3.5 w-3.5" /> },
  { key: "bid_submission_end", label: "Submission Deadline", icon: <CalendarClock className="h-3.5 w-3.5" /> },
  { key: "bid_opening_date", label: "Opening Date", icon: <CalendarDays className="h-3.5 w-3.5" /> },
  { key: "category", label: "Category", icon: <Layers className="h-3.5 w-3.5" /> },
  { key: "bidders_count", label: "Bidder Count", icon: <Users className="h-3.5 w-3.5" /> }
];

export function PdfIntelligence({ extraction }: { extraction: TenderDocumentExtraction | null }) {
  if (!extraction || extraction.empty) return null;

  const present = FIELDS.map((f) => ({ spec: f, field: extraction[f.key] as ExtractedField | null })).filter(
    (x): x is { spec: FieldSpec; field: ExtractedField } => Boolean(x.field)
  );

  if (present.length === 0) return null;

  const coveragePct = Math.round(extraction.coverage * 100);

  return (
    <div>
      {/* header strip */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-[14px] border border-accent/20 bg-accent/[0.05] px-4 py-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg border border-accent/30 bg-accent/10 text-accent">
            <FileScan className="h-4 w-4" />
          </span>
          <div>
            <div className="text-sm font-semibold text-text">Automatically extracted</div>
            <div className="text-[11px] text-faint">
              {present.length} field{present.length > 1 ? "s" : ""} · {extraction.char_count.toLocaleString()} chars analysed
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Boxes className="h-3.5 w-3.5 text-accent" />
          <div className="text-right">
            <div className="text-[9px] uppercase tracking-wide text-faint">Extraction confidence</div>
            <div className="tabular text-sm font-semibold text-accent">{coveragePct}%</div>
          </div>
        </div>
      </div>

      {/* field grid */}
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {present.map(({ spec, field }, i) => (
          <FieldCard key={spec.key as string} label={spec.label} icon={spec.icon} field={field} index={i} />
        ))}
      </div>
    </div>
  );
}

function FieldCard({
  label,
  icon,
  field,
  index
}: {
  label: string;
  icon: React.ReactNode;
  field: ExtractedField;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const conf = Math.round(field.confidence * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.05, duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="group overflow-hidden rounded-[14px] border border-border bg-surface/70 p-3.5 transition-colors hover:border-accent/40"
    >
      <div className="flex items-center justify-between">
        <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">
          <span className="text-accent">{icon}</span>
          {label}
        </span>
        <span className="tabular text-[10px] text-muted">{conf}%</span>
      </div>

      <div className="mt-1.5 break-words text-[15px] font-semibold text-text">{field.value}</div>

      {/* confidence bar */}
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-bg-2">
        <motion.div
          className="h-full rounded-full bg-accent/70"
          initial={{ width: 0 }}
          animate={{ width: `${conf}%` }}
          transition={{ duration: 0.6, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>

      {/* source span — the proof */}
      {field.source_span && (
        <>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="mt-2 inline-flex items-center gap-1 text-[10px] font-medium text-accent transition hover:text-accent-hi"
          >
            <Quote className={`h-3 w-3 transition ${open ? "opacity-100" : "opacity-70"}`} />
            {open ? "Hide source span" : "Source span"}
          </button>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <p className="mt-1.5 rounded-lg border border-border bg-bg-2/50 p-2 font-mono text-[10px] leading-relaxed text-muted">
                  “…{field.source_span}…”
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </motion.div>
  );
}
