"use client";

/**
 * HOME — what needs attention right now.
 *
 * Reading order is the priority order: the one-line standing of the business, the decisions
 * waiting on a person, where attention is concentrated in the network, then data only when
 * data needs something. Nothing here is a KPI for its own sake.
 */
import Link from "next/link";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, EmptyState, Section, Tag } from "@/components/workspace/ui";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { money } from "@/lib/zaad/decisions";
import { attentionAreas, statusLine } from "@/lib/network/attention";
import { STATE_LABEL } from "@/lib/network/model";
import { useSession } from "@/lib/session";
import { Onboarding } from "@/components/workspace/Onboarding";

function Standing() {
  const { decisions, summary, network, index } = useWorkspaceData();
  const open = decisions.filter((d) => d.needsReview);
  const areas = network && index ? attentionAreas(network, index) : [];
  const line = statusLine(areas);
  const tone = open.length ? (areas.some((a) => a.level === "attention") ? "attention" : "watch") : line.tone;

  const headline = open.length === 0
    ? "Nothing needs changing right now."
    : open.length === 1
      ? "One thing needs your decision."
      : `${open.length} things need your decision.`;

  const value = summary?.valueVsCurrent != null && summary.valueVsCurrent > 0
    ? money(summary.valueVsCurrent, summary.currency)
    : null;

  return (
    <div className="status-line">
      <span className="status-dot" data-tone={tone} aria-hidden />
      <div>
        <h1 className="status-head">{headline}</h1>
        <p className="status-sub">
          {open.length === 0
            ? "ZAAD compared your current plan against every alternative it can build and found nothing worth changing. Everything below is for reference."
            : <>Approving them changes the modelled cost of the next {summary?.service.length ? "period" : "plan"} by {value ?? "an amount the report does not price"} against keeping things as they are.{" "}
              {line.headline === "Everything looks normal" ? "Your network is otherwise running normally." : `${line.headline} in the network.`}</>}
        </p>
      </div>
    </div>
  );
}

function AttentionStrip() {
  const { network, index } = useWorkspaceData();
  if (!network || !index) return null;
  const areas = attentionAreas(network, index).slice(0, 4);
  if (!areas.length) {
    return (
      <Section title="Your network">
        <div className="notice">
          Every supplier, lane and site ZAAD can see is running normally.{" "}
          <Link href="/network">Open the network</Link> to look at it.
        </div>
      </Section>
    );
  }
  return (
    <Section title="Where attention is concentrated" more="Open the network" moreHref="/network">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 10 }}>
        {areas.map((a) => {
          const node = a.lead.type === "node" ? index.nodeById.get(a.lead.id) : null;
          const edge = a.lead.type === "edge" ? index.edgeById.get(a.lead.id) : null;
          const state = node?.state ?? edge?.state ?? "LEAN";
          return (
            <Link
              key={a.id}
              href={`/network?${a.lead.type === "node" ? "node" : "edge"}=${encodeURIComponent(a.lead.id)}`}
              className="dec" style={{ textDecoration: "none" }}
            >
              <div className="dec-top">
                <span className="dec-verb" data-tone={a.level === "attention" ? "change" : undefined}>
                  {a.level === "attention" ? "Needs attention" : "Watch"}
                </span>
                <span className="dec-cat">{STATE_LABEL[state]}</span>
              </div>
              <h3 className="dec-h" style={{ fontSize: 14 }}>{a.title}</h3>
              <p className="dec-sub" style={{ display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{a.summary}</p>
            </Link>
          );
        })}
      </div>
    </Section>
  );
}

function DataStrip() {
  const { build, request, directory } = useWorkspaceData();
  const problems: string[] = [];
  if (!request?.pipeline.length) problems.push("No open purchase orders are loaded, so no order change can be evaluated.");
  if (!directory?.suppliers.length) problems.push("No supplier list is loaded, so suppliers show as ids and none can be placed on a map.");
  for (const w of (build?.warnings ?? []).slice(0, 2)) problems.push(w);
  if (!problems.length) return null;
  return (
    <Section title="Your data" more="Open Data" moreHref="/data">
      <div className="notice" data-tone="warn">
        <ul style={{ margin: 0, paddingInlineStart: 18 }}>
          {problems.map((p, i) => <li key={i}>{p}</li>)}
        </ul>
      </div>
    </Section>
  );
}

function HomeBody() {
  const { decisions, summary, computedAt, refresh } = useWorkspaceData();
  const open = decisions.filter((d) => d.needsReview);
  const closed = decisions.filter((d) => !d.needsReview);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
        <Standing />
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Tag tone="live">Live workspace data</Tag>
          <Button role="tertiary" size="sm" onClick={refresh}>Re-run</Button>
        </div>
      </div>

      <Section title={open.length ? "Needs your decision" : "What ZAAD looked at"} more={decisions.length > 4 ? "All decisions" : undefined} moreHref="/decisions">
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
          <EmptyState title="Nothing needs changing right now" actions={<ButtonLink href="/decisions">See what was compared</ButtonLink>}>
            ZAAD reviewed {closed.length || "every"} open commitment and the week&rsquo;s purchases against your current plan and found no change worth making.
          </EmptyState>
        )}
      </Section>

      <AttentionStrip />
      <DataStrip />

      <Section title="Recent decisions">
        <div className="notice">
          {computedAt
            ? <>This plan was computed at {computedAt.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} from data as at {summary ? new Date(summary.asOf).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "—"}.
              Approvals you record are kept against that information set.</>
            : "No plan has been computed in this session yet."}
          {" "}<Link href="/decisions">Review the current plan</Link>.
        </div>
      </Section>
    </>
  );
}

export default function HomePage() {
  const session = useSession();
  const { phase } = useWorkspaceData();
  // Onboarding is a state of Home, not a destination: a workspace that cannot plan yet gets
  // the next single thing to do instead of an empty console.
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
