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
import { queueAheadOf } from "./queue";
import { fetchEvaluationJobIds, fetchInventory, fetchSummary } from "./product";
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
/**
 * A network workspace multiplies the work: three sites and thirty-six service lines make a
 * ten-product run far heavier than a ten-product run on one site. Measured here: ten products over
 * three sites did not finish inside the time the engine gave it, while two finished in twelve
 * seconds. Five is offered so a multi-site operator has a size that returns.
 */
export const SCOPE_CHOICES = [5, 10, 25, 50] as const;

/**
 * How many products the workspace *read* carries.
 *
 * Measured against a 10,000-product vault: reading the whole catalogue into the planning contract
 * took **9 minutes 43 seconds** and then failed, because the contract is capped at 5,000 products.
 * Reading 100 took 2.9 seconds. So the read is bounded, and the bound is stated wherever the things
 * it feeds — Home, Decisions and the Network Twin — are shown.
 *
 * Inventory, Purchase orders, Diagnostics and Data do not use this read at all: they query the
 * operator's records directly and are unaffected by the size of the catalogue.
 */
export const READ_LIMIT = 150;

const READ_RULE = "the products holding the most stock value";

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
  /**
   * Set when the workspace was read *without* a phase the operator has declared, because the
   * engine refused that declaration. The rest of the workspace is real; this names what is absent
   * and why, so nobody concludes from a missing open-PO decision that there was nothing to change.
   */
  degraded: string | null;
  planPhase: PlanPhase;
  /** While queued: how many runs are ahead of this one (0 = next to start), or null when unknown. */
  queueAhead: number | null;
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
  /** What the *read* covered, null when it covered the whole catalogue. */
  readScope: PlanScope | null;
  /**
   * Set when the most recent run ended without a plan and an older plan is what is on screen.
   * Told as a notice rather than by hiding the older plan: the operator asked for something and it
   * did not work, and they should hear that without losing what they already had.
   */
  lastRunFailed: string | null;
  /** When the plan in hand finished, from the job record. */
  computedAt: Date | null;
  /** The job the plan in hand came from; a decision response is recorded against it. */
  planJobId: string | null;
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

/** A minute past the time the engine gave the run. Long enough that a slow clock is not the cause. */
export const ABANDONED_GRACE_MS = 60_000;


export const ABANDONED_MESSAGE =
  "This run has been going for longer than the time it is given, which usually means it was "
  + "interrupted. Nothing was changed. Run it again, over fewer products if it keeps happening.";

/**
 * Has this run been abandoned?
 *
 * A job whose process died stays RUNNING in the store for ever — nothing reaps it — and the page
 * would poll it silently until somebody reloaded and found it still polling. The engine tells us
 * how long it gave the run; once that is comfortably past, the honest thing is to say so.
 *
 * This reads the record and changes nothing about it. Cancelling the job (which does free the
 * workspace's job slot) stays the operator's decision.
 */
