"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardBody,
  CardHead,
  EmptyState,
  KPI,
  KPIRow,
  PageError,
  PageHeader,
  PageLoading,
  RiskBadge,
  Tbtn,
} from "@/components/ui";
import { getDiagnosticSummary, fmt, type DiagnosticSummary } from "@/lib/api";

export default function RecsPage() {
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Computing recommendations from your data…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const recs = data.recommendations ?? [];
  const nHigh = recs.filter((r) => r.risk_level === "High").length;
  const nMedium = recs.filter((r) => r.risk_level === "Medium").length;

  return (
    <div className="page">
      <PageHeader
        title="Recommendations"
        sub="Per-product commitment guidance computed live from your ATP, supplier distributions, and buyer history"
      />

      {recs.length === 0 ? (
        <EmptyState
          title="No data loaded yet"
          body="Upload inventory, supplier, and order history (or load the sample dataset) to generate commitment recommendations."
          action={<Link href="/upload"><Tbtn variant="primary">Upload data</Tbtn></Link>}
        />
      ) : (
        <>
          <KPIRow>
            <KPI label="Products Assessed" value={fmt(recs.length)} />
            <KPI
              label="High Risk"
              value={fmt(nHigh)}
              deltaDir={nHigh > 0 ? "down" : "flat"}
            />
            <KPI label="Medium Risk" value={fmt(nMedium)} />
            <KPI
              label="Safe to Commit (total)"
              value={`${fmt(recs.reduce((s, r) => s + (r.safe_commit_kg ?? 0), 0))} kg`}
              sub="after holdbacks"
            />
          </KPIRow>

          <Card style={{ marginTop: 16 }}>
            <CardHead
              title="Commitment Recommendations"
              sub="Action · reason · risk — holdbacks sized from the shrunk supplier distributions, not raw averages"
            />
            <CardBody tight>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th className="r">ATP kg</th>
                    <th className="r">Safe Commit kg</th>
                    <th className="r">Holdback kg</th>
                    <th>Risk</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {recs.map((r) => (
                    <tr key={r.product_name}>
                      <td style={{ fontWeight: 600 }}>{r.product_name}</td>
                      <td className="r">{fmt(r.atp_kg)}</td>
                      <td className="r" style={{ fontWeight: 600, color: "var(--accent)" }}>
                        {fmt(r.safe_commit_kg)}
                      </td>
                      <td className="r" style={{ color: r.holdback_kg > 0 ? "var(--warn)" : "var(--muted)" }}>
                        {fmt(r.holdback_kg)}
                      </td>
                      <td><RiskBadge level={r.risk_level} /></td>
                      <td style={{ fontSize: 11, color: "var(--muted)", maxWidth: 420 }}>
                        {r.recommendation_text}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
        </>
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
