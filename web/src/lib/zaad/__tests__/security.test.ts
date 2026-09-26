/** Security review 2026-09: the interface's own guards (formula-safe CSV cells, the header set, storage clearing). */
import assert from "node:assert/strict";
import { test } from "node:test";

import { escape, toCSV } from "../../csv";
import { pushRecent, saveRecents } from "../../commands/recents";

test("a cell that would be a spreadsheet formula is written as text (SEC-013)", () => {
  for (const cell of ["=HYPERLINK(\"http://x\")", "=1+1", "+CMD|' /C calc'!A0", "-2+3", "@SUM(A1)", "\tx", "\rx"]) {
    const out = escape(cell);
    assert.ok(out.startsWith("\"'") || out.startsWith("'"), `${cell} -> ${out}`);
  }
  assert.equal(escape("plain"), "plain");
  assert.equal(escape("a,b"), "\"a,b\"");
  assert.equal(escape(12), "12");
  assert.equal(escape(null), "");
  const csv = toCSV([{ name: "=cmd", qty: 1 }], [{ key: "name", label: "name" }, { key: "qty", label: "qty" }]);
  assert.ok(!csv.split("\n")[1].startsWith("="));
});

test("the header set carries a content security policy without a wildcard script source (SEC-012)", async () => {
  const cfg = await import("../../../../next.config");
  const csp = cfg.CONTENT_SECURITY_POLICY;
  assert.ok(csp.includes("frame-ancestors 'none'"));
  assert.ok(csp.includes("object-src 'none'"));
  assert.ok(!/script-src[^;]*\*/.test(csp));
  assert.ok(!/connect-src[^;]*\*/.test(csp));
  const names = cfg.SECURITY_HEADERS.map((h: { key: string }) => h.key);
  for (const required of ["Content-Security-Policy", "X-Frame-Options", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy"]) {
    assert.ok(names.includes(required), required);
  }
  assert.equal((cfg.default as { poweredByHeader?: boolean }).poweredByHeader, false);
});

test("recent-record labels are keyed by workspace and are plain data (SEC-029)", () => {
  const store = new Map<string, string>();
  const storage = { setItem: (k: string, v: string) => { store.set(k, v); } };
  saveRecents("op_a", pushRecent([], { kind: "record", id: "SKU-1", route: "/inventory?sku=SKU-1", label: "Widget" }), storage);
  assert.ok(store.has("zaad.recents.op_a"));
  assert.ok(!store.has("zaad.recents.op_b"));
});
