/**
 * SEC-038 regression: leaving a workspace leaves nothing of it in the browser, and a credential is
 * never stored — nor the previous workspace cleared — before the server has accepted it.
 *
 * Cases A, E, F and G of the closure brief are pinned here against fake stores; B, C and D (what a
 * second workspace, the Back button and a signed-out tab render) are browser flows recorded in the
 * closure tracker's QA section — they reduce to the same invariant tested here: after a switch the
 * keys a page would read back are gone.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  GLOBAL_LOCAL_KEYS, TENANT_LOCAL_PREFIXES, TENANT_SESSION_KEYS,
  clearTenantClientState, isTenantLocalKey, switchCredential,
} from "../../tenant-state";
import { loadRecents, pushRecent, saveRecents } from "../../commands/recents";

class FakeStorage {
  private m = new Map<string, string>();
  get length() { return this.m.size; }
  key(i: number) { return [...this.m.keys()][i] ?? null; }
  getItem(k: string) { return this.m.get(k) ?? null; }
  setItem(k: string, v: string) { this.m.set(k, v); }
  removeItem(k: string) { this.m.delete(k); }
  keys() { return [...this.m.keys()].sort(); }
}

function tenantA() {
  const local = new FakeStorage();
  const session = new FakeStorage();
  session.setItem("harvestmind.operator-token", "token-of-A");
  session.setItem("harvestmind.sector", "commercial");
  local.setItem("zaad.locale", "ar");
  saveRecents("op_a", pushRecent([], { kind: "record", id: "PO-1001", route: "/orders/PO-1001", label: "PO-1001 Supplier A" }), local);
  local.setItem("zaad.prefs.user.op_a", JSON.stringify({ pinned: ["orders"], quickActions: [], bindings: {}, version: 1 }));
  local.setItem("zaad.prefs.device.op_a", JSON.stringify({ bindings: {}, version: 1 }));
  local.setItem("zaad.data.hidden.op_a.stg_fmcg_skus", JSON.stringify(["unit_cost", "margin_pct"]));
  return { local, session };
}

test("A. clearing tenant state removes every tenant-scoped key and nothing else", () => {
  const { local, session } = tenantA();
  const removed = clearTenantClientState({ local, session }, false);
  assert.deepEqual(local.keys(), ["zaad.locale"]);                       // G. the language survives
  assert.equal(session.getItem("harvestmind.operator-token"), null);
  assert.equal(session.getItem("harvestmind.sector"), null);
  for (const key of TENANT_SESSION_KEYS) assert.ok(removed.includes(key));
  assert.ok(removed.some((k) => k.startsWith("zaad.recents.")));
  assert.ok(removed.some((k) => k.startsWith("zaad.prefs.user.")));
  assert.ok(removed.some((k) => k.startsWith("zaad.data.hidden.")));
});

test("the inventory classifies every key the interface writes", () => {
  for (const prefix of TENANT_LOCAL_PREFIXES) assert.ok(isTenantLocalKey(`${prefix}op_x`));
  for (const key of GLOBAL_LOCAL_KEYS) assert.equal(isTenantLocalKey(key), false);
  assert.equal(isTenantLocalKey("zaad.recents.op_a"), true);
  assert.equal(isTenantLocalKey("zaad.data.hidden.op_a.stg_fmcg_skus"), true);
  assert.equal(isTenantLocalKey("zaad.locale"), false);
});

test("E. a refused candidate changes nothing: the previous workspace stays signed in", async () => {
  const { local, session } = tenantA();
  const before = local.keys();
  let stored: string | null = null;
  const result = await switchCredential("dead-link-token", async () => false, (t) => { stored = t; }, { local, session });
  assert.equal(result.outcome, "refused");
  assert.deepEqual(result.cleared, []);
  assert.equal(stored, null);
  assert.deepEqual(local.keys(), before);
  assert.equal(session.getItem("harvestmind.operator-token"), "token-of-A");
});

test("E'. a check that throws (network down) counts as refused, and an empty candidate is ignored", async () => {
  const { local, session } = tenantA();
  const r1 = await switchCredential("x", async () => { throw new Error("offline"); }, () => assert.fail("stored"), { local, session });
  assert.equal(r1.outcome, "refused");
  const r2 = await switchCredential("   ", async () => true, () => assert.fail("stored"), { local, session });
  assert.equal(r2.outcome, "empty");
  assert.equal(session.getItem("harvestmind.operator-token"), "token-of-A");
});

test("an accepted candidate is validated alone, the old workspace is cleared, then the new credential is stored — in that order", async () => {
  const { local, session } = tenantA();
  const order: string[] = [];
  const check = async (candidate: string) => {
    assert.equal(candidate, "token-of-B");
    assert.equal(session.getItem("harvestmind.operator-token"), "token-of-A", "the previous session is intact while the candidate is checked");
    order.push("check");
    return true;
  };
  const store = (t: string) => {
    assert.deepEqual(local.keys(), ["zaad.locale"], "cleared before the new credential is stored");
    order.push(`store:${t}`);
    session.setItem("harvestmind.operator-token", t);
  };
  const result = await switchCredential(" token-of-B ", check, store, { local, session });
  assert.equal(result.outcome, "accepted");
  assert.deepEqual(order, ["check", "store:token-of-B"]);
  assert.ok(result.cleared.length >= 5);
  assert.equal(session.getItem("harvestmind.operator-token"), "token-of-B");
});

test("F. identical ids across workspaces: after a switch B reads none of A's recents, and A's are gone too", async () => {
  const { local, session } = tenantA();
  assert.equal(loadRecents("op_a", local).length, 1);
  await switchCredential("token-of-B", async () => true, (t) => session.setItem("harvestmind.operator-token", t), { local, session });
  assert.deepEqual(loadRecents("op_b", local), []);
  assert.deepEqual(loadRecents("op_a", local), []);
  // B opens the same PO id: only B's key is written, and it carries B's label
  saveRecents("op_b", pushRecent([], { kind: "record", id: "PO-1001", route: "/orders/PO-1001", label: "PO-1001 Supplier B" }), local);
  assert.deepEqual(local.keys(), ["zaad.locale", "zaad.recents.op_b"]);
  assert.equal(loadRecents("op_b", local)[0].label, "PO-1001 Supplier B");
});

test("G. clearing is safe without stores and never throws", () => {
  assert.deepEqual(clearTenantClientState({ local: null, session: null }, false), []);
  const throwing = { length: 1, key: () => { throw new Error("blocked"); }, removeItem: () => { throw new Error("blocked"); } };
  assert.doesNotThrow(() => clearTenantClientState({ local: throwing, session: throwing }, false));
});
