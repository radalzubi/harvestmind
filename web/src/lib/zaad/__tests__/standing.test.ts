/**
 * The one status ladder, held against the exact contradiction it was written to end.
 *
 * Production could say "Nothing ZAAD can improve right now" beside "1 area needs attention" beside
 * a warehouse marked Critical whose service was projected at 100% against a 95% target. Each
 * sentence was true of its own input and the screen as a whole was incoherent. These tests fix the
 * rungs, their order, and the rule that a lower rung never overrides a higher one.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { standing, LEVEL_LABEL, type StandingInput } from "../standing";
import type { AttentionArea } from "@/lib/network/attention";
import type { Decision } from "../decisions";

const BASE: StandingInput = {
  notReady: null, readError: null, planPhase: "ready", planError: null,
  openDecisions: [], proposalsAwaitingReview: 0, areas: [], dataProblems: [],
};

function area(level: "attention" | "watch", title: string): AttentionArea {
  return {
    id: title, lead: { type: "node", id: `node:${title}` }, title, level, score: level === "attention" ? 0.7 : 0.3,
    members: [], summary: `${title} summary`,
    affected: { skus: [], customers: [], stockNodes: [], openOrders: 0, delayedShipments: 0 },
    recommendation: null,
  };
}

function decision(id: string): Decision {
  return { id, needsReview: true } as unknown as Decision;
}

test("a run in flight is its own rung, and never invites you to start another", () => {
  for (const phase of ["queued", "running"] as const) {
    const out = standing({ ...BASE, planPhase: phase, areas: [area("attention", "Aqaba lane")] });
    assert.equal(out.level, "working");
    assert.equal(out.next, null, "the plan card carries the control; the standing must not duplicate it");
    assert.match(out.detail, /You can leave this page/);
    assert.match(out.detail, /Aqaba lane needs watching meanwhile/);
    assert.ok(!/Run a plan/.test(out.headline + out.detail),
      "saying 'run a plan' while one is running is the contradiction this file exists to end");
  }
});

test("a missing upload outranks everything", () => {
  const out = standing({
    ...BASE, notReady: "Upload your customer orders before planning.",
    openDecisions: [decision("a")], proposalsAwaitingReview: 3, areas: [area("attention", "Supplier A")],
  });
  assert.equal(out.level, "blocked");
  assert.match(out.detail, /Upload your customer orders/);
  assert.equal(out.next?.href, "/upload");
  assert.equal(out.label, "Needs data");
  assert.deepEqual(out.watches.map((w) => w.title), ["Supplier A"],
    "a blocked workspace still carries its watches; it just does not lead with them");
});

test("a failed run is blocked, and says what failed", () => {
  const out = standing({ ...BASE, planPhase: "failed", planError: "The run did not finish inside its time." });
  assert.equal(out.level, "blocked");
  assert.match(out.headline, /could not finish/);
  assert.equal(out.detail, "The run did not finish inside its time.");
  assert.equal(out.label, "Run interrupted",
    "a chip reading 'Needs data' above 'could not finish its last run' is simply untrue");
});

test("a decision outranks a watch, and the watch is carried underneath it", () => {
  const out = standing({ ...BASE, openDecisions: [decision("a"), decision("b")], areas: [area("attention", "Aqaba lane")] });
  assert.equal(out.level, "decide");
  assert.equal(out.headline, "2 things need your decision.");
  assert.match(out.detail, /2 recommendations to review/);
  assert.match(out.detail, /Aqaba lane also needs watching/);
  assert.equal(out.watches.length, 1);
});

test("a proposal waiting for approval is a decision too", () => {
  const out = standing({ ...BASE, proposalsAwaitingReview: 1 });
  assert.equal(out.level, "decide");
  assert.equal(out.headline, "One proposed order is waiting for you.");
  assert.equal(out.next?.href, "/orders?state=READY_FOR_REVIEW");
});

test("both kinds of decision are counted separately and read naturally", () => {
  const out = standing({ ...BASE, openDecisions: [decision("a")], proposalsAwaitingReview: 2 });
  assert.equal(out.headline, "One thing needs your decision.");
  assert.equal(out.detail.startsWith("One recommendation to review, and 2 proposed orders waiting for approval."), true, out.detail);
});

test("with nothing to decide, a material condition is a watch and never a crisis", () => {
  const out = standing({ ...BASE, areas: [area("attention", "Jeddah supplier")] });
  assert.equal(out.level, "watch");
  assert.equal(out.headline, "No changes recommended.",
    "the plan's answer leads; the watch elaborates it");
  assert.match(out.detail, /Jeddah supplier needs monitoring/);
  assert.match(out.detail, /found none worth acting on, including here/);
});

test("the contradiction that prompted this cannot be produced", () => {
  // The exact production screen: no recommendation, one scored area, and a quiet one behind it.
  const out = standing({ ...BASE, areas: [area("attention", "Main warehouse"), area("watch", "Lane")] });
  const screen = `${out.headline} ${out.detail}`;
  assert.ok(!/nothing zaad can improve/i.test(screen), screen);
  assert.ok(!/critical/i.test(screen), screen);
  assert.equal(out.level, "watch");
  assert.equal(out.watches.length, 1, "only a material area is a watch; a quiet one is not");
});

test("a quiet network is normal, and says what is worth watching without alarm", () => {
  const out = standing({ ...BASE, areas: [area("watch", "Lane"), area("watch", "Port")] });
  assert.equal(out.level, "normal");
  assert.equal(out.headline, "No changes recommended.");
  assert.match(out.detail, /2 things are showing early signs but nothing that needs you/);
});

test("with no plan yet, the workspace is still usable and says so", () => {
  const out = standing({ ...BASE, planPhase: "none" });
  assert.equal(out.level, "normal");
  assert.equal(out.headline, "ZAAD has read your workspace.");
  assert.match(out.detail, /ready to look at now/);
  assert.equal(out.next?.label, "Run a plan");
});

test("every level has a label a person can read", () => {
  assert.deepEqual(Object.keys(LEVEL_LABEL).sort(), ["blocked", "decide", "normal", "watch", "working"]);
  for (const label of Object.values(LEVEL_LABEL)) {
    assert.ok(!/optimi[sz]er|incumbent|MILP|stance|protection row/i.test(label), label);
  }
});

test("more than two watches are summarised rather than listed to the horizon", () => {
  const out = standing({
    ...BASE,
    areas: ["A", "B", "C", "D"].map((t) => area("attention", t)),
  });
  assert.match(out.detail, /A, B and 2 more need monitoring/);
});
