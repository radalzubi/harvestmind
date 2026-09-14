/**
 * Report -> decisions.
 *
 * One shape for everything ZAAD recommends, whichever phase produced it, answering the
 * same seven questions: what action, on what object, why, what changes, what happens if
 * nothing is done, what the evidence is, and whether anybody has reviewed it.
 *
 * Rules this module keeps:
 *  - Every number comes from the report. Nothing is estimated, scaled or annualised here.
 *  - A quantity the report does not carry is `null` and renders as "Not available", never 0.
 *  - Plan-level economics are attributed to the plan, never to a single line, because the
 *    optimizer prices the plan against the incumbent as a whole.
 *  - Optimizer vocabulary lives in `technical`; `headline`, `why` and `effect` are operator language.
 */
import type {
  ZaadAction, ZaadBuild, ZaadCommitmentOrder, ZaadReport, ZaadRequest, ZaadSource,
} from "./types";

export type DecisionCategory = "Open POs" | "Purchasing" | "Inventory" | "Sourcing" | "Customer allocation" | "Network";

export type DecisionTargetType = "supplier" | "location" | "lane" | "po" | "sku" | "plan";

export interface DecisionTarget {
  type: DecisionTargetType;
  /** Network Twin id when this object exists in the Twin, so a decision can open it there. */
  networkId: string | null;
  id: string;
  label: string;
}

/** A named quantity with its unit. `value === null` means the report did not carry it. */
export interface Fact {
  label: string;
  value: string | null;
  /** Shown under the value when it needs a caveat. */
  note?: string;
}

export interface EvidenceItem {
  label: string;
  detail: string;
  /** Where the figure came from, in the optimizer's provenance vocabulary. */
  provenance?: string;
}

export interface Decision {
  id: string;
  category: DecisionCategory;
  /** The imperative, in operator language: "Delay PO-1842 by 1 week". */
  headline: string;
  /** The verb alone, for badges: DEFER, BUY, MOVE, KEEP. */
  verb: string;
  target: DecisionTarget;
  /** Level 1: one sentence a non-technical reader can act on. */
  summary: string;
  /** Level 2: why, in sentences. */
  why: string[];
  /** Level 2: what changes if this is approved. */
  effect: Fact[];
  /** Level 2: what happens if the current plan is kept. */
  doNothing: string | null;
  /** Level 2: named evidence. */
  evidence: EvidenceItem[];
  /** Level 3: raw report fragments for an analyst. */
  technical: Record<string, unknown>;
  /** Higher sorts first. Deadline pressure, not economics. */
  urgency: number;
  /** Economic size where the report gives one, else null. Not comparable across categories. */
  materiality: number | null;
  needsReview: boolean;
}

export interface PlanSummary {
  status: string;
  /** True when the optimizer recommends changing something. */
  recommendsChange: boolean;
  asOf: string;
  informationHash: string;
  currency: string;
  /** Total modelled cost of the recommended plan against keeping the current one. */
  valueVsCurrent: number | null;
  costBreakdown: Array<{ component: string; current: number | null; recommended: number | null; delta: number | null }>;
  workingCapitalDelta: number | null;
  service: Array<{ id: string; location: string; target: number; current: number | null; recommended: number | null }>;
  reasons: string[];
  limitations: string[];
  /** The phases this workspace actually declared, in operator language. */
  activeCapabilities: string[];
}

const NUMBER = (v: number, digits = 0) =>
  v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export function money(v: number | null | undefined, currency: string): string | null {
  if (v == null || !Number.isFinite(v)) return null;
  const sign = v < 0 ? "-" : "";
  return `${sign}${currency} ${NUMBER(Math.abs(v), Math.abs(v) < 100 ? 2 : 0)}`;
}

export function units(v: number | null | undefined): string | null {
  if (v == null || !Number.isFinite(v)) return null;
  return `${NUMBER(v, Number.isInteger(v) ? 0 : 1)} units`;
}

/** "in 3 weeks" / "this week" / "1 week earlier" for a period index on the weekly grid. */
export function weeks(n: number): string {
  if (n === 0) return "this week";
  if (n === 1) return "next week";
  return `in ${n} weeks`;
}

