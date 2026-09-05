import type { Metadata } from "next";
import Link from "next/link";
import { SectorPicker } from "@/components/SectorPicker";

export const metadata: Metadata = {
  title: "Zaad Supply",
  description: "Purchasing decisions for businesses that import what they sell, safe by construction.",
};

export default function Landing() {
  return (
    <main className="land">
      <header className="land-top">
        <div className="land-brand"><span className="land-mark">Z</span> Zaad Supply</div>
        <nav className="land-nav">
          <Link href="/access">I have a workspace key</Link>
        </nav>
      </header>

      <section className="land-hero">
        <p className="land-eyebrow">Purchasing decisions for businesses that import what they sell</p>
        <h1>How much to buy, and when, without ever making your buying worse.</h1>
        <p className="land-lede">
          Upload a year of purchase orders, receipts, sales and stock counts. You get how you order today as read from
          your own history, what a safe optimizer would have done on that same history with a conservative lower bound,
          and the risk on your supply lanes right now. If the honest answer is &ldquo;no material improvement&rdquo;,
          that is what it says.
        </p>
      </section>

      <SectorPicker />

      <section className="land-trust">
        <h2>Your data stays in a vault we do not open</h2>
        <div className="land-trust-grid">
          <div><b>Pseudonymised on arrival.</b> Item, supplier and customer codes become keyed hashes the moment a file lands; names and contacts are dropped. Nobody, including us, sees a real code.</div>
          <div><b>One vault per workspace.</b> Your files live in their own isolated database, reachable only with your key. There is no administrator screen that shows a workspace&rsquo;s data.</div>
          <div><b>Nothing is promised.</b> Every number is a backtest on your own history against your own policy, with every assumption listed. No forecast of savings, ever.</div>
          <div><b>The optimizer is gated.</b> It changes your orders only when it can show, on your own past, that it would have done better. Otherwise it keeps your policy and says why.</div>
        </div>
      </section>

      <footer className="land-foot">
        <span>Zaad Supply · Amman</span>
        <Link href="/access">Reconnect with a key</Link>
      </footer>
    </main>
  );
}
