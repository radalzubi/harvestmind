/**
 * The diagnostic run as the person sees it: a pure view of a job plus a poller that reconnects,
 * survives interrupted polls, never starts duplicate work, and stops on a terminal state.
 *
 * Nothing here invents progress. The bar is indeterminate; the only facts shown are the backend's
 * status, its real stage, the queue position when known, and the clock.
 */
import type { Job, JobStage, JobStatus } from "@/lib/api";

export type RunKind = "idle" | "queued" | "running" | "reporting" | "done" | "failed" | "timed_out" | "cancelled";

export interface RunView {
  kind: RunKind;
  /** the animated indicator is visible */
  live: boolean;
  title: string;
  /** what is happening right now, in the backend's own words */
  detail: string | null;
  /** seconds since the job was created (queued) or started (running) */
  elapsedS: number | null;
  stages: JobStage[];
  /** index into `stages` of the current real stage, -1 when none reported yet */
  stageIndex: number;
  queuePosition: number | null;
  /** terminal message for failed / timed out / cancelled */
  message: string | null;
  reference: string | null;
  canCancel: boolean;
  canRetry: boolean;
  /** the polling connection has been failing; the run may still be alive */
  connectionLost: boolean;
}

export const TERMINAL: ReadonlySet<JobStatus> = new Set(["done", "failed", "timed_out", "cancelled"]);

export function isTerminal(status: JobStatus | null | undefined): boolean {
  return !!status && TERMINAL.has(status);
}

