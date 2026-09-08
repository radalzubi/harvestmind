import assert from "node:assert/strict";
import { test } from "node:test";
import { ILLUSTRATIVE_NETWORK } from "../fixtures";
import { buildIndex, searchModel } from "../graph";
import { layoutNodes } from "../layout";
import { illustrativeEngine, optimizerEngine, pickEngine } from "../scenario";

const snapshot = () => JSON.stringify(ILLUSTRATIVE_NETWORK);

test("simulation never mutates the live model", () => {
  const before = snapshot();
  const index = buildIndex(ILLUSTRATIVE_NETWORK);
  const result = illustrativeEngine.evaluate(ILLUSTRATIVE_NETWORK, [
    { id: "o1", kind: "lane_unavailable", targetType: "edge", targetId: "lane_yantian_aqaba" },
    { id: "o2", kind: "supplier_fill", targetType: "node", targetId: "sup_a", value: 0.6 },
  ], index);
  assert.equal(snapshot(), before);
  assert.notEqual(result.view, ILLUSTRATIVE_NETWORK);
  const liveLane = ILLUSTRATIVE_NETWORK.edges.find((e) => e.id === "lane_yantian_aqaba")!;
  const simLane = result.view.edges.find((e) => e.id === "lane_yantian_aqaba")!;
  assert.equal(liveLane.state, "PROTECT");
  assert.equal(simLane.state, "ALLOCATE");
  assert.ok(result.exposed.edges.has("lane_yantian_aqaba"));
  assert.ok(result.exposed.nodes.has("port_aqaba"));
});

test("illustrative results are labelled as such and never look like optimizer output", () => {
  const index = buildIndex(ILLUSTRATIVE_NETWORK);
  const result = illustrativeEngine.evaluate(ILLUSTRATIVE_NETWORK, [{ id: "o1", kind: "port_closure", targetType: "node", targetId: "port_aqaba" }], index);
  assert.equal(result.source, "illustrative");
  assert.equal(result.label, "Illustrative scenario result · development demo adapter, not the ZAAD optimizer");
  assert.ok(result.recommendations.length > 0);
  assert.ok(result.recommendations.every((r) => r.source === "illustrative"));
  assert.ok(result.comparison && result.comparison.doNothing.service! < result.comparison.current.service!);
  assert.ok(result.comparison.zaad.service! >= result.comparison.doNothing.service!);
});

test("no overrides means no comparison and the live picture", () => {
  const index = buildIndex(ILLUSTRATIVE_NETWORK);
  const result = illustrativeEngine.evaluate(ILLUSTRATIVE_NETWORK, [], index);
  assert.equal(result.comparison, null);
  assert.deepEqual(result.view.nodes, ILLUSTRATIVE_NETWORK.nodes);
});

test("the optimizer engine is a hook, not a fake", () => {
  assert.equal(optimizerEngine.available, false);
  assert.equal(pickEngine().id, "illustrative");
  const index = buildIndex(ILLUSTRATIVE_NETWORK);
  const r = optimizerEngine.evaluate(ILLUSTRATIVE_NETWORK, [{ id: "x", kind: "port_closure", targetType: "node", targetId: "port_aqaba" }], index);
  assert.equal(r.comparison, null);
  assert.equal(r.recommendations.length, 0);
});

test("layout is deterministic and flows left to right", () => {
  const a = layoutNodes(ILLUSTRATIVE_NETWORK), b = layoutNodes(ILLUSTRATIVE_NETWORK);
  assert.deepEqual([...a.entries()], [...b.entries()]);
  const x = (id: string) => a.get(id)!.x;
  assert.ok(x("sup_c") < x("port_yantian") && x("port_yantian") < x("port_aqaba") && x("port_aqaba") < x("dc_amman") && x("dc_amman") < x("br_north") && x("br_north") < x("cust_north"));
});

test("dependency queries and search", () => {
  const index = buildIndex(ILLUSTRATIVE_NETWORK);
  const down = index.downstream("sup_c");
  assert.ok(down.nodes.has("dc_amman") && down.nodes.has("cust_south"));
  assert.ok(!down.nodes.has("sup_a"));
  const rel = index.related({ type: "edge", id: "lane_yantian_aqaba" })!;
  assert.ok(rel.nodes.has("port_yantian") && rel.nodes.has("sup_c") && rel.nodes.has("br_south"));
  assert.ok(!rel.nodes.has("sup_b"));
  // a prefix match on the lane name outranks a substring match on the port name; nodes win ties
  assert.equal(searchModel(ILLUSTRATIVE_NETWORK, "yantian")[0].id, "lane_yantian_aqaba");
  assert.equal(searchModel(ILLUSTRATIVE_NETWORK, "shenzhen")[0].id, "port_yantian");
  assert.ok(searchModel(ILLUSTRATIVE_NETWORK, "SKU-3120").length > 0);
  assert.deepEqual(searchModel(ILLUSTRATIVE_NETWORK, ""), []);
});

test("the fixture is labelled illustrative and internally consistent", () => {
  assert.equal(ILLUSTRATIVE_NETWORK.provenance, "illustrative");
  assert.ok(ILLUSTRATIVE_NETWORK.notes[0].includes("Illustrative development data"));
  const ids = new Set(ILLUSTRATIVE_NETWORK.nodes.map((n) => n.id));
  for (const e of ILLUSTRATIVE_NETWORK.edges) assert.ok(ids.has(e.from) && ids.has(e.to), e.id);
  const eids = new Set(ILLUSTRATIVE_NETWORK.edges.map((e) => e.id));
  for (const s of ILLUSTRATIVE_NETWORK.shipments) assert.ok(eids.has(s.edgeId));
  for (const e of ILLUSTRATIVE_NETWORK.edges) for (const a of e.alternatives) assert.ok(eids.has(a), a);
});
