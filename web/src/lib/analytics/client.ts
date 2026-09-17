/**
 * The analytics client: typed contracts and fetchers for `/api/zaad/analytics`.
 *
 * The browser sends specs, never SQL, and formats what the server sent, never computing a KPI
 * of its own. Every type here mirrors `api/analytics/contracts.py`.
 */
import { BASE_URL, authHeaders } from "@/lib/api";

export type Grain = "day" | "week" | "month" | "quarter" | "year";
export type FilterOp = "in" | "eq" | "ne" | "contains" | "between" | "gte" | "lte" | "is_null" | "not_null";
export type VisualType = "kpi" | "table" | "pivot" | "line" | "area" | "bar" | "hbar" | "stacked_bar" | "scatter" | "heatmap";
export const VISUAL_TYPES: VisualType[] = ["kpi", "table", "pivot", "line", "area", "bar", "hbar", "stacked_bar", "scatter", "heatmap"];
export type NullReason = "UNKNOWN" | "NOT_MEASURED" | "NOT_APPLICABLE" | "NO_DATA" | "BLOCKED_BY_DATA" | "NOT_IN_PLAN" | "INSUFFICIENT_COVERAGE";

export interface Measure { metric_id: string; version?: number | null; alias?: string | null }
export interface DimensionRef { dimension_id: string; level?: string | null }
export interface TimeRange { start?: string | null; end?: string | null; last?: number | null; unit?: Grain | null }
export interface TimeSpec { grain?: Grain | null; range?: TimeRange | null; anchor?: string | null }
export interface Filter { dimension_id: string; op: FilterOp; values: string[] }
export interface Sort { field: string; dir: "asc" | "desc" }
export interface TopN { dimension_id: string; n: number; others?: boolean; by?: string | null }
export interface Comparison { kind: "period_over_period"; lag: number }

export interface QuerySpec {
  semantic_model_version?: string;
  measures: Measure[];
  dimensions?: DimensionRef[];
  time?: TimeSpec | null;
  filters?: Filter[];
  comparison?: Comparison | null;
  sort?: Sort[];
  limit?: number;
  top_n?: TopN | null;
  purpose?: "insights" | "explore" | "ask" | "export" | "signal" | "dashboard";
}

export interface Encoding { x?: string | null; y?: string[]; series?: string | null; color?: string | null; size?: string | null; rows?: string[]; columns?: string[] }
export interface Formatting { number_style?: "plain" | "grouped" | "compact"; unit_display?: boolean; decimals?: number | null; show_totals?: boolean }
export interface VisualSpec {
  visual_id?: string;
  visual_type: VisualType;
  title: Partial<Record<"en" | "ar", string>>;
  description: Partial<Record<"en" | "ar", string>>;
  query: QuerySpec;
  encoding?: Encoding;
  formatting?: Formatting;
  drill_path?: string[];
  drill_through?: { surface: string; params_from: string[] } | null;
  interactions?: "emit" | "receive" | "both" | "none";
  semantic_model_version?: string;
  version?: number;
}

export interface NullCell { value: number | null; reason: NullReason; why: string; numerator?: number | null; denominator?: number | null; thin?: boolean }
export interface RatioCell { value: number; numerator?: number | null; denominator?: number | null; thin?: boolean; reason?: NullReason; why?: string; basis?: string }
export type Cell = number | string | null | NullCell | RatioCell;

