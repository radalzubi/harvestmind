"use client";

/**
 * The diagnostic while it runs: an indeterminate animated bar (never a fake percentage), the real
 * stage the backend is in, the elapsed clock, the queue position when known, and explicit terminal
 * states with a reference id and a retry path. Everything shown comes from `viewOf`.
 */
import { useEffect, useState } from "react";
import { AlertTriangle, Check, RefreshCw, XCircle } from "lucide-react";
import type { Job } from "@/lib/api";
import { formatElapsed, viewOf } from "@/lib/diagnostic/lifecycle";
import { Tbtn } from "@/components/ui";

export function DiagnosticRun({ job, connectionLost, onCancel, onRetry, cancelling }: {
  job: Job | null; connectionLost: boolean; onCancel: () => void; onRetry: () => void; cancelling?: boolean;
}) {
  const [now, setNow] = useState(() => Date.now());
  const live = job != null && (job.status === "queued" || job.status === "running");
  useEffect(() => {
    if (!live) return;
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, [live]);
  const v = viewOf(job, now, connectionLost);
  if (v.kind === "idle") return null;

  if (v.live) {
    return (
      <div className="diag-run" role="status" aria-live="polite" aria-busy="true">
        <div className="diag-run-title">{v.title}</div>
        <div className="diag-bar" aria-hidden="true"><div className="diag-bar-fill" /></div>
        <div className="diag-run-detail">{v.detail ?? "Working…"}</div>
        <div className="diag-run-meta">
          <span>Elapsed time: <b style={{ fontVariantNumeric: "tabular-nums" }}>{formatElapsed(v.elapsedS)}</b></span>
          {v.queuePosition != null && <span>Queue position: <b>{v.queuePosition}</b></span>}
          {v.connectionLost && <span className="diag-run-lost"><AlertTriangle size={13} /> Connection interrupted; the run continues and we keep checking</span>}
        </div>
        {v.stages.length > 0 && (
          <ol className="diag-stages" aria-label="Diagnostic stages">
            {v.stages.map((s, i) => {
              const state = i < v.stageIndex ? "done" : i === v.stageIndex ? "current" : "pending";
              return (
                <li key={s.key} className={`diag-stage ${state}`} aria-current={state === "current" ? "step" : undefined}>
                  <span className="diag-stage-mark">{state === "done" ? <Check size={12} /> : state === "current" ? <span className="diag-stage-pulse" /> : <span className="diag-stage-dot" />}</span>
                  <span>{s.label}</span>
                </li>
              );
            })}
          </ol>
        )}
        <div className="diag-run-actions">
          {v.canCancel && <Tbtn variant="ghost" onClick={onCancel} pending={cancelling}>Cancel</Tbtn>}
          <span className="diag-run-note">This page can be refreshed or closed; the run continues and reconnects. Reference {v.reference}.</span>
        </div>
      </div>
    );
  }

  if (v.kind === "done") return null;   // the result view takes over
  const tone = v.kind === "cancelled" ? "neutral" : "bad";
  return (
    <div className={`diag-run diag-run-terminal ${tone}`} role="alert">
      <div className="diag-run-title">{v.kind === "cancelled" ? <XCircle size={16} /> : <AlertTriangle size={16} />} {v.title}</div>
      <p className="diag-run-detail">{v.message}</p>
      <div className="diag-run-actions">
        {v.canRetry && <Tbtn variant="primary" icon={<RefreshCw size={13} />} onClick={onRetry}>Run the diagnostic again</Tbtn>}
        <span className="diag-run-note">Reference {v.reference}{v.kind !== "cancelled" ? " — quote it if you contact ZAAD." : ""}</span>
      </div>
    </div>
  );
}
