/**
 * The canonical ZAAD contract, as the released API returns it.
 *
 * These types mirror `zaad.network.v2` (the request) and `zaad.network.report.v2`
 * (the report) closely enough for the product to read them, and no further: every
 * field the UI does not use is left out rather than guessed at, and everything the
 * optimizer may omit is optional. Nothing here reimplements optimizer logic.
 */

export interface ZaadSKU { id: string; unit_value?: number; pack_size?: number; sector?: string | null }

export interface ZaadLocation {
  id: string;
  kind: "central_dc" | "regional_dc" | "branch" | "warehouse";
  capacity_volume?: number;
  holding_per_value_period?: number;
}

export interface ZaadSource {
  id: string;
  supplier: string;
  sku: string;
  destination: string;
  route: string[];
  unit_price: number;
  freight_per_unit?: number;
  handling_per_unit?: number;
  minimum?: number;
  maximum?: number;
  case_multiple?: number;
  capacity_by_period?: number[];
}

export interface ZaadStock {
  id: string; sku: string; location: string;
  quantity: number; reserved?: number; damaged?: number; quarantined?: number; expires_in?: number;
}

export interface ZaadTransfer {
  id: string; sku: string; origin: string; destination: string;
  lead_periods: number; capacity: number; cost_per_unit: number; approved: boolean;
}

export interface ZaadService {
  id: string; sku: string; location: string; customer: string;
  target: number; selling_price: number; sla_per_unmet?: number; metric?: string;
}

export interface ZaadCustomer { id: string; channel: string; priority: number; service_class?: string | null }

export interface ZaadPOOption {
  id: string;
  action: "keep" | "cancel" | "defer" | "expedite" | "reschedule";
  due_in: number;
  max_quantity: number;
  fee_per_unit: number;
  credit_per_unit: number;
  deadline_in?: number;
  contract_reference?: string | null;
  provenance?: string;
  payment_due_in?: number;
  remaining_invoice_per_unit?: number;
}

export interface ZaadOpenPO {
  id: string; source: string; ordered: number; received?: number;
  expected_accepted_remaining: number; current_eta: string; stage: string;
  carrier?: string; cancellation_status?: string;
  prepaid_per_remaining_unit?: number; allow_split_amendments?: boolean;
  options?: ZaadPOOption[];
}

export interface ZaadRequest {
  schema_version: string;
  operator_id: string;
  as_of: string;
  currency: string;
  period_days: number;
  horizon: number;
  skus: ZaadSKU[];
  locations: ZaadLocation[];
  sources: ZaadSource[];
  stock: ZaadStock[];
  transfers: ZaadTransfer[];
  customers: ZaadCustomer[];
  services: ZaadService[];
  pipeline: ZaadOpenPO[];
}

/** `build` from `/request/from-workspace` and `/plan/from-workspace`: what was read and how good it is. */
export interface ZaadBuild {
  origin_monday?: string;
  rows_read?: Record<string, number>;
  compact?: Record<string, number>;
  /** Fitted supplier reliability, keyed by supplier id. */
  fits?: Record<string, {
    fill?: number; fill_sd?: number; lead_days?: number; lead_sd_days?: number;
    sample_size?: number; provenance?: string; lead_provenance?: string;
  }>;
  incumbent_rule?: { rule?: string | null; provenance?: string };
  provenance?: Record<string, string>;
  leakage_guard?: Record<string, unknown>;
  warnings?: string[];
}

export type ZaadActionKind = "purchase" | "transfer" | "po_option";

export interface ZaadAction {
  action: ZaadActionKind;
  period: number;
  quantity: number;
  first_review?: boolean;
  source?: string;
  transfer?: string;
  po?: string;
  option?: string;
  expiry_cohort?: number;
}

export interface ZaadNetworkService {
  service: string; location: string; requested: number;
  jointly_feasible: number | null;
  expected_achieved: number | null;
  incumbent_achieved: number | null;
  selected_achieved: number | null;
}

export interface ZaadEconomics {
  incumbent_costs?: Record<string, number | null>;
  selected_costs?: Record<string, number | null>;
  materiality?: Record<string, unknown>;
  selected_working_capital?: number | null;
  incumbent_working_capital?: number | null;
  [k: string]: unknown;
}

