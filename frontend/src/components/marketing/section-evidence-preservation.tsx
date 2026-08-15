"use client";

import { motion } from "framer-motion";
import { BadgeCheck, Clock, ExternalLink, Hash, Link2, ShieldCheck } from "lucide-react";

const STEPS = [
  {
    n: "01",
    label: "Original Source Captured",
    sub: "Every evidence item records the canonical government portal URL at time of retrieval.",
    icon: ExternalLink,
    tone: "text-accent"
  },
  {
    n: "02",
    label: "Retrieval Timestamp",
    sub: "ISO 8601 timestamp of exact retrieval — admissible as evidence chain metadata.",
    icon: Clock,
    tone: "text-info"
  },
  {
    n: "03",
    label: "Content Archived",
    sub: "The full HTML and PDF (where available) are stored. The investigation survives even if the original page is taken offline.",
    icon: ShieldCheck,
    tone: "text-success"
  },
  {
    n: "04",
    label: "Integrity Hash (SHA-256)",
    sub: "Every archived document receives a SHA-256 content hash. Any tampering is immediately detectable.",
    icon: Hash,
    tone: "text-accent"
  },
  {
    n: "05",
    label: "Permanent Evidence Link",
    sub: "A stable, internal evidence URL that never expires — even when the government portal changes or removes the original.",
    icon: Link2,
    tone: "text-info"
  },
  {
    n: "06",
    label: "Verified Badge",
    sub: "Evidence cards display SHA-256 verification status. Judges, auditors and courts can independently verify the chain of custody.",
    icon: BadgeCheck,
    tone: "text-success"
  }
];

/** Mock evidence card for the illustration */
function EvidenceCardMock() {
  return (
    <div className="w-full max-w-sm rounded-2xl border border-border bg-surface/80 text-left shadow-2xl shadow-black/40">
      {/* header */}
      <div className="flex items-center gap-2 border-b border-border bg-bg-2/50 px-4 py-3">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-accent/30 bg-accent/[0.08] text-accent">
          <ShieldCheck className="h-3.5 w-3.5" />
        </span>
        <span className="flex-1 truncate text-[11.5px] font-medium text-muted">Odisha e-Procurement Portal</span>
        <span className="shrink-0 rounded-md border border-accent/30 bg-accent/[0.08] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-accent">India</span>
      </div>
      {/* body */}
      <div className="p-4">
        <div className="text-[13px] font-medium leading-relaxed text-text">
          Dharmagarh NAC Ward-7 Approach Road — Construction of Drain (Ref: ODP-2024-0781)
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {[
            { label: "Published", value: "14 Mar 2024" },
            { label: "Confidence", value: "97%" }
          ].map((p) => (
            <div key={p.label} className="rounded-lg border border-border bg-bg-2/40 px-2.5 py-2">
              <div className="text-[9px] font-semibold uppercase tracking-wide text-faint">{p.label}</div>
              <div className="mt-1 text-[11.5px] font-semibold text-text">{p.value}</div>
            </div>
          ))}
        </div>
        {/* preservation row */}
        <div className="mt-3 border-t border-border/60 pt-3">
          <div className="mb-2 flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-2/60 px-2.5 py-1.5 text-[11px] font-medium text-muted">
              <ExternalLink className="h-3 w-3" /> Open Original Source
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-success/30 bg-success/[0.07] px-2.5 py-1.5 text-[11px] font-medium text-success">
              <ShieldCheck className="h-3 w-3" /> Archived Evidence
            </span>
          </div>
          <div className="flex items-center gap-3 text-[10.5px] text-faint">
            <span className="flex items-center gap-1">
              <span className="text-faint/60">Retrieved</span> 19 Apr 2024
            </span>
            <span className="flex items-center gap-1 font-mono">
              <span className="text-faint/60">SHA-256</span>
              a3f8d2e1…c7b04f
              <span className="ml-0.5 rounded border border-success/20 bg-success/[0.06] px-1 py-px text-[9px] font-bold uppercase tracking-wide text-success">✓</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function SectionEvidencePreservation() {
  return (
    <section className="relative mx-auto max-w-6xl px-6 py-32">
      <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="grid grid-cols-1 items-center gap-16 lg:grid-cols-[1fr_420px]">
        {/* left: copy */}
        <div>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="t-label mb-4 text-accent">Evidence preservation</div>
            <h2 className="text-4xl font-semibold leading-tight tracking-tight text-text sm:text-5xl">
              Investigations that hold up.
              <br />
              <span className="text-muted">Forever.</span>
            </h2>
            <p className="mt-6 text-lg leading-relaxed text-muted">
              Government pages disappear. URLs expire. PDFs get deleted. SENTRY archives
              every piece of evidence at retrieval time, so your investigation is reproducible
              years after the original source goes offline.
            </p>
          </motion.div>

          <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: "-40px" }}
                  transition={{ duration: 0.45, delay: i * 0.06, ease: [0.22, 1, 0.36, 1] }}
                  className="flex items-start gap-3"
                >
                  <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg border border-border bg-bg-2 ${s.tone}`}>
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-[10px] text-faint">{s.n}</span>
                      <span className="text-[13px] font-semibold text-text">{s.label}</span>
                    </div>
                    <p className="mt-1 text-[12px] leading-relaxed text-faint">{s.sub}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* right: live evidence card mock */}
        <motion.div
          initial={{ opacity: 0, x: 24 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="flex items-center justify-center lg:justify-end"
        >
          <EvidenceCardMock />
        </motion.div>
      </div>

      {/* bottom callout */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="mt-16 grid grid-cols-1 gap-4 sm:grid-cols-3"
      >
        {[
          { label: "Original Source Unavailable?", value: "Archived copy automatically served" },
          { label: "Content Changed?", value: "Hash mismatch instantly detected" },
          { label: "Need to Reproduce?", value: "Every investigation is fully replayable" }
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-border bg-bg-2/40 p-4 text-center">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-faint">{item.label}</div>
            <div className="mt-2 text-[13.5px] font-semibold text-text">{item.value}</div>
          </div>
        ))}
      </motion.div>
    </section>
  );
}
