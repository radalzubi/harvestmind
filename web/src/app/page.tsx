import Link from "next/link";
import type { Metadata } from "next";
import { DemoButton } from "@/components/DemoButton";

export const metadata: Metadata = {
  title: "HarvestMind",
  description: "Purchasing decisions for import-dependent distributors and producers, safe by construction.",
};

const SECTORS = [
  {
    key: "commercial",
    name: "Commercial goods",
    who: "Distributors and manufacturers of packaged goods, household products and raw materials",
    lines: [
      "Whole cases, pallets and minimum orders, in the units you buy in",
      "Real fill rates and lead times measured from your own receipts, by supplier and by lane",
      "A warning on your sea lanes weeks before your deliveries slip",
    ],
  },
  {
    key: "produce",
    name: "Fresh produce",
    who: "Produce importers, distributors, food hubs and growers",
    lines: [
      "Shelf life and spoilage priced into every order, first-expiry-first-out",
      "Yield and weather risk on the supply side, not only demand",
      "Waste and lost sales measured in your own numbers",
    ],
  },
];

export default function Landing() {
  return (
    <main className="land">
      <header className="land-top">
        <div className="land-brand"><span className="land-mark">H</span> HarvestMind</div>
        <nav className="land-nav">
          <Link href="/access">I have access</Link>
          <Link className="land-cta-sm" href="/request-access">Request access</Link>
        </nav>
      </header>

      <section className="land-hero">
        <p className="land-eyebrow">Purchasing decisions for businesses that import what they sell</p>
        <h1>How much to buy, and when, without ever making your buying worse.</h1>
        <p className="land-lede">
          Upload a year of your own purchase orders, receipts, sales and stock counts. Within a week you get three
          things: how you order today as read from your own history, what a safe optimizer would have done on that
          same history with a conservative lower bound, and the risk on your supply lanes right now. If the honest
          answer is &ldquo;no material improvement&rdquo;, that is what the report says.
        </p>
      </section>

      <section className="land-pick">
        <h2>Choose your sector</h2>
        <div className="land-cards">
          {SECTORS.map((s) => (
            <article key={s.key} className="land-card">
              <h3>{s.name}</h3>
              <p className="land-who">{s.who}</p>
              <ul>{s.lines.map((l) => <li key={l}>{l}</li>)}</ul>
              <Link className="land-cta" href={`/request-access?sector=${s.key}`}>Request access as {s.name.toLowerCase()}</Link>
            </article>
          ))}
        </div>
      </section>

      <section className="land-pick">
        <h2>Or look around first</h2>
        <p className="land-who" style={{ marginBottom: 12 }}>A shared workspace loaded with synthetic distributor data, clearly labelled as such. Nothing in it is a real company.</p>
        <DemoButton />
      </section>

      <section className="land-trust">
        <h2>Your data never becomes someone else&rsquo;s advantage</h2>
        <div className="land-trust-grid">
          <div><b>Pseudonymised before storage.</b> Item, supplier and customer codes become keyed hashes the moment a file arrives; names and contacts are dropped. Or anonymise on your own machine first, with a script we give you, and we never see a real code.</div>
          <div><b>One vault per company.</b> Your files live in their own isolated database. Nothing is pooled without your written consent, and then only lane-level aggregates.</div>
          <div><b>Nothing is promised.</b> Every number in a report is a backtest on your own history against your own policy, with the assumptions and public priors it used listed. No forecast of savings, ever.</div>
          <div><b>The optimizer is gated.</b> It changes your orders only when it can show, on your own past, that it would have done better. Otherwise it keeps your policy and says why.</div>
        </div>
      </section>

      <footer className="land-foot">
        <span>HarvestMind · Amman</span>
        <Link href="/request-access">Request access</Link>
      </footer>
    </main>
  );
}
