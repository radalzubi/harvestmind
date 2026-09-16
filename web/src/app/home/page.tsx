"use client";

/**
 * HOME — the executive console. What is happening, and what needs me?
 *
 * One standing, from one ladder (`lib/zaad/standing.ts`), stated once at the top. Everything below
 * it *elaborates* that sentence and is not allowed to contradict it: watches sit underneath a
 * decision rather than beside it as a competing headline, and a network condition never announces
 * itself as a crisis while the plan says nothing needs changing.
 *
 * Then, in reading order: what needs a decision, the shape of the business, where attention is
 * concentrated, what the data needs, and what has happened recently. No KPI is here for its own
 * sake and no table belongs on this page — depth lives in the surfaces built for it.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { ButtonLink, EmptyState, Notice, Section, Tag } from "@/components/workspace/ui";
import { EXTERNAL_LABEL, OUTCOME_METRICS, readHistoryFeed, type HistoryFeed } from "@/lib/zaad/product";
import { PlanGate, RunPlan, ScopeNotice } from "@/components/workspace/PlanState";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { money } from "@/lib/zaad/decisions";
import { attentionAreas } from "@/lib/network/attention";
import { KIND_LABEL } from "@/lib/network/model";
import { standing, type Standing } from "@/lib/zaad/standing";
import { useSession } from "@/lib/session";
import { Onboarding } from "@/components/workspace/Onboarding";
import { COUNT, DATE, MONEY, NUMBER, PERCENT, fetchSummary, listDrafts, track, type DraftSummary, type OperatingSummary } from "@/lib/zaad/product";
import { EMPTY, fetchOverview, linksFor, periodLabel, planSentence, shown, type Overview } from "@/lib/zaad/insights";
import { ChartCard } from "@/components/insights/ChartCard";
import { MultiLine } from "@/components/charts";
import { STATE_LABEL } from "@/lib/zaad/product";
import { operatorWarning } from "@/lib/zaad/warnings";
import { ReadinessLine, useCapabilityReadiness } from "@/components/workspace/Readiness";

function useStanding(): { state: Standing; snapshot: OperatingSummary | null; recent: DraftSummary[] } {
  const data = useWorkspaceData();
  const [snapshot, setSnapshot] = useState<OperatingSummary | null>(null);
  const [recent, setRecent] = useState<DraftSummary[]>([]);

  useEffect(() => {
    if (data.phase !== "ready") return;
    let alive = true;
    fetchSummary(data.request?.as_of?.slice(0, 10)).then((s) => alive && setSnapshot(s)).catch(() => undefined);
    listDrafts({ limit: 5 }).then((d) => alive && setRecent(d.rows)).catch(() => undefined);
    return () => { alive = false; };
  }, [data.phase, data.request]);

  const areas = data.network && data.index ? attentionAreas(data.network, data.index) : [];
  const problems: string[] = [];
  if (data.request && !data.request.pipeline.length) problems.push("No open purchase orders are loaded, so no order change can be evaluated.");
  if (data.directory && !data.directory.suppliers.length) problems.push("No supplier list is loaded, so suppliers show as codes and none can be placed on a map.");
  for (const warning of data.build?.warnings ?? []) {
    const said = operatorWarning(warning);
    if (said && problems.length < 4) problems.push(said);
  }

  return {
    state: standing({
      notReady: data.notReady,
      readError: data.error,
      planPhase: data.planPhase,
      planError: data.planError,
      openDecisions: data.decisions.filter((d) => d.needsReview),
      proposalsAwaitingReview: snapshot?.proposals_awaiting_review ?? 0,
      areas,
      dataProblems: problems,
    }),
    snapshot,
    recent,
  };
}

function Snapshot({ summary }: { summary: OperatingSummary }) {
  const items: Array<{ label: string; value: string; note?: string; href?: string }> = [];
  if (summary.products != null) items.push({ label: "Products", value: NUMBER(summary.products), href: "/inventory" });
  if (summary.inventory_value != null) {
    items.push({
      label: "Stock value", value: MONEY(summary.inventory_value),
      note: summary.snapshot_date ? `as counted ${DATE(summary.snapshot_date)}` : undefined,
      href: "/inventory?sort=inventory_value&dir=desc",
    });
  } else if (summary.on_hand_units != null) {
    items.push({ label: "Units on hand", value: NUMBER(summary.on_hand_units), href: "/inventory" });
  }
  if (summary.open_purchase_orders != null) {
    items.push({
      label: "Open orders", value: NUMBER(summary.open_purchase_orders),
      note: summary.late_purchase_orders ? `${NUMBER(summary.late_purchase_orders)} past their date` : undefined,
      href: "/orders?tab=imported&postate=open",
    });
  }
  if (summary.inbound_units != null) items.push({ label: "Units on order", value: NUMBER(summary.inbound_units), href: "/orders?tab=imported" });
  if (summary.suppliers != null) items.push({ label: "Suppliers", value: NUMBER(summary.suppliers), href: "/diagnostics" });
  if (summary.locations != null && summary.locations > 0) items.push({ label: "Sites", value: NUMBER(summary.locations), href: "/network" });
  if (summary.proposals_open) items.push({ label: "Proposals open", value: NUMBER(summary.proposals_open), href: "/orders" });
  if (!items.length) return null;

  return (
    <Section title="Your business right now" more="Open Inventory" moreHref="/inventory">
      <dl className="snap">
        {items.map((item) => (
          <div key={item.label}>
            <dt>{item.href ? <Link href={item.href} style={{ color: "inherit" }}>{item.label}</Link> : item.label}</dt>
            <dd>{item.value}{item.note && <small>{item.note}</small>}</dd>
          </div>
        ))}
      </dl>
    </Section>
  );
}

/**
 * V2: the closed loop on Home. What needs a person, what has left the building, and the latest
 * thing observed afterwards — from the record, not from the plan. Not project management: five
 * lines, each a link to the place where the work is done.
 */
