"use client";
import Link from "next/link";
import { useRef } from "react";
import { ArrowRight } from "lucide-react";
import { motion, useScroll, useSpring } from "motion/react";
import { Reveal, Stagger, Item } from "../Reveal";
import { PageAtmos } from "../PageAtmos";
import { useLocale } from "@/lib/i18n";
import { ActionSpace, AllocatePanel, ApprovalPanel, BeforeAfter, DecisionLab, DisruptionControls, IncumbentFirst, InventoryBars, ModeCards, NetworkMap, RecoveryStrip, SimProvider, SkuTable, UncertaintyLab } from "./HowItWorksLab";

function Head({ eyebrow, h2, lede, dark }: { eyebrow: string; h2: string; lede: string; dark?: boolean }) {
  return (
    <div className={"hiw-head" + (dark ? " dark" : "")}>
      <Reveal><p className="eyebrow">{eyebrow}</p></Reveal>
      <Reveal delay={0.05}><h2 className="h2">{h2}</h2></Reveal>
      <Reveal delay={0.1}><p className="lede">{lede}</p></Reveal>
    </div>
  );
}

/** Thin scroll progress line under the nav; the page is one continuous simulation. Always rendered
 *  (so server and client markup match); hidden by CSS under prefers-reduced-motion. */
function Progress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 120, damping: 30, mass: .3 });
  return <motion.div className="hiw-progress" style={{ scaleX }} aria-hidden />;
}

export function HowItWorks() {
  const { t } = useLocale();
  const c = t.hiw;
  const firstRef = useRef<HTMLElement>(null);
  const start = () => firstRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  return (
    <SimProvider>
      <Progress />
      <section className="page-hero hiw-hero"><PageAtmos /><div className="wrap">
        <Reveal><p className="eyebrow">{c.eyebrow}</p></Reveal>
        <Reveal delay={0.05}><h1 className="display sm">{c.h1}</h1></Reveal>
        <Reveal delay={0.1}><p className="lede">{c.lede}</p></Reveal>
        <Reveal delay={0.15}><div className="cta-row">
          <button type="button" className="btn btn-primary btn-lg" onClick={start}>{c.start} <ArrowRight size={16} className="dir-icon dir-down" /></button>
          <Link href="/get-started" className="btn btn-ghost btn-lg">{c.open}</Link>
        </div><p className="hiw-hint">{c.scrollHint} <span className="hiw-illustrative-inline">{c.illustrative}</span></p></Reveal>
      </div></section>

      <section className="section hiw-section" ref={firstRef} id="reads"><div className="wrap">
        <Head eyebrow={c.reads.eyebrow} h2={c.reads.h2} lede={c.reads.lede} />
        <div className="hiw-reads">
          <Stagger className="stages">
            {c.reads.items.map(([title, body], i) => (
              <Item key={title} className="stage"><span className="stage-tag">0{i + 1}</span><div><h3>{title}</h3><p>{body}</p></div></Item>
            ))}
          </Stagger>
          <Reveal className="hiw-not"><h4>{c.reads.notTitle}</h4><ul>{c.reads.not.map((x) => <li key={x}>{x}</li>)}</ul></Reveal>
        </div>
      </div></section>

      <section className="section section-dark hiw-section"><div className="wrap">
        <Head eyebrow={c.privacy.eyebrow} h2={c.privacy.h2} lede={c.privacy.lede} dark />
        <Stagger className="hiw-privacy">
          {c.privacy.points.map(([title, body]) => <Item key={title} className="hiw-privacy-point"><h3>{title}</h3><p>{body}</p></Item>)}
        </Stagger>
        <Reveal><Link href="/security" className="hiw-link">{c.privacy.link} <ArrowRight size={14} className="dir-icon" /></Link></Reveal>
      </div></section>

      <section className="section hiw-section" id="network"><div className="wrap">
        <Head eyebrow={c.network.eyebrow} h2={c.network.h2} lede={c.network.lede} />
        <Reveal><NetworkMap /></Reveal>
        <Reveal><p className="hiw-note wide">{c.network.note}</p></Reveal>
      </div></section>

      <section className="section hiw-section" id="uncertainty"><div className="wrap">
        <Head eyebrow={c.uncertainty.eyebrow} h2={c.uncertainty.h2} lede={c.uncertainty.lede} />
        <Reveal><UncertaintyLab /></Reveal>
      </div></section>

      <section className="section section-dark hiw-section" id="decision"><div className="wrap">
        <Head eyebrow={c.lab.eyebrow} h2={c.lab.h2} lede={c.lab.lede} dark />
        <Reveal><DecisionLab /></Reveal>
      </div></section>

      <section className="section hiw-section" id="incumbent"><div className="wrap">
        <Head eyebrow={c.incumbent.eyebrow} h2={c.incumbent.h2} lede={c.incumbent.lede} />
        <Reveal><IncumbentFirst /></Reveal>
      </div></section>

      <section className="section hiw-section hiw-modes" id="modes"><div className="wrap">
        <Head eyebrow={c.modes.eyebrow} h2={c.modes.h2} lede={c.modes.lede} />
        <Reveal><DisruptionControls /></Reveal>
        <Reveal><ModeCards /></Reveal>
        <div className="hiw-modes-grid">
          <Reveal><SkuTable /></Reveal>
          <Reveal delay={0.05}><InventoryBars /></Reveal>
        </div>
      </div></section>

      <section className="section hiw-section" id="allocate"><div className="wrap split">
        <Head eyebrow={c.allocate.eyebrow} h2={c.allocate.h2} lede={c.allocate.lede} />
        <Reveal><AllocatePanel /></Reveal>
      </div></section>

      <section className="section hiw-section" id="recover"><div className="wrap split">
        <Head eyebrow={c.recover.eyebrow} h2={c.recover.h2} lede={c.recover.lede} />
        <Reveal><RecoveryStrip /></Reveal>
      </div></section>

      <section className="section hiw-section" id="compare"><div className="wrap">
        <Head eyebrow={c.compare.eyebrow} h2={c.compare.h2} lede={c.compare.lede} />
        <Reveal><BeforeAfter /></Reveal>
      </div></section>

      <section className="section section-dark hiw-section" id="forecast"><div className="wrap">
        <Head eyebrow={c.forecast.eyebrow} h2={c.forecast.h2} lede={c.forecast.lede} dark />
        <Stagger className="hiw-privacy">
          {c.forecast.points.map(([title, body]) => <Item key={title} className="hiw-privacy-point"><h3>{title}</h3><p>{body}</p></Item>)}
        </Stagger>
      </div></section>

      <section className="section hiw-section" id="actions"><div className="wrap">
        <Head eyebrow={c.actions.eyebrow} h2={c.actions.h2} lede={c.actions.lede} />
        <Reveal><ActionSpace /></Reveal>
      </div></section>

      <section className="section hiw-section" id="approval"><div className="wrap split">
        <Head eyebrow={c.approval.eyebrow} h2={c.approval.h2} lede={c.approval.lede} />
        <Reveal><ApprovalPanel /></Reveal>
      </div></section>

      <section className="section"><div className="wrap">
        <Reveal className="cta-band">
          <h2 className="h2">{c.cta.h2}</h2><p className="lede">{c.cta.lede}</p>
          <div className="cta-row">
            <Link href="/get-started" className="btn btn-primary btn-lg">{c.cta.diagnostic} <ArrowRight size={16} className="dir-icon" /></Link>
            <Link href="/get-started" className="btn btn-ghost btn-lg">{c.cta.open}</Link>
          </div>
        </Reveal>
      </div></section>
    </SimProvider>
  );
}
