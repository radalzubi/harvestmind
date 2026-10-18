/**
 * Comparator labels for plan results (HARDENING V1, H3a).
 *
 * The backend names what the planner compared against (`report.decision_reference`) and what a
 * comparison may claim (`report.comparison`). The frontend repeats those labels; it never decides on
 * its own that the reference is "your current plan". When a report predates the contract the label
 * is a neutral "ZAAD's decision reference", which is true of every report.
 */
import type { ZaadReport } from "./types";

export const NEUTRAL_REFERENCE = "ZAAD's decision reference";

/** The decision reference, lower-case, for use inside a sentence. */
export function referenceLabel(report?: Pick<ZaadReport, "decision_reference"> | null): string {
  const label = report?.decision_reference?.label?.trim();
  return label && label.length > 0 ? label : NEUTRAL_REFERENCE;
}

/** The same label starting a sentence or heading a column. */
export function referenceLabelCap(report?: Pick<ZaadReport, "decision_reference"> | null): string {
  const label = referenceLabel(report);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/** The label of one column of a backend comparison (proposal evaluation), by key. */
export function columnLabel(columns: Array<{ key: string; label: string }> | undefined, key: string, fallback: string): string {
  const hit = columns?.find((c) => c.key === key);
  return hit?.label?.trim() ? hit.label : fallback;
}

/** True when the backend says the comparison may be presented as a claim against the operator. */
export function mayClaimAgainstOperator(report?: Pick<ZaadReport, "comparison"> | null): boolean {
  return report?.comparison?.permissions?.can_claim_against_operator === true;
}
