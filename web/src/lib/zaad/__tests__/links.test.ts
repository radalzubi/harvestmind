/**
 * Every query parameter this product links with must be read by the page it links to.
 *
 * Two buttons labelled "In the network" pointed at `/network?q=<id>`. The twin reads `node`,
 * `edge`, `sku` and `view`; **nothing reads `q`**, so both opened the canvas at whatever it would
 * have shown anyway — a link that looks like it worked, on a product whose whole claim is that
 * every object leads somewhere real. Nothing in the type system or the build could see it: a
 * string containing a URL is just a string.
 *
 * This is the cheapest of the checks §11 proposes, and it is a static one: walk the source for
 * internal links carrying parameters, and for each, assert the route's own page reads it. "Its
 * own" matters — a repo-wide search would have passed `/network?q=`, because `q` is read by
 * Inventory.
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const SRC = join(process.cwd(), "src");

/** Paths served by the API rather than the app router; they are built in `lib/api.ts`. */
const API_PREFIXES = [
  "/assistant/", "/backtest/", "/diagnostics/summary", "/forecasts/", "/fmcg/", "/pool/",
  "/reports/",
];

/**
 * Known dead parameters, kept visible rather than silenced.
 *
 * Both are on the marketing site, which this pass did not touch: `(site)/get-started/page.tsx`
 * reads neither, so the two links that carry them are decoration. They are listed here so the
 * check can run over the whole tree — an allowlist entry is a record, an exclusion is a silence.
 */
const KNOWN_DEAD = new Set(["/get-started?mode", "/get-started?sector"]);

function sources(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      if (entry !== "__tests__") sources(path, out);
    } else if (/\.tsx?$/.test(path)) out.push(path);
  }
  return out;
}

/** `app/foo/bar/page.tsx`, including inside a route group like `(site)`. */
function pageFor(route: string): string | null {
  const direct = join(SRC, "app", route, "page.tsx");
  if (existsSync(direct)) return direct;
  const appDir = join(SRC, "app");
  for (const entry of readdirSync(appDir)) {
    if (!entry.startsWith("(")) continue;
    const grouped = join(appDir, entry, route, "page.tsx");
    if (existsSync(grouped)) return grouped;
  }
  return null;
}

function linkedParams(): Map<string, string> {
  const first = /["'`](\/(?!api\/)[a-z0-9][a-z0-9/\-]*)\?([a-zA-Z_]+)=/g;
  const later = /["'`](\/(?!api\/)[a-z0-9][a-z0-9/\-]*)\?[^"'`]*?&([a-zA-Z_]+)=/g;
  const found = new Map<string, string>();
  for (const file of sources(SRC)) {
    const text = readFileSync(file, "utf8");
    for (const pattern of [first, later]) {
      for (const match of text.matchAll(pattern)) {
        const key = `${match[1]}?${match[2]}`;
        if (!found.has(key)) found.set(key, file);
      }
    }
  }
  return found;
}

test("every parameter a link carries is read by the page it points at", () => {
  const dead: string[] = [];
  let checked = 0;
  for (const [key, from] of linkedParams()) {
    const [route, param] = key.split("?");
    if (API_PREFIXES.some((prefix) => route.startsWith(prefix))) continue;
    const page = pageFor(route);
    if (!page) continue;
    checked += 1;
    if (KNOWN_DEAD.has(key)) continue;
    if (!new RegExp(`get\\("${param}"\\)`).test(readFileSync(page, "utf8"))) {
      dead.push(`${key} — linked from ${from.replace(SRC, "src")}, not read by ${page.replace(SRC, "src")}`);
    }
  }
  assert.deepEqual(dead, [], `a link carries a parameter its destination ignores:\n  ${dead.join("\n  ")}`);
  assert.ok(checked > 12, `only ${checked} links were checked; the scan found nothing to check`);
});

test("the workspace's own deep links are all live", () => {
  // The ones a colleague is actually sent, named so a regression says which broke.
  const must: Array<[string, string]> = [
    ["/network", "node"], ["/network", "sku"], ["/network", "view"], ["/network", "edge"],
    ["/inventory", "sku"], ["/inventory", "q"], ["/inventory", "supplier"], ["/inventory", "cover"],
    ["/orders", "po"], ["/orders", "tab"], ["/orders", "poq"], ["/orders", "postate"],
    ["/decisions", "decision"], ["/data", "dataset"], ["/upload/confirm", "session"],
    ["/orders/new", "amend"], ["/orders/new", "sku"], ["/orders/new", "supplier"],
  ];
  for (const [route, param] of must) {
    const page = pageFor(route);
    assert.ok(page, `no page for ${route}`);
    assert.match(readFileSync(page, "utf8"), new RegExp(`get\\("${param}"\\)`),
                 `${route} does not read ${param}`);
  }
});

test("the known dead links are still the only ones, and still dead", () => {
  // If someone wires these up, this test says so rather than leaving a stale allowlist behind.
  for (const key of KNOWN_DEAD) {
    const [route, param] = key.split("?");
    const page = pageFor(route);
    assert.ok(page, `${route} has no page at all now — update KNOWN_DEAD`);
    assert.doesNotMatch(readFileSync(page, "utf8"), new RegExp(`get\\("${param}"\\)`),
                        `${key} is read now; remove it from KNOWN_DEAD`);
  }
});
