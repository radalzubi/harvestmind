/**
 * The operating product's API: the operator's own records, and the documents they create.
 *
 * Separate from `client.ts`, which speaks to the optimizer. These endpoints never plan: they read
 * the vault, store a proposal, or produce a file. Every list is paged on the server — a workspace
 * with fifty thousand products must never depend on the browser holding them.
 *
 * Errors arrive as `{code, message}`. The message is written for the person reading it, so it is
 * shown as-is; the code is what the interface branches on.
 */
import { BASE_URL as BASE, authHeaders } from "@/lib/api";

export class ProductError extends Error {
  code: string | null;
  status: number;
  constructor(message: string, code: string | null, status: number) {
    super(message);
    this.name = "ProductError";
    this.code = code;
    this.status = status;
  }
}

async function failure(res: Response): Promise<ProductError> {
  let message = `HTTP ${res.status}`;
  let code: string | null = null;
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail)) {
      message = detail.map((e: { loc?: unknown[]; msg?: string }) => `${e.loc?.join(".") || "request"}: ${e.msg}`).join("; ");
    } else if (detail && typeof detail === "object") {
      message = String(detail.message ?? JSON.stringify(detail));
      code = detail.code ?? null;
    }
  } catch {
    /* a response with no JSON body keeps the status line */
  }
  return new ProductError(message, code, res.status);
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw await failure(res);
  return res.status === 204 ? (undefined as T) : (res.json() as Promise<T>);
}

/** Multipart: the JSON content type must not be set, or the boundary is lost. */
async function upload<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", headers: authHeaders(), body: form });
  if (!res.ok) throw await failure(res);
  return res.json() as Promise<T>;
}

function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

// ── the business as it is ─────────────────────────────────────────────────────

export interface OperatingSummary {
  products: number | null;
  suppliers: number | null;
  locations: number | null;
  customers: number | null;
  snapshot_date: string | null;
  on_hand_units: number | null;
  inventory_value: number | null;
  products_without_cost?: number | null;
  open_purchase_orders: number | null;
  inbound_units: number | null;
  late_purchase_orders?: number | null;
  proposals_awaiting_review?: number | null;
  proposals_open?: number | null;
  provenance: string;
}

export const fetchSummary = (asOf?: string | null) =>
  call<OperatingSummary>(`/api/zaad/workspace/summary${query({ as_of: asOf })}`);

export interface InventoryRow {
  sku: string;
  sku_name: string | null;
  brand: string | null;
  category: string | null;
  sub_category: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  unit_cost: number | null;
  unit_price: number | null;
  units_per_case: number | null;
  moq_units: number | null;
  shelf_life_days: number | null;
  abc_class: string | null;
  on_hand: number | null;
  in_transit: number | null;
  sites: number | null;
  inbound_units: number | null;
  open_pos: number | null;
  /** Units on open transfers into the site being viewed; null in the all-sites view. */
  transfer_units?: number | null;
  weekly_demand: number | null;
  inventory_value: number | null;
  cover_weeks: number | null;
}

export interface InventoryPage {
  rows: InventoryRow[];
  total: number;
  limit: number;
  offset: number;
  sort: string;
  direction: string;
  snapshot_date: string | null;
  demand_weeks: number;
  served: boolean;
  note: string | null;
  sortable: string[];
  /** The one site every figure on the page is for, or null when every site is summed. */
  location?: string | null;
  /** What a site view cannot show from this workspace's data, and why. */
  location_notes?: string[];
}

export interface InventoryQuery {
  q?: string; category?: string; brand?: string; supplier_id?: string; abc_class?: string;
  cover?: string; skus?: string; sort?: string; direction?: string; limit?: number; offset?: number;
  location?: string;
}

export interface Location { id: string; kind: string | null; products: number }
export const fetchLocations = () => call<{ locations: Location[] }>("/api/zaad/workspace/locations");

export const fetchInventory = (options: InventoryQuery = {}) =>
  call<InventoryPage>(`/api/zaad/workspace/inventory${query(options as Record<string, string>)}`);

export interface SkuDetail {
  sku: string;
  master: Record<string, unknown>;
  overview: Partial<InventoryRow>;
  stock_by_site: Array<{ location_id: string; on_hand: number | null; in_transit: number | null; snapshot_date: string }>;
  /** The all-sites total against the sum of the site positions shown, and why they differ when they do. */
  reconciliation?: {
    all_sites_total: number | null; sum_of_sites: number; sites_on_latest_snapshot: number;
    sites_with_older_rows: string[]; agree: boolean; snapshot_date: string | null; note: string | null;
  } | null;
  purchase_orders: Array<{ po_id: string; po_date: string; supplier_id: string | null; qty_ordered: number;
    unit_cost: number | null; expected_delivery_date: string | null; qty_received: number | null; first_receipt: string | null }>;
  demand_by_week: Array<{ week: string; ordered: number; shipped: number }>;
  short_shipped_lines: number | null;
  declared_sources: Array<Record<string, unknown>>;
  missing: string[];
  provenance: string;
}

