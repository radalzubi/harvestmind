"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Download } from "lucide-react";
import { Card, CardBody, CardHead, EmptyState, KPI, KPIRow, PageError, PageHeader, PageLoading, Tbtn } from "@/components/ui";
import { HBars } from "@/components/charts";
import { downloadCSV, toCSV } from "@/lib/csv";
import { getDiagnosticSummary, fmtUSD, type DiagnosticSummary } from "@/lib/api";
import { useToast } from "@/components/Toast";

export default function LossPage() {
  const toast = useToast();
  const [data, setData] = useState<DiagnosticSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDiagnosticSummary()
      .then(setData)
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, []);

  if (error) return <PageError error={error} />;
  if (!data) return <PageLoading message="Loading live loss exposure…" />;

  const byProduct = new Map<string, { product: string; waste: number; shortage: number; total: number }>();
  for (const row of data.waste.by_product) {
    byProduct.set(row.product_name, { product: row.product_name, waste: row.loss_usd, shortage: 0, total: row.loss_usd });
  }
  for (const row of data.shortage.by_product) {
    const current = byProduct.get(row.product_name) ?? { product: row.product_name, waste: 0, shortage: 0, total: 0 };
    current.shortage += row.loss_usd;
    current.total += row.loss_usd;
    byProduct.set(row.product_name, current);
  }
  const rows = [...byProduct.values()].sort((a, b) => b.total - a.total);
  const reasons = data.waste.by_reason.slice(0, 8).map((row) => ({ reason: row.reason, v: row.loss_usd }));
  const total = data.waste.total_usd + data.shortage.total_usd;

  const exportRows = () => {
    downloadCSV("live-loss-exposure.csv", toCSV(rows, [
      { key: "product", label: "Product" },
      { key: "waste", label: "Waste loss ($)" },
      { key: "shortage", label: "Shortage exposure ($)" },
      { key: "total", label: "Combined exposure ($)" },
    ]));
    toast.push("Live loss CSV downloaded");
  };

  return (
    <div className="page">
      <PageHeader
        title="Loss exposure"
        sub={`Live from the connected operator vault · ${data.period_days}-day window`}
        actions={<Tbtn icon={<Download size={13} />} onClick={exportRows}>Export</Tbtn>}
      />
      {rows.length === 0 ? (
        <EmptyState
          title="No loss records available"
          body="Upload orders and waste records to calculate product-level exposure. No sample figures are displayed."
          action={<Link href="/upload"><Tbtn variant="primary">Upload data</Tbtn></Link>}
        />
      ) : (
        <>
          <KPIRow cols={3}>
            <KPI label="Combined exposure" value={fmtUSD(total)} sub="Observed period; not a savings claim" />
            <KPI label="Shortage exposure" value={fmtUSD(data.shortage.total_usd)} sub={`${data.shortage.n_at_risk} at-risk lines`} />
            <KPI label="Waste loss" value={fmtUSD(data.waste.total_usd)} sub={`${data.waste.n_rows} recorded events`} />
          </KPIRow>
          <div className="grid-2">
            <Card>
              <CardHead title="Top waste reasons" sub="Recorded cost basis" />
              <CardBody>{reasons.length ? <HBars data={reasons} height={280} /> : <span>No reason-level waste data.</span>}</CardBody>
            </Card>
            <Card>
              <CardHead title="Loss by product" sub="Waste plus shortage exposure" />
              <CardBody tight>
                <div className="table-wrap"><table className="t"><thead><tr><th>Product</th><th className="num">Waste</th><th className="num">Shortage</th><th className="num">Total</th></tr></thead>
                  <tbody>{rows.slice(0, 12).map((row) => <tr key={row.product}><td className="product">{row.product}</td><td className="num">{fmtUSD(row.waste)}</td><td className="num">{fmtUSD(row.shortage)}</td><td className="num strong">{fmtUSD(row.total)}</td></tr>)}</tbody>
                </table></div>
              </CardBody>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
