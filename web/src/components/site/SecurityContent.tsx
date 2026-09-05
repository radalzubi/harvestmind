"use client";
import { Reveal, Stagger, Item } from "./Reveal";
import { useLocale } from "@/lib/i18n";

export function SecurityContent() {
  const { t } = useLocale(); const c = t.security;
  return (
    <>
      <section className="page-hero"><div className="wrap">
        <Reveal><p className="eyebrow">{c.eyebrow}</p></Reveal>
        <Reveal delay={0.05}><h1 className="display sm">{c.h1}</h1></Reveal>
        <Reveal delay={0.1}><p className="lede">{c.lede}</p></Reveal>
      </div></section>
      <section className="section"><div className="wrap">
        <Stagger className="grid2">{c.points.map(([tt, b]) => <Item key={tt} className="feature"><h3>{tt}</h3><p>{b}</p></Item>)}</Stagger>
      </div></section>
      <section className="section"><div className="wrap"><Reveal className="note">
        <p><b>{c.noteTitle}</b> {c.note} <a href="mailto:hello@zaadsupply.com">hello@zaadsupply.com</a>.</p>
      </Reveal></div></section>
    </>
  );
}
