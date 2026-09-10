"use client";

/**
 * The one interaction the homepage is allowed to have: a lane slips, the
 * plan moves. Illustrative figures, labelled as such. Hover, focus or tap
 * stresses the current route; Zaad's alternative appears with its lead
 * time and risk; letting go restores calm. The card also runs one cycle
 * on its own when it scrolls into view so nobody has to discover it.
 */
import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { useLocale } from "@/lib/i18n";
import { useReduce } from "@/lib/motion";

export function RouteCard() {
  const { t } = useLocale();
  const c = t.home.route;
  const reduce = useReduce();
  const [stressed, setStressed] = useState(false);
  const [pinned, setPinned] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const played = useRef(false);

  // one unprompted demonstration when the card first appears; the timers
  // live in a ref so unmounting (or leaving the page mid-demo) clears them
  const timers = useRef<number[]>([]);
  useEffect(() => {
    const el = ref.current;
    if (!el || reduce) return;
    const clear = () => { timers.current.forEach((id) => window.clearTimeout(id)); timers.current = []; };
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting || played.current) return;
      played.current = true;
      timers.current.push(
        window.setTimeout(() => setStressed(true), 900),
        window.setTimeout(() => setStressed(false), 4200),
      );
    }, { threshold: 0.6 });
    io.observe(el);
    return () => { io.disconnect(); clear(); };
  }, [reduce]);

  const on = stressed || pinned;
  const ease = [0.22, 1, 0.36, 1] as const;

  return (
    <div ref={ref} className={`route-card ${on ? "on" : ""}`}
      onPointerEnter={() => setStressed(true)} onPointerLeave={() => setStressed(false)}
      onClick={() => setPinned((p) => !p)} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setPinned((p) => !p); } }}
      role="button" tabIndex={0} aria-pressed={pinned} aria-label={c.aria}>
      <div className="route-card-head">
        <span className="route-card-tag">{c.tag}</span>
        <span className="route-card-hint">{on ? c.hintOn : c.hintOff}</span>
      </div>

      <div className="route-row current">
        <div className="route-row-label">{c.current}</div>
        <svg className="route-svg" viewBox="0 0 320 60" aria-hidden>
          <path className="route-path base" d="M12 44 C 90 10, 200 70, 308 24" />
          <motion.path className="route-path flow" d="M12 44 C 90 10, 200 70, 308 24" pathLength={1}
            animate={reduce ? undefined : { strokeDashoffset: on ? [0, 0] : [1, 0] }} transition={{ duration: 2.4, repeat: Infinity, ease: "linear" }}
            style={{ opacity: on ? 0.25 : 1 }} />
          <circle className="route-dot" cx="12" cy="44" r="4" /><circle className="route-dot" cx="308" cy="24" r="4" />
          {on && <motion.circle className="route-alert" cx="160" cy="40" r="5" initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.5, ease }} />}
        </svg>
        <div className="route-stats">
          <Stat label={c.leadTime} value={on ? c.currentOnDays : c.currentDays} unit={c.days} />
          <Stat label={c.risk} value={on ? c.elevated : c.normal} tone={on ? "warn" : "ok"} />
        </div>
      </div>

      <div className={`route-row alt ${on ? "live" : "standby"}`}>
        <div className="route-row-label">{c.alternative}<span className="route-row-sub">{on ? c.altOn : c.altOff}</span></div>
        <svg className="route-svg" viewBox="0 0 320 60" aria-hidden>
          <path className="route-path base" d="M12 16 C 100 50, 210 10, 308 40" />
          <motion.path className="route-path flow alt" d="M12 16 C 100 50, 210 10, 308 40" pathLength={1}
            initial={false} animate={{ pathLength: on ? 1 : 0, opacity: on ? 1 : 0 }} transition={{ duration: 0.9, ease }} />
          <circle className="route-dot" cx="12" cy="16" r="4" /><circle className="route-dot" cx="308" cy="40" r="4" />
        </svg>
        <div className="route-stats">
          <Stat label={c.leadTime} value={on ? c.altDays : "–"} unit={on ? c.days : undefined} />
          <Stat label={c.risk} value={on ? c.lower : "–"} tone={on ? "ok" : undefined} />
        </div>
      </div>
      <div className="route-card-foot">{c.footnote}</div>
    </div>
  );
}

function Stat({ label, value, unit, tone }: { label: string; value: string; unit?: string; tone?: "ok" | "warn" }) {
  return (
    <div className="route-stat">
      <span className="route-stat-label">{label}</span>
      <span className={`route-stat-value ${tone ?? ""}`}>
        <motion.span key={value} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} style={{ display: "inline-block" }}>
          {value}
        </motion.span>
        {unit && <span className="route-stat-unit"> {unit}</span>}
      </span>
    </div>
  );
}
