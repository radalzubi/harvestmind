import assert from "node:assert/strict";
import { test } from "node:test";

import { replayLabels } from "../labels";

const exact = { comparator_label: "the recorded historical orders", reference_label: "the reconstructed historical rule",
  comparison: { comparator: { type: "ACTUAL_HISTORICAL_ACTION", fidelity: "EXACT", label: "the recorded historical orders" }, permissions: { can_claim_historical_counterfactual_difference: true } },
  periods: { caption: "Cost difference per decision date: the recorded historical orders − ZAAD (positive = ZAAD cost less)" } };

test("labels repeat the backend contract for an exact comparator", () => {
  const l = replayLabels(exact);
  assert.equal(l.actionHeader, "The recorded historical orders");
  assert.equal(l.referenceHeader, "The reconstructed historical rule");
  assert.equal(l.periodCaption, exact.periods.caption);
  assert.equal(l.endStockHeader, "End stock (recorded historical orders / ZAAD)");
  assert.equal(l.serviceHeader, "Service (recorded historical orders / ZAAD)");
});

test("transformed and incomplete comparators never read as the operator's own orders", () => {
  for (const [label, fidelity] of [["a model-adjusted version of the recorded historical orders", "TRANSFORMED"], ["the recorded historical orders that could be identified (some lines could not be mapped to a source)", "INCOMPLETE"]] as const) {
    const l = replayLabels({ comparator_label: label, reference_label: "the reconstructed historical rule", comparison: { comparator: { type: "ACTUAL_HISTORICAL_ACTION", fidelity, label }, permissions: {} } });
    assert.equal(l.actionHeader, label.charAt(0).toUpperCase() + label.slice(1));
    assert.match(l.endStockHeader, /historical-action path/);
    assert.doesNotMatch(JSON.stringify(l), /your (actual )?orders|you \//i);
    assert.match(l.periodCaption, new RegExp(label.replace(/[()]/g, "\\$&") + " − ZAAD"));
  }
});

test("a report without the contract gets neutral language", () => {
  const l = replayLabels({});
  assert.equal(l.actionHeader, "The recorded historical orders as the replay evaluated them (comparator fidelity not established)");
  assert.equal(l.referenceHeader, "The reconstructed rule");
  assert.match(l.periodCaption, /comparator fidelity not established/);
  assert.match(l.endStockHeader, /historical-action path/);
  assert.doesNotMatch(JSON.stringify(l), /your orders|you \//i);
});

test("an operator-declared rule is named as declared, not as the operator's plan", () => {
  const l = replayLabels({ reference_label: "the operator-declared rule" });
  assert.equal(l.referenceHeader, "The operator-declared rule");
  assert.doesNotMatch(JSON.stringify(l), /current plan|your rule/i);
});
