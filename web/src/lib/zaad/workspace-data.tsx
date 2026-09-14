"use client";

/**
 * One read of the workspace, shared by Home, Decisions and Network.
 *
 * Two things happen at different speeds and the product must not pretend otherwise:
 *
 *  - Reading the workspace is fast (~4 s on a 150-product vault). It yields suppliers, sites,
 *    lanes, stock, open orders and fitted supplier reliability — everything the Network Twin and
 *    Data need. Those surfaces are usable immediately and never wait for a solve.
 *  - Planning is a minutes-long MILP. It runs on the released jobs path, which reports QUEUED and
 *    RUNNING honestly, survives a reload, and keeps the last completed plan for the workspace.
 *
 * So Home and Decisions show the last plan with the date of the data it used, and running a new
 * one is a deliberate act with visible progress — not a spinner on every page load.
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "@/lib/session";
import {
  ALL_PHASES, fetchDirectory, fetchWorkspaceState, fetchWorkspaceStateFor,
  listPlanJobs, readPlanJob, submitPlanJob, type JobSummary,
} from "./client";
import { fetchEvaluationJobIds } from "./product";
import { buildDecisions, planSummary, type Decision, type PlanSummary } from "./decisions";
import type { DirectoryResponse, ZaadBuild, ZaadReport, ZaadRequest } from "./types";
import { buildCanonicalModel } from "@/lib/network/adapters/canonical";
import { buildIndex, type NetworkIndex } from "@/lib/network/graph";
import type { NetworkModel } from "@/lib/network/model";

export type ReadPhase = "idle" | "reading" | "ready" | "not-ready" | "error";
export type PlanPhase = "none" | "queued" | "running" | "ready" | "failed";

/**
 * How many products a run covers by default.
 *
 * Measured, not guessed: a bounded eight-product network run took ~108 s end to end, and the
 * server gives a job roughly ten minutes. Ten products is a size that finishes comfortably inside
 * that. It is always stated in the interface and always changeable — a plan over a selection is
 * never presented as if it covered the whole catalogue.
 */
export const DEFAULT_SCOPE = 10;
export const SCOPE_CHOICES = [10, 25, 50] as const;

export interface PlanScope {
  /** The products this run covers. */
  skus: string[];
  /** Every product the workspace holds. */
  total: number;
  /** The rule that chose them, in the operator's words. */
  rule: string;
}

export interface WorkspaceData {
  phase: ReadPhase;
  planPhase: PlanPhase;
  /** Set when the workspace cannot be planned yet — missing uploads, in the server's own words. */
  notReady: string | null;
  error: string | null;
  planError: string | null;
  request: ZaadRequest | null;
  build: ZaadBuild | null;
  report: ZaadReport | null;
  directory: DirectoryResponse | null;
  decisions: Decision[];
  summary: PlanSummary | null;
  network: NetworkModel | null;
  index: NetworkIndex | null;
  /** What the plan in hand covered, null when it covered everything. */
  scope: PlanScope | null;
  /** When the plan in hand finished, from the job record. */
  computedAt: Date | null;
  /** Runs a new plan over `size` products, or every product when `size` is "all". */
  run: (size?: number | "all") => void;
  refresh: () => void;
}

const WorkspaceDataContext = createContext<WorkspaceData | null>(null);

