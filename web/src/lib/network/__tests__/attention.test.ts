import assert from "node:assert/strict";
import { test } from "node:test";
import { attentionAreas, describe, statusLine } from "../attention";
import { ILLUSTRATIVE_NETWORK } from "../fixtures";
import { buildIndex, searchModel } from "../graph";
import { groupCustomers } from "../groups";
import type { NetworkModel } from "../model";

const index = buildIndex(ILLUSTRATIVE_NETWORK);

test("the fixture reads as one problem: the Red Sea lane, led by the most exposed item", () => {
  const areas = attentionAreas(ILLUSTRATIVE_NETWORK, index);
  const attention = areas.filter((a) => a.level === "attention");
  assert.equal(attention.length, 1);
  assert.equal(attention[0].lead.id, "lane_yantian_aqaba");
  assert.ok(attention[0].members.some((m) => m.id === "sup_c"));
  assert.ok(attention[0].recommendation);
  const s = statusLine(areas);
  assert.equal(s.headline, "1 area needs attention");
  assert.equal(s.tone, "attention");
});

test("a calm network says so", () => {
  const calm: NetworkModel = { ...ILLUSTRATIVE_NETWORK, nodes: ILLUSTRATIVE_NETWORK.nodes.map((n) => ({ ...n, risk: { ...n.risk, score: 0.1, level: "low" } })), edges: ILLUSTRATIVE_NETWORK.edges.map((e) => ({ ...e, risk: { ...e.risk, score: 0.1, level: "low" } })) };
  const s = statusLine(attentionAreas(calm, buildIndex(calm)));
  assert.equal(s.headline, "Everything looks normal");
  assert.equal(s.tone, "ok");
});

test("summaries are plain sentences built from the data", () => {
  const lane = describe({ type: "edge", id: "lane_yantian_aqaba" }, ILLUSTRATIVE_NETWORK, index);
  assert.match(lane, /Shenzhen \(Yantian\) to Port of Aqaba is disrupted/);
  assert.match(lane, /Transit is taking 34 days against a usual 28/);
  assert.match(lane, /One shipment is delayed/);
  assert.match(lane, /approved as an alternative/);
  const sup = describe({ type: "node", id: "sup_c" }, ILLUSTRATIVE_NETWORK, index);
  assert.match(sup, /Supplier C is delivering less reliably than usual/);
  assert.match(sup, /2 open orders and 2 SKUs depend on this supplier/);
  assert.match(sup, /PO-7702 is already late/);
  assert.match(sup, /No alternative supplier is approved/);
  const dc = describe({ type: "node", id: "dc_amman" }, ILLUSTRATIVE_NETWORK, index);
  assert.match(dc, /holds 61,400 units/);
  assert.match(dc, /Nappies M 44s runs short week 5/);
  for (const t of [lane, sup, dc]) for (const banned of ["LEAN", "PROTECT", "ALLOCATE", "CVaR", "p_disruptive", "undefined", "null", "NaN"]) assert.ok(!t.includes(banned), `${banned} in "${t}"`);
});

test("search finds purchase orders and shipment references", () => {
  assert.equal(searchModel(ILLUSTRATIVE_NETWORK, "PO 7702")[0].id, "sup_c");
  assert.equal(searchModel(ILLUSTRATIVE_NETWORK, "po-7731")[0].id, "sup_a");
  assert.equal(searchModel(ILLUSTRATIVE_NETWORK, "MSKU")[0].id, "lane_yantian_aqaba");
});

test("many customers behind one site collapse into a group until opened", () => {
  const customers = Array.from({ length: 6 }, (_, i) => ({ ...ILLUSTRATIVE_NETWORK.nodes.find((n) => n.id === "cust_north")!, id: `c${i}`, name: `Customer ${i}` }));
  const edges = customers.map((c) => ({ ...ILLUSTRATIVE_NETWORK.edges.find((e) => e.id === "lane_north_cust")!, id: `e_${c.id}`, to: c.id }));
  const big: NetworkModel = { ...ILLUSTRATIVE_NETWORK, nodes: [...ILLUSTRATIVE_NETWORK.nodes, ...customers], edges: [...ILLUSTRATIVE_NETWORK.edges, ...edges] };
  const collapsed = groupCustomers(big, new Set());
  assert.equal(collapsed.groups.length, 1);
  assert.equal(collapsed.groups[0].feederId, "br_north");
  assert.ok(collapsed.model.nodes.some((n) => n.id === "group:br_north" && n.subtitle === "7 customers"));
  assert.ok(!collapsed.model.nodes.some((n) => n.id === "c3"));
  assert.ok(!collapsed.model.edges.some((e) => e.to === "c3"));
  const opened = groupCustomers(big, new Set(["group:br_north"]));
  assert.ok(opened.model.nodes.some((n) => n.id === "c3"));
  assert.ok(!opened.model.nodes.some((n) => n.id === "group:br_north"));
  // the small fixture is never grouped
  assert.equal(groupCustomers(ILLUSTRATIVE_NETWORK, new Set()).groups.length, 0);
});
