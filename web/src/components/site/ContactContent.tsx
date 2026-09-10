"use client";
import Link from "next/link";
import { Reveal } from "./Reveal";
import { useLocale } from "@/lib/i18n";
import { PageAtmos } from "./PageAtmos";

export function ContactContent() {
  const { t } = useLocale(); const c = t.contact;
  return (
    <section className="page-hero tall"><PageAtmos /><div className="wrap split">
      <Reveal><p className="eyebrow">{c.eyebrow}</p><h1 className="display sm">{c.h1}</h1><p className="lede">{c.lede}</p></Reveal>
      <Reveal delay={0.1} className="contact-card">
        <h4>{c.email}</h4><a className="contact-big" href="mailto:hello@zaadsupply.com" dir="ltr">hello@zaadsupply.com</a>
        <h4>{c.based}</h4><p>{c.city}</p>
        <h4>{c.haveKey}</h4><p><Link href="/get-started?mode=key">{c.enterHere}</Link> {c.straight}</p>
      </Reveal>
    </div></section>
  );
}
