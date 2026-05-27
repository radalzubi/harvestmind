"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardBody, CardHead, EmptyState, KPI, KPIRow, PageError, PageHeader, PageLoading, RiskBadge, Tbtn } from "@/components/ui";
import { getDiagnosticSummary, fmt, type DiagnosticSummary } from "@/lib/api";

export default function ATPPage() {
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Loading ATP data…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const { atp, recommendations } = data;
  const hasInventory = atp.products.length > 0;

  return (
    <div className="page">
      <PageHeader
        title="Available-to-Promise"
        sub="Usable inventory minus committed quantity, near-expiry, and expired stock."
      />

      <KPIRow>
        <KPI label="Products Tracked" value={fmt(atp.products.length)} />
        <KPI label="Risky Products" value={fmt(atp.n_risky)} sub="ATP ≤ 0 or >20% near expiry" />
        <KPI label="Total On Hand" value={fmt(atp.products.reduce((s, p) => s + p.total_on_hand_kg, 0), 0) + " kg"} />
        <KPI label="Near Expiry" value={fmt(atp.products.reduce((s, p) => s + p.near_expiry_kg, 0), 0) + " kg"} sub="≤ 3 days" />
      </KPIRow>

      <Card style={{ marginTop: 20 }}>
        <CardHead title="ATP by Product" />
        <CardBody tight>
          {!hasInventory ? (
            <EmptyState
              title="No inventory lot data loaded"
              body="Upload your current inventory lots to calculate available-to-promise quantities, committed stock, and near-expiry risk by product."
              action={<Link href="/upload"><Tbtn variant="primary">Upload stg_inventory_lots.csv</Tbtn></Link>}
            />
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th className="r">On Hand (kg)</th>
                  <th className="r">Committed (kg)</th>
                  <th className="r">Near Expiry (kg)</th>
                  <th className="r">Expired (kg)</th>
                  <th className="r">ATP (kg)</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {atp.products.map((p) => (
                  <tr key={p.product_id ?? p.product_name}>
                    <td>{p.product_name}</td>
                    <td className="r">{fmt(p.total_on_hand_kg, 1)}</td>
                    <td className="r">{fmt(p.committed_kg, 1)}</td>
                    <td className="r" style={{ color: p.near_expiry_kg > 0 ? "var(--warn)" : undefined }}>
                      {fmt(p.near_expiry_kg, 1)}
                    </td>
                    <td className="r" style={{ color: p.expired_kg > 0 ? "var(--danger)" : undefined }}>
                      {fmt(p.expired_kg, 1)}
                    </td>
                    <td className="r"><strong>{fmt(p.atp_kg, 1)}</strong></td>
                    <td><RiskBadge level={p.risk_level} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      {recommendations.length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Commitment Recommendations" />
          <CardBody tight>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th className="r">ATP (kg)</th>
                  <th className="r">Safe Commit (kg)</th>
                  <th className="r">Holdback (kg)</th>
                  <th>Risk</th>
                  <th style={{ width: "40%" }}>Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {recommendations.map((r) => (
                  <tr key={r.product_name}>
                    <td>{r.product_name}</td>
                    <td className="r">{fmt(r.atp_kg, 1)}</td>
                    <td className="r"><strong style={{ color: "var(--accent)" }}>{fmt(r.safe_commit_kg, 1)}</strong></td>
                    <td className="r">{fmt(r.holdback_kg, 1)}</td>
                    <td><RiskBadge level={r.risk_level} /></td>
                    <td style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.4 }}>
                      {r.recommendation_text}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
