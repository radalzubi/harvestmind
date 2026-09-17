/**
 * Builder state ↔ query spec, URL state, cells and formatting.
 *
 * The rules the surface keeps: a null is a null with a reason and is shown as that reason, never
 * as 0; the browser formats values with the unit the server declared; filters live in the URL so
 * an analysis in progress can be sent to someone.
 */
import type { Cell, Filter, Grain, MetricDoc, NullCell, QuerySpec, RatioCell, ResultColumn, ResultSet, VisualType } from "./client";

export const REASON_LABEL: Record<string, { en: string; ar: string }> = {
  UNKNOWN: { en: "Unknown", ar: "غير معروف" }, NOT_MEASURED: { en: "Not measured", ar: "غير مقاس" }, NOT_APPLICABLE: { en: "Not applicable", ar: "لا ينطبق" },
  NO_DATA: { en: "No data", ar: "لا بيانات" }, BLOCKED_BY_DATA: { en: "Blocked by data", ar: "محجوب بالبيانات" }, NOT_IN_PLAN: { en: "Not in plan", ar: "ليس في الخطة" },
  INSUFFICIENT_COVERAGE: { en: "Insufficient coverage", ar: "تغطية غير كافية" },
};

export function reasonLabel(reason: string | null | undefined, locale: "en" | "ar" = "en"): string {
  return (reason && REASON_LABEL[reason]?.[locale]) || REASON_LABEL.UNKNOWN[locale];
}

export function isNull(cell: Cell): cell is NullCell {
  return typeof cell === "object" && cell !== null && (cell as NullCell).value === null;
}
export function cellValue(cell: Cell): number | null {
  if (cell === null || cell === undefined) return null;
  if (typeof cell === "number") return Number.isFinite(cell) ? cell : null;
  if (typeof cell === "string") return null;
  return typeof cell.value === "number" ? cell.value : null;
}
export function cellText(cell: Cell): string {
  return typeof cell === "string" ? cell : String(cell ?? "");
}
export function cellReason(cell: Cell): string | null {
  if (typeof cell === "object" && cell !== null) return (cell as NullCell | RatioCell).reason ?? null;
  return cell == null ? "UNKNOWN" : null;
}
export function cellWhy(cell: Cell): string | null {
  return typeof cell === "object" && cell !== null ? ((cell as NullCell).why ?? null) : null;
}

/** Format a measure cell with its unit, or say why there is none. Zero is a number. */
export function formatCell(cell: Cell, column: Pick<ResultColumn, "unit" | "currency">, locale: "en" | "ar" = "en", decimals?: number | null): string {
  const v = cellValue(cell);
  if (v === null) return reasonLabel(cellReason(cell), locale);
  const text = formatValue(v, column.unit, column.currency, decimals);
  const reason = cellReason(cell);
  return reason === "INSUFFICIENT_COVERAGE" ? `${text} *` : text;
}

