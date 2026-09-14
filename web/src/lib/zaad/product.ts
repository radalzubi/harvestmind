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
import { authHeaders } from "@/lib/api";

const BASE = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

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
}

export interface InventoryQuery {
  q?: string; category?: string; brand?: string; supplier_id?: string; abc_class?: string;
  cover?: string; skus?: string; sort?: string; direction?: string; limit?: number; offset?: number;
}

export const fetchInventory = (options: InventoryQuery = {}) =>
  call<InventoryPage>(`/api/zaad/workspace/inventory${query(options as Record<string, string>)}`);

export interface SkuDetail {
  sku: string;
  master: Record<string, unknown>;
  overview: Partial<InventoryRow>;
  stock_by_site: Array<{ location_id: string; on_hand: number | null; in_transit: number | null; snapshot_date: string }>;
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
  open_orders: number | null; late_open_orders: number | null; open_units: number | null;
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
  by_product: Array<{ sku: string; orders: number; late_orders: number; mean_late_days: number | null; fill_rate: number | null }>;
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
  call<{ served: boolean; rows: Array<{ route: string; orders: number; suppliers: number; late_orders: number; mean_late_days: number | null; mean_lead_days: number | null }>; note: string }>(
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
  currency: string | null; requested_order_date: string | null; requested_receipt_date: string | null;
  source_po_id: string | null; amendment_action: AmendmentAction | null;
  created_at: string; updated_at: string; approved_by: string | null; approved_at: string | null;
  decision_reason: string | null; supersedes: string | null; superseded_by: string | null;
  lines: number; units: number | null; value: number | null; value_incomplete: boolean | null;
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
  executable: boolean;
  transmitted: boolean;
  warnings: Array<{ level: string; message: string }>;
}

export const listDrafts = (options: {
  state?: string; origin?: string; supplier_id?: string; source_po_id?: string; q?: string;
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

export const updateDraft = (id: string, body: Record<string, unknown>) =>
  call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(body) });

export const deleteDraft = (id: string) =>
  call<void>(`/api/zaad/orders/${encodeURIComponent(id)}`, { method: "DELETE" });

export const actOnDraft = (id: string, action: "submit" | "reopen" | "approve" | "reject", reason?: string) =>
  call<Draft>(`/api/zaad/orders/${encodeURIComponent(id)}/actions/${action}`, {
    method: "POST", body: JSON.stringify({ reason: reason ?? "" }),
  });

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
  comparison?: Comparison | null;
  executable?: boolean;
}

export const startEvaluation = (id: string) =>
  call<{ evaluation_id: string; status: string; scope: string[]; commitments_included: boolean; notes: string[] }>(
    `/api/zaad/orders/${encodeURIComponent(id)}/evaluate`, { method: "POST" });

export const readEvaluation = (id: string) =>
  call<EvaluationState>(`/api/zaad/orders/${encodeURIComponent(id)}/evaluation`);

export const readAmendment = (id: string) =>
  call<{ draft_id: string; po_id: string; priced: boolean; reason: string | null; order?: Record<string, unknown>;
    recommended_action?: string; declared_options: string[]; reading?: string; executable?: boolean }>(
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