/**
 * Three summaries from Insights, and no more: what customers ordered over the last twelve weeks,
 * the inventory exposure now, and what was decided. Read from the same server aggregations as the
 * Insights page, so Home and Insights never disagree; the detail lives on Insights.
 */
function Glance() {
  const [data, setData] = useState<Overview | null>(null);
  useEffect(() => {
    let alive = true;
    fetchOverview({ ...EMPTY, bucket: "week" }).then((d) => alive && setData(d)).catch(() => undefined);
    return () => { alive = false; };
  }, []);
  if (!data || !(data.demand.available || data.inventory.available || data.decisions.recommended)) return null;
  const series = data.demand.series.map((p) => ({ label: periodLabel(p.period, "week"), ordered: p.ordered, shipped: p.shipped }));
  const d = data.demand; const inv = data.inventory; const dec = data.decisions;
  const responses = (dec.responses ?? []).reduce((a, r) => a + r.n, 0);
  return (
    <Section title="At a glance" more="Open Insights" moreHref="/insights">
      <div className="ins-grid" style={{ marginTop: 0 }}>
        {d.available && (
          <ChartCard title="Observed customer orders — 12 weeks" description="Orders your customers placed, by week. Not a demand estimate." leads={[{ href: linksFor.insights("demand", {}), label: "Open Demand" }]}>
            <MultiLine data={series} series={[{ key: "ordered", name: "Ordered" }, { key: "shipped", name: "Shipped" }]} height={160} area />
            {d.period_over_period && <p style={{ margin: "4px 0 0", fontSize: 12.5, color: "var(--ink-700)" }}>Last week vs the one before: {shown(d.period_over_period.change_share, (v) => PERCENT(v, 1), "UNKNOWN")}.</p>}
          </ChartCard>
        )}
        {inv.available && inv.position && (
          <ChartCard title="Inventory exposure" description="Units on hand at the latest count, what is inbound on open orders, and the cover that implies." leads={[{ href: linksFor.insights("inventory", {}), label: "Open Inventory insights" }]}>
            <dl className="ins-stat">
              <div><dt>On hand</dt><dd><span className="ins-num">{shown(inv.position.on_hand, NUMBER, "NO_DATA")}</span></dd></div>
              <div><dt>Inbound</dt><dd><span className="ins-num">{shown(inv.position.inbound_units, NUMBER, "NO_DATA")}</span></dd></div>
              <div><dt>Weeks of cover</dt><dd><span className="ins-num">{shown(inv.position.weeks_of_cover, (v) => NUMBER(v, 1), inv.position.cover_reason)}</span></dd></div>
            </dl>
          </ChartCard>
        )}
        {dec.recommended && (
          <ChartCard title="Decisions and actions" description={planSentence(data.plan, DATE)} leads={[{ href: linksFor.insights("decisions", {}), label: "Open Decisions & value" }]}>
            <dl className="ins-stat">
              <div><dt>Recommended</dt><dd><span className="ins-num">{NUMBER(dec.recommended.total)}</span></dd></div>
              <div><dt>Responses</dt><dd><span className="ins-num">{NUMBER(responses)}</span></dd></div>
              <div><dt>Placed externally</dt><dd><span className="ins-num">{NUMBER((dec.external_status ?? []).reduce((a, r) => a + r.n, 0))}</span><small>{NUMBER(dec.outcomes?.recorded)} outcomes recorded</small></dd></div>
            </dl>
          </ChartCard>
        )}
      </div>
    </Section>
  );
}

