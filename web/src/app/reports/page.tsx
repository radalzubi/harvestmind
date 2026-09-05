"use client";

import { useEffect, useState } from "react";
import { ExternalLink, FileText } from "lucide-react";
import {
  Badge,
  Card,
  CardBody,
  CardHead,
  KPI,
  KPIRow,
  PageHeader,
  Tbtn,
} from "@/components/ui";
import { getDiagnosticSummary, openDiagnosticReport, fmtUSD, fmtPct, type DiagnosticSummary } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function ReportsPage() {
  const toast = useToast();
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const hasData = data && Object.values(data.row_counts).some((v) => v > 0);
  const openReport = () => openDiagnosticReport()
    .catch((reason) => toast.push(`Could not open report: ${String(reason)}`));

  return (
    <div className="page">
      <PageHeader
        title="Reports"
        sub="Generate and export your FSMA-204 diagnostic report"
        actions={
          <Tbtn variant="primary" icon={<ExternalLink size={13} strokeWidth={1.6} />} onClick={openReport}>
            Open Diagnostic Report
          </Tbtn>
        }
      />

      {/* Report card */}
      <Card>
        <CardHead title="Diagnostic Report" sub="Full operator diagnostic — ready to share with your team" />
        <CardBody>
          <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 10,
              background: "var(--surface)",
              border: "1px solid var(--border)",
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
            }}>
              <FileText size={20} color="var(--accent)" strokeWidth={1.6} />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                Zaad Supply Diagnostic
                {data && (
                  <span style={{ marginLeft: 8 }}>
                    <Badge kind="low">{new Date(data.as_of).toLocaleDateString()}</Badge>
                  </span>
                )}
              </div>
              <div style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.6, marginBottom: 12 }}>
                12-section HTML report covering waste loss, shortage loss, supplier reliability,
                buyer fulfillment, inventory risk, traceability, ATP recommendations, and savings opportunity.
                Rendered live from your uploaded data — no static snapshots.
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Tbtn variant="primary" icon={<ExternalLink size={12} />} onClick={openReport}>
                  View in browser
                </Tbtn>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* Live summary preview */}
      {loading && (
        <div style={{ marginTop: 16, color: "var(--muted)", fontSize: 12, padding: 16 }}>Loading diagnostic summary…</div>
      )}
      {error && (
        <div style={{ marginTop: 16, color: "var(--danger)", fontSize: 12, padding: 16 }}>Could not load summary: {error}</div>
      )}
      {data && (
        <>
          <Card style={{ marginTop: 16 }}>
            <CardHead title="Report Preview" sub={`As of ${new Date(data.as_of).toLocaleString()} · ${data.period_days}-day window`} />
            <CardBody>
              <KPIRow>
                <KPI label="Waste Loss" value={fmtUSD(data.waste.total_usd)} deltaDir={data.waste.total_usd > 0 ? "down" : "flat"} />
                <KPI label="Shortage Loss" value={fmtUSD(data.shortage.total_usd)} deltaDir={data.shortage.total_usd > 0 ? "down" : "flat"} />
                <KPI label="Traceability" value={fmtPct(data.traceability_completeness_pct)} deltaDir={data.traceability_completeness_pct >= 0.95 ? "up" : "down"} />
                <KPI label="Est. Annual Savings" value={fmtUSD(data.savings.estimated_annual_savings_usd)} deltaDir="up" />
              </KPIRow>
            </CardBody>
          </Card>

          {!hasData && (
            <div style={{ marginTop: 16, padding: "14px 18px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, color: "var(--muted)" }}>
              No data loaded yet. Upload CSV files via the{" "}
              <a href="/upload" style={{ color: "var(--accent)", textDecoration: "underline" }}>
                Data Upload
              </a>{" "}
              page to generate a populated diagnostic report.
            </div>
          )}
        </>
      )}

      <style>{`.r { text-align: right; }`}</style>
    </div>
  );
}
