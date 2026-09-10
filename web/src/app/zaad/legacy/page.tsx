"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";

type Row = Record<string, unknown>;
type Action = { route: string; item: string; quantity: number; expected_accepted: number; expected_due_in: number; cash: number };
type Report = {
  brand: string; operator_id: string; as_of: string; input_fingerprint: string;
  evidence_label: string; status: string; mode: string; selected_policy: string;
  actions: Action[]; incumbent_actions: Action[]; reasons: string[];
  frontier: Row[]; routes: Row[]; forecasts: Row[]; economics: Row; evidence: Row;
  limitations: string[]; approval_required: boolean; executable_purchase_order: boolean;
};
type Demo = { request: Row; report: Report; classification: string };
const views = ["Overview", "Inventory opportunities", "Supply risk", "Route alternatives", "Recommendations", "Scenario lab", "Evidence"];
const cases = { balanced: "Balanced network", overstock: "Excess inventory", understock: "Low inventory", disruption: "Route disruption", false_alarm: "False alarm", recovery: "Recovery" };
const label = (key: string) => key.replaceAll("_", " ");
const display = (value: unknown): string => {
  if (value === null || value === undefined) return "Unavailable";
  if (typeof value === "number") return Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : "Unavailable";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

function Details({ value }: { value: Row }) {
  return <dl className="grid gap-3 sm:grid-cols-2">{Object.entries(value).map(([key, item]) => <div key={key} className="min-w-0 rounded-lg border border-slate-200 bg-white p-3">
    <dt className="text-xs uppercase tracking-wide text-slate-500">{label(key)}</dt>
    <dd className="mt-1 break-words text-sm text-slate-900">{typeof item === "object" && item !== null
      ? <details><summary className="cursor-pointer text-emerald-800">Inspect evidence</summary><pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(item, null, 2)}</pre></details>
      : display(item)}</dd>
  </div>)}</dl>;
}

function DataTable({ rows, empty }: { rows: Row[]; empty: string }) {
  if (!rows.length) return <p className="rounded border border-dashed p-5 text-sm text-slate-600">{empty}</p>;
  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));
  return <div className="overflow-auto rounded-lg border border-slate-200"><table className="w-full text-left text-sm">
    <thead className="bg-slate-100 text-xs uppercase text-slate-600"><tr>{keys.map((key) => <th className="whitespace-nowrap p-3" key={key}>{label(key)}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={i} className="border-t border-slate-200 bg-white">{keys.map((key) => <td key={key} className="max-w-xs p-3 align-top">
      {typeof row[key] === "object" && row[key] !== null ? <details><summary className="cursor-pointer text-emerald-800">Details</summary><pre className="max-h-60 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(row[key], null, 2)}</pre></details> : display(row[key])}
    </td>)}</tr>)}</tbody>
  </table></div>;
}

