/**
 * Readability at scale: the twin must still be worth looking at with eight, thirty and a hundred
 * suppliers, and with names long enough to break a fixed-width node.
 *
 * The property is not "it renders". It is that a person opening the page can *read* it: nodes do
 * not overlap, the canvas does not grow until the fit-to-view zoom makes every label illegible, and
 * a crowd that is collapsed still carries the risk of its worst member so nothing is hidden.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { groupCustomers, GROUP_THRESHOLD, SUPPLIER_GROUP_THRESHOLD, isGroupId } from "../groups";
import { COLUMN_GAP, ROW_GAP, layoutNodes } from "../layout";
import { buildIndex } from "../graph";
import { riskLevel, type NetworkEdge, type NetworkModel, type NetworkNode } from "../model";

/** The rendered node box, from `network.css`: 176px wide and about 66px tall with its footer. */
const NODE_W = 176;
const NODE_H = 66;
/** Below this the 12.5px node name renders under 8px, which nobody reads. */
const LEGIBLE_ZOOM = 0.55;
const CANVAS = { w: 1200, h: 700 };

function node(id: string, kind: NetworkNode["kind"], name: string, score = 0): NetworkNode {
  return {
    id, kind, name, geo: null, importance: 0.7, state: "LEAN",
    risk: { level: riskLevel(score), score, reasons: score ? [`${name} is short`] : [], evidence: [] },
    metrics: {}, skus: [],
  };
}

function edge(from: string, to: string): NetworkEdge {
  return {
    id: `${from}->${to}`, kind: "supply", from, to, name: `${from} to ${to}`, path: null,
    leadDays: { normal: null, current: null, p90: null },
    capacityPerWeek: null, transportCostPerUnit: null, state: "LEAN",
    risk: { level: "low", score: 0, reasons: [], evidence: [] }, skus: [], alternatives: [],
  };
}

/** `suppliers` suppliers into one port, into one DC, out to `customers` customers. */
function fanIn(suppliers: number, customers = 0, nameLength = 16): NetworkModel {
  const long = "x".repeat(Math.max(0, nameLength - 12));
  const nodes: NetworkNode[] = [
    node("port:aqaba", "port", "Port of Aqaba"),
    node("loc:DC", "dc", "Amman central DC"),
  ];
  const edges: NetworkEdge[] = [edge("port:aqaba", "loc:DC")];
  for (let i = 0; i < suppliers; i++) {
    nodes.push(node(`sup:S${i}`, "supplier", `Supplier ${i} ${long}`, i === 0 ? 0.8 : 0));
    edges.push(edge(`sup:S${i}`, "port:aqaba"));
  }
  for (let i = 0; i < customers; i++) {
    nodes.push(node(`cust:C${i}`, "customer", `Customer ${i}`));
    edges.push(edge("loc:DC", `cust:C${i}`));
  }
  return {
    id: "crowd", name: "Crowded", provenance: "workspace", asOf: "2026-01-05T00:00:00Z",
    nodes, edges, shipments: [], recommendations: [], notes: [],
  };
}

/** What `fitView` would zoom to for this layout on a given canvas. */
function fitZoom(model: NetworkModel): number {
  const placed = [...layoutNodes(model).values()];
  const width = Math.max(...placed.map((p) => p.x)) + NODE_W;
  const height = Math.max(...placed.map((p) => p.y)) + NODE_H;
  return Math.min(CANVAS.w / (width + 80), CANVAS.h / (height + 80), 1);
}

function overlaps(model: NetworkModel): Array<[string, string]> {
  const placed = [...layoutNodes(model).entries()];
  const hits: Array<[string, string]> = [];
  for (let i = 0; i < placed.length; i++) {
    for (let j = i + 1; j < placed.length; j++) {
      const [aId, a] = placed[i];
      const [bId, b] = placed[j];
      if (Math.abs(a.x - b.x) < NODE_W && Math.abs(a.y - b.y) < NODE_H) hits.push([aId, bId]);
    }
  }
  return hits;
}

