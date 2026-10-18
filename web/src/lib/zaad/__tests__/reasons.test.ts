/**
 * The jargon policy, held against the planner's *actual* strings.
 *
 * These are copied verbatim from `zaad/full/planner.py`. If the engine adds a reason that is not
 * translated here, the last test fails on the vocabulary rather than letting it reach a buyer.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { plainReason, plainReasons } from "../reasons";
import { buildDecisions } from "../decisions";
import { build, report, request } from "./fixture";

/** Verbatim from zaad/full/planner.py. */
const ENGINE_REASONS = [
  "Recovery candidate does not materially improve weighted service shortfall versus the incumbent under independent confirmation.",
  "Recovery candidate lowers a service without raising a higher-priority one; priority-weighted recovery rejected.",
  "Recovery candidate improves service but exceeds the configured economic downside tolerance.",
  "No candidate materially improves priority-weighted service shortfall over the incumbent; incumbent retained.",
  "Incumbent misses a requested service target under independent confirmation and no candidate reaches it either; best joint recovery reported.",
  "Neither the incumbent nor any candidate meets every requested service target under independent confirmation, and the gap is material.",
  "Candidate meets a service target the incumbent misses, but exceeds the configured economic downside tolerance.",
  "Independent fitted-model confirmation does not establish positive benefit.",
  "The candidate's own solve stopped with an optimality gap wider than the economic benefit claimed, so the advantage is not established.",
  "Candidate meets every service target with no material economic penalty and materially less carried inventory; adopted.",
  "Incumbent misses a requested service target under independent confirmation; the candidate meets every target within the economic downside tolerance (service-first acceptance).",
  "Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service recovery.",
  "Unit-fill regression control cannot open approval gate.",
  "Operator incumbent is missing; a synthetic proxy is not evidence against the customer's policy.",
  "NO MATERIAL IMPROVEMENT AVAILABLE: the change is below every materiality threshold.",
  "Incumbent itself has no verified feasible projection; no executable fallback is fabricated.",
  "Requested service targets are not jointly achievable under the modeled state; selector evaluated best joint recovery instead of requiring an impossible SLA.",
  "No selection candidate achieves every requested service metric.",
];

/** Words an operator should never have to look up. */
const JARGON = /\b(incumbent|candidate|priority-weighted|out-of-model|optimality gap|SLA|MILP|recourse|nonanticipativity|ATP|synthetic proxy|selector)\b/i;

test("every reason the planner can emit is translated", () => {
  for (const reason of ENGINE_REASONS) {
    const said = plainReason(reason);
    assert.ok(said, `no translation for: ${reason}`);
    assert.ok(!JARGON.test(said!), `jargon survived translation of "${reason}": ${said}`);
  }
});

test("a translated reason still says what the engine said", () => {
  assert.match(
    plainReason("No candidate materially improves priority-weighted service shortfall over the incumbent; incumbent retained.")!,
    /serves your customers better than what you are already doing/,
  );
  assert.match(
    plainReason("Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service recovery.")!,
    /stress tests/,
  );
});

test("an unrecognised reason is shown, with the terms that have plain equivalents replaced", () => {
  const said = plainReason("The incumbent was retained because the candidate hit an SLA wall.")!;
  // H3a: an engine "incumbent" is ZAAD's decision reference, not the operator's plan
  assert.match(said, /ZAAD's decision reference/);
  assert.doesNotMatch(said, /current plan/i);
  assert.match(said, /alternative/);
  assert.match(said, /service agreement/);
  assert.ok(!JARGON.test(said), said);
});

test("nothing is silently dropped and nothing is duplicated", () => {
  assert.equal(plainReason("   "), null);
  const twice = plainReasons([ENGINE_REASONS[3], ENGINE_REASONS[3], ENGINE_REASONS[11]]);
  assert.equal(twice.length, 2, "the same reason twice is said once");
  assert.equal(plainReasons(ENGINE_REASONS).length, 3, "the reader is capped, not buried");
  assert.deepEqual(plainReasons(undefined), []);
});

test("the engine's own words survive into the technical record", () => {
  const engine = { ...report, reasons: [ENGINE_REASONS[3], ENGINE_REASONS[11]] };
  for (const d of buildDecisions(engine, request, build)) {
    const operatorText = [d.headline, d.summary, ...d.why, d.doNothing ?? ""].join(" ");
    assert.ok(!JARGON.test(operatorText), `jargon reached the operator on ${d.id}: ${operatorText}`);
    assert.deepEqual(
      (d.technical as { engine_reasons?: string[] }).engine_reasons,
      engine.reasons,
      `${d.id} lost the engine's own wording`,
    );
  }
});
