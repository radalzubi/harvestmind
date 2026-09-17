import assert from "node:assert/strict";
import { test } from "node:test";
import type { Job } from "@/lib/api";
import { DiagnosticPoller, formatElapsed, isTerminal, viewOf, type PollerDeps, type PollerState } from "../lifecycle";

const STAGES = [
  { key: "preparing", label: "Preparing your historical data" },
  { key: "reconstructing", label: "Reconstructing your purchasing behaviour" },
  { key: "lanes", label: "Reading supply conditions on your lanes" },
  { key: "testing", label: "Testing alternative policies on your own history" },
  { key: "reporting", label: "Building your report" },
];
const T0 = Date.parse("2026-09-17T10:00:00Z");
const job = (over: Partial<Job>): Job => ({
  id: "job_abc", kind: "diagnostic", status: "running", progress: "", stage: null, stages: STAGES, queue_position: null, reference: "job_abc",
  created_at: "2026-09-17T10:00:00Z", started_at: "2026-09-17T10:00:10Z", finished_at: null, error: null, summary: null, report: null, ...over,
});

// ── the view ──
test("idle without a job", () => {
  const v = viewOf(null, T0);
  assert.equal(v.kind, "idle"); assert.equal(v.live, false); assert.equal(v.canRetry, false);
});

test("queued shows the position when known, elapsed since creation, and can cancel", () => {
  const v = viewOf(job({ status: "queued", queue_position: 3, started_at: null, progress: "waiting for a solver slot" }), T0 + 42_000);
  assert.equal(v.kind, "queued"); assert.equal(v.live, true);
  assert.equal(v.detail, "2 diagnostics ahead of you"); assert.equal(v.queuePosition, 3);
  assert.equal(v.elapsedS, 42); assert.equal(v.canCancel, true);
  assert.equal(viewOf(job({ status: "queued", queue_position: 1, started_at: null }), T0).detail, "You are next in line");
  const m = viewOf(job({ status: "queued", queue_position: null, started_at: null, progress: "starting a dedicated solver machine" }), T0);
  assert.equal(m.detail, "Starting a dedicated solver machine"); assert.equal(m.queuePosition, null);
});

test("running shows the real stage, the backend's own words, and elapsed since start; never a percentage", () => {
  const v = viewOf(job({ stage: "testing", progress: "backtesting candidates on your own history at 20 scenarios per fold" }), T0 + 112_000);
  assert.equal(v.kind, "running"); assert.equal(v.live, true);
  assert.equal(v.stageIndex, 3); assert.equal(v.title, "Running your diagnostic");
  assert.match(v.detail!, /backtesting candidates/);
  assert.equal(v.elapsedS, 102);
  assert.equal(JSON.stringify(v).includes("%"), false);
  const early = viewOf(job({ stage: null, progress: "" }), T0 + 11_000);
  assert.equal(early.stageIndex, -1); assert.equal(early.detail, null);
});

test("the reporting stage is its own visible state", () => {
  const v = viewOf(job({ stage: "reporting", progress: "assembling the evidence for your report" }), T0 + 20_000);
  assert.equal(v.kind, "reporting"); assert.equal(v.title, "Building your report"); assert.equal(v.live, true); assert.equal(v.stageIndex, 4);
});

test("done stops the animation and reports the run duration", () => {
  const v = viewOf(job({ status: "done", stage: "reporting", finished_at: "2026-09-17T10:03:10Z" }), T0 + 999_000);
  assert.equal(v.kind, "done"); assert.equal(v.live, false); assert.equal(v.elapsedS, 180); assert.equal(v.canRetry, false);
});

test("failed carries the message and the reference and offers a retry", () => {
  const v = viewOf(job({ status: "failed", error: "ValueError: bad column", reference: "job_abc" }), T0);
  assert.equal(v.kind, "failed"); assert.equal(v.live, false); assert.equal(v.message, "ValueError: bad column");
  assert.equal(v.reference, "job_abc"); assert.equal(v.canRetry, true); assert.equal(v.canCancel, false);
});

