import type { Metadata } from "next";

/**
 * One brand identity for every surface Google reads: metadata, structured data, sitemap.
 * Keep these strings identical wherever the brand is described (About, footer, profiles).
 */
export const SITE_URL = "https://zaadsupply.com";
export const SITE_NAME = "ZAAD";
export const ALTERNATE_NAMES = ["ZAAD Supply", "zaadsupply.com"];
export const BRAND_DESCRIPTION =
  "ZAAD is inventory optimization and supply resilience software for distributors and importers.";
export const HOME_TITLE = "ZAAD | Inventory Optimization & Supply Resilience";
export const HOME_DESCRIPTION =
  "ZAAD helps distributors and importers optimize inventory, purchasing, sourcing and supply resilience while protecting customer service. Backtested on your own history.";
export const LOGO_URL = `${SITE_URL}/brand/zaad-logo-512.png`;
export const SHARE_IMAGE = { url: `${SITE_URL}/og/zaad-supply-network.png`, width: 1200, height: 630,
  alt: "ZAAD supply network intelligence: inventory positions and supply lanes for distributors and importers" };

/** Public, indexable pages and when their content last materially changed (ISO date). */
export const PUBLIC_PAGES: { path: string; updated: string }[] = [
  { path: "/", updated: "2026-09-06" },
  { path: "/product", updated: "2026-09-06" },
  { path: "/sectors", updated: "2026-09-06" },
  { path: "/about", updated: "2026-09-06" },
  { path: "/security", updated: "2026-09-06" },
  { path: "/contact", updated: "2026-09-06" },
  { path: "/resources", updated: "2026-09-06" },
  { path: "/privacy", updated: "2026-09-05" },
  { path: "/terms", updated: "2026-09-05" },
];

/** Workspace and operational routes: authenticated or private, never indexed. */
export const PRIVATE_PREFIXES = [
  "/upload", "/inventory", "/atp", "/backtest", "/data-quality", "/forecasts", "/loss", "/overview", "/partners",
  "/performance", "/recommendations", "/reports", "/supply-risk", "/traceability", "/access", "/admin", "/welcome",
  "/state", "/fmcg", "/zaad", "/api",
];

export function absolute(path: string): string {
  return path === "/" ? `${SITE_URL}/` : `${SITE_URL}${path}`;
}

/** Page metadata with a self-referencing canonical and matching Open Graph fields. */
export function pageMetadata(opts: { title: string; description: string; path: string; type?: "website" | "article"; noindex?: boolean }): Metadata {
  const url = absolute(opts.path);
  return {
    title: opts.title,
    description: opts.description,
    alternates: { canonical: url },
    robots: opts.noindex ? { index: false, follow: false } : { index: true, follow: true },
    openGraph: { title: opts.title, description: opts.description, url, siteName: SITE_NAME, type: opts.type ?? "website",
      locale: "en_US", images: [SHARE_IMAGE] },
    twitter: { card: "summary_large_image", title: opts.title, description: opts.description, images: [SHARE_IMAGE.url] },
  };
}

export function websiteJsonLd() {
  return { "@context": "https://schema.org", "@type": "WebSite", "@id": `${SITE_URL}/#website`,
    name: SITE_NAME, alternateName: ALTERNATE_NAMES, url: `${SITE_URL}/`, inLanguage: ["en", "ar"],
    publisher: { "@id": `${SITE_URL}/#organization` } };
}

export function organizationJsonLd() {
  // Only truthful, public facts. No address, employee count, identifiers or profiles are
  // listed until they exist publicly; add sameAs entries only for official profiles.
  return { "@context": "https://schema.org", "@type": "Organization", "@id": `${SITE_URL}/#organization`,
    name: SITE_NAME, alternateName: ALTERNATE_NAMES, url: `${SITE_URL}/`, description: BRAND_DESCRIPTION,
    logo: { "@type": "ImageObject", url: LOGO_URL, width: 512, height: 512 },
    image: LOGO_URL,
    contactPoint: [{ "@type": "ContactPoint", contactType: "sales", url: `${SITE_URL}/contact`, availableLanguage: ["en", "ar"] }],
    knowsAbout: ["inventory optimization", "supply chain resilience", "purchase order planning", "safety stock", "multi-echelon inventory optimization", "supplier lead time variability"],
    areaServed: ["Jordan", "Middle East", "United States"] };
}

export function breadcrumbJsonLd(items: { name: string; path: string }[]) {
  return { "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({ "@type": "ListItem", position: i + 1, name: item.name, item: absolute(item.path) })) };
}

export function articleJsonLd(a: { title: string; description: string; path: string; published: string; modified: string }) {
  return { "@context": "https://schema.org", "@type": "Article", headline: a.title, description: a.description,
    url: absolute(a.path), mainEntityOfPage: absolute(a.path), datePublished: a.published, dateModified: a.modified,
    inLanguage: "en", image: [SHARE_IMAGE.url], isAccessibleForFree: true,
    author: { "@type": "Organization", "@id": `${SITE_URL}/#organization`, name: SITE_NAME },
    publisher: { "@type": "Organization", "@id": `${SITE_URL}/#organization`, name: SITE_NAME, logo: { "@type": "ImageObject", url: LOGO_URL } } };
}
