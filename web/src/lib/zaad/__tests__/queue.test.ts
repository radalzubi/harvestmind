import { test } from "node:test";
import assert from "node:assert/strict";
import { queueAheadOf } from "../queue";

test("a queued job counts the runs ahead of it: queued ones before it plus the solves holding the planner", () => {
  assert.equal(queueAheadOf({ status: "QUEUED", queue_position: 1, running_now: 1 }), 1);
  assert.equal(queueAheadOf({ status: "QUEUED", queue_position: 3, running_now: 1 }), 3);
  assert.equal(queueAheadOf({ status: "QUEUED", queue_position: 1, running_now: 0 }), 0);
});

test("no position is no claim: an older server or a job this service is not holding says nothing", () => {
  assert.equal(queueAheadOf({ status: "QUEUED" }), null);
  assert.equal(queueAheadOf({ status: "QUEUED", queue_position: null }), null);
  assert.equal(queueAheadOf({ status: "RUNNING", queue_position: 1, running_now: 1 }), null);
});
