import type { NextConfig } from "next";

/** Workspace and operational routes are never indexed, whatever robots.txt says. */
const PRIVATE = ["upload", "inventory", "atp", "backtest", "data-quality", "forecasts", "loss", "overview", "partners",
  "performance", "recommendations", "reports", "supply-risk", "traceability", "access", "admin", "welcome", "state", "fmcg", "zaad", "api",
  // the rebuilt workspace
  "home", "decisions", "network", "data", "advanced", "start"];

/**
 * Security headers for every page (security review 2026-09, SEC-012). The interface keeps the workspace
 * token in session storage, so script injection is the threat this policy is written against: scripts
 * and connections only from this origin, the API origin and the map tiles; no framing; no MIME sniffing;
 * a referrer that never carries a path. Next's own inline bootstrap scripts and the component libraries'
 * inline styles need 'unsafe-inline' (a nonce would need a middleware for every response), so the policy
 * still blocks every external script and every exfiltration target, which is where a stolen token goes.
 */
const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const MAP_ORIGIN = (() => { try { return new URL(process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "https://tiles.openfreemap.org/styles/positron").origin; } catch { return "https://tiles.openfreemap.org"; } })();
export const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  `connect-src 'self' ${API_ORIGIN} ${MAP_ORIGIN}`,
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "upgrade-insecure-requests",
].join("; ");
export const SECURITY_HEADERS = [
  { key: "Content-Security-Policy", value: CONTENT_SECURITY_POLICY },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async redirects() {
    // One canonical host: www and any other alias collapse onto the apex over https.
    return [{ source: "/:path*", has: [{ type: "host", value: "www.zaadsupply.com" }], destination: "https://zaadsupply.com/:path*", permanent: true }];
  },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }]
      .concat(PRIVATE.map((p) => ({ source: `/${p}/:path*`, headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] })))
      .concat(PRIVATE.map((p) => ({ source: `/${p}`, headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] })));
  },
};

export default nextConfig;