function shift(periods: number | null): string | null {
  if (periods == null || periods === 0) return null;
  const n = Math.abs(periods);
  return `${n} week${n === 1 ? "" : "s"} ${periods > 0 ? "later" : "earlier"}`;
}

const COMMITMENT_VERB: Record<string, string> = {
  KEEP: "Keep", CANCEL: "Cancel", REDUCE: "Reduce", DEFER: "Delay", EXPEDITE: "Bring forward", SPLIT: "Split",
};

const COST_LABEL: Record<string, string> = {
  PURCHASE: "Goods", FREIGHT: "Freight", ORDERING: "Order and amendment charges", RECEIVING: "Receiving",
  CARRYING: "Holding stock", FINANCING: "Financing", SHORTAGE: "Missed demand",
  INVENTORY_VALUE_CHANGE: "Change in stock value", OTHER: "Other", TOTAL: "Total",
};

function sourceIndex(request: ZaadRequest | null): Map<string, ZaadSource> {
  return new Map((request?.sources ?? []).map((s) => [s.id, s]));
}

/** Fitted supplier reliability for evidence, only when the build reports a sample. */
function reliabilityEvidence(build: ZaadBuild | null, supplier: string): EvidenceItem[] {
  const fit = build?.fits?.[supplier];
  if (!fit) return [];
  const out: EvidenceItem[] = [];
  if (fit.fill != null) {
    out.push({
      label: "Delivery reliability",
      detail: `${(fit.fill * 100).toFixed(1)}% of ordered quantity arrives, on ${fit.sample_size ?? 0} past deliver${(fit.sample_size ?? 0) === 1 ? "y" : "ies"}`,
      provenance: fit.provenance,
    });
  }
  if (fit.lead_days != null) {
    out.push({
      label: "Lead time",
      detail: `${NUMBER(fit.lead_days, 0)} days${fit.lead_sd_days != null ? ` (give or take ${NUMBER(fit.lead_sd_days, 0)})` : ""}`,
      provenance: fit.lead_provenance ?? fit.provenance,
    });
  }
  return out;
}

// ── open purchase orders (P4B) ───────────────────────────────────────────────