export function abandoned(
  job: { status: string; started_at: string | null; timeout_s?: number | null },
  now: number = Date.now(),
): boolean {
  if (job.status !== "RUNNING" || !job.started_at || !job.timeout_s) return false;
  const started = Date.parse(job.started_at);
  if (!Number.isFinite(started)) return false;
  return now - started - job.timeout_s * 1000 > ABANDONED_GRACE_MS;
}

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
  const [queueAhead, setQueueAhead] = useState<number | null>(null);
  const [notReady, setNotReady] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [request, setRequest] = useState<ZaadRequest | null>(null);
  const [build, setBuild] = useState<ZaadBuild | null>(null);
  const [report, setReport] = useState<ZaadReport | null>(null);
  const [directory, setDirectory] = useState<DirectoryResponse | null>(null);
  const [scope, setScope] = useState<PlanScope | null>(null);
  const [readScope, setReadScope] = useState<PlanScope | null>(null);
  const [lastRunFailed, setLastRunFailed] = useState<string | null>(null);
  const [degraded, setDegraded] = useState<string | null>(null);
  const [computedAt, setComputedAt] = useState<Date | null>(null);
  const [planJobId, setPlanJobId] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const poll = useRef<number | null>(null);
  const alive = useRef(true);

  useEffect(() => () => { alive.current = false; if (poll.current) window.clearInterval(poll.current); }, []);

  /** Read the whole workspace, then attach the last completed plan if there is one. */
  useEffect(() => {
    // Nothing of a previous workspace survives a sign-out or a switch: the read below is keyed on the
    // workspace id and the state is cleared first (security review 2026-09, SEC-017).
    if (poll.current) { window.clearInterval(poll.current); poll.current = null; }
    setRequest(null); setBuild(null); setReport(null); setDirectory(null); setScope(null); setReadScope(null);
    setPlanJobId(null); setPlanPhase("none"); setQueueAhead(null); setComputedAt(null); setLastRunFailed(null); setDegraded(null);
    if (session.status !== "authenticated") { setPhase("idle"); return; }
    let live = true;
    setPhase("reading");
    setError(null);
    setNotReady(null);

    (async () => {
      let state;

      /**
       * Read the workspace, and if the engine refuses a declaration, read it again without that
       * phase rather than showing nothing.
       *
       * Observed: a declared amendment right on an order placed on the plan date makes the *whole*
       * read refuse — the planning adapter drops an order dated on or after the origin, and a right
       * pointing at a dropped order is rejected. One bad row in `stg_po_options` took Home,
       * Decisions and the Network with it. The refusal is correct; losing the workspace to it is not.
       */
      const read = async (skus: string[] | null) => {
        const fetchWith = (options: typeof ALL_PHASES) =>
          skus ? fetchWorkspaceStateFor(skus, options) : fetchWorkspaceState(options);
        try {
          setDegraded(null);
          return await fetchWith(ALL_PHASES);
        } catch (e) {
          const text = messageOf(e);
          if (!/commitments_invalid|commitments:/i.test(text)) throw e;
          const out = await fetchWith({ ...ALL_PHASES, commitments: false });
          setDegraded(
            "ZAAD read this workspace without your declared order-change rights, because the engine "
            + "refused them: " + text.replace(/^\{?['"]?code['"]?:\s*['"]?commitments_invalid['"]?,?\s*/i, "")
              .replace(/^['"]?message['"]?:\s*/i, "").replace(/[{}'"]/g, "").trim()
            + " Everything else below is real; what is missing is any recommendation to change an "
            + "open order.",
          );
          return out;
        }
      };

      // The reads that do not depend on the workspace request start now, beside it, instead of
      // after it (performance pass): the supplier directory, the plan-job list and the evaluation
      // ids are each ~150 ms on production and were serialised behind a 1.7 s read.
      const directoryPromise = fetchDirectory().catch(() => null);
      const jobsPromise = Promise.all([
        listPlanJobs(),
        fetchEvaluationJobIds().catch(() => ({ evaluation_job_ids: [] as string[] })),
      ]).catch(() => null);
      try {
        // How big is this catalogue? One indexed count, tens of milliseconds. A workspace larger
        // than the read bound is read over a named selection rather than in full — the alternative
        // is a ten-minute request that ends in a 422.
        const held = await fetchSummary().then((x) => x.products ?? 0).catch(() => 0);
        if (held > READ_LIMIT) {
          const page = await fetchInventory({ sort: "inventory_value", direction: "desc", limit: READ_LIMIT });
          const chosen = page.rows.map((row) => row.sku);
          if (!live) return;
          setReadScope({ skus: chosen, total: held, rule: READ_RULE });
          state = await read(chosen);
        } else {
          setReadScope(null);
          state = await read(null);
        }
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
      directoryPromise.then((d) => live && setDirectory(d));

      // The last plan this workspace computed, whenever it was — and never an evaluation run. An
      // evaluation uses the same jobs path, and one of its two runs carries a proposed order
      // overlaid on the pipeline; showing that as "your plan" would present an order nobody has
      // placed as the operator's position.
      try {
        const listed = await jobsPromise;
        if (!listed) return;
        const [{ jobs }, evaluations] = listed;
        const ours = new Set(evaluations.evaluation_job_ids);
        const plans = jobs.filter((j) => !ours.has(j.id));
        const last = plans.find((j) => j.status === "DONE");
        const active = plans.find((j) => j.status === "RUNNING" || j.status === "QUEUED");
        if (active) { watch(active.id); return; }
        // A run that failed after the last good plan is not silently forgotten on reload.
        const newest = plans[0];
        if (newest && newest !== last && ["FAILED", "TIMEOUT", "CANCELLED", "ABANDONED"].includes(newest.status)) {
          setLastRunFailed(
            newest.status === "TIMEOUT"
              ? "Your most recent run did not finish inside the time it is given. Try a smaller selection of products."
              : newest.status === "CANCELLED"
                ? "Your most recent run was cancelled."
                : newest.status === "ABANDONED"
                  ? "Your most recent run was interrupted when the service restarted. Nothing was changed; run it again."
                  : "Your most recent run stopped without producing a plan.",
          );
        } else {
          setLastRunFailed(null);
        }
        if (!last || !live) return;
        const detail = await readPlanJob(last.id);
        if (!live || !detail.report) return;
        setReport(detail.report);
        setPlanJobId(last.id);
        setComputedAt(detail.finished_at ? new Date(detail.finished_at) : null);
        setScope(scopeOf(detail.report, state.request));
        setPlanPhase("ready");
      } catch {
        // no job history is simply no plan yet
      }
    })();

    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session.status, session.workspace?.id, tick]);

  const watch = (jobId: string) => {
    if (poll.current) window.clearInterval(poll.current);
    setPlanPhase("queued");
    setPlanError(null);
    const check = async () => {
      try {
        const detail = await readPlanJob(jobId);
        if (!alive.current) return;
        if (detail.status === "RUNNING") { setPlanPhase("running"); setQueueAhead(null); }
        if (detail.status === "QUEUED") { setPlanPhase("queued"); setQueueAhead(queueAheadOf(detail)); }
        if (abandoned(detail)) {
          if (poll.current) window.clearInterval(poll.current);
          poll.current = null;
          setPlanPhase("failed");
          setPlanError(ABANDONED_MESSAGE);
          return;
        }
        if (["DONE", "FAILED", "TIMEOUT", "CANCELLED", "ABANDONED"].includes(detail.status)) {
          if (poll.current) window.clearInterval(poll.current);
          poll.current = null;
          if (detail.status === "DONE" && detail.report) {
            setReport(detail.report);
            setPlanJobId(jobId);
            setComputedAt(detail.finished_at ? new Date(detail.finished_at) : new Date());
            setPlanPhase("ready");
            // An earlier failure is history once a later run has finished; leaving the notice up
            // would tell an operator their most recent run failed while showing its result.
            setLastRunFailed(null);
          } else {
            setPlanPhase("failed");
            setPlanError(
              detail.status === "TIMEOUT"
                ? "The run did not finish inside the time it is given. Try a smaller selection of products."
                : detail.status === "ABANDONED"
                  ? "The run was interrupted when the service restarted. Nothing was changed; run it again."
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
      phase, planPhase, queueAhead, notReady, error, planError, degraded,
      request, build, report, directory, decisions, summary, network,
      index: network ? buildIndex(network) : null,
      scope, readScope, lastRunFailed, computedAt, planJobId, run,
      refresh: () => setTick((t) => t + 1),
    };
  }, [phase, planPhase, queueAhead, notReady, error, planError, degraded, request, build, report, directory, scope, readScope, lastRunFailed, computedAt, planJobId, run, session.workspace]);

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
