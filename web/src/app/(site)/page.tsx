import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "@/components/site/Reveal";
import { Hero } from "@/components/site/Hero";

export const metadata: Metadata = {
  title: "zaad — purchasing decisions for businesses that import what they sell",
  description: "Upload a year of history. See how you order today, what a gated optimizer would have done on that same history, and the risk on your supply lanes now.",
};

const STEPS = [
  { n: "01", title: "Upload a year of history", body: "Purchase orders, receipts, sales and stock counts, straight from your ERP or spreadsheets. Codes are pseudonymised the moment a file lands." },
  { n: "02", title: "We read how you order today", body: "Your reorder points, order sizes and cadence per product, inferred from your own history. That is the policy every candidate has to beat." },
  { n: "03", title: "The optimizer proves itself, or stays quiet", body: "Candidates are backtested on your past under many demand and lead-time scenarios. One is adopted only if its conservative lower bound beats you." },
];

const SECTORS = [
  { slug: "produce", title: "Fresh produce", body: "Fruit, vegetables, and anything with a shelf life measured in days." },
  { slug: "meats", title: "Meat and seafood", body: "Fresh and frozen, cold chain, lot-level traceability." },
  { slug: "commercial", title: "Commercial goods", body: "Packaged goods, household products and raw materials, ordered in cases and pallets." },
];

export default function Home() {
  return (
    <>
      <Hero />

      <section className="section" id="how">
        <div className="wrap">
          <Reveal><p className="eyebrow">How it works</p></Reveal>
          <Reveal delay={0.05}><h2 className="h2">Three steps. No promises you cannot check.</h2></Reveal>
          <Stagger className="steps">
            {STEPS.map((s) => (
              <Item key={s.n} className="step">
                <span className="step-n">{s.n}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      <section className="section section-dark">
        <div className="wrap">
          <Reveal><p className="eyebrow">What you get</p></Reveal>
          <div className="split">
            <Reveal delay={0.05}>
              <h2 className="h2">One honest report on your own numbers.</h2>
              <p className="lede">Every figure is a backtest on your history against your own policy, with every assumption listed. If the honest answer is “no material improvement”, that is what it says.</p>
            </Reveal>
            <Stagger className="list-cards">
              {[
                ["Your current policy", "Reorder points, order sizes and cadence per product, as read from what you actually did."],
                ["A gated comparison", "What a safe optimizer would have done on the same history, with a conservative lower bound, not a best case."],
                ["Lane risk today", "Chokepoint traffic, port calls and freight indicators for the lanes you actually use, with the source of every signal."],
                ["A purchase plan", "Only when the optimizer proved itself. Otherwise your plan, kept, with the reason."],
              ].map(([t, b]) => (
                <Item key={t} className="list-card"><h3>{t}</h3><p>{b}</p></Item>
              ))}
            </Stagger>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <Reveal><p className="eyebrow">Sectors</p></Reveal>
          <Reveal delay={0.05}><h2 className="h2">Built for three kinds of importer.</h2></Reveal>
          <Stagger className="grid3">
            {SECTORS.map((s) => (
              <Item key={s.slug}>
                <Link href={`/get-started?sector=${s.slug}`} className="sector-card">
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                  <span className="sector-card-go">Start <ArrowRight size={14} /></span>
                </Link>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <Reveal className="cta-band">
            <h2 className="h2">Your data stays in a vault we do not open.</h2>
            <p className="lede">Pseudonymised on arrival. One isolated database per workspace, reachable only with your key. No administrator screen shows a workspace’s files.</p>
            <div className="cta-row">
              <Link href="/get-started" className="btn btn-primary btn-lg">Get started <ArrowRight size={16} /></Link>
              <Link href="/security" className="btn btn-ghost btn-lg">Read how it is protected</Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
