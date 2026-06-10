"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import {
  Card,
  CardBody,
  CardHead,
  EmptyState,
  InfoBanner,
  KPI,
  KPIRow,
  PageError,
  PageHeader,
  PageLoading,
  Tbtn,
} from "@/components/ui";
import { getDiagnosticSummary, getRoiCards, fmtUSD, fmtPct, fmt, type DiagnosticSummary, type RoiCards } from "@/lib/api";

export default function OverviewPage() {
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [roi, setRoi] = useState<RoiCards | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // measured card loads independently; its absence must never block the page
    getRoiCards().then(setRoi).catch(() => setRoi(null));
  }, []);

  if (loading) return <PageLoading message="Loading diagnostic summary…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const totalLoss = data.total_waste_loss_usd + data.total_shortage_loss_usd;
  const hasData = Object.values(data.row_counts).some((v) => v > 0);

  return (
    <div className="page">
      <PageHeader
        title="Overview"
        sub={`Diagnostic as of ${new Date(data.as_of).toLocaleDateString()} · ${data.period_days}-day window · ${data.partner_name}`}
        actions={
          <a href="http://localhost:8000/reports/diagnostic" target="_blank" rel="noreferrer">
            <Tbtn variant="primary" icon={<ExternalLink size={13} strokeWidth={1.6} />}>
              View Report
            </Tbtn>
          </a>
        }
      />

      {!hasData && (
        <EmptyState
          title="No operator data loaded yet"
          body="Upload your CSV files to generate a diagnostic. HarvestMind needs product, delivery, inventory, order, and waste data to calculate waste loss, shortage risk, and available-to-promise."
          action={
            <Link href="/upload">
              <Tbtn variant="primary">Upload your data or load sample dataset →</Tbtn>
            </Link>
          }
        />
      )}

      {hasData && totalLoss > 0 && (
        <InfoBanner kind="danger" title="⚠ Addressable loss detected:">
          {fmtUSD(totalLoss)} in waste + shortage losses identified across {data.period_days} days.
          {data.savings.estimated_annual_savings_usd > 0 &&
            ` Opportunity ceiling (assumed 15–30% benchmark): up to ${fmtUSD(data.savings.estimated_annual_savings_usd)}/yr.`}
        </InfoBanner>
      )}

      <KPIRow>
        <KPI
          label="Waste Loss"
          value={fmtUSD(data.waste.total_usd)}
          deltaDir={data.waste.total_usd > 0 ? "down" : "flat"}
          sub={`${fmt(data.waste.n_rows)} waste events`}
        />
        <KPI
          label="Shortage Loss"
          value={fmtUSD(data.shortage.total_usd)}
          deltaDir={data.shortage.total_usd > 0 ? "down" : "flat"}
          sub={`${fmt(data.shortage.n_at_risk)} at-risk order lines`}
        />
        <KPI
          label="Risky Suppliers"
          value={fmt(data.n_risky_suppliers)}
          deltaDir={data.n_risky_suppliers > 0 ? "down" : "flat"}
          sub={`of ${fmt(data.supplier.suppliers.length)} tracked`}
        />
        <KPI
          label="Traceability"
          value={fmtPct(data.traceability_completeness_pct)}
          deltaDir={data.traceability_completeness_pct >= 0.95 ? "up" : "down"}
          sub="FSMA-204 lot completeness"
        />
      </KPIRow>

      {hasData && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 20 }}>
          {/* Top risks */}
          <Card>
            <CardHead title="Top Loss Drivers" sub="Largest addressable losses this period" />
            <CardBody tight>
              {data.top_risks.length === 0 ? (
                <div style={{ padding: "24px 12px", color: "var(--muted)", fontSize: 12, textAlign: "center" }}>
                  No loss data found. Upload waste and order history to see top risks.
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Item</th>
                      <th className="r">Loss</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_risks.map((r, i) => (
                      <tr key={i}>
                        <td style={{ fontSize: 11, color: "var(--muted)" }}>{r.category}</td>
                        <td style={{ fontSize: 12 }}>{r.item}</td>
                        <td className="r" style={{ color: "var(--danger)", fontWeight: 600, fontSize: 12 }}>
                          {fmtUSD(r.loss_usd)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>

          {/* Savings opportunity */}
          <Card>
            <CardHead title="Opportunity Ceiling (Assumed)" sub="Annualized addressable loss × assumed 15–30% benchmark — not a measured result" />
            <CardBody>
              <div style={{ display: "flex", flexDirection: "column", gap: 14, padding: "4px 0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>Waste loss ({data.period_days}-day window)</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--danger)" }}>{fmtUSD(data.savings.waste_loss_usd)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>Shortage loss ({data.period_days}-day window)</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "var(--danger)" }}>{fmtUSD(data.savings.shortage_loss_usd)}</span>
                </div>
                <div style={{ height: 1, background: "var(--border)" }} />
                {data.savings.addressable_loss_usd_period !== undefined && (
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 12, color: "var(--muted)" }}>
                      Period addressable total
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 600 }}>
                      {fmtUSD(data.savings.addressable_loss_usd_period)}
                    </span>
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>
                    Annualized (×{(data.savings.annualization_factor ?? 1).toFixed(2)})
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{fmtUSD(data.savings.addressable_loss_usd)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 4 }}>
                  <span style={{ fontSize: 12, color: "var(--muted)" }}>
                    Opportunity ceiling
                    <br />
                    <span style={{ fontSize: 10 }}>
                      (assumed {Math.round((data.savings.reduction_pct_low ?? 0.15) * 100)}–{Math.round((data.savings.reduction_pct_high ?? 0.30) * 100)}% reduction benchmark)
                    </span>
                  </span>
                  <span style={{ fontSize: 16, fontWeight: 700, color: "var(--accent)", textAlign: "right" }}>
                    {data.savings.estimated_annual_savings_usd_low !== undefined &&
                     data.savings.estimated_annual_savings_usd_high !== undefined ? (
                      <>
                        {fmtUSD(data.savings.estimated_annual_savings_usd_low)}
                        <span style={{ fontWeight: 400, color: "var(--muted)" }}> – </span>
                        {fmtUSD(data.savings.estimated_annual_savings_usd_high)}
                      </>
                    ) : (
                      fmtUSD(data.savings.estimated_annual_savings_usd)
                    )}
                  </span>
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      )}

      {/* Measured backtest card — separate from the assumed ceiling, never summed */}
      {hasData && roi && (
        <Card style={{ marginTop: 16 }}>
          <CardHead
            title="Measured Backtest Result"
            sub="From a rolling-origin backtest on your own history — a different question than the assumed ceiling above; the two are never combined"
          />
          <CardBody>
            {roi.measured_card.status === "measured" ? (
              <div style={{ display: "flex", gap: 32, alignItems: "baseline", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: roi.measured_card.gate_passed ? "var(--accent)" : "var(--danger)" }}>
                    {roi.measured_card.sp_vs_lp_edge_pct}%
                  </div>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    optimizer vs deterministic plan · wins {roi.measured_card.wins}/{roi.measured_card.n_origins} · t={roi.measured_card.paired_t}
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "var(--muted)", maxWidth: 520 }}>
                  {roi.measured_card.verdict}
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "var(--muted)" }}>
                Not yet measured — {roi.measured_card.note}
                {roi.measured_card.weeks_available != null &&
                  ` (${roi.measured_card.weeks_available}/${roi.measured_card.weeks_required} weeks of history available).`}
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Data loaded summary */}
      <Card style={{ marginTop: 16 }}>
        <CardHead title="Data Loaded" sub="Rows in each staging table" />
        <CardBody tight>
          <table className="data-table">
            <thead>
              <tr>
                <th>Table</th>
                <th className="r">Rows</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.row_counts).map(([table, count]) => (
                <tr key={table}>
                  <td style={{ fontFamily: "monospace", fontSize: 11 }}>{table}</td>
                  <td className="r">{fmt(count)}</td>
                  <td>
                    <span style={{ fontSize: 11, color: count > 0 ? "var(--accent)" : "var(--muted)" }}>
                      {count > 0 ? "✓ Loaded" : "— Empty"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
