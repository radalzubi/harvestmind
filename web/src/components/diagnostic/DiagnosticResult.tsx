"use client";

/**
 * The diagnostic result as the start page shows it: the in-app report when the stored report is in
 * the format this build renders, and otherwise an honest note with the PDF of that run.
 *
 * Two lines of defence, because a result a person cannot open must never take the page with it
 * (incident 2026-10-03, see `lib/diagnostic/report-shape`):
 *  1. the shape check — a report stored in a layout this build does not render is not handed to the view;
 *  2. an error boundary — anything the check did not foresee is contained to this card.
 */
import { Component, type ReactNode } from "react";
import { Download } from "lucide-react";
import { Tbtn } from "@/components/ui";
import { reportRenderable } from "@/lib/diagnostic/report-shape";
import { DiagnosticReportView } from "./DiagnosticReport";

type Reason = "other-layout" | "render-failed";

/**
 * The wording claims only what is true for every stored report that lands here. It does not name a
 * report version (the version label did not change when the layout did, so it tells the two apart
 * for nobody), and it does not promise that running again changes the outcome (a sector whose
 * report is still built in the other layout gets the same note after a new run).
 */
export function ReportUnavailable({ reason, onDownload, downloading }: { reason: Reason; onDownload: () => void; downloading?: boolean }) {
  return (
    <div className="diag-report" role="status">
      <p style={{ margin: "0 0 10px" }}>
        {reason === "other-layout"
          ? "This result is stored in a report layout this page does not show. Nothing was lost: the full report of this run is available as a PDF."
          : "This result could not be displayed here. Nothing was lost: the full report of this run is available as a PDF."}
      </p>
      <Tbtn variant="primary" icon={<Download size={13} />} onClick={onDownload} pending={downloading}>Download the report (PDF)</Tbtn>
    </div>
  );
}

class ReportBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  componentDidCatch(error: unknown): void {
    // the error only — never the report, which is the workspace's data
    console.error("The diagnostic report could not be rendered.", error);
  }

  render(): ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

export function DiagnosticResult({ report, onDownload, downloading }: { report: unknown; onDownload: () => void; downloading?: boolean }) {
  if (!reportRenderable(report)) {
    return <ReportUnavailable reason="other-layout" onDownload={onDownload} downloading={downloading} />;
  }
  return (
    <ReportBoundary key={report.run_id} fallback={<ReportUnavailable reason="render-failed" onDownload={onDownload} downloading={downloading} />}>
      <DiagnosticReportView report={report} onDownload={onDownload} downloading={downloading} />
    </ReportBoundary>
  );
}
