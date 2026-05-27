"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardBody, CardHead, EmptyState, KPI, KPIRow, PageError, PageHeader, PageLoading, RiskBadge, Tbtn } from "@/components/ui";
import { getDiagnosticSummary, fmtUSD, fmt, type DiagnosticSummary } from "@/lib/api";

export default function InventoryPage() {
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Loading inventory risk data…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const { waste, atp } = data;
  const totalNearExpiry = atp.products.reduce((s, p) => s + p.near_expiry_kg, 0);
  const totalExpired = atp.products.reduce((s, p) => s + p.expired_kg, 0);
  const totalOnHand = atp.products.reduce((s, p) => s + p.total_on_hand_kg, 0);
  const hasInventory = atp.products.length > 0;
  const hasWaste = waste.by_product.length > 0;

  return (
    <div className="page">
      <PageHeader
        title="Inventory Risk"
        sub="Near-expiry inventory, expired stock, waste events, and lot-level risk flags."
      />

      <KPIRow>
        <KPI label="Total On Hand" value={fmt(totalOnHand, 0) + " kg"} />
        <KPI
          label="Near Expiry (≤3 days)"
          value={fmt(totalNearExpiry, 0) + " kg"}
          deltaDir={totalNearExpiry > 0 ? "down" : "flat"}
          delta={totalOnHand > 0 ? `${((totalNearExpiry / totalOnHand) * 100).toFixed(1)}% of stock` : undefined}
        />
        <KPI
          label="Expired Stock"
          value={fmt(totalExpired, 0) + " kg"}
          deltaDir={totalExpired > 0 ? "down" : "flat"}
        />
        <KPI
          label="Waste Loss"
          value={fmtUSD(waste.total_usd)}
          deltaDir={waste.total_usd > 0 ? "down" : "flat"}
        />
      </KPIRow>

      {/* Inventory lots by product */}
      <Card style={{ marginTop: 20 }}>
        <CardHead title="Inventory by Product" />
        <CardBody tight>
          {!hasInventory ? (
            <EmptyState
              title="No inventory lot data loaded"
              body="Upload your current inventory lots to see on-hand quantities, committed stock, and near-expiry risk by product."
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
                  <tr key={p.product_name}>
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

      {/* Waste by product */}
      {!hasWaste && hasInventory && (
        <div style={{ marginTop: 16, padding: "12px 16px", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12, color: "var(--muted)" }}>
          No waste adjustment data loaded. Upload stg_waste_adjustments.csv to see waste loss by product and reason.
        </div>
      )}

      {hasWaste && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Waste Loss by Product" />
          <CardBody tight>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th className="r">Qty Lost (kg)</th>
                  <th className="r">Loss ($)</th>
                </tr>
              </thead>
              <tbody>
                {waste.by_product.map((w, i) => (
                  <tr key={i}>
                    <td>{w.product_name || "—"}</td>
                    <td className="r">{fmt(w.quantity_lost_kg, 1)}</td>
                    <td className="r">{fmtUSD(w.loss_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}

      {waste.by_reason.length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Waste Loss by Reason" />
          <CardBody tight>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Reason</th>
                  <th className="r">Qty Lost (kg)</th>
                  <th className="r">Loss ($)</th>
                </tr>
              </thead>
              <tbody>
                {waste.by_reason.map((w, i) => (
                  <tr key={i}>
                    <td>{w.reason || "—"}</td>
                    <td className="r">{fmt(w.quantity_lost_kg, 1)}</td>
                    <td className="r">{fmtUSD(w.loss_usd)}</td>
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
