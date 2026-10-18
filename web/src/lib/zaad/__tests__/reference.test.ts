import assert from "node:assert/strict";
import { test } from "node:test";

import { NEUTRAL_REFERENCE, columnLabel, mayClaimAgainstOperator, referenceLabel, referenceLabelCap } from "../reference";

test("the reference label is the backend's and is never 'your current plan'", () => {
  const reconstructed = { decision_reference: { type: "RECONSTRUCTED_POLICY", fidelity: "RECONSTRUCTED", provenance: "INFERRED_FROM_HISTORY", label: "the reconstructed historical rule" } };
  assert.equal(referenceLabel(reconstructed), "the reconstructed historical rule");
  assert.equal(referenceLabelCap(reconstructed), "The reconstructed historical rule");
  const orders = { decision_reference: { type: "INCUMBENT_ORDER_SET", fidelity: "NOT_AVAILABLE", provenance: "ORIGIN_NOT_ESTABLISHED", label: "the incumbent order set in the request (origin not established; not a captured operator plan)" } };
  assert.match(referenceLabel(orders), /origin not established/);
  assert.doesNotMatch(referenceLabel(orders), /your current plan/i);
});

test("a report from before the contract gets the neutral label, not a claim", () => {
  assert.equal(referenceLabel(null), NEUTRAL_REFERENCE);
  assert.equal(referenceLabel({ decision_reference: undefined }), NEUTRAL_REFERENCE);
  assert.equal(referenceLabel({ decision_reference: { type: "X", fidelity: "Y", provenance: null, label: "  " } }), NEUTRAL_REFERENCE);
  assert.equal(mayClaimAgainstOperator(null), false);
  assert.equal(mayClaimAgainstOperator({ comparison: { mode: "PLAN_MODE", claim_class: "MODEL_COMPARISON", permissions: { can_claim_against_operator: false } } }), false);
});

test("proposal columns take the backend's label and fall back to a neutral one", () => {
  const columns = [{ key: "current", label: "Reconstructed policy baseline" }, { key: "zaad", label: "What ZAAD recommends" }];
  assert.equal(columnLabel(columns, "current", "Decision reference"), "Reconstructed policy baseline");
  assert.equal(columnLabel(undefined, "current", "Decision reference"), "Decision reference");
  assert.equal(columnLabel([{ key: "current", label: "" }], "current", "Decision reference"), "Decision reference");
});
