"use client";
/**
 * One chart, honestly framed. Title and a one-sentence description for every reader (and every
 * screen reader); the chart; a "Show as table" toggle so the values are reachable without colour
 * or a pointer; and the "Data & scope" disclosure that says which rows, which metric, which
 * numerator and denominator, which filters, when the data was last updated, and which plan — when
 * the number is optimizer-derived. A chart with nothing to draw says why, in the server's words.
 */
import { useId, useState, type ReactNode } from "react";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { Disclosure } from "@/components/workspace/ui";
import { DATE } from "@/lib/zaad/product";
import { planSentence, reasonLabel, scopeSentence, type Provenance } from "@/lib/zaad/insights";

export interface TableColumn { key: string; label: string; format?: (v: unknown) => string; align?: "start" | "end" }

export function ChartCard({
  title, description, children, provenance, table, rows, leads, empty, emptyReason, emptyWhy, aside, rowsCount,
}: {
  title: string; description: string; children?: ReactNode; provenance?: Provenance | null;
  table?: TableColumn[]; rows?: Array<Record<string, unknown>>;
  /** Where this chart leads. No dead ends. */
  leads?: Array<{ href: string; label: string }>;
  empty?: boolean; emptyReason?: string | null; emptyWhy?: string | null; aside?: ReactNode; rowsCount?: number | null;
}) {
  const [asTable, setAsTable] = useState(false);
  const id = useId();
  return (
    <figure className="ins-card" aria-labelledby={`${id}-t`} aria-describedby={`${id}-d`}>
      <figcaption className="ins-card-h">
        <div>
          <h3 id={`${id}-t`}>{title}</h3>
          <p id={`${id}-d`}>{description}</p>
        </div>
        {table && rows && rows.length > 0 && !empty && (
          <button type="button" className="zb zb--tertiary zb--sm" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
            {asTable ? "Show as chart" : "Show as table"}
          </button>
        )}
      </figcaption>
      {empty ? (
        <p className="ins-empty" role="status">
          <strong>{reasonLabel(emptyReason)}.</strong> {emptyWhy ?? "Nothing to draw for this scope."}
        </p>
      ) : asTable && table && rows ? (
        <div className="tbl-wrap" style={{ overflowX: "auto" }}>
          <table className="tbl ins-table">
            <thead><tr>{table.map((c) => <th key={c.key} scope="col" data-align={c.align ?? "start"}>{c.label}</th>)}</tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>{table.map((c) => <td key={c.key} data-align={c.align ?? "start"}>{c.format ? c.format(r[c.key]) : String(r[c.key] ?? "—")}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="ins-chart">{children}</div>
      )}
      {aside}
      {leads && leads.length > 0 && (
        <p className="ins-leads">
          {leads.map((l) => <Link key={l.href} href={l.href} className="zb zb--tertiary zb--sm">{l.label} <ArrowUpRight size={13} aria-hidden /></Link>)}
        </p>
      )}
      {provenance && <DataScope provenance={provenance} rows={rowsCount} />}
    </figure>
  );
}

export function DataScope({ provenance, rows }: { provenance: Provenance; rows?: number | null }) {
  const coverage = Object.entries(provenance.coverage ?? {}).filter(([, v]) => v != null);
  return (
    <Disclosure summary="Data & scope" hint={scopeSentence(provenance, rows)}>
      <dl className="kv ins-scope">
        <dt>Metric</dt><dd>{provenance.metric}</dd>
        <dt>Numerator</dt><dd>{provenance.numerator}</dd>
        <dt>Denominator</dt><dd>{provenance.denominator}</dd>
        <dt>Scope</dt><dd>{scopeSentence(provenance, rows)}</dd>
        <dt>Source data</dt><dd><span dir="ltr">{provenance.source_data.join(", ")}</span></dd>
        {coverage.length > 0 && <><dt>Coverage</dt><dd>{coverage.map(([k, v]) => `${k.replace(/_/g, " ")}: ${typeof v === "number" ? v.toLocaleString("en-US") : String(v)}`).join(" · ")}</dd></>}
        <dt>Last updated</dt><dd>{provenance.last_updated ? DATE(provenance.last_updated) : "Unknown"}</dd>
        {provenance.plan && <><dt>Plan</dt><dd>{planSentence({ available: true, finished_at: provenance.plan.finished_at ?? null, stale: provenance.plan.stale }, DATE)}</dd></>}
        {provenance.note && <><dt>Note</dt><dd>{provenance.note}</dd></>}
      </dl>
    </Disclosure>
  );
}
