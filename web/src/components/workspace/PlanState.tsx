"use client";

/**
 * Running ZAAD, and saying honestly where the run has got to.
 *
 * A plan is a minutes-long solve, so it is a deliberate act with visible progress, not a spinner
 * on page load. The only states shown are the ones the server actually reports — queued, running,
 * done, failed — with no invented percentage.
 *
 * When a run covers fewer products than the workspace holds, that is stated wherever the plan is,
 * in the same words, with the rule that chose them. A scoped plan is never presented as if it
 * covered the whole catalogue.
 */
import { useState } from "react";
import { Play, RotateCw } from "lucide-react";
import { DEFAULT_SCOPE, SCOPE_CHOICES, useWorkspaceData } from "@/lib/zaad/workspace-data";
import { Button, ButtonLink, EmptyState, ErrorState, Notice } from "./ui";

export function ScopeNotice() {
  const { scope } = useWorkspaceData();
  if (!scope) return null;
  return (
    <Notice tone="info">
      <strong>This plan covers {scope.skus.length} of your {scope.total} products</strong> — {scope.rule}.
      Anything outside that selection was not looked at. Run again over more products to widen it.
    </Notice>
  );
}

/** The run control, with the size of the run visible before it starts. */
export function RunPlan({ label = "Run ZAAD", role = "primary" }: { label?: string; role?: "primary" | "secondary" | "tertiary" }) {
  const { run, request, planPhase } = useWorkspaceData();
  const [size, setSize] = useState<number | "all">(DEFAULT_SCOPE);
  const total = request?.skus.length ?? 0;
  const busy = planPhase === "queued" || planPhase === "running";
  const choices: Array<number | "all"> = [...SCOPE_CHOICES.filter((c) => c < total), "all"];

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      {total > DEFAULT_SCOPE && (
        <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12.5, color: "var(--ink-600)" }}>
          <span>Cover</span>
          <select
            className="zinput" style={{ width: "auto", padding: "6px 8px", fontSize: 12.5 }}
            value={String(size)} onChange={(e) => setSize(e.target.value === "all" ? "all" : Number(e.target.value))}
            aria-label="How many products this run covers"
          >
            {choices.map((c) => (
              <option key={String(c)} value={String(c)}>
                {c === "all" ? `all ${total} products` : `${c} products`}
              </option>
            ))}
          </select>
        </label>
      )}
      <Button role={role} icon={busy ? undefined : <Play size={14} aria-hidden />} pending={busy} onClick={() => run(size)}>
        {busy ? "Running…" : label}
      </Button>
      {size === "all" && total > 50 && (
        <span style={{ fontSize: 12, color: "var(--ink-500)" }}>
          All {total} products may not finish inside the time a run is given.
        </span>
      )}
    </div>
  );
}

/**
 * What to show when there is no plan to show. Returns null once a plan is in hand, so a page can
 * render this above its content and let it disappear.
 */
export function PlanGate({ children }: { children?: React.ReactNode }) {
  const { planPhase, planError, report, run } = useWorkspaceData();

  if (planPhase === "ready" && report) return <>{children}</>;

  if (planPhase === "queued" || planPhase === "running") {
    return (
      <div className="state-box">
        <p className="phase" style={{ justifyContent: "center" }} aria-live="polite">
          <span className="spin" aria-hidden />
          {planPhase === "queued" ? "Your run is queued…" : "Comparing every option against your current plan…"}
        </p>
        <p style={{ marginTop: 12 }}>
          A full comparison takes a few minutes. You can leave this page — the run continues and the
          result will be here when you come back. The network and your data are ready now.
        </p>
      </div>
    );
  }

  if (planPhase === "failed") {
    const timedOut = /time/i.test(planError ?? "");
    const refused = /invalid|declares|does not carry|must|cannot/i.test(planError ?? "");
    return (
      <ErrorState
        title="The run did not produce a plan"
        affects="Your data is untouched and nothing was sent anywhere."
        whatToDo={
          timedOut ? "Run it again over fewer products so it finishes inside the time a run is given."
            : refused ? "Something in your declared data does not line up. The diagnostics below name it exactly, and Data is where it is fixed."
            : "Run it again. If it fails a second time, the diagnostics below tell support where it stopped."
        }
        detail={planError ?? undefined}
        actions={<>
          <Button role="primary" icon={<RotateCw size={14} aria-hidden />} onClick={() => run()}>Run again</Button>
          {refused && <ButtonLink href="/data">Open Data</ButtonLink>}
        </>}
      />
    );
  }

  return (
    <EmptyState title="No plan has been computed yet" actions={<RunPlan />}>
      ZAAD reads your workspace as soon as you open it — your network and your data are ready below.
      Comparing your current plan against every alternative is a solve that takes a few minutes, so
      it runs when you ask for it.
    </EmptyState>
  );
}
