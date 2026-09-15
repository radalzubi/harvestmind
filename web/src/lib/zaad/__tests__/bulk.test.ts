import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { bulkBodies, planBulk, proposalFromDecision } from "../bulk";
import type { Decision } from "../decisions";

function buy(id: string, supplier: string, sku: string, selected: number, destination = "DC", price = 2): Decision {
  return {
    id: `buy:${id}`, category: "Purchasing", headline: "", verb: selected ? "BUY MORE" : "HOLD",
    target: { type: "supplier", id: supplier, networkId: `sup:${supplier}`, label: supplier }, summary: "", why: [], effect: [], doNothing: null,
    evidence: [], technical: { source: { id, supplier, sku, destination, route: [], unit_price: price, case_multiple: 12 }, selected, incumbent: 0 },
    urgency: 1, materiality: null, needsReview: true,
  };
}

describe("bulk purchase creation", () => {
  it("groups by supplier and destination, in a stable order, lines by product", () => {
    const plan = planBulk([buy("s3", "SUP-2", "SKU-9", 10), buy("s1", "SUP-1", "SKU-2", 5), buy("s2", "SUP-1", "SKU-1", 7), buy("s4", "SUP-1", "SKU-1", 3, "NORTH")]);
    assert.deepEqual(plan.asked, []);
    assert.deepEqual(plan.groups.map((g) => g.key), ["SUP-1|DC", "SUP-1|NORTH", "SUP-2|DC"]);
    assert.deepEqual(plan.groups[0].lines.map((l) => l.sku), ["SKU-1", "SKU-2"]);
    assert.deepEqual(plan.groups[0].decision_ids, ["buy:s1", "buy:s2"]);
  });
  it("never invents a line: holds, moves, amendments and unknown sources are asked, not created", () => {
    const hold = buy("h", "SUP-1", "SKU-1", 0);
    const move: Decision = { ...buy("m", "SUP-1", "SKU-1", 5), id: "move:lane1" };
    const amend: Decision = { ...buy("p", "SUP-1", "SKU-1", 5), id: "po:PO-1" };
    const unknown: Decision = { ...buy("u", "SUP-1", "SKU-1", 5), technical: { source: "src_missing", selected: 5 } };
    const plan = planBulk([hold, move, amend, unknown, buy("ok", "SUP-1", "SKU-1", 5)]);
    assert.equal(plan.groups.length, 1);
    assert.deepEqual(plan.asked.map((a) => a.decision.id).sort(), ["buy:h", "buy:u", "move:lane1", "po:PO-1"]);
    assert.equal("reason" in proposalFromDecision(hold), true);
  });
  it("sums the same product within one group and records where it came from", () => {
    const plan = planBulk([buy("a", "SUP-1", "SKU-1", 5), buy("b", "SUP-1", "SKU-1", 7)]);
    assert.deepEqual(plan.groups[0].lines, [{ sku: "SKU-1", quantity: 12, unit_price: 2, units_per_case: 12 }]);
    const bodies = bulkBodies(plan, "usd");
    assert.equal(bodies[0].origin, "ZAAD_RECOMMENDATION"); assert.equal(bodies[0].supplier_id, "SUP-1"); assert.equal(bodies[0].destination_id, "DC"); assert.equal(bodies[0].currency, "usd"); assert.equal(bodies[0].source_decision_id, "buy:a");
    assert.ok(String(bodies[0].notes).includes("buy:b"));
  });
});
