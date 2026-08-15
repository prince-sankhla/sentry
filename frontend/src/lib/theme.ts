/**
 * SENTRY design tokens, as JavaScript.
 *
 * The CSS `@theme` block in `app/globals.css` is the source of truth for
 * anything that can wear a Tailwind class. Some surfaces can't: ECharts,
 * React Flow and react-simple-maps paint to canvas/SVG and need literal
 * colour strings. Those read from here.
 *
 * Keep this file in lockstep with the `@theme` block — same names, same
 * values. It exists to stop hex literals scattering back through the app.
 */

/* ------------------------------------------------------------------ palette */

export const PALETTE = {
  /* surfaces */
  bg: "#0F1115",
  bg2: "#171A21",
  surface: "#1D232E",
  surface2: "#232A36",
  elevated: "#2A323F",

  /* hairlines */
  border: "#262C37",
  borderStrong: "#333B48",

  /* text ramp */
  text: "#F5F7FA",
  muted: "#8D98A7",
  faint: "#626C7A",

  /* emerald — brand + primary action only, never status */
  accent: "#10B981",
  accentHi: "#34D399",
  accentLo: "#059669",

  /* semantic */
  success: "#2F9E6E",
  warning: "#C8963E",
  danger: "#D4574E",
  info: "#6E8B93"
} as const;

/**
 * Risk severity lattice — ordinal, low → critical.
 *
 * Deliberately desaturated and deliberately *not* emerald: brand and status
 * must never share a signal, or a primary button reads as a "low risk" chip.
 */
export const RISK = {
  low: "#6E8B93",
  medium: "#C8963E",
  high: "#D4574E",
  critical: "#B03A50",
  /** no evidence / below reporting threshold */
  insufficient: "#4A5462"
} as const;

export type RiskLevel = keyof typeof RISK;

/* -------------------------------------------------------------------- charts */

/** Shared ECharts palette, pulled from the design tokens. */
export const CHART = {
  accent: PALETTE.accent,
  accentHi: PALETTE.accentHi,
  /** legacy alias retained for existing call sites */
  copper: PALETTE.accent,
  info: PALETTE.info,
  steel: PALETTE.info,
  cyan: "#4AA3A8",
  success: PALETTE.success,
  danger: PALETTE.danger,
  warning: PALETTE.warning,
  grid: PALETTE.border,
  axis: PALETTE.faint,
  text: PALETTE.muted,
  surface: PALETTE.surface,
  border: PALETTE.border
} as const;

/**
 * Ordered categorical series palette.
 *
 * Emerald leads; everything after it is desaturated and spaced far enough
 * apart in hue and lightness to stay separable — including in greyscale and
 * for the common forms of colour-vision deficiency. No rainbow.
 */
export const CHART_SERIES = [
  "#10B981", // emerald
  "#6E8B93", // slate-teal
  "#C8963E", // muted gold
  "#7C8AA0", // slate
  "#4AA3A8", // teal
  "#8D98A7" // graphite
] as const;

export const tooltipStyle = {
  backgroundColor: "rgba(15,17,21,0.96)",
  borderColor: PALETTE.border,
  borderWidth: 1,
  textStyle: { color: PALETTE.text, fontSize: 12 },
  extraCssText:
    "border-radius:12px;box-shadow:0 18px 48px -24px rgba(0,0,0,0.85);backdrop-filter:blur(8px);padding:8px 10px;"
} as const;

/* --------------------------------------------------------------------- graph */

/**
 * Relationship-graph node treatment.
 *
 * Monochrome by design, matching the landing-page hero graph: every node is
 * the same graphite chip and type is read from its icon, not its hue. Emerald
 * is reserved for selection, focus and path highlight — so the one coloured
 * thing on screen is always the thing you're looking at.
 */
export const GRAPH = {
  node: {
    fill: "#1D232E",
    fillHover: "#232A36",
    border: "#333B48",
    icon: "#8D98A7",
    label: "#F5F7FA",
    sublabel: "#8D98A7"
  },
  /** selected / searched / on the highlighted path */
  highlight: {
    fill: "#132A26",
    border: PALETTE.accent,
    icon: PALETTE.accent,
    glow: "rgba(16,185,129,0.28)"
  },
  /** de-emphasised when a selection is active */
  dimmed: {
    fill: "#171A21",
    border: "#262C37",
    icon: "#4A5462",
    label: "#626C7A"
  },
  edge: {
    default: "#333B48",
    dimmed: "#232A36",
    highlight: PALETTE.accent,
    /** risk-bearing relationships keep a status tint */
    risk: RISK.high
  }
} as const;

/* ----------------------------------------------------------------- geography */

/**
 * Choropleth ramp for the India map: empty graphite → deep emerald.
 * Sequential and perceptually ordered, so density reads without a legend.
 */
export const MAP = {
  empty: "#171A21",
  scale: ["#1B2A2A", "#1C3A34", "#1B5344", "#137256", "#10B981"] as const,
  stroke: "#0F1115",
  hover: PALETTE.accentHi,
  pressed: PALETTE.accent,
  marker: PALETTE.accentHi,
  markerStroke: "#0F1115"
} as const;

/**
 * Interpolate the choropleth ramp. `t` is clamped to 0–1.
 * Returns `MAP.empty` for t <= 0 so "no data" stays visually distinct
 * from "lowest bucket".
 */
export function mapColor(t: number): string {
  if (!Number.isFinite(t) || t <= 0) return MAP.empty;
  const clamped = Math.min(1, t);
  const scale = MAP.scale;
  const pos = clamped * (scale.length - 1);
  const i = Math.min(scale.length - 2, Math.floor(pos));
  return mix(scale[i], scale[i + 1], pos - i);
}

/** Linear RGB mix between two hex colours. */
export function mix(a: string, b: string, t: number): string {
  const ca = hexToRgb(a);
  const cb = hexToRgb(b);
  const r = Math.round(ca[0] + (cb[0] - ca[0]) * t);
  const g = Math.round(ca[1] + (cb[1] - ca[1]) * t);
  const bl = Math.round(ca[2] + (cb[2] - ca[2]) * t);
  return `#${[r, g, bl].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16)
  ];
}

/** Hex + alpha → rgba() string. Handy for canvas glows and washes. */
export function alpha(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}
