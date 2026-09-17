"use client";

/**
 * The diagnostic result in the app: the same structured report the PDF renders
 * (reports/diagnostic_findings.py), so the two never tell different stories. Every finding links
 * to the record it is about (SKU → Inventory, supplier → Supplier diagnostics, open orders →
 * Purchase orders) and to the decision workflow.
 */
import { useState } from "react";
import Link from "next/link";
import { ChevronDown, ChevronRight, Download, ExternalLink } from "lucide-react";
import type { DiagnosticReport as Report, ReportFinding, ReportRelated } from "@/lib/api";
import { Tbtn } from "@/components/ui";

const ID = /^[A-Za-z0-9 _.:@+\-\/&()'#,]{1,120}$/;

/** Where a related entity leads in ZAAD. Mirrors analytics/links.drillThrough for the same kinds. */
export function hrefFor(r: ReportRelated): { href: string; label: string } | null {
  const m = encodeURIComponent(r.id);
  switch (r.kind) {
    case "sku": return ID.test(r.id) ? { href: `/inventory?sku=${m}`, label: `View SKU ${r.id}` } : null;
    case "supplier": return ID.test(r.id) ? { href: `/diagnostics/supplier/${m}`, label: `View supplier ${r.id}` } : null;
    case "po": return { href: "/orders?tab=imported&postate=open", label: "View purchase orders" };
    case "decision": return { href: "/decisions", label: "Run a decision" };
    case "screen": return r.id === "upload" ? { href: "/upload", label: "Upload data" } : r.id === "inventory" ? { href: "/inventory", label: "Inventory" } : null;
    default: return null;
  }
}

const SEV_LABEL: Record<string, string> = { high: "High", medium: "Medium", low: "Low", info: "Note" };

export function DiagnosticReportView({ report, onDownload, downloading }: { report: Report; onDownload: () => void; downloading?: boolean }) {
  const [showAppendix, setShowAppendix] = useState(false);
  const r = report;
  const cards = r.findings.filter((f) => f.severity === "high" || f.severity === "medium");
  const rest = r.findings.filter((f) => f.severity !== "high" && f.severity !== "medium");
  return (
    <div className="diag-report">
      <section className="diag-exec">
        <div className="diag-kicker">Executive summary</div>
        <h2 className="diag-headline">{r.conclusion.headline}</h2>
        <p>{r.conclusion.body}</p>
        {r.executive_summary.findings.length > 0 && (
          <>
            <div className="diag-sub">Most important findings</div>
            <ol className="diag-exec-list">
              {r.executive_summary.findings.map((f) => (
                <li key={f.id}><a href={`#finding-${f.id}`}><b>{f.headline}</b></a> — {f.line} <span className="diag-muted">(confidence {f.confidence.toLowerCase()})</span></li>
              ))}
            </ol>
          </>
        )}
        {r.executive_summary.actions.length > 0 && (
          <>
            <div className="diag-sub">Recommended actions</div>
            <ul className="diag-exec-list">{r.executive_summary.actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
          </>
        )}
        <p><b>Data quality and confidence: {r.executive_summary.confidence.level}.</b> {r.executive_summary.confidence.statement}</p>
        <div className="diag-exec-actions">
          <Tbtn variant="primary" icon={<Download size={13} />} onClick={onDownload} pending={downloading}>Download the report (PDF)</Tbtn>
          <span className="diag-muted">Run {r.run_id} · {String(r.generated_at ?? "").slice(0, 10)} · measured on your own history, not a forecast</span>
        </div>
      </section>

      <Section title="1. Data readiness and confidence">
        <p><b>{r.readiness.label}</b> · overall confidence <b>{r.readiness.confidence}</b></p>
        <p>{r.readiness.statement}</p>
        <dl className="diag-facts">
          {r.readiness.facts.map((f) => <div key={f.label}><dt>{f.label}</dt><dd>{f.value}</dd></div>)}
        </dl>
        {r.readiness.limitations.length > 0 && (
          <>
            <div className="diag-sub">What the limitations mean for this analysis</div>
            <ul>{r.readiness.limitations.map((l, i) => <li key={i}>{l.effect}</li>)}</ul>
          </>
        )}
        {r.readiness.missing_fields.length > 0 && (
          <p className="diag-muted">Fields that would strengthen it: {r.readiness.missing_fields.slice(0, 10).map((m) => m.field).join(", ")}{r.readiness.missing_fields.length > 10 ? " and others" : ""}. <Link href="/upload">Upload data</Link></p>
        )}
      </Section>

      {r.ordering_today.items.length > 0 && (
        <Section title="2. How you appear to order today">
          <p className="diag-muted">{r.ordering_today.summary}</p>
          <div className="diag-table-wrap">
            <table className="diag-table">
              <thead><tr><th>Observation</th><th>What we read</th><th>Basis</th></tr></thead>
              <tbody>
                {r.ordering_today.items.map((it) => (
                  <tr key={it.label}><td><b>{it.label}</b></td><td>{it.value}{it.note && <div className="diag-muted diag-small">{it.note}</div>}</td><td><span className={`diag-tag ${it.tag.replace(" ", "-").toLowerCase()}`}>{it.tag}</span></td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      <Section title="3. Historical policy comparison">
        {r.policy_comparison.available ? (
          <>
            <p><b>{r.policy_comparison.current_label}</b> versus <b>{r.policy_comparison.candidate_label}</b>, replayed on your own history.</p>
            <div className="diag-table-wrap">
              <table className="diag-table">
                <thead><tr><th>Measure</th><th>Your current policy</th><th>{r.policy_comparison.candidate_label}</th><th>Reading</th></tr></thead>
                <tbody>
                  {r.policy_comparison.rows.map((row) => (
                    <tr key={row.metric}><td>{row.metric}{row.note && <div className="diag-muted diag-small">{row.note}</div>}</td><td>{row.current}</td><td><b>{row.candidate}</b></td><td className="diag-muted">{row.difference}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            {r.policy_comparison.explanation.map((p, i) => <p key={i}>{p}</p>)}
            {r.policy_comparison.fold_chart && <FoldChart chart={r.policy_comparison.fold_chart} />}
          </>
        ) : r.policy_comparison.explanation.map((p, i) => <p key={i}>{p}</p>)}
      </Section>

      {r.findings.length > 0 && (
        <Section title="4. Management attention">
          <p className="diag-muted">Ranked by severity and, where a defensible measure exists, by the share of your demand value involved.</p>
          {cards.map((f) => <FindingCard key={f.id} f={f} />)}
          {rest.length > 0 && (
            <>
              <div className="diag-sub">Also noted (lower severity)</div>
              <ul>{rest.map((f) => <li key={f.id} id={`finding-${f.id}`}><b>{f.headline}.</b> {f.observation} <span className="diag-muted">What to consider: {f.recommendation}</span> <Links related={f.related} /></li>)}</ul>
            </>
          )}
        </Section>
      )}

      <Section title="5. Supplier analysis">
        {r.suppliers.available && r.suppliers.rows.length > 0 ? (
          <>
            <div className="diag-table-wrap">
              <table className="diag-table">
                <thead><tr><th>Supplier</th><th>Share of value</th><th>Products</th><th>Receipts</th><th>Fill</th><th>Lead time</th><th>Spread</th><th>Lane</th><th>Reading</th></tr></thead>
                <tbody>
                  {r.suppliers.rows.map((s) => (
                    <tr key={s.supplier}>
                      <td>{hrefFor({ kind: "supplier", id: s.supplier, label: s.supplier }) ? <Link href={hrefFor({ kind: "supplier", id: s.supplier, label: s.supplier })!.href}>{s.supplier}</Link> : s.supplier}</td>
                      <td>{s.share_of_value}</td><td>{s.products}</td><td>{s.receipts}</td><td>{s.fill}</td><td>{s.lead_time}</td><td>{s.lead_spread}</td><td>{s.lane}</td>
                      <td>{s.reading}<div className="diag-muted diag-small">evidence {s.evidence}</div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="diag-muted diag-small">{r.suppliers.note}</p>
          </>
        ) : <p>{r.suppliers.note}</p>}
      </Section>

      <Section title="6. Supply lane risk">
        {r.lanes.length > 0 ? (
          <>
            <p className="diag-muted diag-small">{r.lanes[0].score_meaning}</p>
            {r.lanes.filter((ln) => ln.attention === "ELEVATED" || ln.attention === "UNAVAILABLE").map((ln) => (
              <div key={ln.lane} className={`diag-lane ${ln.attention.toLowerCase()}`}>
                <div className="diag-lane-head"><b>{ln.label.toUpperCase()}</b> — <span className="diag-lane-attn">{ln.attention}</span> · lane score {ln.score} · evidence {ln.evidence_strength}</div>
                <div className="diag-muted diag-small">{ln.evidence_note}</div>
                <div className="diag-lane-cols">
                  <div><div className="diag-sub">External condition</div><ul>{ln.external.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                  <div><div className="diag-sub">Your exposure</div><ul>{ln.exposure.map((x, i) => <li key={i}>{x}</li>)}</ul></div>
                  <div><div className="diag-sub">Recommended response</div><p>{ln.response}</p><Link href="/orders?tab=imported&postate=open" className="diag-link">View purchase orders <ExternalLink size={12} /></Link></div>
                </div>
              </div>
            ))}
            {r.lanes.some((ln) => ln.attention === "WATCH" || ln.attention === "NORMAL") && (
              <div className="diag-table-wrap">
                <table className="diag-table">
                  <thead><tr><th>Lane</th><th>Attention</th><th>Score</th><th>Evidence</th><th>External condition</th><th>Your exposure</th><th>Response</th></tr></thead>
                  <tbody>
                    {r.lanes.filter((ln) => ln.attention === "WATCH" || ln.attention === "NORMAL").map((ln) => (
                      <tr key={ln.lane} className={`diag-lane-row ${ln.attention.toLowerCase()}`}>
                        <td><b>{ln.label}</b></td><td><span className="diag-lane-attn">{ln.attention}</span></td><td>{ln.score}</td><td>{ln.evidence_strength}</td>
                        <td className="diag-small">{ln.external.slice(0, 3).join("; ")}</td><td className="diag-small">{ln.exposure.slice(0, 2).join("; ")}</td><td className="diag-small">{ln.response}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        ) : <p>No shipping route is declared per supplier, so no lane evidence could be attached. Declare the route in the supplier list to enable this section.</p>}
      </Section>

      <Section title="7. Recommended actions">
        {(["now", "next", "monitor"] as const).map((k) => r.actions[k].length > 0 && (
          <div key={k}>
            <div className="diag-sub">{k.toUpperCase()}</div>
            <ul>{r.actions[k].map((a, i) => <li key={i}>{a.text} {a.link && hrefFor(a.link) && <Link href={hrefFor(a.link)!.href} className="diag-link">{hrefFor(a.link)!.label} <ExternalLink size={12} /></Link>}</li>)}</ul>
          </div>
        ))}
      </Section>

      <section className="diag-section">
        <button type="button" className="diag-toggle" onClick={() => setShowAppendix((s) => !s)} aria-expanded={showAppendix}>
          {showAppendix ? <ChevronDown size={14} /> : <ChevronRight size={14} />} Appendix: assumptions and methodology
        </button>
        {showAppendix && (
          <div className="diag-appendix">
            <div className="diag-sub">Methodology</div>
            <ul>{r.appendix.methodology.map((m, i) => <li key={i}>{m}</li>)}</ul>
            {r.appendix.candidates.length > 0 && (
              <>
                <div className="diag-sub">Policy candidates tested</div>
                <div className="diag-table-wrap">
                  <table className="diag-table">
                    <thead><tr><th>Candidate</th><th>Average</th><th>Conservative estimate</th><th>Worst period</th><th>Periods</th><th>Selection rule</th><th>Unseen validation</th></tr></thead>
                    <tbody>{r.appendix.candidates.map((c) => <tr key={c.candidate}><td>{c.label}<div className="diag-muted diag-small">{c.candidate}</div></td><td>{c.mean}</td><td>{c.lower_bound}</td><td>{c.worst}</td><td>{c.folds}</td><td>{c.inner_gates}</td><td>{c.holdout}</td></tr>)}</tbody>
                  </table>
                </div>
              </>
            )}
            {r.appendix.assumptions.length > 0 && (
              <>
                <div className="diag-sub">Inputs and their provenance</div>
                <div className="diag-table-wrap">
                  <table className="diag-table"><thead><tr><th>Input</th><th>Provenance</th></tr></thead>
                    <tbody>{r.appendix.assumptions.map((a, i) => <tr key={i}><td>{a.input}</td><td>{a.provenance}</td></tr>)}</tbody></table>
                </div>
                <p className="diag-muted diag-small">operator = supplied by you · measured = derived from your transactions · public_benchmark = a published figure · assumed = a stated default · unknown = nothing known, the decision does not depend on it</p>
              </>
            )}
            {r.appendix.glossary.length > 0 && (
              <>
                <div className="diag-sub">Terms used in this report</div>
                <div className="diag-table-wrap">
                  <table className="diag-table"><thead><tr><th>In the report</th><th>Internal term</th><th>Meaning</th></tr></thead>
                    <tbody>{r.appendix.glossary.map((g) => <tr key={g.term}><td>{g.term}</td><td className="diag-muted">{g.internal}</td><td>{g.meaning}</td></tr>)}</tbody></table>
                </div>
              </>
            )}
            {r.appendix.warnings.length > 0 && (<><div className="diag-sub">Run notes (verbatim)</div><ul className="diag-small">{r.appendix.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul></>)}
            <div className="diag-sub">Run identity</div>
            <ul className="diag-small">
              <li>run {String(r.appendix.run.run_id)} · generated {String(r.appendix.run.generated_at ?? "")} · report version {String(r.appendix.run.report_version)} · summary version {String(r.appendix.run.summary_version ?? "pre-2026.09.2")}</li>
              <li>internal readiness verdict {String(r.appendix.run.internal_readiness_verdict)} · internal decision {String(r.appendix.run.internal_decision)}: {String(r.appendix.run.internal_reason)}</li>
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="diag-section"><h3 className="diag-h">{title}</h3>{children}</section>;
}

function Links({ related }: { related: ReportRelated[] }) {
  const links = related.map((x) => ({ x, l: hrefFor(x) })).filter((p) => p.l).slice(0, 6);
  if (!links.length) return null;
  return <span className="diag-links">{links.map(({ x, l }) => <Link key={`${x.kind}:${x.id}`} href={l!.href} className="diag-link">{l!.label} <ExternalLink size={11} /></Link>)}</span>;
}

function FindingCard({ f }: { f: ReportFinding }) {
  const [open, setOpen] = useState(false);
  return (
    <article className={`diag-card sev-${f.severity}`} id={`finding-${f.id}`}>
      <div className="diag-card-kicker"><span className={`diag-sev sev-${f.severity}`}>{SEV_LABEL[f.severity] ?? f.severity}</span> · {f.category} · confidence {f.confidence}</div>
      <div className="diag-card-head">{f.headline}</div>
      <p><b>What happened.</b> {f.observation}</p>
      <p><b>Why it matters.</b> {f.business_implication}</p>
      {f.possible_driver && <p><b>Likely cause.</b> <span className={`diag-tag ${f.driver_tag.replace(" ", "-").toLowerCase()}`}>{f.driver_tag}</span> {f.possible_driver}</p>}
      <p><b>What to consider.</b> {f.recommendation}</p>
      <div className="diag-card-foot">
        {f.evidence.length > 0 && (
          <button type="button" className="diag-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
            {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />} Supporting data
          </button>
        )}
        <Links related={f.related} />
      </div>
      {open && (
        <dl className="diag-facts diag-small">
          {f.evidence.map((e) => <div key={e.label}><dt>{e.label}</dt><dd>{e.value}</dd></div>)}
          <div><dt>Basis</dt><dd>{f.confidence_basis}</dd></div>
        </dl>
      )}
    </article>
  );
}

function FoldChart({ chart }: { chart: NonNullable<Report["policy_comparison"]["fold_chart"]> }) {
  const vals = [...chart.selection.map((v, i) => ({ label: `period ${i + 1}`, v, hold: false })), ...(chart.holdout_mean != null ? [{ label: "unseen validation (avg)", v: chart.holdout_mean, hold: true }] : [])];
  const all = vals.map((x) => x.v).concat([0, chart.threshold ?? 0]);
  const lo = Math.min(...all, -0.05), hi = Math.max(...all, 0.05);
  const span = hi - lo || 1;
  const x = (v: number) => ((v - lo) / span) * 100;
  return (
    <figure className="diag-chart">
      <figcaption>{chart.title}</figcaption>
      <div className="diag-chart-body">
        {vals.map((b) => (
          <div key={b.label} className="diag-chart-row">
            <span className="diag-chart-label">{b.label}</span>
            <span className="diag-chart-track">
              <span className="diag-chart-zero" style={{ left: `${x(0)}%` }} />
              {chart.threshold != null && <span className="diag-chart-thr" style={{ left: `${x(chart.threshold)}%` }} title={`threshold ${(chart.threshold * 100).toFixed(0)}%`} />}
              <span className={`diag-chart-bar ${b.hold ? "hold" : b.v >= 0 ? "pos" : "neg"}`} style={{ left: `${Math.min(x(0), x(b.v))}%`, width: `${Math.abs(x(b.v) - x(0))}%` }} />
            </span>
            <span className="diag-chart-val">{b.v >= 0 ? "+" : ""}{(b.v * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
      <p className="diag-muted diag-small">Each bar is one historical period: the candidate's cost change against your policy on that period. Positive = the candidate cost less. The dashed line is the selection threshold; the grey bar is the average on the unseen validation periods.</p>
    </figure>
  );
}
