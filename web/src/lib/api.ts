/**
 * Zaad Supply API client.
 * All fetch calls go through this module.
 * Base URL is read from NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 */

/**
 * Where the API is. Exported because the operating product's own client (`lib/zaad/product.ts`)
 * had a second copy of this line: two private constants with one definition, which agree until
 * the day someone changes one of them and the product's data calls and the legacy ones point at
 * different hosts.
 */
export const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

import { clearTenantClientState } from "@/lib/tenant-state";

const TOKEN_KEY = "harvestmind.operator-token";

/** A refused response, with its status kept so callers can tell "not accepted" from "not reachable". */
export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) { super(detail); this.name = "ApiError"; this.status = status; }
}

/**
 * Does the server accept this credential? Asked with the candidate alone — never with the credential
 * already stored — and before anything of the previous workspace is touched (SEC-038). A network
 * failure counts as "not accepted": the person keeps whatever session they had.
 */
export async function credentialAccepted(candidate: string): Promise<boolean> {
  try {
    const r = await fetch(`${BASE_URL}/me`, { headers: { Authorization: `Bearer ${candidate.trim()}` } });
    return r.ok;
  } catch { return false; }
}

export function getApiToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setApiToken(token: string): void {
  if (typeof window === "undefined") return;
  const cleaned = token.trim();
  if (cleaned) window.sessionStorage.setItem(TOKEN_KEY, cleaned);
  else window.sessionStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event("harvestmind-auth-change"));
}

/**
 * Every key the interface writes for a workspace, cleared with the credential (security review 2026-09,
 * SEC-029 / SEC-038). One definition, in `lib/tenant-state`; this name stays for its callers.
 */
export function clearWorkspaceStorage(): void {
  clearTenantClientState();
}

export function clearApiToken(): void {
  clearTenantClientState();
  setApiToken("");
}

