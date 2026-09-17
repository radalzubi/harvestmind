"use client";

/**
 * One analysis, honestly framed: title, description, the visual, "Show as table", "Data & scope",
 * and where it leads. The same card on Explore, on a dashboard tile and in an Ask ZAAD answer.
 */
import { useId, useState, type ReactNode } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import type { ResultSet, VisualSpec } from "@/lib/analytics/client";
import { descriptionOf, titleOf } from "@/lib/analytics/visual";
import { ProvenanceCard } from "./ProvenanceCard";
import { VisualRenderer } from "./VisualRenderer";

export function AnalysisCard({ visual, result, height, onMember, actions, leads, badge, compact, wide, children }: {
  visual: VisualSpec; result: ResultSet | null; height?: number; onMember?: (dimension: string, member: string) => void;
  actions?: ReactNode; leads?: Array<{ href: string; label: string }>; badge?: ReactNode; compact?: boolean; wide?: boolean; children?: ReactNode;
}) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const [asTable, setAsTable] = useState(false);
  const id = useId();
  const tabular = visual.visual_type === "table" || visual.visual_type === "pivot" || visual.visual_type === "kpi";
  return (
    <figure className="ins-card ex-card" aria-labelledby={`${id}-t`} aria-describedby={`${id}-d`} data-wide={wide ? "true" : undefined}>
      <figcaption className="ins-card-h">
        <div style={{ minWidth: 0 }}>
          <h3 id={`${id}-t`}>{titleOf(visual, lc) || copy.canvas} {badge}</h3>
          <p id={`${id}-d`}>{descriptionOf(visual, lc)}</p>
        </div>
        <div className="ex-card-actions">
          {result && !result.empty && !tabular && (
            <button type="button" className="zb zb--tertiary zb--sm" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>{asTable ? copy.showChart : copy.showTable}</button>
          )}
          {actions}
        </div>
      </figcaption>
      <div className="ins-chart">
        {result ? (
          asTable ? <VisualRenderer visual={{ ...visual, visual_type: "table" }} result={result} onMember={onMember} compact={compact} />
                  : <VisualRenderer visual={visual} result={result} height={height} onMember={onMember} compact={compact} />
        ) : <div className="sk sk-card" aria-busy="true" />}
      </div>
      {children}
      {leads && leads.length > 0 && (
        <p className="ins-leads">{leads.map((l) => <Link key={l.href} href={l.href} className="zb zb--tertiary zb--sm">{l.label} <ArrowUpRight size={13} aria-hidden /></Link>)}</p>
      )}
      {result && <ProvenanceCard result={result} />}
    </figure>
  );
}