export const fetchSku = (sku: string) =>
  call<SkuDetail>(`/api/zaad/workspace/inventory/${encodeURIComponent(sku)}`);

export interface ImportedOrderRow {
  po_id: string; po_date: string | null; supplier_id: string | null; eta: string | null;
  lines: number; ordered_units: number | null; value: number | null; value_incomplete: boolean;
  open_units: number | null; first_receipt: string | null; received_units: number | null;
  received_unattributed: boolean;
}

export const fetchImportedOrders = (options: {
  q?: string; supplier_id?: string; state?: string; sort?: string; direction?: string;
  limit?: number; offset?: number; as_of?: string | null;
} = {}) =>
  call<{ rows: ImportedOrderRow[]; total: number; limit: number; offset: number; sort: string; direction: string; served: boolean; note?: string }>(
    `/api/zaad/workspace/purchase-orders${query(options as Record<string, string>)}`);

export interface ImportedOrderDetail {
  po_id: string;
  lines: Array<Record<string, unknown>>;
  receipts: Array<Record<string, unknown>>;
  declared_options: Array<Record<string, unknown>>;
  declared_terms: Record<string, unknown> | null;
  supplier: Record<string, unknown> | null;
  amendment_rights_declared: boolean;
  provenance: string;
}

export const fetchImportedOrder = (poId: string) =>
  call<ImportedOrderDetail>(`/api/zaad/workspace/purchase-orders/${encodeURIComponent(poId)}`);

// ── suppliers and diagnostics ─────────────────────────────────────────────────

export interface SupplierRow {
  supplier_id: string; name: string | null; origin: string | null; route: string | null;
  risk_group: string | null; matched_orders: number | null; fill_rate: number | null;
  short_fill_rate: number | null; late_rate: number | null; mean_late_days: number | null;
  p50_lead_days: number | null; p90_lead_days: number | null; lead_sd_days: number | null;
  promised_lead_days: number | null; fill_sd: number | null; mean_lead_days: number | null;
  orders_with_promise: number | null; last_receipt: string | null;
  open_orders: number | null; late_open_orders: number | null;
  /** How many open orders carry a promised date — the denominator "past their date" is measured against. */
  open_orders_with_promise?: number | null;
  open_units: number | null;
  skus: number | null;
}

export const fetchSuppliers = (options: { q?: string; sort?: string; direction?: string; limit?: number; offset?: number; as_of?: string | null } = {}) =>
  call<{ rows: SupplierRow[]; total: number; served: boolean; note?: string; short_fill_tolerance: number; thin_sample: number }>(
    `/api/zaad/workspace/suppliers${query(options as Record<string, string>)}`);

export interface LatenessStatement { statement: string; sample?: number | null; thin?: boolean; note?: string }

export interface SupplierDetail {
  supplier_id: string;
  master: Record<string, unknown> | null;
  measured: SupplierRow;
  deliveries: Array<{ po_id: string; po_date: string; promised: string | null; first_receipt: string;
    ordered: number; received: number; rejected: number; observed_lead_days: number | null;
    promised_lead_days: number | null; late_days: number | null; fill: number | null; first_sku: string; lines: number }>;
  by_product: Array<{ sku: string; orders: number; orders_with_promise: number | null; late_orders: number; mean_late_days: number | null; fill_rate: number | null }>;
  by_month: Array<{ month: string; orders: number; late_orders: number; mean_lead_days: number | null }>;
  trend: { recent: Record<string, number>; earlier: Record<string, number> } | null;
  skus: Array<{ sku: string; sku_name: string | null; category: string | null }>;
  alternatives: { declared: boolean; rows: Array<Record<string, unknown>>; note: string | null };
  exposure: { skus: number | null; on_hand_value: number | null; open_units: number | null };
  lateness: {
    observed: LatenessStatement[];
    associations: LatenessStatement[];
    drivers: LatenessStatement[];
    unknown: { statement: string; missing_fields: string[]; available_fields: string[] };
    driver_note: string;
  };
  short_fill_tolerance: number;
  thin_sample: number;
}

export const fetchSupplier = (id: string, asOf?: string | null) =>
  call<SupplierDetail>(`/api/zaad/workspace/suppliers/${encodeURIComponent(id)}${query({ as_of: asOf })}`);

