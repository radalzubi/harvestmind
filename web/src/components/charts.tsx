"use client";

import React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  LabelList,
} from "recharts";
import type {
  ValueType,
  NameType,
} from "recharts/types/component/DefaultTooltipContent";
import type { RenderableText } from "recharts/types/component/Text";

const AXIS_STYLE = {
  fontFamily: "var(--sans)",
  fontSize: 10.5,
  fill: "#A1A1AA",
};

const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid var(--line)",
  borderRadius: 6,
  fontSize: 12,
  padding: "8px 10px",
  boxShadow: "var(--shadow-md)",
};

/** Safely coerce a Recharts ValueType to a plain number for formatting. */
function toNum(v: ValueType | undefined | null): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
  }
  if (Array.isArray(v)) return typeof v[0] === "number" ? v[0] : 0;
  return 0;
}

type LineSeriesPoint = {
  label: string;
  baseline?: number;
  optimised?: number;
  value?: number;
};

// ── LineSeries ─────────────────────────────────────────────────────────────────

export function LineSeries({
  data,
  series,
  height = 300,
  yFormat = (v: number) => `$${Math.round(v / 1000)}K`,
  area = true,
  showSavedDelta = false,
}: {
  data: LineSeriesPoint[];
  series: { key: keyof LineSeriesPoint; name: string; color: string }[];
  height?: number;
  yFormat?: (v: number) => string;
  area?: boolean;
  showSavedDelta?: boolean;
}) {
  // Recharts ContentType variance requires a targeted cast here; this is the
  // standard pattern for custom tooltip components in Recharts + TypeScript.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const renderTooltip = React.useCallback(
    (props: Record<string, unknown>) =>
      <SavedDeltaTooltip {...(props as any)} yFormat={yFormat} />,
    [yFormat],
  );

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
        <CartesianGrid stroke="#F2F2EF" strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="label"
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
          minTickGap={32}
        />
        <YAxis
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          tickFormatter={yFormat}
          width={48}
        />
        <Tooltip
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          content={showSavedDelta ? (renderTooltip as any) : undefined}
          contentStyle={TOOLTIP_STYLE}
          labelStyle={{ color: "#71717A", fontWeight: 500, marginBottom: 4 }}
          formatter={(v: ValueType | undefined) => yFormat(toNum(v))}
        />
        {series.map((s) => (
          <Area
            key={s.name}
            type="monotone"
            dataKey={s.key as string}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            fill={area ? s.color : "transparent"}
            fillOpacity={area ? 0.08 : 0}
            dot={false}
            activeDot={{ r: 3, strokeWidth: 1.5, stroke: "#fff", fill: s.color }}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── SavedDeltaTooltip (internal, typed with TooltipContentProps broad generic) ─

type TooltipEntry = {
  dataKey?: string | number;
  name?: string;
  value?: ValueType;
  color?: string;
};

function SavedDeltaTooltip({
  active,
  label,
  payload,
  yFormat,
}: {
  active?: boolean;
  label?: string | number;
  payload?: TooltipEntry[];
  yFormat: (v: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;

  const bEntry = payload.find((p) => p.dataKey === "baseline");
  const oEntry = payload.find((p) => p.dataKey === "optimised");
  const bNum = bEntry != null ? toNum(bEntry.value) : null;
  const oNum = oEntry != null ? toNum(oEntry.value) : null;
  const saved = bNum != null && oNum != null ? bNum - oNum : null;

  return (
    <div style={TOOLTIP_STYLE as React.CSSProperties}>
      <div style={{ color: "#71717A", fontWeight: 500, fontSize: 11.5, marginBottom: 6 }}>
        {String(label ?? "")}
      </div>
      {payload.map((p, i) => (
        <div
          key={String(p.dataKey ?? i)}
          style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, marginBottom: 2 }}
        >
          <span
            style={{ width: 8, height: 8, borderRadius: 2, background: p.color, flex: "none" }}
          />
          <span style={{ color: "#52525B" }}>{p.name}</span>
          <span style={{ marginLeft: "auto", color: "#0F172A", fontVariantNumeric: "tabular-nums" }}>
            {yFormat(toNum(p.value))}
          </span>
        </div>
      ))}
      {saved != null && (
        <div
          style={{
            marginTop: 6,
            paddingTop: 6,
            borderTop: "1px solid var(--line-soft)",
            display: "flex",
            justifyContent: "space-between",
            fontSize: 12.5,
            color: saved >= 0 ? "#15803D" : "#B91C1C",
            fontWeight: 500,
          }}
        >
          <span>Saved</span>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>
            {saved >= 0 ? "−" : "+"}
            {yFormat(Math.abs(saved))}
          </span>
        </div>
      )}
    </div>
  );
}

// ── GroupedBars ────────────────────────────────────────────────────────────────

export function GroupedBars({
  data,
  height = 280,
  yFormat = (v: number) => `$${v.toFixed(2)}`,
}: {
  data: { label: string; baseline: number; optimised: number }[];
  height?: number;
  yFormat?: (v: number) => string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}>
        <CartesianGrid stroke="#F2F2EF" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_STYLE} tickLine={false} axisLine={false} />
        <YAxis
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          tickFormatter={yFormat}
          width={48}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: ValueType | undefined) => yFormat(toNum(v))}
        />
        <Bar dataKey="baseline" fill="#E4E4E7" radius={[3, 3, 0, 0]} barSize={24} />
        <Bar dataKey="optimised" fill="#4F46E5" radius={[3, 3, 0, 0]} barSize={24} />
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── HBars ──────────────────────────────────────────────────────────────────────

export function HBars({
  data,
  height = 260,
  format = (v: number) => `$${Math.round(v).toLocaleString()}`,
  color = "#4F46E5",
}: {
  data: { reason: string; v: number }[];
  height?: number;
  format?: (v: number) => string;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 60, left: 8, bottom: 4 }}
      >
        <CartesianGrid stroke="#F2F2EF" horizontal={false} />
        <XAxis
          type="number"
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          tickFormatter={format}
        />
        <YAxis
          dataKey="reason"
          type="category"
          tick={{ ...AXIS_STYLE, fontSize: 12, fill: "#52525B" }}
          tickLine={false}
          axisLine={false}
          width={130}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: ValueType | undefined) => format(toNum(v))}
        />
        <Bar dataKey="v" fill={color} radius={[3, 3, 3, 3]} barSize={11}>
          <LabelList
            dataKey="v"
            position="right"
            formatter={(value: RenderableText) =>
              typeof value === "number" ? format(value) : ""
            }
            style={{ fontSize: 11.5, fill: "#27272A", fontFamily: "var(--sans)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── Waterfall ──────────────────────────────────────────────────────────────────

type WaterfallItem = { label: string; value: number; kind: "plus" | "minus" | "total" };

export function Waterfall({
  items,
  height = 280,
  yFormat = (v: number) => `$${Math.round(v / 1000)}K`,
}: {
  items: WaterfallItem[];
  height?: number;
  yFormat?: (v: number) => string;
}) {
  let running = 0;
  const data = items.map((it) => {
    if (it.kind === "total") {
      return { label: it.label, base: 0, fill: running, value: running, kind: "total" as const };
    }
    const sgn = it.kind === "minus" ? -1 : 1;
    const start = running;
    running += sgn * it.value;
    const top = Math.max(start, running);
    const bot = Math.min(start, running);
    return { label: it.label, base: bot, fill: top - bot, value: it.value, kind: it.kind };
  });

  const colorFor = (kind: "plus" | "minus" | "total") =>
    kind === "minus" ? "#B91C1C" : kind === "total" ? "#0F172A" : "#0F766E";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 16, right: 8, left: 8, bottom: 4 }}>
        <CartesianGrid stroke="#F2F2EF" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ ...AXIS_STYLE, fontSize: 11, fill: "#475569" }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          tick={AXIS_STYLE}
          tickLine={false}
          axisLine={false}
          tickFormatter={yFormat}
          width={48}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(
            _v: ValueType | undefined,
            _name: NameType | undefined,
            item: { payload?: { value?: number } },
          ) => yFormat(item.payload?.value ?? 0)}
        />
        <Bar dataKey="base" stackId="w" fill="transparent" />
        <Bar dataKey="fill" stackId="w" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={colorFor(d.kind)} />
          ))}
          <LabelList
            dataKey="value"
            position="top"
            formatter={(value: RenderableText) =>
              typeof value === "number" ? yFormat(value) : ""
            }
            style={{ fontSize: 11, fill: "#0F172A", fontFamily: "var(--sans)" }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ── MultiLine / StackedBars (Insights) ─────────────────────────────────────────
//
// Generic series for the Insights surface: the keys are whatever the server sent, the colours are
// the product palette, and a null stays a gap in the line rather than a zero. Non-colour
// distinction: every series also differs by stroke dash, so two lines never rely on hue alone.

const PALETTE = ["#4F46E5", "#0EA5E9", "#F59E0B", "#10B981", "#EF4444", "#8B5CF6", "#64748B"];
const DASHES = ["0", "6 3", "2 2", "8 4 2 4", "4 2", "10 2", "1 3"];

export interface GenericPoint { label: string; [key: string]: number | string | null | undefined }

export function MultiLine({
  data, series, height = 260, yFormat = (v: number) => v.toLocaleString("en-US"), onPoint, area = false,
}: {
  data: GenericPoint[];
  series: { key: string; name: string; color?: string }[];
  height?: number;
  yFormat?: (v: number) => string;
  onPoint?: (label: string) => void;
  area?: boolean;
}) {
  const Chart = area ? AreaChart : AreaChart;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <Chart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 4 }}
             onClick={(state: { activeLabel?: string | number } | null) => { if (onPoint && state?.activeLabel != null) onPoint(String(state.activeLabel)); }}>
        <CartesianGrid stroke="#F2F2EF" vertical={false} />
        <XAxis dataKey="label" tick={AXIS_STYLE} tickLine={false} axisLine={false} minTickGap={24} />
        <YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={56} tickFormatter={yFormat} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: ValueType | undefined, name: NameType | undefined) => [v == null ? "—" : yFormat(toNum(v)), String(name)]} />
        {series.map((s, i) => (
          <Area key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color ?? PALETTE[i % PALETTE.length]}
                strokeWidth={2} strokeDasharray={DASHES[i % DASHES.length]} fill={s.color ?? PALETTE[i % PALETTE.length]}
                fillOpacity={area ? 0.08 : 0} connectNulls={false} dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
        ))}
      </Chart>
    </ResponsiveContainer>
  );
}

