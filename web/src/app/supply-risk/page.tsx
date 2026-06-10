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
  RiskBadge,
  Tbtn,
} from "@/components/ui";
import { getSupplyRisk, fmt, fmtPct, type SupplyRiskResponse } from "@/lib/api";

export default function SupplyRiskPage() {
  const [data, setData] = useState<SupplyRiskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSupplyRisk()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageLoading message="Estimating supplier distributions…" />;
  if (error) return <PageError error={error} />;
  if (!data) return null;

  const cal = data.calibration;
  const quantilePct = data.prior.downside_quantile != null
    ? Math.round((data.prior.downside_quantile as number) * 100)
    : 10;

  return (
    <div className="page">
      <PageHeader
        title="Supply Risk"
        sub="Per-supplier fill-rate distributions: shrunk mean, downside, and how much each is borrowed from the population"
      />

      {/* Calibration verdict — the honesty banner */}
      {cal.status === "ok" && cal.gate_passed === true && (
        <InfoBanner kind="info" title="Distributions are calibrated:">
          The 10–90% interval covered {fmtPct(cal.coverage_10_90 ?? 0)} of {fmt(cal.n_held_out)} held-out
          deliveries (target 80%), PIT-uniformity KS {cal.ks_statistic?.toFixed(3)} ≤ 0.15.
          The stated uncertainties match observed reality on this data.
        </InfoBanner>
      )}
      {cal.status === "ok" && cal.gate_passed === false && (
        <InfoBanner kind="danger" title="Calibration FAILED — do not commit on these intervals:">
          Coverage {fmtPct(cal.coverage_10_90 ?? 0)} vs 80% target, KS {cal.ks_statistic?.toFixed(3)}.
          The model&apos;s stated uncertainties do not match reality on this data; use raw history until recalibrated.
        </InfoBanner>
      )}
      {cal.status !== "ok" && (
        <InfoBanner kind="warn" title="Not yet calibrated:">
          Calibration needs at least 20 held-out deliveries. Upload more delivery history before
          trusting the intervals below.
        </InfoBanner>
      )}

      {data.suppliers.length === 0 ? (
        <EmptyState
          title="No supplier delivery data loaded"
          body="Upload supplier delivery history (ordered vs accepted quantities) to estimate fill-rate distributions."
          action={<Link href="/upload"><Tbtn variant="primary">Upload stg_supplier_deliveries.csv</Tbtn></Link>}
        />
      ) : (
        <>
          <KPIRow>
            <KPI label="Suppliers Modeled" value={fmt(data.suppliers.length)} />
            <KPI
              label="Downside Quantile"
              value={`p${quantilePct}`}
              sub="derived from your cost ratio, not hand-set"
            />
            <KPI
              label="Population Fill"
              value={data.prior.mean != null ? fmtPct(data.prior.mean as number) : "—"}
              sub={`κ = ${(data.prior.kappa as number)?.toFixed(1) ?? "—"} pseudo-deliveries`}
            />
            <KPI
              label="Calibration"
              value={cal.gate_passed == null ? "—" : cal.gate_passed ? "PASS" : "FAIL"}
              deltaDir={cal.gate_passed ? "up" : "down"}
              sub={cal.coverage_10_90 != null ? `${fmtPct(cal.coverage_10_90)} of 80% target` : "needs data"}
            />
          </KPIRow>

          <Card style={{ marginTop: 16 }}>
            <CardHead
              title="Supplier Fill-Rate Distributions"
              sub={`Sorted by downside (p${quantilePct}) — the conservative number commitments should rely on`}
            />
            <CardBody tight>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Supplier</th>
                    <th className="r">Deliveries</th>
                    <th className="r">Raw Mean</th>
                    <th className="r">Shrunk Mean</th>
                    <th className="r">Downside p{quantilePct}</th>
                    <th className="r">Spread</th>
                    <th className="r">Borrowed</th>
                    <th>Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {data.suppliers.map((s) => (
                    <tr key={s.supplier_id}>
                      <td style={{ fontWeight: 600 }}>{s.supplier_name || s.supplier_id}</td>
                      <td className="r">{fmt(s.n_deliveries)}</td>
                      <td className="r" style={{ color: "var(--muted)" }}>
                        {s.observed_mean != null ? fmtPct(s.observed_mean) : "—"}
                      </td>
                      <td className="r">{fmtPct(s.posterior_mean)}</td>
                      <td className="r" style={{
                        fontWeight: 600,
                        color: s.downside < 0.7 ? "var(--danger)" : s.downside < 0.85 ? "var(--warn)" : "var(--accent)",
                      }}>
                        {fmtPct(s.downside)}
                      </td>
                      <td className="r" style={{ color: s.spread > 0.15 ? "var(--warn)" : "var(--muted)" }}>
                        {fmtPct(s.spread)}
                      </td>
                      <td className="r" style={{ color: "var(--muted)" }} title="weight on the population prior">
                        {fmtPct(s.shrinkage)}
                      </td>
                      <td><RiskBadge level={s.risk_level} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          <Card style={{ marginTop: 16 }}>
            <CardHead
              title="External Signals (Tier 2)"
              sub="Weather and other covariates are admitted per-operator only on measured calibration gain — never on faith"
            />
            <CardBody tight>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Signal</th>
                    <th>Status</th>
                    <th>Why</th>
                  </tr>
                </thead>
                <tbody>
                  {data.covariates.signals.map((sig) => (
                    <tr key={sig.signal}>
                      <td style={{ fontWeight: 600 }}>{sig.signal}</td>
                      <td style={{ color: sig.admitted ? "var(--accent)" : "var(--muted)", fontWeight: 600 }}>
                        {sig.admitted ? "admitted" : "not admitted"}
                      </td>
                      <td style={{ fontSize: 11, color: "var(--muted)" }}>{sig.reason ?? "passed the calibration-gain test"}</td>
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
