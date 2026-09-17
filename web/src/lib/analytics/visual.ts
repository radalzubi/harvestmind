/**
 * VisualSpec + ResultSet → what a renderer needs. Renderer-independent: nothing here names a
 * chart library. A Recharts renderer, a table and an export all read the same shapes.
 */
import type { Cell, Encoding, ResultColumn, ResultSet, VisualSpec, VisualType } from "./client";
import { cellText, cellValue, formatDimension, isNull } from "./spec";

export interface SeriesPoint { label: string; key: string; [series: string]: number | string | null }
export interface ChartData {
  /** x axis labels in order, with the raw member key for drill / cross-filter */
  points: SeriesPoint[];
  /** series keys (a measure id, or `${measure}::${member}` when a series dimension splits it) */
  series: Array<{ key: string; name: string; unit?: string; currency?: string | null; measure: string; member?: string }>;
  xDimension: ResultColumn | null;
  seriesDimension: ResultColumn | null;
  /** cells that were null with a reason, so the legend can say so */
  gaps: Array<{ label: string; series: string; reason: string }>;
  /** measures not drawn because their unit differs from the axis's; they stay in the table twin */
  notDrawn: Array<{ id: string; name: string; unit?: string }>;
}

export const SHAPE_MATRIX: Record<string, VisualType[]> = {
  trend: ["line", "area", "bar", "stacked_bar", "table", "pivot"],
  trend_series: ["line", "stacked_bar", "area", "table", "pivot", "heatmap"],
  ranking: ["hbar", "bar", "table", "pivot"],
  relationship: ["scatter", "table"],
  matrix: ["heatmap", "pivot", "table"],
  kpi: ["kpi", "table"],
  detail: ["table", "pivot"],
};

export function shapeOf(result: Pick<ResultSet, "columns" | "spec">): keyof typeof SHAPE_MATRIX {
  const dims = result.columns.filter((c) => c.kind === "dimension");
  const measures = result.columns.filter((c) => c.kind === "measure");
  const time = dims.some((d) => d.dimension_kind === "time");
  const members = dims.filter((d) => d.dimension_kind !== "time");
  if (time && !members.length) return "trend";
  if (time && members.length === 1) return "trend_series";
  if (!time && members.length === 2) return "matrix";
  if (!time && members.length === 1 && measures.length >= 2 && !result.spec.top_n && measures.some((m) => !m.additive)) return "relationship";
  if (!time && members.length === 1) return "ranking";
  if (!members.length && !time) return measures.length <= 3 ? "kpi" : "detail";
  return "detail";
}

export function allowedVisuals(result: Pick<ResultSet, "columns" | "spec">): VisualType[] {
  return SHAPE_MATRIX[shapeOf(result)];
}

export function recommendVisual(result: Pick<ResultSet, "columns" | "spec">): VisualType {
  const s = shapeOf(result);
  const measures = result.columns.filter((c) => c.kind === "measure");
  const additive = measures.every((m) => m.additive);
  switch (s) {
    case "trend": return measures.length === 1 && additive ? "area" : "line";
    case "trend_series": return additive && measures.length === 1 ? "stacked_bar" : "line";
    case "ranking": return "hbar";
    case "relationship": return "scatter";
    case "matrix": return measures.length === 1 ? "heatmap" : "pivot";
    case "kpi": return "kpi";
    default: return "table";
  }
}

/** Build series data for line / area / bar / stacked bar: x = time (or the first member), series = measures × optional member. */
export function chartData(result: ResultSet, encoding: Encoding | undefined, locale: "en" | "ar"): ChartData {
  const cols = result.columns;
  const dims = cols.map((c, i) => ({ c, i })).filter(({ c }) => c.kind === "dimension");
  const measures = cols.map((c, i) => ({ c, i })).filter(({ c }) => c.kind === "measure");
  const xId = encoding?.x ?? (dims.find(({ c }) => c.dimension_kind === "time") ?? dims[0])?.c.id ?? null;
  const x = dims.find(({ c }) => c.id === xId) ?? null;
  const seriesId = encoding?.series ?? dims.find(({ c }) => c.id !== xId)?.c.id ?? null;
  const s = dims.find(({ c }) => c.id === seriesId && c.id !== xId) ?? null;
  const yIds = encoding?.y?.length ? encoding.y : measures.map(({ c }) => c.id);
  // one unit per axis: a count next to a ratio would flatten the ratio to zero; the rest stay in the table
  const wanted = measures.filter(({ c }) => yIds.includes(c.id));
  const axisUnit = wanted[0]?.c.unit;
  const ys = wanted.filter(({ c }) => c.unit === axisUnit);
  const notDrawn = wanted.filter(({ c }) => c.unit !== axisUnit).map(({ c }) => ({ id: c.id, name: c.label[locale] ?? c.label.en, unit: c.unit }));
  const points = new Map<string, SeriesPoint>();
  const series = new Map<string, ChartData["series"][number]>();
  const gaps: ChartData["gaps"] = [];
  if (result.empty) return { points: [], series: [], xDimension: x?.c ?? null, seriesDimension: s?.c ?? null, gaps, notDrawn };
  for (const row of result.rows) {
    const key = x ? cellText(row[x.i]) : "all";
    const label = x ? formatDimension(row[x.i], x.c, locale) : "";
    const member = s ? cellText(row[s.i]) : null;
    const point = points.get(key) ?? { label, key };
    for (const { c, i } of ys) {
      const sk = member != null ? `${c.id}::${member}` : c.id;
      if (!series.has(sk)) series.set(sk, { key: sk, name: member != null ? (ys.length > 1 ? `${c.label[locale] ?? c.label.en} · ${member}` : member) : (c.label[locale] ?? c.label.en), unit: c.unit, currency: c.currency, measure: c.id, member: member ?? undefined });
      const v = cellValue(row[i]);
      point[sk] = v;
      if (v === null) gaps.push({ label, series: sk, reason: isNull(row[i]) ? row[i].reason : "UNKNOWN" });
    }
    points.set(key, point);
  }
  let ordered = [...points.values()];
  if (x?.c.dimension_kind === "time") ordered.sort((a, b) => a.key.localeCompare(b.key));
  const seriesList = [...series.values()];
  // series over members: cap what a chart can carry legibly; the table shows the rest
  if (seriesList.length > 12) {
    const keep = new Set(seriesList.slice(0, 12).map((z) => z.key));
    ordered = ordered.map((p) => Object.fromEntries(Object.entries(p).filter(([k]) => k === "label" || k === "key" || keep.has(k))) as SeriesPoint);
    return { points: ordered, series: seriesList.slice(0, 12), xDimension: x?.c ?? null, seriesDimension: s?.c ?? null, gaps, notDrawn };
  }
  return { points: ordered, series: seriesList, xDimension: x?.c ?? null, seriesDimension: s?.c ?? null, gaps, notDrawn };
}

