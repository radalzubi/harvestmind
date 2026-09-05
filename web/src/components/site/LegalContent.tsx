"use client";
import { Reveal } from "./Reveal";
import { useLocale } from "@/lib/i18n";

export function LegalContent({ kind }: { kind: "privacy" | "terms" }) {
  const { t } = useLocale(); const c = t[kind];
  return (
    <section className="page-hero"><div className="wrap doc">
      <Reveal><p className="eyebrow">{c.eyebrow}</p><h1 className="h1">{c.h1}</h1><p className="muted">{c.updated}</p></Reveal>
      <Reveal delay={0.05} className="prose">
        {c.sections.map(([h, b]) => (<div key={h}><h3>{h}</h3><p>{b}</p></div>))}
      </Reveal>
    </div></section>
  );
}