export interface SectorRow {
  sku: string; sku_name: string | null; sector: string | null; storage_state: string | null;
  shelf_life_days: number | null; age_at_receipt_days: number | null;
  min_remaining_life_sale_days: number | null; remaining_life_at_receipt_days: number | null;
  deliveries: number | null; fill_mean: number | null; fill_sd: number | null;
  lead_mean_days: number | null; lead_sd_days: number | null;
  days_to_expiry: number | null; on_hand: number | null; demand_cv: number | null;
}

export const fetchSector = (options: { sector?: string; sort?: string; direction?: string; limit?: number; offset?: number } = {}) =>
  call<{ rows: SectorRow[]; total: number; served: boolean; note?: string; sectors?: string[]; absent?: string[] }>(
    `/api/zaad/workspace/sector${query(options as Record<string, string>)}`);

export const fetchCorridors = () =>
  call<{ served: boolean; rows: Array<{ route: string; orders: number; suppliers: number; orders_with_promise: number | null; late_orders: number; mean_late_days: number | null; mean_lead_days: number | null }>; note: string }>(
    "/api/zaad/workspace/corridors");

// ── the data explorer ─────────────────────────────────────────────────────────

export interface DatasetInfo {
  key: string; label: string; table: string; description: string;
  rows: number | null; available: boolean; filters: string[];
}

export const fetchDatasets = () =>
  call<{ datasets: DatasetInfo[]; max_page: number }>("/api/zaad/workspace/datasets");

export interface DatasetPage {
  dataset: string; label: string; description: string;
  columns: Array<{ name: string; label: string; kind: string; primary: boolean }>;
  rows: Array<Record<string, unknown>>;
  total: number; total_is_floor: boolean; limit: number; offset: number;
  sort: string; direction: string; served: boolean;
}

