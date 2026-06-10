/**
 * HarvestMind API client.
 * All fetch calls go through this module.
 * Base URL is read from NEXT_PUBLIC_API_URL (default: http://localhost:8000).
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function apiFetch<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new Error(detail);
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
  const res = await fetch(url, { method: "POST", body: form });
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

export function fmt(n: number | null | undefined, digits = 0): string {
  if (n == null || isNaN(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtUSD(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return "$—";
  return "$" + fmt(n, 0);
}

export function fmtPct(n: number | null | undefined, decimals = 1): string {
  if (n == null || isNaN(n)) return "—%";
  return (n * 100).toFixed(decimals) + "%";
}
