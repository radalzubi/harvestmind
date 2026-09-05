import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "About — zaad" };

export default function AboutPage() {
  return (
    <>
      <section className="page-hero">
        <div className="wrap">
          <Reveal><p className="eyebrow">About us</p></Reveal>
          <Reveal delay={0.05}><h1 className="display sm">Zaad means provisions.</h1></Reveal>
          <Reveal delay={0.1}><p className="lede">In Arabic, zaad is what you carry for the road. We build for the people who carry it for everyone else: the importers and distributors whose buying decisions decide whether shelves are full, and at what cost.</p></Reveal>
        </div>
      </section>
      <section className="section">
        <div className="wrap split">
          <Reveal><h2 className="h2">Why we started</h2></Reveal>
          <Reveal delay={0.08} className="prose">
            <p>Distributors in Jordan and the wider region buy across lanes that can change in a week: a strait slows, a port backs up, a supplier ships short. The tools sold to them either forecast confidently and optimise against the forecast, or hand them a dashboard and leave the decision where it was.</p>
            <p>We wanted something narrower and more honest. Read how a business actually orders. Estimate the state its suppliers and lanes are in. Change its orders only when its own history shows the change would have paid, and say so plainly when it would not.</p>
            <p>That is the whole product. It is built in Amman, and it is in pilot with a small number of distributors who let us test it on their real files.</p>
          </Reveal>
        </div>
      </section>
      <section className="section section-dark">
        <div className="wrap">
          <Reveal><p className="eyebrow">What we hold ourselves to</p></Reveal>
          <Stagger className="grid3">
            {[
              ["No forecast of savings", "We publish backtests on your data, never a promised percentage."],
              ["Negative results stay", "When a method loses to your policy, that result is kept and reported, not tuned away."],
              ["Your data is not our asset", "Vaults are isolated and pseudonymised. We do not pool your files to sell insight to anyone else."],
            ].map(([t, b]) => <Item key={t} className="feature dark"><h3>{t}</h3><p>{b}</p></Item>)}
          </Stagger>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <Reveal className="cta-band">
            <h2 className="h2">Talk to us.</h2>
            <p className="lede">If you import what you sell and want to see the diagnostic on your own history, we would like to hear from you.</p>
            <div className="cta-row"><Link href="/contact" className="btn btn-primary btn-lg">Contact <ArrowRight size={16} /></Link></div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
