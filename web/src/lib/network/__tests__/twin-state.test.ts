/**
 * Twin behaviour that the two views must share: switching lens keeps the place, a product
 * filter keeps the graph connected, and large customer sets collapse without losing anyone.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { buildCanonicalModel } from "../adapters/canonical";
import { buildIndex } from "../graph";
import { groupCustomers, isGroupId } from "../groups";
import type { NetworkModel } from "../model";
import { build, directory, report, request } from "@/lib/zaad/__tests__/fixture";

const model = buildCanonicalModel({ request, build, report, directory, homeRegion: "JO", workspaceName: "Acme" });

/** Mirrors the reducer in components/network/store.tsx, which is not importable without React. */
type State = { view: "network" | "map"; selection: { type: "node" | "edge"; id: string } | null; sku: string | null; panelOpen: boolean; fitSignal: number; focusSignal: number };
type Action =
  | { type: "view"; view: "network" | "map" }
  | { type: "select"; ref: State["selection"]; focus?: boolean }
  | { type: "sku"; sku: string | null };

function reduce(s: State, a: Action): State {
  switch (a.type) {
    case "view": return s.view === a.view ? s : { ...s, view: a.view, fitSignal: s.fitSignal + 1 };
    case "select": {
      const same = s.selection?.type === a.ref?.type && s.selection?.id === a.ref?.id;
      if (same && !a.focus) return s;
      return { ...s, selection: a.ref, panelOpen: a.ref != null, focusSignal: a.focus ? s.focusSignal + 1 : s.focusSignal };
    }
    case "sku": return { ...s, sku: a.sku, fitSignal: s.fitSignal + 1 };
  }
}

const initial: State = { view: "network", selection: null, sku: null, panelOpen: false, fitSignal: 0, focusSignal: 0 };

test("switching between NETWORK and MAP keeps the selection, the filter and the panel", () => {
  let s = reduce(initial, { type: "select", ref: { type: "node", id: "sup:SUP-B" } });
  s = reduce(s, { type: "sku", sku: "SKU-2" });
  const before = { ...s };
  s = reduce(s, { type: "view", view: "map" });
  assert.deepEqual(s.selection, before.selection);
  assert.equal(s.sku, before.sku);
  assert.equal(s.panelOpen, true);
  assert.equal(s.fitSignal, before.fitSignal + 1, "only the camera refits");
  s = reduce(s, { type: "view", view: "network" });
  assert.deepEqual(s.selection, before.selection);
  assert.equal(s.sku, "SKU-2");
});

test("re-selecting the same object with focus re-centres without churning state", () => {
  let s = reduce(initial, { type: "select", ref: { type: "node", id: "sup:SUP-A" } });
  const quiet = reduce(s, { type: "select", ref: { type: "node", id: "sup:SUP-A" } });
  assert.equal(quiet, s, "an identical selection is a no-op");
  s = reduce(s, { type: "select", ref: { type: "node", id: "sup:SUP-A" }, focus: true });
  assert.equal(s.focusSignal, 1, "a deep link to the current object still re-centres it");
});

test("clearing the selection closes the panel", () => {
  let s = reduce(initial, { type: "select", ref: { type: "edge", id: "lane:SUP-A->aqaba" } });
  assert.equal(s.panelOpen, true);
  s = reduce(s, { type: "select", ref: null });
  assert.equal(s.panelOpen, false);
});

/** Mirrors `filterBySku` in the store. */
function filterBySku(m: NetworkModel, sku: string | null): NetworkModel {
  if (!sku) return m;
  const nodes = m.nodes.filter((n) => n.skus.includes(sku) || n.kind === "port");
  const keep = new Set(nodes.map((n) => n.id));
  const edges = m.edges.filter((e) => keep.has(e.from) && keep.has(e.to) && (e.skus.length === 0 || e.skus.includes(sku)));
  const connected = new Set(edges.flatMap((e) => [e.from, e.to]));
  return { ...m, nodes: nodes.filter((n) => n.kind !== "port" || connected.has(n.id)), edges };
}

test("a product filter keeps only what carries that product, and drops orphaned ports", () => {
  const one = filterBySku(model, "SKU-1");
  assert.ok(one.nodes.some((n) => n.id === "sup:SUP-A"));
  assert.ok(!one.nodes.some((n) => n.id === "sup:SUP-B"), "a supplier of another product is filtered out");
  for (const e of one.edges) {
    const ids = new Set(one.nodes.map((n) => n.id));
    assert.ok(ids.has(e.from) && ids.has(e.to), `${e.id} points at a node the filter removed`);
  }
  const two = filterBySku(model, "SKU-2");
  assert.ok(!two.nodes.some((n) => n.kind === "port"), "the Aqaba port only carries SKU-1, so it goes too");
});

test("no filter returns the identical model, so the views never rebuild for nothing", () => {
  assert.equal(filterBySku(model, null), model);
});

test("many customers on one site collapse into one node that keeps their worst state", () => {
  const many: NetworkModel = {
    ...model,
    nodes: [
      ...model.nodes,
      ...[1, 2, 3, 4].map((i) => ({
        id: `cust:C${i}`, kind: "customer" as const, name: `Customer ${i}`, geo: null, importance: 0.4,
        state: (i === 3 ? "ALLOCATE" : "LEAN") as NetworkModel["nodes"][number]["state"],
        risk: { level: (i === 3 ? "high" : "low") as "high" | "low", score: i === 3 ? 0.6 : 0.05, reasons: i === 3 ? ["Short of its agreed level"] : [], evidence: [] },
        metrics: { demandPerWeek: 100 }, skus: ["SKU-1"],
      })),
    ],
    edges: [
      ...model.edges,
      ...[1, 2, 3, 4].map((i) => ({
        id: `service:MAIN->C${i}`, kind: "service" as const, from: "loc:MAIN", to: `cust:C${i}`, name: `MAIN → C${i}`,
        path: null, leadDays: { normal: null, current: null, p90: null }, capacityPerWeek: null, transportCostPerUnit: null,
        state: "LEAN" as const, risk: { level: "low" as const, score: 0, reasons: [], evidence: [] }, skus: ["SKU-1"], alternatives: [],
      })),
    ],
  };
  const { model: display, groups } = groupCustomers(many, new Set());
  assert.equal(groups.length, 1);
  const group = display.nodes.find((n) => isGroupId(n.id))!;
  assert.equal(group.subtitle, "4 customers");
  assert.equal(group.state, "ALLOCATE", "the group cannot look calmer than its worst member");
  assert.equal(group.metrics.demandPerWeek, 400);
  assert.ok(!display.nodes.some((n) => n.id === "cust:C1"), "members are hidden while collapsed");

  const expanded = groupCustomers(many, new Set([group.id]));
  assert.ok(expanded.model.nodes.some((n) => n.id === "cust:C1"), "opening the group brings everyone back");
  assert.ok(buildIndex(expanded.model).nodeById.has("cust:C3"));
});
