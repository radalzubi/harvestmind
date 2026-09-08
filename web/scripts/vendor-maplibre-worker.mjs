// Copies MapLibre's web worker (and the shared module it imports) into
// public/vendor so the browser can load it from a plain URL. Bundlers do not
// reliably serve `new Worker(new URL(..., import.meta.url))` from inside a
// dependency, and without its worker MapLibre parses no tiles at all.
//
// Runs at postinstall and again at the start of `npm run build`; either run
// exits non-zero when the files cannot be produced, so a build never ships a
// map that would silently stay blank. `--check` only verifies.
import { copyFileSync, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const dist = join(root, "node_modules", "maplibre-gl", "dist");
const out = join(root, "public", "vendor");
export const FILES = ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"];
const checkOnly = process.argv.includes("--check");

function fail(msg) {
  console.error(`maplibre worker: ${msg}`);
  process.exit(1);
}

const pkgPath = join(root, "node_modules", "maplibre-gl", "package.json");
if (!existsSync(pkgPath)) fail("maplibre-gl is not installed (node_modules/maplibre-gl missing)");
const pkg = JSON.parse(readFileSync(pkgPath, "utf8"));

if (!checkOnly) {
  mkdirSync(out, { recursive: true });
  for (const f of FILES) {
    const src = join(dist, f);
    if (!existsSync(src)) fail(`${f} not found in maplibre-gl ${pkg.version}; the dist layout changed and this script needs updating`);
    copyFileSync(src, join(out, f));
  }
  writeFileSync(join(out, "maplibre-gl.version.json"), JSON.stringify({ version: pkg.version, license: pkg.license, files: FILES }));
}

// verify: every file present, non-empty, and the worker still imports the shared module we copied
for (const f of FILES) {
  const p = join(out, f);
  if (!existsSync(p) || statSync(p).size < 1000) fail(`${p} is missing or empty; run \`node scripts/vendor-maplibre-worker.mjs\``);
}
const worker = readFileSync(join(out, FILES[0]), "utf8");
const dep = worker.match(/from\s*["']\.\/([^"']+)["']/)?.[1];
if (dep && !FILES.includes(dep)) fail(`worker imports ./${dep}, which is not vendored`);
const meta = JSON.parse(readFileSync(join(out, "maplibre-gl.version.json"), "utf8"));
if (meta.version !== pkg.version) fail(`vendored ${meta.version} but maplibre-gl ${pkg.version} is installed; run \`node scripts/vendor-maplibre-worker.mjs\``);
console.log(`maplibre worker: ${checkOnly ? "verified" : "vendored"} ${pkg.version} (${FILES.join(", ")}) in public/vendor`);
