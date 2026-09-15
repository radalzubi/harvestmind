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
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { insightsLinksFor } from "@/lib/zaad/insights";
import { ArrowUpRight, Check, X } from "lucide-react";
import type { Decision, PlanSummary } from "@/lib/zaad/decisions";
import { recordForReview, submitReview } from "@/lib/zaad/client";
import { REASON_CODES, listResponses, respondDecision, track, type DecisionResponse } from "@/lib/zaad/product";
import { useSession } from "@/lib/session";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useToast } from "@/components/Toast";
import { Button, Disclosure, Evidence, Facts, TechnicalDetails } from "./ui";

/** Lifecycle words for a decision, from the operator's response and the proposal it became. */
export const RESPONSE_LABEL: Record<DecisionResponse["status"], string> = {
  REVIEWED: "Reviewed", ACCEPTED: "Accepted", OVERRIDDEN: "Overridden", REJECTED: "Rejected",
};

/**
 * V2: the operator's response to *this* decision, recorded against the plan it came from.
 * Reviewed / accepted / overridden / rejected, with a structured reason when there is one. The
 * recommendation itself is never marked executed: what was actually done lives on the proposal.
 */
function ResponsePanel({ decision }: { decision: Decision }) {
  const session = useSession();
  const { planJobId } = useWorkspaceData();
  const toast = useToast();
  const [existing, setExisting] = useState<DecisionResponse | null>(null);
  const [status, setStatus] = useState<DecisionResponse["status"] | "">("");
  const [code, setCode] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const canRespond = session.can("respondDecision");

  useEffect(() => {
    if (!planJobId) return;
    let alive = true;
    listResponses(planJobId).then((r) => { if (alive) setExisting(r.rows.find((x) => x.decision_id === decision.id) ?? null); })
      .catch(() => { if (alive) setExisting(null); });
    return () => { alive = false; };
  }, [planJobId, decision.id]);

  if (!planJobId) return null;

  async function save() {
    if (!status || !planJobId) return;
    setBusy(true);
    try {
      const saved = await respondDecision({
        job_id: planJobId, decision_id: decision.id, status, recommended: decision.verb,
        target_type: decision.target.type, target_id: decision.target.id,
        reason_code: code || null, reason_text: text.trim() || null,
      });
      setExisting(saved);
      track("decision_opened", { decision_id: decision.id, job_id: planJobId });
      toast.push(`Recorded as ${RESPONSE_LABEL[status].toLowerCase()}. Nothing was sent to a supplier.`);
      setStatus(""); setCode(""); setText("");
    } catch (e) {
      toast.push(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const needsReason = status === "OVERRIDDEN" || status === "REJECTED";
  return (
    <div className="approve" style={{ marginTop: 18 }}>
      <strong style={{ fontSize: 13.5, color: "var(--ink-950)" }}>Your response to this recommendation</strong>
      <p className="zhelp" style={{ marginTop: 4 }}>
        {existing
          ? <>Recorded as <strong>{RESPONSE_LABEL[existing.status]}</strong>{existing.reason_code ? ` — ${REASON_CODES[existing.reason_code] ?? existing.reason_code}` : ""}{existing.reason_text ? `: “${existing.reason_text}”` : ""}{existing.draft_id ? <> · <Link href={`/orders/${encodeURIComponent(existing.draft_id)}`}>the proposal it became</Link></> : ""}.</>
          : "Not yet responded to. A response is your record of what you did about it; the proposal, if you create one, records what actually happened."}
      </p>
      {canRespond && (
        <div style={{ display: "grid", gap: 8, marginTop: 10, maxWidth: 520 }}>
          <div className="chips" role="group" aria-label="Response">
            {(["ACCEPTED", "OVERRIDDEN", "REJECTED", "REVIEWED"] as const).map((s) => (
              <button key={s} type="button" className="chip" aria-pressed={status === s} onClick={() => setStatus(s)}>{RESPONSE_LABEL[s]}</button>
            ))}
          </div>
          {needsReason && (
            <label>
              <span className="fld-label">Why (optional, but useful later)</span>
              <select className="fld fld--block" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Reason">
                <option value="">No particular reason to record</option>
                {Object.entries(REASON_CODES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </label>
          )}
          <input className="fld fld--block" maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Anything to add (optional)" aria-label="Note" />
          <div><Button pending={busy} disabled={!status} onClick={save}>Record response</Button></div>
        </div>
      )}
      {!canRespond && <p className="zhelp">Your role can read this decision but not record a response.</p>}
    </div>
  );
}

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
        <label className="zlabel" htmlFor="review-note">Anything to add <span style={{ color: "var(--ink-500)", fontWeight: 400 }}>(optional)</span></label>
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

/** Action → Insights: the demand, stock, supplier history and value behind this decision, with its filters. */
function InsightsLinks({ decision }: { decision: Decision }) {
  const { request } = useWorkspaceData();
  const links = insightsLinksFor(decision, request);
  const items = [
    links.demand && { href: links.demand, label: "See demand behind this decision" },
    links.inventory && { href: links.inventory, label: "See inventory position" },
    links.supplier && { href: links.supplier, label: "See supplier history" },
    { href: links.value, label: "See value breakdown" },
  ].filter((x): x is { href: string; label: string } => Boolean(x));
  return (
    <p style={{ display: "flex", flexWrap: "wrap", gap: "2px 8px", margin: "8px 0 0", marginInlineStart: -10 }}>
      {items.map((item) => <Link key={item.href} href={item.href} className="zb zb--tertiary zb--sm">{item.label} <ArrowUpRight size={13} aria-hidden /></Link>)}
    </p>
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
      <InsightsLinks decision={decision} />

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

      <ResponsePanel decision={decision} />

      {decision.needsReview && summary && (
        <div style={{ marginTop: 12 }}>
          <Disclosure summary="Record a review of the whole plan" hint="one decision per information set">
            <ReviewPanel summary={summary} openCount={openCount} />
          </Disclosure>
        </div>
      )}
    </div>
  );
}
