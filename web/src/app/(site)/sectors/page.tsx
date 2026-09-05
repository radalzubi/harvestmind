import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "Sectors — zaad" };

const SECTORS = [
  { slug: "produce", title: "Fresh produce", lead: "Days of shelf life, weekly buying, waste that shows up as margin you never see.",
    files: ["Product catalog", "Supplier deliveries", "Inventory lots", "Buyer orders", "Waste and spoilage adjustments"],
    gets: ["Inventory risk by lot age", "Available-to-promise by day", "Supplier reliability and lead-time spread", "A rolling-origin benchmark of your buying"] },
  { slug: "meats", title: "Meat and seafood", lead: "Cold chain, frozen and fresh side by side, and lots that must be traceable end to end.",
    files: ["Product catalog", "Supplier deliveries", "Inventory lots", "Buyer orders", "Waste and write-offs"],
    gets: ["Lot-level traceability", "Inventory risk by remaining life", "Supplier lead-time reliability", "A benchmark of your buying policy"] },
  { slug: "commercial", title: "Commercial goods", lead: "Cases, layers and pallets, promotions, minimum orders, and lanes that can close overnight.",
    files: ["SKU master", "Customer orders", "Purchase orders", "Goods received", "Stock counts", "Supplier list"],
    gets: ["Your incumbent policy per SKU", "Gated comparison with a conservative lower bound", "Lane risk from public chokepoint and port signals", "A purchase plan when, and only when, it is proven"] },
];

export default function SectorsPage() {
  return (
    <>
      <section className="page-hero">
        <div className="wrap">
          <Reveal><p className="eyebrow">Sectors</p></Reveal>
          <Reveal delay={0.05}><h1 className="display sm">Three kinds of importer. One honest method.</h1></Reveal>
          <Reveal delay={0.1}><p className="lede">The files differ, the shelf lives differ, the lanes differ. The rule is the same: nothing changes your orders until your own history says it should.</p></Reveal>
        </div>
      </section>
      {SECTORS.map((s, i) => (
        <section key={s.slug} className={i % 2 ? "section section-dark" : "section"} id={s.slug}>
          <div className="wrap split">
            <Reveal>
              <p className="eyebrow">{s.title}</p>
              <h2 className="h2">{s.lead}</h2>
              <Link href={`/get-started?sector=${s.slug}`} className="btn btn-primary" style={{ marginTop: 20 }}>Start with {s.title.toLowerCase()} <ArrowRight size={14} /></Link>
            </Reveal>
            <Reveal delay={0.1} className="two-lists">
              <div><h4>You upload</h4><ul>{s.files.map((f) => <li key={f}>{f}</li>)}</ul></div>
              <div><h4>You get</h4><ul>{s.gets.map((f) => <li key={f}>{f}</li>)}</ul></div>
            </Reveal>
          </div>
        </section>
      ))}
    </>
  );
}
