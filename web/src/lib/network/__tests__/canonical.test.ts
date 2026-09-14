import assert from "node:assert/strict";
import { test } from "node:test";
import { buildCanonicalModel } from "../adapters/canonical";
import { attentionAreas, describe as describeItem, statusLine } from "../attention";
import { buildIndex, searchModel } from "../graph";
import { layoutNodes } from "../layout";
import { build, directory, report, request } from "@/lib/zaad/__tests__/fixture";

const model = buildCanonicalModel({ request, build, report, directory, homeRegion: "JO", workspaceName: "Acme" });
const index = buildIndex(model);
const node = (id: string) => model.nodes.find((n) => n.id === id)!;
const edge = (id: string) => model.edges.find((e) => e.id === id)!;

test("the twin is built from the operator's own workspace and says so", () => {
  assert.equal(model.provenance, "workspace");
  assert.equal(model.id, "workspace:acme");
  assert.equal(model.asOf, request.as_of);
});

test("every declared supplier, site, customer and port appears once", () => {
  assert.deepEqual(
    model.nodes.map((n) => n.id).sort(),
    ["cust:RETAIL", "loc:MAIN", "loc:RIYADH", "port:aqaba", "sup:SUP-A", "sup:SUP-B"],
  );
});

test("a supplier's risk comes from its measured fill and nothing else", () => {
  const a = node("sup:SUP-A");
  assert.equal(a.name, "Anwar Trading");
  assert.equal(a.state, "LEAN");
  assert.equal(a.risk.reasons.length, 0, "a 98% fill is not a reason to alarm anyone");
  assert.equal(a.metrics.fill?.mean, 0.98);
  assert.equal(a.metrics.fill?.n, 41);

  const b = node("sup:SUP-B");
  assert.ok(b.risk.score > 0, "a 84% fill must register");
  assert.match(b.risk.reasons[0], /84\.0% of ordered quantity has been arriving/);
  assert.ok(b.risk.evidence.includes("23 past deliveries"));
});

test("the build report's own field names are read, not ones we wished for", () => {
  // Captured verbatim from GET /api/zaad/network/request/from-workspace on a live workspace. The
  // field is `fill_mean`. An earlier version of the contract types declared `fill`, so every read
  // was undefined and supplier reliability silently never reached the twin's risk scoring at all —
  // the kind of defect a green build and a matching-but-wrong fixture will never catch.
  const captured = {
    "SUP-B": {
      fill_mean: 0.9801432066227092,
      fill_sd: 0.024574341608084818,
      lead_days: 34,
      lead_sd_days: 2.1065374432940898,
      sample_size: 24,
      provenance: "INFERRED_FROM_HISTORY",
    },
  };
  const m = buildCanonicalModel({
    request, build: { ...build, fits: captured }, report, directory, homeRegion: "JO", workspaceName: "Acme",
  });
  const b = m.nodes.find((n) => n.id === "sup:SUP-B")!;
  assert.equal(b.metrics.fill?.mean, 0.9801432066227092, "the fitted fill reaches the model");
  assert.equal(b.metrics.fill?.n, 24);
  assert.ok(!(b.missing ?? []).some((x) => /Delivery reliability needs more delivery history/.test(x)),
    "and a supplier with 24 measured deliveries is not described as unmeasured");
});

test("a thin sample caps how alarming a supplier is allowed to look", () => {
  const thin = { ...build, fits: { ...build.fits, "SUP-B": { fill_mean: 0.3, sample_size: 2, provenance: "INFERRED_FROM_HISTORY" } } };
  const m = buildCanonicalModel({ request, build: thin, report, directory, homeRegion: "JO", workspaceName: "Acme" });
  const b = m.nodes.find((n) => n.id === "sup:SUP-B")!;
  assert.ok(b.risk.score <= 0.45, `a 2-delivery sample must not reach critical, got ${b.risk.score}`);
  assert.match(b.risk.reasons[0], /only 2 deliveries measured/);
});

