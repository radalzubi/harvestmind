"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "./Reveal";
import { useLocale } from "@/lib/i18n";
import { PageAtmos } from "./PageAtmos";

export function AboutContent() {
  const { t } = useLocale(); const c = t.about;
  return (
    <>
      <section className="page-hero"><PageAtmos /><div className="wrap">
        <Reveal><p className="eyebrow">{c.eyebrow}</p></Reveal>
        <Reveal delay={0.05}><h1 className="display sm">{c.h1}</h1></Reveal>
        <Reveal delay={0.1}><p className="lede">{c.lede}</p></Reveal>
      </div></section>
      <section className="section"><div className="wrap split">
        <Reveal><h2 className="h2">{c.whyH2}</h2></Reveal>
        <Reveal delay={0.08} className="prose">{c.why.map((p) => <p key={p.slice(0, 24)}>{p}</p>)}</Reveal>
      </div></section>
      <section className="section section-dark"><div className="wrap">
        <Reveal><p className="eyebrow">{c.valuesEyebrow}</p></Reveal>
        <Stagger className="grid3">{c.values.map(([tt, b]) => <Item key={tt} className="feature dark"><h3>{tt}</h3><p>{b}</p></Item>)}</Stagger>
      </div></section>
      <section className="section"><div className="wrap">
        <Reveal className="cta-band">
          <h2 className="h2">{c.ctaH2}</h2><p className="lede">{c.ctaLede}</p>
          <div className="cta-row"><Link href="/contact" className="btn btn-primary btn-lg">{c.cta} <ArrowRight size={16} className="dir-icon" /></Link></div>
        </Reveal>
      </div></section>
    </>
  );
}
