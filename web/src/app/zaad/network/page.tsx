"use client";

import Link from "next/link";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

type Row = Record<string, unknown>;
type Report = {
  status: string; mode: string; selected_policy: string; information_hash: string;
  evidence_label: string; version: string; reasons: string[]; limitations: string[];
  actions: Row[]; incumbent_actions: Row[]; cash: Row[]; service_frontier: Row[];
  forecasts: Row; eta: Row; stress_confirmation: Row[]; candidates: Row;
  confirmation: Row; recovery_guidance: Row | null;
};
function Evidence({ title, value }: { title: string; value: unknown }) {
  return <details className="rounded-xl border border-slate-200 bg-white p-4"><summary className="cursor-pointer font-medium">{title}</summary>
    <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words text-xs">{JSON.stringify(value, null, 2)}</pre></details>;
}
export default function NetworkPlanner() {
  const [draft, setDraft] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [decision, setDecision] = useState("");
  const [reason, setReason] = useState("");
  const [reviewStatus, setReviewStatus] = useState("");
  async function fixture(caseName: string) {
    setError(""); setReport(null); setDecision("");
    try { setDraft(JSON.stringify(await apiFetch(`/api/zaad/network/fixture?case=${caseName}`), null, 2)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load fixture."); }
  }
  async function run(save: boolean) {
    setBusy(true); setError(""); setDecision(""); setReviewStatus("");
    try {
      JSON.parse(draft);
      if (save) {
        const result = await apiFetch<{ decision_id: string; report: Report }>("/api/zaad/network/shadow", { method: "POST", body: draft });
        setReport(result.report); setDecision(result.decision_id);
      } else setReport(await apiFetch<Report>("/api/zaad/network/plan", { method: "POST", body: draft }));
    } catch (e) { setError(e instanceof Error ? e.message : "Planning failed."); }
    finally { setBusy(false); }
  }
  async function review(status: "APPROVED" | "REJECTED") {
    if (!report || !decision) return;
    setBusy(true); setError("");
    try {
      const result = await apiFetch<{ status: string }>(`/api/zaad/network/shadow/${encodeURIComponent(decision)}/review`, {
        method: "POST", body: JSON.stringify({ status, information_hash: report.information_hash, version: 1, reason }),
      });
      setReviewStatus(result.status);
    } catch (e) { setError(e instanceof Error ? e.message : "Review failed."); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-6xl space-y-6 px-4 py-8 text-slate-900">
    <header><Link href="/zaad" className="text-sm text-emerald-800">← ZAAD overview</Link>
      <h1 className="mt-3 text-3xl font-semibold">Network planning & resilience</h1>
      <p className="mt-2 max-w-3xl text-slate-600">Continuous purchasing, network inventory, contractual shipment changes, and dated liquidity. Review-only engineering build; no autonomous orders.</p></header>
    <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm">Synthetic fixtures are not customer validation. A retained incumbent is not certified safe. Inspect every service and stress failure below.</section>
    <section className="space-y-3"><h2 className="text-lg font-medium">1. Load the planning state</h2>
      <div className="flex flex-wrap gap-2">{["normal", "transfer", "substitution", "recovery", "cash", "understock"].map(c => <button disabled={busy} key={c} onClick={() => fixture(c)} className="rounded border bg-white px-3 py-2 text-sm capitalize disabled:opacity-50">{c} fixture</button>)}</div>
      <label className="block text-sm">Import canonical v2 JSON (nothing is sent until you run planning)
        <input type="file" accept="application/json,.json" className="mt-2 block" disabled={busy} onChange={async e => {
          const f = e.target.files?.[0]; if (!f) return;
          if (f.size > 2 * 1024 * 1024) { setError("Interactive snapshots are limited to 2 MiB."); return; }
          setDraft(await f.text()); setReport(null); setDecision("");
        }} /></label>
      <textarea aria-label="Planning state JSON" value={draft} onChange={e => setDraft(e.target.value)} className="h-64 w-full rounded-lg border bg-white p-3 font-mono text-xs" spellCheck={false} />
      <div className="flex flex-wrap gap-3"><button disabled={busy || !draft} onClick={() => run(false)} className="rounded-lg bg-emerald-900 px-4 py-2 text-white disabled:opacity-50">{busy ? "Computing…" : "Compare plans"}</button>
        <button disabled={busy || !draft} onClick={() => run(true)} className="rounded-lg border px-4 py-2 disabled:opacity-50">Save authenticated shadow decision</button></div>
      <p className="text-xs text-slate-500">Durable storage requires an authenticated operator and a dedicated shadow database. Never uploads to training.</p>
    </section>
    {error && <p role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">{error}</p>}
    {report && <section className="space-y-4"><h2 className="text-2xl font-semibold">{report.status.replaceAll("_", " ")}</h2>
      <p>{report.mode} · {report.selected_policy} · {report.evidence_label}</p>
      {report.reasons.map((r, i) => <p key={i} className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">{r}</p>)}
      <Evidence title="Purchase, source, route, transfer, cancellation and rescheduling actions" value={report.actions} />
      <Evidence title="Incumbent actions — same physical constraints" value={report.incumbent_actions} />
      <Evidence title="Customer service and individually achievable bounds" value={report.service_frontier} />
      <Evidence title="Cash, debt and period liquidity" value={report.cash} />
      <Evidence title="Out-of-model stress confirmation — including failures" value={report.stress_confirmation} />
      <Evidence title="Recovery guidance — not an approved exception to the gate" value={report.recovery_guidance} />
      <Evidence title="Forecast adaptation and censored ETA" value={{ forecasts: report.forecasts, eta: report.eta }} />
      <Evidence title="Solver candidates and confirmation economics" value={{ candidates: report.candidates, confirmation: report.confirmation }} />
      {decision && <section className="space-y-3 rounded-lg border p-4"><h3 className="font-semibold">Human review</h3><p className="break-all text-xs">Decision {decision}</p>
        <label className="block text-sm">Reason<input maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} className="mt-1 block w-full rounded border p-2" /></label>
        <div className="flex gap-3">{(["APPROVED", "REJECTED"] as const).map(s => <button key={s} onClick={() => review(s)} disabled={busy || !reason.trim() || !!reviewStatus || report.status !== "PENDING_REVIEW"} className="rounded border px-3 py-2 disabled:opacity-40">{s === "APPROVED" ? "Approve for shadow review" : "Reject"}</button>)}</div>
        <p>{reviewStatus || "Approval never transmits a purchase order. Expired or changed information sets require replanning."}</p></section>}
      <Evidence title="Limits and information-set provenance" value={{ version: report.version, hash: report.information_hash, limitations: report.limitations }} />
    </section>}
  </main>;
}
