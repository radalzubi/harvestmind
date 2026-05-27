"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge, Card, CardBody, CardHead, EmptyState, KPI, KPIRow, PageError, PageHeader, PageLoading, Tbtn } from "@/components/ui";
import { getDiagnosticSummary, fmtPct, fmt, type DiagnosticSummary } from "@/lib/api";

export default function TraceabilityPage() {
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Loading traceability data…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const { traceability } = data;
  const t = traceability;
  const statusKind = t.completeness_pct >= 0.95 ? "low" : t.completeness_pct >= 0.5 ? "medium" : "high";

  return (
    <div className="page">
      <PageHeader
        title="Traceability Readiness"
        sub="FSMA-204 lot-level completeness. A lot is complete if it has lot_id, product_id, supplier_id, arrival_date, quantity, and unit."
      />

      <KPIRow>
        <KPI
          label="Completeness"
          value={fmtPct(t.completeness_pct)}
          deltaDir={t.completeness_pct >= 0.9 ? "up" : "down"}
          sub="Target: ≥ 95%"
        />
        <KPI label="Total Lots" value={fmt(t.total_lots)} />
        <KPI label="Complete Lots" value={fmt(t.complete_lots)} />
        <KPI
          label="Incomplete Lots"
          value={fmt(t.total_lots - t.complete_lots)}
          deltaDir={(t.total_lots - t.complete_lots) > 0 ? "down" : "flat"}
        />
      </KPIRow>

      {/* Status banner — only shown when lot data exists */}
      {t.total_lots > 0 && <div style={{
        marginTop: 20,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: "14px 18px",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}>
        <Badge kind={statusKind}>
          {t.completeness_pct >= 0.95 ? "Full Compliance" :
           t.completeness_pct >= 0.5 ? "Partial Compliance" :
           t.completeness_pct > 0 ? "Minimal Compliance" : "No Data"}
        </Badge>
        <span style={{ fontSize: 12, color: "var(--muted)" }}>
          {t.completeness_pct >= 0.95
            ? "Lot traceability meets FSMA-204 readiness threshold."
            : t.completeness_pct >= 0.5
            ? "More than half of lots are traceable. Address missing fields to reach compliance."
            : "Traceability records are incomplete. Upload complete inventory lot data."}
        </span>
      </div>}

      {/* Missing field breakdown */}
      {Object.keys(t.missing_breakdown).length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Missing Fields — Lots Affected" />
          <CardBody tight>
            <table className="data-table">
              <thead>
                <tr><th>Required Field</th><th className="r">Lots Missing</th><th className="r">% of Total</th></tr>
              </thead>
              <tbody>
                {Object.entries(t.missing_breakdown)
                  .sort(([, a], [, b]) => b - a)
                  .map(([field, count]) => (
                    <tr key={field}>
                      <td style={{ fontFamily: "monospace", fontSize: 12 }}>{field}</td>
                      <td className="r">{count}</td>
                      <td className="r">{t.total_lots > 0 ? ((count / t.total_lots) * 100).toFixed(1) + "%" : "—"}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}

      {/* Incomplete lot list */}
      {t.incomplete_lots.length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title={`Incomplete Lots (showing ${Math.min(t.incomplete_lots.length, 50)})`} />
          <CardBody tight>
            <table className="data-table">
              <thead>
                <tr><th>Lot ID</th><th>Product</th><th>Missing Fields</th></tr>
              </thead>
              <tbody>
                {t.incomplete_lots.slice(0, 50).map((lot, i) => (
                  <tr key={i}>
                    <td style={{ fontFamily: "monospace", fontSize: 11 }}>{lot.lot_id || "—"}</td>
                    <td>{lot.product_name || "—"}</td>
                    <td style={{ color: "var(--danger)", fontSize: 11 }}>{lot.missing_fields.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      )}

      {t.total_lots === 0 && (
        <EmptyState
          title="No inventory lot data loaded"
          body="Upload your inventory lots to see FSMA-204 lot-level traceability completeness. HarvestMind checks for lot_id, product_id, supplier_id, arrival_date, quantity, and unit on each lot."
          action={<Link href="/upload"><Tbtn variant="primary">Upload stg_inventory_lots.csv</Tbtn></Link>}
        />
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
