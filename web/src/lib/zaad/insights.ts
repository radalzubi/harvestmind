/**
 * INSIGHTS — the operator's own records aggregated on the server, and the latest completed plan
 * read back. Nothing here starts a solve, and nothing here recomputes a number the server sent.
 *
 * Two rules the whole surface keeps:
 *   - a null is a null with a reason (UNKNOWN, NOT MEASURED, NOT APPLICABLE, NO DATA, BLOCKED BY
 *     DATA, NOT IN PLAN) and is shown as that reason, never as 0;
 *   - the filters live in the URL, so a chart a person is looking at can be sent to someone else
 *     and every link out of a chart carries the same filters into Inventory, Purchase orders, Data
 *     and Decisions.
 */
import { apiFetch } from "@/lib/api";

export type Bucket = "day" | "week" | "month";
export const BUCKETS: Bucket[] = ["day", "week", "month"];
export type Tab = "overview" | "demand" | "inventory" | "supply" | "service" | "decisions" | "perishability";
export const TABS: Tab[] = ["overview", "demand", "inventory", "supply", "service", "decisions"];

export interface Filters {
  bucket: Bucket; start: string | null; end: string | null;
  sku: string | null; category: string | null; brand: string | null; customer: string | null; location: string | null; supplier: string | null;
}
export const FILTER_KEYS = ["sku", "category", "brand", "customer", "location", "supplier"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];

export const EMPTY: Filters = { bucket: "week", start: null, end: null, sku: null, category: null, brand: null, customer: null, location: null, supplier: null };