function commitmentDecision(order: ZaadCommitmentOrder, report: ZaadReport, request: ZaadRequest | null, build: ZaadBuild | null, currency: string): Decision {
  const src = sourceIndex(request).get(order.source);
  const supplier = src?.supplier ?? order.source;
  const verb = COMMITMENT_VERB[order.recommended_action] ?? order.recommended_action;
  const current = order.current_commitment;
  const timing = order.timing_change?.[0] ?? null;
  const moved = shift(timing?.periods_shift ?? null);
  const drivers = order.economic_drivers;

  const headline = order.recommended_action === "KEEP"
    ? `Keep ${order.po} as it stands`
    : order.recommended_action === "SPLIT"
      ? `Split ${order.po} across ${Object.keys(order.quantities).length} options`
      : `${verb} ${order.po}${moved ? ` by ${moved.replace(/ (later|earlier)$/, "")}` : ""}${order.quantity_affected && order.recommended_action !== "DEFER" && order.recommended_action !== "EXPEDITE" ? ` — ${units(order.quantity_affected)}` : ""}`;

  const why: string[] = [];
  if (order.recommended_action === "DEFER") why.push("You already have enough cover for the demand this order was meant to meet, so holding it later costs less than holding it now.");
  if (order.recommended_action === "EXPEDITE") why.push("Bringing this order forward protects demand that the current arrival date would miss.");
  if (order.recommended_action === "CANCEL") why.push("The stock this order would add is not needed over the planning horizon, and the order is still cancellable.");
  if (order.recommended_action === "REDUCE") why.push("Part of this order is not needed over the planning horizon; the rest still is.");
  if (order.recommended_action === "SPLIT") why.push("Part of this order is worth changing and part is worth keeping.");
  if (report.reasons?.length) why.push(...report.reasons.slice(0, 2));

  const effect: Fact[] = [];
  if (timing && timing.periods_shift != null && timing.periods_shift !== 0) {
    effect.push({ label: "Arrival", value: `moves from ${weeks(timing.arrival_period_keep)} to ${weeks(timing.arrival_period_option)}` });
    effect.push({ label: "Payment", value: `moves from ${weeks(timing.payment_period_keep)} to ${weeks(timing.payment_period_option)}` });
  }
  if (order.recommended_action !== "KEEP") {
    effect.push({ label: "Quantity affected", value: units(order.quantity_affected) });
    // A zero saving is a priced answer, not a missing one — but printing "0" among real figures
    // reads as a number worth looking at, so the invoice is described instead.
    if (drivers.invoice_avoided) effect.push({ label: "Invoice avoided", value: money(drivers.invoice_avoided, currency) });
    else effect.push({ label: "Remaining invoice", value: money(drivers.remaining_invoice_keep, currency), note: "unchanged by this — the timing moves, the amount does not" });
    if (drivers.amendment_fees) effect.push({ label: "Amendment fee", value: money(drivers.amendment_fees, currency) });
    if (drivers.refundable_credits) effect.push({ label: "Refundable credit", value: money(drivers.refundable_credits, currency) });
    if (drivers.deposit_sunk) effect.push({ label: "Deposit not recoverable", value: money(drivers.deposit_sunk, currency) });
  }

  const doNothing = order.recommended_action === "KEEP"
    ? `${units(current.open_units)} arrive ${weeks(current.arrival_period)} as agreed, invoiced at ${money(current.remaining_invoice_per_unit, currency)} per unit.`
    : `${units(current.open_units)} arrive ${weeks(current.arrival_period)} and ${money(current.open_units * current.remaining_invoice_per_unit, currency)} falls due ${weeks(current.payment_period)}.`;

  const evidence: EvidenceItem[] = [
    { label: "Open commitment", detail: `${units(current.open_units)} still to come from ${supplier}; ${units(current.expected_accepted_units)} expected to be accepted${current.expected_fill != null ? ` (${(current.expected_fill * 100).toFixed(0)}%)` : ""}.` },
    { label: "Order stage", detail: `${order.stage.replaceAll("_", " ").toLowerCase()}; ${order.cancellation_status.replaceAll("_", " ").toLowerCase()}.` },
    ...reliabilityEvidence(build, supplier),
  ];
  if (current.deposit_paid) evidence.push({ label: "Deposit paid", detail: money(current.deposit_paid, currency) ?? "" });
  for (const basis of order.contractual_basis ?? []) {
    evidence.push({
      label: "Contractual right",
      detail: `Option ${basis.option}${basis.contract_reference ? `, ${basis.contract_reference}` : ""}`,
      provenance: basis.provenance,
    });
  }
  if (!order.contractual_basis?.length && order.recommended_action === "KEEP") {
    evidence.push({ label: "Contractual right", detail: "No amendment right is declared for this order beyond keeping it." });
  }

  // A deadline that has nearly passed outranks a bigger but unhurried change.
  const deadlineWeeks = Math.min(...(order.timing_change ?? []).map((t) => t.arrival_period_keep), current.arrival_period);
  return {
    id: `po:${order.po}`,
    category: "Open POs",
    headline,
    verb: order.recommended_action,
    target: { type: "po", id: order.po, networkId: `sup:${supplier}`, label: `${order.po} · ${supplier}` },
    summary: order.recommended_action === "KEEP"
      ? `No change is worth making to ${order.po}.`
      : `${headline}. Approval is required; ZAAD does not send anything to the supplier.`,
    why,
    effect,
    doNothing,
    evidence,
    technical: { order, commitments_version: report.commitments?.version, verdict: report.commitments?.commitment_verdict },
    urgency: order.recommended_action === "KEEP" ? 0 : Math.max(1, 12 - deadlineWeeks),
    materiality: order.recommended_action === "KEEP" ? 0 : (drivers.invoice_avoided || null),
    needsReview: order.recommended_action !== "KEEP",
  };
}

// ── purchases and transfers ──────────────────────────────────────────────────