function ClosedLoop() {
  const [feed, setFeed] = useState<HistoryFeed | null>(null);
  useEffect(() => {
    let alive = true;
    readHistoryFeed().then((f) => alive && setFeed(f)).catch(() => alive && setFeed(null));
    return () => { alive = false; };
  }, []);
  if (!feed) return null;
  const c = feed.counts;
  const latest = feed.outcomes[0];
  const items: Array<{ label: string; value: string; href: string; note?: string }> = [
    { label: "Awaiting approval", value: NUMBER(c.awaiting_approval), href: "/orders?state=READY_FOR_REVIEW" },
    { label: "Approved, not yet recorded as placed", value: NUMBER(c.approved_not_placed), href: "/orders?state=APPROVED&external_status=NONE" },
    { label: "Placed, awaiting acknowledgement", value: NUMBER(c.placed_not_acknowledged), href: "/orders?external_status=PLACED_EXTERNALLY" },
  ];
  if (!items.some((i) => i.value !== "0") && !latest) return null;
  return (
    <Section title="What needs you, and what happened" more="Open History" moreHref="/history">
      <dl className="snap">
        {items.map((item) => (
          <div key={item.label}><dt><Link href={item.href} style={{ color: "inherit" }}>{item.label}</Link></dt><dd>{item.value}{item.note && <small>{item.note}</small>}</dd></div>
        ))}
        {latest && (
          <div><dt><Link href={latest.draft_id ? `/orders/${encodeURIComponent(latest.draft_id)}` : "/history"} style={{ color: "inherit" }}>Latest outcome</Link></dt>
            <dd>{OUTCOME_METRICS[latest.metric]?.label ?? latest.metric}<small>observed after the action{latest.observed_at ? ` · ${DATE(latest.observed_at)}` : ""} · not attributed to ZAAD</small></dd></div>
        )}
      </dl>
    </Section>
  );
}

