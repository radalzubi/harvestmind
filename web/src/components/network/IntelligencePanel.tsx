"use client";

/**
 * The right-hand intelligence panel. One selection, everything ZAAD knows
 * about it, and a plain "not available" for everything it does not. In
 * SIMULATE it also hosts the controls for changing the selected node or lane.
 */
import { useMemo, useState, type ReactNode } from "react";
import { X, Trash2 } from "lucide-react";
import { fmt, fmtPct } from "@/lib/api";
import type { NetworkEdge, NetworkNode, NetworkRecommendation, SelectionRef, ZaadState } from "@/lib/network/model";
import { EDGE_LABEL, KIND_LABEL, STATE_LABEL } from "@/lib/network/model";
import { OVERRIDE_SPECS, SPEC_BY_KIND, type OverrideKind, type ScenarioMetrics } from "@/lib/network/scenario";
import { useTwin } from "./store";

const NA = ({ why }: { why?: string }) => <dd className="na" title={why}>not available</dd>;

function Rows({ rows }: { rows: Array<[string, ReactNode | null | undefined, string?]> }) {
  return (
    <dl className="twin-rows">
      {rows.map(([k, v, why]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{k}</dt>
          {v == null || v === "" ? <NA why={why} /> : <dd>{v}</dd>}
        </div>
      ))}
    </dl>
  );
}

function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return <section className="twin-sec"><h4>{title}{aside}</h4>{children}</section>;
}

function StatePill({ state }: { state: ZaadState }) {
  return <span className={`state-pill st-${state}`}><i />{STATE_LABEL[state]}</span>;
}