export interface ResultColumn {
  id: string; kind: "dimension" | "measure" | "comparison"; label: Record<string, string>; level?: string | null; dimension_kind?: "member" | "time" | "register";
  metric_id?: string; ref?: string; unit?: string; currency?: string | null; aggregation_rule?: string; additive?: boolean; evidence_class?: string; register?: string | null;
  lag?: number; blocked?: [string, string] | null;
}
export interface Coverage { measure: string; rows: number | null; measured_share: number | null; insufficient: boolean; thin_sample: boolean; total: Cell }
export interface Provenance {
  definitions: Array<{ ref: string; metric_id: string; display_name: Record<string, string>; business_definition: string; numerator: string; denominator: string; aggregation_rule: string; evidence_class: string; register: string | null; unit: string; parameters: Record<string, unknown>; lineage: string[] }>;
  source_entities: string[]; source_data: string[]; fact: string;
  filters: Array<{ dimension_id: string; label: Record<string, string>; op: string; values: string[] }>;
  blocked: Record<string, { reason: string; why: string }>;
  time: { grain: string | null; anchor: string; start: string | null; end: string | null };
  date_range: { start: string | null; end: string | null }; bucket: string;
  last_updated: string | null; data_cutoff: string | null; dataset_version: string | null;
  plan: { job_id?: string; finished_at?: string | null; as_of?: string | null; information_hash?: string; stale?: boolean; stale_reason?: string | null } | null;
  metric: string; numerator: string; denominator: string; coverage: Record<string, number | null>; notes: string[]; engine: string; scope_filtered: string[];
}
export interface ResultSet {
  query_id: string; semantic_model_version: string;
  dataset_version: { dataset_version_id: string; last_updated: string | null; data_cutoff: string | null; first_seen?: string | null; tables?: Record<string, number> };
  generated_at: string; columns: ResultColumn[]; rows: Cell[][]; empty: boolean;
  coverage: Record<string, Coverage>; provenance: Provenance;
  bounds: { truncated: boolean; limit_applied: number; top_n_applied: TopN | null; rows: number };
  timing: { planned_ms: number; executed_ms: number; cache: "hit" | "miss" | "bypass" };
  spec: QuerySpec; spec_hash: string;
}

export interface MetricDoc {
  metric_id: string; version: number; ref: string; display_name: Record<string, string>; description: Record<string, string>; business_definition: string;
  numerator: string; denominator: string; source_entities: string[]; fact: string; aggregation_rule: string; allowed_dimensions: string[]; disallowed_dimensions: string[];
  required_fields: string[]; coverage_rule: { measure: string; insufficient_below: number | null; thin_sample_below: number | null }; null_behavior: Record<string, string>;
  unit: string; currency_behavior: string; grain: string; evidence_class: string; security_classification: string; domain: string; status: string; additive: boolean;
  register: string | null; time_anchor: string | null; lineage: string[]; queryable: boolean; implemented_today: string; parameters: Record<string, unknown>;
}
export interface DimensionDoc {
  id: string; label: Record<string, string>; entity: string; description: string; kind: "member" | "time" | "register"; parent: string | null;
  members: [string, string] | null; status: string; classification: string; drill_through: string | null; queryable: boolean;
}
export interface ModelDoc {
  semantic_model_version: string; domains: string[]; time_grains: Grain[]; null_reasons: string[]; value_registers: string[];
  entities: Array<{ id: string; label: Record<string, string>; description: string; source: string; key: string[]; status: string }>;
  dimensions: DimensionDoc[]; metrics: MetricDoc[];
  relationships: Array<{ from: string; to: string; on: string; cardinality: string }>;
  facts: Array<{ id: string; entity: string; dimensions: Record<string, string>; time_anchor: string; time_anchors: string[]; source: string }>;
  drill_paths: Record<string, string>; parameters: Record<string, number>;
  permissions: { role: string; classes: string[]; capabilities: string[] };
  capabilities: Record<"viewAnalytics" | "createAnalysis" | "editOwnAnalysis" | "shareAnalysis" | "exportAnalytics" | "askZaad" | "manageAnalytics", boolean>;
}

export interface Validation {
  valid: boolean; code?: string; message?: string; fact?: string; metrics?: string[]; dimensions?: Array<{ id: string; route: string; level: string | null }>;
  grain?: string | null; recommended_visual?: VisualType; visual_reason?: string; allowed_dimensions?: string[]; notes?: string[];
}

