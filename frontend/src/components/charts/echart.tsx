"use client";

/**
 * Thin wrapper around Apache ECharts. We import only the modules we use (tree-shaken)
 * and register them once. All SENTRY charts render through this so theming, sizing,
 * and lazy-loading stay consistent. Heavy — only mount on the client.
 */
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  GraphicComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsCoreOption } from "echarts/core";
import { useEffect, useRef } from "react";

echarts.use([
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
  CanvasRenderer
]);

/**
 * ECharts renders to a canvas, so CSS custom properties cannot be consumed by
 * the canvas renderer. The application palette is intentionally centralised in
 * `lib/theme.ts`; this bridge remaps those known palette literals whenever light
 * mode is active. Dark mode passes the original option through unchanged.
 */
const LIGHT_COLOR_MAP: Record<string, string> = {
  "#0F1115": "#FFFFFF",
  "#171A21": "#F7F9FB",
  "#1D232E": "#FFFFFF",
  "#232A36": "#F2F6F7",
  "#2A323F": "#FFFFFF",
  "#262C37": "#DFE6E8",
  "#333B48": "#C8D3D6",
  "#F5F7FA": "#182126",
  "#8D98A7": "#66737A",
  "#626C7A": "#8A969B",
  "#4A5462": "#66737A",
  "#7C8AA0": "#687A84",
  "#4AA3A8": "#327F84",
  "rgba(15,17,21,0.96)": "rgba(255,255,255,0.98)",
  "rgba(0,0,0,0.85)": "rgba(26,43,49,0.14)"
};

function isLightTheme(): boolean {
  return typeof document !== "undefined" && document.documentElement.classList.contains("sentry-light");
}

function resolveThemeValue(value: string): string {
  if (!isLightTheme()) return value;
  return LIGHT_COLOR_MAP[value.toUpperCase()] ?? LIGHT_COLOR_MAP[value] ?? value;
}

function resolveThemeOption<T>(value: T): T {
  if (!isLightTheme()) return value;
  if (typeof value === "string") return resolveThemeValue(value) as T;
  if (Array.isArray(value)) return value.map((item) => resolveThemeOption(item)) as T;
  if (value && typeof value === "object") {
    const output: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      output[key] = resolveThemeOption(item);
    }
    return output as T;
  }
  return value;
}

export function EChart({
  option,
  height = 240,
  className = "",
  onEvents
}: {
  option: EChartsCoreOption;
  height?: number | string;
  className?: string;
  onEvents?: Record<string, (params: unknown) => void>;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const optionRef = useRef(option);
  optionRef.current = option;

  const applyOption = () => {
    chartRef.current?.setOption(resolveThemeOption(optionRef.current), true);
  };

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    applyOption();

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);

    const onThemeChange = () => applyOption();
    window.addEventListener("sentry:theme-change", onThemeChange);

    return () => {
      observer.disconnect();
      window.removeEventListener("sentry:theme-change", onThemeChange);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    applyOption();
  }, [option]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || !onEvents) return;
    for (const [event, handler] of Object.entries(onEvents)) {
      chart.on(event, handler);
    }
    return () => {
      for (const event of Object.keys(onEvents)) chart.off(event);
    };
  }, [onEvents]);

  return <div ref={ref} className={className} style={{ height, width: "100%" }} />;
}

/**
 * Chart theming lives in `lib/theme.ts` alongside the graph and map palettes,
 * so every canvas surface on the platform reads from one place. Re-exported
 * here for the existing call sites.
 */
export { CHART, CHART_SERIES, tooltipStyle } from "@/lib/theme";
