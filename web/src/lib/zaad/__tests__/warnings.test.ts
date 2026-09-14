/**
 * The engine's build warnings are the only place the product tells an operator that something in
 * their own data limits what ZAAD could do. They are written for an engineer, so they are
 * formatted — and the property that matters is that formatting never becomes paraphrase: every
 * content word the engine chose has to survive.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { operatorWarning } from "../warnings";

test("a capability the workspace never declared is not a data problem", () => {
  assert.equal(operatorWarning(
    "recourse requested but the vault declares no recourse specification " +
    "(stg_recourse_spec, migration 019): the frozen request is built"), null);
  assert.equal(operatorWarning(
    "commitments requested but the vault declares no PO options " +
    "(stg_po_options / stg_po_commitments, migration 022): every open order stays KEEP-only"), null);
});

test("a table named in the sentence becomes the file the operator uploaded", () => {
  // "in stg_fmcg_lanes:" used to become "in lanes:", which reads as a field label rather than a
  // place to go and fix something.
  assert.equal(
    operatorWarning("no lanes declared in stg_fmcg_lanes: locations are planned as isolated (no transfers)"),
    "No lanes declared in your lanes upload: locations are planned as isolated (no transfers)");
});

test("a product at a place is written the way the rest of the product writes it", () => {
  assert.equal(
    operatorWarning("QA-001075@QA-BR-AQABA has demand but no supplier delivery and no lane: " +
                    "it can only serve from stock on hand"),
    "QA-001075 at QA-BR-AQABA has demand but no supplier delivery and no lane: " +
    "it can only serve from stock on hand");
});

test("every content word survives", () => {
  const raw = "no lanes declared in stg_fmcg_lanes: locations are planned as isolated (no transfers)";
  const said = operatorWarning(raw)!;
  for (const word of ["lanes", "declared", "locations", "planned", "isolated", "transfers"]) {
    assert.ok(said.toLowerCase().includes(word), `"${word}" was lost`);
  }
});

test("a sentence with nothing to translate is returned as a sentence", () => {
  assert.equal(operatorWarning("two sites share a name"), "Two sites share a name");
});

test("an email address is not a service id", () => {
  // The rule is for `SKU@LOCATION`. Neither side of one contains a dot, so an address survives.
  assert.equal(operatorWarning("contact buyer@example.com about the shortfall"),
               "Contact buyer@example.com about the shortfall");
});

test("an empty warning is dropped rather than shown as an empty line", () => {
  assert.equal(operatorWarning("   "), null);
});
