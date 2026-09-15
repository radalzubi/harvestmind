"use client";

/**
 * DECISIONS — a work queue, not a report archive.
 *
 * The list keeps its place while the detail opens beside it; the selected decision lives in
 * the address bar, so a decision can be sent to a colleague or opened from the network.
 */
import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Gate } from "@/components/workspace/Gate";
import { DecisionCard } from "@/components/workspace/DecisionCard";
import { DecisionDetail } from "@/components/workspace/DecisionDetail";
import { Button, Disclosure, EmptyState, Facts, Notice, PageHead, TechnicalDetails } from "@/components/workspace/ui";
import { PlanGate, RunPlan, ScopeNotice } from "@/components/workspace/PlanState";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useSession } from "@/lib/session";
import { useToast } from "@/components/Toast";
import { bulkBodies, planBulk } from "@/lib/zaad/bulk";
import { createDraftsBulk, listResponses, track, type DecisionResponse } from "@/lib/zaad/product";
import { money, type Decision, type DecisionCategory } from "@/lib/zaad/decisions";

type Filter = "needs-review" | "all" | DecisionCategory;

function PlanEconomics() {
  const { summary } = useWorkspaceData();
  if (!summary) return null;
  const c = summary.currency;
  const priced = summary.costBreakdown.filter((r) => r.delta != null);
  // A component whose difference rounds to nothing has not moved. Printing "+USD 0.00" beside seven
  // of them, under a heading reading "7 components", dressed a plan the engine had kept as a plan
  // that had changed in seven places.
  const moved = priced.filter((r) => Math.abs(r.delta!) >= 0.005);
  const unpriced = summary.valueVsCurrent == null && summary.workingCapitalDelta == null && priced.length === 0;
  return (
    <div className="side" style={{ position: "static" }}>
      <div className="side-h">
        <h2 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>The plan as a whole</h2>
        <p style={{ margin: "4px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>
          ZAAD chooses the plan together, so these are the plan&rsquo;s figures against keeping things as they are.
        </p>
      </div>
      <div className="side-b">
        {unpriced ? (
          <p style={{ margin: 0, fontSize: 13, color: "var(--ink-600)", lineHeight: 1.6 }}>
            ZAAD kept your current plan and priced no alternative against it, so there is no cost
            difference to report. The reasons it gives are under Limits of this plan.
          </p>
        ) : (
          <Facts items={[
            // A difference that rounds to nothing reads as a saving if it is printed as one.
            { label: "Modelled cost change", value: summary.valueVsCurrent == null ? null
                : Math.abs(summary.valueVsCurrent) < 0.005 ? "no difference"
                : `${summary.valueVsCurrent >= 0 ? "saves " : "costs "}${money(Math.abs(summary.valueVsCurrent), c)}` },
            { label: "Cash tied up", value: summary.workingCapitalDelta == null ? null
                : Math.abs(summary.workingCapitalDelta) < 0.005 ? "no difference"
                : `${summary.workingCapitalDelta >= 0 ? "+" : "−"}${money(Math.abs(summary.workingCapitalDelta), c)}` },
          ]} />
        )}
        {summary.service.length > 0 && summary.service.some((x) => x.recommended != null) && (
          <div style={{ marginTop: 14 }}>
            <h3 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>Service to customers</h3>
            <dl className="evid">
              {summary.service.slice(0, 6).map((s) => (
                <div className="evid-row" key={s.id}>
                  <dt>{s.location}</dt>
                  <dd>
                    {s.recommended != null ? `${(s.recommended * 100).toFixed(1)}%` : <span className="na">Not available</span>}
                    {" against a "}{(s.target * 100).toFixed(1)}% target
                    {s.current != null && s.recommended != null && Math.abs(s.current - s.recommended) > 0.0005 &&
                      ` (now ${(s.current * 100).toFixed(1)}%)`}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          {priced.length > 0 && <Disclosure summary="Cost, line by line"
            hint={moved.length
              ? `${moved.length} of ${priced.length} moved`
              : `${priced.length} priced, none moved`}>
            <dl className="evid">
              {priced.map((r) => (
                <div className="evid-row" key={r.component}>
                  <dt>{r.component}</dt>
                  <dd style={{ fontVariantNumeric: "tabular-nums" }}>
                    {Math.abs(r.delta!) < 0.005
                      ? <span className="na">no change</span>
                      : <>{r.delta! >= 0 ? "+" : "−"}{money(Math.abs(r.delta!), c)}</>}
                    <span style={{ color: "var(--ink-500)" }}> ({money(r.current, c)} → {money(r.recommended, c)})</span>
                  </dd>
                </div>
              ))}
            </dl>
          </Disclosure>}
          <Disclosure summary="Limits of this plan" hint={`${summary.limitations.length} stated`}>
            <ul style={{ margin: 0, paddingInlineStart: 18 }}>
              {summary.limitations.map((l, i) => <li key={i} style={{ marginBottom: 4 }}>{l}</li>)}
            </ul>
          </Disclosure>
          <TechnicalDetails value={{ status: summary.status, information_hash: summary.informationHash, as_of: summary.asOf, capabilities: summary.activeCapabilities, reasons: summary.reasons }} hint="information set" />
        </div>
      </div>
    </div>
  );
}

/**
 * Bulk creation: pick purchase recommendations, see exactly which proposals they become (one per
 * supplier and destination, deterministic) and which cannot become one and why, then create them
 * all at once — or nothing. Nothing is sent to a supplier; the proposals start as drafts.
 */
function BulkBar({ decisions, checked, onDone, onClear }: {
  decisions: Decision[]; checked: Set<string>; onDone: (ids: string[]) => void; onClear: () => void;
}) {
  const router = useRouter();
  const toast = useToast();
  const { request } = useWorkspaceData();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chosen = useMemo(() => decisions.filter((d) => checked.has(d.id)), [decisions, checked]);
  const plan = useMemo(() => planBulk(chosen), [chosen]);
  if (chosen.length === 0) return null;

  async function create() {
    setBusy(true); setError(null);
    try {
      const made = await createDraftsBulk(bulkBodies(plan, request?.currency ?? "USD"));
      track("bulk_created", { count: made.created });
      toast.push(`${made.created} proposal${made.created === 1 ? "" : "s"} created as drafts. Nothing has been sent to a supplier.`);
      onDone(made.drafts.map((d) => d.draft_id));
      setOpen(false);
      router.push(made.created === 1 ? `/orders/${encodeURIComponent(made.drafts[0].draft_id)}` : "/orders?state=DRAFT");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  }

  return (
    <div className="notice" style={{ marginBottom: 14, display: "grid", gap: 10 }}>
      <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <strong>{chosen.length} selected</strong>
        <span style={{ color: "var(--ink-600)" }}>
          {plan.groups.length ? `becomes ${plan.groups.length} purchase order${plan.groups.length === 1 ? "" : "s"}` : "none of these can become a purchase order"}
          {plan.asked.length ? ` · ${plan.asked.length} need${plan.asked.length === 1 ? "s" : ""} your attention` : ""}
        </span>
        <div style={{ marginInlineStart: "auto", display: "flex", gap: 8 }}>
          <Button size="sm" role="tertiary" onClick={onClear}>Clear</Button>
          <Button size="sm" role="primary" disabled={!plan.groups.length} onClick={() => setOpen((o) => !o)}>
            {open ? "Hide" : "Review and create"}
          </Button>
        </div>
      </div>
      {open && (
        <div style={{ display: "grid", gap: 10 }}>
          {plan.groups.map((g) => (
            <div key={g.key} style={{ border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "8px 10px", background: "var(--surface)" }}>
              <strong style={{ color: "var(--ink-950)" }}>{g.supplier_id}</strong>
              {g.destination_id && <span style={{ color: "var(--ink-500)" }}> · deliver to {g.destination_id}</span>}
              <ul style={{ margin: "6px 0 0", paddingInlineStart: 18, fontSize: 13 }}>
                {g.lines.map((l) => <li key={l.sku}>{l.sku} — {l.quantity.toLocaleString("en-US")} units{l.unit_price != null ? ` at ${l.unit_price}` : ""}</li>)}
              </ul>
            </div>
          ))}
          {plan.asked.length > 0 && (
            <Notice tone="warn">
              <strong>Not created, and why:</strong>
              <ul style={{ margin: "6px 0 0", paddingInlineStart: 18 }}>
                {plan.asked.map((a) => <li key={a.decision.id}>{a.decision.headline}: {a.reason}</li>)}
              </ul>
            </Notice>
          )}
          {error && <Notice tone="warn">{error}</Notice>}
          <div>
            <Button role="primary" pending={busy} disabled={!plan.groups.length} onClick={create}>
              Create {plan.groups.length} draft{plan.groups.length === 1 ? "" : "s"} — all or none
            </Button>
            <p className="zhelp" style={{ marginTop: 6 }}>Created as drafts for evaluation and approval. ZAAD does not contact your supplier.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function DecisionsBody() {
  const router = useRouter();
  const params = useSearchParams();
  const session = useSession();
  const { decisions, summary } = useWorkspaceData();
  const [checked, setChecked] = useState<Set<string>>(() => new Set());
  const canCreate = session.can("createProposal");
  // The operator's responses in this plan, so each card carries where it stands (accepted,
  // overridden, rejected, reviewed) and whether a proposal was raised from it.
  const { planJobId } = useWorkspaceData();
  const [responses, setResponses] = useState<Map<string, DecisionResponse>>(() => new Map());
  useEffect(() => {
    if (!planJobId) { setResponses(new Map()); return; }
    let alive = true;
    listResponses(planJobId).then((r) => { if (alive) setResponses(new Map(r.rows.map((x) => [x.decision_id, x]))); })
      .catch(() => { if (alive) setResponses(new Map()); });
    return () => { alive = false; };
  }, [planJobId]);
  const selectable = useMemo(() => new Set(decisions.filter((d) => d.id.startsWith("buy:") && d.needsReview).map((d) => d.id)), [decisions]);
  const open = useMemo(() => decisions.filter((d) => d.needsReview), [decisions]);
  // Opening on an empty "Needs review" while six decisions sit behind "All" reads as a fault.
  const [filter, setFilter] = useState<Filter | null>(null);
  const active: Filter = filter ?? (open.length ? "needs-review" : "all");
  const selectedId = params.get("decision");
  const categories = useMemo(
    () => [...new Set(decisions.map((d) => d.category))] as DecisionCategory[],
    [decisions],
  );

  const linked = useMemo(() => decisions.find((d) => d.id === selectedId) ?? null, [decisions, selectedId]);

  const shown = useMemo(() => {
    const base = active === "all" ? decisions : active === "needs-review" ? open : decisions.filter((d) => d.category === active);
    // A decision someone was sent a link to stays visible even when the filter would hide it,
    // rather than the filter silently changing under them.
    return linked && !base.includes(linked) ? [linked, ...base] : base;
  }, [decisions, open, active, linked]);

  const selected: Decision | null = linked ?? shown[0] ?? null;
  // A link to a decision this plan does not contain used to open a *different* decision, under a
  // heading that said "Selected decision" — the address bar naming one order and the panel showing
  // another. A colleague following that link would read the wrong order's reasoning.
  const askedForMissing = Boolean(selectedId && !linked);

  const select = (id: string) => {
    const q = new URLSearchParams(params.toString());
    q.set("decision", id);
    router.replace(`/decisions?${q}`, { scroll: false });
  };

  return (
    <>
      <div role="tablist" aria-label="Filter decisions" style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {([["needs-review", `Needs review${open.length ? ` (${open.length})` : ""}`], ["all", `All (${decisions.length})`], ...categories.map((c) => [c, c] as const)] as Array<[Filter, string]>)
          .map(([id, label]) => (
            <button key={id} role="tab" aria-selected={active === id} className="chip" onClick={() => setFilter(id)}
              style={active === id ? { background: "var(--ink-950)", color: "#fff", borderColor: "var(--ink-950)" } : undefined}>
              {label}
            </button>
          ))}
      </div>

      {canCreate && selectable.size > 1 && checked.size === 0 && (
        <p className="zhelp" style={{ marginBottom: 10 }}>Tick purchase recommendations to create several proposed orders at once.</p>
      )}
      <BulkBar decisions={decisions} checked={checked} onClear={() => setChecked(new Set())} onDone={() => setChecked(new Set())} />

      <div className="split-list">
        <div className="dec-list">
          {shown.length === 0 && (
            <EmptyState title={active === "needs-review" ? "Nothing needs changing right now" : "Nothing in this group"}>
              {active === "needs-review"
                ? "ZAAD compared your current plan against every alternative it could build and found no change worth making."
                : "Switch the filter to see everything ZAAD looked at."}
            </EmptyState>
          )}
          {shown.map((d) => (
            <DecisionCard key={d.id} decision={d} selected={selected?.id === d.id} onSelect={select}
              response={responses.get(d.id) ?? null}
              checked={checked.has(d.id)}
              onCheck={canCreate && selectable.has(d.id)
                ? (id, next) => setChecked((c) => { const n = new Set(c); if (next) n.add(id); else n.delete(id); return n; })
                : undefined} />
          ))}
        </div>

        <div>
          {selected ? (
            <div className="side">
              <div className="side-h" style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                <strong style={{ fontSize: 12, color: "var(--ink-500)", fontWeight: 500 }}>Selected decision</strong>
              </div>
              <div className="side-b">
                {askedForMissing && (
                  <div style={{ marginBottom: 12 }}>
                    <Notice tone="warn">
                      The decision this link points at is not in the plan on screen. It may have been
                      part of an earlier run, or cover a product this run did not. What is shown
                      below is the first decision in the list, not the one that was asked for.
                    </Notice>
                  </div>
                )}
                <DecisionDetail decision={selected} summary={summary} openCount={open.length} />
              </div>
            </div>
          ) : (
            <PlanEconomics />
          )}
          {selected && <div style={{ marginTop: 14 }}><PlanEconomics /></div>}
        </div>
      </div>
    </>
  );
}

/**
 * The page's own heading and its run control, outside the plan gate.
 *
 * They used to be inside it, so while a run was in flight the page had no title, no scope notice
 * and no way to do anything — a surface that erases itself for the minutes it is working is worse
 * than one that says what it is doing.
 */
function DecisionsHeader() {
  const { decisions, planPhase } = useWorkspaceData();
  const open = decisions.filter((d) => d.needsReview);
  return (
    <>
      <PageHead
        title="Decisions"
        sub={planPhase !== "ready"
          ? "What ZAAD recommends changing, and why."
          : open.length
            ? `${open.length} recommendation${open.length === 1 ? "" : "s"} waiting on you. ZAAD records your answer; it never contacts a supplier.`
            : "ZAAD found nothing worth changing. Everything it compared is listed here."}
        // With no plan yet the gate below already offers the run, sized; a second copy of the same
        // control in the header is one control too many. Home does the same.
        actions={planPhase !== "none" ? <RunPlan label="Run again" role="secondary" /> : undefined}
      />
      <div style={{ marginBottom: 14, display: "grid", gap: 10 }}><ScopeNotice /></div>
    </>
  );
}

export default function DecisionsPage() {
  return (
    <Gate>
      <Suspense fallback={null}>
        <DecisionsHeader />
        <PlanGate>
          <DecisionsBody />
        </PlanGate>
      </Suspense>
    </Gate>
  );
}
