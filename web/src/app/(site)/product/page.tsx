import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "How it works — zaad" };

const STAGES = [
  ["Read", "Your history becomes a policy", "From purchase orders, receipts, sales and stock counts we infer how you order each product today: when you reorder, how much, how often, and how you react to a late supplier. That policy is the incumbent. Every candidate must beat it."],
  ["Estimate", "The state you are operating in", "Per supplier and per lane, the diagnostic asks whether the recent past looks like the normal past. Late deliveries, short shipments and demand shifts move a probability, not a switch. Public signals for your lanes, chokepoint transits, port calls, freight and fuel indices, add an outlook with its quality stated."],
  ["Backtest", "Candidates on your own past", "Each candidate optimizer is replayed through rolling windows of your history under many demand and lead-time scenarios. We keep the mean, the conservative lower bound and the worst fold, per candidate."],
  ["Gate", "Adopt only when proven", "A candidate is adopted only if its lower bound beats your policy on held-out folds. Otherwise the report keeps your plan and says exactly why. There is no forecast of savings, only what happened on your data."],
  ["Plan", "A purchase plan you can act on", "When a candidate passes, you get order quantities and timing per product with the reason for every change from your current plan, a stability cost so the plan does not churn week to week, and the lane risk that shaped it."],
];

export default function ProductPage() {
  return (
    <>
      <section className="page-hero">
        <div className="wrap">
          <Reveal><p className="eyebrow">Product</p></Reveal>
          <Reveal delay={0.05}><h1 className="display sm">A diagnostic that has to earn the right to change your orders.</h1></Reveal>
          <Reveal delay={0.1}><p className="lede">Most tools forecast and then optimise against the forecast. We start from what you already do, and only move away from it when your own history shows it would have paid.</p></Reveal>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <Stagger className="stages">
            {STAGES.map(([tag, title, body]) => (
              <Item key={tag} className="stage">
                <span className="stage-tag">{tag}</span>
                <div><h3>{title}</h3><p>{body}</p></div>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <Reveal className="cta-band">
            <h2 className="h2">Try it on a year of your files.</h2>
            <p className="lede">A private workspace opens in seconds. If the answer is “keep doing what you do”, you will hear it plainly.</p>
            <div className="cta-row"><Link href="/get-started" className="btn btn-primary btn-lg">Get started <ArrowRight size={16} /></Link></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
