/**
 * Counts printed beside a noun.
 *
 * A filtered list of one is the normal case, not the edge case: "1 proposals", "only 1 orders" and
 * "one in ten takes 1 days" were all reachable in the shipped surfaces. COUNT is the one place that
 * decides the agreement, so these tests are what stops it drifting back.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { COUNT, MONEY, NUMBER, PERCENT, TALLY, pagerState } from "../product";

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

/**
 * The pager rule. It has been wrong twice: once shipping ("101–1 of 1 product", and Next disabled
 * over 271,140 records the explorer would still serve) and once in the first attempt at the fix
 * (a last page that is exactly full left Next enabled). It is one function now, and these are the
 * four worlds it has to be right in.
 */
const at = (o: object) => pagerState({ total: 150, limit: 50, offset: 0, shown: 50, ...o });

test("a list that fits on one page is a count, not a range", () => {
  assert.deepEqual(pagerState({ total: 7, limit: 50, offset: 0, shown: 7 }), { kind: "count", total: 7 });
  assert.deepEqual(pagerState({ total: 0, limit: 50, offset: 0, shown: 0 }), { kind: "count", total: 0 });
});

test("the range ends where the rows end, not where the total says", () => {
  assert.deepEqual(at({ offset: 0 }), { kind: "range", from: 1, to: 50, atStart: true, atEnd: false });
  assert.deepEqual(at({ offset: 50 }), { kind: "range", from: 51, to: 100, atStart: false, atEnd: false });
  assert.deepEqual(at({ offset: 100 }), { kind: "range", from: 101, to: 150, atStart: false, atEnd: true });
});

test("a last page that is exactly full is still the last page", () => {
  // The regression the first fix introduced: `shown < limit` alone leaves Next enabled here.
  assert.deepEqual(at({ total: 100, offset: 50, shown: 50 }),
                   { kind: "range", from: 51, to: 100, atStart: false, atEnd: true });
});

test("a short page is the last page whatever the total claims", () => {
  const short = at({ offset: 100, shown: 12 });
  assert.deepEqual(short, { kind: "range", from: 101, to: 112, atStart: false, atEnd: true });
});

test("a floored total does not end the list", () => {
  // The explorer stops counting at 100,000 and says "more than"; the rows keep coming.
  const deep = pagerState({ total: 100_000, limit: 50, offset: 150_000, shown: 50, isFloor: true });
  assert.deepEqual(deep, { kind: "range", from: 150_001, to: 150_050, atStart: false, atEnd: false });
  // and a page that really is past the end says so rather than printing a reversed range
  assert.deepEqual(pagerState({ total: 100_000, limit: 50, offset: 400_000, shown: 0, isFloor: true }),
                   { kind: "past", page: 8_001 });
});

test("a page past the end is named, never printed as a reversed range", () => {
  assert.deepEqual(pagerState({ total: 1, limit: 50, offset: 100, shown: 0 }), { kind: "past", page: 3 });
  const said = pagerState({ total: 150, limit: 50, offset: 500, shown: 0 });
  assert.equal(said.kind, "past");
  assert.ok(said.kind === "past" && said.page === 11);
});

test("the first page is never reported as past the end", () => {
  assert.deepEqual(pagerState({ total: 0, limit: 50, offset: 0, shown: 0, isFloor: true }),
                   { kind: "range", from: 1, to: 0, atStart: true, atEnd: true });
});
