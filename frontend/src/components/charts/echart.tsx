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

/**
 * Chart theming lives in `lib/theme.ts` alongside the graph and map palettes,
 * so every canvas surface on the platform reads from one place. Re-exported
 * here for the existing call sites.
 */
export { CHART, CHART_SERIES, tooltipStyle } from "@/lib/theme";