const ID = /^[A-Za-z0-9 _.:@+\-\/&()'#,]{1,120}$/;
function clean(value: string | null): string | null {
  if (!value) return null;
  const v = value.trim();
  return ID.test(v) ? v : null;
}
function isoDate(value: string | null): string | null {
  return value && /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : null;
}

/** The filters a URL carries. Unknown buckets fall back to week; malformed values are dropped, never guessed. */
export function filtersFromParams(params: { get(name: string): string | null }): Filters {
  const bucket = params.get("bucket");
  return {
    bucket: (BUCKETS as string[]).includes(bucket ?? "") ? (bucket as Bucket) : "week",
    start: isoDate(params.get("start")), end: isoDate(params.get("end")),
    sku: clean(params.get("sku")), category: clean(params.get("category")), brand: clean(params.get("brand")),
    customer: clean(params.get("customer")), location: clean(params.get("location")), supplier: clean(params.get("supplier")),
  };
}

/** The query string the API and the page share; only what is set travels. */
export function filtersToQuery(f: Filters, extra: Record<string, string | null | undefined> = {}): string {
  const q = new URLSearchParams();
  q.set("bucket", f.bucket);
  for (const key of ["start", "end", ...FILTER_KEYS] as const) if (f[key]) q.set(key, f[key] as string);
  for (const [k, v] of Object.entries(extra)) if (v) q.set(k, v);
  return q.toString();
}

export function activeFilters(f: Filters): Array<{ key: FilterKey; value: string }> {
  return FILTER_KEYS.filter((k) => f[k]).map((k) => ({ key: k, value: f[k] as string }));
}

/** Where a chart leads. Every link carries the filters the reader already has. */
export const linksFor = {
  inventory: (f: Partial<Filters>, sku?: string | null): string => {
    const q = new URLSearchParams();
    if (sku) q.set("sku", sku);
    if (f.category) q.set("category", f.category);
    if (f.brand) q.set("brand", f.brand);
    if (f.supplier) q.set("supplier", f.supplier);
    if (f.location) q.set("location", f.location);
    const s = q.toString();
    return `/inventory${s ? `?${s}` : ""}`;
  },
  purchaseOrders: (po?: string | null, supplier?: string | null): string => {
    const q = new URLSearchParams({ tab: "imported", postate: "open" });
    if (po) q.set("po", po);
    if (supplier) q.set("poq", supplier);
    return `/orders?${q.toString()}`;
  },
  data: (dataset: string, column?: string | null, value?: string | null): string => {
    const q = new URLSearchParams({ dataset });
    if (column && value) { q.set("fcol", column); q.set("fval", value); }
    return `/data?${q.toString()}`;
  },
  decision: (id: string): string => `/decisions?decision=${encodeURIComponent(id)}`,
  supplier: (id: string): string => `/diagnostics?tab=suppliers&q=${encodeURIComponent(id)}`,
  insights: (tab: Tab, f: Partial<Filters>): string => `/insights?${filtersToQuery({ ...EMPTY, ...f }, { tab })}`,
};

/** Null reasons, in words. A number that is absent is shown as why, never as zero. */
export type NullReason = "UNKNOWN" | "NOT_MEASURED" | "NOT_APPLICABLE" | "NO_DATA" | "BLOCKED_BY_DATA" | "NOT_IN_PLAN";
export const REASON_LABEL: Record<NullReason, string> = {
  UNKNOWN: "Unknown", NOT_MEASURED: "Not measured", NOT_APPLICABLE: "Not applicable", NO_DATA: "No data",
  BLOCKED_BY_DATA: "Blocked by data", NOT_IN_PLAN: "Not in plan",
};
export function reasonLabel(reason: string | null | undefined): string {
  return (reason && REASON_LABEL[reason as NullReason]) || "Unknown";
}
/** Format a value, or say why there is none. `0` is a number and is formatted as one. */
export function shown(value: number | null | undefined, format: (v: number) => string, reason?: string | null): string {
  if (value == null || !Number.isFinite(value)) return reasonLabel(reason ?? "UNKNOWN");
  return format(value);
}

export interface PlanSummary {
  available: boolean; reason?: string; why?: string;
  job_id?: string; finished_at?: string | null; as_of?: string | null; status?: string; information_hash?: string;
  stale?: boolean; stale_reason?: string | null; products?: number; scope_skus?: string[];
}
/** The sentence under an optimizer-derived chart: which plan, when, and whether the data moved since. */
export function planSentence(plan: PlanSummary | null | undefined, format: (iso: string) => string): string {
  if (!plan || !plan.available) return "No completed ZAAD plan yet. Insights never starts a run on its own; run one from Home.";
  const when = plan.finished_at ? format(plan.finished_at) : "unknown time";
  const base = `Latest ZAAD plan: ${when}${plan.products != null ? ` · ${plan.products} product${plan.products === 1 ? "" : "s"}` : ""}.`;
  return plan.stale ? `${base} Workspace data changed afterward.` : base;
}

export interface Provenance {
  source_data: string[]; metric: string; numerator: string; denominator: string;
  date_range: { start: string | null; end: string | null }; bucket: string; filters: Record<string, string>;
  coverage: Record<string, number | string | null>; last_updated: string | null;
  plan: { job_id?: string; finished_at?: string | null; as_of?: string | null; stale?: boolean; stale_reason?: string | null } | null;
  note?: string | null;
}
/** The scope a reader is looking at, in one line: range, bucket, filters, rows. */
export function scopeSentence(p: Provenance | null | undefined, rows?: number | null): string {
  if (!p) return "";
  const parts: string[] = [];
  const range = p.date_range?.start || p.date_range?.end
    ? `${p.date_range.start ?? "the beginning"} → ${p.date_range.end ?? "the latest row"}`
    : "the whole history";
  parts.push(`${range}, by ${p.bucket}`);
  const filters = Object.entries(p.filters ?? {}).map(([k, v]) => `${k} = ${v}`);
  parts.push(filters.length ? `filtered by ${filters.join(", ")}` : "no filters");
  if (rows != null) parts.push(`${rows.toLocaleString("en-US")} rows`);
  return parts.join(" · ");
}

/** A bucket boundary as a person reads it. Kept in ISO so Arabic and English show the same digits. */
export function periodLabel(period: string, bucket: Bucket): string {
  const iso = period.slice(0, 10);
  if (bucket === "month") return iso.slice(0, 7);
  if (bucket === "week") return `w/c ${iso}`;
  return iso;
}

// ── payloads ──────────────────────────────────────────────────────────────────

export interface SeriesPoint { period: string; ordered: number | null; shipped: number | null; unfulfilled: number | null; lines: number; customers?: number; products?: number; ordered_measured?: number | null; lines_unmeasured?: number }
export interface TopRow { id: string | null; ordered: number | null; shipped: number | null; unfulfilled: number | null; lines: number }
export interface Demand {
  available: boolean; reason?: string; why?: string; label?: string; fulfilment?: "MEASURED" | "NOT_MEASURED"; fulfilment_note?: string;
  series: SeriesPoint[]; truncated?: boolean; partial_last_period?: boolean;
  totals?: { ordered: number | null; shipped: number | null; lines: number; customers: number; products: number; first_order: string | null; last_order: string | null; lines_unmeasured: number };
  top?: Record<string, { rows: TopRow[]; reason?: string; why?: string }>;
  concentration?: { customers: number; top_1_share: number | null; top_5_share: number | null; hhi: number | null; basis: string };
  period_over_period?: { period: string; previous: string; ordered: number | null; previous_ordered: number | null; change: number | null; change_share: number | null; basis?: string } | null;
  provenance: Provenance;
}
export interface DemandPeriod {
  available: boolean; period: string; bucket: string;
  top_skus: TopRow[]; top_customers: TopRow[]; top_locations: TopRow[];
  largest_increases: Array<{ sku: string; ordered: number | null; previous: number | null; change: number }>;
  largest_declines: Array<{ sku: string; ordered: number | null; previous: number | null; change: number }>;
  affected_inventory: Array<{ sku: string; on_hand: number; in_transit: number; sites: number; weekly_demand: number | null; weeks_of_cover: number | null }>;
  open_purchase_orders: Array<{ po_id: string; sku: string; supplier_id: string; po_date: string; eta: string | null; open_units: number }>;
  related_decisions: Array<{ kind: string; id: string; target: string; sku: string | null; verb: string; quantity: number | null; period: number | null }>;
  provenance: Provenance;
}
export interface Inventory {
  available: boolean; reason?: string; why?: string;
  series: Array<{ period: string; snapshot_date: string; units: number; value: number | null; rows_without_cost: number; in_transit: number; products: number; sites: number }>;
  by_site_series: Array<{ period: string; location_id: string; units: number; value: number | null }>;
  latest_snapshot: string | null;
  by_site: Array<{ id: string; units: number; value: number | null; products: number }>;
  by_category: Array<{ id: string | null; units: number; value: number | null; products: number }>;
  position: { on_hand: number | null; inbound_units: number | null; weekly_demand: number | null; weeks_of_cover: number | null; products: number; products_without_demand: number; cover_basis: string; cover_reason: string | null };
  provenance: Provenance;
}
export interface Supply {
  available: boolean; reason?: string; why?: string; as_of: string;
  open_by_expected_arrival: Array<{ period: string; units: number; orders: number }>;
  open_without_expected_date: { units: number; orders: number };
  received: Array<{ period: string; units: number; orders: number; rejected: number }>;
  aging: Array<{ age: string; units: number; orders: number }>;
  late_open: { orders: number; units: number; orders_without_eta: number };
  by_supplier: Array<{ id: string; open_units: number; open_orders: number; open_value: number | null }>;
  by_destination: Array<{ id: string; open_units: number; open_orders: number }> | { rows: never[]; reason: string; why: string };
  totals: { open_units: number | null; open_orders: number; open_value: number | null; open_lines_without_cost: number };
  provenance: Provenance;
}
export interface Ratio { value: number | null; numerator?: number | null; denominator?: number | null; thin?: boolean; coverage?: number | null; reason?: string; why?: string; orders?: number }
export interface SupplierRow {
  supplier_id: string; matched_orders: number; units_ordered: number; units_received: number; fill_rate: number | null; short_fill_rate: number | null; short_fills: number;
  p50_lead_days: number | null; p90_lead_days: number | null; orders_with_promise: number; late_orders: number; late_rate: number | null; mean_late_days: number | null;
  lateness: Ratio; fill: Ratio; exposure: { open_units: number; open_value: number | null; open_orders: number };
  share_of_units_ordered: number | null; amendment_rights_on_open_orders: number; products_with_declared_alternative: number; alternative_for_products: number;
}
export interface Suppliers {
  available: boolean; reason?: string; why?: string; suppliers: SupplierRow[];
  trend: Array<{ supplier_id: string; period: string; matched_orders: number; fill_rate: number | null; p50_lead_days: number | null; orders_with_promise: number; late_orders: number; short_fills: number; late_rate: number | null; late_reason: string | null }>;
  share_basis: string; short_fill_tolerance: number; thin_sample: number; sourcing: { present: boolean; note: string } | null; provenance: Provenance;
}
export interface Service {
  available: boolean; reason?: string; why?: string; fulfilment: "MEASURED" | "NOT_MEASURED";
  series: Array<{ period: string; ordered: number; shipped: number | null; unfulfilled: number | null; service_level: number | null; lines: number }>;
  by_customer: Array<{ id: string; ordered: number; shipped: number | null; unfulfilled: number | null; lines: number; lines_short: number | null; service_level: Ratio; service_class: string | null; service_class_reason: string | null }>;
  by_service_class: Array<{ id: string; customers: number; ordered: number; shipped: number; ordered_measured: number; service_level: number | null }>;
  declared_service_classes: Array<{ class_id: string; contractual_service_floor: number | null; strategic: boolean; tier: string | null; provenance: string | null }>;
  atp: { present: boolean; reason?: string; why?: string; note?: string; summary?: Record<string, unknown>; orders?: Array<Record<string, unknown>> };
  risk_scores: { value: null; reason: string; why: string }; provenance: Provenance;
}
export interface DecisionRow { kind: string; id: string; target: string; sku: string | null; verb: string; quantity: number | null; period: number | null }
export interface Decisions {
  plan: PlanSummary;
  recommended: { open_po_by_verb: Record<string, number>; other: Record<string, number>; total: number };
  responses: Array<{ status: string; n: number; for_latest_plan: number }>;
  proposals_by_state: Array<{ state: string; n: number }>;
  proposals_by_origin: Array<{ origin: string; amendment_action: string; n: number }>;
  external_status: Array<{ external_status: string; n: number }>;
  outcomes: { recorded: number; with_comparator: number; drafts_with_outcomes: number };
  decisions: DecisionRow[]; registers: Record<string, string>; provenance: Provenance;
}
export interface Register { available: boolean; reason?: string | null; why?: string | null; basis?: string; [k: string]: unknown }
export interface Value { registers: Record<string, Register>; order: string[]; currency: string | null; never_combined: string; provenance: Provenance }
export interface Connectivity {
  plan: PlanSummary;
  families: Array<{ family: string; name: string; backend_source: string; api: string; visualization: string; drilldown: string; in_plan: boolean; declared: boolean; status: string }>;
  note: string;
}
export interface Overview {
  plan: PlanSummary; data_last_updated: string | null;
  demand: { available: boolean; label?: string; series: SeriesPoint[]; fulfilment?: string; totals?: Demand["totals"]; period_over_period?: Demand["period_over_period"]; concentration?: Demand["concentration"] };
  inventory: { available: boolean; position?: Inventory["position"]; by_site: Inventory["by_site"]; series: Inventory["series"]; latest_snapshot?: string | null };
  supply: { available: boolean; totals?: Supply["totals"]; late_open?: Supply["late_open"]; open_without_expected_date?: Supply["open_without_expected_date"]; by_supplier: Supply["by_supplier"] };
  decisions: { recommended?: Decisions["recommended"]; responses?: Decisions["responses"]; proposals_by_state?: Decisions["proposals_by_state"]; external_status?: Decisions["external_status"]; outcomes?: Decisions["outcomes"] };
  scope: { date_range: { start: string | null; end: string | null }; bucket: string; filters: Record<string, string> };
}

export const VALUE_REGISTER_LABEL: Record<string, string> = {
  MODELED_DIFFERENCE: "Modelled difference", BACKTESTED_OPPORTUNITY: "Backtested opportunity",
  APPROVED_EXPECTED_DIFFERENCE: "Approved expected difference", OBSERVED_AFTER_ACTION: "Observed after action", REALIZED_VALUE: "Realized value",
};

const base = "/api/zaad/insights";
export const fetchOverview = (f: Filters) => apiFetch<Overview>(`${base}/summary?${filtersToQuery(f)}`);
export const fetchPlan = () => apiFetch<PlanSummary>(`${base}/plan`);
export const fetchDemand = (f: Filters) => apiFetch<Demand>(`${base}/demand?${filtersToQuery(f)}`);
export const fetchDemandPeriod = (f: Filters, period: string) => apiFetch<DemandPeriod>(`${base}/demand/period?${filtersToQuery(f, { period })}`);
export const fetchInventoryInsights = (f: Filters) => apiFetch<Inventory>(`${base}/inventory?${filtersToQuery(f)}`);
export const fetchSupply = (f: Filters) => apiFetch<Supply>(`${base}/supply?${filtersToQuery(f)}`);
export const fetchSupplierInsights = (f: Filters) => apiFetch<Suppliers>(`${base}/suppliers?${filtersToQuery(f)}`);
export const fetchService = (f: Filters) => apiFetch<Service>(`${base}/service?${filtersToQuery(f)}`);
export const fetchDecisionInsights = () => apiFetch<Decisions>(`${base}/decisions`);
export const fetchValue = () => apiFetch<Value>(`${base}/value`);
export const fetchConnectivity = () => apiFetch<Connectivity>(`${base}/connectivity`);

// ── action → insights ─────────────────────────────────────────────────────────

/** The Insights views behind one decision, from what the decision names and what the request maps. */
export function insightsLinksFor(
  decision: { target: { type: string; id: string }; technical?: Record<string, unknown> },
  request: { sources?: Array<{ id: string; sku: string; supplier?: string }>; pipeline?: Array<{ id: string; source: string }> } | null | undefined,
): { demand: string | null; inventory: string | null; supplier: string | null; value: string } {
  const sources = new Map((request?.sources ?? []).map((s) => [s.id, s]));
  let sku: string | null = null;
  let supplier: string | null = null;
  const fromSource = (id: unknown) => {
    const s = typeof id === "string" ? sources.get(id) : undefined;
    if (s) { sku = sku ?? s.sku; supplier = supplier ?? (s.supplier ?? null); }
  };
  if (decision.target.type === "sku") sku = decision.target.id;
  if (decision.target.type === "supplier") supplier = decision.target.id;
  if (decision.target.type === "po") {
    const po = (request?.pipeline ?? []).find((p) => p.id === decision.target.id);
    if (po) fromSource(po.source);
    const order = decision.technical?.order as { source?: string } | undefined;
    if (order?.source) fromSource(order.source);
  }
  if (typeof decision.technical?.source === "string") fromSource(decision.technical.source);
  return {
    demand: sku ? linksFor.insights("demand", { sku }) : null,
    inventory: sku ? linksFor.insights("inventory", { sku }) : null,
    supplier: supplier ? linksFor.insights("supply", { supplier }) : null,
    value: linksFor.insights("decisions", {}),
  };
}
