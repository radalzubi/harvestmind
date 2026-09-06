"use client";

/**
 * A miniature of the workspace's verdict card. Illustrative figures. The
 * three lines are the whole method: read your policy, test candidates on
 * your past, change only when the lower bound wins.
 */
import { motion } from "motion/react";
import { useLocale } from "@/lib/i18n";
import { useQaMotionOff } from "@/lib/motion";

export function DecisionCard() {
  const { t } = useLocale();
  const c = t.home.decision;
  const qa = useQaMotionOff();
  const ease = [0.22, 1, 0.36, 1] as const;
  const rows = [
    { name: c.rowYours, lb: "", tone: "base" },
    { name: c.rowA, lb: "+0.3%", tone: "fail" },
    { name: c.rowB, lb: "+1.9%", tone: "pass" },
    { name: c.rowC, lb: "-4.5%", tone: "fail" },
  ];
  return (
    <motion.div className="decision-card" initial={qa ? false : { opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "0px 0px -15% 0px" }} transition={{ duration: 0.7, ease }}>
      <div className="decision-head"><span className="decision-dot" />{c.title}</div>
      <div className="decision-rows">
        {rows.map((r, i) => (
          <motion.div key={r.name} className={`decision-row ${r.tone}`} initial={qa ? false : { opacity: 0, x: -8 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: 0.25 + i * 0.12, duration: 0.5, ease }}>
            <span>{r.name}</span>
            <span className="decision-lb">{r.lb || c.baseline}</span>
            <span className="decision-verdict">{r.tone === "base" ? "" : r.tone === "pass" ? c.adopted : c.kept}</span>
          </motion.div>
        ))}
      </div>
      <div className="decision-foot">{c.foot}</div>
    </motion.div>
  );
}
