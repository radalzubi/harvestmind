"use client";

/**
 * HISTORY — what ZAAD recommended, what we did about it, what left the building, what happened
 * afterwards, and what all of it was worth — in five registers that are never collapsed into one.
 *
 * Nothing on this page is a claim that ZAAD caused anything. A modelled difference is two engine
 * runs; an operator-approved expected difference is the comparison an approver saw; a realized
 * outcome is what a person observed after an action; realized savings need a comparator with its
 * basis stated; and a backtested opportunity does not exist in this product, which it says.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { Gate } from "@/components/workspace/Gate";
import { EmptyState, ErrorState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { DataTable, NotAvailable } from "@/components/workspace/Table";
import { RESPONSE_LABEL } from "@/components/workspace/DecisionDetail";
import {
  DATE, EXTERNAL_LABEL, MONEY, NUMBER, OUTCOME_METRICS, PERCENT, REASON_CODES, STATE_LABEL, readHistoryFeed, track,
  type HistoryFeed, type Outcome,
} from "@/lib/zaad/product";

function Registers({ feed }: { feed: HistoryFeed }) {
  return (
    <Section title="Five kinds of value, kept apart">
      <dl className="kv">
        <dt>Modelled difference</dt>
        <dd>What two engine runs over one information set project, before anything happens. Shown on each proposal's comparison.</dd>
        <dt>Backtested opportunity</dt>
        <dd><NotAvailable why={feed.backtested.note} /> {feed.backtested.note}</dd>
        <dt>Operator-approved expected difference</dt>
        <dd>The comparison an approver saw when they approved — recorded with the approval, and marked when it was already out of date.</dd>
        <dt>Realized outcome</dt>
        <dd>What a person observed after an action, or what receipts matched. Observed after the action; not attributed to ZAAD.</dd>
        <dt>Realized savings</dt>
        <dd>Only where an observation carries a comparator with its basis stated. Otherwise absent, not estimated.</dd>
      </dl>
    </Section>
  );
}

function fmt(metric: string, v: number | null, currency = "USD") {
  if (v == null) return "—";
  const kind = OUTCOME_METRICS[metric]?.unit;
  return kind === "money" ? MONEY(v, currency) : kind === "fraction" ? PERCENT(v) : NUMBER(v);
}

function HistoryBody() {
  const [feed, setFeed] = useState<HistoryFeed | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    readHistoryFeed().then((f) => { if (alive) { setFeed(f); track("history_opened"); } }).catch((e) => alive && setError(e instanceof Error ? e.message : String(e)));
    return () => { alive = false; };
  }, []);

  if (error) return <ErrorState title="History could not be read" affects="Nothing was changed." whatToDo="Reload the page." detail={error} />;
  if (!feed) return <Loading label="Reading your decision history…" cards={3} />;

  const c = feed.counts;
  return (
    <>
      <Section title="Where things stand">
        <dl className="snap">
          <div><dt><Link href="/orders?state=READY_FOR_REVIEW" style={{ color: "inherit" }}>Awaiting approval</Link></dt><dd>{NUMBER(c.awaiting_approval)}</dd></div>
          <div><dt><Link href="/orders?external_status=NONE&state=APPROVED" style={{ color: "inherit" }}>Approved, not yet placed</Link></dt><dd>{NUMBER(c.approved_not_placed)}<small>as far as anyone has recorded</small></dd></div>
          <div><dt><Link href="/orders?external_status=PLACED_EXTERNALLY" style={{ color: "inherit" }}>Placed, awaiting acknowledgement</Link></dt><dd>{NUMBER(c.placed_not_acknowledged)}</dd></div>
          <div><dt>Responses to decisions</dt><dd>{NUMBER(c.responses)}</dd></div>
          <div><dt>Outcomes observed</dt><dd>{NUMBER(c.outcomes_recorded)}</dd></div>
        </dl>
      </Section>

      <Section title="What ZAAD recommended, and what you did about it">
        {feed.responses.length === 0 ? (
          <EmptyState title="No decision has been responded to yet">Open a recommendation on Decisions and record whether you accepted, overrode or rejected it.</EmptyState>
        ) : (
          <DataTable caption="Responses to decisions, newest first" dense rows={feed.responses} rowKey={(r) => r.response_id}
            columns={[
              { key: "updated_at", label: "When", render: (r) => DATE(r.updated_at) },
              { key: "recommended", label: "ZAAD recommended", render: (r) => r.recommended ?? <span className="na">—</span> },
              { key: "target", label: "On", render: (r) => r.target_id ? <Link href={`/decisions?decision=${encodeURIComponent(r.decision_id)}`}>{r.target_id}</Link> : r.decision_id },
              { key: "status", label: "Response", render: (r) => <span className="chip" data-tone={r.status === "ACCEPTED" ? "good" : r.status === "REJECTED" ? "bad" : r.status === "OVERRIDDEN" ? "warn" : undefined}>{RESPONSE_LABEL[r.status]}</span> },
              { key: "reason", label: "Why", render: (r) => r.reason_code ? `${REASON_CODES[r.reason_code] ?? r.reason_code}${r.reason_text ? ` — ${r.reason_text}` : ""}` : (r.reason_text ?? <span className="na">none given</span>) },
              { key: "draft", label: "Became", render: (r) => r.draft_id ? <Link href={`/orders/${encodeURIComponent(r.draft_id)}`}>a proposal</Link> : <span className="na">—</span> },
              { key: "actor", label: "By", render: (r) => r.actor ?? "—" },
            ]} />
        )}
      </Section>

      <Section title="Proposals decided, and where they are now">
        {feed.decided.length === 0 ? (
          <EmptyState title="Nothing has been approved or rejected yet">Approvals and rejections appear here with what was recorded afterwards.</EmptyState>
        ) : (
          <DataTable caption="Approved, exported and rejected proposals" dense rows={feed.decided} rowKey={(r) => r.draft_id}
            columns={[
              { key: "reference", label: "Order", render: (r) => <Link href={`/orders/${encodeURIComponent(r.draft_id)}`}>{r.reference || r.draft_id.replace(/^draft_/, "")}</Link> },
              { key: "state", label: "Decision", render: (r) => STATE_LABEL[r.state] },
              { key: "against", label: "Approved against", render: (r) => r.approval_evaluation_state === "current" ? "a current evaluation" : r.approval_evaluation_state === "stale_acknowledged" ? "an out-of-date evaluation, acknowledged" : r.approval_evaluation_state === "none" ? "no evaluation" : <span className="na">not recorded</span> },
              { key: "external", label: "Outside ZAAD", render: (r) => r.external_status ? `${EXTERNAL_LABEL[r.external_status]}${r.external_reference ? ` · ${r.external_reference}` : ""}` : <span className="na">nothing recorded yet</span> },
              { key: "when", label: "When", render: (r) => DATE(r.approved_at ?? r.updated_at) },
              { key: "by", label: "By", render: (r) => r.approved_by ?? "—" },
            ]} />
        )}
      </Section>

      <Section title="What happened afterwards">
        <Notice>Observed after the action, as recorded by a person or matched from your receipts. Not attributed to ZAAD.</Notice>
        {feed.outcomes.length === 0 ? (
          <div style={{ marginTop: 10 }}><EmptyState title="No outcome has been observed yet">Record what arrived, when and at what cost on an approved proposal.</EmptyState></div>
        ) : (
          <div style={{ marginTop: 10 }}>
            <DataTable caption="Observations, newest first" dense rows={feed.outcomes} rowKey={(r: Outcome) => r.outcome_id}
              columns={[
                { key: "draft", label: "Order", render: (r) => r.draft_id ? <Link href={`/orders/${encodeURIComponent(r.draft_id)}`}>{r.draft_id.replace(/^draft_/, "")}</Link> : "—" },
                { key: "metric", label: "What", render: (r) => OUTCOME_METRICS[r.metric]?.label ?? r.metric },
                { key: "value", label: "Observed", numeric: true, render: (r) => fmt(r.metric, r.value) },
                { key: "observed_at", label: "When", render: (r) => r.observed_at ? DATE(r.observed_at) : <span className="na">—</span> },
                { key: "source", label: "How", render: (r) => r.source === "matched" ? "matched from receipts" : "recorded by a person" },
                { key: "comparator", label: "Realized saving?", render: (r) => r.comparator_value != null && r.comparator_basis
                  ? `against ${fmt(r.metric, r.comparator_value)} (${r.comparator_basis})` : <span className="na">no comparator — an observation only</span> },
              ]} />
          </div>
        )}
      </Section>

      <Registers feed={feed} />
    </>
  );
}

export default function HistoryPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <PageHead title="History" sub="What ZAAD recommended, what you did, what left the building, and what happened afterwards." />
      <HistoryBody />
    </Gate>
  );
}
