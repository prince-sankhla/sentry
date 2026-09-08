"use client";

import { useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, ExternalLink, FileSearch, MapPin, ShieldAlert, Wrench } from "lucide-react";
import { useRouter } from "next/navigation";

const CASES = {
  "delhi-cwg": {
    key: "delhi-cwg",
    title: "Delhi Street-Light Modernisation — CWG-2010",
    eyebrow: "REAL CASE · CAG AUDIT RECONSTRUCTION",
    authority: "GNCTD / PWD / MCD / NDMC",
    location: "Delhi",
    value: "₹286 crore tendered cost",
    source: "CAG Performance Audit Report No. 4 of 2011 · Chapter 5 / Report context",
    sourceUrl: "https://cag.gov.in/webroot/uploads/download_audit_report/2011/Union_Performance_Civil_XIXth_Commonwealth_Games_6_2011_chapter_22.pdf",
    summary: "CAG examined the modernisation of Delhi's street-light system across around 800 km of roads and reported procurement and competition concerns.",
    facts: [
      ["Scale", "~800 km of Delhi roads"],
      ["Tendered cost", "₹286 crore"],
      ["Avoidable extra expenditure", "₹31.07 crore across three agencies"],
      ["Price example", "Keselec-Schreder Ambar-3: ₹15,160 as indigenous in PWD vs ₹32,000 as imported in MCD"],
    ],
    signals: [
      { level: "HIGH", title: "Import / domestic price anomaly", body: "CAG reported that imported luminaries were procured at materially higher prices and identified ₹31.07 crore of avoidable extra expenditure." },
      { level: "HIGH", title: "Specification / evaluation gap", body: "CAG reported identical technical specifications for imported and indigenous luminaries, while a supporting techno-economic evaluation was not documented." },
      { level: "MEDIUM", title: "Procurement design concern", body: "The audit found that the procurement process did not ensure procurement at competitive rates and questioned differentiation between imported and indigenous luminaries." },
    ],
    alternative: [
      "Different site or performance requirements could explain some price variation.",
      "Imported products could have had legitimate technical advantages.",
      "Procurement conditions, maintenance scope or other contract terms may affect unit cost.",
      "Those explanations require supporting records; an anomaly is not itself proof of wrongdoing.",
    ],
    next: [
      "Retrieve the original tender and technical specifications.",
      "Compare imported vs indigenous specifications line-by-line.",
      "Retrieve invoices, quotations and approval / evaluation records.",
      "Trace the documented justification for the imported-luminaire decision.",
    ],
    fieldRequirement: "streetlight",
    fieldLabel: "Physical verification of installed streetlights and asset identity",
  },
  "dhanbad-led": {
    key: "dhanbad-led",
    title: "Dhanbad Municipal LED Street Lights",
    eyebrow: "REAL CASE · CAG AUDIT RECONSTRUCTION",
    authority: "Dhanbad Municipal Corporation",
    location: "Dhanbad, Jharkhand",
    value: "Estimate ₹4.15 crore · payment ₹3.63 crore",
    source: "CAG Annual Technical Inspection Report on Local Bodies, year ended 31 March 2016",
    sourceUrl: "https://cag.gov.in/webroot/uploads/download_audit_report/2017/Annual_Technical_Inspection_Report_of_2017_-_Local_Bodies_Government_of_Jharkhand.pdf",
    summary: "CAG examined installation and functionality of LED street lights and documented specification changes, payment, and physical-verification issues.",
    facts: [
      ["Estimated", "809 LED lights · ₹4.15 crore"],
      ["Supplied", "795 lights · payment ₹3.63 crore"],
      ["Audit verification", "237 lights jointly physically verified"],
      ["Observed issue", "171 of 237 (72%) were non-functional or functioning improperly"],
      ["Unfruitful expenditure", "₹0.79 crore attributed to the 171 lights"],
    ],
    signals: [
      { level: "HIGH", title: "Field-condition discrepancy", body: "Audit's joint physical verification found 171 of the 237 checked lights non-functional or improperly functioning." },
      { level: "HIGH", title: "Specification reduction without price reduction", body: "CAG reported reductions in wattage, LED efficiency and ingress protection while the price was not reduced accordingly." },
      { level: "MEDIUM", title: "Contractor-responsibility gap", body: "The audit linked feeder-pillar, timer, earthing and LED-panel issues to responsibilities stated in the agreement." },
    ],
    alternative: [
      "Some failures may have been temporary and covered by warranty obligations.",
      "Site electrical infrastructure can affect performance independently of procurement intent.",
      "A physical failure finding does not by itself establish fraudulent intent.",
      "The next step is to reconcile contract, warranty, maintenance and payment records with field evidence.",
    ],
    next: [
      "Retrieve the final technical specification and approved changes.",
      "Reconcile supplied quantity, payment records and asset register.",
      "Verify warranty / maintenance obligations and service calls.",
      "Repeat field verification on a representative sample and preserve dated evidence.",
    ],
    fieldRequirement: "streetlight",
    fieldLabel: "Physical verification of streetlight presence / visible condition / asset identity",
  },
} as const;

