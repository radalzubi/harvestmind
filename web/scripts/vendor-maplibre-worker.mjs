// Copies MapLibre's web worker (and the shared module it imports) into
// public/vendor so the browser can load it from a plain URL. Bundlers do not
// reliably serve `new Worker(new URL(..., import.meta.url))` from inside a
// dependency, and without its worker MapLibre parses no tiles at all.
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = join(here, "..", "node_modules", "maplibre-gl", "dist");
const out = join(here, "..", "public", "vendor");
const pkg = JSON.parse(readFileSync(join(here, "..", "node_modules", "maplibre-gl", "package.json"), "utf8"));
mkdirSync(out, { recursive: true });
for (const f of ["maplibre-gl-worker.mjs", "maplibre-gl-shared.mjs"]) {
  const src = join(dist, f);
  if (existsSync(src)) copyFileSync(src, join(out, f));
}
writeFileSync(join(out, "maplibre-gl.version.json"), JSON.stringify({ version: pkg.version, license: pkg.license }));
console.log(`vendored maplibre-gl ${pkg.version} worker into public/vendor`);