export interface SavedAnalysis {
  analysis_id: string; name: string; description: string | null; owner: string; visibility: "private" | "workspace"; origin: "user" | "ask_zaad" | "zaad_curated";
  visual: VisualSpec; semantic_model_version: string; dataset_version_id: string | null; notes: string | null; version: number; created_at: string; updated_at: string;
  compatibility: { compatible: boolean; codes: string[]; message?: string; fact?: string; metrics?: string[] };
}
export interface DashboardTile { tile_id: string; analysis_id: string; x: number; y: number; w: number; h: number }
export interface DashboardSpec { tiles: DashboardTile[]; shared_filters: Filter[]; time?: TimeSpec | null; semantic_model_version?: string }
export interface Dashboard {
  dashboard_id: string; name: string; description: string | null; owner: string; visibility: "private" | "workspace"; spec: DashboardSpec;
  semantic_model_version: string; version: number; created_at: string; updated_at: string; tiles: number;
  analyses?: Record<string, SavedAnalysis>; missing?: string[];
}
export interface Claim { kind: "OBSERVATION" | "ASSOCIATION" | "MODELED" | "PLAN_RESULT" | "MISSING"; text: string; source: "model" | "rules" }
export interface AskAnswer {
  answered: boolean; question?: string; intent?: string; planner?: "rules" | "model"; attempts: Array<{ source: string; outcome: string; code?: string; message?: string }>;
  spec?: QuerySpec; visual?: VisualSpec; visual_reason?: string; result?: ResultSet; claims?: Claim[]; explanation_plan?: string[]; clarification?: string | null;
  reasons_present?: string[]; warnings: string[]; data_cutoff: string | null; dataset_version?: ResultSet["dataset_version"];
  handoff?: { possible: boolean; skus: string[]; suppliers: string[] }; timing_ms: number;
}
export interface Handoff {
  context: { skus: string[]; suppliers: string[]; locations: string[]; time_window: Record<string, unknown>; observed_issue: string; metrics: string[]; fact: string; spec_hash: string; note: string };
  request_built: boolean; refusal?: { code: string; message: string }; request_summary?: Record<string, unknown>; build_warnings?: string[]; notes?: string[];
  job: { submitted: boolean; job_id?: string; poll?: string; error?: string; message?: string } | null;
}

export class AnalyticsError extends Error {
  code: string | null;
  status: number;
  constructor(message: string, code: string | null, status: number) { super(message); this.name = "AnalyticsError"; this.code = code; this.status = status; }
}

async function failure(res: Response): Promise<AnalyticsError> {
  let message = `HTTP ${res.status}`;
  let code: string | null = null;
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") message = detail;
    else if (detail && typeof detail === "object") { message = String(detail.message ?? JSON.stringify(detail)); code = detail.code ?? null; }
  } catch { /* keep the status line */ }
  return new AnalyticsError(message, code, res.status);
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers ?? {}) } });
  if (!res.ok) throw await failure(res);
  return res.status === 204 ? (undefined as T) : (res.json() as Promise<T>);
}

const base = "/api/zaad/analytics";
const q = (params: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const text = s.toString();
  return text ? `?${text}` : "";
};

export const fetchModel = (locale = "en") => call<ModelDoc>(`${base}/model${q({ locale })}`);
export const runQuery = (spec: QuerySpec, options: { noCache?: boolean } = {}) =>
  call<ResultSet>(`${base}/query`, { method: "POST", body: JSON.stringify(spec), headers: options.noCache ? { "Cache-Control": "no-cache" } : {} });
export const validateQuery = (spec: QuerySpec) => call<Validation>(`${base}/validate`, { method: "POST", body: JSON.stringify(spec) });
export const fetchMembers = (dimension: string, search?: string, limit = 100) =>
  call<{ dimension_id: string; members: string[] }>(`${base}/dimensions/${encodeURIComponent(dimension)}/members${q({ q: search, limit })}`);
export const fetchAllowedDimensions = (metrics: string[]) => call<{ metrics: string[]; dimensions: string[] }>(`${base}/allowed-dimensions${q({ metrics: metrics.join(",") })}`);
export const fetchDatasetVersion = (recorded?: string | null) =>
  call<ResultSet["dataset_version"] & { moved?: { stale: boolean; current: string; recorded: string | null; tables_moved: string[] } }>(`${base}/dataset-version${q({ recorded })}`);

