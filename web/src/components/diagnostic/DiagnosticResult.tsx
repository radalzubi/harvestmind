"use client";

/**
 * The diagnostic result as the start page shows it: the in-app report when the stored report is in
 * the format this build renders, and otherwise an honest note with the PDF of that run.
 *
 * Two lines of defence, because a result a person cannot open must never take the page with it
 * (incident 2026-10-03, see `lib/diagnostic/report-shape`):
 *  1. the shape check — a report from a different report version is not handed to the view;
 *  2. an error boundary — anything the check did not foresee is contained to this card.
 */
import { Component, type ReactNode } from "react";
import { Download } from "lucide-react";
import { Tbtn } from "@/components/ui";
import { reportRenderable, reportVersion } from "@/lib/diagnostic/report-shape";
import { DiagnosticReportView } from "./DiagnosticReport";

type Reason = "different-version" | "render-failed";

export function ReportUnavailable({ reason, version, onDownload, downloading }: { reason: Reason; version: string | null; onDownload: () => void; downloading?: boolean }) {
  return (
    <div className="diag-report" role="status">
      <p style={{ margin: "0 0 10px" }}>
        {reason === "different-version"
          ? `This result was produced by a different version of the diagnostic${version ? ` (report version ${version})` : ""}, so it cannot be shown here in the current layout. Nothing was lost: the report of this run is still available as a PDF, and running the diagnostic again produces a report in the current format.`
          : "This result could not be displayed here. Nothing was lost: the report of this run is still available as a PDF."}
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
  const version = reportVersion(report);
  if (!reportRenderable(report)) {
    return <ReportUnavailable reason="different-version" version={version} onDownload={onDownload} downloading={downloading} />;
  }
  return (
    <ReportBoundary key={report.run_id} fallback={<ReportUnavailable reason="render-failed" version={version} onDownload={onDownload} downloading={downloading} />}>
      <DiagnosticReportView report={report} onDownload={onDownload} downloading={downloading} />
    </ReportBoundary>
  );
}