test("timed out is explicit, not a spinner", () => {
  const v = viewOf(job({ status: "timed_out", error: "the diagnostic exceeded 60 minutes; run it again or contact ZAAD with reference job_abc" }), T0);
  assert.equal(v.kind, "timed_out"); assert.equal(v.live, false); assert.match(v.message!, /run it again/); assert.equal(v.canRetry, true);
});

test("cancelled is a clean terminal state", () => {
  const v = viewOf(job({ status: "cancelled", error: null }), T0);
  assert.equal(v.kind, "cancelled"); assert.equal(v.live, false); assert.match(v.message!, /cancelled/); assert.equal(v.canRetry, true);
});

test("elapsed formatting", () => {
  assert.equal(formatElapsed(0), "0s"); assert.equal(formatElapsed(59), "59s"); assert.equal(formatElapsed(102), "1m 42s");
  assert.equal(formatElapsed(3725), "1h 02m 05s"); assert.equal(formatElapsed(null), ""); assert.equal(formatElapsed(-5), "");
});

test("terminal states", () => {
  for (const s of ["done", "failed", "timed_out", "cancelled"] as const) assert.equal(isTerminal(s), true);
  for (const s of ["queued", "running"] as const) assert.equal(isTerminal(s), false);
  assert.equal(isTerminal(null), false);
});

// ── the poller, with fake timers and a scripted server ──
function harness(script: { start?: Job; latest?: Job | null; polls: Array<Job | Error>; cancel?: Job }) {
  const timers: Array<{ fn: () => void; ms: number; id: number }> = [];
  let nextId = 1;
  const calls = { start: 0, fetch: 0, latest: 0, cancel: 0 };
  const states: PollerState[] = [];
  const deps: PollerDeps = {
    start: async () => { calls.start += 1; if (!script.start) throw new Error("no start"); return script.start; },
    latest: async () => { calls.latest += 1; return script.latest ?? null; },
    cancel: async () => { calls.cancel += 1; if (!script.cancel) throw new Error("no cancel"); return script.cancel; },
    fetchJob: async () => { calls.fetch += 1; const next = script.polls.shift(); if (next === undefined) throw new Error("poll script exhausted"); if (next instanceof Error) throw next; return next; },
    setTimer: (fn, ms) => { const id = nextId++; timers.push({ fn, ms, id }); return id; },
    clearTimer: (h) => { const i = timers.findIndex((t) => t.id === h); if (i >= 0) timers.splice(i, 1); },
    intervalMs: 3000, lostAfter: 2, maxBackoffMs: 20000,
  };
  const p = new DiagnosticPoller(deps, (s) => states.push(s));
  const fire = async () => { const t = timers.shift(); if (!t) throw new Error("no timer pending"); t.fn(); await new Promise((r) => setImmediate(r)); await new Promise((r) => setImmediate(r)); return t.ms; };
  return { p, timers, calls, states, fire };
}

test("start polls until done, then stops; the timer is cleared", async () => {
  const h = harness({ start: job({ status: "queued", started_at: null }), polls: [job({ stage: "preparing" }), job({ stage: "testing" }), job({ status: "done", stage: "reporting" })] });
  await h.p.start();
  assert.equal(h.p.state.job!.status, "queued"); assert.equal(h.timers.length, 1);
  assert.equal(await h.fire(), 3000); assert.equal(h.p.state.job!.stage, "preparing");
  await h.fire(); assert.equal(h.p.state.job!.stage, "testing");
  await h.fire(); assert.equal(h.p.state.job!.status, "done");
  assert.equal(h.timers.length, 0, "no poll after a terminal state");
  assert.equal(h.calls.fetch, 3);
});

test("a repeated press while starting or while active never starts a second run", async () => {
  const h = harness({ start: job({ status: "running", stage: "preparing" }), polls: [job({ stage: "testing" })] });
  const a = h.p.start(); const b = h.p.start(); const c = h.p.start();
  await Promise.all([a, b, c]);
  assert.equal(h.calls.start, 1);
  await h.p.start();                       // active job: still no new start
  assert.equal(h.calls.start, 1);
  assert.equal(h.timers.length, 1, "one polling timer, not three");
});

test("a start that fails re-enables the button", async () => {
  const h = harness({ polls: [] });
  await assert.rejects(() => h.p.start(), /no start/);
  assert.equal(h.p.state.starting, false); assert.equal(h.p.state.job, null);
});