export interface ScatterPoint { name: string; x: number; y: number; key: string }

export function scatterData(result: ResultSet, encoding: Encoding | undefined): { points: ScatterPoint[]; xColumn: ResultColumn | null; yColumn: ResultColumn | null; nameColumn: ResultColumn | null } {
  const measures = result.columns.filter((c) => c.kind === "measure");
  const dims = result.columns.filter((c) => c.kind === "dimension");
  const xCol = measures.find((m) => m.id === encoding?.x) ?? measures[0] ?? null;
  const yCol = measures.find((m) => m.id === encoding?.y?.[0] && m.id !== xCol?.id) ?? measures.find((m) => m.id !== xCol?.id) ?? null;
  const nameCol = dims.find((d) => d.id === encoding?.color) ?? dims[0] ?? null;
  const ix = result.columns.findIndex((c) => c.id === xCol?.id), iy = result.columns.findIndex((c) => c.id === yCol?.id), iname = result.columns.findIndex((c) => c.id === nameCol?.id);
  const points: ScatterPoint[] = [];
  if (result.empty) return { points, xColumn: xCol, yColumn: yCol, nameColumn: nameCol };
  for (const row of result.rows) {
    const x = ix >= 0 ? cellValue(row[ix]) : null, y = iy >= 0 ? cellValue(row[iy]) : null;
    if (x === null || y === null) continue;
    const name = iname >= 0 ? cellText(row[iname]) : "";
    points.push({ name, x, y, key: name });
  }
  return { points, xColumn: xCol, yColumn: yCol, nameColumn: nameCol };
}

export interface HeatCell { row: string; column: string; value: number | null; cell: Cell }
export interface HeatData { rows: string[]; columns: string[]; cells: HeatCell[]; measure: ResultColumn | null; rowDim: ResultColumn | null; colDim: ResultColumn | null; min: number; max: number }

export function heatData(result: ResultSet, encoding: Encoding | undefined, locale: "en" | "ar"): HeatData {
  const dims = result.columns.map((c, i) => ({ c, i })).filter(({ c }) => c.kind === "dimension");
  const measures = result.columns.map((c, i) => ({ c, i })).filter(({ c }) => c.kind === "measure");
  const rowDim = dims.find(({ c }) => c.id === encoding?.rows?.[0]) ?? dims[0] ?? null;
  const colDim = dims.find(({ c }) => c.id === encoding?.columns?.[0] && c.id !== rowDim?.c.id) ?? dims.find(({ c }) => c.id !== rowDim?.c.id) ?? null;
  const measure = measures.find(({ c }) => encoding?.y?.includes(c.id)) ?? measures[0] ?? null;
  const rows: string[] = [], columns: string[] = [], cells: HeatCell[] = [];
  let min = Infinity, max = -Infinity;
  if (!result.empty && rowDim && measure) {
    for (const row of result.rows) {
      const r = formatDimension(row[rowDim.i], rowDim.c, locale);
      const c = colDim ? formatDimension(row[colDim.i], colDim.c, locale) : "";
      if (!rows.includes(r)) rows.push(r);
      if (!columns.includes(c)) columns.push(c);
      const v = cellValue(row[measure.i]);
      if (v !== null) { min = Math.min(min, v); max = Math.max(max, v); }
      cells.push({ row: r, column: c, value: v, cell: row[measure.i] });
    }
  }
  if (rowDim?.c.dimension_kind === "time") rows.sort();
  if (colDim?.c.dimension_kind === "time") columns.sort();
  return { rows, columns, cells, measure: measure?.c ?? null, rowDim: rowDim?.c ?? null, colDim: colDim?.c ?? null, min: Number.isFinite(min) ? min : 0, max: Number.isFinite(max) ? max : 0 };
}

export function titleOf(v: VisualSpec, locale: "en" | "ar"): string {
  return v.title[locale] || v.title.en || "";
}
export function descriptionOf(v: VisualSpec, locale: "en" | "ar"): string {
  return v.description[locale] || v.description.en || "";
}
