import assert from "node:assert/strict";
import { test } from "node:test";
import { scopeSentence, solveScope } from "../scope";

const req = (sources: Array<{ sku: string; supplier: string; resources?: string[] }>, terms: string[] = []) => ({
  skus: [...new Set(sources.map((s) => s.sku))].map((id) => ({ id })) as never,
  sources: sources.map((s, i) => ({ id: `src${i}`, sku: s.sku, supplier: s.supplier, destination: "DC", route: [], unit_price: 1, resources: s.resources ?? [] })) as never,
  supplier_terms: terms.map((supplier) => ({ supplier })),
});

test("products sharing a supplier capacity resource are one joint problem", () => {
  const s = solveScope(req([{ sku: "A", supplier: "S1", resources: ["cap_S1"] }, { sku: "B", supplier: "S1", resources: ["cap_S1"] }, { sku: "C", supplier: "S2", resources: ["cap_S2"] }]), 150);
  assert.deepEqual(s, { catalogue: 150, evaluated: 3, coupled: 2, components: 2 });
  assert.equal(scopeSentence(s), "Catalogue 150 · evaluated 3 · solved together; 2 of them share supplier capacity or order terms, forming 2 independent groups.");
});

test("supplier-level order terms tie a supplier's products together", () => {
  const s = solveScope(req([{ sku: "A", supplier: "S1" }, { sku: "B", supplier: "S1" }], ["S1"]), null);
  assert.equal(s.components, 1);
  assert.equal(scopeSentence(s), "Evaluated 2 · solved together as one problem: every product shares supplier capacity or order terms with another.");
});

test("a single product is solved on its own and an empty request has no groups", () => {
  assert.equal(scopeSentence(solveScope(req([{ sku: "A", supplier: "S1" }]), 10)), "Catalogue 10 · evaluated 1 · solved on its own.");
  assert.equal(solveScope({ skus: [], sources: [] } as never, 10).components, 0);
});

test("the plan's own products are the ones counted, not everything the request holds", () => {
  const s = solveScope(req([{ sku: "A", supplier: "S1", resources: ["cap"] }, { sku: "B", supplier: "S1", resources: ["cap"] }, { sku: "C", supplier: "S2" }]), 150, ["A", "B"]);
  assert.deepEqual(s, { catalogue: 150, evaluated: 2, coupled: 2, components: 1 });
});

test("uncoupled products are said to be separable, not \"solved together\"", () => {
  const s = solveScope(req([{ sku: "A", supplier: "S1" }, { sku: "B", supplier: "S2" }]), 150);
  assert.equal(scopeSentence(s), "Catalogue 150 · evaluated 2 · none of them share supplier capacity or order terms; they were planned in one run and each could be planned on its own.");
});