for (const suppliers of [8, 30, 100]) {
  test(`${suppliers} suppliers: no two nodes are drawn on top of each other`, () => {
    const collapsed = groupCustomers(fanIn(suppliers, 40), new Set()).model;
    assert.deepEqual(overlaps(collapsed), [], "the layout grid guarantees clearance in both axes");
  });

  test(`${suppliers} suppliers: the view still opens at a zoom the labels survive`, () => {
    const collapsed = groupCustomers(fanIn(suppliers, 40), new Set()).model;
    const zoom = fitZoom(collapsed);
    assert.ok(zoom >= LEGIBLE_ZOOM,
      `${suppliers} suppliers collapse to a canvas that fits at ${zoom.toFixed(2)}, under ${LEGIBLE_ZOOM}`);
  });
}

test("a hundred suppliers drawn individually would be unreadable — which is why they are grouped", () => {
  // The measurement that justifies the grouping, kept here so nobody removes it as unnecessary.
  const zoom = fitZoom(fanIn(100));
  assert.ok(zoom < LEGIBLE_ZOOM, `ungrouped fit zoom was ${zoom.toFixed(2)}; the grouping is load-bearing`);
});

test("a crowd is collapsed into one node that still carries its worst member's risk", () => {
  const { model, groups } = groupCustomers(fanIn(30), new Set());
  const group = model.nodes.find((n) => isGroupId(n.id) && n.kind === "supplier")!;
  assert.ok(group, "thirty suppliers behind one port become one node");
  assert.equal(group.name, "30 suppliers");
  assert.equal(group.risk.score, 0.8, "the group is as exposed as its most exposed member");
  assert.match(group.risk.reasons[0], /^Supplier 0\b.*is short/, "and says which member that is");
  assert.equal(groups[0].memberIds.length, 30, "every member is remembered so the group can open");
});

test("opening a group puts every member back", () => {
  const closed = groupCustomers(fanIn(30), new Set());
  const groupId = closed.groups[0].id;
  const open = groupCustomers(fanIn(30), new Set([groupId]));
  assert.equal(open.model.nodes.filter((n) => n.kind === "supplier").length, 30);
  assert.ok(!open.model.nodes.some((n) => isGroupId(n.id) && n.kind === "supplier"));
});

test("a crowd below the threshold is left alone", () => {
  const small = groupCustomers(fanIn(SUPPLIER_GROUP_THRESHOLD - 1, GROUP_THRESHOLD - 1), new Set());
  assert.deepEqual(small.groups, [], "eight is a corridor; three is a list of suppliers");
  assert.equal(small.model.nodes.length, fanIn(SUPPLIER_GROUP_THRESHOLD - 1, GROUP_THRESHOLD - 1).nodes.length);
});

test("a supplier feeding two entry points is never swallowed by either group", () => {
  const model = fanIn(12);
  model.nodes.push(node("port:jeddah", "port", "Jeddah Islamic Port"));
  model.edges.push(edge("port:jeddah", "loc:DC"), edge("sup:S0", "port:jeddah"));
  const { model: collapsed } = groupCustomers(model, new Set());
  assert.ok(collapsed.nodes.some((n) => n.id === "sup:S0"),
    "a supplier on two corridors belongs to neither crowd and stays visible");
});

test("grouping keeps the graph connected, so nothing loses its path to the business", () => {
  const { model } = groupCustomers(fanIn(30, 40), new Set());
  const index = buildIndex(model);
  const group = model.nodes.find((n) => isGroupId(n.id) && n.kind === "supplier")!;
  assert.ok(index.downstream(group.id).nodes.has("loc:DC"), "the collapsed suppliers still reach the DC");
  const customers = model.nodes.find((n) => isGroupId(n.id) && n.kind === "customer")!;
  assert.ok(index.upstream(customers.id).nodes.has("loc:DC"), "and the collapsed customers are still served by it");
});

test("long names do not change the geometry, because a node box is a fixed width", () => {
  const long = groupCustomers(fanIn(30, 0, 90), new Set()).model;
  assert.deepEqual(overlaps(long), []);
  assert.equal(COLUMN_GAP - NODE_W, 60, "sixty pixels of clearance between columns");
  assert.ok(ROW_GAP - NODE_H >= 16, "and at least sixteen between rows");
});
