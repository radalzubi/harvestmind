"use client";

/**
 * A decision in full, in three layers: what and why in plain words, then the evidence, then
 * the raw report for an analyst. The review control sits at the end of that reading order,
 * so nobody is asked to decide before they have been told anything.
 *
 * On approval: ZAAD's released review model records one human decision per information set —
 * the plan is chosen as a whole against the current plan, so that is what is approved. The
 * panel says so rather than implying a per-line approval the ledger does not hold.
 */
import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Check, X } from "lucide-react";
import type { Decision, PlanSummary } from "@/lib/zaad/decisions";
import { recordForReview, submitReview } from "@/lib/zaad/client";
import { useSession } from "@/lib/session";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useToast } from "@/components/Toast";
import { Button, Disclosure, Evidence, Facts, TechnicalDetails } from "./ui";

const REASONS = [
  "I agree with the recommendation",
  "Commercial constraint",
  "Spoke to the supplier",
  "Customer commitment",
  "Cash priority",
  "Needs more evidence",
];

function ReviewPanel({ summary, openCount }: { summary: PlanSummary; openCount: number }) {
  const session = useSession();
  const { request, refresh } = useWorkspaceData();
  const toast = useToast();
  const [chips, setChips] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<"APPROVED" | "REJECTED" | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const reason = useMemo(() => [...chips, note.trim()].filter(Boolean).join(" — "), [chips, note]);
  const canApprove = session.can("approve");

  async function send(status: "APPROVED" | "REJECTED") {
    if (!request || !reason) return;
    setPending(status);
    try {
      const recorded = await recordForReview(request);
      const result = await submitReview(recorded.decision_id, {
        status, information_hash: summary.informationHash, version: 1, reason,
      });
      setDone(result.status);
      toast.push(status === "APPROVED" ? "Recommendation approved and recorded" : "Recommendation rejected and recorded");
      refresh();
    } catch (e) {
      toast.push(`Could not record your decision: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setPending(null);
    }
  }

  if (done) {
    return (
      <div className="approve" style={{ marginTop: 18 }}>
        <strong style={{ fontSize: 13.5, color: "var(--ink-950)" }}>Recorded as {done.toLowerCase()}.</strong>
        <p className="zhelp">Your decision and its reason are stored against this information set. Nothing was sent to a supplier.</p>
      </div>
    );
  }

  return (
    <div className="approve" style={{ marginTop: 18 }}>
      <strong style={{ fontSize: 13.5, color: "var(--ink-950)" }}>Your decision</strong>
      <p className="zhelp" style={{ marginTop: 4 }}>
        {openCount === 1
          ? "Recording your decision covers this recommendation."
          : `Recording your decision covers all ${openCount} recommendations in this plan — ZAAD chose them together against your current plan.`}
        {" "}ZAAD does not contact your supplier.
      </p>
      <div className="chips" role="group" aria-label="Reason">
        {REASONS.map((r) => (
          <button key={r} type="button" className="chip" aria-pressed={chips.includes(r)}
            onClick={() => setChips((c) => c.includes(r) ? c.filter((x) => x !== r) : [...c, r])}>
            {r}
          </button>
        ))}
      </div>
      <div className="zfield">
        <label className="zlabel" htmlFor="review-note">Anything to add <span style={{ color: "var(--ink-400)", fontWeight: 400 }}>(optional)</span></label>
        <input id="review-note" className="zinput" maxLength={1600} value={note} onChange={(e) => setNote(e.target.value)}
          placeholder="Context for whoever reads this later" />
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
        <Button role="primary" icon={<Check size={14} aria-hidden />} disabled={!canApprove || !reason} pending={pending === "APPROVED"} onClick={() => send("APPROVED")}>
          Approve recommendation
        </Button>
        <Button icon={<X size={14} aria-hidden />} disabled={!canApprove || !reason} pending={pending === "REJECTED"} onClick={() => send("REJECTED")}>
          Reject
        </Button>
      </div>
      {!reason && <p className="zhelp">Pick a reason so the record says why.</p>}
      {!canApprove && <p className="zhelp">Your access can read this workspace but not record decisions.</p>}
    </div>
  );
}

export function DecisionDetail({ decision, summary, openCount }: { decision: Decision; summary: PlanSummary | null; openCount: number }) {
  const twinHref = decision.target.networkId
    ? `/network?${decision.target.networkId.startsWith("lane:") ? "edge" : "node"}=${encodeURIComponent(decision.target.networkId)}&decision=${encodeURIComponent(decision.id)}`
    : null;

  return (
    <div>
      <p style={{ margin: 0, fontSize: 12, color: "var(--ink-500)" }}>{decision.category} · {decision.target.label}</p>
      <h2 style={{ margin: "6px 0 0", fontSize: 19, fontWeight: 600, letterSpacing: "-.02em", color: "var(--ink-950)", lineHeight: 1.3 }}>
        {decision.headline}
      </h2>
      <p style={{ margin: "10px 0 0", fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.6 }}>{decision.summary}</p>

      {twinHref && (
        <Link href={twinHref} className="zb zb--tertiary zb--sm" style={{ marginTop: 10, marginInlineStart: -10 }}>
          View in network <ArrowUpRight size={14} aria-hidden />
        </Link>
      )}

      {decision.effect.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>What changes</h3>
          <Facts items={decision.effect} />
        </div>
      )}

      <div style={{ marginTop: 18 }}>
        <Disclosure summary="Why ZAAD recommends this" hint={decision.why.length ? `${decision.why.length} reason${decision.why.length === 1 ? "" : "s"}` : undefined} defaultOpen>
          {decision.why.length
            ? decision.why.map((w, i) => <p key={i} style={{ margin: 0 }}>{w}</p>)
            : <p className="na">The report gives no reason text for this item.</p>}
          {decision.doNothing && (
            <p style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line-soft)" }}>
              <strong style={{ color: "var(--ink-950)", fontWeight: 500 }}>If you keep the current plan: </strong>
              {decision.doNothing}
            </p>
          )}
        </Disclosure>

        <Disclosure summary="Evidence" hint={`${decision.evidence.length} item${decision.evidence.length === 1 ? "" : "s"}`}>
          <Evidence items={decision.evidence} />
        </Disclosure>

        <TechnicalDetails value={decision.technical} hint="raw report fields" />
      </div>

      {decision.needsReview && summary && <ReviewPanel summary={summary} openCount={openCount} />}
    </div>
  );
}
