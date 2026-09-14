/**
 * A canonical workspace, shaped exactly as the released API returns it.
 *
 * Lives under `__tests__` on purpose: there is no importable illustrative model anywhere in
 * `src/lib`, so an authenticated surface cannot fall back to demonstration data even by mistake.
 */
import type { DirectoryResponse, WorkspacePlanResponse, WorkspaceRequestResponse, ZaadReport, ZaadRequest } from "../types";

export const request: ZaadRequest = {
  schema_version: "zaad.network.v2",
  operator_id: "acme",
  as_of: "2026-09-07T00:00:00Z",
  currency: "USD",
  period_days: 7,
  horizon: 12,
  skus: [
    { id: "SKU-1", unit_value: 12 },
    { id: "SKU-2", unit_value: 30 },
  ],
  locations: [
    { id: "MAIN", kind: "central_dc" },
    { id: "RIYADH", kind: "branch" },
  ],
  sources: [
    { id: "src_a1", supplier: "SUP-A", sku: "SKU-1", destination: "MAIN", route: [], unit_price: 10, freight_per_unit: 1, minimum: 100 },
    { id: "src_b2", supplier: "SUP-B", sku: "SKU-2", destination: "MAIN", route: [], unit_price: 25 },
  ],
  stock: [
    { id: "st1", sku: "SKU-1", location: "MAIN", quantity: 4000 },
    { id: "st2", sku: "SKU-2", location: "RIYADH", quantity: 250 },
  ],
  transfers: [
    { id: "tr1", sku: "SKU-2", origin: "MAIN", destination: "RIYADH", lead_periods: 1, capacity: 2000, cost_per_unit: 0.4, approved: true },
  ],
  customers: [{ id: "RETAIL", channel: "retail", priority: 2, service_class: "A" }],
  services: [
    { id: "svc1", sku: "SKU-1", location: "MAIN", customer: "RETAIL", target: 0.97, selling_price: 18 },
    { id: "svc2", sku: "SKU-2", location: "RIYADH", customer: "RETAIL", target: 0.97, selling_price: 44 },
  ],
  pipeline: [
    {
      id: "PO-1842", source: "src_b2", ordered: 1200, expected_accepted_remaining: 1200,
      current_eta: "2026-10-04T00:00:00Z", stage: "CONFIRMED", carrier: "MSC",
      cancellation_status: "CANCELLABLE_WITH_FEE", prepaid_per_remaining_unit: 2, allow_split_amendments: false,
      options: [
        { id: "keep", action: "keep", due_in: 4, max_quantity: 1200, fee_per_unit: 0, credit_per_unit: 0, payment_due_in: 4, remaining_invoice_per_unit: 25 },
        { id: "defer1", action: "defer", due_in: 5, max_quantity: 1200, fee_per_unit: 0.5, credit_per_unit: 0, payment_due_in: 5, remaining_invoice_per_unit: 25, contract_reference: "MSA §7.2", provenance: "OPERATOR_DECLARED" },
      ],
    },
  ],
};

export const build: WorkspaceRequestResponse["build"] = {
  origin_monday: "2026-09-07",
  rows_read: { stg_fmcg_skus: 2, stg_fmcg_orders: 900, stg_fmcg_purchase_orders: 40 },
  compact: { skus: 2, sources: 2, services: 2 },
  fits: {
    "SUP-A": { fill: 0.98, sample_size: 41, lead_days: 28, provenance: "INFERRED_FROM_HISTORY" },
    "SUP-B": { fill: 0.84, sample_size: 23, lead_days: 34, lead_sd_days: 6, provenance: "INFERRED_FROM_HISTORY" },
  },
  incumbent_rule: { rule: "periodic:2", provenance: "INFERRED_FROM_HISTORY" },
  warnings: ["Transfer lane MAIN->RIYADH has no declared cost; it is priced at zero."],
};

