"use client";

/**
 * A decision as a row: enough to decide whether to open it, never so much that opening it
 * is a disappointment. One click opens the detail beside the list; the list keeps its place.
 */
import type { Decision } from "@/lib/zaad/decisions";

const CHANGE = new Set(["DEFER", "EXPEDITE", "CANCEL", "REDUCE", "SPLIT", "BUY MORE", "BUY LESS", "MOVE", "HOLD"]);

/** Lifecycle words for the chip on a card: what the operator recorded about this recommendation. */
const RESPONSE_CHIP: Record<string, { label: string; tone?: "good" | "warn" | "bad" }> = {
  ACCEPTED: { label: "Accepted", tone: "good" }, OVERRIDDEN: { label: "Overridden", tone: "warn" },
  REJECTED: { label: "Rejected", tone: "bad" }, REVIEWED: { label: "Reviewed" },
};

export function DecisionCard({ decision, selected, onSelect, checked, onCheck, response }: {
  decision: Decision; selected?: boolean; onSelect: (id: string) => void;
  /** When given, the card carries a checkbox for bulk creation; `undefined` means no selection mode. */
  checked?: boolean; onCheck?: (id: string, next: boolean) => void;
  /** The operator's recorded response to this decision in the current plan, when there is one. */
  response?: { status: string; draft_id?: string | null } | null;
}) {
  const facts = decision.effect.filter((f) => f.value != null).slice(0, 3);
  return (
    <button
      className="dec" data-selected={selected ? "true" : undefined}
      onClick={() => onSelect(decision.id)}
      aria-label={`${decision.headline}. Open the full explanation.`}
    >
      <div className="dec-top">
        {onCheck && (
          <input type="checkbox" checked={Boolean(checked)} aria-label={`Select ${decision.headline} for a purchase order`}
            onClick={(e) => e.stopPropagation()} onChange={(e) => onCheck(decision.id, e.target.checked)}
            style={{ marginInlineEnd: 6 }} />
        )}
        <span className="dec-verb" data-tone={decision.verb === "KEEP" ? "keep" : CHANGE.has(decision.verb) ? "change" : undefined}>
          {decision.verb}
        </span>
        <span className="dec-cat">{decision.category}</span>
        {response && RESPONSE_CHIP[response.status] && (
          <span className="chip" data-tone={RESPONSE_CHIP[response.status].tone} style={{ marginInlineStart: "auto" }}>
            {RESPONSE_CHIP[response.status].label}{response.draft_id ? " · proposal raised" : ""}
          </span>
        )}
        {!decision.needsReview && !response && <span className="dec-cat" style={{ marginInlineStart: "auto" }}>No action needed</span>}
      </div>
      <h3 className="dec-h">{decision.headline}</h3>
      <p className="dec-sub">{decision.target.label}</p>
      {facts.length > 0 && (
        <div className="dec-facts">
          {facts.map((f) => <span className="dec-fact" key={f.label}>{f.label} <b>{f.value}</b></span>)}
        </div>
      )}
    </button>
  );
}
