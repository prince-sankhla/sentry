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

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, true);
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

/** Shared palette pulled from the design tokens. */
export const CHART = {
  accent: "#d29a4e",
  accentHi: "#ecbd74",
  copper: "#c07c48",
  info: "#5f92c2",
  steel: "#5f92c2",
  cyan: "#46b4c4",
  success: "#3ec08a",
  danger: "#e5484d",
  warning: "#e0a63e",
  grid: "#232a33",
  axis: "#626c7a",
  text: "#98a2b0",
  surface: "#14181e",
  border: "#232a33"
} as const;

/** Ordered categorical series palette — graphite-friendly, no rainbow.
 *  Copper leads, then steel, emerald, amber, cyan, muted slate. */
export const CHART_SERIES = [
  "#d29a4e",
  "#5f92c2",
  "#3ec08a",
  "#e0a63e",
  "#46b4c4",
  "#8a94a4"
] as const;

export const tooltipStyle = {
  backgroundColor: "rgba(14,17,22,0.96)",
  borderColor: CHART.border,
  borderWidth: 1,
  textStyle: { color: "#e9edf2", fontSize: 12 },
  extraCssText:
    "border-radius:12px;box-shadow:0 18px 48px -24px rgba(0,0,0,0.85);backdrop-filter:blur(8px);"
} as const;
