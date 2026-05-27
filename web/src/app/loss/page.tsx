"use client";

import { Download } from "lucide-react";
import {
  BarCell,
  Card,
  CardBody,
  CardHead,
  KPI,
  KPIRow,
  PageHeader,
  Tbtn,
} from "@/components/ui";
import { HBars, LineSeries } from "@/components/charts";
import { LOSSES, SPOT_TREND, WASTE_REASONS, fmt } from "@/lib/data";
import { downloadCSV, toCSV } from "@/lib/csv";
import { useToast } from "@/components/Toast";

export default function LossPage() {
  const toast = useToast();
  const maxTotal = Math.max(...LOSSES.map((l) => l.total));

  const exportLossesCSV = () => {
    const csv = toCSV(LOSSES, [
      { key: "sku", label: "SKU" },
      { key: "product", label: "Product" },
      { key: "spot", label: "Spot premium ($)" },
      { key: "waste", label: "Waste cost ($)" },
      { key: "total", label: "Total loss ($)" },
      { key: "reason", label: "Top reason" },
      { key: "action", label: "Recommended action" },
    ]);
    downloadCSV("loss-by-product.csv", csv);
    toast.push("CSV downloaded");
  };

  const exportAllCSV = () => {
    exportLossesCSV();
  };

  return (
    <div className="page">
      <PageHeader
        title="Loss exposure"
        sub="Where revenue is leaking — trailing 12 weeks"
        actions={
          <Tbtn icon={<Download size={13} strokeWidth={1.6} />} onClick={exportAllCSV}>
            Export
          </Tbtn>
        }
      />

      <KPIRow cols={3}>
        <KPI label="Combined loss" value="$81.2K" delta="−5.1% vs last quarter" deltaDir="up" sub="2.7% of revenue" />
        <KPI label="Spot premium" value="$42.5K" delta="+4.2% vs last quarter" deltaDir="down" sub="84 emergency POs" />
        <KPI label="Waste cost" value="$38.7K" delta="−12.4% vs last quarter" deltaDir="up" sub="218 events · $1.2K avg" />
      </KPIRow>

      <div className="grid-2">
        <Card>
          <CardHead title="Top waste reasons" sub="By cost — quality and shelf life dominate" />
          <CardBody>
            <HBars data={WASTE_REASONS} color="#4F46E5" height={260} />
          </CardBody>
        </Card>

        <Card>
          <CardHead title="Spot spending over time" sub="Weekly emergency-PO total ($)" />
          <CardBody>
            <LineSeries
              data={SPOT_TREND.map((d) => ({ label: d.label, optimised: d.val }))}
              series={[{ key: "optimised", name: "Spot $", color: "#4F46E5" }]}
              height={260}
              yFormat={(v) => `$${(v / 1000).toFixed(1)}K`}
            />
          </CardBody>
        </Card>
      </div>

      <div style={{ height: 16 }} />

      <Card>
        <CardHead
          title="Loss by product"
          sub="Sorted by total loss"
          bordered
          actions={
            <Tbtn icon={<Download size={12} strokeWidth={1.6} />} onClick={exportLossesCSV}>
              CSV
            </Tbtn>
          }
        />
        <CardBody tight>
          <div className="table-wrap">
            <table className="t">
              <thead>
                <tr>
                  <th>Product</th>
                  <th className="num">Spot</th>
                  <th className="num">Waste</th>
                  <th className="num">Total</th>
                  <th>Top reason</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {LOSSES.map((r) => (
                  <tr key={r.sku}>
                    <td className="product">{r.product}</td>
                    <td className="num">{fmt.cur(r.spot)}</td>
                    <td className="num">{fmt.cur(r.waste)}</td>
                    <td className="num strong">
                      <BarCell
                        value={r.total}
                        max={maxTotal}
                        color="var(--accent)"
                        format={(v) => fmt.cur(v)}
                      />
                    </td>
                    <td className="muted">{r.reason}</td>
                    <td className="muted">{r.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
