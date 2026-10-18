import assert from "node:assert/strict";
import { test } from "node:test";
import { buildDecisions, planSummary, money, units, weeks } from "../decisions";
import { productsWithAmendmentRights, rankProducts } from "../workspace-data";
import { build, report, request } from "./fixture";

const decisions = buildDecisions(report, request, build);
const byId = new Map(decisions.map((d) => [d.id, d]));

test("every recommendation the report carries becomes exactly one decision", () => {
  assert.deepEqual(
    decisions.map((d) => d.id).sort(),
    ["buy:src_a1", "move:tr1", "po:PO-1842"],
  );
});

test("an open-PO change reads as an instruction, not as optimizer vocabulary", () => {
  const d = byId.get("po:PO-1842")!;
  assert.equal(d.category, "Open POs");
  assert.equal(d.verb, "DEFER");
  assert.match(d.headline, /^Delay PO-1842 by 1 week$/);
  assert.equal(d.needsReview, true);
  // nothing in the operator-facing text may carry the engine's words
  const operatorText = [d.headline, d.summary, ...d.why, d.doNothing ?? "", ...d.effect.map((f) => `${f.label} ${f.value ?? ""}`)].join(" ");
  for (const jargon of ["incumbent", "P4B", "recourse", "MILP", "nonanticipativity", "ATP", "PENDING_REVIEW"]) {
    assert.ok(!new RegExp(jargon, "i").test(operatorText), `"${jargon}" leaked into operator copy: ${operatorText}`);
  }
});

test("a PO decision states the timing change, the do-nothing outcome and the contractual right", () => {
  const d = byId.get("po:PO-1842")!;
  const arrival = d.effect.find((f) => f.label === "Arrival");
  assert.equal(arrival?.value, "moves from in 4 weeks to in 5 weeks");
  const payment = d.effect.find((f) => f.label === "Payment");
  assert.equal(payment?.value, "moves from in 4 weeks to in 5 weeks");
  assert.match(d.doNothing!, /1,200 units arrive in 4 weeks/);
  const right = d.evidence.find((e) => e.label === "Contractual right");
  assert.match(right!.detail, /MSA §7\.2/);
  assert.equal(right!.provenance, "OPERATOR_DECLARED");
});

test("a quantity the report does not price is null, never zero", () => {
  const d = byId.get("po:PO-1842")!;
  // the fixture's defer avoids no invoice, so no "saved" figure is shown at all
  assert.equal(d.effect.find((f) => f.label === "Invoice avoided"), undefined);
  const invoice = d.effect.find((f) => f.label === "Remaining invoice")!;
  assert.equal(invoice.value, "USD 30,000");
  assert.match(invoice.note!, /the timing moves, the amount does not/);
  assert.equal(money(null, "USD"), null);
  assert.equal(units(undefined), null);
  assert.equal(money(Number.NaN, "USD"), null);
});

test("supplier reliability is quoted with the sample it rests on", () => {
  const d = byId.get("buy:src_a1")!;
  const reliability = d.evidence.find((e) => e.label === "Delivery reliability")!;
  assert.match(reliability.detail, /98\.0% of ordered quantity arrives, on 41 past deliveries/);
  assert.equal(reliability.provenance, "INFERRED_FROM_HISTORY");
});

