/**
 * The canonical ZAAD endpoints, and only those.
 *
 * Every product surface plans through `/api/zaad/network/*` — the released P1..P5 + P4B
 * engine. The superseded `/fmcg` planning modes are not called from anywhere in the product:
 * they answer 410 in production (`ZAAD_LEGACY_PLANNERS=0`).
 */
import { apiFetch } from "@/lib/api";
import type { DirectoryResponse, WorkspacePlanResponse, WorkspaceRequestResponse, ZaadReport, ZaadRequest } from "./types";

/** Every released phase the workspace can declare. Absent declarations simply return nothing. */
export interface PlanOptions {
  horizon?: number;
  serviceTarget?: number;
  maxSolveSeconds?: number;
  /** P2 multi-location network: locations, lanes and transfers from the vault. */
  network?: boolean;
  /** P3 sourcing portfolio. */
  sourcing?: boolean;
  /** P4 adaptive recourse. */
  recourse?: boolean;
  /** P5 customer allocation. */
  atp?: boolean;
  /** P4B open-PO commitment intervention. */
  commitments?: boolean;
}

/**
 * Ask for everything the workspace has declared. A phase whose tables are empty contributes
 * nothing to the report, so asking is free and the product never has to know in advance which
 * phases a given operator has set up.
 */
export const ALL_PHASES: PlanOptions = { network: true, sourcing: true, recourse: true, atp: true, commitments: true };

function query(options: PlanOptions, extra: Record<string, string> = {}): string {
  const q = new URLSearchParams({
    horizon: String(options.horizon ?? 12),
    service_target: String(options.serviceTarget ?? 0.95),
    max_solve_seconds: String(options.maxSolveSeconds ?? 15),
    network: String(Boolean(options.network)),
    sourcing: String(Boolean(options.sourcing)),
    recourse: String(Boolean(options.recourse)),
    atp: String(Boolean(options.atp)),
    commitments: String(Boolean(options.commitments)),
    ...extra,
  });
  return q.toString();
}

/** The workspace's current state as the optimizer sees it. No plan is run. */
export function fetchWorkspaceState(options: PlanOptions = ALL_PHASES): Promise<WorkspaceRequestResponse> {
  return apiFetch<WorkspaceRequestResponse>(`/api/zaad/network/request/from-workspace?${query(options)}`);
}

/** Plan the workspace and return the full network report. Approval always stays with the operator. */
export function fetchWorkspacePlan(options: PlanOptions = ALL_PHASES): Promise<WorkspacePlanResponse> {
  return apiFetch<WorkspacePlanResponse>(`/api/zaad/network/plan/from-workspace?${query(options, { shape: "network" })}`, { method: "POST" });
}

/** Declared supplier and location master data the compact request does not carry. Read-only. */
export function fetchDirectory(): Promise<DirectoryResponse> {
  return apiFetch<DirectoryResponse>("/api/zaad/network/directory");
}

/**
 * Record a plan for human review and return its id. The canonical shadow endpoint takes a
 * canonical request body; the product records the workspace's own plan through it so that an
 * approval is anchored to an information set, exactly as the engineering path does.
 */
export function recordForReview(request: unknown): Promise<{ decision_id: string; report: unknown }> {
  return apiFetch<{ decision_id: string; report: unknown }>("/api/zaad/network/shadow", {
    method: "POST", body: JSON.stringify(request),
  });
}

export function submitReview(decisionId: string, body: { status: "APPROVED" | "REJECTED"; information_hash: string; version: number; reason: string }): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/api/zaad/network/shadow/${encodeURIComponent(decisionId)}/review`, {
    method: "POST", body: JSON.stringify(body),
  });
}

// ── Asynchronous planning ────────────────────────────────────────────────────
//
// A real solve takes minutes, not milliseconds: a bounded eight-product network run measured
// ~108 s on a developer machine. Holding an HTTP request open for that is not a product, so the
// released jobs path carries every plan — it reports QUEUED / RUNNING honestly, survives a page
// reload, and keeps the last completed plan for the workspace.

export interface JobSummary {
  id: string;
  /** ABANDONED: the service that owned the run stopped before it finished (a restart). */
  status: "QUEUED" | "RUNNING" | "DONE" | "FAILED" | "TIMEOUT" | "CANCELLED" | "ABANDONED";
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  engine_version: string;
  /** What the job was for; a workspace plan is WORKSPACE_PLAN, an evaluation's runs are PROPOSAL_*. */
  purpose?: string;
  reference?: string | null;
}

export interface JobDetail extends JobSummary {
  report: ZaadReport | null;
  error: string | null;
  timeout_s: number;
}

/** The workspace's own plans. An evaluation's runs carry another purpose and are never listed here. */
export function listPlanJobs(): Promise<{ jobs: JobSummary[] }> {
  return apiFetch<{ jobs: JobSummary[] }>("/api/zaad/network/jobs?purpose=WORKSPACE_PLAN");
}

export function readPlanJob(id: string): Promise<JobDetail> {
  return apiFetch<JobDetail>(`/api/zaad/network/jobs/${encodeURIComponent(id)}`);
}

export function submitPlanJob(request: ZaadRequest): Promise<{ job_id: string; status: string; timeout_s: number }> {
  return apiFetch<{ job_id: string; status: string; timeout_s: number }>("/api/zaad/network/jobs", {
    method: "POST", body: JSON.stringify(request),
  });
}

export function cancelPlanJob(id: string): Promise<unknown> {
  return apiFetch(`/api/zaad/network/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
}

/** Read the workspace for a named subset of products. */
export function fetchWorkspaceStateFor(skus: string[], options: PlanOptions = ALL_PHASES): Promise<WorkspaceRequestResponse> {
  return apiFetch<WorkspaceRequestResponse>(
    `/api/zaad/network/request/from-workspace?${query(options, { skus: skus.join(",") })}`,
  );
}