export function formatValue(v: number, unit: string | undefined, currency?: string | null, decimals?: number | null): string {
  const d = decimals ?? undefined;
  if (unit === "ratio") return `${(v * 100).toFixed(d ?? 1)}%`;
  if (unit === "money") {
    const digits = d ?? (Math.abs(v) < 100 ? 2 : 0);
    return `${currency ? currency + " " : ""}${v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
  }
  if (unit === "days" || unit === "weeks") return `${v.toLocaleString("en-US", { minimumFractionDigits: d ?? 1, maximumFractionDigits: d ?? 1 })} ${unit === "days" ? "d" : "wk"}`;
  const digits = d ?? (Number.isInteger(v) ? 0 : 1);
  return v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function formatDimension(cell: Cell, column: ResultColumn, locale: "en" | "ar" = "en"): string {
  if (isNull(cell)) return reasonLabel(cell.reason, locale);
  const text = cellText(cell);
  if (column.dimension_kind === "time") return periodLabel(text, (column.level as Grain) ?? "week");
  return text;
}

export function periodLabel(period: string, grain: Grain): string {
  const iso = period.slice(0, 10);
  if (grain === "month") return iso.slice(0, 7);
  if (grain === "year") return iso.slice(0, 4);
  if (grain === "quarter") { const m = Number(iso.slice(5, 7)); return `${iso.slice(0, 4)} Q${Math.floor((m - 1) / 3) + 1}`; }
  if (grain === "week") return `w/c ${iso}`;
  return iso;
}

// ── builder state ──

export interface BuilderState {
  measures: string[];
  dimensions: string[];
  grain: Grain | null;
  start: string | null;
  end: string | null;
  last: number | null;
  unit: Grain | null;
  filters: Filter[];
  topN: number | null;
  topBy: string | null;
  others: boolean;
  comparison: boolean;
  sortField: string | null;
  sortDir: "asc" | "desc";
  visual: VisualType | null;
  limit: number;
}

export const EMPTY_BUILDER: BuilderState = {
  measures: [], dimensions: [], grain: null, start: null, end: null, last: null, unit: null, filters: [], topN: null, topBy: null, others: false,
  comparison: false, sortField: null, sortDir: "desc", visual: null, limit: 400,
};

export function toSpec(state: BuilderState, purpose: QuerySpec["purpose"] = "explore"): QuerySpec | null {
  if (!state.measures.length) return null;
  const spec: QuerySpec = { measures: state.measures.map((metric_id) => ({ metric_id })), dimensions: state.dimensions.map((dimension_id) => ({ dimension_id })), filters: state.filters, purpose, limit: state.limit };
  if (state.grain || state.start || state.end || state.last) {
    spec.time = { grain: state.grain ?? undefined };
    if (state.start || state.end) spec.time.range = { start: state.start, end: state.end };
    else if (state.last && state.unit) spec.time.range = { last: state.last, unit: state.unit };
  }
  const memberDims = state.dimensions.filter((d) => d !== "date");
  if (state.topN && memberDims.length) spec.top_n = { dimension_id: memberDims[0], n: state.topN, others: state.others, by: state.topBy ?? state.measures[0] };
  if (state.comparison && state.grain) spec.comparison = { kind: "period_over_period", lag: 1 };
  if (state.sortField) spec.sort = [{ field: state.sortField, dir: state.sortDir }];
  return spec;
}

export function fromSpec(spec: QuerySpec, visual: VisualType | null = null): BuilderState {
  const r = spec.time?.range ?? null;
  return {
    measures: spec.measures.map((m) => m.metric_id),
    dimensions: (spec.dimensions ?? []).map((d) => d.dimension_id).filter((d) => d !== "date"),
    grain: spec.time?.grain ?? null, start: r?.start ?? null, end: r?.end ?? null, last: r?.last ?? null, unit: r?.unit ?? null,
    filters: spec.filters ?? [], topN: spec.top_n?.n ?? null, topBy: spec.top_n?.by ?? null, others: Boolean(spec.top_n?.others),
    comparison: Boolean(spec.comparison), sortField: spec.sort?.[0]?.field ?? null, sortDir: spec.sort?.[0]?.dir ?? "desc", visual, limit: spec.limit ?? 400,
  };
}

// ── URL state: compact, bounded, safe ──

const ID = /^[A-Za-z0-9 _.:@+\-\/&()'#,]{1,120}$/;
const IDENT = /^[a-z][a-z0-9_]{0,63}$/;
const ISO = /^\d{4}-\d{2}-\d{2}$/;
const GRAINS: Grain[] = ["day", "week", "month", "quarter", "year"];
const VISUALS: VisualType[] = ["kpi", "table", "pivot", "line", "area", "bar", "hbar", "stacked_bar", "scatter", "heatmap"];
const OPS = ["in", "eq", "ne", "contains", "between", "gte", "lte", "is_null", "not_null"];

export function stateToParams(state: BuilderState): URLSearchParams {
  const p = new URLSearchParams();
  if (state.measures.length) p.set("m", state.measures.join(","));
  if (state.dimensions.length) p.set("d", state.dimensions.join(","));
  if (state.grain) p.set("g", state.grain);
  if (state.start) p.set("start", state.start);
  if (state.end) p.set("end", state.end);
  if (state.last && state.unit) p.set("last", `${state.last}${state.unit[0]}`);
  for (const f of state.filters) p.append("f", `${f.dimension_id}:${f.op}:${f.values.join("|")}`);
  if (state.topN) p.set("top", String(state.topN) + (state.others ? "+" : ""));
  if (state.topBy) p.set("by", state.topBy);
  if (state.comparison) p.set("cmp", "1");
  if (state.sortField) p.set("sort", `${state.sortField}:${state.sortDir}`);
  if (state.visual) p.set("v", state.visual);
  return p;
}

export function stateFromParams(params: { get(name: string): string | null; getAll(name: string): string[] }): BuilderState {
  const idents = (s: string | null) => (s ?? "").split(",").map((x) => x.trim()).filter((x) => IDENT.test(x));
  const grain = params.get("g");
  const last = params.get("last");
  const lastMatch = last ? last.match(/^(\d{1,3})([dwmqy])$/) : null;
  const unitOf: Record<string, Grain> = { d: "day", w: "week", m: "month", q: "quarter", y: "year" };
  const filters: Filter[] = [];
  for (const raw of params.getAll("f").slice(0, 12)) {
    const [dim, op, values] = raw.split(":");
    if (!IDENT.test(dim ?? "") || !OPS.includes(op ?? "")) continue;
    const vals = (values ?? "").split("|").map((v) => v.trim()).filter((v) => v && ID.test(v)).slice(0, 200);
    if ((op === "in" && !vals.length) || (["eq", "ne", "contains", "gte", "lte"].includes(op) && vals.length !== 1) || (op === "between" && vals.length !== 2)) continue;
    filters.push({ dimension_id: dim, op: op as Filter["op"], values: op === "is_null" || op === "not_null" ? [] : vals });
  }
  const top = params.get("top");
  const topMatch = top ? top.match(/^(\d{1,2})(\+?)$/) : null;
  const sort = params.get("sort");
  const sortMatch = sort ? sort.match(/^([a-z][a-z0-9_]{0,63}):(asc|desc)$/) : null;
  const v = params.get("v");
  const start = params.get("start"), end = params.get("end");
  const by = params.get("by");
  return {
    ...EMPTY_BUILDER,
    measures: idents(params.get("m")).slice(0, 6), dimensions: idents(params.get("d")).slice(0, 3),
    grain: grain && (GRAINS as string[]).includes(grain) ? (grain as Grain) : null,
    start: start && ISO.test(start) ? start : null, end: end && ISO.test(end) ? end : null,
    last: lastMatch ? Number(lastMatch[1]) : null, unit: lastMatch ? unitOf[lastMatch[2]] : null,
    filters, topN: topMatch ? Number(topMatch[1]) : null, others: Boolean(topMatch?.[2]), topBy: by && IDENT.test(by) ? by : null,
    comparison: params.get("cmp") === "1", sortField: sortMatch ? sortMatch[1] : null, sortDir: sortMatch ? (sortMatch[2] as "asc" | "desc") : "desc",
    visual: v && (VISUALS as string[]).includes(v) ? (v as VisualType) : null,
  };
}

// ── cross-filtering ──

/** A member event from one visual becomes an `in` filter on the receiving state; the same member again clears it. */
export function applyCrossFilter(filters: Filter[], dimension_id: string, member: string): Filter[] {
  if (!IDENT.test(dimension_id) || !ID.test(member)) return filters;
  const existing = filters.find((f) => f.dimension_id === dimension_id && f.op === "in");
  if (existing && existing.values.length === 1 && existing.values[0] === member) return filters.filter((f) => f !== existing);
  return [...filters.filter((f) => f.dimension_id !== dimension_id), { dimension_id, op: "in", values: [member] }];
}

/** Dashboard-level filters applied to a tile's query: only dimensions the tile's metrics allow. */
export function mergeFilters(query: QuerySpec, shared: Filter[], allowed: (metricIds: string[]) => string[]): QuerySpec {
  const allow = new Set(allowed(query.measures.map((m) => m.metric_id)));
  const applicable = shared.filter((f) => allow.has(f.dimension_id));
  if (!applicable.length) return query;
  const own = (query.filters ?? []).filter((f) => !applicable.some((s) => s.dimension_id === f.dimension_id));
  return { ...query, filters: [...own, ...applicable] };
}

/** Whether a total may be shown for a measure column: additive measures or a server-computed overall figure. */
export function totalAllowed(column: ResultColumn, coverage: ResultSet["coverage"]): boolean {
  if (column.kind !== "measure" || !column.metric_id) return false;
  const total = coverage[column.metric_id]?.total;
  return total !== undefined && cellValue(total) !== null;
}

export function metricLabel(m: MetricDoc, locale: "en" | "ar"): string {
  return m.display_name[locale] ?? m.display_name.en;
}

/** The dimensions every named metric allows: the intersection, from the model document. */
export function allowedDimensionsFor(metrics: MetricDoc[], ids: string[]): string[] {
  const sets = ids.map((id) => metrics.find((m) => m.metric_id === id)).map((m) => new Set(m?.allowed_dimensions ?? []));
  if (!sets.length || sets.some((s) => !s.size)) return [];
  return [...sets[0]].filter((d) => sets.every((s) => s.has(d)));
}

export const TIME_DIMENSION = "date";