export const fetchDataset = (dataset: string, options: {
  q?: string; sort?: string; direction?: string; limit?: number; offset?: number; where?: string[];
} = {}) => {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(options)) {
    if (key === "where" || value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  for (const clause of options.where ?? []) search.append("where", clause);
  const text = search.toString();
  return call<DatasetPage>(`/api/zaad/workspace/datasets/${encodeURIComponent(dataset)}${text ? `?${text}` : ""}`);
};

export const fetchDatasetValues = (dataset: string, column: string) =>
  call<{ values: string[] }>(`/api/zaad/workspace/datasets/${encodeURIComponent(dataset)}/values/${encodeURIComponent(column)}`);

export interface SearchHit { kind: string; id: string; label: string; detail: string | null; href: string }

export const searchWorkspace = (q: string, limit = 8) =>
  call<{ results: SearchHit[] }>(`/api/zaad/workspace/search${query({ q, limit })}`);

// ── proposed orders ───────────────────────────────────────────────────────────

export type DraftState = "DRAFT" | "READY_FOR_REVIEW" | "APPROVED" | "REJECTED" | "EXPORTED" | "SUPERSEDED";
export type DraftOrigin = "ZAAD_RECOMMENDATION" | "CURRENT_POLICY" | "MANUAL" | "UPLOADED_PROPOSAL" | "IMPORTED_AMENDMENT";
export type AmendmentAction = "KEEP" | "DEFER" | "EXPEDITE" | "REDUCE" | "CANCEL" | "SPLIT";

export interface DraftLine {
  line_no?: number;
  sku: string;
  quantity: number;
  unit_price?: number | null;
  units_per_case?: number | null;
  requested_receipt_date?: string | null;
  notes?: string | null;
}

export interface DraftSummary {
  draft_id: string; origin: DraftOrigin; state: DraftState; revision: number;
  reference: string | null; supplier_id: string | null; destination_id: string | null;
  /** A transfer moves the operator's own stock from this site to `destination_id`; null on a purchase. */
  transfer_origin_id?: string | null;
  kind?: "PURCHASE" | "TRANSFER";
  currency: string | null; requested_order_date: string | null; requested_receipt_date: string | null;
  source_po_id: string | null; amendment_action: AmendmentAction | null;
  created_at: string; updated_at: string; approved_by: string | null; approved_at: string | null;
  decision_reason: string | null; supersedes: string | null; superseded_by: string | null;
  lines: number; units: number | null; value: number | null; value_incomplete: boolean | null;
  /** V2: what a person recorded happened outside ZAAD, if anything. */
  external_status?: ExternalStatus | null;
  external_reference?: string | null;
  version?: number;
}

export interface Draft extends Omit<DraftSummary, "lines"> {
  notes: string | null;
  source_decision_id: string | null;
  evaluation_id: string | null;
  lines: DraftLine[];
  events: Array<{ happened_at: string; actor: string | null; event: string; revision: number | null; detail: string | null }>;
  exports: Array<{ export_id: string; profile_name: string; format: string; filename: string; happened_at: string; actor: string | null }>;
  evaluations: Array<{ evaluation_id: string; status: string; created_at: string; as_of: string | null }>;
  editable: boolean;
  deletable: boolean;
  /** Only an approved (or already exported) proposal produces a file. */
  exportable: boolean;
  executable: boolean;
  transmitted: boolean;
  warnings: Array<{ level: string; message: string }>;
  /** The newest evaluation no longer describes these lines, or the workspace data changed since. */
  evaluation_stale?: boolean;
  evaluation_stale_reason?: string | null;
  /** What the approval was made against: an evaluation id, and whether it was current. */
  approved_evaluation_id?: string | null;
  approval_evaluation_state?: "current" | "stale_acknowledged" | "none" | null;
  /** Who created the draft (an actor id); the self-approval policy compares it with the approver. */
  created_by?: string | null;
  /** V2: when and by whom the external status was last recorded. Never set by ZAAD. */
  external_updated_at?: string | null;
  external_updated_by?: string | null;
}

export type ExternalStatus = "PLACED_EXTERNALLY" | "ACKNOWLEDGED" | "PARTIALLY_FULFILLED" | "FULFILLED" | "CANCELLED_EXTERNALLY";
export const EXTERNAL_LABEL: Record<ExternalStatus, string> = {
  PLACED_EXTERNALLY: "Placed in your system", ACKNOWLEDGED: "Acknowledged by the supplier",
  PARTIALLY_FULFILLED: "Partly delivered", FULFILLED: "Delivered", CANCELLED_EXTERNALLY: "Cancelled outside ZAAD",
};
/** The ladder a person may record, from each state. Mirrors the server's EXTERNAL_TRANSITIONS. */
export const EXTERNAL_NEXT: Record<string, ExternalStatus[]> = {
  none: ["PLACED_EXTERNALLY", "CANCELLED_EXTERNALLY"],
  PLACED_EXTERNALLY: ["ACKNOWLEDGED", "PARTIALLY_FULFILLED", "FULFILLED", "CANCELLED_EXTERNALLY"],
  ACKNOWLEDGED: ["PARTIALLY_FULFILLED", "FULFILLED", "CANCELLED_EXTERNALLY"],
  PARTIALLY_FULFILLED: ["PARTIALLY_FULFILLED", "FULFILLED", "CANCELLED_EXTERNALLY"],
  FULFILLED: [], CANCELLED_EXTERNALLY: [],
};

export const listDrafts = (options: {
  state?: string; origin?: string; supplier_id?: string; source_po_id?: string; q?: string; external_status?: string;
  sort?: string; direction?: string; limit?: number; offset?: number;
} = {}) =>
  call<{ rows: DraftSummary[]; total: number; limit: number; offset: number; sort: string; direction: string }>(
    `/api/zaad/orders${query(options as Record<string, string>)}`);

export const readDraft = (id: string) => call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}`);

/**
 * Job ids that belong to a proposal evaluation.
 *
 * The workspace's own plan and an evaluation's two runs go down the same released jobs path, and
 * the job record does not say which is which. Without this, "the last completed plan" on Home could
 * be the run that had a proposed order overlaid on the pipeline — a plan of a workspace plus an
 * order nobody has placed, shown as the operator's position.
 */
export const fetchEvaluationJobIds = () =>
  call<{ evaluation_job_ids: string[] }>("/api/zaad/orders/evaluation-jobs");

export const createDraft = (body: Record<string, unknown>) =>
  call<Draft>("/api/zaad/orders", { method: "POST", body: JSON.stringify(body) });

/** Several proposals as one unit: the server creates all of them or none. */
export const createDraftsBulk = (drafts: Array<Record<string, unknown>>) =>
  call<{ drafts: Draft[]; created: number }>("/api/zaad/orders/bulk", {
    method: "POST", body: JSON.stringify({ drafts }),
    headers: { "Idempotency-Key": `bulk-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}` },
  });

export const updateDraft = (id: string, body: Record<string, unknown>) =>
  call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(body) });

export const deleteDraft = (id: string) =>
  call<void>(`/api/zaad/orders/${encodeURIComponent(id)}`, { method: "DELETE" });

export const actOnDraft = (
  id: string, action: "submit" | "reopen" | "approve" | "reject", reason?: string,
  options: { acknowledgeStale?: boolean; expectedVersion?: number | null } = {},
) =>
  call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}/actions/${action}`, {
    method: "POST", body: JSON.stringify({ reason: reason ?? "", acknowledge_stale: Boolean(options.acknowledgeStale),
      expected_version: options.expectedVersion ?? undefined }),
  });

// ── V2: the closed loop, history, outcomes, responses, settings ───────────────

