import assert from "node:assert/strict";
import { test } from "node:test";
import { buildWorkspaceModel, type StateResponse } from "../adapters/workspace";

const supplierState = (p = 0.1, dominant = "NORMAL") => ({ dominant, p_disruptive: p, stress: p, probabilities: { NORMAL: 1 - p, SUPPLIER_DEGRADED: p }, reasons: ["r1", "r2"], change_points: [] });

const FULL: StateResponse = {
  as_of: "2026-09-07", mode: "BALANCED",
  portfolio: { probabilities: { NORMAL: 0.7, WATCH: 0.3 }, dominant: "NORMAL", stress: 0.3, reasons: ["stress reason"], data_quality: 0.8 },
  sku: { A: { ...supplierState(0.4, "SUPPLIER_DEGRADED") }, B: { ...supplierState() }, C: { ...supplierState() } },
  supplier: { s1: supplierState(0.35, "SUPPLIER_DEGRADED"), s2: supplierState(0.05) },
  outlooks: { aqaba: { risk: 0.6, quality: 0.5, reasons: ["Bab el-Mandeb transits low"], missing: ["port:AQABA"], contrib: { chokepoint: 0.4 } } },
  network: {
    products: ["A", "B", "C"], supplier_of: { A: "s1", B: "s1", C: "s2" }, route_of: { s1: "aqaba" }, lead_of: { s1: 2, s2: 3 },
    opening: { A: 10, B: 0, C: 4 }, pipeline: { A: 7 }, unit_cost: { A: 1.5, B: 2, C: 0.75 },
    suppliers: { s1: { name: "Alpha", route: "aqaba", origin_iso3: "TUR", capacity_per_week: 900 }, s2: { name: null, route: null, origin_iso3: null, capacity_per_week: null } },
  },
};
const me = { operator_id: "op", name: "Acme", sector: "commercial" as const, region: "JO", created_at: "", upload_count: 1 };
const status = { tables: { stg_fmcg_skus: 3, stg_fmcg_inventory: 3, stg_fmcg_purchase_orders: 10 } };

test("populated workspace: suppliers, lane, port and warehouse are linked and provenance is workspace", () => {
  const m = buildWorkspaceModel({ state: FULL, status, me, supply: null });
  assert.equal(m.provenance, "workspace");
  const ids = new Set(m.nodes.map((n) => n.id));
  assert.ok(ids.has("dc_workspace") && ids.has("sup_s1") && ids.has("sup_s2") && ids.has("port_aqaba"));
  const s1 = m.nodes.find((n) => n.id === "sup_s1")!;
  assert.deepEqual(s1.skus, ["A", "B"]);
  assert.equal(s1.name, "Alpha");
  assert.equal(s1.geo?.precision, "approximate");          // placed by origin country
  assert.equal(s1.metrics.leadDays?.mean, 14);              // weeks -> days
  assert.equal(s1.state, "PROTECT");                        // SUPPLIER_DEGRADED
  const lane = m.edges.find((e) => e.id === "lane_s1_aqaba")!;
  assert.equal(lane.kind, "ocean");
  assert.equal(lane.to, "port_aqaba");
  assert.ok(lane.path && lane.path.length > 3);
  assert.equal(lane.state, "ALLOCATE");                     // outlook risk 0.6
  assert.ok(lane.missing?.some((x) => x.includes("port:AQABA")));
  const dc = m.nodes.find((n) => n.id === "dc_workspace")!;
  assert.equal(dc.metrics.onHandUnits, 14);
  assert.equal(dc.metrics.inboundUnits, 7);
  assert.equal(dc.metrics.onHandValue, 10 * 1.5 + 4 * 0.75);
  assert.equal(dc.geo?.precision, "approximate");
  // nothing illustrative leaks in
  assert.equal(m.shipments.length, 0);
  assert.equal(m.recommendations.length, 0);
  assert.ok(!m.notes.some((n) => /illustrative/i.test(n)));
});

test("old server without the network block still renders and says what is missing", () => {
  const { network: _drop, ...older } = FULL;
  void _drop;
  const m = buildWorkspaceModel({ state: older, status: null, me: null, supply: null });
  assert.equal(m.nodes.filter((n) => n.kind === "supplier").length, 2);
  const s1 = m.nodes.find((n) => n.id === "sup_s1")!;
  assert.deepEqual(s1.skus, []);
  assert.ok(s1.missing?.some((x) => /SKU assignment/.test(x)));
  assert.ok(m.notes.some((n) => /no `network` block/.test(n)));
  const dc = m.nodes.find((n) => n.id === "dc_workspace")!;
  assert.equal(dc.metrics.onHandUnits, null);
  assert.equal(dc.geo, null);                               // no region known
  assert.ok(dc.missing?.some((x) => /No coordinates/.test(x)));
  // a lane with an outlook but no tagged supplier still appears, honestly labelled
  assert.ok(m.edges.some((e) => e.id === "lane_aqaba"));
});

test("no route tags: suppliers attach to the warehouse as relationships, not lanes", () => {
  const state: StateResponse = { ...FULL, outlooks: {}, network: { ...FULL.network, route_of: {}, suppliers: { s1: { name: "Alpha" } } } };
  const m = buildWorkspaceModel({ state, status, me, supply: null });
  assert.ok(m.edges.every((e) => e.kind === "supply"));
  assert.ok(m.edges.every((e) => e.path === null));
  assert.ok(!m.nodes.some((n) => n.kind === "port"));
  const s1 = m.nodes.find((n) => n.id === "sup_s1")!;
  assert.ok(s1.missing?.some((x) => /No route tag/.test(x)));
});

test("incomplete supplier master and partial network block do not throw", () => {
  const state: StateResponse = { mode: "EFFICIENCY", supplier: { s9: supplierState() }, network: { supplier_of: { Z: "s9" } } };
  const m = buildWorkspaceModel({ state, status: { tables: {} }, me: null, supply: null });
  const s9 = m.nodes.find((n) => n.id === "sup_s9")!;
  assert.equal(s9.name, "s9");
  assert.deepEqual(s9.skus, ["Z"]);
  assert.equal(s9.metrics.leadDays, undefined);
  assert.equal(m.nodes.find((n) => n.id === "dc_workspace")!.metrics.onHandUnits, null);
});

test("empty workspace is a single warehouse with no lanes", () => {
  const m = buildWorkspaceModel({ state: {}, status: null, me: null, supply: null });
  assert.equal(m.nodes.length, 1);
  assert.equal(m.nodes[0].kind, "dc");
  assert.equal(m.edges.length, 0);
});

test("calibrated fill enriches a supplier only when the id matches", () => {
  const supply = { suppliers: [{ supplier_id: "s2", supplier_name: "Beta", n_deliveries: 30, posterior_mean: 0.9, downside: 0.7, spread: 0.1, risk_level: "Medium" }] };
  const m = buildWorkspaceModel({ state: FULL, status, me, supply });
  assert.equal(m.nodes.find((n) => n.id === "sup_s2")!.metrics.fill?.mean, 0.9);
  assert.equal(m.nodes.find((n) => n.id === "sup_s2")!.name, "Beta");
  assert.equal(m.nodes.find((n) => n.id === "sup_s1")!.metrics.fill, undefined);
});
