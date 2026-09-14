"use client";

/**
 * DECISIONS — a work queue, not a report archive.
 *
 * The list keeps its place while the detail opens beside it; the selected decision lives in
 * the address bar, so a decision can be sent to a colleague or opened from the network.
 */
import { Suspense, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Gate } from "@/components/workspace/Gate";
import { DecisionCard } from "@/components/workspace/DecisionCard";
import { DecisionDetail } from "@/components/workspace/DecisionDetail";
import { Disclosure, EmptyState, Facts, PageHead, TechnicalDetails } from "@/components/workspace/ui";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { money, type Decision, type DecisionCategory } from "@/lib/zaad/decisions";

type Filter = "needs-review" | "all" | DecisionCategory;

function PlanEconomics() {
  const { summary } = useWorkspaceData();
  if (!summary) return null;
  const c = summary.currency;
  const priced = summary.costBreakdown.filter((r) => r.delta != null);
  return (
    <div className="side" style={{ position: "static" }}>
      <div className="side-h">
        <h2 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>The plan as a whole</h2>
        <p style={{ margin: "4px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>
          ZAAD chooses the plan together, so these are the plan&rsquo;s figures against keeping things as they are.
        </p>
      </div>
      <div className="side-b">
        <Facts items={[
          { label: "Modelled cost change", value: summary.valueVsCurrent != null ? `${summary.valueVsCurrent >= 0 ? "saves " : "costs "}${money(Math.abs(summary.valueVsCurrent), c)}` : null },
          { label: "Cash tied up", value: summary.workingCapitalDelta != null ? `${summary.workingCapitalDelta >= 0 ? "+" : "−"}${money(Math.abs(summary.workingCapitalDelta), c)}` : null },
        ]} />
        {summary.service.length > 0 && (
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
          <Disclosure summary="Cost, line by line" hint={`${priced.length} components`}>
            <dl className="evid">
              {priced.map((r) => (
                <div className="evid-row" key={r.component}>
                  <dt>{r.component}</dt>
                  <dd style={{ fontVariantNumeric: "tabular-nums" }}>
                    {r.delta! >= 0 ? "+" : "−"}{money(Math.abs(r.delta!), c)}
                    <span style={{ color: "var(--ink-400)" }}> ({money(r.current, c)} → {money(r.recommended, c)})</span>
                  </dd>
                </div>
              ))}
            </dl>
          </Disclosure>
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

function DecisionsBody() {
  const router = useRouter();
  const params = useSearchParams();
  const { decisions, summary } = useWorkspaceData();
  const [filter, setFilter] = useState<Filter>("needs-review");
  const selectedId = params.get("decision");

  const open = useMemo(() => decisions.filter((d) => d.needsReview), [decisions]);
  const categories = useMemo(
    () => [...new Set(decisions.map((d) => d.category))] as DecisionCategory[],
    [decisions],
  );

  const linked = useMemo(() => decisions.find((d) => d.id === selectedId) ?? null, [decisions, selectedId]);

  const shown = useMemo(() => {
    const base = filter === "all" ? decisions : filter === "needs-review" ? open : decisions.filter((d) => d.category === filter);
    // A decision someone was sent a link to stays visible even when the filter would hide it,
    // rather than the filter silently changing under them.
    return linked && !base.includes(linked) ? [linked, ...base] : base;
  }, [decisions, open, filter, linked]);

  const selected: Decision | null = linked ?? shown[0] ?? null;

  const select = (id: string) => {
    const q = new URLSearchParams(params.toString());
    q.set("decision", id);
    router.replace(`/decisions?${q}`, { scroll: false });
  };

  return (
    <>
      <PageHead
        title="Decisions"
        sub={open.length
          ? `${open.length} recommendation${open.length === 1 ? "" : "s"} waiting on you. ZAAD records your answer; it never contacts a supplier.`
          : "ZAAD found nothing worth changing. Everything it compared is listed here."}
      />

      <div role="tablist" aria-label="Filter decisions" style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 14 }}>
        {([["needs-review", `Needs review${open.length ? ` (${open.length})` : ""}`], ["all", `All (${decisions.length})`], ...categories.map((c) => [c, c] as const)] as Array<[Filter, string]>)
          .map(([id, label]) => (
            <button key={id} role="tab" aria-selected={filter === id} className="chip" onClick={() => setFilter(id)}
              style={filter === id ? { background: "var(--ink-950)", color: "#fff", borderColor: "var(--ink-950)" } : undefined}>
              {label}
            </button>
          ))}
      </div>

      <div className="split-list">
        <div className="dec-list">
          {shown.length === 0 && (
            <EmptyState title={filter === "needs-review" ? "Nothing needs changing right now" : "Nothing in this group"}>
              {filter === "needs-review"
                ? "ZAAD compared your current plan against every alternative it could build and found no change worth making."
                : "Switch the filter to see everything ZAAD looked at."}
            </EmptyState>
          )}
          {shown.map((d) => (
            <DecisionCard key={d.id} decision={d} selected={selected?.id === d.id} onSelect={select} />
          ))}
        </div>

        <div>
          {selected ? (
            <div className="side">
              <div className="side-h" style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
                <strong style={{ fontSize: 12, color: "var(--ink-500)", fontWeight: 500 }}>Selected decision</strong>
              </div>
              <div className="side-b">
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

export default function DecisionsPage() {
  return (
    <Gate>
      <Suspense fallback={null}>
        <DecisionsBody />
      </Suspense>
    </Gate>
  );
}
