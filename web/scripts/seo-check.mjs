#!/usr/bin/env node
/**
 * SEO checks against a running site (local `next start` or production).
 *
 *   node scripts/seo-check.mjs --base http://localhost:3000
 *   node scripts/seo-check.mjs --base https://zaadsupply.com
 *
 * Every public page: HTTP 200, exactly one <h1>, a title, a meta description, a self-referencing
 * canonical on the expected host, no noindex, og:site_name and og:image, and structured data
 * present in the initial HTML. Homepage: WebSite and Organization JSON-LD with the brand name,
 * alternate names and a logo. Private routes: X-Robots-Tag noindex. robots.txt and sitemap.xml
 * exist and agree. Favicon and share image respond. Exit code 1 on any failure.
 */
const args = process.argv.slice(2);
const base = (args[args.indexOf("--base") + 1] || "http://localhost:3000").replace(/\/$/, "");
const expectHost = args.includes("--expect-host") ? args[args.indexOf("--expect-host") + 1] : "https://zaadsupply.com";

const PUBLIC = ["/", "/product", "/sectors", "/about", "/security", "/contact", "/resources", "/privacy", "/terms",
  "/resources/what-is-inventory-optimization-for-distributors", "/resources/lean-protect-allocate-recover"];
const PRIVATE = ["/upload", "/inventory", "/admin", "/reports", "/zaad/network"];

let failures = 0;
const ok = (cond, msg) => { if (!cond) { failures += 1; console.log("  FAIL", msg); } else console.log("  ok  ", msg); };
const attr = (html, re) => { const m = html.match(re); return m ? m[1] : null; };
const all = (html, re) => [...html.matchAll(re)].map((m) => m[1]);

async function get(path, opts = {}) {
  const res = await fetch(base + path, { redirect: "manual", headers: { "user-agent": "Mozilla/5.0 (compatible; seo-check)" }, ...opts });
  return { status: res.status, headers: res.headers, text: await res.text() };
}

const seen = { titles: new Set(), descriptions: new Set() };
for (const path of PUBLIC) {
  console.log(`\n${path}`);
  const { status, headers, text } = await get(path);
  ok(status === 200, `HTTP ${status}`);
  const title = attr(text, /<title>([^<]*)<\/title>/);
  ok(Boolean(title && title.trim()), `title: ${title}`);
  ok(!seen.titles.has(title), "title is unique"); seen.titles.add(title);
  const description = attr(text, /<meta name="description" content="([^"]*)"/);
  ok(Boolean(description && description.length > 40), `description (${description?.length ?? 0} chars)`);
  ok(!seen.descriptions.has(description), "description is unique"); seen.descriptions.add(description);
  const canonical = attr(text, /<link rel="canonical" href="([^"]*)"/);
  const expected = path === "/" ? `${expectHost}/` : `${expectHost}${path}`;
  // The root canonical may be emitted without the trailing slash; Google treats both as the same origin root.
  ok(canonical === expected || (path === "/" && canonical === expectHost), `canonical ${canonical} == ${expected}`);
  const h1s = all(text, /<h1[^>]*>([\s\S]*?)<\/h1>/g);
  ok(h1s.length === 1, `exactly one h1 (${h1s.length})`);
  const robots = attr(text, /<meta name="robots" content="([^"]*)"/);
  ok(!(robots && /noindex/.test(robots)) && !/noindex/.test(headers.get("x-robots-tag") || ""), "indexable (no noindex)");
  ok(attr(text, /<meta property="og:site_name" content="([^"]*)"/) === "ZAAD", "og:site_name is ZAAD");
  ok(Boolean(attr(text, /<meta property="og:image" content="([^"]*)"/)), "og:image present");
  ok(/<html lang="en"/.test(text), "html lang=en server-rendered");
  const ld = all(text, /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g).map((s) => JSON.parse(s.replace(/\\u003c/g, "<")));
  ok(ld.length >= 1, `JSON-LD blocks: ${ld.length}`);
  if (path === "/") {
    const site = ld.find((x) => x["@type"] === "WebSite");
    const org = ld.find((x) => x["@type"] === "Organization");
    ok(site && site.name === "ZAAD" && Array.isArray(site.alternateName) && site.alternateName.includes("ZAAD Supply") && site.url === `${expectHost}/`, "WebSite JSON-LD: name ZAAD, alternateName, canonical url");
    ok(org && org.name === "ZAAD" && org.url === `${expectHost}/` && org.logo && /zaad-logo-512\.png$/.test(org.logo.url) && typeof org.description === "string", "Organization JSON-LD: name, url, logo, description");
    ok(org && !org.address && !org.telephone, "Organization JSON-LD carries no fabricated address or phone");
    ok(/ZAAD/.test(text.replace(/<script[\s\S]*?<\/script>/g, "")), "visible homepage text mentions ZAAD");
    ok(/<link rel="icon"[^>]*href="\/favicon\.ico/.test(text), "favicon link present");
  } else {
    ok(ld.some((x) => x["@type"] === "BreadcrumbList"), "BreadcrumbList JSON-LD present");
  }
  if (path.startsWith("/resources/")) ok(ld.some((x) => x["@type"] === "Article" && x.headline), "Article JSON-LD present");
}

console.log("\nprivate routes");
for (const path of PRIVATE) {
  const { status, headers } = await get(path);
  ok(/noindex/.test(headers.get("x-robots-tag") || ""), `${path} X-Robots-Tag noindex (HTTP ${status})`);
}

console.log("\nrobots and sitemap");
const robots = await get("/robots.txt");
ok(robots.status === 200 && /User-Agent: \*/i.test(robots.text) && /Allow: \//i.test(robots.text), "robots.txt allows public crawl");
ok(/Disallow: \/upload/.test(robots.text) && /Disallow: \/api/.test(robots.text), "robots.txt disallows workspace and api");
ok(new RegExp(`Sitemap: ${expectHost.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}/sitemap\\.xml`).test(robots.text), "robots.txt names the sitemap");
const sitemap = await get("/sitemap.xml");
ok(sitemap.status === 200 && /<urlset/.test(sitemap.text), "sitemap.xml is a urlset");
const locs = all(sitemap.text, /<loc>([^<]*)<\/loc>/g);
ok(locs.every((u) => u.startsWith(expectHost)), `sitemap URLs on ${expectHost} (${locs.length} urls)`);
ok(locs.includes(`${expectHost}/`) && locs.includes(`${expectHost}/product`) && locs.includes(`${expectHost}/resources`), "sitemap includes home, product, resources");
ok(!locs.some((u) => /\/(upload|admin|api|zaad)\b/.test(u.replace(expectHost, ""))), "sitemap excludes private routes");
ok(all(sitemap.text, /<lastmod>([^<]*)<\/lastmod>/g).length === locs.length, "every sitemap URL has lastmod");

console.log("\nassets");
for (const asset of ["/favicon.ico", "/icon.svg", "/apple-icon.png", "/icon-192.png", "/brand/zaad-logo-512.png", "/og/zaad-supply-network.png"]) {
  const res = await fetch(base + asset, { method: "GET" });
  ok(res.status === 200 && /image\//.test(res.headers.get("content-type") || ""), `${asset} ${res.status} ${res.headers.get("content-type")}`);
}

console.log(failures ? `\n${failures} failure(s)` : "\nall checks passed");
process.exit(failures ? 1 : 0);
