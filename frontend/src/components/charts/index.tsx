"use client";

import type { EChartsCoreOption } from "echarts/core";
import { useMemo } from "react";
import { CHART, EChart, tooltipStyle } from "./echart";

/* ============================================================ Donut */

export type DonutSlice = { name: string; value: number; color: string };

export function DonutChart({
  slices,
  centerLabel,
  centerValue,
  height = 260
}: {
  slices: DonutSlice[];
  centerLabel?: string;
  centerValue?: string;
  height?: number;
}) {
  const option = useMemo<EChartsCoreOption>(
    () => ({
      tooltip: {
        trigger: "item",
        ...tooltipStyle,
        formatter: (p: { name: string; value: number; percent: number }) =>
          `${p.name}<br/><b>${p.value.toLocaleString("en-IN")}</b> · ${p.percent}%`
      },
      series: [
        {
          type: "pie",
          radius: ["62%", "88%"],
          center: ["50%", "50%"],
          avoidLabelOverlap: false,
          padAngle: 2,
          itemStyle: { borderRadius: 6, borderColor: CHART.surface, borderWidth: 2 },
          label: { show: false },
          labelLine: { show: false },
          emphasis: { scale: true, scaleSize: 6 },
          data: slices.map((s) => ({ name: s.name, value: s.value, itemStyle: { color: s.color } }))
        }
      ],
      graphic: centerValue
        ? [
            {
              type: "text",
              left: "center",
              top: "42%",
              style: { text: centerValue, fill: "#e7ecf3", fontSize: 30, fontWeight: 700, textAlign: "center" }
            },
            {
              type: "text",
              left: "center",
              top: "58%",
              style: { text: centerLabel ?? "", fill: CHART.text, fontSize: 12, textAlign: "center" }
            }
          ]
        : []
    }),
    [slices, centerLabel, centerValue]
  );
  return <EChart option={option} height={height} />;
}

/* ============================================================ Area trend */

export function AreaTrend({
  categories,
  values,
  color = CHART.accent,
  height = 220,
  valueFormatter
}: {
  categories: string[];
  values: number[];
  color?: string;
  height?: number;
  valueFormatter?: (v: number) => string;
}) {
  const option = useMemo<EChartsCoreOption>(
    () => ({
      grid: { left: 8, right: 12, top: 16, bottom: 24, containLabel: true },
      tooltip: {
        trigger: "axis",
        ...tooltipStyle,
        formatter: (params: Array<{ axisValue: string; value: number }>) => {
          const p = params[0];
          return `${p.axisValue}<br/><b>${valueFormatter ? valueFormatter(p.value) : p.value.toLocaleString("en-IN")}</b>`;
        }
      },
      xAxis: {
        type: "category",
        data: categories,
        boundaryGap: false,
        axisLine: { lineStyle: { color: CHART.grid } },
        axisTick: { show: false },
        axisLabel: { color: CHART.axis, fontSize: 10 }
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { color: CHART.grid, type: "dashed" } },
        axisLabel: { color: CHART.axis, fontSize: 10, formatter: (v: number) => compact(v) }
      },
      series: [
        {
          type: "line",
          data: values,
          smooth: 0.35,
          symbol: "circle",
          symbolSize: 6,
          showSymbol: false,
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          areaStyle: {
            color: {
              type: "linear",
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: hexA(color, 0.35) },
                { offset: 1, color: hexA(color, 0) }
              ]
            }
          }
        }
      ]
    }),
    [categories, values, color, valueFormatter]
  );
  return <EChart option={option} height={height} />;
}

/* ============================================================ Mini sparkline */

export function Sparkline({
  values,
  color = CHART.success,
  height = 40,
  width = 96
}: {
  values: number[];
  color?: string;
  height?: number;
  width?: number;
}) {
  const option = useMemo<EChartsCoreOption>(
    () => ({
      grid: { left: 1, right: 1, top: 3, bottom: 3 },
      xAxis: { type: "category", show: false, data: values.map((_, i) => i) },
      yAxis: { type: "value", show: false, min: "dataMin", max: "dataMax" },
      series: [
        {
          type: "line",
          data: values,
          smooth: 0.4,
          symbol: "none",
          lineStyle: { color, width: 1.6 },
          areaStyle: {
            color: {
              type: "linear",
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: hexA(color, 0.28) },
                { offset: 1, color: hexA(color, 0) }
              ]
            }
          }
        }
      ]
    }),
    [values, color]
  );
  return <EChart option={option} height={height} className="!w-full" />;
}

/* ============================================================ Horizontal bars */

export function HBarChart({
  labels,
  values,
  color = CHART.accent,
  height = 240,
  valueFormatter
}: {
  labels: string[];
  values: number[];
  color?: string;
  height?: number;
  valueFormatter?: (v: number) => string;
}) {
  const option = useMemo<EChartsCoreOption>(
    () => ({
      grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        ...tooltipStyle,
        formatter: (params: Array<{ name: string; value: number }>) => {
          const p = params[0];
          return `${p.name}<br/><b>${valueFormatter ? valueFormatter(p.value) : p.value.toLocaleString("en-IN")}</b>`;
        }
      },
      xAxis: { type: "value", splitLine: { lineStyle: { color: CHART.grid, type: "dashed" } }, axisLabel: { color: CHART.axis, fontSize: 10, formatter: (v: number) => compact(v) } },
      yAxis: {
        type: "category",
        data: [...labels].reverse(),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: CHART.text, fontSize: 11, width: 130, overflow: "truncate" }
      },
      series: [
        {
          type: "bar",
          data: [...values].reverse(),
          barWidth: "56%",
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: { type: "linear", x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: hexA(color, 0.5) }, { offset: 1, color }] }
          }
        }
      ]
    }),
    [labels, values, color, valueFormatter]
  );
  return <EChart option={option} height={height} />;
}

/* ============================================================ helpers */

function compact(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e7) return `${(v / 1e7).toFixed(1)}Cr`;
  if (abs >= 1e5) return `${(v / 1e5).toFixed(1)}L`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return String(v);
}

function hexA(hex: string, alpha: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
