"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import { useQaMotionOff, useReduce } from "@/lib/motion";

// The network canvas is client-only and not needed for first paint.
const SupplyField = dynamic(() => import("./SupplyField").then((m) => m.SupplyField), { ssr: false });

const ease = [0.22, 1, 0.36, 1] as const;

/** A button that leans a few pixels toward the pointer, and springs back. */
function Magnetic({ children }: { children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReduce();
  const onMove = (e: React.PointerEvent) => {
    const el = ref.current;
    if (!el || reduce || e.pointerType !== "mouse") return;
    const r = el.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
    const dy = (e.clientY - (r.top + r.height / 2)) / r.height;
    el.style.transform = `translate(${dx * 6}px, ${dy * 4}px)`;
  };
  const reset = () => { if (ref.current) ref.current.style.transform = ""; };
  return <div ref={ref} className="magnetic" onPointerMove={onMove} onPointerLeave={reset}>{children}</div>;
}

export function Hero() {
  const qa = useQaMotionOff();
  const { t } = useLocale();
  const h = t.hero;
  // QA switch: /?field=off renders the hero without the network canvas.
  const [field, setField] = useState(true);
  useEffect(() => { setField(new URLSearchParams(window.location.search).get("field") !== "off"); }, []);
  // Sequence: atmosphere is there from the first paint; the headline
  // resolves upward, the sentence follows, the buttons settle, then the
  // network's packets are already moving underneath. Nothing blocks input.
  const up = (d: number) => ({
    initial: qa ? false : { opacity: 0, y: 26, filter: "blur(6px)" },
    animate: { opacity: 1, y: 0, filter: "blur(0px)" },
    transition: { duration: 0.8, delay: d, ease },
  });
  return (
    <section className="hero">
      <div className="hero-layers" aria-hidden>
        <div className="hero-atmos" />
        <div className="hero-sweep" />
        <div className="hero-noise" />
        {field && <SupplyField />}
        <div className="hero-veil" />
      </div>
      <div className="wrap hero-inner">
        <motion.p className="eyebrow" {...up(0.05)}>{h.eyebrow}</motion.p>
        <motion.h1 className="display" {...up(0.14)}>
          {h.h1a}<br /><span className="display-muted">{h.h1b}</span>
        </motion.h1>
        <motion.p className="lede hero-lede" {...up(0.26)}>{h.lede}</motion.p>
        <motion.div className="cta-row" {...up(0.36)}>
          <Magnetic><Link href="/get-started" className="btn btn-primary btn-lg">{h.cta} <ArrowRight size={16} className="dir-icon" /></Link></Magnetic>
          <Link href="/how-it-works" className="btn btn-ghost btn-lg">{h.how}</Link>
        </motion.div>
      </div>
      <motion.a href="#moment" className="hero-cue" aria-label="Scroll" initial={qa ? false : { opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.1, duration: 0.8 }}>
        <span /><i />
      </motion.a>
      <div className="hero-vignette" aria-hidden />
    </section>
  );
}