export const recordExternalStatus = (id: string, body: {
  status: ExternalStatus; external_reference?: string | null; note?: string | null; observed_at?: string | null; expected_version?: number | null;
}) => call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}/external-status`, { method: "POST", body: JSON.stringify(body) });

export interface AuditRow {
  audit_id: string; actor: string | null; actor_role: string | null; object_type: string; object_id: string; action: string;
  before_revision: number | null; after_revision: number | null; before_state: string | null; after_state: string | null;
  request_id: string | null; context: Record<string, unknown> | null; happened_at: string;
}
export interface Outcome {
  outcome_id: string; draft_id: string | null; metric: string; value: number | null; unit: string | null; observed_at: string | null;
  source: "recorded" | "matched"; comparator_value: number | null; comparator_basis: string | null; note: string | null;
  actor: string | null; recorded_at: string;
}
export interface RealizedValue {
  realized_outcome: boolean;
  realized_savings: Array<{ metric: string; observed: number | null; comparator: number | null; basis: string; difference: number | null; unit: string | null }>;
  note: string;
}
export interface DraftHistory {
  draft_id: string; revisions: string[];
  events: Draft["events"]; audit: AuditRow[]; exports: Draft["exports"]; outcomes: Outcome[];
  evaluations: Array<{ evaluation_id: string; draft_id: string; revision: number | null; status: string; as_of: string | null; created_at: string;
    baseline_job_id: string | null; proposal_job_id: string | null; draft_hash: string | null; workspace_version: string | null }>;
  decision_responses: DecisionResponse[];
  external: { status: ExternalStatus | null; reference: string | null; updated_at: string | null; updated_by: string | null; recorded_by_person: true };
  realized_value: RealizedValue;
}
export const readHistory = (id: string) => call<DraftHistory>(`/api/zaad/orders/${encodeURIComponent(id)}/history`);

export const OUTCOME_METRICS: Record<string, { label: string; unit: string }> = {
  received_units: { label: "Units received", unit: "units" }, receipt_date: { label: "Date received", unit: "date" },
  purchase_cost: { label: "Purchase cost", unit: "money" }, fill_rate: { label: "Fill rate", unit: "fraction" },
  lead_days: { label: "Lead time", unit: "days" }, stockout_days: { label: "Days out of stock", unit: "days" },
  expedite_cost: { label: "Expedite cost", unit: "money" }, waste_units: { label: "Units wasted", unit: "units" },
  working_capital: { label: "Working capital", unit: "money" }, customer_allocation_units: { label: "Units allocated to customers", unit: "units" },
};
export const recordOutcome = (id: string, body: {
  metric: string; value?: number | null; observed_at?: string | null; comparator_value?: number | null; comparator_basis?: string | null; note?: string | null;
}) => call<Outcome>(`/api/zaad/orders/${encodeURIComponent(id)}/outcomes`, { method: "POST", body: JSON.stringify(body) });

export interface DecisionResponse {
  response_id: string; job_id: string; decision_id: string; target_type: string | null; target_id: string | null; recommended: string | null;
  status: "REVIEWED" | "ACCEPTED" | "OVERRIDDEN" | "REJECTED"; reason_code: string | null; reason_text: string | null; draft_id: string | null;
  information_hash: string | null; as_of: string | null; actor: string | null; created_at: string; updated_at: string;
}
export const REASON_CODES: Record<string, string> = {
  supplier_relationship: "Supplier relationship", contract_not_represented: "A contract term ZAAD does not hold",
  cash_constraint: "Cash constraint", customer_commitment: "Customer commitment", promotion: "A promotion",
  management_decision: "Management decision", data_wrong: "The data is wrong", capacity_unavailable: "Capacity is not available", other: "Other",
};
export const respondDecision = (body: {
  job_id: string; decision_id: string; status: DecisionResponse["status"]; recommended?: string | null; target_type?: string | null;
  target_id?: string | null; reason_code?: string | null; reason_text?: string | null; draft_id?: string | null;
}) => call<DecisionResponse>("/api/zaad/decisions/responses", { method: "POST", body: JSON.stringify(body) });
export const listResponses = (jobId?: string | null) =>
  call<{ rows: DecisionResponse[]; total: number }>(`/api/zaad/decisions/responses${jobId ? `?job_id=${encodeURIComponent(jobId)}` : ""}`);

export interface HistoryFeed {
  responses: DecisionResponse[];
  decided: Array<Pick<Draft, "draft_id" | "reference" | "origin" | "state" | "revision" | "supplier_id" | "approved_by" | "approved_at" | "decision_reason"
    | "approved_evaluation_id" | "approval_evaluation_state" | "external_status" | "external_reference" | "external_updated_at" | "source_decision_id" | "source_po_id" | "updated_at">>;
  outcomes: Outcome[];
  counts: { awaiting_approval: number; approved_not_placed: number; placed_not_acknowledged: number; outcomes_recorded: number; responses: number };
  registers: string[];
  backtested: { available: boolean; note: string };
}
export const readHistoryFeed = () => call<HistoryFeed>("/api/zaad/history");

export interface ExportPreview {
  draft_id: string; profile: Omit<ExportProfile, "columns">; columns: ExportProfile["columns"];
  reason: "chosen" | "supplier_default" | "workspace_default" | "standard"; detail: string; exportable: boolean;
  adapter: { name: string; kind: string; real: boolean; transmits: boolean; note: string };
  validation: { ok: boolean; problems: string[] };
}
export const exportPreview = (id: string, profileId?: string | null) =>
  call<ExportPreview>(`/api/zaad/orders/${encodeURIComponent(id)}/export/preview${profileId ? `?profile_id=${encodeURIComponent(profileId)}` : ""}`);

export const readSettings = () => call<{ settings: { self_approval: string; default_export_profile: string | null } }>("/api/zaad/workspace/settings");
export const writeSettings = (body: Record<string, string | null>) =>
  call<{ settings: { self_approval: string; default_export_profile: string | null } }>("/api/zaad/workspace/settings", { method: "PUT", body: JSON.stringify(body) });

/** Semantic telemetry: an allowlisted name and identifier keys only. Fire-and-forget; never blocks a page. */
export function track(name: string, properties: Record<string, string | number | boolean> = {}): void {
  try {
    void call("/api/zaad/telemetry", { method: "POST", body: JSON.stringify({ events: [{ name, properties }] }) }).catch(() => undefined);
  } catch { /* telemetry never surfaces */ }
}

export const reviseDraft = (id: string) =>
  call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}/revise`, { method: "POST" });

