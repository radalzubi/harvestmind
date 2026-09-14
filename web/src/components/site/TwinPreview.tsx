"use client";

/**
 * The Network Twin, shown on the public site.
 *
 * Hand-drawn SVG in the product's own visual language rather than the real Twin: the landing
 * page must not pull MapLibre or React Flow into its critical path, and a prospect needs to
 * recognise the shape of the product, not operate it. It is labelled illustrative because it is.
 *
 * Selecting a node moves the reading panel beside it — the same interaction the real product
 * has, so the page demonstrates the idea instead of describing it.
 */
import { useState } from "react";
import { motion } from "motion/react";
import { useLocale } from "@/lib/i18n";
import { useQaMotionOff, useReduce } from "@/lib/motion";

type Tone = "calm" | "watch" | "action";

interface Spot {
  id: string;
  label: string;
  kind: string;
  x: number;
  y: number;
  tone: Tone;
  reading: string;
  decision: string | null;
}

const TONE: Record<Tone, string> = { calm: "var(--ink-900)", watch: "#D97706", action: "var(--high)" };

export function TwinPreview() {
  const { t } = useLocale();
  const c = t.home.twin;
  const qa = useQaMotionOff();
  const reduce = useReduce();
  const [active, setActive] = useState("lane");

  const spots: Spot[] = [
    { id: "sup1", label: c.spots.sup1, kind: c.kinds.supplier, x: 60, y: 58, tone: "calm", reading: c.readings.sup1, decision: null },
    { id: "sup2", label: c.spots.sup2, kind: c.kinds.supplier, x: 60, y: 148, tone: "watch", reading: c.readings.sup2, decision: c.decisions.sup2 },
    { id: "port", label: c.spots.port, kind: c.kinds.port, x: 236, y: 103, tone: "calm", reading: c.readings.port, decision: null },
    { id: "dc", label: c.spots.dc, kind: c.kinds.dc, x: 404, y: 103, tone: "calm", reading: c.readings.dc, decision: null },
    { id: "branch", label: c.spots.branch, kind: c.kinds.branch, x: 566, y: 55, tone: "action", reading: c.readings.branch, decision: c.decisions.branch },
    { id: "cust", label: c.spots.cust, kind: c.kinds.customer, x: 566, y: 152, tone: "calm", reading: c.readings.cust, decision: null },
  ];
  const links: Array<{ id: string; from: string; to: string; tone: Tone; label?: string }> = [
    { id: "l1", from: "sup1", to: "port", tone: "calm" },
    { id: "lane", from: "sup2", to: "port", tone: "watch", label: c.laneLabel },
    { id: "l3", from: "port", to: "dc", tone: "calm" },
    { id: "l4", from: "dc", to: "branch", tone: "action" },
    { id: "l5", from: "dc", to: "cust", tone: "calm" },
  ];

  const at = (id: string) => spots.find((s) => s.id === id)!;
  const selected = spots.find((s) => s.id === active) ?? links.find((l) => l.id === active) ?? null;
  const selectedLane = links.find((l) => l.id === active) ?? null;
  const reading = selectedLane ? c.readings.lane : (selected as Spot | null)?.reading ?? "";
  const decision = selectedLane ? c.decisions.lane : (selected as Spot | null)?.decision ?? null;
  const title = selectedLane ? c.laneLabel : (selected as Spot | null)?.label ?? "";
  const kind = selectedLane ? c.kinds.lane : (selected as Spot | null)?.kind ?? "";

  return (
    <div className="twinp">
      <div className="twinp-canvas">
        <svg viewBox="0 0 640 210" className="twinp-svg" role="img" aria-label={c.aria}>
          {links.map((l) => {
            const a = at(l.from), b = at(l.to);
            const mx = (a.x + b.x) / 2;
            const on = active === l.id;
            return (
              <g key={l.id}>
                <path
                  d={`M ${a.x + 26} ${a.y} C ${mx} ${a.y} ${mx} ${b.y} ${b.x - 26} ${b.y}`}
                  fill="none"
                  stroke={on ? "var(--accent)" : l.tone === "calm" ? "var(--line-strong)" : TONE[l.tone]}
                  strokeWidth={on ? 2.4 : l.tone === "calm" ? 1.4 : 2}
                  strokeLinecap="round"
                />
                {l.label && (
                  <g
                    className="twinp-hit"
                    role="button"
                    tabIndex={0}
                    aria-label={`${c.kinds.lane}: ${l.label}`}
                    onClick={() => setActive(l.id)}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setActive(l.id); } }}
                  >
                    <rect x={mx - 40} y={(a.y + b.y) / 2 - 11} width={80} height={22} rx={11} fill="var(--surface)" stroke={on ? "var(--accent)" : "var(--line)"} />
                    <text x={mx} y={(a.y + b.y) / 2 + 4} textAnchor="middle" className="twinp-lane-text">{l.label}</text>
                  </g>
                )}
              </g>
            );
          })}
          {spots.map((s) => {
            const on = active === s.id;
            return (
              <g
                key={s.id}
                className="twinp-hit"
                role="button"
                tabIndex={0}
                aria-label={`${s.kind}: ${s.label}`}
                aria-pressed={on}
                onClick={() => setActive(s.id)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setActive(s.id); } }}
              >
                <circle cx={s.x} cy={s.y} r={on ? 12 : 9} fill="var(--surface)" stroke={on ? "var(--accent)" : TONE[s.tone]} strokeWidth={on ? 3 : 2} />
                {s.tone !== "calm" && !reduce && (
                  <circle cx={s.x} cy={s.y} r={9} fill="none" stroke={TONE[s.tone]} strokeWidth={1.5} opacity={0.5}>
                    <animate attributeName="r" values="9;17;9" dur="3.2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values=".5;0;.5" dur="3.2s" repeatCount="indefinite" />
                  </circle>
                )}
                <text x={s.x} y={s.y + 26} textAnchor="middle" className="twinp-label">{s.label}</text>
              </g>
            );
          })}
        </svg>
        <span className="twinp-tag">{c.illustrative}</span>
      </div>

      <motion.div
        className="twinp-panel"
        key={active}
        initial={qa || reduce ? false : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
        aria-live="polite"
      >
        <p className="twinp-kind">{kind}</p>
        <h3 className="twinp-title">{title}</h3>
        <p className="twinp-reading">{reading}</p>
        {decision ? (
          <div className="twinp-decision">
            <span className="twinp-verb">{c.recommends}</span>
            <p>{decision}</p>
          </div>
        ) : (
          <p className="twinp-none">{c.noChange}</p>
        )}
      </motion.div>
    </div>
  );
}
