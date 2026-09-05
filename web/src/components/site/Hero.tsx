"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useLocale } from "@/lib/i18n";

const ease = [0.22, 1, 0.36, 1] as const;

export function Hero() {
  const reduce = useReducedMotion();
  const { t } = useLocale();
  const h = t.hero;
  const up = (d: number) => ({
    initial: reduce ? false : { opacity: 0, y: 22 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.8, delay: d, ease },
  });
  return (
    <section className="hero">
      <div className="hero-bg" aria-hidden>
        <motion.div className="hero-orb a" animate={reduce ? undefined : { x: [0, 30, 0], y: [0, -20, 0] }} transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }} />
        <motion.div className="hero-orb b" animate={reduce ? undefined : { x: [0, -40, 0], y: [0, 24, 0] }} transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }} />
        <div className="hero-grid" />
      </div>
      <div className="wrap hero-inner">
        <motion.p className="eyebrow" {...up(0.05)}>{h.eyebrow}</motion.p>
        <motion.h1 className="display" {...up(0.15)}>
          {h.h1a}<br />
          <span className="display-muted">{h.h1b}</span>
        </motion.h1>
        <motion.p className="lede hero-lede" {...up(0.28)}>{h.lede}</motion.p>
        <motion.div className="cta-row" {...up(0.38)}>
          <Link href="/get-started" className="btn btn-primary btn-lg">{h.cta} <ArrowRight size={16} className="dir-icon" /></Link>
          <Link href="/product" className="btn btn-ghost btn-lg">{h.how}</Link>
        </motion.div>
        <motion.div className="hero-proof" {...up(0.5)}>
          {h.proof.map((p, i) => (<span key={p} style={{ display: "contents" }}>{i > 0 && <i />}<span>{p}</span></span>))}
        </motion.div>
      </div>
    </section>
  );
}