function changedActions(report: ZaadReport, kind: ZaadAction["action"]): Map<string, { selected: number; incumbent: number; period: number }> {
  const key = (a: ZaadAction) => `${a.source ?? a.transfer ?? a.po ?? ""}|${a.period}`;
  const out = new Map<string, { selected: number; incumbent: number; period: number }>();
  for (const a of report.actions ?? []) {
    if (a.action !== kind) continue;
    out.set(key(a), { selected: a.quantity, incumbent: 0, period: a.period });
  }
  for (const a of report.incumbent_actions ?? []) {
    if (a.action !== kind) continue;
    const hit = out.get(key(a));
    if (hit) hit.incumbent = a.quantity;
    else out.set(key(a), { selected: 0, incumbent: a.quantity, period: a.period });
  }
  return out;
}

function purchaseDecisions(report: ZaadReport, request: ZaadRequest | null, build: ZaadBuild | null, currency: string): Decision[] {
  const sources = sourceIndex(request);
  const rows = changedActions(report, "purchase");
  const out: Decision[] = [];
  for (const [key, row] of rows) {
    // Only the first review is a decision; later periods are replanning guidance, as the report says.
    if (row.period !== 0) continue;
    if (Math.abs(row.selected - row.incumbent) < 1e-6) continue;
    const sourceId = key.split("|")[0];
    const src = sources.get(sourceId);
    const supplier = src?.supplier ?? sourceId;
    const sku = src?.sku ?? "";
    const more = row.selected > row.incumbent;
    const delta = Math.abs(row.selected - row.incumbent);
    const value = src ? row.selected * src.unit_price : null;
    const headline = row.selected === 0
      ? `Do not order ${sku} from ${supplier} this week`
      : `${more ? "Order more" : "Order less"} ${sku} from ${supplier} — ${units(row.selected)} this week`;
    out.push({
      id: `buy:${sourceId}`,
      category: "Purchasing",
      headline,
      verb: row.selected === 0 ? "HOLD" : more ? "BUY MORE" : "BUY LESS",
      target: { type: "supplier", id: supplier, networkId: `sup:${supplier}`, label: `${supplier} · ${sku}` },
      summary: `${headline}. Approval is required; ZAAD does not place the order.`,
      why: (report.reasons ?? []).slice(0, 3),
      effect: [
        { label: "Order this week", value: units(row.selected) },
        { label: "Current plan orders", value: units(row.incumbent) },
        { label: "Difference", value: `${more ? "+" : "-"}${units(delta)}` },
        { label: "Order value", value: money(value, currency), note: src ? undefined : "unit price is not available for this source" },
      ],
      doNothing: `The current plan orders ${units(row.incumbent)} of ${sku} from ${supplier} this week.`,
      evidence: [
        ...(src ? [{ label: "Landed unit cost", detail: `${money(src.unit_price, currency)} goods${src.freight_per_unit ? ` + ${money(src.freight_per_unit, currency)} freight` : ""} per unit` }] : []),
        ...reliabilityEvidence(build, supplier),
        ...(src?.minimum ? [{ label: "Minimum order", detail: units(src.minimum) ?? "" }] : []),
      ],
      technical: { source: src ?? sourceId, selected: row.selected, incumbent: row.incumbent },
      urgency: 6,
      materiality: value,
      needsReview: true,
    });
  }
  return out;
}

