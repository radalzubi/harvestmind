import type { MetadataRoute } from "next";
import { PRIVATE_PREFIXES, SITE_URL } from "@/lib/seo";

/** Public marketing pages are crawlable; workspace, admin and API routes are not. Private
 * routes also carry an X-Robots-Tag: noindex header (next.config.ts), which is what actually
 * keeps them out of results; robots.txt alone does not. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: PRIVATE_PREFIXES.map((p) => `${p}/`).concat(PRIVATE_PREFIXES) }],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
