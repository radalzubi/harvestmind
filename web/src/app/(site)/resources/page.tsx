import type { Metadata } from "next";
import Link from "next/link";
import { JsonLd } from "@/components/site/JsonLd";
import { ARTICLES } from "@/lib/resources";
import { breadcrumbJsonLd, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Resources: Inventory Optimization and Supply Resilience for Distributors",
  description: "Short, sourced guides for distributors and importers on inventory optimization, safety stock, supplier variability, multi-echelon planning and resilience under supply disruption.",
  path: "/resources",
});

export default function ResourcesIndex() {
  return (
    <>
      <JsonLd data={breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Resources", path: "/resources" }])} />
      <section className="section">
        <div className="wrap">
          <p className="eyebrow">Resources</p>
          <h1 className="display sm">Inventory optimization and supply resilience, without the sales pitch.</h1>
          <p className="lede">Written for the people who place purchase orders at distributors and importers. Every article cites its sources and says what it does not know.</p>
          <div className="resource-grid">
            {ARTICLES.map((a) => (
              <Link key={a.slug} href={`/resources/${a.slug}`} className="resource-card">
                <h2>{a.heading}</h2>
                <p>{a.description}</p>
                <span className="resource-meta">{a.readingMinutes} min read · updated {a.modified}</span>
              </Link>
            ))}
          </div>
          <p className="resource-foot">
            Want to see these ideas on your own history? <Link href="/how-it-works">See how ZAAD works</Link> or <Link href="/get-started">open a workspace</Link>.
          </p>
        </div>
      </section>
    </>
  );
}
