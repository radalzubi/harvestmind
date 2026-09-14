"use client";

/**
 * Is ZAAD ready to plan, and if not, what is the next single thing to do?
 *
 * The answer is assembled from what the server already reports — loaded tables, the quality
 * report and the planning adapter's own refusal message — and phrased as a data source with a
 * state, not as a database table. Today every source is a file the operator uploads; the shape
 * is the same when a source is an ERP or an EDI feed instead.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { getDataQuality, getIntakeStatus, type DataQualityReport, type IntakeStatus } from "@/lib/api";
import { useSession } from "@/lib/session";

export type SourceState = "missing" | "loaded" | "problem";

export interface DataSource {
  /** The staging table underneath. Shown only under technical details. */
  table: string;
  name: string;
  why: string;
  required: boolean;
  state: SourceState;
  rows: number;
  issues: string[];
}

export interface Readiness {
  loading: boolean;
  error: string | null;
  sources: DataSource[];
  /** True when every required source has rows. */
  canPlan: boolean;
  /** The one thing to do next, or null when there is nothing. */
  nextStep: { title: string; detail: string; table: string | null } | null;
  score: number | null;
  scoreLabel: string | null;
  totalRows: number;
  refresh: () => void;
}

const COMMERCIAL: Array<{ table: string; name: string; why: string; required: boolean }> = [
  { table: "stg_fmcg_skus", name: "Product list", why: "What you sell, its pack size and value", required: true },
  { table: "stg_fmcg_orders", name: "Customer orders", why: "What your customers actually bought, so demand can be fitted", required: true },
  { table: "stg_fmcg_purchase_orders", name: "Purchase orders", why: "What you have on order and when it is due", required: false },
  { table: "stg_fmcg_receipts", name: "Goods received", why: "What actually arrived, so supplier reliability can be measured", required: false },
  { table: "stg_fmcg_inventory", name: "Stock counts", why: "What you are holding today", required: false },
  { table: "stg_fmcg_suppliers", name: "Supplier list", why: "Supplier names, origins and shipping routes", required: false },
];

const PRODUCE: Array<{ table: string; name: string; why: string; required: boolean }> = [
  { table: "stg_products", name: "Products", why: "What you handle and its shelf life", required: true },
  { table: "stg_supplier_deliveries", name: "Supplier deliveries", why: "What each supplier delivered and when", required: true },
  { table: "stg_inventory_lots", name: "Inventory lots", why: "What you are holding, by lot and expiry", required: true },
  { table: "stg_buyer_orders", name: "Buyer orders", why: "What your buyers ordered and what was fulfilled", required: true },
  { table: "stg_waste_adjustments", name: "Waste log", why: "What was written off and why", required: false },
];

export function useReadiness(): Readiness {
  const session = useSession();
  const [status, setStatus] = useState<IntakeStatus | null>(null);
  const [quality, setQuality] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (session.status !== "authenticated") return;
    let alive = true;
    setLoading(true);
    setError(null);
    Promise.all([getIntakeStatus(), getDataQuality().catch(() => null)])
      .then(([s, q]) => { if (!alive) return; setStatus(s); setQuality(q); })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [session.status, tick]);

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  return useMemo(() => ({
    ...derive(session.workspace?.family === "produce" ? PRODUCE : COMMERCIAL, status, quality),
    loading, error, refresh,
  }), [status, quality, loading, error, session.workspace, refresh]);
}

/**
 * The pure part: catalog plus what the server reports, in, readiness out. Separated from the
 * hook so the rule that decides "can ZAAD plan, and what is the one next thing" is testable.
 */
export function derive(
  catalog: Array<{ table: string; name: string; why: string; required: boolean }>,
  status: IntakeStatus | null,
  quality: DataQualityReport | null,
): Omit<Readiness, "loading" | "error" | "refresh"> {
  const sources: DataSource[] = catalog.map((c) => {
    const loaded = status?.tables?.[c.table];
    const q = quality?.tables?.[c.table];
    const rows = loaded?.row_count ?? q?.row_count ?? 0;
    const issues = rows === 0 ? [] : q?.issues ?? [];
    return { ...c, rows, issues, state: rows === 0 ? "missing" : issues.length ? "problem" : "loaded" };
  });
  const missingRequired = sources.filter((s) => s.required && s.state === "missing");
  const problems = sources.filter((s) => s.state === "problem");
  // One next step, and it is always the one that unblocks the most: a missing required source
  // before a quality problem, and a quality problem before nothing.
  const nextStep = missingRequired.length
    ? { title: `Add your ${missingRequired[0].name.toLowerCase()}`, detail: missingRequired[0].why, table: missingRequired[0].table }
    : problems.length
      ? { title: `Fix ${problems[0].issues.length} issue${problems[0].issues.length === 1 ? "" : "s"} in your ${problems[0].name.toLowerCase()}`, detail: problems[0].issues[0], table: problems[0].table }
      : null;
  return {
    sources,
    canPlan: missingRequired.length === 0,
    nextStep,
    score: quality?.score ?? null,
    scoreLabel: quality?.score_label ?? null,
    // Always the sum of the sources shown. The quality endpoint reports its own global total,
    // which can belong to a different upload family and would contradict the rows listed here.
    totalRows: sources.reduce((a, s) => a + s.rows, 0),
  };
}

export const CATALOGS = { commercial: COMMERCIAL, produce: PRODUCE };
