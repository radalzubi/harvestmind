import assert from "node:assert/strict";
import { test } from "node:test";
import { CATALOGS, derive } from "../readiness";
import type { DataQualityReport, IntakeStatus } from "@/lib/api";

const status = (rows: Record<string, number>): IntakeStatus => ({
  tables: Object.fromEntries(Object.entries(rows).map(([t, n]) => [t, { description: t, row_count: n, loaded: n > 0 }])),
  any_data_loaded: Object.values(rows).some((n) => n > 0),
  all_tables_loaded: false,
});

const quality = (tables: Record<string, string[]>, score = 80): DataQualityReport => ({
  score, score_label: "Good", total_rows: 1000, errors: [], warnings: [],
  tables: Object.fromEntries(Object.entries(tables).map(([t, issues]) => [t, { row_count: 10, status: "ok", issues }])),
});

test("an empty workspace cannot plan and asks for the first required source only", () => {
  const r = derive(CATALOGS.commercial, status({}), null);
  assert.equal(r.canPlan, false);
  assert.equal(r.nextStep!.title, "Add your product list");
  assert.match(r.nextStep!.detail, /What you sell/);
  assert.equal(r.sources.every((s) => s.state === "missing"), true);
});

test("optional sources never block planning", () => {
  const r = derive(CATALOGS.commercial, status({ stg_fmcg_skus: 120, stg_fmcg_orders: 8000 }), null);
  assert.equal(r.canPlan, true);
  assert.equal(r.nextStep, null);
  assert.equal(r.sources.find((s) => s.table === "stg_fmcg_suppliers")!.required, false);
  assert.equal(r.sources.find((s) => s.table === "stg_fmcg_suppliers")!.state, "missing");
});

test("a missing required source outranks a quality problem", () => {
  const r = derive(
    CATALOGS.commercial,
    status({ stg_fmcg_skus: 120, stg_fmcg_purchase_orders: 40 }),
    quality({ stg_fmcg_purchase_orders: ["3 rows have invalid dates"] }),
  );
  assert.equal(r.canPlan, false);
  assert.equal(r.nextStep!.title, "Add your customer orders");
});

test("with everything required present, the next step is the quality problem", () => {
  const r = derive(
    CATALOGS.commercial,
    status({ stg_fmcg_skus: 120, stg_fmcg_orders: 8000, stg_fmcg_purchase_orders: 40 }),
    quality({ stg_fmcg_purchase_orders: ["3 rows have invalid dates", "1 row has no supplier"] }),
  );
  assert.equal(r.canPlan, true);
  assert.equal(r.nextStep!.title, "Fix 2 issues in your purchase orders");
  assert.equal(r.nextStep!.detail, "3 rows have invalid dates");
});

test("a source with no rows is missing, not a quality problem", () => {
  const r = derive(
    CATALOGS.commercial,
    status({ stg_fmcg_skus: 120, stg_fmcg_orders: 8000, stg_fmcg_inventory: 0 }),
    quality({ stg_fmcg_inventory: ["table is empty"] }),
  );
  const inventory = r.sources.find((s) => s.table === "stg_fmcg_inventory")!;
  assert.equal(inventory.state, "missing");
  assert.deepEqual(inventory.issues, [], "an absent source does not also shout about its contents");
});

test("the produce workspace has its own required set", () => {
  const r = derive(CATALOGS.produce, status({ stg_products: 40 }), null);
  assert.equal(r.canPlan, false);
  assert.equal(r.nextStep!.title, "Add your supplier deliveries");
  assert.equal(r.sources.filter((s) => s.required).length, 4);
  assert.equal(r.sources.find((s) => s.table === "stg_waste_adjustments")!.required, false);
});

test("no source in either catalog shows a database table name as its name", () => {
  for (const catalog of [CATALOGS.commercial, CATALOGS.produce]) {
    for (const s of catalog) {
      assert.ok(!/^stg_/.test(s.name), `${s.name} is a table name, not an operator's word`);
      assert.ok(s.why.length > 10, `${s.name} does not say why ZAAD wants it`);
    }
  }
});

test("row totals fall back to what the sources report when there is no quality report", () => {
  const r = derive(CATALOGS.commercial, status({ stg_fmcg_skus: 120, stg_fmcg_orders: 8000 }), null);
  assert.equal(r.totalRows, 8120);
  assert.equal(r.score, null);
});