export function formatElapsed(seconds: number | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return "";
  const s = Math.floor(seconds);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m ${String(r).padStart(2, "0")}s`;
  if (m > 0) return `${m}m ${String(r).padStart(2, "0")}s`;
  return `${r}s`;
}

function parseIso(s: string | null | undefined): number | null {
  if (!s) return null;
  const t = Date.parse(s);
  return Number.isFinite(t) ? t : null;
}

/** Derive what to show from a job and the clock. Pure. */
export function viewOf(job: Job | null, nowMs: number, connectionLost = false): RunView {
  const stages = job?.stages ?? [];
  const idle: RunView = { kind: "idle", live: false, title: "", detail: null, elapsedS: null, stages, stageIndex: -1, queuePosition: null,
    message: null, reference: null, canCancel: false, canRetry: false, connectionLost: false };
  if (!job) return idle;
  const stageIndex = job.stage ? stages.findIndex((s) => s.key === job.stage) : -1;
  const started = parseIso(job.started_at) ?? parseIso(job.created_at);
  const created = parseIso(job.created_at);
  const finished = parseIso(job.finished_at);
  const base = { stages, stageIndex, reference: job.reference ?? job.id, connectionLost };
  switch (job.status) {
    case "queued": {
      const pos = job.queue_position ?? null;
      const machine = job.progress?.toLowerCase().includes("machine");
      return { ...base, kind: "queued", live: true, title: "Waiting to start",
        detail: pos != null ? (pos === 1 ? "You are next in line" : `${pos - 1} diagnostic${pos - 1 === 1 ? "" : "s"} ahead of you`) : machine ? "Starting a dedicated solver machine" : "Waiting for a solver slot",
        elapsedS: created != null ? Math.max(0, (nowMs - created) / 1000) : null, queuePosition: pos, message: null, canCancel: true, canRetry: false };
    }
    case "running": {
      const reporting = job.stage === "reporting";
      return { ...base, kind: reporting ? "reporting" : "running", live: true, title: reporting ? "Building your report" : "Running your diagnostic",
        detail: job.progress || (stageIndex >= 0 ? stages[stageIndex].label : null),
        elapsedS: started != null ? Math.max(0, (nowMs - started) / 1000) : null, queuePosition: null, message: null, canCancel: true, canRetry: false };
    }
    case "done":
      return { ...base, kind: "done", live: false, title: "Diagnostic ready", detail: null,
        elapsedS: started != null && finished != null ? Math.max(0, (finished - started) / 1000) : null, queuePosition: null, message: null, canCancel: false, canRetry: false };
    case "failed":
      return { ...base, kind: "failed", live: false, title: "The diagnostic could not complete", detail: null, elapsedS: null, queuePosition: null,
        message: job.error || "An error occurred.", canCancel: false, canRetry: true };
    case "timed_out":
      return { ...base, kind: "timed_out", live: false, title: "The diagnostic ran out of time", detail: null, elapsedS: null, queuePosition: null,
        message: job.error || "The run exceeded its time limit.", canCancel: false, canRetry: true };
    case "cancelled":
      return { ...base, kind: "cancelled", live: false, title: "Diagnostic cancelled", detail: null, elapsedS: null, queuePosition: null,
        message: "You cancelled this run. Nothing was changed.", canCancel: false, canRetry: true };
    default:
      return idle;
  }
}

// ── the poller ──

export interface PollerDeps {
  fetchJob: (id: string) => Promise<Job>;
  start: () => Promise<Job>;
  latest: () => Promise<Job | null>;
  cancel: (id: string) => Promise<Job>;
  setTimer: (fn: () => void, ms: number) => unknown;
  clearTimer: (handle: unknown) => void;
  /** polling interval while active (ms) */
  intervalMs?: number;
  /** consecutive failed polls before the view reports the connection as lost */
  lostAfter?: number;
  /** longest back-off between polls after failures (ms) */
  maxBackoffMs?: number;
}

export interface PollerState {
  job: Job | null;
  connectionLost: boolean;
  /** a start request is in flight; a second press is ignored */
  starting: boolean;
}

/**
 * Drives one diagnostic: reconnects to the workspace's newest job on mount, starts a run at most
 * once per press, polls on a fixed interval with back-off on errors, and stops at a terminal state.
 * Every side effect is injected so the behaviour is unit-tested without a browser.
 */
export class DiagnosticPoller {
  private handle: unknown = null;
  private failures = 0;
  private stopped = false;
  state: PollerState = { job: null, connectionLost: false, starting: false };

  constructor(private readonly deps: PollerDeps, private readonly onChange: (s: PollerState) => void) {}

  private emit(patch: Partial<PollerState>): void {
    this.state = { ...this.state, ...patch };
    this.onChange(this.state);
  }

  /** Reconnect: adopt the newest job; keep polling it when it is still active. */
  async reconnect(): Promise<void> {
    try {
      const j = await this.deps.latest();
      if (this.stopped) return;
      this.emit({ job: j, connectionLost: false });
      if (j && !isTerminal(j.status)) this.schedule(0);
    } catch {
      /* no job to reconnect to, or the request failed: the person can start one */
    }
  }

  /** Start a run. Idempotent while a start is in flight or a run is active. */
  async start(): Promise<Job | null> {
    if (this.state.starting) return this.state.job;
    if (this.state.job && !isTerminal(this.state.job.status)) return this.state.job;
    this.emit({ starting: true });
    try {
      const j = await this.deps.start();
      if (this.stopped) return j;
      this.failures = 0;
      this.emit({ job: j, connectionLost: false, starting: false });
      if (!isTerminal(j.status)) this.schedule(this.interval());
      return j;
    } catch (e) {
      this.emit({ starting: false });
      throw e;
    }
  }

  async cancel(): Promise<void> {
    const j = this.state.job;
    if (!j || isTerminal(j.status)) return;
    const c = await this.deps.cancel(j.id);
    if (this.stopped) return;
    this.emit({ job: c });
    if (isTerminal(c.status)) this.clear();
  }

  /** One poll. Exposed for tests; the timer calls it. */
  async tick(): Promise<void> {
    const j = this.state.job;
    if (!j || this.stopped) return;
    try {
      const next = await this.deps.fetchJob(j.id);
      if (this.stopped) return;
      this.failures = 0;
      this.emit({ job: next, connectionLost: false });
      if (isTerminal(next.status)) { this.clear(); return; }
      this.schedule(this.interval());
    } catch {
      if (this.stopped) return;
      this.failures += 1;
      const lost = this.failures >= (this.deps.lostAfter ?? 3);
      if (lost !== this.state.connectionLost) this.emit({ connectionLost: lost });
      // keep trying with back-off; the run is still alive on the server
      this.schedule(Math.min(this.interval() * 2 ** Math.min(this.failures, 5), this.deps.maxBackoffMs ?? 30000));
    }
  }

  stop(): void {
    this.stopped = true;
    this.clear();
  }

  private interval(): number { return this.deps.intervalMs ?? 3000; }

  private schedule(ms: number): void {
    this.clear();
    this.handle = this.deps.setTimer(() => { this.handle = null; void this.tick(); }, ms);
  }

  private clear(): void {
    if (this.handle != null) { this.deps.clearTimer(this.handle); this.handle = null; }
  }
}
