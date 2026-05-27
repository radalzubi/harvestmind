"use client";

import { useState } from "react";
import { Code, Download, Play } from "lucide-react";
import {
  Badge,
  Card,
  CardBody,
  CardHead,
  KPI,
  KPIRow,
  Legend,
  PageHeader,
  Tbtn,
} from "@/components/ui";
import { LineSeries } from "@/components/charts";
import { downloadCSV, toCSV } from "@/lib/csv";
import { useToast } from "@/components/Toast";
import { BACKTEST_SUMMARY, MODEL_LABELS, fmtMoney } from "@/lib/backtest";

export default function BacktestPage() {
  const toast = useToast();
  const [pendingRun, setPendingRun] = useState(false);

  const k = BACKTEST_SUMMARY.kpis;
  const cfg = BACKTEST_SUMMARY.config;

  const onRun = async () => {
    setPendingRun(true);
    await new Promise((r) => setTimeout(r, 1400));
    setPendingRun(false);
    toast.push(`Backtest complete · ${fmtMoney(k.annual_savings_usd)} annual benefit · ${k.roi_multiple}× ROI`);
  };

  const onConfigure = () => {
    toast.push(
      `Config: ${cfg.n_origins} origins, ${cfg.horizon_weeks}w horizon, ${cfg.n_scenarios} scenarios, spot cap ${(cfg.spot_capacity_factor * 100).toFixed(0)}%`,
      "info",
    );
  };

  const onCSV = () => {
    const csv = toCSV(BACKTEST_SUMMARY.per_origin, [
      { key: "origin", label: "Origin" },
      { key: "baseline_total_cost", label: "Baseline ($)" },
      { key: "optimised_total_cost", label: "Optimised ($)" },
      { key: "saved", label: "Saved ($)" },
      { key: "baseline_fill_pct", label: "Baseline fill %" },
      { key: "optimised_fill_pct", label: "Optimised fill %" },
      { key: "baseline_waste_kg", label: "Baseline waste kg" },
      { key: "optimised_waste_kg", label: "Optimised waste kg" },
      { key: "baseline_spot_kg", label: "Baseline spot kg" },
      { key: "optimised_spot_kg", label: "Optimised spot kg" },
      { key: "baseline_lost_kg", label: "Baseline lost kg" },
      { key: "optimised_lost_kg", label: "Optimised lost kg" },
    ]);
    downloadCSV("backtest-results.csv", csv);
    toast.push("CSV downloaded");
  };

  const totalSaved = BACKTEST_SUMMARY.per_origin.reduce((s, r) => s + r.saved, 0);

  return (
    <div className="page">
      <PageHeader
        title="Backtest"
        sub={`Generated ${new Date(BACKTEST_SUMMARY.generated_at).toLocaleString()} · ${cfg.n_origins} origins, ${cfg.horizon_weeks}-week horizon, ${cfg.n_scenarios} SAA scenarios`}
        actions={
          <>
            <Tbtn icon={<Code size={13} strokeWidth={1.6} />} onClick={onConfigure}>
              Configure
            </Tbtn>
            <Tbtn
              variant="primary"
              icon={<Play size={12} strokeWidth={1.6} />}
              onClick={onRun}
              pending={pendingRun}
            >
              {pendingRun ? "Running..." : "Run backtest"}
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
          sub={`across ${cfg.n_origins} origins`}
        />
        <KPI
          label="ROI"
          value={`${k.roi_multiple.toFixed(1)}×`}
          sub={`vs ${fmtMoney(k.annual_subscription_usd)}/yr subscription`}
        />
        <KPI
          label="Service lift"
          value={`${k.fill_rate_lift_pts >= 0 ? "+" : ""}${k.fill_rate_lift_pts.toFixed(1)} pts`}
          deltaDir={k.fill_rate_lift_pts >= 0 ? "up" : "down"}
          sub={`${k.fill_rate_baseline.toFixed(1)}% → ${k.fill_rate_optimised.toFixed(1)}%`}
        />
        <KPI
          label="Spot Δ"
          value={fmtMoney(k.annual_spot_premium_savings_usd)}
          sub={`${Math.abs(k.spot_kg_avoided_period).toLocaleString()} kg over ${cfg.n_origins} origins`}
        />
      </KPIRow>

      <Card>
        <CardHead
          title={`Cost across origins · ${MODEL_LABELS[BACKTEST_SUMMARY.baseline_model]} vs ${MODEL_LABELS[BACKTEST_SUMMARY.optimised_model]}`}
          sub={`Period saved ${fmtMoney(totalSaved)} across ${cfg.n_origins} origins`}
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
            height={300}
            showSavedDelta
          />
        </CardBody>
      </Card>

      <div style={{ height: 16 }} />

      <Card>
        <CardHead
          title="Per-origin results"
          sub="One row per rolling-origin evaluation"
          bordered
          actions={
            <Tbtn icon={<Download size={12} strokeWidth={1.6} />} onClick={onCSV}>
              CSV
            </Tbtn>
          }
        />
        <CardBody tight>
          <div className="table-wrap">
            <table className="t">
              <thead>
                <tr>
                  <th>Origin</th>
                  <th className="num">Baseline</th>
                  <th className="num">Optimised</th>
                  <th className="num">Saved $</th>
                  <th className="num">Saved %</th>
                  <th className="num">Base fill</th>
                  <th className="num">Opt fill</th>
                  <th className="num">Lost kg (opt)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {BACKTEST_SUMMARY.per_origin.map((r) => {
                  const savedPct =
                    r.baseline_total_cost > 0
                      ? r.saved / r.baseline_total_cost
                      : 0;
                  const fillDelta = r.optimised_fill_pct - r.baseline_fill_pct;
                  const pass = r.saved >= 0 && fillDelta >= -1;
                  return (
                    <tr key={r.origin}>
                      <td className="strong">{r.origin}</td>
                      <td className="num muted">{fmtMoney(r.baseline_total_cost)}</td>
                      <td className="num strong">{fmtMoney(r.optimised_total_cost)}</td>
                      <td className="num">
                        <span style={{ color: r.saved >= 0 ? "var(--good)" : "var(--bad)" }}>
                          {fmtMoney(r.saved)}
                        </span>
                      </td>
                      <td className="num">
                        <span style={{ color: r.saved >= 0 ? "var(--good)" : "var(--bad)" }}>
                          {(savedPct * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="num">{r.baseline_fill_pct.toFixed(1)}%</td>
                      <td className="num">
                        <span style={{ color: fillDelta < -1 ? "var(--bad)" : "var(--ink-700)" }}>
                          {r.optimised_fill_pct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="num">{r.optimised_lost_kg.toLocaleString()}</td>
                      <td>
                        {pass ? (
                          <Badge kind="low">Pass</Badge>
                        ) : r.saved >= 0 ? (
                          <Badge kind="medium">Service drop</Badge>
                        ) : (
                          <Badge kind="critical">Worse</Badge>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
