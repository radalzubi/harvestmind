"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardBody, CardHead, InfoBanner, PageHeader, PageLoading, PageError } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type Outlook = { risk: number; quality: number; reasons: string[]; missing: string[] };
type State = {
  mode: string;
  portfolio: { probabilities: Record<string, number>; dominant: string; stress: number; reasons: string[]; data_quality: number };
  posture: { commit_window: number; cvar_lambda: number; autonomy: number; scenario_width: number; candidates: string[] };
  outlooks: Record<string, Outlook>;
  replan_triggers: string[];
};

export default function StatePage() {
  const [s, setS] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { apiFetch<State>("/fmcg/state").then(setS).catch((e) => setError(e.message)); }, []);
  if (error && /upload/i.test(error)) {
    return (
      <div className="page">
        <PageHeader title="State and lanes" sub="Appears once your history is loaded" />
        <InfoBanner kind="info" title="Nothing to read yet">
          {error} <Link href="/upload">Go to upload</Link>.
        </InfoBanner>
      </div>
    );
  }
  if (error) return <div className="page"><PageError error={error} /></div>;
  if (!s) return <PageLoading message="Reading your operating state…" />;
  const probs = Object.entries(s.portfolio.probabilities).sort((a, b) => b[1] - a[1]).slice(0, 5);
  return (
    <div className="page">
      <PageHeader title="State and lanes" sub="What the engine believes about your operation right now, and how much freedom it gives the optimizer" />
      <InfoBanner kind="info" title={`Mode: ${s.mode}`}>
        {s.mode === "EFFICIENCY" && "Calm: the optimizer minimises ordinary cost with no bound around your current orders; the evidence gate still protects your policy."}
        {s.mode === "BALANCED" && "Something is moving: the optimizer stays within a bound around your current orders and weighs the downside more."}
        {s.mode === "PROTECTION" && "Disrupted: tight bound around your current orders, strong downside weighting, one-week commitments."}
      </InfoBanner>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <Card>
          <CardHead title="Regime" sub={`Dominant ${s.portfolio.dominant} · stress ${s.portfolio.stress.toFixed(2)} · data quality ${s.portfolio.data_quality.toFixed(2)}`} />
          <CardBody>
            {probs.map(([k, v]) => (
              <div key={k} style={{ display: "grid", gridTemplateColumns: "160px 1fr 48px", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <span>{k}</span>
                <div style={{ background: "var(--line-soft)", height: 8, borderRadius: 4 }}><div style={{ width: `${Math.round(v * 100)}%`, background: "var(--accent)", height: 8, borderRadius: 4 }} /></div>
                <span style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{Math.round(v * 100)}%</span>
              </div>
            ))}
            <ul style={{ marginTop: 12, paddingLeft: 18, color: "var(--ink-600)" }}>{s.portfolio.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          </CardBody>
        </Card>
        <Card>
          <CardHead title="Posture" sub="What the state changes in the optimizer" />
          <CardBody>
            <dl style={{ display: "grid", gridTemplateColumns: "1fr auto", rowGap: 6, margin: 0 }}>
              <dt>Executable commitment</dt><dd style={{ margin: 0 }}>{s.posture.commit_window} week{s.posture.commit_window === 1 ? "" : "s"}</dd>
              <dt>Downside weight</dt><dd style={{ margin: 0 }}>{s.posture.cvar_lambda.toFixed(2)}</dd>
              <dt>Scenario width</dt><dd style={{ margin: 0 }}>{s.posture.scenario_width.toFixed(2)}</dd>
              <dt>Autonomy</dt><dd style={{ margin: 0 }}>{s.posture.autonomy.toFixed(2)}</dd>
              <dt>Candidates admitted</dt><dd style={{ margin: 0 }}>{s.posture.candidates.join(", ")}</dd>
            </dl>
          </CardBody>
        </Card>
      </div>
      <Card style={{ marginTop: 16 }}>
        <CardHead title="Supply lanes" sub="Forward-looking risk from public shipping and logistics feeds, with how much evidence sits behind it" />
        <CardBody>
          {Object.keys(s.outlooks).length === 0 && <p style={{ color: "var(--ink-500)" }}>Tag your suppliers with a route (for example aqaba, red_sea, hormuz) in the supplier list to see lane risk.</p>}
          {Object.entries(s.outlooks).map(([lane, o]) => (
            <div key={lane} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <b>{lane}</b><span>risk {Math.round(o.risk * 100)}% · evidence {o.quality.toFixed(2)}</span>
              </div>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "var(--ink-600)" }}>{o.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              {o.missing.length > 0 && <div style={{ fontSize: 12, color: "var(--ink-500)", marginTop: 4 }}>Missing feeds: {o.missing.join(", ")}</div>}
            </div>
          ))}
        </CardBody>
      </Card>
      <Card style={{ marginTop: 16 }}>
        <CardHead title="When to replan" />
        <CardBody><ul style={{ margin: 0, paddingLeft: 18 }}>{s.replan_triggers.map((t) => <li key={t}>{t}</li>)}</ul></CardBody>
      </Card>
    </div>
  );
}
