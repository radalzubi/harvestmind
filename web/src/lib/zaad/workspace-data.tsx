"use client";

/**
 * One read of the workspace, shared by Home, Decisions and Network.
 *
 * Planning is a real solve, so it happens once per session unless something asks for it again;
 * the three surfaces then read the same report and can never disagree about what ZAAD recommends.
 * The two phases below are the two calls actually made — no invented progress.
 */
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "@/lib/session";
import { ALL_PHASES, fetchDirectory, fetchWorkspacePlan, fetchWorkspaceState } from "./client";
import { buildDecisions, planSummary, type Decision, type PlanSummary } from "./decisions";
import type { DirectoryResponse, ZaadBuild, ZaadReport, ZaadRequest } from "./types";
import { buildCanonicalModel } from "@/lib/network/adapters/canonical";
import { buildIndex, type NetworkIndex } from "@/lib/network/graph";
import type { NetworkModel } from "@/lib/network/model";

export type Phase = "idle" | "reading" | "planning" | "ready" | "not-ready" | "error";

export interface WorkspaceData {
  phase: Phase;
  /** Set when the workspace cannot be planned yet — missing uploads, in the server's own words. */
  notReady: string | null;
  error: string | null;
  request: ZaadRequest | null;
  build: ZaadBuild | null;
  report: ZaadReport | null;
  directory: DirectoryResponse | null;
  decisions: Decision[];
  summary: PlanSummary | null;
  network: NetworkModel | null;
  index: NetworkIndex | null;
  /** When the plan in hand was computed, in this browser. */
  computedAt: Date | null;
  refresh: () => void;
}

const WorkspaceDataContext = createContext<WorkspaceData | null>(null);

function messageOf(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}

/** The server says `workspace_not_ready` with an operator-facing sentence; keep its words. */
function notReadyMessage(e: unknown): string | null {
  const text = messageOf(e);
  if (/workspace_not_ready/i.test(text) || /upload .* before planning/i.test(text) || /^Upload /i.test(text)) {
    return text.replace(/^\{?['"]?code['"]?:\s*['"]?workspace_not_ready['"]?,?\s*/i, "").replace(/^['"]?message['"]?:\s*/i, "").replace(/[{}'"]/g, "").trim();
  }
  return null;
}

export function WorkspaceDataProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const [phase, setPhase] = useState<Phase>("idle");
  const [notReady, setNotReady] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [request, setRequest] = useState<ZaadRequest | null>(null);
  const [build, setBuild] = useState<ZaadBuild | null>(null);
  const [report, setReport] = useState<ZaadReport | null>(null);
  const [directory, setDirectory] = useState<DirectoryResponse | null>(null);
  const [computedAt, setComputedAt] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);
  const inflight = useRef(false);

  useEffect(() => {
    if (session.status !== "authenticated") { setPhase("idle"); return; }
    if (inflight.current) return;
    let alive = true;
    inflight.current = true;
    setPhase("reading");
    setError(null);
    setNotReady(null);

    (async () => {
      let state;
      try {
        state = await fetchWorkspaceState(ALL_PHASES);
      } catch (e) {
        if (!alive) return;
        const missing = notReadyMessage(e);
        if (missing) { setNotReady(missing); setPhase("not-ready"); }
        else { setError(messageOf(e)); setPhase("error"); }
        return;
      }
      if (!alive) return;
      setRequest(state.request);
      setBuild(state.build);
      // The directory is a display convenience; a workspace without the optional supplier
      // upload still plans, so a failure here never stops the page.
      fetchDirectory().then((d) => { if (alive) setDirectory(d); }).catch(() => { if (alive) setDirectory(null); });

      setPhase("planning");
      try {
        const planned = await fetchWorkspacePlan(ALL_PHASES);
        if (!alive) return;
        setReport(planned.report);
        setBuild(planned.build ?? state.build);
        setComputedAt(new Date());
        setPhase("ready");
      } catch (e) {
        if (!alive) return;
        const missing = notReadyMessage(e);
        if (missing) { setNotReady(missing); setPhase("not-ready"); }
        else { setError(messageOf(e)); setPhase("error"); }
      }
    })().finally(() => { inflight.current = false; });

    return () => { alive = false; };
  }, [session.status, tick]);

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
      phase, notReady, error, request, build, report, directory, decisions, summary, network,
      index: network ? buildIndex(network) : null,
      computedAt,
      refresh: () => setTick((t) => t + 1),
    };
  }, [phase, notReady, error, request, build, report, directory, computedAt, session.workspace]);

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
