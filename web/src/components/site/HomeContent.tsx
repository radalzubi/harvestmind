"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "./Reveal";
import { Hero } from "./Hero";
import { useLocale } from "@/lib/i18n";

export function HomeContent() {
  const { t } = useLocale();
  const c = t.home;
  return (
    <>
      <Hero />
      <section className="section" id="how">
        <div className="wrap">
          <Reveal><p className="eyebrow">{c.howEyebrow}</p></Reveal>
          <Reveal delay={0.05}><h2 className="h2">{c.howH2}</h2></Reveal>
          <Stagger className="steps">
            {c.steps.map((s) => (
              <Item key={s.n} className="step"><span className="step-n">{s.n}</span><h3>{s.title}</h3><p>{s.body}</p></Item>
            ))}
          </Stagger>
        </div>
      </section>
      <section className="section section-dark">
        <div className="wrap">
          <Reveal><p className="eyebrow">{c.getEyebrow}</p></Reveal>
          <div className="split">
            <Reveal delay={0.05}><h2 className="h2">{c.getH2}</h2><p className="lede">{c.getLede}</p></Reveal>
            <Stagger className="list-cards">
              {c.gets.map(([tt, b]) => <Item key={tt} className="list-card"><h3>{tt}</h3><p>{b}</p></Item>)}
            </Stagger>
          </div>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <Reveal><p className="eyebrow">{c.sectorsEyebrow}</p></Reveal>
          <Reveal delay={0.05}><h2 className="h2">{c.sectorsH2}</h2></Reveal>
          <Stagger className="grid3">
            {c.sectors.map((s) => (
              <Item key={s.slug}>
                <Link href={`/get-started?sector=${s.slug}`} className="sector-card">
                  <h3>{s.title}</h3><p>{s.body}</p>
                  <span className="sector-card-go">{c.start} <ArrowRight size={14} className="dir-icon" /></span>
                </Link>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <Reveal className="cta-band">
            <h2 className="h2">{c.vaultH2}</h2>
            <p className="lede">{c.vaultLede}</p>
            <div className="cta-row">
              <Link href="/get-started" className="btn btn-primary btn-lg">{c.vaultCta} <ArrowRight size={16} className="dir-icon" /></Link>
              <Link href="/security" className="btn btn-ghost btn-lg">{c.vaultMore}</Link>
            </div>
          </Reveal>
        </div>
      </section>
    </>
  );
}