export const listAnalyses = (options: { q?: string; origin?: string; limit?: number; offset?: number } = {}) =>
  call<{ rows: SavedAnalysis[]; total: number; limit: number; offset: number }>(`${base}/analyses${q(options)}`);
export const readAnalysis = (id: string) => call<SavedAnalysis>(`${base}/analyses/${encodeURIComponent(id)}`);
export const createAnalysis = (body: { name: string; description?: string | null; visual: VisualSpec; visibility?: "private" | "workspace"; origin?: "user" | "ask_zaad"; notes?: string | null }) =>
  call<SavedAnalysis>(`${base}/analyses`, { method: "POST", body: JSON.stringify(body) });
export const updateAnalysis = (id: string, changes: Partial<{ name: string; description: string | null; visual: VisualSpec; visibility: "private" | "workspace"; notes: string | null }>) =>
  call<SavedAnalysis>(`${base}/analyses/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(changes) });
export const deleteAnalysis = (id: string) => call<void>(`${base}/analyses/${encodeURIComponent(id)}`, { method: "DELETE" });
export const runAnalysis = (id: string) =>
  call<{ analysis: SavedAnalysis; result: ResultSet; moved: { stale: boolean; current: string; recorded: string | null; tables_moved: string[] } }>(`${base}/analyses/${encodeURIComponent(id)}/run`, { method: "POST" });

export const listDashboards = (options: { limit?: number; offset?: number } = {}) =>
  call<{ rows: Dashboard[]; total: number; limit: number; offset: number }>(`${base}/dashboards${q(options)}`);
export const readDashboard = (id: string) => call<Dashboard>(`${base}/dashboards/${encodeURIComponent(id)}`);
export const createDashboard = (body: { name: string; description?: string | null; spec?: DashboardSpec; visibility?: "private" | "workspace" }) =>
  call<Dashboard>(`${base}/dashboards`, { method: "POST", body: JSON.stringify(body) });
export const updateDashboard = (id: string, changes: Partial<{ name: string; description: string | null; spec: DashboardSpec; visibility: "private" | "workspace" }>) =>
  call<Dashboard>(`${base}/dashboards/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify(changes) });
export const duplicateDashboard = (id: string) => call<Dashboard>(`${base}/dashboards/${encodeURIComponent(id)}/duplicate`, { method: "POST" });
export const deleteDashboard = (id: string) => call<void>(`${base}/dashboards/${encodeURIComponent(id)}`, { method: "DELETE" });

export const askZaad = (body: { question: string; locale?: "en" | "ar"; previous?: QuerySpec | null; previous_visual_type?: VisualType | null; conversation_id?: string | null }) =>
  call<AskAnswer>(`${base}/ask`, { method: "POST", body: JSON.stringify(body) });
export const askStatus = () => call<{ model_available: boolean; provider: string | null; fallback: string }>(`${base}/ask/status`);
export const fetchSupplierSignals = (months = 12) => call<Record<string, unknown>>(`${base}/signals/supplier-deterioration${q({ months })}`);
export const requestHandoff = (body: { query: QuerySpec; observed_issue?: string; skus?: string[]; suppliers?: string[]; locations?: string[]; submit?: boolean }) =>
  call<Handoff>(`${base}/handoff`, { method: "POST", body: JSON.stringify(body) });

/** Exports go through a real download: the endpoint answers a file, so this posts and hands the blob to the browser. */
export async function exportResult(spec: QuerySpec, fmt: "csv" | "xlsx", name: string, locale: "en" | "ar" = "en"): Promise<void> {
  const res = await fetch(`${BASE_URL}${base}/export${q({ fmt, name, locale })}`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(spec) });
  if (!res.ok) throw await failure(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = (res.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1]) ?? `${name}.${fmt}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
