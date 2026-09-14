"use client";

/**
 * A decision as a row: enough to decide whether to open it, never so much that opening it
 * is a disappointment. One click opens the detail beside the list; the list keeps its place.
 */
import type { Decision } from "@/lib/zaad/decisions";

const CHANGE = new Set(["DEFER", "EXPEDITE", "CANCEL", "REDUCE", "SPLIT", "BUY MORE", "BUY LESS", "MOVE", "HOLD"]);

export function DecisionCard({ decision, selected, onSelect }: {
  decision: Decision; selected?: boolean; onSelect: (id: string) => void;
}) {
  const facts = decision.effect.filter((f) => f.value != null).slice(0, 3);
  return (
    <button
      className="dec" data-selected={selected ? "true" : undefined}
      onClick={() => onSelect(decision.id)}
      aria-label={`${decision.headline}. Open the full explanation.`}
    >
      <div className="dec-top">
        <span className="dec-verb" data-tone={decision.verb === "KEEP" ? "keep" : CHANGE.has(decision.verb) ? "change" : undefined}>
          {decision.verb}
        </span>
        <span className="dec-cat">{decision.category}</span>
        {!decision.needsReview && <span className="dec-cat" style={{ marginInlineStart: "auto" }}>No action needed</span>}
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