export function StackedBars({
  data, series, height = 260, yFormat = (v: number) => v.toLocaleString("en-US"), onBar, layout = "horizontal",
}: {
  data: GenericPoint[];
  series: { key: string; name: string; color?: string }[];
  height?: number;
  yFormat?: (v: number) => string;
  onBar?: (label: string) => void;
  layout?: "horizontal" | "vertical";
}) {
  const vertical = layout === "vertical";
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout={layout} margin={{ top: 8, right: vertical ? 40 : 8, left: 8, bottom: 4 }}
                onClick={(state: { activeLabel?: string | number } | null) => { if (onBar && state?.activeLabel != null) onBar(String(state.activeLabel)); }}>
        <CartesianGrid stroke="#F2F2EF" vertical={vertical} horizontal={!vertical} />
        {vertical
          ? <><XAxis type="number" tick={AXIS_STYLE} tickLine={false} axisLine={false} tickFormatter={yFormat} /><YAxis type="category" dataKey="label" tick={AXIS_STYLE} tickLine={false} axisLine={false} width={150} /></>
          : <><XAxis dataKey="label" tick={AXIS_STYLE} tickLine={false} axisLine={false} minTickGap={24} /><YAxis tick={AXIS_STYLE} tickLine={false} axisLine={false} width={56} tickFormatter={yFormat} /></>}
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: ValueType | undefined, name: NameType | undefined) => [v == null ? "—" : yFormat(toNum(v)), String(name)]} />
        {series.map((s, i) => (
          <Bar key={s.key} dataKey={s.key} name={s.name} stackId="stack" fill={s.color ?? PALETTE[i % PALETTE.length]}
               radius={i === series.length - 1 ? [3, 3, 0, 0] : 0} isAnimationActive={false} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
