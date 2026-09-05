"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "lucide-react";

const ease = [0.22, 1, 0.36, 1] as const;

export function Hero() {
  const reduce = useReducedMotion();
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
        <motion.p className="eyebrow" {...up(0.05)}>Purchasing decisions for businesses that import what they sell</motion.p>
        <motion.h1 className="display" {...up(0.15)}>
          How much to buy, and when,<br />
          <span className="display-muted">without ever making your buying worse.</span>
        </motion.h1>
        <motion.p className="lede hero-lede" {...up(0.28)}>
          Upload a year of purchase orders, receipts, sales and stock counts. See how you order today, what a safe optimizer would have done on that same history, and the risk on your supply lanes right now.
        </motion.p>
        <motion.div className="cta-row" {...up(0.38)}>
          <Link href="/get-started" className="btn btn-primary btn-lg">Get started <ArrowRight size={16} /></Link>
          <Link href="/product" className="btn btn-ghost btn-lg">How it works</Link>
        </motion.div>
        <motion.div className="hero-proof" {...up(0.5)}>
          <span>Backtested on your history</span><i />
          <span>Pseudonymised on arrival</span><i />
          <span>No forecast of savings, ever</span>
        </motion.div>
      </div>
    </section>
  );
}
