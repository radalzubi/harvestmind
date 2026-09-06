"use client";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "./Reveal";
import { useLocale } from "@/lib/i18n";
import { PageAtmos } from "./PageAtmos";

export function SectorsContent() {
  const { t } = useLocale(); const c = t.sectorsPage;
  return (
    <>
      <section className="page-hero"><PageAtmos /><div className="wrap">
        <Reveal><p className="eyebrow">{c.eyebrow}</p></Reveal>
        <Reveal delay={0.05}><h1 className="display sm">{c.h1}</h1></Reveal>
        <Reveal delay={0.1}><p className="lede">{c.lede}</p></Reveal>
      </div></section>
      {c.items.map((s, i) => (
        <section key={s.slug} className={i % 2 ? "section section-dark" : "section"} id={s.slug}>
          <div className="wrap split">
            <Reveal>
              <p className="eyebrow">{s.title}</p>
              <h2 className="h2">{s.lead}</h2>
              <Link href={`/get-started?sector=${s.slug}`} className="btn btn-primary" style={{ marginTop: 20 }}>{c.startWith} {s.title} <ArrowRight size={14} className="dir-icon" /></Link>
            </Reveal>
            <Reveal delay={0.1} className="two-lists">
              <div><h4>{c.upload}</h4><ul>{s.files.map((f) => <li key={f}>{f}</li>)}</ul></div>
              <div><h4>{c.get}</h4><ul>{s.gets.map((f) => <li key={f}>{f}</li>)}</ul></div>
            </Reveal>
          </div>
        </section>
      ))}
    </>
  );
}
