import type { NextConfig } from "next";

/** Workspace and operational routes are never indexed, whatever robots.txt says. */
const PRIVATE = ["upload", "inventory", "atp", "backtest", "data-quality", "forecasts", "loss", "overview", "partners",
  "performance", "recommendations", "reports", "supply-risk", "traceability", "access", "admin", "welcome", "state", "fmcg", "zaad", "api", "network"];

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    // One canonical host: www and any other alias collapse onto the apex over https.
    return [{ source: "/:path*", has: [{ type: "host", value: "www.zaadsupply.com" }], destination: "https://zaadsupply.com/:path*", permanent: true }];
  },
  async headers() {
    return PRIVATE.map((p) => ({ source: `/${p}/:path*`, headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] }))
      .concat(PRIVATE.map((p) => ({ source: `/${p}`, headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] })));
  },
};

export default nextConfig;
