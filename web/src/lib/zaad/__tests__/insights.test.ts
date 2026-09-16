import { test } from "node:test";
import assert from "node:assert/strict";
import {
  EMPTY, TABS, activeFilters, filtersFromParams, filtersToQuery, linksFor, periodLabel, planSentence, reasonLabel,
  scopeSentence, shown,
} from "../insights";

const params = (s: string) => new URLSearchParams(s);

test("filters come from the URL and go back to it; only what is set travels", () => {
  const f = filtersFromParams(params("bucket=month&sku=DEMO-0010&customer=DEMO-CUST-GROW&start=2026-01-01"));
  assert.equal(f.bucket, "month");
  assert.equal(f.sku, "DEMO-0010");
  assert.equal(f.customer, "DEMO-CUST-GROW");
  assert.equal(f.start, "2026-01-01");
  assert.equal(f.end, null);
  assert.equal(filtersToQuery(f), "bucket=month&start=2026-01-01&sku=DEMO-0010&customer=DEMO-CUST-GROW");
  assert.deepEqual(activeFilters(f), [{ key: "sku", value: "DEMO-0010" }, { key: "customer", value: "DEMO-CUST-GROW" }]);
});

test("a malformed URL is not guessed at: bad buckets fall back to week, bad dates and ids are dropped", () => {
  const f = filtersFromParams(params("bucket=year&start=yesterday&sku=%3Cscript%3E&location=DEMO-BR-AQABA"));
  assert.equal(f.bucket, "week");
  assert.equal(f.start, null);
  assert.equal(f.sku, null);
  assert.equal(f.location, "DEMO-BR-AQABA");
});

test("a missing number is shown as its reason, never as zero; zero is a number", () => {
  assert.equal(shown(null, (v) => String(v), "NOT_MEASURED"), "Not measured");
  assert.equal(shown(undefined, (v) => String(v), "NOT_IN_PLAN"), "Not in plan");
  assert.equal(shown(null, (v) => String(v)), "Unknown");
  assert.equal(shown(0, (v) => `${v} units`), "0 units");
  assert.equal(reasonLabel("BLOCKED_BY_DATA"), "Blocked by data");
  assert.equal(reasonLabel("something else"), "Unknown");
});

test("the plan sentence says which plan, and that the data moved afterward when it did", () => {
  const fmt = (iso: string) => iso.slice(0, 10);
  assert.match(planSentence(null, fmt), /No completed ZAAD plan yet/);
  assert.equal(planSentence({ available: true, finished_at: "2026-09-15T10:32:00", products: 5 }, fmt), "Latest ZAAD plan: 2026-09-15 · 5 products.");
  assert.equal(planSentence({ available: true, finished_at: "2026-09-15T10:32:00", products: 1, stale: true }, fmt),
    "Latest ZAAD plan: 2026-09-15 · 1 product. Workspace data changed afterward.");
});

test("the scope sentence discloses range, bucket, filters and rows", () => {
  const p = { source_data: ["stg_fmcg_orders"], metric: "m", numerator: "n", denominator: "d", date_range: { start: "2026-01-01", end: null },
    bucket: "week", filters: { customer: "DEMO-CUST-GROW" }, coverage: {}, last_updated: null, plan: null };
  assert.equal(scopeSentence(p, 21011), "2026-01-01 → the latest row, by week · filtered by customer = DEMO-CUST-GROW · 21,011 rows");
  assert.equal(scopeSentence({ ...p, date_range: { start: null, end: null }, filters: {} }), "the whole history, by week · no filters");
});

test("every chart leads somewhere, carrying the filters", () => {
  assert.equal(linksFor.inventory({ ...EMPTY, location: "DEMO-BR-AQABA" }, "DEMO-0010"), "/inventory?sku=DEMO-0010&location=DEMO-BR-AQABA");
  assert.equal(linksFor.purchaseOrders("DEMO-PO-00364"), "/orders?tab=imported&postate=open&po=DEMO-PO-00364");
  assert.equal(linksFor.data("customer_orders", "customer_id", "DEMO-CUST-GROW"), "/data?dataset=customer_orders&fcol=customer_id&fval=DEMO-CUST-GROW");
  assert.equal(linksFor.decision("po:DEMO-PO-00364"), "/decisions?decision=po%3ADEMO-PO-00364");
  assert.equal(linksFor.insights("demand", { sku: "DEMO-0010" }), "/insights?bucket=week&sku=DEMO-0010&tab=demand");
});

test("period labels keep ISO digits so they read the same in Arabic and English", () => {
  assert.equal(periodLabel("2026-08-10T00:00:00", "week"), "w/c 2026-08-10");
  assert.equal(periodLabel("2026-08-01", "month"), "2026-08");
  assert.equal(periodLabel("2026-08-10", "day"), "2026-08-10");
});

test("the tabs are the six the product promises, in order", () => {
  assert.deepEqual(TABS, ["overview", "demand", "inventory", "supply", "service", "decisions"]);
});

test("a decision opens the demand, inventory and supplier views behind it, through the request's maps", async () => {
  const { insightsLinksFor } = await import("../insights");
  const request = { sources: [{ id: "SRC-1", sku: "DEMO-0010", supplier: "DEMO-SUP-03" }], pipeline: [{ id: "DEMO-PO-00676", source: "SRC-1" }] };
  const po = insightsLinksFor({ target: { type: "po", id: "DEMO-PO-00676" } }, request);
  assert.equal(po.demand, "/insights?bucket=week&sku=DEMO-0010&tab=demand");
  assert.equal(po.inventory, "/insights?bucket=week&sku=DEMO-0010&tab=inventory");
  assert.equal(po.supplier, "/insights?bucket=week&supplier=DEMO-SUP-03&tab=supply");
  assert.equal(po.value, "/insights?bucket=week&tab=decisions");
  const unknown = insightsLinksFor({ target: { type: "po", id: "NOPE" } }, request);
  assert.equal(unknown.demand, null, "no product is claimed when the request does not name one");
  assert.equal(insightsLinksFor({ target: { type: "supplier", id: "DEMO-SUP-01" } }, null).supplier, "/insights?bucket=week&supplier=DEMO-SUP-01&tab=supply");
});

test("the Arabic copy for Insights mirrors the English keys, and never translates identifiers", async () => {
  const { en } = await import("../../i18n/en");
  const { ar } = await import("../../i18n/ar");
  const keys = (o: object): string[] => Object.entries(o).flatMap(([k, v]) => (v && typeof v === "object" ? keys(v as object).map((s) => `${k}.${s}`) : [k]));
  assert.deepEqual(keys(ar.workspace.insights), keys(en.workspace.insights));
  assert.equal(ar.workspace.nav.insights.length > 0, true);
  for (const tab of ["overview", "demand", "inventory", "supply", "service", "decisions", "perishability"] as const) {
    assert.notEqual(ar.workspace.insights.tabs[tab], en.workspace.insights.tabs[tab]);
  }
  assert.equal(periodLabel("2026-08-03", "week"), "w/c 2026-08-03", "period labels stay ISO in both languages");
});
