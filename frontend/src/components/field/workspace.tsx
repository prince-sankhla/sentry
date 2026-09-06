"use client";

import { useState } from "react";
import { Activity, Camera, CheckCircle2, FileText, Gauge, MapPin, Radar, ShieldCheck, Siren, Wifi } from "lucide-react";
import { Badge } from "@/components/ui/page";

const capabilities = ["Pothole","Road crack","Streetlight","CCTV","Signboard","Drain / manhole","Solar panel","QR / asset ID","OCR"];
const evidence = [
  {id:"P-0042",type:"Pothole",confidence:"91%",meta:"Ward 14 · 23:18:44"},
  {id:"SL-0118",type:"Streetlight",confidence:"96%",meta:"Pole chainage 1.84 km · 23:18:31"},
  {id:"CC-0081",type:"CCTV",confidence:"88%",meta:"Gate junction · Pole 08 · 23:18:17"}
];

export function FieldWorkspace(){
  const [tab,setTab]=useState<"live"|"evidence"|"contract">("live");
  const [armed,setArmed]=useState(true);
  return <main className="space-y-6">
    <section className="rounded-2xl border border-border bg-surface p-6 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div><div className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-accent"><Radar className="h-3.5 w-3.5"/>SENTRY FIELD <span className="text-faint">/</span><span className="text-muted">Physical Verification Console</span></div><h1 className="text-3xl font-semibold tracking-tight text-text md:text-5xl">Field mission control</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-muted">Convert contract requirements into machine inspections and preserve accepted observations as traceable field evidence.</p></div>
        <div className="flex flex-wrap gap-2"><Badge tone="success"><span className="h-1.5 w-1.5 rounded-full bg-current"/> Rover online</Badge><Badge tone="info"><Wifi className="h-3 w-3"/> Camera stream</Badge><button onClick={()=>setArmed(!armed)} className="rounded-lg border border-border px-3 py-1.5 text-xs font-semibold text-text hover:border-accent/40">{armed?"Pause mission":"Arm mission"}</button></div>
      </div>
    </section>

    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {[["Mission coverage","47 / 50","94% inspected",Radar],["Field findings","3","Needs review",Siren],["Evidence captured","18","Traceable events",FileText],["Live inference","9.8 FPS","CPU runtime",Gauge]].map(([a,b,c,Icon])=><div key={a as string} className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="flex justify-between"><div><div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">{a as string}</div><div className="mt-2 text-2xl font-semibold text-text">{b as string}</div><div className="mt-1 text-xs text-muted">{c as string}</div></div><Icon className="h-4 w-4 text-accent"/></div></div>)}
    </section>

    <section className="grid gap-6 lg:grid-cols-[230px_minmax(0,1fr)_300px]">
      <aside className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Mission #ST-2048</div><div className="mt-3 rounded-xl border border-accent/20 bg-accent/5 p-3"><div className="text-sm font-semibold text-text">Urban road & asset verification</div><div className="mt-1 text-xs leading-5 text-muted">Verify road defects, streetlights, cameras and asset identity.</div></div><div className="my-4 h-px bg-border"/><div className="flex justify-between text-xs"><span className="text-muted">Coverage</span><span className="text-text">94%</span></div><div className="mt-2 h-1.5 rounded-full bg-bg-2"><div className="h-full w-[94%] rounded-full bg-accent"/></div><div className="mt-5 text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Capabilities</div><div className="mt-3 space-y-2">{capabilities.map(x=><div key={x} className="flex items-center gap-2 text-xs text-text"><CheckCircle2 className="h-3.5 w-3.5 text-success"/>{x}</div>)}</div></aside>

      <div className="min-w-0 rounded-2xl border border-border bg-surface shadow-sm"><div className="flex items-center justify-between border-b border-border px-4 py-3"><div className="flex gap-1 rounded-lg bg-surface-2 p-1">{(["live","evidence","contract"] as const).map(x=><button key={x} onClick={()=>setTab(x)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize ${tab===x?"bg-surface text-text shadow-sm":"text-muted"}`}>{x}</button>)}</div><div className="text-[11px] text-muted"><TimerDot/> Auto-capture enabled</div></div>
        {tab==="live"&&<div className="p-4"><div className="relative aspect-video overflow-hidden rounded-xl bg-[#10131a]"><div className="absolute left-4 top-4 flex gap-2"><Badge tone="success"><Activity className="h-3 w-3"/> LIVE</Badge><Badge tone="muted"><Camera className="h-3 w-3"/> Front camera</Badge></div><div className="absolute inset-x-[14%] bottom-[24%] top-[26%] rounded-xl border border-accent/70"/><div className="absolute bottom-[20%] left-[17%] rounded-lg bg-accent px-2.5 py-1 text-[11px] font-semibold text-white">Pothole · 0.91</div><div className="absolute bottom-4 left-4 text-[10px] text-white/60"><MapPin className="mr-1 inline h-3 w-3"/> GPS waiting for rover telemetry</div></div><div className="mt-4 grid gap-3 sm:grid-cols-3">{[["Current finding","Pothole #P-0042","Confidence 91%"],["Context","Road zone accepted","No person overlap"],["Evidence","Frame preserved","Event ID generated"]].map(x=><div key={x[0]} className="rounded-xl border border-border bg-surface-2 p-3"><div className="text-[10px] uppercase tracking-[0.14em] text-faint">{x[0]}</div><div className="mt-1 text-sm font-semibold text-text">{x[1]}</div><div className="mt-1 text-xs text-muted">{x[2]}</div></div>)}</div></div>}
        {tab==="evidence"&&<div className="divide-y divide-border">{evidence.map(x=><div key={x.id} className="grid gap-3 p-4 md:grid-cols-[76px_1fr_auto] md:items-center"><div className="flex aspect-square items-center justify-center rounded-xl border border-border bg-surface-2"><FileText className="h-6 w-6 text-accent"/></div><div><div className="text-sm font-semibold text-text">{x.type} · {x.id}</div><div className="mt-1 text-xs text-muted">{x.meta}</div><div className="mt-1 text-xs text-faint">Confidence {x.confidence}</div></div><Badge tone="success">Observed</Badge></div>)}</div>}
        {tab==="contract"&&<div className="p-4"><div className="rounded-xl border border-border bg-surface-2 p-4"><div className="text-[10px] uppercase tracking-[0.14em] text-faint">Requirement R-01</div><div className="mt-1 text-lg font-semibold text-text">Install and maintain 50 streetlights</div><div className="mt-5 grid gap-3 sm:grid-cols-3">{[["Expected","50"],["Observed","47"],["Unverified","3"]].map(x=><div key={x[0]} className="rounded-xl border border-border bg-surface p-3"><div className="text-[10px] uppercase tracking-[0.14em] text-faint">{x[0]}</div><div className="mt-1 text-xl font-semibold text-text">{x[1]}</div></div>)}</div></div></div>}
      </div>

      <aside className="space-y-4"><div className="rounded-2xl border border-border bg-surface p-4 shadow-sm"><div className="flex justify-between"><div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-faint">Field signal</div><Badge tone="success">Stable</Badge></div><div className="mt-4 space-y-3">{[["Camera","98%"],["Inference","92%"],["Evidence writer","100%"],["GPS","Not connected"]].map(x=><div key={x[0]} className="flex justify-between text-xs"><span className="text-text">{x[0]}</span><span className={x[1]==="Not connected"?"text-faint":"text-success"}>{x[1]}</span></div>)}</div></div><div className="rounded-2xl border border-accent/20 bg-accent/5 p-4"><div className="flex gap-3"><ShieldCheck className="h-5 w-5 text-accent"/><div><div className="text-sm font-semibold text-text">Investigator attention</div><p className="mt-1 text-xs leading-5 text-muted">Observed discrepancies become verification tasks, not automatic legal conclusions.</p></div></div></div></aside>
    </section>
  </main>;
}
function TimerDot(){return <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-success"/>}