// ── evaluation ────────────────────────────────────────────────────────────────

export interface LedgerRow {
  component: string; label: string;
  current: number | null; zaad: number | null; proposal: number | null;
  proposal_vs_current: number | null; zaad_vs_current: number | null;
}

export interface Comparison {
  columns: Array<{ key: string; label: string; source: string }>;
  currency: string;
  ledger: LedgerRow[];
  working_capital: { current: number | null; zaad: number | null; proposal: number | null };
  service: Array<{ service: string; location: string | null; requested: number | null; current: number | null; zaad: number | null; proposal: number | null }>;
  scope: string[];
  as_of: string | null;
  information_hash: string | null;
  baseline_status: string | null;
  proposal_status: string | null;
  limitations: string[];
  unavailable: string[];
  amendment: boolean;
  /**
   * For an amendment: the declared contract terms the counterfactual was run under. The fee is
   * the operator's own per-unit term times the units changed — not a model — and sits beside the
   * engine's difference, never inside it.
   */
  contract_terms?: {
    po_id: string; action: string; option_id: string | null; engine_action: string | null; units_changed: number | null;
    fee_per_unit: number | null; fee_total: number | null; credit_per_unit: number | null; credit_total: number | null;
    contract_reference: string | null; provenance: string | null; eta_before: string | null; eta_after: string | null;
    ordered_before: number | null; ordered_after: number | null; open_before: number | null; open_after: number | null;
    basis: "DECLARED_CONTRACT_TERMS"; modelled_difference: number | null; net_difference: number | null; net_basis: string;
  } | null;
  /** True when the optimizer retained the operator's own plan, so the middle column repeats the left. */
  zaad_abstained?: boolean;
  executable: boolean;
}

export interface EvaluationState {
  evaluation_id?: string;
  draft_id: string;
  status: "NONE" | "QUEUED" | "RUNNING" | "DONE" | "FAILED";
  message?: string;
  runs?: Record<string, { status: string; job_id?: string; error?: string | null; finished_at?: string | null }>;
  scope?: string[];
  as_of?: string | null;
  /** When this evaluation was submitted. */
  evaluated_at?: string | null;
  /** True when the proposal has been edited since, so the comparison describes different lines. */
  stale?: boolean;
  stale_reason?: string | null;
  comparison?: Comparison | null;
  executable?: boolean;
}

export const startEvaluation = (id: string) =>
  call<{ evaluation_id: string; status: string; scope: string[]; commitments_included: boolean; notes: string[] }>(
    `/api/zaad/orders/${encodeURIComponent(id)}/evaluate`, { method: "POST" });

export const readEvaluation = (id: string) =>
  call<EvaluationState>(`/api/zaad/orders/${encodeURIComponent(id)}/evaluation`);

/**
 * One declared amendment right, exactly as the engine reports it.
 *
 * Per-unit terms only: ZAAD prices a change against these inside a plan, and never totals them up
 * outside one.
 */
export interface AmendmentWindow {
  option: string; action: string; label?: string; provenance?: string;
  fee_per_unit?: number | null; credit_per_unit?: number | null;
  capacity_units?: number | null; deadline?: string | null; eligible?: boolean;
  [key: string]: unknown;
}

