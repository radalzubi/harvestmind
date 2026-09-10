import type { MetadataRoute } from "next";
import { PUBLIC_PAGES, absolute } from "@/lib/seo";
import { ARTICLES } from "@/lib/resources";

/** Canonical public URLs only. lastModified is the date the page content last changed. */
export default function sitemap(): MetadataRoute.Sitemap {
  const pages = PUBLIC_PAGES.map((p) => ({ url: absolute(p.path), lastModified: new Date(p.updated) }));
  const articles = ARTICLES.map((a) => ({ url: absolute(`/resources/${a.slug}`), lastModified: new Date(a.modified) }));
  return [...pages, ...articles];
}
