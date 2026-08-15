"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useId } from "react";

import { CONTRACT_ICON, NODE_TYPES, type NodeKind } from "./node-types";

/**
 * The hero's floating investigation graph — glass + brushed metal, a central
 * evidence core with the seven entity types orbiting it on slowly-animating
 * connection lines. Pure SVG + Framer Motion (deterministic layout, no random
 * data, no fabricated statistics). Reused wherever a live graph motif is shown.
 */

type GraphNode = {
  kind: NodeKind;
  /** polar position around the core, in degrees + radius fraction */
  angle: number;
  radius: number;
};

// Deterministic, hand-placed layout — reads as an intentional constellation.
const NODES: GraphNode[] = [
  { kind: "buyer", angle: -90, radius: 1 },
  { kind: "tender", angle: -32, radius: 1.05 },
  { kind: "award", angle: 28, radius: 1 },
  { kind: "document", angle: 90, radius: 1.02 },
  { kind: "company", angle: 150, radius: 1 },
  { kind: "director", angle: -150, radius: 1.05 },
  { kind: "supplier", angle: -118, radius: 0.62 }
];

const CX = 260;
const CY = 230;
const BASE_R = 168;

function polar(angle: number, radius: number) {
  const rad = (angle * Math.PI) / 180;
  return { x: CX + Math.cos(rad) * BASE_R * radius, y: CY + Math.sin(rad) * BASE_R * radius };
}

export function InvestigationGraph({ className = "" }: { className?: string }) {
  const reduce = useReducedMotion();
  const gid = useId().replace(/:/g, "");

  return (
    <div className={`relative ${className}`}>
      <svg
        viewBox="0 0 520 460"
        className="h-full w-full"
        role="img"
        aria-label="Investigation graph connecting buyers, suppliers, companies, directors, awards, documents and tenders"
      >
        <defs>
          <radialGradient id={`${gid}-core`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#34d399" stopOpacity="0.95" />
            <stop offset="55%" stopColor="#10b981" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#059669" stopOpacity="0.15" />
          </radialGradient>
          <linearGradient id={`${gid}-line`} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.05" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.6" />
          </linearGradient>
          <filter id={`${gid}-glow`} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* connection lines (drawn first, behind nodes) */}
        {NODES.map((n, i) => {
          const p = polar(n.angle, n.radius);
          return (
            <g key={`edge-${n.kind}`}>
              <line x1={CX} y1={CY} x2={p.x} y2={p.y} stroke={`url(#${gid}-line)`} strokeWidth={1.2} />
              {!reduce && (
                <line
                  x1={CX}
                  y1={CY}
                  x2={p.x}
                  y2={p.y}
                  stroke="#34d399"
                  strokeWidth={1.4}
                  strokeOpacity={0.9}
                  className="mkt-flow"
                  style={{ animationDelay: `${i * 0.32}s` }}
                />
              )}
            </g>
          );
        })}

        {/* central evidence core */}
        <motion.g
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        >
          <circle cx={CX} cy={CY} r={46} fill={`url(#${gid}-core)`} filter={`url(#${gid}-glow)`} />
          <motion.circle
            cx={CX}
            cy={CY}
            r={30}
            fill="#0f1115"
            stroke="#34d399"
            strokeWidth={1.5}
            animate={reduce ? {} : { r: [30, 33, 30] }}
            transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut" }}
          />
          <g transform={`translate(${CX - 11} ${CY - 11})`} className="text-[#34d399]">
            <CoreMark />
          </g>
        </motion.g>

        {/* entity nodes */}
        {NODES.map((n, i) => {
          const p = polar(n.angle, n.radius);
          const { icon: Icon, label } = NODE_TYPES[n.kind];
          return (
            <motion.g
              key={n.kind}
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3 + i * 0.09, duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
            >
              <motion.g
                animate={reduce ? {} : { y: [0, i % 2 ? -5 : -8, 0] }}
                transition={{ duration: 5 + i * 0.4, repeat: Infinity, ease: "easeInOut" }}
              >
                <circle cx={p.x} cy={p.y} r={26} fill="#1d232e" stroke="#333b48" strokeWidth={1} />
                <circle cx={p.x} cy={p.y} r={26} fill="none" stroke="#10b981" strokeWidth={1} strokeOpacity={0.35} />
                <foreignObject x={p.x - 13} y={p.y - 20} width={26} height={26}>
                  <div className="flex h-[26px] items-center justify-center text-[#8dd9bd]">
                    <Icon className="h-[15px] w-[15px]" />
                  </div>
                </foreignObject>
                <text
                  x={p.x}
                  y={p.y + 20}
                  textAnchor="middle"
                  className="fill-[#8d98a7] text-[8.5px] font-medium uppercase tracking-wider"
                >
                  {label}
                </text>
              </motion.g>
            </motion.g>
          );
        })}
      </svg>

      {/* corner provenance chip — honest, no fabricated counts */}
      <div className="pointer-events-none absolute bottom-3 right-3 flex items-center gap-1.5 rounded-full border border-[#262c37] bg-[#171a21]/80 px-2.5 py-1 text-[10px] font-medium text-[#8d98a7] backdrop-blur">
        <CONTRACT_ICON className="h-3 w-3 text-[#10b981]" />
        Connected from official records
      </div>
    </div>
  );
}

function CoreMark() {
  // Minimal hexagon shield — the SENTRY evidence-core glyph.
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <path
        d="M11 1.5 19 6v10l-8 4.5L3 16V6l8-4.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M11 6.5v9M6.5 9l9 4M15.5 9l-9 4" stroke="currentColor" strokeWidth="1.1" strokeOpacity="0.7" />
    </svg>
  );
}