type CaseKey = keyof typeof CASES;

export function RealAuditCaseStudio({ caseKey }: { caseKey?: string }) {
  const router = useRouter();
  const initial = (caseKey && caseKey in CASES ? caseKey : "delhi-cwg") as CaseKey;
  const [selectedKey, setSelectedKey] = useState<CaseKey>(initial);
  const [phase, setPhase] = useState<"overview" | "evidence" | "assessment" | "next">("overview");
  const item = CASES[selectedKey];
  const phases = useMemo(() => [
    ["overview", "Case intake"],
    ["evidence", "Evidence review"],
    ["assessment", "Risk assessment"],
    ["next", "Next verification"],
  ] as const, []);

  function selectCase(key: CaseKey) {
    setSelectedKey(key);
    setPhase("overview");
    router.replace(`/investigate?case=${key}`);
  }

  function goField() {
    router.push(`/field?case=${item.key}`);
  }

  return (
    <section className="mt-8 overflow-hidden rounded-3xl border border-border bg-surface shadow-sm">
      <div className="border-b border-border bg-bg-2/50 p-6 md:p-8">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-4xl">
            <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold uppercase tracking-[.16em] text-accent">
              <ShieldAlert className="h-3.5 w-3.5" />
              {item.eyebrow}
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-text md:text-4xl">{item.title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{item.summary}</p>
          </div>
          <a href={item.sourceUrl} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs font-semibold text-text">
            <FileSearch className="h-3.5 w-3.5" /> Open CAG source <ExternalLink className="h-3 w-3" />
          </a>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Meta label="Authority" value={item.authority} />
          <Meta label="Location" value={item.location} />
          <Meta label="Value context" value={item.value} />
          <Meta label="Provenance" value="Official CAG audit record" />
        </div>
      </div>

      <div className="border-b border-border px-4 py-3 md:px-6">
        <div className="flex flex-wrap gap-2">
          {(Object.keys(CASES) as CaseKey[]).map((key) => (
            <button key={key} onClick={() => selectCase(key)} className={`rounded-xl border px-3 py-2 text-xs font-semibold ${selectedKey === key ? "border-accent/40 bg-accent/10 text-text" : "border-border text-muted"}`}>
              {CASES[key].title}
            </button>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {phases.map(([key, label], index) => (
            <button key={key} onClick={() => setPhase(key)} className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-semibold ${phase === key ? "bg-accent/10 text-accent" : "text-muted"}`}>
              <span className="grid h-5 w-5 place-items-center rounded-full border border-border text-[9px]">{index + 1}</span>{label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-6 md:p-8">
        {phase === "overview" && (
          <div className="grid gap-4 lg:grid-cols-4">
            {item.facts.map(([label, value]) => <Fact key={label} label={label} value={value} />)}
          </div>
        )}

        {phase === "evidence" && (
          <div className="grid gap-4 lg:grid-cols-3">
            {item.signals.map((signal) => <Signal key={signal.title} level={signal.level} title={signal.title} body={signal.body} />)}
          </div>
        )}

        {phase === "assessment" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Why SENTRY flags this">
              {item.signals.map((signal) => <div key={signal.title} className="mb-4 last:mb-0"><div className="text-xs font-semibold text-text">{signal.title}</div><p className="mt-1 text-xs leading-5 text-muted">{signal.body}</p></div>)}
            </Panel>
            <Panel title="Alternative explanations / guardrail">
              <div className="space-y-2">{item.alternative.map((line) => <div key={line} className="flex gap-2 text-xs leading-5 text-muted"><CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />{line}</div>)}</div>
            </Panel>
          </div>
        )}

        {phase === "next" && (
          <div className="grid gap-4 lg:grid-cols-[1.2fr_.8fr]">
            <Panel title="Investigator next checks">
              <div className="space-y-3">{item.next.map((line, index) => <div key={line} className="flex gap-3"><span className="grid h-6 w-6 shrink-0 place-items-center rounded-full border border-border text-[10px] font-semibold text-accent">{index + 1}</span><div className="text-sm leading-6 text-text">{line}</div></div>)}</div>
            </Panel>
            <Panel title="Physical verification gate">
              <div className="rounded-2xl border border-accent/20 bg-accent/5 p-4">
                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.14em] text-accent"><Wrench className="h-3.5 w-3.5" /> Verification required</div>
                <p className="mt-2 text-sm font-semibold text-text">{item.fieldLabel}</p>
                <p className="mt-2 text-xs leading-5 text-muted">SENTRY has a procurement-side signal. The next question is what actually exists in the field. Open the same case in SENTRY FIELD to dispatch the rover mission and attach dated visual evidence.</p>
                <button onClick={goField} className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-accent px-4 py-3 text-xs font-semibold text-bg">
                  Continue to SENTRY FIELD <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </Panel>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3 border-t border-border bg-bg-2/30 p-5 md:flex-row md:items-center md:justify-between">
        <div className="text-xs text-muted"><span className="font-semibold text-text">Investigation posture:</span> evidence-backed signal, not an automatic finding of fraud.</div>
        <div className="flex gap-2">
          {phase !== "overview" && <button onClick={() => setPhase(phases[Math.max(0, phases.findIndex(([key]) => key === phase) - 1)][0])} className="rounded-xl border border-border px-3 py-2 text-xs font-semibold text-muted">Back</button>}
          {phase !== "next" && <button onClick={() => setPhase(phases[Math.min(phases.length - 1, phases.findIndex(([key]) => key === phase) + 1)][0])} className="inline-flex items-center gap-2 rounded-xl border border-accent/30 bg-accent/10 px-3 py-2 text-xs font-semibold text-text">Continue <ArrowRight className="h-3 w-3" /></button>}
          {phase === "next" && <button onClick={goField} className="inline-flex items-center gap-2 rounded-xl bg-accent px-3 py-2 text-xs font-semibold text-bg"><MapPin className="h-3.5 w-3.5" /> Open Field Verification</button>}
        </div>
      </div>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[9px] font-semibold uppercase tracking-[.14em] text-faint">{label}</div><div className="mt-1 text-xs font-semibold leading-5 text-text">{value}</div></div>;
}
function Fact({ label, value }: { label: string; value: string }) {
  return <div className="rounded-2xl border border-border bg-surface-2 p-4"><div className="text-[9px] font-semibold uppercase tracking-[.14em] text-faint">{label}</div><div className="mt-2 text-sm font-semibold leading-6 text-text">{value}</div></div>;
}
function Signal({ level, title, body }: { level: string; title: string; body: string }) {
  return <div className="rounded-2xl border border-border bg-surface-2 p-5"><div className="inline-flex rounded-full bg-accent/10 px-2 py-1 text-[9px] font-semibold uppercase tracking-[.13em] text-accent">{level}</div><div className="mt-3 text-sm font-semibold text-text">{title}</div><p className="mt-2 text-xs leading-5 text-muted">{body}</p></div>;
}
function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-border bg-surface-2 p-5"><div className="mb-4 text-[10px] font-semibold uppercase tracking-[.15em] text-accent">{title}</div>{children}</div>;
}