export const readAmendment = (id: string) =>
  call<{ draft_id: string; po_id: string; priced: boolean; reason: string | null; order?: Record<string, unknown>;
    recommended_action?: string; declared_options: string[]; declared_windows?: AmendmentWindow[];
    proposed_window?: AmendmentWindow | null; reading?: string; executable?: boolean }>(
    `/api/zaad/orders/${encodeURIComponent(id)}/amendment`);

// ── export formats ────────────────────────────────────────────────────────────

export interface ExportColumn { header: string; field: string | null; constant: string | null }

export interface ExportProfile {
  profile_id: string | null;
  name: string;
  format: "csv" | "xlsx" | "print";
  sheet_name?: string | null;
  delimiter?: string | null;
  date_format?: string | null;
  number_format?: string | null;
  filename_template?: string | null;
  supplier_id?: string | null;
  columns: ExportColumn[];
  built_in?: boolean;
  /** The format used when an export names none: per supplier when `supplier_id` is set, else for the workspace. */
  is_default?: boolean;
}

export const fetchProfiles = () =>
  call<{ profiles: ExportProfile[]; fields: Record<string, string>; formats: string[]; import_fields: Record<string, string> }>(
    "/api/zaad/orders/profiles");

export const saveProfile = (body: Record<string, unknown>, profileId?: string | null) =>
  profileId
    ? call<{ profile_id: string }>(`/api/zaad/orders/profiles/${encodeURIComponent(profileId)}`, { method: "PUT", body: JSON.stringify(body) })
    : call<{ profile_id: string }>("/api/zaad/orders/profiles", { method: "POST", body: JSON.stringify(body) });