test("a supplier with no declared origin or route is not placed, and the model says why", () => {
  const b = node("sup:SUP-B");
  assert.equal(b.geo, null);
  assert.ok(b.missing!.some((m) => /No origin country is declared/.test(m)));
  assert.ok(b.missing!.some((m) => /No shipping route is declared/.test(m)));
  assert.ok(model.notes.some((n) => /1 supplier is not on the map/.test(n)));
});

test("a supplier placed from its country is marked approximate; a port is exact", () => {
  const a = node("sup:SUP-A");
  assert.equal(a.geo!.precision, "approximate");
  assert.equal(node("port:aqaba").geo!.precision, "exact");
});

test("a lane drawn from a route tag says it is a published route, not a tracked ship", () => {
  const lane = edge("lane:SUP-A->aqaba");
  assert.ok(lane.path && lane.path.length > 2);
  assert.ok(lane.missing!.some((m) => /not a tracked vessel/.test(m)));
  assert.ok(lane.missing!.some((m) => /follows the supplier that ships on it/.test(m)));
  assert.equal(model.shipments.length, 0, "nothing is ever drawn in motion");
});

test("multi-site workspaces are not stacked on one country centroid", () => {
  assert.equal(node("loc:MAIN").geo, null);
  assert.equal(node("loc:RIYADH").geo, null);
  assert.ok(model.notes.some((n) => /Sites are not placed on the map/.test(n)));
});

test("a single-site workspace is placed at the operator's country", () => {
  const single = { ...request, locations: [request.locations[0]], transfers: [], stock: request.stock.filter((s) => s.location === "MAIN") };
  const m = buildCanonicalModel({ request: single, build, report, directory, homeRegion: "JO", workspaceName: "Acme" });
  const main = m.nodes.find((n) => n.id === "loc:MAIN")!;
  assert.equal(main.geo!.precision, "approximate");
  assert.deepEqual([main.geo!.lon, main.geo!.lat], [36.2, 31.3]);
});

test("a site's state comes from the optimizer's own protection rows", () => {
  assert.equal(node("loc:RIYADH").state, "PROTECT");
  assert.equal(node("loc:MAIN").state, "LEAN");
});

test("a site's service reading is the report's, and a shortfall raises its risk", () => {
  const riyadh = node("loc:RIYADH");
  assert.equal(riyadh.metrics.serviceTarget, 0.97);
  assert.equal(riyadh.metrics.serviceProjected, 0.94);
  assert.match(riyadh.risk.reasons[0], /3\.0 points below target/);
  assert.equal(node("loc:MAIN").risk.reasons.length, 0);
});

test("holding planned cover is not a warning, however much of it there is", () => {
  // The production defect this closes: a site marked Critical while its service was projected at
  // 100% against a 95% target and the panel said no change was recommended. The score was being
  // driven by `protect` rows — which are P0 holding cover where cover is justified, i.e. the
  // system working. Twenty of them must still leave the site calm.
  const many = {
    ...report,
    protection: Array.from({ length: 20 }, (_, i) => ({
      sku: `SKU-${i}`, location: "MAIN", stance: "protect", protection_units: 100,
    })),
    network_service: [
      { service: "svc_main", location: "MAIN", requested: 0.95, jointly_feasible: 1,
        expected_achieved: 1, incumbent_achieved: 1, selected_achieved: 1 },
    ],
  };
  const m = buildCanonicalModel({ request, build, report: many, directory, homeRegion: "JO", workspaceName: "Acme" });
  const main = m.nodes.find((n) => n.id === "loc:MAIN")!;
  assert.equal(main.risk.score, 0, "planned protection contributes nothing to risk");
  assert.equal(main.risk.level, "low");
  assert.deepEqual(main.risk.reasons, [], "and it is not offered as a reason to worry");
  assert.ok(main.risk.evidence.some((e) => /being held with extra cover, as planned/.test(e)),
    "it is still visible — as evidence, in the language of a plan working");
  assert.equal(main.state, "PROTECT", "the optimizer's stance is unchanged; only the alarm is");
  const led = attentionAreas(m, buildIndex(m)).map((x) => x.lead.id);
  assert.ok(!led.includes("loc:MAIN"),
    `nothing reaches Home claiming the warehouse needs attention, got ${led.join(", ")}`);
});