const messageOf = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** The server says `workspace_not_ready` with an operator-facing sentence; keep its words. */
function notReadyMessage(e: unknown): string | null {
  const text = messageOf(e);
  if (/workspace_not_ready/i.test(text) || /upload .* before planning/i.test(text) || /^Upload /i.test(text)) {
    return text
      .replace(/^\{?['"]?code['"]?:\s*['"]?workspace_not_ready['"]?,?\s*/i, "")
      .replace(/^['"]?message['"]?:\s*/i, "")
      .replace(/[{}'"]/g, "")
      .trim();
  }
  return null;
}

/**
 * Products whose open orders carry a declared amendment right.
 *
 * These must never be left out of a run. They are where the open-PO decisions live, and a
 * selection that drops one leaves its declared options pointing at an order the request no
 * longer carries — which the server rightly refuses.
 */
export function productsWithAmendmentRights(request: ZaadRequest): Set<string> {
  const bySource = new Map(request.sources.map((s) => [s.id, s.sku]));
  const out = new Set<string>();
  for (const po of request.pipeline) {
    const declared = (po.options ?? []).some((o) => o.action !== "keep");
    const sku = bySource.get(po.source);
    if (declared && sku) out.add(sku);
  }
  return out;
}

/**
 * Rank products by where the decisions are: units still on open order first, then the value
 * sitting in stock. Deterministic, and stated in the interface wherever a scoped plan is shown.
 */
export function rankProducts(request: ZaadRequest): string[] {
  const onOrder = new Map<string, number>();
  const bySource = new Map(request.sources.map((s) => [s.id, s.sku]));
  for (const po of request.pipeline) {
    const sku = bySource.get(po.source);
    if (sku) onOrder.set(sku, (onOrder.get(sku) ?? 0) + po.expected_accepted_remaining);
  }
  const value = new Map<string, number>();
  const unitValue = new Map(request.skus.map((s) => [s.id, s.unit_value ?? 0]));
  for (const st of request.stock) {
    value.set(st.sku, (value.get(st.sku) ?? 0) + st.quantity * (unitValue.get(st.sku) ?? 0));
  }
  return request.skus
    .map((s) => s.id)
    .sort((a, b) => (onOrder.get(b) ?? 0) - (onOrder.get(a) ?? 0) || (value.get(b) ?? 0) - (value.get(a) ?? 0) || a.localeCompare(b));
}

const SCOPE_RULE = "every product with a declared order change, then the products with the most units still on order";

/** A plan covering fewer products than the workspace holds must say so. */
function scopeOf(planned: ZaadReport, full: ZaadRequest): PlanScope | null {
  const planned_skus = new Set<string>();
  for (const row of planned.protection ?? []) {
    const sku = (row as { sku?: string }).sku;
    if (sku) planned_skus.add(sku);
  }
  if (!planned_skus.size || planned_skus.size >= full.skus.length) return null;
  return { skus: [...planned_skus], total: full.skus.length, rule: SCOPE_RULE };
}

export function WorkspaceDataProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const [phase, setPhase] = useState<ReadPhase>("idle");
  const [planPhase, setPlanPhase] = useState<PlanPhase>("none");
  const [notReady, setNotReady] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [request, setRequest] = useState<ZaadRequest | null>(null);
  const [build, setBuild] = useState<ZaadBuild | null>(null);
  const [report, setReport] = useState<ZaadReport | null>(null);
  const [directory, setDirectory] = useState<DirectoryResponse | null>(null);
  const [scope, setScope] = useState<PlanScope | null>(null);
  const [computedAt, setComputedAt] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);
  const poll = useRef<number | null>(null);
  const alive = useRef(true);

  useEffect(() => () => { alive.current = false; if (poll.current) window.clearInterval(poll.current); }, []);

  /** Read the whole workspace, then attach the last completed plan if there is one. */
  useEffect(() => {
    if (session.status !== "authenticated") { setPhase("idle"); return; }
    let live = true;
    setPhase("reading");
    setError(null);
    setNotReady(null);

    (async () => {
      let state;
      try {
        state = await fetchWorkspaceState(ALL_PHASES);
      } catch (e) {
        if (!live) return;
        const missing = notReadyMessage(e);
        if (missing) { setNotReady(missing); setPhase("not-ready"); }
        else { setError(messageOf(e)); setPhase("error"); }
        return;
      }
      if (!live) return;
      setRequest(state.request);
      setBuild(state.build);
      setPhase("ready");
      // A workspace without the optional supplier upload still plans, so this never blocks a page.
      fetchDirectory().then((d) => live && setDirectory(d)).catch(() => live && setDirectory(null));

      // The last plan this workspace computed, whenever it was — and never an evaluation run. An
      // evaluation uses the same jobs path, and one of its two runs carries a proposed order
      // overlaid on the pipeline; showing that as "your plan" would present an order nobody has
      // placed as the operator's position.
      try {
        const [{ jobs }, evaluations] = await Promise.all([
          listPlanJobs(),
          fetchEvaluationJobIds().catch(() => ({ evaluation_job_ids: [] as string[] })),
        ]);
        const ours = new Set(evaluations.evaluation_job_ids);
        const plans = jobs.filter((j) => !ours.has(j.id));
        const last = plans.find((j) => j.status === "DONE");
        const active = plans.find((j) => j.status === "RUNNING" || j.status === "QUEUED");
        if (active) { watch(active.id); return; }
        if (!last || !live) return;
        const detail = await readPlanJob(last.id);
        if (!live || !detail.report) return;
        setReport(detail.report);
        setComputedAt(detail.finished_at ? new Date(detail.finished_at) : null);
        setScope(scopeOf(detail.report, state.request));
        setPlanPhase("ready");
      } catch {
        // no job history is simply no plan yet
      }
    })();

    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.status, tick]);

  const watch = (jobId: string) => {
    if (poll.current) window.clearInterval(poll.current);
    setPlanPhase("queued");
    setPlanError(null);
    const check = async () => {
      try {
        const detail = await readPlanJob(jobId);
        if (!alive.current) return;
        if (detail.status === "RUNNING") setPlanPhase("running");
        if (detail.status === "QUEUED") setPlanPhase("queued");
        if (["DONE", "FAILED", "TIMEOUT", "CANCELLED"].includes(detail.status)) {
          if (poll.current) window.clearInterval(poll.current);
          poll.current = null;
          if (detail.status === "DONE" && detail.report) {
            setReport(detail.report);
            setComputedAt(detail.finished_at ? new Date(detail.finished_at) : new Date());
            setPlanPhase("ready");
          } else {
            setPlanPhase("failed");
            setPlanError(
              detail.status === "TIMEOUT"
                ? "The run did not finish inside the time it is given. Try a smaller selection of products."
                : detail.error || "The run stopped without producing a plan.",
            );
          }
        }
      } catch (e) {
        if (poll.current) window.clearInterval(poll.current);
        poll.current = null;
        setPlanPhase("failed");
        setPlanError(messageOf(e));
      }
    };
    check();
    poll.current = window.setInterval(check, 3000);
  };

  const run = async (size: number | "all" = DEFAULT_SCOPE) => {
    if (!request) return;
    setPlanPhase("queued");
    setPlanError(null);
    try {
      const ranked = rankProducts(request);
      // Every product with a declared amendment right comes first and always travels with the run.
      const must = productsWithAmendmentRights(request);
      const chosen = size === "all"
        ? ranked
        : [...ranked.filter((s) => must.has(s)), ...ranked.filter((s) => !must.has(s))].slice(0, Math.max(size, must.size));
      const coversAll = chosen.length >= request.skus.length;
      const body = coversAll
        ? request
        : (await fetchWorkspaceStateFor(chosen, ALL_PHASES)).request;
      setScope(coversAll ? null : { skus: chosen, total: request.skus.length, rule: SCOPE_RULE });
      const { job_id } = await submitPlanJob(body);
      watch(job_id);
    } catch (e) {
      setPlanPhase("failed");
      setPlanError(messageOf(e));
    }
  };

  const value = useMemo<WorkspaceData>(() => {
    const decisions = report ? buildDecisions(report, request, build) : [];
    const summary = report ? planSummary(report, request) : null;
    const network = request
      ? buildCanonicalModel({
          request, build: build ?? {}, report, directory,
          homeRegion: session.workspace?.region || null,
          workspaceName: session.workspace?.name ?? "Your workspace",
        })
      : null;
    return {
      phase, planPhase, notReady, error, planError,
      request, build, report, directory, decisions, summary, network,
      index: network ? buildIndex(network) : null,
      scope, computedAt, run,
      refresh: () => setTick((t) => t + 1),
    };
  }, [phase, planPhase, notReady, error, planError, request, build, report, directory, scope, computedAt, run, session.workspace]);

  return <WorkspaceDataContext.Provider value={value}>{children}</WorkspaceDataContext.Provider>;
}

export function useWorkspaceData(): WorkspaceData {
  const value = useContext(WorkspaceDataContext);
  if (!value) throw new Error("useWorkspaceData must be used inside <WorkspaceDataProvider>");
  return value;
}

/** Only the decisions that still want a human answer. */
export function useOpenDecisions(): Decision[] {
  const { decisions } = useWorkspaceData();
  return useMemo(() => decisions.filter((d) => d.needsReview), [decisions]);
}

/** Jobs still in flight, for the shell's progress line. */
export function activeJob(jobs: JobSummary[]): JobSummary | undefined {
  return jobs.find((j) => j.status === "RUNNING" || j.status === "QUEUED");
}