function StandingLine({ state }: { state: Standing }) {
  const { summary, planPhase } = useWorkspaceData();
  const value = summary?.valueVsCurrent != null && summary.valueVsCurrent > 0
    ? money(summary.valueVsCurrent, summary.currency) : null;
  return (
    <div className="status-line">
      <span className="status-dot"
        data-tone={state.level === "blocked" || state.level === "decide" ? "attention"
          : state.level === "watch" ? "watch" : "ok"}
        aria-hidden />
      <div>
        <span className="lvl" data-level={state.level}><span className="lvl-dot" aria-hidden />{state.label}</span>
        <h1 className="status-head" style={{ marginTop: 4 }}>{state.headline}</h1>
        <p className="status-sub">
          {state.detail}
          {state.level === "decide" && planPhase === "ready" && value && (
            <> Approving them changes the modelled cost of the plan by {value} against keeping things as they are.</>
          )}
        </p>
        {/* With no plan yet the section below carries the run control, where it can name the scope. */}
        {state.next && !(state.level === "normal" && planPhase === "none") && (
          <p style={{ margin: "8px 0 0" }}>
            <Link href={state.next.href} className="zb zb--secondary zb--sm">
              {state.next.label} <ArrowRight size={13} aria-hidden />
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}

function Watches({ state }: { state: Standing }) {
  const { index } = useWorkspaceData();
  if (!state.watches.length || !index) {
    return (
      <Section title="Your network" more="Open the network" moreHref="/network">
        <Notice>Every supplier, lane and site ZAAD can see is running normally.</Notice>
      </Section>
    );
  }
  return (
    <Section title="Worth watching" more="Open the network" moreHref="/network">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 }}>
        {state.watches.slice(0, 4).map((area) => {
          const node = area.lead.type === "node" ? index.nodeById.get(area.lead.id) : null;
          return (
            <Link key={area.id} className="dec" style={{ textDecoration: "none" }}
              href={`/network?${area.lead.type === "node" ? "node" : "edge"}=${encodeURIComponent(area.lead.id)}`}>
              <div className="dec-top">
                <span className="dec-verb" data-tone="change">Watch</span>
                <span className="dec-cat">{node ? KIND_LABEL[node.kind] : "Lane"}</span>
              </div>
              <h3 className="dec-h" style={{ fontSize: 14 }}>{area.title}</h3>
              {/* This was clamped to three lines with `overflow: hidden`. A watch summary names
                  the products with no route to be replenished, and the fourth line is as much a
                  fact as the first — worse, under WCAG 1.4.12's text spacing the same words need
                  more lines and more of them disappear. The cards are grid items that stretch to
                  their row, so letting this one grow costs a little height and no content. */}
              <p className="dec-sub">{area.summary}</p>
            </Link>
          );
        })}
      </div>
    </Section>
  );
}

function HomeBody() {
  const { decisions, computedAt, planPhase, summary, build, request, directory } = useWorkspaceData();
  const { state, snapshot, recent } = useStanding();
  const { readiness } = useCapabilityReadiness();
  useEffect(() => { track("workspace_opened", { surface: "home" }); }, []);
  const open = decisions.filter((d) => d.needsReview);
  const closed = decisions.filter((d) => !d.needsReview);

  const problems: string[] = [];
  if (request && !request.pipeline.length) problems.push("No open purchase orders are loaded, so no order change can be evaluated.");
  if (directory && !directory.suppliers.length) problems.push("No supplier list is loaded, so suppliers show as codes and none can be placed on a map.");
  for (const warning of build?.warnings ?? []) {
    const said = operatorWarning(warning);
    if (said && problems.length < 4) problems.push(said);
  }

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
        <StandingLine state={state} />
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Tag tone="live">Live workspace data</Tag>
          {planPhase !== "none" && <RunPlan label="Run again" role="secondary" />}
        </div>
      </div>

      <div style={{ marginTop: 16, display: "grid", gap: 10 }}><ScopeNotice /></div>

      <Section
        title={open.length ? "Needs your decision" : planPhase === "ready" ? "What ZAAD looked at" : "Your plan"}
        more={planPhase === "ready" && decisions.length > 4 ? "All decisions" : undefined}
        moreHref="/decisions"
      >
        <PlanGate>
          {open.length > 0 ? (
            <div className="dec-list">
              {open.slice(0, 4).map((d) => (
                <Link key={d.id} href={`/decisions?decision=${encodeURIComponent(d.id)}`} style={{ textDecoration: "none", color: "inherit" }}>
                  <div className="dec">
                    <div className="dec-top">
                      <span className="dec-verb" data-tone="change">{d.verb}</span>
                      <span className="dec-cat">{d.category}</span>
                    </div>
                    <h3 className="dec-h">{d.headline}</h3>
                    <p className="dec-sub">{d.target.label}</p>
                    {d.effect.filter((f) => f.value != null).length > 0 && (
                      <div className="dec-facts">
                        {d.effect.filter((f) => f.value != null).slice(0, 3).map((f) => (
                          <span className="dec-fact" key={f.label}>{f.label} <b>{f.value}</b></span>
                        ))}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="Nothing needs changing right now"
              actions={<><ButtonLink href="/decisions">See what was compared</ButtonLink>
                <ButtonLink href="/orders/new">Create a purchase order anyway</ButtonLink></>}>
              {/* "ZAAD reviewed 6 open commitments" sat a screen above "Open orders: 205", with
                  nothing between them saying they are the same kind of thing counted over
                  different scopes. The denominator is on the page already; the sentence uses it. */}
              {closed.length
                ? snapshot?.open_purchase_orders != null && snapshot.open_purchase_orders > closed.length
                  ? `ZAAD reviewed ${NUMBER(closed.length)} of your ${NUMBER(snapshot.open_purchase_orders)} open commitments and the week's purchases`
                  : `ZAAD reviewed ${COUNT(closed.length, "open commitment")} and the week's purchases`
                : "ZAAD reviewed every open commitment and the week's purchases"}{" "}
              against your current plan and found no change worth making.
            </EmptyState>
          )}
        </PlanGate>
      </Section>

      {snapshot && <Snapshot summary={snapshot} />}
      <Glance />

      <Watches state={state} />

      <ClosedLoop />

      {(problems.length > 0 || (readiness && (readiness.summary.blocked > 0 || readiness.summary.partial > 0))) && (
        <Section title="Your data" more="Open Upload" moreHref="/upload">
          <div className="notice" data-tone="warn" style={{ display: "grid", gap: 8 }}>
            {readiness && <ReadinessLine readiness={readiness} />}
            {problems.length > 0 && (
              <ul style={{ margin: 0, paddingInlineStart: 18 }}>
                {problems.map((p, i) => <li key={i}>{p}</li>)}
              </ul>
            )}
          </div>
        </Section>
      )}

      {recent.length > 0 && (
        <Section title="Recent activity" more="All purchase orders" moreHref="/orders">
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 6 }}>
            {recent.map((draft) => (
              <li key={draft.draft_id}>
                <Link href={`/orders/${encodeURIComponent(draft.draft_id)}`}
                  style={{ display: "flex", gap: 10, alignItems: "center", padding: "8px 10px", borderRadius: "var(--radius-sm)",
                    textDecoration: "none", color: "var(--ink-800)", border: "1px solid var(--line)", background: "var(--surface)" }}>
                  <span className="chip">{STATE_LABEL[draft.state]}</span>
                  <span style={{ fontWeight: 500, color: "var(--ink-950)" }}>{draft.reference || draft.draft_id.replace(/^draft_/, "")}</span>
                  <span style={{ color: "var(--ink-500)", fontSize: 12.5 }}>
                    {draft.supplier_id ?? "no supplier"} · {NUMBER(draft.lines)} line{draft.lines === 1 ? "" : "s"}
                  </span>
                  <span style={{ marginInlineStart: "auto", color: "var(--ink-500)", fontSize: 12 }}>{DATE(draft.updated_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {planPhase === "ready" && computedAt && (
        <Section title="This plan">
          <div className="notice">
            {/* `as_of` is midnight UTC. Rendered in the reader's own zone it slid to the previous
                day west of Greenwich, so this sentence said "as at 4 January" while the Value tab,
                which uses DATE(), said "As at 5 Jan 2026" — one date, two days, one product.
                `computedAt` is a wall-clock moment and stays local, which is what it means. */}
            Computed {computedAt.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} from your data as at{" "}
            {summary ? DATE(summary.asOf) : "—"}.
            Approvals you record are kept against that information set. <Link href="/decisions">Review it</Link>.
          </div>
        </Section>
      )}
    </>
  );
}

export default function HomePage() {
  const session = useSession();
  const { phase } = useWorkspaceData();
  // Onboarding is a state of Home, not a destination: a workspace that cannot plan yet gets the
  // next single thing to do instead of an empty console.
  if (session.status === "authenticated" && phase === "not-ready") {
    return (
      <>
        <div className="ws-h"><div><h1>Welcome to ZAAD</h1><p>One more step before ZAAD can tell you what to change.</p></div></div>
        <Onboarding />
      </>
    );
  }
  return (
    <Gate>
      <HomeBody />
    </Gate>
  );
}
