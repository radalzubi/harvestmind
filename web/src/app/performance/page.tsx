"use client";

import { Download } from "lucide-react";
import {
  Card,
  CardBody,
  CardHead,
  KPI,
  KPIRow,
  Legend,
  PageHeader,
  Tbtn,
} from "@/components/ui";
import { GroupedBars, LineSeries, Waterfall } from "@/components/charts";
import { downloadCSV, toCSV } from "@/lib/csv";
import { useToast } from "@/components/Toast";
import { BACKTEST_SUMMARY, MODEL_LABELS, fmtMoney } from "@/lib/backtest";

export default function PerformancePage() {
  const toast = useToast();
  const k = BACKTEST_SUMMARY.kpis;
  const cfg = BACKTEST_SUMMARY.config;

  const onExport = () => {
    const csv = toCSV(BACKTEST_SUMMARY.cost_trend, [
      { key: "label", label: "Origin" },
      { key: "baseline", label: "Baseline ($)" },
      { key: "optimised", label: "Optimised ($)" },
    ]);
    downloadCSV("performance-trend.csv", csv);
    toast.push("CSV downloaded");
  };

  const onCompare = () => {
    toast.push("Period comparison coming soon", "info");
  };

  // Waterfall composition: actual values from real backtest
  const waterfallItems = [
    { label: "Spot Δ", value: Math.abs(k.annual_spot_premium_savings_usd), kind: (k.annual_spot_premium_savings_usd >= 0 ? "plus" : "minus") as "plus" | "minus" },
    { label: "Waste Δ", value: Math.abs(k.annual_waste_reduction_usd), kind: (k.annual_waste_reduction_usd >= 0 ? "plus" : "minus") as "plus" | "minus" },
    { label: "Subscription", value: k.annual_subscription_usd, kind: "minus" as const },
    { label: "Net benefit", value: k.annual_savings_usd - k.annual_subscription_usd, kind: "total" as const },
  ];

  const totalSavedAcrossOrigins = BACKTEST_SUMMARY.cost_trend.reduce(
    (s, d) => s + (d.baseline - d.optimised),
    0,
  );

  return (
    <div className="page">
      <PageHeader
        title="Performance"
        sub={`${MODEL_LABELS[BACKTEST_SUMMARY.optimised_model]} vs ${MODEL_LABELS[BACKTEST_SUMMARY.baseline_model]} · ${cfg.n_origins} origins · spot capacity ${(cfg.spot_capacity_factor * 100).toFixed(0)}% of demand`}
        actions={
          <>
            <Tbtn icon={<Download size={13} strokeWidth={1.6} />} onClick={onExport}>
              Export
            </Tbtn>
            <Tbtn variant="primary" onClick={onCompare}>
              Compare period
            </Tbtn>
          </>
        }
      />

      <KPIRow cols={4}>
        <KPI
          label="Annual benefit"
          value={fmtMoney(k.annual_savings_usd)}
          delta={`${fmtMoney(k.confidence_low_usd)} – ${fmtMoney(k.confidence_high_usd)} 95% CI`}
          deltaDir={k.annual_savings_usd >= 0 ? "up" : "down"}
          sub="modeled"
        />
        <KPI
          label="Period total saved"
          value={fmtMoney(k.period_saved_usd)}
          sub={`${cfg.n_origins} origins × ${cfg.horizon_weeks}w`}
        />
        <KPI
          label="Service level"
          value={k.fill_rate_optimised.toFixed(1)}
          unit="%"
          delta={`${k.fill_rate_lift_pts >= 0 ? "+" : ""}${k.fill_rate_lift_pts.toFixed(1)} pts vs baseline`}
          deltaDir={k.fill_rate_lift_pts >= 0 ? "up" : "down"}
          sub={`baseline ${k.fill_rate_baseline.toFixed(1)}%`}
        />
        <KPI
          label="ROI"
          value={`${k.roi_multiple.toFixed(1)}×`}
          sub={`vs ${fmtMoney(k.annual_subscription_usd)}/yr subscription`}
        />
      </KPIRow>

      <Card>
        <CardHead
          title="Cost: baseline vs optimised"
          sub={`Total cost per origin · cumulative ${fmtMoney(totalSavedAcrossOrigins)} saved across ${cfg.n_origins} origins`}
          actions={
            <Legend
              items={[
                { label: "Baseline", color: "#E4E4E7" },
                { label: "Optimised", color: "#4F46E5" },
              ]}
            />
          }
        />
        <CardBody>
          <LineSeries
            data={BACKTEST_SUMMARY.cost_trend}
            series={[
              { key: "baseline", name: "Baseline", color: "#E4E4E7" },
              { key: "optimised", name: "Optimised", color: "#4F46E5" },
            ]}
            height={320}
            showSavedDelta
          />
        </CardBody>
      </Card>

      <div style={{ height: 16 }} />

      <div className="grid-2">
        <Card>
          <CardHead title="Where the savings come from" sub="Annualized composition vs naive baseline" />
          <CardBody>
            <Waterfall items={waterfallItems} height={280} />
          </CardBody>
        </Card>
        <Card>
          <CardHead title="Fill rate by origin" sub="Optimised should track or beat baseline" />
          <CardBody>
            <GroupedBars
              data={BACKTEST_SUMMARY.per_origin.map((r) => ({
                label: r.origin.slice(5),  // MM-DD
                baseline: r.baseline_fill_pct,
                optimised: r.optimised_fill_pct,
              }))}
              height={280}
              yFormat={(v) => `${v.toFixed(0)}%`}
            />
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
