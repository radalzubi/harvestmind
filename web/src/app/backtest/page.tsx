"use client";

import { useState } from "react";
import Link from "next/link";
import { Play } from "lucide-react";
import {
  Card,
  CardBody,
  CardHead,
  EmptyState,
  InfoBanner,
  KPI,
  KPIRow,
  PageHeader,
  Tbtn,
} from "@/components/ui";
import { runBenchmark, fmt, fmtUSD, type BenchmarkResult } from "@/lib/api";

const POLICY_LABELS: Record<string, string> = {
  two_sided_sp: "Two-sided stochastic SP",
  deterministic_lp: "Deterministic LP (mean demand)",
  order_up_to: "Order-up-to (μ + zσ heuristic)",
  naive_runrate: "Naive run-rate (trailing 4 wks)",
};

const SPOT_PRESETS = [
  { label: "Cheap spot (1.3× / 30%)", mult: 1.3, cap: 0.3 },
  { label: "Moderate (1.3× / 15%)", mult: 1.3, cap: 0.15 },
  { label: "Expensive (1.6× / 15%)", mult: 1.6, cap: 0.15 },
  { label: "Scarce (2.0× / 10%)", mult: 2.0, cap: 0.1 },
];

export default function BenchmarkPage() {
  const [result, setResult] = useState<BenchmarkResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preset, setPreset] = useState(0);

  const run = async (presetIdx: number) => {
    setRunning(true);
    setError(null);
    setPreset(presetIdx);
    try {
      const p = SPOT_PRESETS[presetIdx];
      setResult(await runBenchmark(p.mult, p.cap));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="page">
      <PageHeader
        title="Benchmark"
        sub="Rolling-origin head-to-head on your own history: the optimizer must beat the simple baselines or say so"
      />

      <Card>
        <CardHead
          title="Spot Economics Assumption"
          sub="The SP-vs-LP edge depends on what emergency coverage really costs you — pick an assumption, or better, tell us your real numbers"
        />
        <CardBody>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {SPOT_PRESETS.map((p, i) => (
              <Tbtn
                key={p.label}
                variant={i === preset && result ? "primary" : "default"}
                onClick={() => run(i)}
                disabled={running}
              >
                {running && i === preset ? "Running…" : p.label}
              </Tbtn>
            ))}
          </div>
        </CardBody>
      </Card>

      {error && (
        <InfoBanner kind="danger" title="Benchmark failed:">{error}</InfoBanner>
      )}

      {!result && !running && !error && (
        <EmptyState
          title="Run the benchmark on your staged history"
          body="Needs at least 34 weeks of buyer-order history (26 training + 8 evaluation origins). Every policy is scored identically: overage at cost, spot at premium, unmet at lost margin."
          action={<Tbtn variant="primary" onClick={() => run(0)} icon={<Play size={14} />}>Run benchmark</Tbtn>}
        />
      )}

      {result && result.status === "insufficient_history" && (
        <EmptyState
          title="Not enough history to benchmark"
          body={`The benchmark needs ${result.weeks_required ?? 34} weeks of order history; you have ${result.weeks_available ?? 0}. Upload more history to enable an honest head-to-head.`}
          action={<Link href="/upload"><Tbtn variant="primary">Upload data</Tbtn></Link>}
        />
      )}

      {result && result.status === "ok" && result.policies && (
        <>
          {result.gate_passed ? (
            <InfoBanner kind="info" title="Gate passed under this spot assumption:">
              {result.verdict} Edge vs LP: {result.sp_vs_deterministic_lp?.edge_pct}%
              ({result.sp_vs_deterministic_lp?.wins}/{result.sp_vs_deterministic_lp?.n} origins,
              t = {result.sp_vs_deterministic_lp?.paired_t}).
            </InfoBanner>
          ) : (
            <InfoBanner kind="danger" title="Gate FAILED under this spot assumption:">
              {result.verdict}
            </InfoBanner>
          )}

          <KPIRow>
            <KPI
              label="SP vs Deterministic LP"
              value={result.sp_vs_deterministic_lp?.edge_pct != null ? `${result.sp_vs_deterministic_lp.edge_pct}%` : "—"}
              deltaDir={(result.sp_vs_deterministic_lp?.edge_pct ?? 0) > 0 ? "up" : "down"}
              sub={`wins ${result.sp_vs_deterministic_lp?.wins}/${result.sp_vs_deterministic_lp?.n} · t=${result.sp_vs_deterministic_lp?.paired_t}`}
            />
            <KPI
              label="SP vs Naive"
              value={result.sp_vs_naive?.edge_pct != null ? `${result.sp_vs_naive.edge_pct}%` : "—"}
              deltaDir={(result.sp_vs_naive?.edge_pct ?? 0) > 0 ? "up" : "down"}
              sub={`wins ${result.sp_vs_naive?.wins}/${result.sp_vs_naive?.n}`}
            />
            <KPI
              label="SP vs Order-up-to"
              value={result.sp_vs_order_up_to?.edge_pct != null ? `${result.sp_vs_order_up_to.edge_pct}%` : "—"}
              deltaDir={(result.sp_vs_order_up_to?.edge_pct ?? 0) > 0 ? "up" : "down"}
              sub={`wins ${result.sp_vs_order_up_to?.wins}/${result.sp_vs_order_up_to?.n}`}
            />
            <KPI
              label="Gate"
              value={result.gate_passed ? "PASS" : "FAIL"}
              deltaDir={result.gate_passed ? "up" : "down"}
              sub="must beat LP AND naive"
            />
          </KPIRow>

          <Card style={{ marginTop: 16 }}>
            <CardHead title="Policy Head-to-Head" sub={result.scoring ?? ""} />
            <CardBody tight>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Policy</th>
                    <th className="r">Cost / origin</th>
                    <th className="r">Service %</th>
                    <th className="r">Waste kg / origin</th>
                    <th className="r">Folds</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.policies).map(([key, row]) => (
                    <tr key={key} style={key === "two_sided_sp" ? { background: "rgba(74,222,128,0.04)" } : undefined}>
                      <td style={{ fontWeight: key === "two_sided_sp" ? 700 : 500 }}>
                        {POLICY_LABELS[key] ?? key}
                      </td>
                      <td className="r" style={{ fontWeight: 600 }}>{fmtUSD(row.cost_per_origin)}</td>
                      <td className="r">{row.service_pct != null ? `${row.service_pct}%` : "—"}</td>
                      <td className="r">{fmt(row.waste_kg_per_origin)}</td>
                      <td className="r">{row.n_folds}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>

          <InfoBanner kind="warn" title="Read before quoting these numbers:">
            {result.spot_economics?.note}. Scored on {result.data_basis}. Results on synthetic
            sample data are synthetic; “validated” requires your real history.
          </InfoBanner>
        </>
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