export default function ZaadPage() {
  const [active, setActive] = useState("Overview");
  const [demoCase, setDemoCase] = useState("balanced");
  const [report, setReport] = useState<Report | null>(null);
  const [source, setSource] = useState<Row | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [classification, setClassification] = useState("No operator data loaded");
  const [edge, setEdge] = useState("");

  async function loadDemo() {
    setBusy(true); setError(""); setReport(null);
    try {
      const result = await apiFetch<Demo>(`/api/zaad/demo?case=${encodeURIComponent(demoCase)}`);
      setReport(result.report); setSource(result.request); setDraft(JSON.stringify(result.request, null, 2));
      setClassification(result.classification); setEdge("");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load the demonstration."); }
    finally { setBusy(false); }
  }

  async function calculate(payload?: Row) {
    setBusy(true); setError(""); setReport(null);
    try {
      const request = payload ?? JSON.parse(draft);
      if (typeof request !== "object" || request === null || Array.isArray(request)) throw new Error("Import a canonical planning object.");
      const result = await apiFetch<Report>("/api/zaad/plan", { method: "POST", body: JSON.stringify(request) });
      setReport(result); setSource(request); setDraft(JSON.stringify(request, null, 2));
      setClassification(result.evidence_label + " · recommendation only, not measured savings");
    } catch (e) { setError(e instanceof Error ? e.message : "Request rejected. Check the input schema."); }
    finally { setBusy(false); }
  }

  async function importFile(file?: File) {
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { setError("JSON exceeds the 2 MiB request limit."); return; }
    try {
      const text = await file.text(); const value = JSON.parse(text);
      if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Expected a planning object.");
      setDraft(JSON.stringify(value, null, 2)); setReport(null); setSource(null);
      setClassification("Imported locally; not submitted or saved until you request a review");
      setActive("Scenario lab"); setError("");
    } catch { setError("This file is not valid canonical JSON."); }
  }

  function hypothetical(kind: "close" | "freight") {
    if (!source) return;
    const copy = JSON.parse(JSON.stringify(source)) as Row;
    copy.evidence_label = "SYNTHETIC";
    if (kind === "close") {
      if (!edge) { setError("Choose the actual network segment to close."); return; }
      copy.edges = (copy.edges as Row[]).map((e) => e.id === edge ? { ...e, available: false } : e);
    } else {
      // This changes quoted landed cost, not freight alone: do not imply the
      // canonical input has a freight-only component when it does not.
      copy.routes = (copy.routes as Row[]).map((r) => ({ ...r, landed_cost: Number(r.landed_cost) * 1.4 }));
    }
    void calculate(copy);
  }

  const networkEdges = Array.isArray(source?.edges) ? source.edges as Row[] : [];
  const routes = Array.isArray(source?.routes) ? source.routes as Row[] : [];
  const forecastRows = report?.forecasts ?? [];

  return <main className="min-h-screen bg-slate-50 p-4 text-slate-900 sm:p-8">
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="rounded-2xl bg-emerald-950 p-6 text-white sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="text-xs uppercase tracking-[.24em] text-emerald-300">ZAAD · decision workspace</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">Inventory with a plan for uncertainty.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-100">Right-size normal stock, trace supply exposure, and compare feasible alternatives. Every proposal stays under human review.</p></div>
          <a href="https://zaadsupply.com" className="text-sm underline underline-offset-4">zaadsupply.com ↗</a>
        </div>
        <p className="mt-6 inline-block rounded-full border border-emerald-700 px-3 py-1 text-xs">Experimental · no autonomous purchase orders</p>
      </header>

      <section className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4" aria-label="Data controls">
        <label className="text-sm">Synthetic case<select value={demoCase} onChange={(e) => setDemoCase(e.target.value)} className="mt-1 block rounded border border-slate-300 bg-white p-2">
          {Object.entries(cases).map(([value, title]) => <option key={value} value={value}>{title}</option>)}</select></label>
        <button onClick={loadDemo} disabled={busy} className="rounded bg-emerald-800 px-4 py-2 text-sm text-white disabled:opacity-50">{busy ? "Calculating…" : "Load demonstration"}</button>
        <label className="text-sm">Import canonical JSON<input type="file" accept=".json,application/json" disabled={busy} onChange={(e) => void importFile(e.target.files?.[0])} className="mt-1 block max-w-xs text-xs" /></label>
        <p className="w-full text-xs text-slate-500">{classification}. Data is not written to a training pool by this endpoint.</p>
      </section>
      {error && <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-900">{error}</div>}
      <div aria-live="polite" className="text-sm text-slate-600">{busy ? "Running bounded scenario comparisons. Prior results are hidden until the new review finishes." : report ? `${report.mode} · ${label(report.status)} · ${report.evidence_label}` : "Load a synthetic case or import your canonical request to begin."}</div>

      <nav aria-label="Decision views" className="flex flex-wrap gap-2 border-b border-slate-200 pb-4">
        {views.map((view) => <button key={view} onClick={() => setActive(view)} aria-current={active === view ? "page" : undefined}
          className={`rounded-full px-4 py-2 text-sm ${active === view ? "bg-emerald-900 text-white" : "bg-white text-slate-700 hover:bg-slate-200"}`}>{view}</button>)}
      </nav>

      <section className="space-y-5" aria-label={active}>
        <h2 className="text-xl font-semibold">{active}</h2>
        {active === "Overview" && (report ? <>
          <div className="grid gap-3 md:grid-cols-3">{[["Operating mode", report.mode], ["Decision", label(report.status)], ["Selected policy", label(report.selected_policy)]].map(([title, value]) => <div key={title} className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-xs uppercase tracking-wide text-slate-500">{title}</p><p className="mt-2 text-xl font-medium">{value}</p></div>)}</div>
          <ul className="list-disc space-y-2 pl-5 text-sm">{report.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>
          <Details value={report.economics} />
          <p className="text-sm text-slate-600">Predictions are scenario estimates. Current customer service and realized savings are not inferred from this simulation. Inventory release is not annual recurring profit.</p>
        </> : <p className="text-sm text-slate-600">No result yet. Nothing here is populated with invented operator metrics.</p>)}

        {active === "Inventory opportunities" && <>
          <p className="text-sm text-slate-600">Training-derived demand, protection and target trade-offs. Compare achieved scenario service with the requested target; a target is not a guarantee.</p>
          <DataTable rows={forecastRows} empty="No inventory forecasts loaded." />
          <h3 className="font-medium">Stock / service candidate frontier</h3><DataTable rows={report?.frontier ?? []} empty="No feasible frontier is available yet." />
        </>}

        {active === "Supply risk" && <>
          <p className="text-sm text-slate-600">Exposure follows explicit route segments. Shared segments can fail together; alternatives are not independent merely because their supplier names differ.</p>
          <DataTable rows={report?.routes ?? []} empty="No route-risk result loaded." />
          <DataTable rows={networkEdges} empty="Import a connected network graph to inspect exposures." />
          <p className="text-sm text-amber-900">Risk weights and scenario mixtures are not calibrated event probabilities unless separate operator evidence establishes that.</p>
        </>}

        {active === "Route alternatives" && <>
          <p className="text-sm text-slate-600">Alternatives require approved, unexpired quotes and a contiguous source-to-destination itinerary. Blocked or unreviewed options cannot supply phantom capacity.</p>
          <div className="grid gap-3 lg:grid-cols-2">{routes.map((route) => <article key={String(route.id)} className="rounded-xl border border-slate-200 bg-white p-4"><h3 className="font-medium">{String(route.id)} · {String(route.item)}</h3><p className="my-3 break-words text-sm text-emerald-900">{(route.edges as string[]).map((id) => { const e = networkEdges.find((x) => x.id === id); return e ? `${e.origin} → ${e.destination} (${e.mode})` : id; }).join(" / ")}</p><Details value={{ landed_cost: route.landed_cost, currency: source?.currency, capacity: route.capacity, approved: route.approved, compliance: route.compliance, valid_until: route.valid_until }} /></article>)}</div>
          {!routes.length && <p className="text-sm text-slate-500">No route quotes loaded.</p>}
        </>}

        {active === "Recommendations" && <>
          <div className="rounded border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">Review only. This page cannot place, cancel, reschedule or transmit a purchase order. Approval and ERP write-back are not enabled.</div>
          <h3 className="font-medium">Proposed review actions</h3><DataTable rows={(report?.actions ?? []) as unknown as Row[]} empty="No new orders recommended or no review loaded. Inspect the decision reason." />
          <h3 className="font-medium">Incumbent comparator</h3><DataTable rows={(report?.incumbent_actions ?? []) as unknown as Row[]} empty="No incumbent actions available." />
          {report && <ul className="list-disc space-y-2 pl-5 text-sm">{report.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul>}
        </>}

        {active === "Scenario lab" && <>
          <p className="text-sm text-slate-600">Counterfactuals are labelled synthetic, never external observations. Closing one segment affects only itineraries that use it. Delays require an explicit dated signal in the canonical request; we do not rewrite delivery history to manufacture a warning.</p>
          <div className="flex flex-wrap items-end gap-3"><label className="text-sm">Network segment<select value={edge} onChange={(e) => setEdge(e.target.value)} className="mt-1 block rounded border p-2"><option value="">Choose a segment</option>{networkEdges.map((e) => <option key={String(e.id)} value={String(e.id)}>{String(e.id)}</option>)}</select></label>
            <button disabled={busy || !source} onClick={() => hypothetical("close")} className="rounded border px-3 py-2 text-sm disabled:opacity-40">Test segment closure</button>
            <button disabled={busy || !source} onClick={() => hypothetical("freight")} className="rounded border px-3 py-2 text-sm disabled:opacity-40">Test all landed quotes +40%</button></div>
          <label className="block text-sm">Canonical request · inspect before submitting<textarea value={draft} onChange={(e) => { setDraft(e.target.value); setReport(null); setSource(null); }} spellCheck={false} className="mt-2 h-80 w-full rounded-lg border border-slate-300 bg-white p-3 font-mono text-xs" placeholder="Load a demonstration to see the complete versioned schema." /></label>
          <button onClick={() => void calculate()} disabled={busy || !draft} className="rounded bg-emerald-800 px-4 py-2 text-sm text-white disabled:opacity-40">Review this request</button>
        </>}

        {active === "Evidence" && (report ? <>
          <Details value={{ operator: report.operator_id, as_of: report.as_of, fingerprint: report.input_fingerprint, classification: report.evidence_label, approval_required: report.approval_required, executable_purchase_order: report.executable_purchase_order, ...report.evidence }} />
          <h3 className="font-medium">What this review does not establish</h3><ul className="list-disc space-y-2 pl-5 text-sm">{report.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul>
          <details className="rounded border bg-white p-4"><summary className="cursor-pointer text-sm">Complete report JSON</summary><pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(report, null, 2)}</pre></details>
        </> : <p className="text-sm text-slate-500">No decision evidence loaded. Missing data is not a normal-risk signal.</p>)}
      </section>
      <footer className="border-t border-slate-200 pt-4 text-xs text-slate-500">ZAAD · experimental decision support · zaadsupply.com · human review required</footer>
    </div>
  </main>;
}