export const report: ZaadReport = {
  schema_version: "zaad.network.report.v2",
  brand: "ZAAD",
  version: "8.0",
  operator_id: "acme",
  as_of: "2026-09-07T00:00:00Z",
  information_hash: "a".repeat(64),
  evidence_label: "SYNTHETIC",
  status: "PENDING_REVIEW",
  mode: "PROTECT",
  selected_policy: "commitment_aware",
  approval_required: true,
  executable_purchase_order: false,
  reasons: ["Supplier SUP-B has been delivering short of its order quantity.", "Cover at MAIN exceeds the protection level for SKU-2."],
  limitations: ["Synthetic evidence is not customer validation."],
  actions: [
    { action: "purchase", source: "src_a1", period: 0, quantity: 900, first_review: true },
    { action: "po_option", po: "PO-1842", option: "defer1", period: 0, quantity: 1200, first_review: true },
    { action: "transfer", transfer: "tr1", period: 0, quantity: 400, first_review: true },
  ],
  incumbent_actions: [
    { action: "purchase", source: "src_a1", period: 0, quantity: 1500, first_review: true },
    { action: "po_option", po: "PO-1842", option: "keep", period: 0, quantity: 1200, first_review: true },
  ],
  network_service: [
    { service: "svc1", location: "MAIN", requested: 0.97, jointly_feasible: 0.99, expected_achieved: 0.974, incumbent_achieved: 0.975, selected_achieved: 0.974 },
    { service: "svc2", location: "RIYADH", requested: 0.97, jointly_feasible: 0.98, expected_achieved: 0.94, incumbent_achieved: 0.93, selected_achieved: 0.94 },
  ],
  economics: {
    incumbent_costs: { TOTAL: 121000, PURCHASE: 92000, CARRYING: 15000, SHORTAGE: 9000, ORDERING: 3000, FINANCING: 2000 },
    selected_costs: { TOTAL: 113500, PURCHASE: 86000, CARRYING: 13000, SHORTAGE: 9500, ORDERING: 3200, FINANCING: 1800 },
    incumbent_working_capital: 64000,
    selected_working_capital: 58000,
  },
  protection: [
    { sku: "SKU-2", location: "RIYADH", stance: "protect", on_hand_units: 250, protection_units: 480, explanation: "Cover at RIYADH is below the protection level.", state: { risk_active: true, decaying: false, activity: 0.4, periods_to_lean: 3 } },
    { sku: "SKU-1", location: "MAIN", stance: "lean", on_hand_units: 4000, protection_units: 900, state: { risk_active: false } },
  ] as unknown as ZaadReport["protection"],
  commitments: {
    version: "zaad.commitments.1.1",
    verdict: "COMMITMENT CHANGE RECOMMENDED",
    commitment_action: "DEFER",
    commitment_verdict: "COMMITMENT CHANGE RECOMMENDED",
    commitment_value_vs_keep: 7500,
    overall_plan_status: "PENDING_REVIEW",
    plan_changes_outside_commitments: [{ kind: "purchase", id: "src_a1", period: 0, incumbent_quantity: 1500, selected_quantity: 900 }],
    reading: "Commitment verdict: COMMITMENT CHANGE RECOMMENDED - DEFER PO-1842 (1200 units).",
    approval_required: true,
    executable_amendment: false,
    orders: [
      {
        po: "PO-1842", source: "src_b2", stage: "CONFIRMED", cancellation_status: "CANCELLABLE_WITH_FEE",
        current_commitment: {
          open_units: 1200, expected_accepted_units: 1140, expected_fill: 0.95,
          arrival_period: 4, remaining_invoice_per_unit: 25, payment_period: 4, deposit_paid: 2400,
          contract_reference: "MSA §7.2",
        },
        incumbent: { action: "KEEP", quantities: { keep: 1200 } },
        recommended_action: "DEFER",
        quantities: { defer1: 1200 },
        quantity_affected: 1200,
        timing_change: [{
          option: "defer1", quantity: 1200, arrival_period_keep: 4, arrival_period_option: 5, periods_shift: 1,
          payment_period_keep: 4, payment_period_option: 5,
        }],
        contractual_basis: [{ option: "defer1", contract_reference: "MSA §7.2", provenance: "OPERATOR_DECLARED" }],
        economic_drivers: {
          amendment_fees: 600, refundable_credits: 0,
          remaining_invoice_keep: 30000, remaining_invoice_after: 30000, invoice_avoided: 0, deposit_sunk: 0,
        },
        approval_required: true, executable_amendment: false,
      },
    ],
  },
};

export const directory: DirectoryResponse = {
  suppliers: [
    { id: "SUP-A", name: "Anwar Trading", origin_iso3: "TUR", route: "suez", capacity_per_week: 5000, lead_time_promised_weeks: 4, risk_group: null, risk_group_kind: null },
    { id: "SUP-B", name: "Baraka Foods", origin_iso3: null, route: null, capacity_per_week: null, lead_time_promised_weeks: null, risk_group: "plant_x", risk_group_kind: "PLANT" },
  ],
  locations: [{ id: "MAIN", kind: "central_dc", capacity_units: null }, { id: "RIYADH", kind: "branch", capacity_units: null }],
  rows_read: { stg_fmcg_suppliers: 2, stg_fmcg_locations: 2 },
  provenance: "OPERATOR_DECLARED",
};

export const plan: WorkspacePlanResponse = { report, build, executable_purchase_order: false };
