/**
 * A run whose process died.
 *
 * `zaad/full/jobs.py` has no reaper: if the API restarts mid-solve, the row stays RUNNING for
 * ever. Observed directly — restarting the API mid-run left a job the page polled indefinitely.
 * The optimizer package is frozen and this pass does not touch it, so the product tells the reader
 * instead. This is the rule it uses.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { ABANDONED_GRACE_MS, abandoned } from "../workspace-data";

const STARTED = "2026-09-14T13:09:31.964270+00:00";
const AT = Date.parse(STARTED);
const running = { status: "RUNNING", started_at: STARTED, timeout_s: 900 } as const;

test("a run inside the time the engine gave it is not abandoned", () => {
  assert.equal(abandoned(running, AT + 1_000), false);
  assert.equal(abandoned(running, AT + 899_000), false);
});

test("a run just past its time is given a minute of grace", () => {
  assert.equal(abandoned(running, AT + 900_000 + 1_000), false, "a slow clock is not an interruption");
  assert.equal(abandoned(running, AT + 900_000 + ABANDONED_GRACE_MS + 1_000), true);
});

test("the microsecond precision the engine writes is parsed, not thrown away", () => {
  assert.ok(Number.isFinite(AT), "Date.parse must read the engine's own timestamp format");
  assert.equal(abandoned(running, AT + 2_000_000), true);
});

test("only a running job can be abandoned", () => {
  for (const status of ["QUEUED", "DONE", "FAILED", "TIMEOUT", "CANCELLED"]) {
    assert.equal(abandoned({ status, started_at: STARTED, timeout_s: 900 }, AT + 9_000_000), false, status);
  }
});

test("a record without the two fields the rule needs is never called abandoned", () => {
  assert.equal(abandoned({ status: "RUNNING", started_at: null, timeout_s: 900 }, AT + 9_000_000), false);
  assert.equal(abandoned({ status: "RUNNING", started_at: STARTED, timeout_s: null }, AT + 9_000_000), false);
  assert.equal(abandoned({ status: "RUNNING", started_at: "not a date", timeout_s: 900 }, AT + 9_000_000), false);
});

test("the observed orphan would have been caught", () => {
  // The real record from the session: started 13:09:31Z with a 900 s allowance, still RUNNING at
  // 13:34Z because the API had been restarted under it.
  assert.equal(abandoned(running, Date.parse("2026-09-14T13:34:00Z")), true);
});
