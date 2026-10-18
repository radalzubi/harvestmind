/**
 * Replay labels for the diagnostic report (HARDENING V1, H3a).
 *
 * Every name for the historical-action path and the rule comes from the backend's comparator contract
 * (`comparator_label`, `reference_label`, `periods.caption`). A report produced before the contract never
 * established that its historical-action leg was exact, so it is described as not established, never as
 * the operator's own orders. Nothing here decides fidelity.
 */
export interface ReplayLabelInput {
  comparator_label?: string | null;
  reference_label?: string | null;
  comparison?: { comparator?: { type?: string; fidelity?: string; label?: string | null } | null; permissions?: Record<string, boolean | undefined> } | null;
  periods?: { caption?: string | null } | null;
}

export interface ReplayLabels {
  actionLabel: string;
  actionHeader: string;
  referenceLabel: string;
  referenceHeader: string;
  periodCaption: string;
  serviceHeader: string;
  endStockHeader: string;
}

const NOT_ESTABLISHED = "the recorded historical orders as the replay evaluated them (comparator fidelity not established)";

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function replayLabels(rp: ReplayLabelInput | null | undefined): ReplayLabels {
  const actionLabel = rp?.comparator_label?.trim() || NOT_ESTABLISHED;
  const referenceLabel = rp?.reference_label?.trim() || "the reconstructed rule";
  const fidelity = rp?.comparison?.comparator?.fidelity;
  // only an EXACT comparator may be shortened to "recorded historical orders" in a column header
  const short = fidelity === "EXACT" ? "recorded historical orders" : "historical-action path";
  return {
    actionLabel,
    actionHeader: cap(actionLabel),
    referenceLabel,
    referenceHeader: cap(referenceLabel),
    periodCaption: rp?.periods?.caption?.trim() || `Cost difference per decision date: ${actionLabel} − ZAAD (positive = ZAAD cost less)`,
    serviceHeader: `Service (${short} / ZAAD)`,
    endStockHeader: `End stock (${short} / ZAAD)`,
  };
}