function Spark({ points }: { points: Array<{ period: string; fill: number }> }) {
  const w = 300, h = 34;
  const min = Math.min(0.75, ...points.map((p) => p.fill)), max = 1;
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${(i / (points.length - 1)) * w},${h - ((p.fill - min) / (max - min)) * (h - 4) - 2}`).join(" ");
  return (
    <svg className="twin-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-label="Fill history">
      <path d={d} fill="none" stroke="var(--accent)" strokeWidth={1.6} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function Rec({ r }: { r: NetworkRecommendation }) {
  return (
    <div className={`twin-rec st-${r.state}`}>
      <div className="act">{r.action}</div>
      <div className="why">{r.rationale}</div>
      <div className="no"><b>If nothing is done:</b> {r.noAction}</div>
      <div className="src"><span className={`twin-chip ${r.source === "optimizer" ? "ws" : "illus"}`}>{r.source === "optimizer" ? "ZAAD plan" : "Illustrative"}</span></div>
    </div>
  );
}

function Missing({ items }: { items?: string[] }) {
  if (!items?.length) return null;
  return <Section title="Not in the data"><div className="twin-missing">{items.map((m) => <div key={m}>· {m}</div>)}</div></Section>;
}

function NodeLink({ id, onPick }: { id: string; onPick: (r: SelectionRef) => void }) {
  const { index } = useTwin();
  const n = index.nodeById.get(id);
  if (!n) return null;
  return <button className="twin-chip-btn" onClick={() => onPick({ type: "node", id })}>{n.name}</button>;
}
function EdgeLink({ id, onPick }: { id: string; onPick: (r: SelectionRef) => void }) {
  const { index } = useTwin();
  const e = index.edgeById.get(id);
  if (!e) return null;
  return <button className="twin-chip-btn" onClick={() => onPick({ type: "edge", id })}>{e.name}</button>;
}

// ── Simulation controls ───────────────────────────────────────────────────────

function SimulateControls({ target, type }: { target: NetworkNode | NetworkEdge; type: "node" | "edge" }) {
  const { state, dispatch } = useTwin();
  const specs = OVERRIDE_SPECS.filter((s) => s.appliesTo(target, type));
  const [kindState, setKind] = useState<OverrideKind>(specs[0]?.kind ?? "lead_time_delay");
  // a kind chosen for an earlier target may not apply here
  const kind = specs.some((s) => s.kind === kindState) ? kindState : specs[0]?.kind ?? kindState;
  const spec = SPEC_BY_KIND[kind] ?? specs[0];
  const [value, setValue] = useState<number>(spec?.input?.initial ?? 0);
  const mine = state.overrides.filter((o) => o.targetId === target.id && o.targetType === type);
  if (!spec) return null;
  const pick = (k: OverrideKind) => { setKind(k); setValue(SPEC_BY_KIND[k].input?.initial ?? 0); };
  return (
    <div className="twin-sim" role="group" aria-label="Simulate a change">
      <h4>Simulate a change here</h4>
      <select aria-label="Change type" value={kind} onChange={(e) => pick(e.target.value as OverrideKind)}>
        {specs.map((s) => <option key={s.kind} value={s.kind}>{s.label}</option>)}
      </select>
      <div className="xsmall muted" style={{ marginTop: 4 }}>{spec.hint}</div>
      {spec.input && (
        <div className="twin-sim-row">
          <input type="range" aria-label={spec.label} min={spec.input.min} max={spec.input.max} step={spec.input.step} value={value} onChange={(e) => setValue(Number(e.target.value))} />
          <span className="val">{spec.input.format(value)}</span>
        </div>
      )}
      <div className="twin-sim-row">
        <button className="tbtn primary" style={{ height: 28 }} onClick={() => dispatch({ type: "override:add", override: { id: `${kind}_${target.id}_${Date.now()}`, kind, targetType: type, targetId: target.id, value: spec.input ? value : undefined } })}>
          Apply change
        </button>
      </div>
      {mine.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {mine.map((o) => {
            const s = SPEC_BY_KIND[o.kind];
            return (
              <div className="twin-ov" key={o.id}>
                <span className="k">{s.label}{o.value != null && s.input ? ` ${s.input.format(o.value)}` : ""}</span>
                <button aria-label={`Remove ${s.label}`} onClick={() => dispatch({ type: "override:remove", id: o.id })}><Trash2 size={13} /></button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Scenario summary (CURRENT / DO NOTHING / ZAAD) ────────────────────────────

const money = (v: number | null) => (v == null ? null : `$${fmt(v)}`);
const cmpClass = (v: number | null, base: number | null, lowerIsBetter: boolean) => {
  if (v == null || base == null || Math.abs(v - base) < 1e-9) return "";
  return (lowerIsBetter ? v < base : v > base) ? "good" : "bad";
};

export function ScenarioSummary() {
  const { scenario, state, dispatch, index, engine } = useTwin();
  if (!scenario) return null;
  const c = scenario.comparison;
  const row = (label: string, key: keyof ScenarioMetrics, fmtv: (v: number | null) => ReactNode, lowerIsBetter: boolean) => {
    const cur = c!.current[key], dn = c!.doNothing[key], z = c!.zaad[key];
    return (
      <div key={key} style={{ display: "contents" }}>
        <span className="l">{label}</span>
        <span className={`v ${cur == null ? "na" : ""}`}>{cur == null ? "n/a" : fmtv(cur)}</span>
        <span className={`v ${dn == null ? "na" : cmpClass(dn, cur, lowerIsBetter)}`}>{dn == null ? "n/a" : fmtv(dn)}</span>
        <span className={`v ${z == null ? "na" : cmpClass(z, cur, lowerIsBetter)}`}>{z == null ? "n/a" : fmtv(z)}</span>
      </div>
    );
  };
  return (
    <Section title="Scenario" aside={state.overrides.length > 0 && <button className="twin-chip-btn" onClick={() => dispatch({ type: "override:clear" })}>Reset</button>}>
      <div className="twin-chips" style={{ marginBottom: 10 }}>
        <span className={`twin-chip ${scenario.source === "optimizer" ? "ws" : "illus"}`}>{engine.label}</span>
      </div>
      {state.overrides.length === 0 && <div className="small muted">Select a node or lane, then apply a change. LIVE data is never altered.</div>}
      {state.overrides.map((o) => {
        const s = SPEC_BY_KIND[o.kind];
        const t = o.targetType === "node" ? index.nodeById.get(o.targetId)?.name : index.edgeById.get(o.targetId)?.name;
        return (
          <div className="twin-ov" key={o.id}>
            <span className="t">{t}</span>
            <span className="k">{s.label}{o.value != null && s.input ? ` ${s.input.format(o.value)}` : ""}</span>
            <button aria-label={`Remove ${s.label} on ${t}`} onClick={() => dispatch({ type: "override:remove", id: o.id })}><Trash2 size={13} /></button>
          </div>
        );
      })}
      {c && (
        <div className="twin-cmp" style={{ marginTop: 12 }}>
          <span /><span className="h">Current</span><span className="h">Do nothing</span><span className="h zaad">ZAAD</span>
          {row("Service", "service", (v) => fmtPct(v, 1), false)}
          {row("Inventory", "inventoryUnits", (v) => `${fmt(v)} u`, true)}
          {row("Shortage exposure", "shortageUnits", (v) => `${fmt(v)} u`, true)}
          {row("Expedite cost", "expediteCost", money, true)}
          {row("Total modelled cost", "totalCost", money, true)}
        </div>
      )}
      <div className="xsmall muted" style={{ marginTop: 10, lineHeight: 1.45 }}>{scenario.label}</div>
    </Section>
  );
}

// ── Node and lane details ─────────────────────────────────────────────────────

function RiskBlock({ risk }: { risk: NetworkNode["risk"] }) {
  return (
    <Section title="Risk" aside={<span className={`twin-chip ${risk.level === "critical" ? "bad" : risk.level === "high" || risk.level === "medium" ? "warn" : ""}`}>{risk.level} · {Math.round(risk.score * 100)}</span>}>
      <div className="twin-risk-bar"><i style={{ width: `${Math.round(risk.score * 100)}%` }} /></div>
      {risk.reasons.length > 0 && <ul className="twin-list" style={{ marginTop: 8 }}>{risk.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
      {risk.evidence.length > 0 && <div className="twin-chips" style={{ marginTop: 8 }}>{risk.evidence.map((e) => <span className="twin-chip" key={e}>{e}</span>)}</div>}
    </Section>
  );
}

function Recs({ id }: { id: string }) {
  const { model } = useTwin();
  const recs = model.recommendations.filter((r) => r.targetId === id);
  return (
    <Section title="ZAAD recommends">
      {recs.length ? recs.map((r) => <Rec key={r.id} r={r} />) : <div className="small muted">No recommendation targets this item in the current read.</div>}
    </Section>
  );
}

function NodeDetails({ n }: { n: NetworkNode }) {
  const { index, select } = useTwin();
  const m = n.metrics;
  const down = index.downstream(n.id), up = index.upstream(n.id);
  const downNodes = [...down.nodes].map((id) => index.nodeById.get(id)!).filter(Boolean);
  const customers = downNodes.filter((x) => x.kind === "customer");
  const stock = downNodes.filter((x) => x.kind === "dc" || x.kind === "branch");
  const downstreamOnHand = stock.reduce((s, x) => s + (x.metrics.onHandUnits ?? 0), 0);
  const pick = (r: SelectionRef) => select(r, true);
  return (
    <>
      {n.kind === "supplier" && (
        <>
          <Section title="Fill and lead time">
            <Rows rows={[
              ["Fill, mean", m.fill?.mean != null ? fmtPct(m.fill.mean, 0) : null, "needs delivery history"],
              ["Fill, downside p10", m.fill?.p10 != null ? fmtPct(m.fill.p10, 0) : null],
              ["Fill, upside p90", m.fill?.p90 != null ? fmtPct(m.fill.p90, 0) : null],
              ["Deliveries observed", m.fill?.n != null ? fmt(m.fill.n) : null],
              ["Lead time, mean", m.leadDays?.mean != null ? `${fmt(m.leadDays.mean)} d` : null],
              ["Lead time, p90", m.leadDays?.p90 != null ? `${fmt(m.leadDays.p90)} d` : null],
              ["Capacity per week", m.capacityPerWeek != null ? `${fmt(m.capacityPerWeek)} u` : null],
            ]} />
            {m.fillHistory?.length ? <div style={{ marginTop: 10 }}><Spark points={m.fillHistory} /><div className="xsmall muted">Fill by week, last {m.fillHistory.length}</div></div> : null}
          </Section>
          <Section title="Open purchase orders">
            {m.openPOs?.length ? <ul className="twin-list">{m.openPOs.map((po) => <li key={po.id}><b>{po.id}</b> · {fmt(po.units)} u · {po.sku} · <span className={po.status === "late" ? "twin-chip bad" : "twin-chip"}>{po.status.replace("_", " ")}{po.due ? ` · ${po.due}` : ""}</span></li>)}</ul>
              : <div className="small muted">{m.openPOs ? "No open POs." : "Open POs are not available."}</div>}
          </Section>
          <Section title="Shared failure domains">
            {m.sharedFailureDomains?.length ? <div className="twin-chips">{m.sharedFailureDomains.map((d) => <span className="twin-chip warn" key={d}>{d}</span>)}</div> : <div className="small muted">None identified.</div>}
          </Section>
        </>
      )}
      {n.kind === "port" && (
        <Section title="Port">
          <Rows rows={[["Dwell, mean", m.dwellDays?.mean != null ? `${m.dwellDays.mean} d` : null], ["Dwell, p90", m.dwellDays?.p90 != null ? `${m.dwellDays.p90} d` : null], ["Congestion", m.congestion != null ? fmtPct(m.congestion, 0) : null]]} />
          <div className="twin-chips" style={{ marginTop: 10 }}>
            {[...(index.inEdges.get(n.id) ?? []), ...(index.outEdges.get(n.id) ?? [])].map((e) => <EdgeLink key={e.id} id={e.id} onPick={pick} />)}
          </div>
        </Section>
      )}
      {(n.kind === "dc" || n.kind === "branch") && (
        <>
          <Section title="Stock and service">
            <Rows rows={[
              ["On hand", m.onHandUnits != null ? `${fmt(m.onHandUnits)} u` : null, "needs an inventory snapshot"],
              ["On-hand value", m.onHandValue != null ? `$${fmt(m.onHandValue)}` : null],
              ["Inbound", m.inboundUnits != null ? `${fmt(m.inboundUnits)} u` : null, "needs open purchase orders"],
              ["Service target", m.serviceTarget != null ? fmtPct(m.serviceTarget, 1) : null, "set when a plan is built"],
              ["Projected service", m.serviceProjected != null ? fmtPct(m.serviceProjected, 1) : null, "comes from a built plan"],
              ["Local protection", m.protection?.localUnits != null ? `${fmt(m.protection.localUnits)} u` : null],
              ["Pooled protection", m.protection?.pooledUnits != null ? `${fmt(m.protection.pooledUnits)} u` : null],
            ]} />
          </Section>
          <Section title="Shortages and excess">
            {m.shortages?.length ? <ul className="twin-list">{m.shortages.map((s) => <li key={s.sku}><span className="twin-chip bad">short</span> {s.sku}{s.units ? ` · ${fmt(s.units)} u` : ""} · {s.when}</li>)}</ul> : <div className="small muted">No projected shortage.</div>}
            {m.excess?.length ? <ul className="twin-list" style={{ marginTop: 6 }}>{m.excess.map((s) => <li key={s.sku}><span className="twin-chip warn">excess</span> {s.sku} · {fmt(s.units)} u · {s.weeksOfCover} wk cover</li>)}</ul> : null}
            {m.transferOpportunities?.length ? <ul className="twin-list" style={{ marginTop: 6 }}>{m.transferOpportunities.map((t) => <li key={t.sku + t.to}><span className="twin-chip">transfer</span> {fmt(t.units)} u of {t.sku} to {t.to}</li>)}</ul> : null}
          </Section>
        </>
      )}
      {n.kind === "customer" && (
        <Section title="Demand">
          <Rows rows={[["Demand per week", m.demandPerWeek != null ? `${fmt(m.demandPerWeek)} u` : null], ["Service target", m.serviceTarget != null ? fmtPct(m.serviceTarget, 1) : null], ["Tier", m.tier ?? null]]} />
        </Section>
      )}
      <Section title="Dependencies">
        <Rows rows={[
          ["Feeds", downNodes.length ? `${downNodes.length} node${downNodes.length === 1 ? "" : "s"}` : "nothing downstream"],
          ["Customers affected", customers.length ? customers.map((c) => c.name).join(", ") : n.kind === "customer" ? "—" : null, "no customer nodes downstream"],
          ["Downstream stock", stock.length ? `${fmt(downstreamOnHand)} u` : null],
          ["Sources upstream", up.nodes.size ? [...up.nodes].map((id) => index.nodeById.get(id)?.name).filter(Boolean).join(", ") : n.kind === "supplier" ? "—" : null],
        ]} />
        {n.skus.length > 0 && <div className="twin-chips" style={{ marginTop: 8 }}>{n.skus.map((s) => <span className="twin-chip" key={s}>{s}</span>)}</div>}
      </Section>
      <Section title="Alternatives">
        {n.alternatives?.length ? <div className="twin-chips">{n.alternatives.map((a) => <NodeLink key={a} id={a} onPick={pick} />)}</div> : <div className="small muted">No approved alternative recorded.</div>}
      </Section>
    </>
  );
}

function EdgeDetails({ e }: { e: NetworkEdge }) {
  const { index, model, select } = useTwin();
  const pick = (r: SelectionRef) => select(r, true);
  const ships = model.shipments.filter((s) => s.edgeId === e.id);
  const down = index.downstream(e.to);
  const downNodes = [...down.nodes, e.to].map((id) => index.nodeById.get(id)!).filter(Boolean);
  const customers = downNodes.filter((x) => x.kind === "customer");
  const stock = downNodes.filter((x) => x.kind === "dc" || x.kind === "branch");
  const onHand = stock.reduce((s, x) => s + (x.metrics.onHandUnits ?? 0), 0);
  const from = index.nodeById.get(e.from), to = index.nodeById.get(e.to);
  const upSuppliers = [...index.upstream(e.from).nodes, e.from].map((id) => index.nodeById.get(id)).filter((x): x is NetworkNode => !!x && x.kind === "supplier");
  const altSuppliers = [...new Set(upSuppliers.flatMap((s) => s.alternatives ?? []))];
  return (
    <>
      <Section title="Lane">
        <div className="twin-chips" style={{ marginBottom: 8 }}>
          {from && <NodeLink id={from.id} onPick={pick} />}<span className="muted">→</span>{to && <NodeLink id={to.id} onPick={pick} />}
        </div>
        <Rows rows={[
          ["Normal lead time", e.leadDays.normal != null ? `${e.leadDays.normal} d` : null, "needs receipts against POs"],
          ["Current lead time", e.leadDays.current != null ? `${e.leadDays.current} d` : null, "needs receipts against open POs"],
          ["Lead time p90", e.leadDays.p90 != null ? `${e.leadDays.p90} d` : null],
          ["Capacity per week", e.capacityPerWeek != null ? `${fmt(e.capacityPerWeek)} u` : null],
          ["Transport cost", e.transportCostPerUnit != null ? `$${e.transportCostPerUnit.toFixed(2)} / u` : null, "not in the upload"],
        ]} />
      </Section>
      <Section title="Shipments on this lane">
        {ships.length ? <ul className="twin-list">{ships.map((s) => <li key={s.id}><b>{s.ref}</b> · {fmt(s.units)} u · <span className={`twin-chip ${s.status === "delayed" ? "bad" : s.status === "customs" || s.status === "at_port" ? "warn" : ""}`}>{s.status.replace("_", " ")}</span>{s.eta ? ` · ETA ${s.eta}` : ""}{s.etaOriginal && s.etaOriginal !== s.eta ? ` (was ${s.etaOriginal})` : ""}</li>)}</ul>
          : <div className="small muted">{model.shipments.length ? "Nothing in transit here." : "Shipment positions are not available."}</div>}
      </Section>
      <Section title="Disruption evidence">
        {e.disruptionEvidence?.length ? <ul className="twin-list">{e.disruptionEvidence.map((d) => <li key={d}>{d}</li>)}</ul> : <div className="small muted">No disruption evidence on this lane.</div>}
      </Section>
      <Section title="Downstream">
        <Rows rows={[
          ["Customers affected", customers.length ? customers.map((c) => c.name).join(", ") : null, "no customer nodes downstream"],
          ["Downstream stock", stock.length ? `${fmt(onHand)} u` : null, "no stock positions downstream"],
        ]} />
        {e.skus.length > 0 && <div className="twin-chips" style={{ marginTop: 8 }}>{e.skus.map((s) => <span className="twin-chip" key={s}>{s}</span>)}</div>}
      </Section>
      <Section title="Alternatives">
        {e.alternatives.length ? e.alternatives.map((a) => {
          const alt = index.edgeById.get(a);
          if (!alt) return null;
          const dCost = alt.transportCostPerUnit != null && e.transportCostPerUnit != null ? alt.transportCostPerUnit - e.transportCostPerUnit : null;
          const dDays = alt.leadDays.normal != null && e.leadDays.normal != null ? alt.leadDays.normal - e.leadDays.normal : null;
          return (
            <div key={a} style={{ marginBottom: 8 }}>
              <EdgeLink id={a} onPick={pick} />
              <div className="xsmall muted" style={{ marginTop: 4 }}>
                {dDays != null ? `${dDays >= 0 ? "+" : ""}${dDays} d` : "lead time n/a"} · {dCost != null ? `${dCost >= 0 ? "+" : "−"}$${Math.abs(dCost).toFixed(2)} / u incremental` : "incremental cost n/a"}
              </div>
            </div>
          );
        }) : <div className="small muted">No alternative lane recorded.</div>}
        {altSuppliers.length > 0 && <div style={{ marginTop: 6 }}><div className="xsmall muted" style={{ marginBottom: 4 }}>Alternative suppliers upstream</div><div className="twin-chips">{altSuppliers.map((a) => <NodeLink key={a} id={a} onPick={pick} />)}</div></div>}
      </Section>
    </>
  );
}

// ── Overview when nothing is selected ─────────────────────────────────────────

function Overview() {
  const { model, state, select, load } = useTwin();
  const pick = (r: SelectionRef) => select(r, true);
  const exposed = useMemo(() => [
    ...model.nodes.filter((n) => n.state !== "LEAN").map((n) => ({ ref: { type: "node" as const, id: n.id }, name: n.name, state: n.state, score: n.risk.score })),
    ...model.edges.filter((e) => e.state !== "LEAN").map((e) => ({ ref: { type: "edge" as const, id: e.id }, name: e.name, state: e.state, score: e.risk.score })),
  ].sort((a, b) => b.score - a.score), [model]);
  const counts = useMemo(() => { const c: Record<ZaadState, number> = { LEAN: 0, PROTECT: 0, ALLOCATE: 0, RECOVER: 0 }; for (const n of model.nodes) c[n.state]++; return c; }, [model]);
  return (
    <>
      <div className="twin-panel-head">
        <div className="twin-panel-kind">{model.provenance === "workspace" ? <span className="twin-chip ws">Workspace data</span> : <span className="twin-chip illus">Illustrative development data</span>}</div>
        <div className="twin-panel-title">{model.name}</div>
        <div className="twin-panel-sub">{model.nodes.length} nodes · {model.edges.length} lanes · as of {model.asOf}</div>
      </div>
      <div className="twin-panel-body">
        {state.mode === "simulate" && <ScenarioSummary />}
        <Section title="State">
          <div className="twin-chips">{(Object.keys(counts) as ZaadState[]).map((s) => <span key={s} className={`state-pill st-${s}`}><i />{STATE_LABEL[s]} {counts[s]}</span>)}</div>
        </Section>
        <Section title="Exposed now">
          {exposed.length ? <ul className="twin-list">{exposed.map((x) => <li key={x.ref.type + x.ref.id}><button className="twin-chip-btn" onClick={() => pick(x.ref)}>{x.name}</button> <span className={`state-pill st-${x.state}`} style={{ marginLeft: 6 }}><i />{STATE_LABEL[x.state]}</span></li>)}</ul> : <div className="small muted">Nothing outside LEAN.</div>}
        </Section>
        <Section title="ZAAD recommends">
          {model.recommendations.length ? model.recommendations.map((r) => (
            <div key={r.id}><button className="twin-chip-btn" style={{ marginTop: 8 }} onClick={() => pick({ type: r.targetType, id: r.targetId })}>{r.targetType === "node" ? "Node" : "Lane"} · {r.targetId}</button><Rec r={r} /></div>
          )) : <div className="small muted">No recommendations in this read. Build a purchase plan to attach the optimizer&apos;s orders.</div>}
        </Section>
        <Section title="Data">
          <ul className="twin-list">{model.notes.map((n) => <li key={n}>{n}</li>)}{load.workspaceError && <li>{load.workspaceError}</li>}</ul>
        </Section>
      </div>
    </>
  );
}

export function IntelligencePanel() {
  const { state, index, dispatch, select } = useTwin();
  const sel = state.selection;
  const node = sel?.type === "node" ? index.nodeById.get(sel.id) : undefined;
  const edge = sel?.type === "edge" ? index.edgeById.get(sel.id) : undefined;
  if (!node && !edge) return <aside className="twin-panel" aria-label="Network overview"><Overview /></aside>;
  const target = (node ?? edge)!;
  const kind = node ? KIND_LABEL[node.kind] : EDGE_LABEL[edge!.kind];
  const isIllus = false;
  return (
    <aside className="twin-panel" aria-label={`${kind} details`}>
      <div className="twin-panel-head" style={{ position: "sticky" }}>
        <div className="twin-panel-kind">{kind} <StatePill state={target.state} />{isIllus && <span className="twin-chip illus">Illustrative</span>}</div>
        <div className="twin-panel-title">{target.name}</div>
        {node?.subtitle && <div className="twin-panel-sub">{node.subtitle}{node.geo?.precision === "approximate" ? " · position approximate" : ""}{!node.geo ? " · no coordinates" : ""}</div>}
        {edge && <div className="twin-panel-sub">{EDGE_LABEL[edge.kind]}{edge.path ? "" : " · no route geometry"}</div>}
        <button className="twin-icon twin-close" aria-label="Close details" onClick={() => { select(null); dispatch({ type: "panel", open: true }); }}><X size={14} /></button>
      </div>
      <div className="twin-panel-body">
        {state.mode === "simulate" && <SimulateControls key={target.id} target={target} type={node ? "node" : "edge"} />}
        {state.mode === "simulate" && <ScenarioSummary />}
        <RiskBlock risk={target.risk} />
        {node ? <NodeDetails n={node} /> : <EdgeDetails e={edge!} />}
        <Recs id={target.id} />
        <Missing items={target.missing} />
      </div>
    </aside>
  );
}