export function authHeaders(): Record<string, string> {
  const token = getApiToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((e: { loc?: unknown[]; msg?: string }) =>
        `${e.loc?.join(".") || "request"}: ${e.msg || "Invalid input"}`).join("; ");
      else if (body.detail != null) detail = JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface DiagnosticSummary {
  partner_name: string;
  as_of: string;
  period_days: number;
  row_counts: Record<string, number>;
  waste: {
    total_usd: number;
    by_product: Array<{ product_name: string; quantity_lost_kg: number; loss_usd: number }>;
    by_reason: Array<{ reason: string; quantity_lost_kg: number; loss_usd: number }>;
    n_rows: number;
  };
  shortage: {
    total_usd: number;
    by_product: Array<{ product_name: string; missed_kg: number; loss_usd: number }>;
    by_buyer: Array<{ buyer_name: string; missed_kg: number; loss_usd: number }>;
    n_at_risk: number;
  };
  supplier: {
    suppliers: Array<{
      supplier_id: string;
      supplier_name: string;
      n_deliveries: number;
      fill_rate: number | null;  // null = no ordered-quantity data
      rejection_rate: number;
      risk_level: "High" | "Medium" | "Low" | "Unknown";
    }>;
    n_risky: number;
    n_unknown?: number;
  };
  buyer: {
    buyers: Array<{
      buyer_id: string;
      buyer_name: string;
      n_orders: number;
      fulfillment_rate: number;
      substitution_rate: number;
      missed_rate: number;
      risk_level: "High" | "Medium" | "Low";
    }>;
    n_risky: number;
  };
  traceability: {
    completeness_pct: number;
    total_lots: number;
    complete_lots: number;
    incomplete_lots: Array<{ lot_id: string; product_name: string; missing_fields: string[] }>;
    missing_breakdown: Record<string, number>;
  };
  atp: {
    products: Array<{
      product_id: string;
      product_name: string;
      total_on_hand_kg: number;
      committed_kg: number;
      expired_kg: number;
      near_expiry_kg: number;
      usable_kg: number;
      atp_kg: number;
      near_expiry_pct: number;
      risk_level: "High" | "Medium" | "Low";
    }>;
    n_risky: number;
  };
  recommendations: Array<{
    product_name: string;
    product_id: string;
    atp_kg: number;
    safe_commit_kg: number;
    holdback_kg: number;
    near_expiry_kg: number;
    supplier_fill_rate: number;
    buyer_fulfillment_rate: number;
    risk_level: "High" | "Medium" | "Low";
    risk_flags: string[];
    recommendation_text: string;
  }>;
  savings: {
    addressable_loss_usd: number;          // annualized
    addressable_loss_usd_period?: number;  // raw period total
    period_days?: number;
    annualization_factor?: number;
    reduction_pct_low?: number;
    reduction_pct_high?: number;
    reduction_pct_assumed: number;
    estimated_annual_savings_usd_low?: number;
    estimated_annual_savings_usd_high?: number;
    estimated_annual_savings_usd: number;
    waste_loss_usd: number;
    shortage_loss_usd: number;
  };
  period_days_detected?: number;
  top_risks: Array<{ category: string; item: string; loss_usd: number }>;
  total_waste_loss_usd: number;
  total_shortage_loss_usd: number;
  total_addressable_loss_usd: number;
  n_risky_suppliers: number;
  n_risky_products: number;
  n_risky_buyers: number;
  traceability_completeness_pct: number;
}

export interface DataQualityReport {
  score: number;
  score_label: string;
  tables: Record<string, { row_count: number; status: string; issues: string[] }>;
  errors: string[];
  warnings: string[];
  total_rows: number;
}

export interface IntakeStatus {
  tables: Record<string, { description: string; row_count: number; loaded: boolean }>;
  any_data_loaded: boolean;
  all_tables_loaded: boolean;
}

export interface UploadResult {
  table: string;
  description: string;
  rows_inserted: number;
  warnings: string[];
  errors: string[];
}

export interface SampleLoadResult {
  status: string;
  tables_loaded: number;
  rows_by_table: Record<string, number>;
  total_rows: number;
  errors: string[];
}

export interface DemandForecastProduct {
  product_name: string;
  model: string;
  forecast_kg_per_week: number;
  quantiles_kg: Record<string, number>;
  n_holdout_residuals: number;
  drivers: string[];
}

export interface DemandForecastResponse {
  as_of: string;
  horizon_weeks: number;
  products: DemandForecastProduct[];
  model_info: { status: string; [k: string]: unknown };
}

export interface ForecastEvalFold {
  fold: number;
  origin: string;
  n_series: number;
  wape_model: number;
  wape_seasonal_naive: number;
  bias_pct_model: number;
}

export interface ForecastEvaluation {
  status: string;
  folds?: ForecastEvalFold[];
  wape_model?: number;
  wape_seasonal_naive?: number;
  oos_mase_ratio?: number | null;
  bias_pct_model?: number | null;
  gate_passed: boolean | null;
  gate_rule?: string;
  metrics_policy?: string;
  weeks_available?: number;
}

export interface SupplierRiskEntry {
  supplier_id: string;
  supplier_name: string;
  n_deliveries: number;
  observed_mean: number | null;
  posterior_mean: number;
  downside: number;
  spread: number;
  shrinkage: number;
  risk_level: string;
}

export interface SupplyRiskResponse {
  suppliers: SupplierRiskEntry[];
  prior: { mean?: number; kappa?: number; n_suppliers?: number; downside_quantile?: number; [k: string]: unknown };
  calibration: {
    status: string;
    gate_passed: boolean | null;
    coverage_10_90?: number;
    ks_statistic?: number;
    n_held_out?: number;
    gate_rule?: string;
  };
  covariates: { signals: Array<{ signal: string; admitted: boolean; reason?: string }>; policy: string };
}

export interface BenchmarkPolicyRow {
  cost_per_origin: number;
  service_pct: number | null;
  waste_kg_per_origin: number;
  n_folds: number;
}

export interface BenchmarkEdge {
  edge_pct: number | null;
  wins: number;
  n: number;
  paired_t: number | null;
}

export interface BenchmarkResult {
  status: string;
  policies?: Record<string, BenchmarkPolicyRow>;
  sp_vs_deterministic_lp?: BenchmarkEdge;
  sp_vs_naive?: BenchmarkEdge;
  sp_vs_order_up_to?: BenchmarkEdge;
  gate_passed: boolean | null;
  verdict?: string;
  spot_economics?: { spot_cost_multiplier: number; spot_capacity_factor: number; note: string };
  scoring?: string;
  data_basis?: string;
  weeks_available?: number;
  weeks_required?: number;
}

export interface RoiCards {
  ceiling_card: {
    status: string;
    basis: string;
    note: string;
    annual_low_usd: number;
    annual_high_usd: number;
    addressable_loss_usd: number;
  };
  measured_card: {
    status: string;
    note?: string;
    sp_vs_lp_edge_pct?: number | null;
    wins?: number;
    n_origins?: number;
    paired_t?: number | null;
    gate_passed?: boolean;
    verdict?: string;
    weeks_available?: number;
    weeks_required?: number;
  };
  do_not_sum: string;
}

export interface ConfidenceIndex {
  index: number | null;
  label: string;
  arithmetic?: string;
  reason?: string;
  components?: { demand_oos_wape: number; avg_supplier_spread: number };
}

export interface ExtractionFieldMeta {
  confidence: number;
  inference_source: string;
  requires_confirmation: boolean;
  flag_reason?: string | null;
}

export interface ExtractionMapping {
  source_column: string;
  target_field: string;
  confidence: number;
  reasoning: string;
  alternative_mapping?: string | null;
}

export interface ExtractionRow {
  row_index: number;
  table: string;
  fields: Record<string, unknown>;
  field_metadata: Record<string, ExtractionFieldMeta>;
  flags: string[];
  requires_confirmation: boolean;
  rejected: boolean;
  rejection_reason?: string | null;
}

export interface ExtractionResultPayload {
  session_id: string;
  source_files: string[];
  column_mappings: ExtractionMapping[];
  extracted_rows: ExtractionRow[];
  unmapped_columns: string[];
  schema_gaps: string[];
  summary: {
    total_rows: number;
    auto_accepted: number;
    flagged_for_review: number;
    rejected: number;
    tables_found: string[];
    tables_missing: string[];
    schema_coverage_pct: number;
    overall_confidence: number;
    estimated_api_cost_usd?: number | null;
  };
  requires_human_review: boolean;
  mock_mode: boolean;
  status: string;
  rejection_guidance?: string | null;
  sufficiency_warnings: string[];
  fallback_used: boolean;
}

export interface ConfirmResponse {
  session_id: string;
  rows_inserted: Record<string, number>;
  total_inserted: number;
  corrections_recorded: number;
  sufficiency_warnings: string[];
}

export interface PoolStatus {
  pool: {
    n_operators_contributing: number;
    n_signals: number;
    coverage_by_category: Record<string, number>;
    signals_by_type: Record<string, number>;
  };
  operator?: {
    operator_id: string;
    pool_consent: boolean;
    pool_contribution_count: number;
  };
}

// ── API calls ──────────────────────────────────────────────────────────────

export async function getDiagnosticSummary(
  partnerName = "Operator",
  days = 365
): Promise<DiagnosticSummary> {
  return apiFetch<DiagnosticSummary>(
    `/diagnostics/summary?partner_name=${encodeURIComponent(partnerName)}&days=${days}`
  );
}


export async function getDemandForecast(weeks = 4): Promise<DemandForecastResponse> {
  return apiFetch<DemandForecastResponse>(`/forecasts/demand?weeks=${weeks}`);
}

export async function getForecastEvaluation(): Promise<ForecastEvaluation> {
  return apiFetch<ForecastEvaluation>("/forecasts/demand/evaluation");
}


export async function getSupplyRisk(): Promise<SupplyRiskResponse> {
  return apiFetch<SupplyRiskResponse>("/forecasts/supply");
}


export async function runBenchmark(
  spotMult = 1.3,
  spotCap = 0.3,
  folds = 8
): Promise<BenchmarkResult> {
  return apiFetch<BenchmarkResult>(
    `/backtest/benchmark?spot_cost_multiplier=${spotMult}&spot_capacity_factor=${spotCap}&folds=${folds}`,
    { method: "POST" }
  );
}


export async function getRoiCards(): Promise<RoiCards> {
  return apiFetch<RoiCards>("/reports/roi-cards");
}

export async function getConfidence(): Promise<ConfidenceIndex> {
  return apiFetch<ConfidenceIndex>("/reports/confidence");
}


export async function extractFiles(files: File[]): Promise<ExtractionResultPayload> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const res = await fetch(`${BASE_URL}/intake/extract`, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<ExtractionResultPayload>;
}

export async function getExtractionSession(id: string): Promise<ExtractionResultPayload> {
  return apiFetch<ExtractionResultPayload>(`/intake/session/${encodeURIComponent(id)}`);
}

export async function confirmExtraction(payload: {
  session_id: string;
  rows: Array<{ row_index: number; table: string; fields: Record<string, unknown>; accepted: boolean }>;
  corrections: Array<Record<string, unknown>>;
  actioned_flag_indices: number[];
}): Promise<ConfirmResponse> {
  return apiFetch<ConfirmResponse>("/intake/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}


export async function getPoolStatus(operatorId?: string): Promise<PoolStatus> {
  const q = operatorId ? `?operator_id=${encodeURIComponent(operatorId)}` : "";
  return apiFetch<PoolStatus>(`/pool/status${q}`);
}

export async function setPoolConsent(consented: boolean, operatorId?: string): Promise<{ pool_consent: boolean; note: string }> {
  const operator = operatorId ? `&operator_id=${encodeURIComponent(operatorId)}` : "";
  return apiFetch(`/pool/consent?consented=${consented}${operator}`, { method: "POST" });
}

export async function getDataQuality(): Promise<DataQualityReport> {
  return apiFetch<DataQualityReport>("/data/quality");
}

export async function getIntakeStatus(): Promise<IntakeStatus> {
  return apiFetch<IntakeStatus>("/intake/status");
}

export async function uploadCSV(
  table: string,
  file: File
): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const url = `${BASE_URL}/intake/upload/${table}`;
  const res = await fetch(url, {
    method: "POST",
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json() as Promise<UploadResult>;
}

export async function clearStagingTable(table: string): Promise<void> {
  await apiFetch(`/intake/clear/${table}`, { method: "POST" });
}

export async function loadSampleData(): Promise<SampleLoadResult> {
  return apiFetch<SampleLoadResult>("/intake/load-sample-data", { method: "POST" });
}

export async function openDiagnosticReport(
  partnerName = "Operator",
  days = 365,
): Promise<void> {
  const path = `/reports/diagnostic?partner_name=${encodeURIComponent(partnerName)}&days=${days}`;
  const res = await fetch(`${BASE_URL}${path}`, { headers: authHeaders() });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const blobUrl = URL.createObjectURL(await res.blob());
  window.open(blobUrl, "_blank", "noopener,noreferrer");
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}

export function fmt(n: number | null | undefined, digits = 0): string {
  if (n == null || isNaN(n)) return "n/a";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtUSD(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return "n/a";
  return "$" + fmt(n, 0);
}

export function fmtPct(n: number | null | undefined, decimals = 1): string {
  if (n == null || isNaN(n)) return "n/a";
  return (n * 100).toFixed(decimals) + "%";
}

// ── Front door: access requests, identity, diagnostic jobs ───────────────

export interface AccessRequestInput {
  company: string; contact_name: string; email: string; country: string;
  sector: Sector; erp?: string; sku_count?: number | null; note?: string;
}

export function requestAccess(body: AccessRequestInput): Promise<{ id: string; status: string; message: string }> {
  return apiFetch("/access/request", { method: "POST", body: JSON.stringify(body) });
}
export type Sector = "commercial" | "produce" | "meats";
/** Table family a sector uploads into: meats share the perishable-lot tables with produce. */
export function familyOf(s: Sector | null | undefined): "commercial" | "produce" { return s === "commercial" ? "commercial" : "produce"; }
export function getSector(): Sector | null {
  if (typeof window === "undefined") return null;
  const s = window.sessionStorage.getItem("harvestmind.sector");
  return s === "commercial" || s === "produce" ? s : null;
}
export function setSector(s: Sector): void {
  if (typeof window !== "undefined") window.sessionStorage.setItem("harvestmind.sector", s);
}

export interface Me {
  operator_id: string; name: string; display_name?: string; logo_url?: string | null; sector: Sector; region: string;
  created_at: string; upload_count: number;
  /** V2: the acting person, their role and what it grants; the workspace's policy. */
  actor?: { id: string; name: string; role: string } | null;
  capabilities?: string[];
  policy?: { self_approval?: string | null; default_export_profile?: string | null } | null;
}
export function getMe(): Promise<Me> { return apiFetch<Me>("/me"); }

export type JobStatus = "queued" | "running" | "done" | "failed" | "timed_out" | "cancelled";
export interface JobStage { key: string; label: string }
export interface Job {
  id: string; kind: string; status: JobStatus; progress: string;
  /** the real step the backend is in (one of `stages`), or null before the first stage */
  stage?: string | null; stages?: JobStage[];
  /** 1 = next to start; null when unknown or not queued */
  queue_position?: number | null;
  /** the id to quote when asking ZAAD about a failed run */
  reference?: string;
  created_at: string; started_at?: string | null; finished_at?: string | null; error?: string | null;
  summary?: Record<string, unknown> | null;
  /** the structured diagnostic report (present when done) */
  report?: DiagnosticReport | null;
  timing?: { queue_wait_s?: number; run_s?: number; report_build_s?: number } | null;
}
export function startDiagnostic(): Promise<Job> { return apiFetch<Job>("/jobs/diagnostic", { method: "POST" }); }
export function getJob(id: string): Promise<Job> { return apiFetch<Job>(`/jobs/${encodeURIComponent(id)}`); }
export async function latestJob(): Promise<Job | null> { return (await apiFetch<{ job: Job | null }>("/jobs/latest")).job; }
export function cancelJob(id: string): Promise<Job> { return apiFetch<Job>(`/jobs/${encodeURIComponent(id)}/cancel`, { method: "POST" }); }
export function getReport(id: string): Promise<DiagnosticReport> { return apiFetch<DiagnosticReport>(`/jobs/${encodeURIComponent(id)}/report.json`); }

// ── the structured diagnostic report (reports/diagnostic_findings.py) ──
export type Severity = "high" | "medium" | "low" | "info";
export interface ReportRelated { kind: "sku" | "supplier" | "po" | "screen" | "decision" | string; id: string; label: string }
export interface ReportFinding {
  id: string; category: string; headline: string; severity: Severity; materiality: number | null;
  observation: string; business_implication: string; possible_driver: string | null; driver_tag: "OBSERVED" | "LIKELY DRIVER" | "UNKNOWN" | string;
  recommendation: string; confidence: "High" | "Moderate" | "Low" | string; confidence_basis: string;
  evidence: { label: string; value: string }[]; related: ReportRelated[]; summary_line?: string | null;
}
export interface ReportAction { text: string; link: ReportRelated | null }
export interface ReportLane {
  lane: string; label: string; attention: "ELEVATED" | "WATCH" | "NORMAL" | "UNAVAILABLE" | string; score: string; score_meaning: string;
  evidence_strength: string; evidence_note: string; external: string[]; exposure: string[]; response: string;
}
export interface DiagnosticReport {
  version: string; run_id: string; company: string; generated_at: string | null; sector: string | null;
  conclusion: { kind: string; headline: string; body: string; benchmark_headline?: string; replay_headline?: string };
  executive_summary: { benchmark: { label: string; statement: string | null }; replay: { label: string; statement: string | null; available: boolean };
    findings: { id: string; headline: string; line: string; severity: Severity; confidence: string }[]; actions: string[]; confidence: { level: string; statement: string; replay_level?: string | null } };
  readiness: { label: string; level: string; confidence: string; confidence_rule: string; statement: string; facts: { label: string; value: string }[];
    limitations: { effect: string }[]; missing_fields: { field: string }[]; required_missing: string[]; history_weeks: number | null; products: number | null; suppliers: number | null };
  ordering_today: { summary: string; items: { label: string; value: string; note: string | null; tag: string }[] };
  policy_benchmark: { available: boolean; title?: string; question?: string; explainer?: string; statement?: string | null; current_label: string; candidate: string | null; candidate_label: string;
    rows: { metric: string; current: string; candidate: string; difference: string; note: string | null }[];
    explanation: string[]; outcome: string | null; fold_chart: { selection: number[]; holdout_mean: number | null; threshold: number | null; title: string } | null };
  optimizer_replay: {
    title?: string; question: string; explainer: string; available: boolean; status: string; statement: string; reason?: string | null;
    currency?: string | null; currency_note?: string | null;
    scope?: { skus: string[]; sku_count: number; skus_in_workspace: number; demand_value_share: number | null; origin: string; horizon_weeks: number; rule: string | null; text: string };
    coverage?: { completed: number; planned: number; partial: boolean; dates: string[]; text: string; selection_rule: string;
      selection?: { rule: string | null; information: string | null; coverage: Record<string, number> | null; strata: Record<string, number | string> | null; swapped: { dropped: string; added: string; reason: string }[] | null } };
    table?: { metric: string; actual: string; rule: string; zaad: string; difference: string; better: boolean | null; note: string | null }[];
    not_measured?: string[]; retention_note?: string | null;
    decisions_summary?: { text?: string; unattributed_recorded_rows?: number; zaad_less_than_recorded?: number; zaad_more_than_recorded?: number;
      zaad_ordered_where_identified_recorded_had_none?: number; rows_compared_on_model_evaluated_quantity?: number;
      rows: number; changed: number; retained_rule_reviews?: number; identical_to_rule?: boolean; zaad_ordered_where_you_did_not: number; zaad_ordered_less: number; zaad_ordered_more: number; zaad_did_not_order_where_you_did: number; abstained_reviews: number; units_difference: number };
    periods?: { caption?: string; series: number[]; dates: string[]; currency: string | null; improved: number | null; worse: number | null; mean: number | null; median: number | null; worst: number | null; best: number | null; sd: number | null; ci80: [number, number] | null; n_negative: number; worst_date: string | null; text: string };
    vs_rule?: { relative: number | null; improved: number | null; identical?: boolean; text: string };
    regimes?: { state: string; periods: number; mean: number | null; improved: number | null; text: string }[]; regime_note?: string;
    operating_regimes?: { regime: string; periods: number; mean: number | null; improved: number | null; definition: string | null; text: string }[]; operating_regime_note?: string;
    decision_changes?: { available: boolean; text: string; reviews?: number; review_outcomes?: Record<string, number>; lines?: Record<string, number>; lines_total?: number; changed_lines?: number; material_lines?: number; material_reviews?: number; timing?: Record<string, number>; source_changes?: string; open_order_changes?: string; magnitude?: Record<string, number>; materiality_rule?: string };
    evidence_basis?: { text: string; by_leg: Record<string, { units: number; shares: Record<string, number> }>; demand: string; opening_state: string; rules: Record<string, string>; metrics: Record<string, string> };
    rule_conformance_note?: string | null; engine_text?: string;
    settlement?: { shares: Record<string, number>; orders: number; rules: Record<string, string>; text: string };
    lookahead?: { clean: boolean | null; snapshots: number; text: string };
    confidence?: { level: string; reasons: string[]; dimensions: Record<string, string>; rule: string };
    performance?: Record<string, number | string | null>; engine?: Record<string, string>; limits?: string[];
    // H3a: the comparator the replay used and the labels the report may use for it
    comparison?: { mode: string; readiness: string; claim_class: string | null; comparator: { type: string; fidelity: string; label: string | null };
      decision_reference?: { type: string; fidelity: string; provenance: string | null; label: string }; permissions: Record<string, boolean>;
      coverage?: Record<string, unknown> | null; caveats?: string[] } | null;
    comparator_label?: string; reference_label?: string; claim_class?: string | null;
    decisions?: { review: number; date: string; sku: string; supplier: string | null; location: string; actual_qty: number | null; rule_qty: number | null; zaad_qty: number | null;
      actual_observed_qty?: number | null; actual_evaluated_qty?: number | null; actual_fidelity?: string | null;
      actual_identity_fidelity?: string | null; actual_evaluation_fidelity?: string | null;
      zaad_vs_recorded?: string | null; comparison_basis?: string | null; zaad_action_label?: string | null;
      quantity_difference: number | null; zaad_action: string; zaad_status: string | null; zaad_policy: string | null; fallback_to_rule: boolean | null; timing: string | null;
      settlement: string | null; settlement_cell: string; outcome: Record<string, { served: number; demand: number; end_stock: number }>; economic_outcome: string }[];
  };
  provenance_ledger?: { input: string; provenance: string; plain: string; basis: string; note: string | null; replay_provenance: string | null; replay_note: string | null }[];
  consistency_checks?: { check: string; pass: boolean; detail: string }[];
  findings: ReportFinding[];
  suppliers: { available: boolean; rows: { supplier: string; share_of_value: string; products: string; receipts: string; fill: string; lead_time: string; lead_spread: string; lane: string; reading: string; evidence: string }[]; note: string };
  lanes: ReportLane[];
  actions: { now: ReportAction[]; next: ReportAction[]; monitor: ReportAction[] };
  appendix: { methodology: string[]; assumptions: { input: string; provenance: string }[]; candidates: Record<string, string>[]; gates: Record<string, unknown>; warnings: string[];
    run: Record<string, unknown>; glossary: { term: string; internal: string; meaning: string }[];
    replay?: { engine?: Record<string, string> | null; performance?: Record<string, number | string | null> | null; lookahead?: { clean: boolean | null; text: string } | null;
      settlement_rules?: Record<string, string> | null; limits?: string[] | null; confidence_rule?: string | null } };
}
export function reportUrl(id: string): string { return `${BASE_URL}/jobs/${encodeURIComponent(id)}/report.pdf`; }
export async function downloadReport(id: string): Promise<void> {
  const res = await fetch(reportUrl(id), { headers: authHeaders() });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `zaad-diagnostic-${id}.pdf`; a.click();
  URL.revokeObjectURL(url);
}