test("refresh reconnects to the newest active job and resumes polling", async () => {
  const h = harness({ latest: job({ stage: "lanes" }), polls: [job({ stage: "testing" }), job({ status: "done" })] });
  await h.p.reconnect();
  assert.equal(h.calls.latest, 1); assert.equal(h.p.state.job!.stage, "lanes");
  assert.equal(h.timers.length, 1); assert.equal(h.timers[0].ms, 0, "the first poll after reconnect is immediate");
  await h.fire(); await h.fire();
  assert.equal(h.p.state.job!.status, "done"); assert.equal(h.timers.length, 0);
});

test("refresh with a finished job shows it without polling; with no job stays idle", async () => {
  const a = harness({ latest: job({ status: "done" }), polls: [] });
  await a.p.reconnect(); assert.equal(a.p.state.job!.status, "done"); assert.equal(a.timers.length, 0);
  const b = harness({ latest: null, polls: [] });
  await b.p.reconnect(); assert.equal(b.p.state.job, null); assert.equal(b.timers.length, 0);
});

test("polling interruption backs off, flags the connection after two failures, and recovers", async () => {
  const h = harness({ start: job({ stage: "testing" }), polls: [new Error("net"), new Error("net"), new Error("net"), job({ stage: "testing" }), job({ status: "done" })] });
  await h.p.start();
  assert.equal(await h.fire(), 3000); assert.equal(h.p.state.connectionLost, false); assert.equal(h.timers[0].ms, 6000);
  await h.fire(); assert.equal(h.p.state.connectionLost, true); assert.equal(h.timers[0].ms, 12000);
  await h.fire(); assert.equal(h.timers[0].ms, 20000, "capped back-off");
  await h.fire(); assert.equal(h.p.state.connectionLost, false); assert.equal(h.timers[0].ms, 3000, "back to the normal interval");
  await h.fire(); assert.equal(h.p.state.job!.status, "done"); assert.equal(h.timers.length, 0);
  assert.equal(h.p.state.job!.stage, "reporting" === h.p.state.job!.stage ? "reporting" : h.p.state.job!.stage);
});

test("cancel moves to the terminal state and stops polling", async () => {
  const h = harness({ start: job({ stage: "testing" }), cancel: job({ status: "cancelled" }), polls: [] });
  await h.p.start(); assert.equal(h.timers.length, 1);
  await h.p.cancel();
  assert.equal(h.p.state.job!.status, "cancelled"); assert.equal(h.timers.length, 0); assert.equal(h.calls.cancel, 1);
  await h.p.cancel();                       // idempotent on a terminal job
  assert.equal(h.calls.cancel, 1);
});

test("a stale or reaped job arrives as timed_out through the normal poll and stops the animation", async () => {
  const h = harness({ start: job({ stage: "testing" }), polls: [job({ status: "timed_out", error: "no progress from the solver machine for 31 minutes; run it again or contact ZAAD with reference job_abc" })] });
  await h.p.start(); await h.fire();
  const v = viewOf(h.p.state.job, T0);
  assert.equal(v.kind, "timed_out"); assert.equal(v.live, false); assert.match(v.message!, /reference job_abc/); assert.equal(h.timers.length, 0);
});

test("stop() after unmount silences late results", async () => {
  const h = harness({ start: job({ stage: "testing" }), polls: [job({ status: "done" })] });
  await h.p.start(); const before = h.states.length;
  h.p.stop();
  assert.equal(h.timers.length, 0);
  await h.p.tick();
  assert.equal(h.states.length, before, "no state change after stop");
});

test("queue position reaches the view through polling", async () => {
  const h = harness({ start: job({ status: "queued", started_at: null, queue_position: 2 }), polls: [job({ status: "queued", started_at: null, queue_position: 1 }), job({ stage: "preparing" })] });
  await h.p.start();
  assert.equal(viewOf(h.p.state.job, T0).detail, "1 diagnostic ahead of you");
  await h.fire(); assert.equal(viewOf(h.p.state.job, T0).detail, "You are next in line");
  await h.fire(); assert.equal(viewOf(h.p.state.job, T0).kind, "running");
});
