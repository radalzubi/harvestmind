"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardBody, CardHead, InfoBanner, PageHeader, PageLoading, PageError } from "@/components/ui";
import { apiFetch } from "@/lib/api";

type Outlook = { risk: number; quality: number; reasons: string[]; missing: string[] };
type Plain = {
  headline: string; regime: string; regime_reasons: string[]; posture: string[];
  lanes: Array<{ lane: string; sentence: string; reasons: string[]; missing: string[] }>;
  triggers: string[]; glossary: Record<string, string>;
};
type State = {
  mode: string;
  portfolio: { probabilities: Record<string, number>; dominant: string; stress: number; reasons: string[]; data_quality: number };
  posture: { commit_window: number; cvar_lambda: number; autonomy: number; scenario_width: number; candidates: string[] };
  outlooks: Record<string, Outlook>;
  replan_triggers: string[];
  plain?: Plain;
};

const REGIME: Record<string, string> = {
  NORMAL: "Normal", CALM: "Calm", WATCH: "Worth watching", PORT_DISRUPTION: "Port disruption", ROUTE_DISRUPTION: "Route disruption",
  SUPPLIER_DEGRADED: "Supplier slipping", SUPPLIER_FAILURE: "Supplier failing", DEMAND_VOLATILE: "Swingy demand",
  DEMAND_SHIFT: "Demand shifted", RECOVERY: "Recovering", CAPACITY_CONSTRAINED: "Capacity squeeze",
};
const MODE_LABEL: Record<string, string> = { EFFICIENCY: "Calm", BALANCED: "Something is moving", PROTECTION: "Disrupted" };

export default function StatePage() {
  const [s, setS] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showNumbers, setShowNumbers] = useState(false);
  useEffect(() => { apiFetch<State>("/fmcg/state").then(setS).catch((e) => setError(e.message)); }, []);
  if (error && /upload/i.test(error)) {
    return (
      <div className="page">
        <PageHeader title="State and lanes" sub="Appears once your history is loaded" />
        <InfoBanner kind="info" title="Nothing to read yet">{error} <Link href="/upload">Go to upload</Link>.</InfoBanner>
      </div>
    );
  }
  if (error) return <div className="page"><PageError error={error} /></div>;
  if (!s) return <PageLoading message="Reading your operating state…" />;
  const p = s.plain;
  const probs = Object.entries(s.portfolio.probabilities).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const level = (x: number, lo: number, hi: number, w: [string, string, string]) => (x < lo ? w[0] : x < hi ? w[1] : w[2]);

  return (
    <div className="page">
      <PageHeader title="State and lanes" sub="What the engine believes about your operation right now, in plain words. Use Explain, top right, to ask questions." />
      <InfoBanner kind={s.mode === "PROTECTION" ? "danger" : s.mode === "BALANCED" ? "warn" : "info"} title={`Right now: ${MODE_LABEL[s.mode] ?? s.mode}`}>
        {p?.headline}
      </InfoBanner>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <Card>
          <CardHead title="How things look" sub={`Most likely: ${REGIME[s.portfolio.dominant] ?? s.portfolio.dominant}`} />
          <CardBody>
            <p style={{ marginTop: 0 }}>{p?.regime}</p>
            {probs.map(([k, v]) => (
              <div key={k} style={{ display: "grid", gridTemplateColumns: "150px 1fr 44px", gap: 8, alignItems: "center", marginBottom: 6 }}>
                <span>{REGIME[k] ?? k}</span>
                <div style={{ background: "var(--line-soft)", height: 8, borderRadius: 4 }}><div style={{ width: `${Math.round(v * 100)}%`, background: "var(--accent)", height: 8, borderRadius: 4 }} /></div>
                <span style={{ textAlign: "end", fontVariantNumeric: "tabular-nums" }}>{Math.round(v * 100)}%</span>
              </div>
            ))}
            {p && p.regime_reasons.length > 0 && (
              <>
                <div className="small strong" style={{ marginTop: 12 }}>What is driving it</div>
                <ul style={{ margin: "4px 0 0", paddingInlineStart: 18, color: "var(--ink-600)" }}>{p.regime_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              </>
            )}
          </CardBody>
        </Card>
        <Card>
          <CardHead title="What the optimizer may do" sub="The state sets how much freedom it gets" />
          <CardBody>
            <ul style={{ margin: 0, paddingInlineStart: 18, display: "grid", gap: 8 }}>{(p?.posture ?? []).map((line) => <li key={line}>{line}</li>)}</ul>
            <button className="tbtn ghost small" style={{ marginTop: 12 }} onClick={() => setShowNumbers((v) => !v)}>{showNumbers ? "Hide the raw numbers" : "Show the raw numbers"}</button>
            {showNumbers && (
              <dl className="small" style={{ display: "grid", gridTemplateColumns: "1fr auto", rowGap: 4, margin: "10px 0 0", color: "var(--ink-600)" }}>
                <dt>Firm weeks</dt><dd style={{ margin: 0 }}>{s.posture.commit_window}</dd>
                <dt>Caution weight</dt><dd style={{ margin: 0 }}>{s.posture.cvar_lambda.toFixed(2)} ({level(s.posture.cvar_lambda, 0.35, 0.65, ["low", "moderate", "high"])})</dd>
                <dt>Range of futures</dt><dd style={{ margin: 0 }}>{s.posture.scenario_width.toFixed(2)}</dd>
                <dt>Freedom to change orders</dt><dd style={{ margin: 0 }}>{s.posture.autonomy.toFixed(2)}</dd>
                <dt>Stress</dt><dd style={{ margin: 0 }}>{s.portfolio.stress.toFixed(2)}</dd>
                <dt>Data quality</dt><dd style={{ margin: 0 }}>{s.portfolio.data_quality.toFixed(2)}</dd>
              </dl>
            )}
          </CardBody>
        </Card>
      </div>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="Your supply lanes" sub="Forward-looking risk from public shipping and logistics feeds, and how much evidence sits behind it" />
        <CardBody>
          {Object.keys(s.outlooks).length === 0 && <p style={{ color: "var(--ink-500)", margin: 0 }}>Tag your suppliers with a route (for example aqaba, red_sea, hormuz) in the supplier list to see lane risk.</p>}
          {(p?.lanes ?? []).map((lane) => (
            <div key={lane.lane} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
              <b>{lane.sentence}</b>
              <ul style={{ margin: "6px 0 0", paddingInlineStart: 18, color: "var(--ink-600)" }}>{lane.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              {lane.missing.length > 0 && <div className="xsmall muted" style={{ marginTop: 4 }}>No data yet from: {lane.missing.join(", ")}</div>}
            </div>
          ))}
        </CardBody>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="When the plan is redone early" sub="Any of these, and the next review is brought forward" />
        <CardBody><ul style={{ margin: 0, paddingInlineStart: 18, display: "grid", gap: 6 }}>{(p?.triggers ?? s.replan_triggers).map((t) => <li key={t}>{t}</li>)}</ul></CardBody>
      </Card>

      {p && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Words used here" />
          <CardBody>
            <dl style={{ margin: 0, display: "grid", gap: 8 }}>
              {Object.entries(p.glossary).map(([k, v]) => (<div key={k}><dt className="strong">{k}</dt><dd className="small" style={{ margin: "2px 0 0", color: "var(--ink-600)" }}>{v}</dd></div>))}
            </dl>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