function transferDecisions(report: ZaadReport, request: ZaadRequest | null, currency: string): Decision[] {
  const byId = new Map((request?.transfers ?? []).map((t) => [t.id, t]));
  const out: Decision[] = [];
  for (const [key, row] of changedActions(report, "transfer")) {
    if (row.period !== 0) continue;
    if (Math.abs(row.selected - row.incumbent) < 1e-6 || row.selected <= 0) continue;
    const id = key.split("|")[0];
    const t = byId.get(id);
    const headline = t
      ? `Move ${units(row.selected)} of ${t.sku} from ${t.origin} to ${t.destination}`
      : `Move ${units(row.selected)} on transfer ${id}`;
    out.push({
      id: `move:${id}`,
      category: "Inventory",
      headline,
      verb: "MOVE",
      target: { type: "lane", id, networkId: `lane:${id}`, label: t ? `${t.origin} → ${t.destination}` : id },
      summary: `${headline}. Approval is required; ZAAD does not raise the transfer.`,
      why: (report.reasons ?? []).slice(0, 3),
      effect: [
        { label: "Quantity", value: units(row.selected) },
        { label: "Arrives", value: t ? weeks(t.lead_periods) : null },
        { label: "Transfer cost", value: t ? money(row.selected * t.cost_per_unit, currency) : null },
      ],
      doNothing: t
        ? `Stock stays at ${t.origin}; ${t.destination} covers demand from what it already holds and what is inbound.`
        : "Stock stays where it is.",
      evidence: t ? [{ label: "Lane", detail: `${t.origin} → ${t.destination}, ${t.lead_periods} week${t.lead_periods === 1 ? "" : "s"}, ${money(t.cost_per_unit, currency)} per unit${t.approved ? "" : " (not approved)"}` }] : [],
      technical: { transfer: t ?? id, selected: row.selected, incumbent: row.incumbent },
      urgency: 5,
      materiality: t ? row.selected * t.cost_per_unit : null,
      needsReview: true,
    });
  }
  return out;
}

// ── the plan as a whole ──────────────────────────────────────────────────────

export function planSummary(report: ZaadReport, request: ZaadRequest | null): PlanSummary {
  const currency = request?.currency ?? "USD";
  const econ = report.economics ?? {};
  const inc = econ.incumbent_costs ?? null;
  const sel = econ.selected_costs ?? null;
  const value = inc?.TOTAL != null && sel?.TOTAL != null ? inc.TOTAL - sel.TOTAL : null;
  const components = ["PURCHASE", "FREIGHT", "ORDERING", "CARRYING", "FINANCING", "SHORTAGE", "INVENTORY_VALUE_CHANGE"];
  const costBreakdown = components
    .map((c) => ({
      component: COST_LABEL[c] ?? c,
      current: inc?.[c] ?? null,
      recommended: sel?.[c] ?? null,
      delta: inc?.[c] != null && sel?.[c] != null ? (sel[c] as number) - (inc[c] as number) : null,
    }))
    .filter((r) => r.current != null || r.recommended != null);

  const capabilities: string[] = [];
  if ((request?.locations?.length ?? 0) > 1) capabilities.push("Network positioning");
  if (report.sourcing) capabilities.push("Sourcing split");
  if (report.recourse) capabilities.push("Future adjustments");
  if (report.atp) capabilities.push("Customer allocation");
  if (report.commitments) capabilities.push("Open PO changes");

  return {
    status: report.status,
    recommendsChange: report.status === "PENDING_REVIEW",
    asOf: report.as_of,
    informationHash: report.information_hash,
    currency,
    valueVsCurrent: value,
    costBreakdown,
    workingCapitalDelta:
      econ.selected_working_capital != null && econ.incumbent_working_capital != null
        ? econ.selected_working_capital - econ.incumbent_working_capital
        : null,
    service: (report.network_service ?? []).map((s) => ({
      id: s.service, location: s.location, target: s.requested,
      current: s.incumbent_achieved, recommended: s.selected_achieved ?? s.expected_achieved,
    })),
    reasons: report.reasons ?? [],
    limitations: report.limitations ?? [],
    activeCapabilities: capabilities,
  };
}

/** Everything ZAAD recommends right now, most urgent first. */
export function buildDecisions(report: ZaadReport, request: ZaadRequest | null, build: ZaadBuild | null): Decision[] {
  const currency = request?.currency ?? "USD";
  const out: Decision[] = [
    ...(report.commitments?.orders ?? []).map((o) => commitmentDecision(o, report, request, build, currency)),
    ...purchaseDecisions(report, request, build, currency),
    ...transferDecisions(report, request, currency),
  ];
  return out.sort((a, b) => {
    if (a.needsReview !== b.needsReview) return a.needsReview ? -1 : 1;
    if (a.urgency !== b.urgency) return b.urgency - a.urgency;
    return (b.materiality ?? 0) - (a.materiality ?? 0);
  });
}

export const CATEGORIES: DecisionCategory[] = ["Open POs", "Purchasing", "Inventory", "Sourcing", "Customer allocation", "Network"];