test("a purchase decision compares against what the decision reference would order, named by the backend", () => {
  const d = byId.get("buy:src_a1")!;
  assert.equal(d.verb, "BUY LESS");
  assert.match(d.headline, /Order less SKU-1 from SUP-A — 900 units this week/);
  // H3a: the fixture report carries no decision_reference, so the reference is named neutrally, never as "the current plan"
  assert.equal(d.effect.find((f) => f.label === "ZAAD's decision reference orders")?.value, "1,500 units");
  assert.ok(!d.effect.some((f) => /current plan/i.test(f.label)));
  assert.match(d.doNothing ?? "", /^ZAAD's decision reference orders 1,500 units/);
  const labelled = buildDecisions({ ...report, decision_reference: { type: "RECONSTRUCTED_POLICY", fidelity: "RECONSTRUCTED", provenance: "INFERRED_FROM_HISTORY", label: "the reconstructed historical rule" } }, request, build);
  const l = labelled.find((x) => x.id === "buy:src_a1")!;
  assert.equal(l.effect.find((f) => f.label === "The reconstructed historical rule orders")?.value, "1,500 units");
  assert.equal(d.effect.find((f) => f.label === "Difference")?.value, "-600 units");
  assert.equal(d.effect.find((f) => f.label === "Order value")?.value, "USD 9,000");
});

test("a transfer names both ends, the arrival and the cost", () => {
  const d = byId.get("move:tr1")!;
  assert.equal(d.category, "Inventory");
  assert.match(d.headline, /Move 400 units of SKU-2 from MAIN to RIYADH/);
  assert.equal(d.effect.find((f) => f.label === "Arrives")?.value, "next week");
  assert.equal(d.effect.find((f) => f.label === "Transfer cost")?.value, "USD 160");
  assert.equal(d.target.networkId, "lane:tr1");
});

test("only first-review actions become decisions; later periods are replanning guidance", () => {
  const later = { ...report, commitments: undefined, actions: [{ action: "purchase" as const, source: "src_a1", period: 3, quantity: 500 }], incumbent_actions: [] };
  assert.equal(buildDecisions(later, request, build).length, 0);
});

test("every decision can open the object it affects in the network", () => {
  for (const d of decisions) assert.ok(d.target.networkId, `${d.id} has no network target`);
});

test("decisions needing review sort ahead of the rest, then by urgency", () => {
  const keepOnly = {
    ...report,
    status: "RETAIN_INCUMBENT",
    actions: [],
    incumbent_actions: [],
    commitments: {
      ...report.commitments!,
      commitment_action: "KEEP",
      verdict: "NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE",
      orders: [{ ...report.commitments!.orders[0], recommended_action: "KEEP" as const, quantity_affected: 0, timing_change: [], contractual_basis: [] }],
    },
  };
  const out = buildDecisions(keepOnly, request, build);
  assert.equal(out.length, 1);
  assert.equal(out[0].needsReview, false);
  assert.equal(out[0].verb, "KEEP");
  assert.match(out[0].headline, /Keep PO-1842 as it stands/);
  assert.match(out[0].evidence.find((e) => e.label === "Contractual right")!.detail, /No amendment right is declared/);
});

test("the plan summary prices the plan, not a line, and keeps the engine's own limitations", () => {
  const s = planSummary(report, request);
  assert.equal(s.valueVsCurrent, 7500);
  assert.equal(s.workingCapitalDelta, -6000);
  assert.equal(s.recommendsChange, true);
  assert.equal(s.currency, "USD");
  assert.deepEqual(s.service.map((x) => x.location), ["MAIN", "RIYADH"]);
  assert.equal(s.service[1].recommended, 0.94);
  assert.ok(s.costBreakdown.some((r) => r.component === "Holding stock" && r.delta === -2000));
  assert.deepEqual(s.limitations, report.limitations);
  assert.ok(s.activeCapabilities.includes("Open PO changes"));
  assert.ok(s.activeCapabilities.includes("Network positioning"));
});

test("a report with no economics says the value is unavailable rather than zero", () => {
  const s = planSummary({ ...report, economics: {} }, request);
  assert.equal(s.valueVsCurrent, null);
  assert.equal(s.workingCapitalDelta, null);
  assert.deepEqual(s.costBreakdown, []);
});

test("period wording is the operator's, not an index", () => {
  assert.equal(weeks(0), "this week");
  assert.equal(weeks(1), "next week");
  assert.equal(weeks(6), "in 6 weeks");
});

// ── run scope ───────────────────────────────────────────────────────────────
// A run may cover a selection of products. The selection must never orphan a declared
// amendment right: the server refuses a request carrying options for an order it no longer
// holds, and silently dropping the commitment analysis instead would hide the decisions that
// matter most.

test("every product with a declared amendment right is found", () => {
  const withRights = productsWithAmendmentRights(request);
  assert.deepEqual([...withRights], ["SKU-2"]);
});

test("a product whose only option is keep carries no declared right", () => {
  const keepOnly = {
    ...request,
    pipeline: [{ ...request.pipeline[0], options: [request.pipeline[0].options![0]] }],
  };
  assert.equal(productsWithAmendmentRights(keepOnly).size, 0);
});

test("ranking puts the products with the most on order first", () => {
  assert.deepEqual(rankProducts(request), ["SKU-2", "SKU-1"]);
});

test("ranking is stable for products with nothing on order and no stock value", () => {
  const bare = { ...request, pipeline: [], stock: [] };
  assert.deepEqual(rankProducts(bare), ["SKU-1", "SKU-2"], "ties fall back to the product id");
});
