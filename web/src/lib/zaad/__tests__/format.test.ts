/**
 * Counts printed beside a noun.
 *
 * A filtered list of one is the normal case, not the edge case: "1 proposals", "only 1 orders" and
 * "one in ten takes 1 days" were all reachable in the shipped surfaces. COUNT is the one place that
 * decides the agreement, so these tests are what stops it drifting back.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { COUNT, MONEY, NUMBER, PERCENT, TALLY } from "../product";

test("one is singular", () => {
  assert.equal(COUNT(1, "order"), "1 order");
  assert.equal(COUNT(1, "matched order"), "1 matched order");
});

test("everything else is plural", () => {
  assert.equal(COUNT(0, "order"), "0 orders");
  assert.equal(COUNT(2, "order"), "2 orders");
  assert.equal(COUNT(1865, "matched order"), "1,865 matched orders");
});

test("an irregular plural is passed rather than guessed", () => {
  assert.equal(COUNT(1, "company", "companies"), "1 company");
  assert.equal(COUNT(3, "company", "companies"), "3 companies");
});

test("a count that is not a number is not available, not zero", () => {
  assert.equal(COUNT(null, "order"), "—");
  assert.equal(COUNT(undefined, "order"), "—");
  assert.equal(COUNT(Number.NaN, "order"), "—");
});

test("minus one is still singular", () => {
  assert.equal(COUNT(-1, "day"), "-1 day");
});

test("thousands are grouped the way the tables group them", () => {
  assert.equal(NUMBER(1865), "1,865");
  assert.equal(COUNT(1000, "product"), "1,000 products");
});

test("the other formatters still say — rather than inventing a zero", () => {
  assert.equal(NUMBER(null), "—");
  assert.equal(MONEY(null), "—");
  assert.equal(PERCENT(null), "—");
});

/**
 * TALLY is the rule three tables got wrong the same way: they tested a count for truth, so a
 * measured zero printed the dash that the rest of the product reserves for "not available".
 */
test("a measured zero is a word, not the dash that means not available", () => {
  assert.deepEqual(TALLY(0), { text: "none", muted: true });
  assert.deepEqual(TALLY(0, "nothing on order"), { text: "nothing on order", muted: true });
});

test("only absence is the dash", () => {
  assert.deepEqual(TALLY(null), { text: "—", muted: true });
  assert.deepEqual(TALLY(undefined), { text: "—", muted: true });
  assert.deepEqual(TALLY(Number.NaN), { text: "—", muted: true });
});

test("a count is the count, grouped as the tables group it", () => {
  assert.deepEqual(TALLY(1), { text: "1", muted: false });
  assert.deepEqual(TALLY(27), { text: "27", muted: false });
  assert.deepEqual(TALLY(1865), { text: "1,865", muted: false });
});

test("zero and absence never render alike", () => {
  assert.notEqual(TALLY(0).text, TALLY(null).text);
});