test("a site that genuinely cannot be resupplied still raises its hand", () => {
  const stuck = {
    ...report,
    protection: [{ sku: "SKU-1", location: "MAIN", stance: "no_replenishment" }],
  };
  const m = buildCanonicalModel({ request, build, report: stuck, directory, homeRegion: "JO", workspaceName: "Acme" });
  const main = m.nodes.find((n) => n.id === "loc:MAIN")!;
  assert.ok(main.risk.score >= 0.5);
  assert.match(main.risk.reasons[0], /no replenishment route/);
});

test("stock is summed from the snapshot and valued at the declared unit value", () => {
  assert.equal(node("loc:MAIN").metrics.onHandUnits, 4000);
  assert.equal(node("loc:MAIN").metrics.onHandValue, 48000);
  assert.equal(node("loc:RIYADH").metrics.onHandValue, 7500);
});

test("open orders hang off the supplier that owes them", () => {
  const b = node("sup:SUP-B");
  assert.equal(b.metrics.openPOs!.length, 1);
  assert.equal(b.metrics.openPOs![0].id, "PO-1842");
  assert.equal(b.metrics.openPOs![0].sku, "SKU-2");
  assert.equal(b.metrics.openPOs![0].units, 1200);
});

test("customers carry only the service actually agreed, and admit they have no place", () => {
  const c = node("cust:RETAIL");
  assert.equal(c.metrics.serviceTarget, 0.97);
  assert.equal(c.metrics.demandPerWeek, null, "weekly demand is not in the contract, so it is not invented");
  assert.equal(c.geo, null);
  assert.ok(c.missing!.some((m) => /Customer locations are not part of the current upload/.test(m)));
});

test("a declared but unapproved transfer lane says so", () => {
  const held = { ...request, transfers: [{ ...request.transfers[0], approved: false }] };
  const m = buildCanonicalModel({ request: held, build, report, directory, homeRegion: "JO", workspaceName: "Acme" });
  const lane = m.edges.find((e) => e.id === "lane:MAIN->RIYADH")!;
  assert.ok(lane.missing!.some((x) => /declared but not approved/.test(x)));
});

test("recommendations attach to the object they affect", () => {
  const po = model.recommendations.find((r) => r.id === "po:PO-1842")!;
  assert.equal(po.targetId, "sup:SUP-B");
  assert.equal(po.source, "optimizer");
  assert.match(po.action, /DEFER PO-1842/);
  assert.match(po.noAction, /arrive as agreed/);
  const buy = model.recommendations.find((r) => r.id === "buy:SUP-A")!;
  assert.equal(buy.targetId, "sup:SUP-A");
  assert.match(buy.action, /Order 900 units this week/);
});

test("a workspace with no plan still draws a network, with no recommendations", () => {
  const m = buildCanonicalModel({ request, build, report: null, directory, homeRegion: "JO", workspaceName: "Acme" });
  assert.ok(m.nodes.length > 0);
  assert.deepEqual(m.recommendations, []);
  assert.equal(m.nodes.find((n) => n.id === "loc:RIYADH")!.metrics.serviceProjected, null);
});

test("a workspace with no supplier list still works and says what is lost", () => {
  const m = buildCanonicalModel({ request, build, report, directory: null, homeRegion: null, workspaceName: "Acme" });
  assert.equal(m.nodes.find((n) => n.id === "sup:SUP-A")!.name, "SUP-A");
  assert.ok(m.notes.some((n) => /No supplier master list is uploaded/.test(n)));
});

test("build warnings reach the reader rather than being swallowed", () => {
  assert.ok(model.notes.some((n) => /priced at zero/.test(n)));
});

test("the attention layer leads with the site that is actually short", () => {
  const areas = attentionAreas(model, index);
  assert.ok(areas.length > 0);
  const line = statusLine(areas);
  assert.match(line.headline, /need|normal/);
  const sentence = describeItem({ type: "node", id: "sup:SUP-B" }, model, index);
  assert.match(sentence, /Baraka Foods is/);
});

