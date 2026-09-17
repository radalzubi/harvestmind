/**
 * The analytics client logic without a browser: builder state ↔ spec ↔ URL, honest cells,
 * visual mapping, totals gating, cross-filtering and drill-through links.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import type { ResultSet } from "../client";
import { EMPTY_BUILDER, applyCrossFilter, cellValue, formatCell, formatDimension, fromSpec, mergeFilters, periodLabel, reasonLabel, stateFromParams, stateToParams, toSpec, totalAllowed } from "../spec";
import { allowedVisuals, chartData, heatData, recommendVisual, scatterData, shapeOf } from "../visual";
import { drillThrough, recordsBehind } from "../links";

const result = (over: Partial<ResultSet> = {}): ResultSet => ({
  query_id: "q_1", semantic_model_version: "2026.09", dataset_version: { dataset_version_id: "dv_1", last_updated: null, data_cutoff: "2026-09-14" }, generated_at: "2026-09-16T00:00:00Z",
  columns: [
    { id: "date", kind: "dimension", label: { en: "Date", ar: "التاريخ" }, level: "month", dimension_kind: "time" },
    { id: "supplier", kind: "dimension", label: { en: "Supplier", ar: "المورد" }, dimension_kind: "member" },
    { id: "supplier_fill_rate", kind: "measure", metric_id: "supplier_fill_rate", label: { en: "Supplier fill rate", ar: "نسبة" }, unit: "ratio", additive: false, aggregation_rule: "ratio_of_sums", evidence_class: "OBSERVED_FACT" },
  ],
  rows: [
    ["2026-01-01", "S1", { value: 0.95, numerator: 95, denominator: 100 }],
    ["2026-02-01", "S1", { value: null, reason: "BLOCKED_BY_DATA", why: "no promised dates" }],
    ["2026-01-01", "S2", { value: 0.8, numerator: 80, denominator: 100 }],
  ],
  empty: false,
  coverage: { supplier_fill_rate: { measure: "matched orders", rows: 3, measured_share: null, insufficient: false, thin_sample: false, total: { value: 0.875, numerator: 175, denominator: 200 } } },
  provenance: { definitions: [], source_entities: [], source_data: [], fact: "matched_purchase_order", filters: [{ dimension_id: "supplier", label: { en: "Supplier" }, op: "eq", values: ["S1"] }], blocked: {}, time: { grain: "month", anchor: "po_date", start: null, end: null }, date_range: { start: null, end: null }, bucket: "month", last_updated: null, data_cutoff: null, dataset_version: "dv_1", plan: null, metric: "", numerator: "", denominator: "", coverage: {}, notes: [], engine: "duckdb", scope_filtered: [] },
  bounds: { truncated: false, limit_applied: 400, top_n_applied: null, rows: 3 }, timing: { planned_ms: 1, executed_ms: 2, cache: "miss" },
  spec: { measures: [{ metric_id: "supplier_fill_rate" }], dimensions: [{ dimension_id: "supplier" }], time: { grain: "month" } }, spec_hash: "abc",
  ...over,
});

test("a null is shown as its reason, never as zero; zero is a number", () => {
  assert.equal(formatCell({ value: null, reason: "NOT_MEASURED", why: "" }, { unit: "units" }), "Not measured");
  assert.equal(formatCell({ value: null, reason: "NOT_MEASURED", why: "" }, { unit: "units" }, "ar"), "غير مقاس");
  assert.equal(formatCell(0, { unit: "units" }), "0");
  assert.equal(formatCell({ value: 0.123, reason: "INSUFFICIENT_COVERAGE", why: "" }, { unit: "ratio" }), "12.3% *");
  assert.equal(formatCell(1234.5, { unit: "money", currency: "JOD" }), "JOD 1,235");
  assert.equal(formatCell(3.456, { unit: "weeks" }), "3.5 wk");
  assert.equal(cellValue(null), null);
  assert.equal(cellValue("S1"), null);
  assert.equal(reasonLabel("nonsense"), "Unknown");
  assert.equal(formatDimension("2026-03-01", { id: "date", kind: "dimension", label: {}, dimension_kind: "time", level: "quarter" }), "2026 Q1");
  assert.equal(periodLabel("2026-03-09", "week"), "w/c 2026-03-09");
});

test("builder state round-trips through the spec and the URL, dropping anything malformed", () => {
  const state = { ...EMPTY_BUILDER, measures: ["ordered_units", "shipped_units"], dimensions: ["category"], grain: "month" as const, last: 12, unit: "month" as const,
                  filters: [{ dimension_id: "supplier", op: "in" as const, values: ["S1", "S2"] }], topN: 5, topBy: "ordered_units", others: true, comparison: true, sortField: "ordered_units", sortDir: "desc" as const, visual: "stacked_bar" as const };
  const spec = toSpec(state)!;
  assert.deepEqual(spec.measures, [{ metric_id: "ordered_units" }, { metric_id: "shipped_units" }]);
  assert.deepEqual(spec.time, { grain: "month", range: { last: 12, unit: "month" } });
  assert.deepEqual(spec.top_n, { dimension_id: "category", n: 5, others: true, by: "ordered_units" });
  assert.deepEqual(spec.comparison, { kind: "period_over_period", lag: 1 });
  const back = fromSpec(spec, "stacked_bar");
  assert.deepEqual(back, state);
  const params = stateToParams(state);
  assert.equal(params.get("m"), "ordered_units,shipped_units");
  assert.equal(params.get("last"), "12m");
  assert.equal(params.get("top"), "5+");
  const again = stateFromParams(params);
  assert.deepEqual(again, state);
  const bad = stateFromParams(new URLSearchParams("m=sum(x),ordered_units&d=sku)&g=decade&f=sku:raw:1&f=category:eq:Bev&top=999&v=treemap&start=yesterday"));
  assert.deepEqual(bad.measures, ["ordered_units"]);
  assert.deepEqual(bad.dimensions, []);
  assert.equal(bad.grain, null);
  assert.deepEqual(bad.filters, [{ dimension_id: "category", op: "eq", values: ["Bev"] }]);
  assert.equal(bad.topN, null);
  assert.equal(bad.visual, null);
  assert.equal(bad.start, null);
  assert.equal(toSpec(EMPTY_BUILDER), null);
});

test("cross-filters are governed member events: toggle, replace, refuse junk; shared filters apply only where allowed", () => {
  let f = applyCrossFilter([], "supplier", "S1");
  assert.deepEqual(f, [{ dimension_id: "supplier", op: "in", values: ["S1"] }]);
  f = applyCrossFilter(f, "supplier", "S2");
  assert.deepEqual(f, [{ dimension_id: "supplier", op: "in", values: ["S2"] }]);
  f = applyCrossFilter(f, "supplier", "S2");
  assert.deepEqual(f, []);
  assert.deepEqual(applyCrossFilter([], "sku;drop", "x"), []);
  assert.deepEqual(applyCrossFilter([], "sku", "x=1"), []);
  const allowed = (ids: string[]) => (ids.includes("supplier_fill_rate") ? ["supplier", "sku", "date"] : ["category", "customer"]);
  const q = mergeFilters({ measures: [{ metric_id: "supplier_fill_rate" }], filters: [{ dimension_id: "supplier", op: "eq", values: ["S9"] }] },
                         [{ dimension_id: "category", op: "in", values: ["Bev"] }, { dimension_id: "supplier", op: "in", values: ["S1"] }], allowed);
  assert.deepEqual(q.filters, [{ dimension_id: "supplier", op: "in", values: ["S1"] }], "the shared supplier filter replaces the tile's own; category does not apply");
  const untouched = mergeFilters({ measures: [{ metric_id: "ordered_units" }] }, [{ dimension_id: "supplier", op: "in", values: ["S1"] }], (ids) => (ids[0] === "ordered_units" ? ["category"] : []));
  assert.equal(untouched.filters, undefined);
});

test("visual mapping: shape, allowed types, recommendation, series with gaps, scatter, heatmap", () => {
  const r = result();
  assert.equal(shapeOf(r), "trend_series");
  assert.equal(recommendVisual(r), "line", "a ratio over members and time is lines, never stacked");
  assert.ok(allowedVisuals(r).includes("heatmap") && !allowedVisuals(r).includes("kpi"));
  const data = chartData(r, undefined, "en");
  assert.deepEqual(data.series.map((s) => s.name), ["S1", "S2"]);
  assert.equal(data.points.length, 2);
  assert.equal(data.points[1]["supplier_fill_rate::S1"], null, "a blocked cell is a gap");
  assert.equal(data.gaps[0].reason, "BLOCKED_BY_DATA");
  const mixed = result({ columns: [r.columns[0], r.columns[2], { ...r.columns[2], id: "matched_orders", metric_id: "matched_orders", unit: "orders", additive: true, label: { en: "Measured orders", ar: "" } }],
                         rows: [["2026-01-01", { value: 0.9 }, 120]], spec: { measures: [{ metric_id: "supplier_fill_rate" }, { metric_id: "matched_orders" }], time: { grain: "month" } } });
  const one = chartData(mixed, undefined, "en");
  assert.deepEqual(one.series.map((x) => x.key), ["supplier_fill_rate"], "a count is never drawn on a ratio axis");
  assert.deepEqual(one.notDrawn.map((x) => x.id), ["matched_orders"]);
  const kpi = result({ columns: [r.columns[2]], rows: [[{ value: 0.9 }]], spec: { measures: [{ metric_id: "supplier_fill_rate" }] } });
  assert.equal(shapeOf(kpi), "kpi");
  assert.equal(recommendVisual(kpi), "kpi");
  const ranking = result({ columns: [r.columns[1], r.columns[2]], rows: [["S1", { value: 0.9 }], ["S2", { value: 0.8 }]], spec: { measures: [{ metric_id: "supplier_fill_rate" }], dimensions: [{ dimension_id: "supplier" }] } });
  assert.equal(recommendVisual(ranking), "hbar");
  const two = result({ columns: [r.columns[1], r.columns[2], { ...r.columns[2], id: "matched_orders", metric_id: "matched_orders", unit: "orders", additive: true }], rows: [["S1", { value: 0.9 }, 10], ["S2", { value: 0.8 }, 3]],
                       spec: { measures: [{ metric_id: "supplier_fill_rate" }, { metric_id: "matched_orders" }], dimensions: [{ dimension_id: "supplier" }] } });
  assert.equal(shapeOf(two), "relationship");
  const sc = scatterData(two, undefined);
  assert.equal(sc.points.length, 2);
  assert.equal(sc.points[0].name, "S1");
  const heat = heatData(r, undefined, "en");
  assert.deepEqual(heat.rows, ["2026-01", "2026-02"]);
  assert.deepEqual(heat.columns, ["S1", "S2"]);
  assert.equal(heat.cells.find((c) => c.row === "2026-02" && c.column === "S1")?.value, null);
});

test("totals are shown only where the server computed one", () => {
  const r = result();
  assert.equal(totalAllowed(r.columns[2], r.coverage), true);
  const noTotal = result({ coverage: { supplier_fill_rate: { measure: "", rows: 3, measured_share: null, insufficient: false, thin_sample: false, total: { value: null, reason: "NOT_APPLICABLE", why: "" } } } });
  assert.equal(totalAllowed(noTotal.columns[2], noTotal.coverage), false);
  assert.equal(totalAllowed(r.columns[1], r.coverage), false);
});

test("drill-through carries the member and nothing invented; records behind a result go to the explorer", () => {
  assert.deepEqual(drillThrough("sku", "DEMO-0001"), { href: "/inventory?sku=DEMO-0001", label: "Inventory" });
  assert.deepEqual(drillThrough("supplier", "DEMO-SUP-02"), { href: "/diagnostics/supplier/DEMO-SUP-02", label: "Supplier" });
  assert.equal(drillThrough("supplier", "<script>"), null);
  assert.equal(drillThrough("date", "2026-01-01"), null);
  const behind = recordsBehind(result());
  assert.equal(behind?.href, "/data?dataset=purchase_orders&fcol=supplier_id&fval=S1");
  assert.equal(recordsBehind(result({ provenance: { ...result().provenance, fact: "decision" } }))?.href, "/decisions");
});
