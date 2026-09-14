/**
 * Two conventions this product learned the hard way, checked over the source itself.
 *
 * Both were defects in four or more places at once, which is what makes them worth a check rather
 * than a code review: they are shapes, not mistakes, and the shape reads naturally.
 *
 *   * **A number tested for truth.** `value ? NUMBER(value) : "—"` prints the dash this product
 *     reserves for *not available* over a zero the vault states plainly. On a workspace where
 *     every purchase order has been received it turned three whole columns into a claim of
 *     ignorance. `TALLY` decides that now; see `format.test.ts`.
 *   * **Money without a currency.** A hard `$` in a template string quoted a site's stock value in
 *     dollars three lines from a facts row using the workspace's own currency. The two agree on a
 *     dollar workspace and one of them is simply wrong anywhere else.
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const SRC = join(process.cwd(), "src");
/** The operating product. The legacy produce surfaces are a different release and not this pass. */
const SCOPE = [
  join(SRC, "lib", "zaad"), join(SRC, "lib", "network"), join(SRC, "components", "workspace"),
  join(SRC, "components", "network"),
  ...["home", "decisions", "inventory", "orders", "diagnostics", "data", "upload", "network", "access"]
    .map((route) => join(SRC, "app", route)),
];

function sources(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry !== "__tests__") sources(path, out);
    } else if (/\.tsx?$/.test(path)) out.push(path);
  }
  return out;
}

function inScope(): string[] {
  return SCOPE.flatMap((dir) => {
    try { return statSync(dir).isDirectory() ? sources(dir) : [dir]; } catch { return []; }
  });
}

/** A line of prose rather than code — these files quote the bad shape to explain it. */
const isComment = (line: string) => /^\s*(\*|\/\/|\/\*)/.test(line);
/**
 * The one legitimate reason to branch on a count: zero means something *other* than "none of
 * these", and the branch says what. `open_units === 0` is not "no units" but "this order has been
 * received", which is a different fact and a different word. Marked at the site, so the exception
 * is a sentence someone wrote rather than a pattern the check failed to see.
 */
const ALLOWED = "zero-is-a-state";

test("a number is never tested for truth before it is formatted", () => {
  // `x ? NUMBER(x)` — the same expression as both the test and the argument. A zero passed to
  // NUMBER prints "0", so the only reason to branch first is to say something else about the zero.
  const shape = /([A-Za-z_][\w.]*)\s*\?\s*(?:NUMBER|MONEY|PERCENT|COUNT|money|units)\(\s*\1\s*[,)]/g;
  const found: string[] = [];
  for (const file of inScope()) {
    const text = readFileSync(file, "utf8");
    const lines = text.split("\n");
    for (const match of text.matchAll(shape)) {
      const at = text.slice(0, match.index).split("\n").length;
      const here = lines[at - 1] ?? "";
      if (isComment(here)) continue;
      if (here.includes(ALLOWED) || (lines[at - 2] ?? "").includes(ALLOWED)) continue;
      found.push(`${file.replace(SRC, "src")}:${at} — ${match[0].trim()}`);
    }
  }
  assert.deepEqual(found, [],
    `a measured zero would render as the dash that means "not available":\n  ${found.join("\n  ")}`);
});

test("money is never quoted in a currency nobody read", () => {
  // `$${...}` in a template literal. Every currency in this product comes from the workspace.
  const shape = /\$\$\{/g;
  const found: string[] = [];
  for (const file of inScope()) {
    const text = readFileSync(file, "utf8");
    const lines = text.split("\n");
    for (const match of text.matchAll(shape)) {
      const at = text.slice(0, match.index).split("\n").length;
      if (isComment(lines[at - 1] ?? "")) continue;
      found.push(`${file.replace(SRC, "src")}:${at}`);
    }
  }
  assert.deepEqual(found, [], `a hard currency symbol:\n  ${found.join("\n  ")}`);
});

test("the scan actually reaches the files it claims to", () => {
  // Without this the two tests above pass on an empty list the day a path is renamed.
  const files = inScope();
  assert.ok(files.length > 30, `only ${files.length} files in scope`);
  for (const must of ["lib/zaad/product.ts", "components/workspace/Table.tsx",
                      "lib/network/attention.ts", "app/inventory/page.tsx"]) {
    assert.ok(files.some((f) => f.endsWith(must.replaceAll("/", require("node:path").sep))),
              `${must} is not being scanned`);
  }
});
