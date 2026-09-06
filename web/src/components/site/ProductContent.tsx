"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "./Reveal";
import { useLocale } from "@/lib/i18n";
import { PageAtmos } from "./PageAtmos";

export function ProductContent() {
  const { t } = useLocale(); const c = t.product;
  return (
    <>
      <section className="page-hero"><PageAtmos /><div className="wrap">
        <Reveal><p className="eyebrow">{c.eyebrow}</p></Reveal>
        <Reveal delay={0.05}><h1 className="display sm">{c.h1}</h1></Reveal>
        <Reveal delay={0.1}><p className="lede">{c.lede}</p></Reveal>
      </div></section>
      <section className="section"><div className="wrap">
        <Stagger className="stages">
          {c.stages.map(([tag, title, body]) => (
            <Item key={tag} className="stage"><span className="stage-tag">{tag}</span><div><h3>{title}</h3><p>{body}</p></div></Item>
          ))}
        </Stagger>
      </div></section>
      <section className="section"><div className="wrap">
        <Reveal className="cta-band">
          <h2 className="h2">{c.ctaH2}</h2><p className="lede">{c.ctaLede}</p>
          <div className="cta-row"><Link href="/get-started" className="btn btn-primary btn-lg">{c.cta} <ArrowRight size={16} className="dir-icon" /></Link></div>
        </Reveal>
      </div></section>
    </>
  );
}
