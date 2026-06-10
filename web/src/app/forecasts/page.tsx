"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
import {
  getDemandForecast,
  getForecastEvaluation,
  fmt,
  fmtPct,
  type DemandForecastResponse,
  type ForecastEvaluation,
} from "@/lib/api";

export default function ForecastsPage() {
  const [fc, setFc] = useState<DemandForecastResponse | null>(null);
  const [ev, setEv] = useState<ForecastEvaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getDemandForecast(4), getForecastEvaluation()])
      .then(([f, e]) => {
        setFc(f);
        setEv(e);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Fitting demand models on your history…" />;
  if (error) return <PageError error={error} />;
  if (!fc) return null;

  const insufficient = fc.model_info.status === "insufficient_history";

  return (
    <div className="page">
      <PageHeader
        title="Demand Forecast"
        sub="Next-week demand per product with uncertainty, from models fit to your own order history"
      />

      {/* Honest gate banner — never hide an unflattering verdict */}
      {ev && ev.status === "ok" && ev.gate_passed === true && (
        <InfoBanner kind="info" title="Model beats seasonal-naive out-of-sample:">
          WAPE {fmtPct(ev.wape_model ?? 0)} vs naive {fmtPct(ev.wape_seasonal_naive ?? 0)}
          {" "}(ratio {ev.oos_mase_ratio?.toFixed(2)}, bias {ev.bias_pct_model?.toFixed(1)}%)
          across {ev.folds?.length ?? 0} rolling-origin folds.
        </InfoBanner>
      )}
      {ev && ev.status === "ok" && ev.gate_passed === false && (
        <InfoBanner kind="danger" title="Honest verdict — model does NOT beat seasonal-naive:">
          On your data the simple seasonal-naive forecaster is currently the better predictor
          (model WAPE {fmtPct(ev.wape_model ?? 0)} vs naive {fmtPct(ev.wape_seasonal_naive ?? 0)}).
          Forecasts below are shown for transparency, but the naive baseline is the honest planning input.
        </InfoBanner>
      )}
      {ev && ev.status !== "ok" && (
        <InfoBanner kind="warn" title="Not enough history to evaluate:">
          Rolling-origin evaluation needs at least 16 weeks of order history.
          The forecaster has not been validated on your data yet.
        </InfoBanner>
      )}

      {insufficient ? (
        <EmptyState
          title="Not enough order history to forecast"
          body="The demand forecaster needs at least 8 weeks of buyer order history. Upload more history to enable forecasting."
          action={<Link href="/upload"><Tbtn variant="primary">Upload stg_buyer_orders.csv</Tbtn></Link>}
        />
      ) : (
        <>
          <KPIRow>
            <KPI label="Products Forecast" value={fmt(fc.products.length)} />
            <KPI
              label="OOS WAPE (model)"
              value={ev?.wape_model != null ? fmtPct(ev.wape_model) : "—"}
              sub="lower is better"
            />
            <KPI
              label="vs Seasonal-Naive"
              value={ev?.oos_mase_ratio != null ? `${ev.oos_mase_ratio.toFixed(2)}×` : "—"}
              deltaDir={ev?.gate_passed ? "up" : "down"}
              sub="< 1.00 = model wins"
            />
            <KPI
              label="Bias"
              value={ev?.bias_pct_model != null ? `${ev.bias_pct_model.toFixed(1)}%` : "—"}
              sub="+ = over-forecasting"
            />
          </KPIRow>

          <Card style={{ marginTop: 16 }}>
            <CardHead
              title="Next-Week Demand by Product"
              sub={`As of ${fc.as_of} · q10–q90 from held-out residuals · weekly rate held flat across the horizon`}
            />
            <CardBody tight>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th className="r">Forecast kg/wk</th>
                    <th className="r">q10</th>
                    <th className="r">q90</th>
                    <th>Model</th>
                    <th>Drivers (arithmetic, not magic)</th>
                  </tr>
                </thead>
                <tbody>
                  {fc.products.map((p) => (
                    <tr key={p.product_name}>
                      <td style={{ fontWeight: 600 }}>{p.product_name}</td>
                      <td className="r" style={{ fontWeight: 600 }}>{fmt(p.forecast_kg_per_week)}</td>
                      <td className="r" style={{ color: "var(--muted)" }}>{fmt(p.quantiles_kg.q10)}</td>
                      <td className="r" style={{ color: "var(--muted)" }}>{fmt(p.quantiles_kg.q90)}</td>
                      <td><code style={{ fontSize: 11 }}>{p.model}</code></td>
                      <td style={{ fontSize: 11, color: "var(--muted)" }}>{p.drivers.join(" · ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          {ev?.folds && ev.folds.length > 0 && (
            <Card style={{ marginTop: 16 }}>
              <CardHead
                title="Rolling-Origin Evaluation"
                sub="Out-of-sample, lookahead-protected. Metrics: WAPE / naive-ratio / bias — MAPE is never used."
              />
              <CardBody tight>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Origin</th>
                      <th className="r">Series</th>
                      <th className="r">WAPE model</th>
                      <th className="r">WAPE naive</th>
                      <th className="r">Bias %</th>
                      <th className="r">Winner</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ev.folds.map((f) => (
                      <tr key={f.fold}>
                        <td>{f.origin}</td>
                        <td className="r">{f.n_series}</td>
                        <td className="r">{fmtPct(f.wape_model)}</td>
                        <td className="r">{fmtPct(f.wape_seasonal_naive)}</td>
                        <td className="r">{f.bias_pct_model.toFixed(1)}%</td>
                        <td className="r" style={{
                          color: f.wape_model < f.wape_seasonal_naive ? "var(--accent)" : "var(--danger)",
                          fontWeight: 600,
                        }}>
                          {f.wape_model < f.wape_seasonal_naive ? "model" : "naive"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardBody>
            </Card>
          )}
        </>
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
