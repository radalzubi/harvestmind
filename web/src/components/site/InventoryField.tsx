"use client";

/**
 * Eight abstract stock positions. Protection flows from where it is excess
 * to where it is thin, then the field settles: LEAN, PROTECT, ALLOCATE,
 * RECOVER. Pure CSS transitions on heights; a slow interval drives it; it
 * only runs while visible and never under reduced motion.
 */
import { useEffect, useRef, useState } from "react";

import { useLocale } from "@/lib/i18n";
import { useReduce } from "@/lib/motion";

const LEAN = [0.55, 0.5, 0.58, 0.52, 0.56, 0.5, 0.54, 0.52];
const EXPOSED = [0.55, 0.5, 0.92, 0.52, 0.18, 0.5, 0.88, 0.22];
const PROTECTED = [0.55, 0.5, 0.62, 0.52, 0.6, 0.5, 0.6, 0.58];

export function InventoryField() {
  const { t } = useLocale();
  const c = t.home.field;
  const reduce = useReduce();
  const [stage, setStage] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const stages = [LEAN, EXPOSED, PROTECTED, LEAN];
  const words = [c.lean, c.protect, c.allocate, c.recover];

  useEffect(() => {
    const el = ref.current;
    if (!el || reduce) return;
    let timer = 0;
    const io = new IntersectionObserver(([e]) => {
      window.clearInterval(timer);
      if (e.isIntersecting) timer = window.setInterval(() => setStage((s) => (s + 1) % 4), 2600);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => { io.disconnect(); window.clearInterval(timer); };
  }, [reduce]);

  const heights = stages[stage];
  return (
    <div ref={ref} className="inv-field" aria-label={c.aria} role="img">
      <div className="inv-bars">
        {heights.map((v, i) => {
          const tone = v > 0.8 ? "excess" : v < 0.3 ? "thin" : "ok";
          return <div key={i} className={`inv-bar ${tone}`} style={{ height: `${Math.round(v * 100)}%` }} />;
        })}
      </div>
      <div className="inv-words" aria-hidden>
        {words.map((w, i) => <span key={w} className={i === stage ? "on" : ""}>{w}</span>)}
      </div>
    </div>
  );
}