export const deleteProfile = (profileId: string) =>
  call<void>(`/api/zaad/orders/profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" });

export const readTemplate = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return upload<{ headers: string[]; format: string; suggested_columns: ExportColumn[]; fields: Record<string, string> }>(
    "/api/zaad/orders/profiles/read-template", form);
};

export const readProposalFile = (file: File, mapping?: Record<string, string>) => {
  const form = new FormData();
  form.append("file", file);
  if (mapping) form.append("mapping", JSON.stringify(mapping));
  return upload<{
    headers?: string[]; preview?: string[][]; rows: number; truncated: boolean;
    suggested_mapping?: Record<string, string>; fields?: Record<string, string>;
    lines?: DraftLine[]; order?: Record<string, string>; problems?: string[];
  }>("/api/zaad/orders/read-proposal", form);
};
/**
 * Produce the file and hand it to the browser.
 *
 * Exporting is not transmitting: this downloads a document for the operator to place themselves.
 * The response is fetched with the workspace's own credentials, so it cannot be a plain link.
 */
export async function exportDraft(id: string, options: { profileId?: string | null; format?: string } = {}): Promise<string> {
  const res = await fetch(
    `${BASE}/api/zaad/orders/${encodeURIComponent(id)}/export${query({ profile_id: options.profileId, format: options.format })}`,
    { method: "POST", headers: authHeaders() });
  if (!res.ok) throw await failure(res);
  const disposition = res.headers.get("content-disposition") ?? "";
  const named = disposition.match(/filename="?([^"]+)"?/);
  const name = named ? named[1] : "purchase-order";
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return name;
}

// ── shared formatting ─────────────────────────────────────────────────────────

export const NUMBER = (value: number | null | undefined, digits = 0): string =>
  value == null || !Number.isFinite(value) ? "—"
    : value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

/**
 * A measured count, told apart from a count ZAAD does not have.
 *
 * `value ? NUMBER(value) : "—"` reads naturally and is wrong: it prints the dash that means
 * "not available" over a zero the vault states plainly. Three tables carried that line, and on a
 * workspace where every purchase order has been received it turned whole columns into a claim of
 * ignorance. Zero is a word here; only absence is the dash.
 */
/**
 * Where a paged list actually is, decided once so five tables cannot disagree.
 *
 * Two facts break the obvious arithmetic over `total`, and both are live in this product:
 *
 *   * a page **past the end** (a stale link, the back button) makes `offset + 1` exceed `total`,
 *     which printed "101–1 of 1 product";
 *   * a **floored** total — the data explorer stops counting at `COUNT_CEILING` and says "more
 *     than" — is smaller than the rows that still come back, which printed "150,001–100,000" and
 *     disabled Next over 271,140 records that were still there.
 *
 * `shown` (how many rows the page rendered) is the only quantity true in both worlds, so it
 * decides the range and the end. An exact total ends the list as well: without that a last page
 * that is exactly full leaves Next enabled and it walks off the end.
 */
export type PagerState =
  | { kind: "count"; total: number }
  | { kind: "past"; page: number }
  | { kind: "range"; from: number; to: number; atStart: boolean; atEnd: boolean };

export function pagerState(
  { total, limit, offset, shown, isFloor }:
  { total: number; limit: number; offset: number; shown: number; isFloor?: boolean },
): PagerState {
  if (!isFloor && total <= limit && offset === 0) return { kind: "count", total };
  if (offset > 0 && shown === 0) return { kind: "past", page: Math.floor(offset / limit) + 1 };
  const to = offset + shown;
  return {
    kind: "range", from: offset + 1, to,
    atStart: offset === 0,
    atEnd: shown < limit || (!isFloor && to >= total),
  };
}

export const TALLY = (value: number | null | undefined, none = "none"): { text: string; muted: boolean } =>
  value == null || !Number.isFinite(value) ? { text: "—", muted: true }
    : value === 0 ? { text: none, muted: true }
    : { text: NUMBER(value), muted: false };

/**
 * A count and its noun, agreeing. `COUNT(1, "order")` is "1 order", not "1 orders".
 *
 * A filtered list of one is the normal case, not the edge case, so every count printed beside a
 * noun goes through this. An irregular plural is passed explicitly.
 */
export const COUNT = (value: number | null | undefined, one: string, many?: string): string =>
  value == null || !Number.isFinite(value) ? "—"
    : `${NUMBER(value)} ${Math.abs(value) === 1 ? one : (many ?? `${one}s`)}`;

export const MONEY = (value: number | null | undefined, currency = "USD"): string =>
  value == null || !Number.isFinite(value) ? "—"
    : `${value < 0 ? "-" : ""}${currency} ${NUMBER(Math.abs(value), Math.abs(value) < 100 ? 2 : 0)}`;

export const PERCENT = (value: number | null | undefined, digits = 1): string =>
  value == null || !Number.isFinite(value) ? "—" : `${(value * 100).toFixed(digits)}%`;

export const DATE = (value: string | null | undefined): string => {
  if (!value) return "—";
  const parsed = new Date(String(value).length <= 10 ? `${value}T00:00:00Z` : value);
  return Number.isNaN(parsed.getTime()) ? String(value)
    : parsed.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
};

export const STATE_LABEL: Record<DraftState, string> = {
  DRAFT: "Draft",
  READY_FOR_REVIEW: "Waiting for review",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  EXPORTED: "Exported",
  SUPERSEDED: "Replaced",
};

export const ORIGIN_LABEL: Record<DraftOrigin, string> = {
  ZAAD_RECOMMENDATION: "From a ZAAD recommendation",
  CURRENT_POLICY: "From your current ordering rule",
  MANUAL: "Created here",
  UPLOADED_PROPOSAL: "Uploaded",
  IMPORTED_AMENDMENT: "Change to an existing order",
};

export const AMENDMENT_LABEL: Record<AmendmentAction, string> = {
  KEEP: "Keep as it is",
  DEFER: "Arrive later",
  EXPEDITE: "Arrive sooner",
  REDUCE: "Reduce the quantity",
  CANCEL: "Cancel",
  SPLIT: "Split the delivery",
};


// ── data readiness, per capability ───────────────────────────────────────────
//
// Not "is a file there" but "are the fields ZAAD needs present and usable", counted from the vault.

export type CapabilityStatus = "READY" | "PARTIAL" | "BLOCKED" | "UNAVAILABLE";

export interface CapabilityReadiness {
  capability: string;
  label: string;
  status: CapabilityStatus;
  reason: string;
  source: string | null;
  column: string | null;
  coverage: number | null;
}

export interface FieldReadiness {
  name: string; label: string; required: boolean; present: boolean;
  coverage: number | null; valid: number | null; feeds: string[]; kind: "text" | "number" | "date";
}

export interface SourceReadiness {
  key: string; table: string; label: string; required: boolean; present: boolean; rows: number;
  date_range: { from: string | null; to: string | null }; last_uploaded: string | null; hint: string;
  fields: FieldReadiness[];
}

export interface QualityCheck {
  check: string; severity: "BLOCKING" | "MATERIAL" | "INFORMATIONAL"; count: number; message: string;
  source: string; column: string | null;
}

export interface WorkspaceReadiness {
  sources: SourceReadiness[];
  capabilities: CapabilityReadiness[];
  quality: QualityCheck[];
  summary: { can_plan: boolean; ready: number; partial: number; blocked: number; unavailable: number; material_issues: number };
  provenance: string;
}

export const fetchReadiness = () => call<WorkspaceReadiness>("/api/zaad/workspace/readiness");

export const CAPABILITY_STATUS_LABEL: Record<CapabilityStatus, string> = {
  READY: "Ready", PARTIAL: "Partial", BLOCKED: "Blocked", UNAVAILABLE: "Not in the upload",
};
