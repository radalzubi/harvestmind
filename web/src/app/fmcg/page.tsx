"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

type Money = { amount: string; currency: string };
type Order = {
  sku: string; supplier_id: string; week_offset: number; order_units: number;
  lots: number; lot_unit: string; units_per_lot: number; purchase_value: Money; explanation: string[];
};
type Plan = {
  run_id: string; mode_run: string; solver_status: string; warnings: string[];
  unit: string; currency: string; orders: Order[]; purchase_value: Money;
  selection_backtest_costs: Record<string, Money>;
};
type Status = { tables: Record<string, number>; ready_to_plan: boolean; minimum_history_weeks: number };

export default function FmcgPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("canonical");
  const [horizon, setHorizon] = useState(12);
  const [service, setService] = useState(0.97);
  const [open, setOpen] = useState<number | null>(null);
  const [needsDiagnostic, setNeedsDiagnostic] = useState(false);

  const refresh = () => apiFetch<Status>("/fmcg/status").then(setStatus).catch((e) =>
    setError(e instanceof Error ? e.message : "status failed"));
  useEffect(() => { refresh(); }, []);

  async function build() {
    setBusy(true); setError(null); setPlan(null); setNeedsDiagnostic(false);
    try {
      const q = new URLSearchParams({ mode, horizon_weeks: String(horizon), service_level: String(service) });
      setPlan(await apiFetch<Plan>(`/fmcg/plan?${q}`, { method: "POST" }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "plan failed";
      if (msg.includes("diagnostic_required")) setNeedsDiagnostic(true);
      else setError(msg);
    } finally { setBusy(false); }
  }

  const money = (m?: Money) => (m ? `${Number(m.amount).toLocaleString()} ${m.currency}` : "n/a");

  return (
    <main className="p-6 space-y-6 max-w-6xl">
      <h1 className="text-2xl font-semibold">Purchase plan</h1>
      <p className="text-sm opacity-80">Whole cases and pallets, MOQ, fill and lead-time risk. A recommendation on
        your uploaded history, in eaches, not a realised saving.</p>

      <section className="rounded border p-4 space-y-2">
        <h2 className="font-medium">1. Your data</h2>
        {status && (
          <p className="text-sm">{Object.values(status.tables).reduce((a, b) => a + b, 0).toLocaleString()} rows loaded across {Object.values(status.tables).filter((n) => n > 0).length} files.
            {" "}<a className="underline" href="/upload">Upload or replace files</a>.</p>
        )}
        {status && !status.ready_to_plan && <p className="text-sm text-amber-700">Upload the required files first (at least {status.minimum_history_weeks} weeks of history).</p>}
      </section>

      <section className="rounded border p-4 space-y-3">
        <h2 className="font-medium">2. Plan</h2>
        <p className="text-xs opacity-70">Safe: applies the verdict of your latest diagnostic, so it solves in seconds. The diagnostic is where the candidates are backtested on your own history. Adaptive: the state-conditioned optimizer, ungated. The others are single policies for comparison.</p>
        <div className="flex gap-4 flex-wrap items-end">
          <label className="text-sm">Mode
            <select className="block border rounded px-2 py-1" value={mode} onChange={(e) => setMode(e.target.value)}>
              {["canonical", "safe", "adaptive", "stochastic", "deterministic", "order_up_to", "incumbent"].map((m) => <option key={m}>{m === "canonical" ? "canonical (frozen ZAAD P1)" : `${m} (legacy)`}</option>)}
            </select></label>
          <label className="text-sm">Horizon (weeks)
            <input className="block border rounded px-2 py-1 w-24" type="number" min={4} max={26} value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))} /></label>
          <label className="text-sm">Service target
            <input className="block border rounded px-2 py-1 w-24" type="number" step={0.005} min={0.8} max={0.995}
              value={service} onChange={(e) => setService(Number(e.target.value))} /></label>
          <button className="rounded bg-black text-white px-4 py-2 disabled:opacity-40"
            disabled={busy || !status?.ready_to_plan} onClick={build}>{busy ? "Solving…" : "Build plan"}</button>
        </div>
        {needsDiagnostic && (
          <p className="text-sm rounded border border-amber-300 bg-amber-50 px-3 py-2" role="alert">
            Run the diagnostic first. It backtests the candidates on your history and decides whether the optimizer may change your orders; the plan then solves in seconds.{" "}
            <Link className="underline font-medium" href="/start">Go to Start</Link>
          </p>
        )}
        {error && <p className="text-sm text-red-600" role="alert">{error}</p>}
        {plan && (
          <div className="space-y-3">
            <p className="text-sm">Mode run <b>{plan.mode_run}</b> · solver <b>{plan.solver_status}</b> · run {plan.run_id}
              · purchase value <b>{money(plan.purchase_value)}</b></p>
            {Object.keys(plan.selection_backtest_costs ?? {}).length > 0 && (
              <p className="text-xs opacity-70">Trailing-history backtest cost by candidate (lower won):{" "}
                {Object.entries(plan.selection_backtest_costs).map(([k, v]) => `${k}: ${money(v)}`).join(" · ")}</p>
            )}
            <div className="overflow-x-auto">
              <table className="text-sm w-full">
                <thead><tr className="text-left">
                  <th>SKU</th><th>Supplier</th><th>Week</th><th className="text-right">Units</th>
                  <th className="text-right">Lots</th><th>Lot</th><th className="text-right">Value</th><th></th>
                </tr></thead>
                <tbody>
                  {plan.orders.map((o, i) => (
                    <tr key={i} className="border-t align-top">
                      <td className="font-mono">{o.sku}</td><td>{o.supplier_id}</td><td>{o.week_offset}</td>
                      <td className="text-right">{o.order_units.toLocaleString()}</td>
                      <td className="text-right">{o.lots}</td><td>{o.lot_unit} × {o.units_per_lot}</td>
                      <td className="text-right">{money(o.purchase_value)}</td>
                      <td><button className="underline text-xs" onClick={() => setOpen(open === i ? null : i)}>why</button>
                        {open === i && <ul className="text-xs mt-1 list-disc pl-4">{o.explanation.map((l, k) => <li key={k}>{l}</li>)}</ul>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {plan.warnings.map((w, i) => <p key={i} className="text-xs text-amber-700">{w}</p>)}
          </div>
        )}
      </section>
    </main>
  );
}