test("search finds an order, a supplier and a product", () => {
  assert.equal(searchModel(model, "PO-1842")[0].id, "sup:SUP-B");
  assert.equal(searchModel(model, "Anwar")[0].id, "sup:SUP-A");
  assert.ok(searchModel(model, "SKU-2").length > 0);
});

test("the layout is deterministic and lays supply out left to right", () => {
  const a = layoutNodes(model);
  const b = layoutNodes(model);
  for (const [id, at] of a) assert.deepEqual(b.get(id), at, `${id} moved between identical runs`);
  assert.ok(a.get("sup:SUP-A")!.x < a.get("port:aqaba")!.x);
  assert.ok(a.get("port:aqaba")!.x < a.get("loc:MAIN")!.x);
  assert.ok(a.get("loc:MAIN")!.x < a.get("cust:RETAIL")!.x);
});

/**
 * Subject-verb agreement in the twin's sentences. These strings are assembled from lists whose
 * length is usually more than one, so the plural was written once: a supplier carrying a single
 * product read "1 SKU depend on this supplier" in the panel a person is asked to act on.
 */
test("a single dependency takes a singular verb", () => {
  const sentences = model.nodes.map((n) => describeItem({ type: "node", id: n.id }, model, index))
    .concat(model.edges.map((e) => describeItem({ type: "edge", id: e.id }, model, index)));
  // The subject opens its own sentence, so the check anchors there: "1 open order and 1 SKU depend"
  // is a compound subject and correctly plural, while a sentence *starting* "1 SKU depend" is not.
  for (const clause of sentences.flatMap((said) => said.split(/(?<=\.)\s+/))) {
    assert.ok(!/^1 SKU depend\b/.test(clause), `"1 SKU depend" in: ${clause}`);
    assert.ok(!/^1 open order depend\b/.test(clause), `"1 open order depend" in: ${clause}`);
    assert.ok(!/^Stock depend\b/.test(clause), `"Stock depend" in: ${clause}`);
    assert.ok(!/\b1 customer groups\b/.test(clause), `"1 customer groups" in: ${clause}`);
    assert.ok(!/\b\d+ customers? (?!group)/.test(clause) || !/depend/.test(clause),
              `a customer count without its noun in: ${clause}`);
  }
});

test("the fixture actually reaches both sides of the rule", () => {
  // Without this the test above passes on a fixture that never produces a singular subject.
  const clauses = model.nodes.map((n) => describeItem({ type: "node", id: n.id }, model, index))
    .concat(model.edges.map((e) => describeItem({ type: "edge", id: e.id }, model, index)))
    .flatMap((said) => said.split(/(?<=\.)\s+/))
    .filter((c) => /\bdepends?\b/.test(c));
  assert.ok(clauses.some((c) => /^1 SKU depends on/.test(c)), "no singular subject in the fixture");
  // And the rule must not over-correct: subjects joined by "and" stay plural whatever their counts.
  assert.ok(clauses.some((c) => /^1 open order and 1 SKU depend on/.test(c)), "no compound subject");
});

/**
 * A sentence that quotes money must quote the workspace's money. `describe()` had a hard `$` in
 * it, three lines from a facts row that formats the same number through the workspace currency.
 */
test("a site's stock value is quoted in the workspace's own currency", () => {
  const jod = buildCanonicalModel({
    request: { ...request, currency: "JOD" }, build, report, directory,
    homeRegion: "JO", workspaceName: "Acme",
  });
  const jodIndex = buildIndex(jod);
  const site = jod.nodes.find((n) => (n.kind === "dc" || n.kind === "branch") && n.metrics.onHandValue != null);
  assert.ok(site, "the fixture has a site with a stock value");
  const said = describeItem({ type: "node", id: site.id }, jod, jodIndex);
  assert.ok(said.includes("JOD"), `no workspace currency in: ${said}`);
  assert.ok(!said.includes("$"), `a dollar sign survived in: ${said}`);

  // And the default fixture, which does trade in dollars, says so by name rather than by symbol.
  const usd = describeItem({ type: "node", id: site.id }, model, index);
  assert.ok(usd.includes("USD"), usd);
});
