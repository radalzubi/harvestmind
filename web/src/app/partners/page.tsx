"use client";

import { useEffect, useMemo, useState } from "react";
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
  Tabs,
  Tbtn,
} from "@/components/ui";
import { getDiagnosticSummary, fmtPct, fmt, type DiagnosticSummary } from "@/lib/api";

type Tab = "suppliers" | "buyers";

export default function PartnersPage() {
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("suppliers");

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Loading partner data…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const { supplier, buyer } = data;

  const riskOrder: Record<string, number> = { High: 0, Medium: 1, Low: 2, Unknown: 4 };
  const sortedSuppliers = useMemo(
    () => [...supplier.suppliers].sort((a, b) => (riskOrder[a.risk_level] ?? 3) - (riskOrder[b.risk_level] ?? 3)),
    [supplier.suppliers],
  );
  const sortedBuyers = useMemo(
    () => [...buyer.buyers].sort((a, b) => (riskOrder[a.risk_level] ?? 3) - (riskOrder[b.risk_level] ?? 3)),
    [buyer.buyers],
  );

  // Suppliers with known fill rates only — Unknown tier is excluded from averages
  const ratedSuppliers = supplier.suppliers.filter((s) => s.fill_rate !== null);
  const avgSupplierFill = ratedSuppliers.length > 0
    ? ratedSuppliers.reduce((acc, x) => acc + (x.fill_rate as number), 0) / ratedSuppliers.length
    : 0;
  const avgSupplierRej = supplier.suppliers.length > 0
    ? supplier.suppliers.reduce((s, x) => s + x.rejection_rate, 0) / supplier.suppliers.length
    : 0;
  const avgBuyerFulfillment = buyer.buyers.length > 0
    ? buyer.buyers.reduce((s, x) => s + x.fulfillment_rate, 0) / buyer.buyers.length
    : 0;
  const avgBuyerMissed = buyer.buyers.length > 0
    ? buyer.buyers.reduce((s, x) => s + x.missed_rate, 0) / buyer.buyers.length
    : 0;

  return (
    <div className="page">
      <PageHeader
        title="Partners"
        sub="Supplier reliability and buyer fulfillment ranked by risk"
      />

      <Tabs<Tab>
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "suppliers", label: "Suppliers", count: supplier.suppliers.length },
          { id: "buyers", label: "Buyers", count: buyer.buyers.length },
        ]}
      />

      {tab === "suppliers" ? (
        <>
          <KPIRow>
            <KPI
              label="At Risk"
              value={fmt(supplier.n_risky)}
              deltaDir={supplier.n_risky > 0 ? "down" : "flat"}
              sub="fill rate < 80%"
            />
            <KPI
              label="Avg Fill Rate"
              value={fmtPct(avgSupplierFill)}
              deltaDir={avgSupplierFill >= 0.9 ? "up" : "down"}
              sub="Target: ≥ 95%"
            />
            <KPI
              label="Avg Rejection Rate"
              value={fmtPct(avgSupplierRej)}
              deltaDir={avgSupplierRej <= 0.05 ? "up" : "down"}
            />
            <KPI label="Suppliers Tracked" value={fmt(supplier.suppliers.length)} />
          </KPIRow>

          <Card style={{ marginTop: 16 }}>
            <CardHead title="Supplier Reliability" sub="Sorted by risk tier — High first" />
            <CardBody tight>
              {sortedSuppliers.length === 0 ? (
                <EmptyState
                  title="No supplier delivery data loaded"
                  body="Upload your supplier delivery history to see fill rates, rejection rates, and reliability scores by supplier."
                  action={<Link href="/upload"><Tbtn variant="primary">Upload stg_supplier_deliveries.csv</Tbtn></Link>}
                />
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Supplier</th>
                      <th className="r">Deliveries</th>
                      <th className="r">Fill Rate</th>
                      <th className="r">Rejection Rate</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedSuppliers.map((s) => {
                      const fr = s.fill_rate;
                      const color = fr === null
                        ? "var(--muted)"
                        : fr < 0.80 ? "var(--danger)"
                        : fr < 0.90 ? "var(--warn)"
                        : "var(--accent)";
                      return (
                        <tr key={s.supplier_id}>
                          <td>{s.supplier_name || s.supplier_id || "—"}</td>
                          <td className="r">{fmt(s.n_deliveries)}</td>
                          <td className="r" style={{ color, fontWeight: 600 }}>
                            {fr === null ? "—" : fmtPct(fr)}
                          </td>
                          <td className="r" style={{ color: s.rejection_rate > 0.1 ? "var(--danger)" : undefined }}>
                            {fmtPct(s.rejection_rate)}
                          </td>
                          <td><RiskBadge level={s.risk_level} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>
        </>
      ) : (
        <>
          <KPIRow>
            <KPI
              label="At Risk"
              value={fmt(buyer.n_risky)}
              deltaDir={buyer.n_risky > 0 ? "down" : "flat"}
              sub="fulfillment rate < 90%"
            />
            <KPI
              label="Avg Fulfillment"
              value={fmtPct(avgBuyerFulfillment)}
              deltaDir={avgBuyerFulfillment >= 0.9 ? "up" : "down"}
              sub="Target: ≥ 90%"
            />
            <KPI
              label="Avg Missed Rate"
              value={fmtPct(avgBuyerMissed)}
              deltaDir={avgBuyerMissed <= 0.05 ? "up" : "down"}
            />
            <KPI label="Buyers Tracked" value={fmt(buyer.buyers.length)} />
          </KPIRow>

          <Card style={{ marginTop: 16 }}>
            <CardHead title="Buyer Fulfillment" sub="Sorted by risk tier — High first" />
            <CardBody tight>
              {sortedBuyers.length === 0 ? (
                <EmptyState
                  title="No buyer order data loaded"
                  body="Upload your buyer order history to see fulfillment rates, missed orders, and substitution rates by buyer."
                  action={<Link href="/upload"><Tbtn variant="primary">Upload stg_buyer_orders.csv</Tbtn></Link>}
                />
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Buyer</th>
                      <th className="r">Orders</th>
                      <th className="r">Fulfillment</th>
                      <th className="r">Substitution</th>
                      <th className="r">Missed</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedBuyers.map((b) => (
                      <tr key={b.buyer_id}>
                        <td>{b.buyer_name || b.buyer_id || "—"}</td>
                        <td className="r">{fmt(b.n_orders)}</td>
                        <td className="r" style={{
                          color: b.fulfillment_rate < 0.90 ? "var(--danger)" : b.fulfillment_rate < 0.95 ? "var(--warn)" : "var(--accent)",
                          fontWeight: 600,
                        }}>
                          {fmtPct(b.fulfillment_rate)}
                        </td>
                        <td className="r">{fmtPct(b.substitution_rate)}</td>
                        <td className="r" style={{ color: b.missed_rate > 0.1 ? "var(--danger)" : undefined }}>
                          {fmtPct(b.missed_rate)}
                        </td>
                        <td><RiskBadge level={b.risk_level} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardBody>
          </Card>
        </>
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