export interface ZaadCommitmentOrder {
  po: string;
  source: string;
  stage: string;
  cancellation_status: string;
  current_commitment: {
    open_units: number; expected_accepted_units: number; expected_fill: number | null;
    arrival_period: number; remaining_invoice_per_unit: number; payment_period: number;
    deposit_paid: number; contract_reference?: string | null;
  };
  irreversibility?: unknown;
  amendment_windows?: unknown[];
  incumbent: { action: string; quantities: Record<string, number> };
  recommended_action: "KEEP" | "CANCEL" | "REDUCE" | "DEFER" | "EXPEDITE" | "SPLIT";
  quantities: Record<string, number>;
  quantity_affected: number;
  timing_change: Array<{
    option: string; quantity: number;
    arrival_period_keep: number; arrival_period_option: number; periods_shift: number | null;
    payment_period_keep: number; payment_period_option: number;
  }>;
  contractual_basis: Array<{ option: string; contract_reference?: string | null; provenance?: string }>;
  economic_drivers: {
    amendment_fees: number; refundable_credits: number;
    remaining_invoice_keep: number; remaining_invoice_after: number; invoice_avoided: number;
    deposit_sunk: number; note?: string;
  };
  approval_required: boolean;
  executable_amendment: boolean;
}

export interface ZaadCommitments {
  version: string;
  verdict: string;
  commitment_action: string;
  commitment_verdict: string;
  commitment_value_vs_keep: number | null;
  overall_plan_status?: string;
  plan_changes_outside_commitments?: Array<{ kind: string; id: string; period: number; incumbent_quantity: number; selected_quantity: number }>;
  reading: string;
  orders: ZaadCommitmentOrder[];
  inventory_service_effect?: Record<string, number | null>;
  material_improvement_vs_keep?: { plan_level_value: number | null; materiality?: unknown; note?: string };
  commitment_ledger_lines?: Record<string, { selected: number | null; incumbent: number | null }>;
  assumptions?: string[];
  approval_required: boolean;
  executable_amendment: boolean;
}

export interface ZaadAtp {
  [k: string]: unknown;
  orders?: Array<Record<string, unknown>>;
}

export interface ZaadReport {
  schema_version: string;
  brand: string;
  version: string;
  operator_id: string;
  as_of: string;
  information_hash: string;
  evidence_label: string;
  status: string;
  mode: string;
  selected_policy: string;
  actions: ZaadAction[];
  incumbent_actions: ZaadAction[];
  approval_required: boolean;
  executable_purchase_order: boolean;
  reasons: string[];
  limitations: string[];
  network_service?: ZaadNetworkService[];
  service_frontier?: Array<Record<string, unknown>>;
  economics?: ZaadEconomics;
  orchestration?: Record<string, unknown>;
  solve_quality?: Record<string, unknown>;
  cash?: Array<Record<string, unknown>>;
  confirmation?: Record<string, unknown>;
  stress_confirmation?: Array<Record<string, unknown>>;
  candidates?: Record<string, unknown>;
  recovery_guidance?: Record<string, unknown> | null;
  forecasts?: Record<string, unknown>;
  eta?: Record<string, unknown>;
  protection?: Array<Record<string, unknown>>;
  commitments?: ZaadCommitments;
  atp?: ZaadAtp;
  sourcing?: Record<string, unknown>;
  recourse?: Record<string, unknown>;
  physics?: Record<string, unknown>;
}

export interface WorkspaceRequestResponse { request: ZaadRequest; build: ZaadBuild }
export interface WorkspacePlanResponse { report: ZaadReport; build: ZaadBuild; executable_purchase_order: boolean }

/** `/api/zaad/network/directory` — declared master data the compact request does not carry. */
export interface DirectorySupplier {
  id: string;
  name: string | null;
  origin_iso3: string | null;
  route: string | null;
  capacity_per_week: number | null;
  lead_time_promised_weeks: number | null;
  risk_group: string | null;
  risk_group_kind: string | null;
}
export interface DirectoryLocation { id: string; kind: string | null; capacity_units: number | null }
export interface DirectoryResponse {
  suppliers: DirectorySupplier[];
  locations: DirectoryLocation[];
  rows_read: Record<string, number>;
  provenance: string;
}

/** The status the report gives a plan, in the operator's language. */
export const PLAN_STATUS_LABEL: Record<string, string> = {
  PENDING_REVIEW: "Changes to review",
  RETAIN_INCUMBENT: "No change recommended",
  NO_ACTION: "No change recommended",
  // The selector found no candidate materially better than the current plan.
  ABSTAIN: "No change recommended",
  CAPITAL_OPTIMIZATION: "Changes to review",
  NETWORK_ALLOCATION: "Changes to review",
  NORMAL_REPLENISHMENT: "Changes to review",
  TIME_LIMIT_NO_USABLE_PLAN: "Could not be computed in time",
  DATA_INSUFFICIENCY: "Not enough data",
};

export function planStatusLabel(status: string | undefined): string {
  if (!status) return "Unknown";
  return PLAN_STATUS_LABEL[status] ?? status.replaceAll("_", " ").toLowerCase();
}
