"use client";

/**
 * The right-hand panel. First level answers only: what is this, what is
 * happening, what is affected, what does ZAAD recommend. Everything else
 * sits under "See details". In a simulation the same panel offers a few
 * plain presets, one Run button, and a CURRENT / DO NOTHING / ZAAD result.
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { X, Trash2, ChevronRight } from "lucide-react";
import { fmt, fmtPct } from "@/lib/api";
import { affectedBy, describe, leadRecommendation, shortName } from "@/lib/network/attention";
import type { NetworkEdge, NetworkNode, NetworkRecommendation, SelectionRef, ZaadState } from "@/lib/network/model";
import { EDGE_LABEL, KIND_LABEL, RISK_LABEL, STATE_LABEL, STATE_SENTENCE, STATE_TECHNICAL } from "@/lib/network/model";
import { OVERRIDE_SPECS, PRESETS, SEVERITY_LABEL, SPEC_BY_KIND, summarizeResult, type OverrideKind, type ScenarioMetrics, type Severity } from "@/lib/network/scenario";
import { useTwin } from "./store";

// ── Small pieces ──────────────────────────────────────────────────────────────

function Rows({ rows }: { rows: Array<[string, ReactNode | null | undefined, string?]> }) {
  return (
    <dl className="twin-rows">
      {rows.map(([k, v, why]) => (
        <div key={k} style={{ display: "contents" }}>
          <dt>{k}</dt>
          {v == null || v === "" ? <dd className="na" title={why}>{why ?? "not available"}</dd> : <dd>{v}</dd>}
        </div>
      ))}
    </dl>
  );
}

function Section({ title, children, aside }: { title: string; children: ReactNode; aside?: ReactNode }) {
  return <section className="twin-sec"><h4>{title}{aside}</h4>{children}</section>;
}

/** A collapsible detail block; `open` is driven by "See details". */
function Detail({ title, open, children, count }: { title: string; open: boolean; children: ReactNode; count?: number | string }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => { if (ref.current) ref.current.open = open; }, [open]);
  return (
    <details className="twin-detail" ref={ref}>
      <summary><ChevronRight size={14} className="chev" />{title}{count != null && count !== 0 && count !== "" ? <span className="count">{count}</span> : null}</summary>
      <div className="twin-detail-body">{children}</div>
    </details>
  );
}

function StatePill({ state }: { state: ZaadState }) {
  if (state === "LEAN") return null;
  return <span className={`state-pill st-${state}`}><i />{STATE_LABEL[state]}</span>;
}

function Spark({ points }: { points: Array<{ period: string; fill: number }> }) {
  const w = 300, h = 34;
  const min = Math.min(0.75, ...points.map((p) => p.fill)), max = 1;
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${(i / (points.length - 1)) * w},${h - ((p.fill - min) / (max - min)) * (h - 4) - 2}`).join(" ");
  return <svg className="twin-spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-label="Delivery reliability by week"><path d={d} fill="none" stroke="var(--accent)" strokeWidth={1.6} vectorEffect="non-scaling-stroke" /></svg>;
}

function Rec({ r, lead = false }: { r: NetworkRecommendation; lead?: boolean }) {
  return (
    <div className={`twin-rec st-${r.state} ${lead ? "lead" : ""}`}>
      <div className="act">{r.action}</div>
      <div className="why"><b>Why:</b> {r.rationale}</div>
      <div className="no"><b>If nothing is done:</b> {r.noAction}</div>
      {r.source === "illustrative" && <div className="src"><span className="twin-chip illus">Illustrative</span></div>}
      {r.source === "optimizer" && <div className="src"><span className="twin-chip ws">From your purchase plan</span></div>}
    </div>
  );
}

function NodeLink({ id, onPick }: { id: string; onPick: (r: SelectionRef) => void }) {
  const { index } = useTwin();
  const n = index.nodeById.get(id);
  return n ? <button className="twin-chip-btn" onClick={() => onPick({ type: "node", id })}>{n.name}</button> : null;
}
function EdgeLink({ id, onPick }: { id: string; onPick: (r: SelectionRef) => void }) {
  const { index } = useTwin();
  const e = index.edgeById.get(id);
  return e ? <button className="twin-chip-btn" onClick={() => onPick({ type: "edge", id })}>{e.name}</button> : null;
}

const na = (why: string) => why;

// ── First level: what / happening / affected / recommends ─────────────────────

function Affected({ target, type }: { target: NetworkNode | NetworkEdge; type: "node" | "edge" }) {
  const { model, index } = useTwin();
  const a = useMemo(() => affectedBy({ type, id: target.id }, model, index), [target.id, type, model, index]);
  const facts: Array<[string, string]> = [];
  if (a.skus.length) facts.push([String(a.skus.length), `SKU${a.skus.length === 1 ? "" : "s"}`]);
  if (a.openOrders) facts.push([String(a.openOrders), `open order${a.openOrders === 1 ? "" : "s"}`]);
  if (a.delayedShipments) facts.push([String(a.delayedShipments), `delayed shipment${a.delayedShipments === 1 ? "" : "s"}`]);
  if (a.customers.length) facts.push([String(a.customers.length), `customer group${a.customers.length === 1 ? "" : "s"}`]);
  if (!facts.length) return null;
  return (
    <div className="twin-facts">
      {facts.map(([v, l]) => <div key={l} className="twin-fact"><b>{v}</b><span>{l}</span></div>)}
    </div>
  );
}

function SelectionPanel({ target, type }: { target: NetworkNode | NetworkEdge; type: "node" | "edge" }) {
  const { model, index, state, dispatch, select } = useTwin();
  const [details, setDetails] = useState(false);   // the panel is keyed by target, so this resets on its own
  const node = type === "node" ? (target as NetworkNode) : null;
  const edge = type === "edge" ? (target as NetworkEdge) : null;
  const rec = leadRecommendation({ type, id: target.id }, model);
  const summary = describe({ type, id: target.id }, model, index);
  const pick = (r: SelectionRef) => select(r, true);
  const a = affectedBy({ type, id: target.id }, model, index);
  const m = node?.metrics ?? {};
  const ships = edge ? model.shipments.filter((s) => s.edgeId === edge.id) : [];
  const alts = node ? (node.alternatives ?? []).map((id) => index.nodeById.get(id)).filter(Boolean) : [];
  const altEdges = edge ? edge.alternatives.map((id) => index.edgeById.get(id)).filter(Boolean) : [];
  const evidence = [...target.risk.reasons, ...(edge?.disruptionEvidence ?? [])];
  const from = edge ? index.nodeById.get(edge.from) : null, to = edge ? index.nodeById.get(edge.to) : null;
  return (
    <>
      <div className="twin-panel-head">
        <div className="twin-panel-kind">{node ? KIND_LABEL[node.kind] : EDGE_LABEL[edge!.kind]} <StatePill state={target.state} /></div>
        <div className="twin-panel-title">{target.name}</div>
        <div className="twin-panel-sub">
          {node?.subtitle}{node?.geo?.precision === "approximate" ? <span className="faint"> · approximate location</span> : null}
          {edge && from && to ? <>{from.name} → {to.name}</> : null}
        </div>
        <button className="twin-icon twin-close" aria-label="Close" onClick={() => { select(null); dispatch({ type: "panel", open: false }); }}><X size={14} /></button>
      </div>
      <div className="twin-panel-body">
        <p className="twin-summary">{summary}</p>
        <Affected target={target} type={type} />
        {rec ? (
          <Section title="ZAAD recommends"><Rec r={rec} lead /></Section>
        ) : (
          <Section title="ZAAD recommends"><div className="twin-quiet">No action needed right now. {STATE_SENTENCE[target.state]}</div></Section>
        )}
        <div className="twin-actions">
          <button className="tbtn primary" onClick={() => setDetails((d) => !d)}>{details ? "Hide details" : "See details"}</button>
          {state.mode === "live" && <button className="tbtn ghost" onClick={() => dispatch({ type: "simulate:start", subject: { type, id: target.id } })}>Simulate disruption</button>}
        </div>

        <div className="twin-details">
          {node && (node.kind === "dc" || node.kind === "branch") && (
            <Detail title="Stock and service" open={details}>
              <Rows rows={[
                ["On hand", m.onHandUnits != null ? `${fmt(m.onHandUnits)} units` : null, na("needs an inventory snapshot")],
                ["Stock value", m.onHandValue != null ? `$${fmt(m.onHandValue)}` : null, na("needs unit costs")],
                ["On the way", m.inboundUnits != null ? `${fmt(m.inboundUnits)} units` : null, na("needs open orders")],
                ["Service target", m.serviceTarget != null ? fmtPct(m.serviceTarget, 1) : null, na("set when a plan is built")],
                ["Projected service", m.serviceProjected != null ? fmtPct(m.serviceProjected, 1) : null, na("appears once a plan is built")],
                ["Held locally", m.protection?.localUnits != null ? `${fmt(m.protection.localUnits)} units` : null, na("appears once a plan is built")],
                ["Held centrally for this site", m.protection?.pooledUnits != null ? `${fmt(m.protection.pooledUnits)} units` : null, na("appears once a plan is built")],
              ]} />
            </Detail>
          )}
          {node && node.kind === "supplier" && (
            <Detail title="Reliability and lead time" open={details}>
              <Rows rows={[
                ["Delivered, typical", m.fill?.mean != null ? fmtPct(m.fill.mean, 0) : null, na("needs delivery history")],
                ["Delivered, bad week (p10)", m.fill?.p10 != null ? fmtPct(m.fill.p10, 0) : null, na("needs delivery history")],
                ["Deliveries observed", m.fill?.n != null ? fmt(m.fill.n) : null, na("needs delivery history")],
                ["Lead time, typical", m.leadDays?.mean != null ? `${fmt(m.leadDays.mean)} days` : null, na("needs receipts")],
                ["Lead time, slow (p90)", m.leadDays?.p90 != null ? `${fmt(m.leadDays.p90)} days` : null, na("needs receipts")],
                ["Capacity per week", m.capacityPerWeek != null ? `${fmt(m.capacityPerWeek)} units` : null, na("not provided")],
              ]} />
              {m.fillHistory?.length ? <div style={{ marginTop: 10 }}><Spark points={m.fillHistory} /><div className="xsmall muted">Share delivered, by week</div></div> : null}
              {m.sharedFailureDomains?.length ? <div style={{ marginTop: 10 }}><div className="xsmall muted" style={{ marginBottom: 4 }}>Shares a single point of failure with</div><div className="twin-chips">{m.sharedFailureDomains.map((d) => <span className="twin-chip warn" key={d}>{d}</span>)}</div></div> : null}
            </Detail>
          )}
          {node && node.kind === "port" && (
            <Detail title="Port" open={details}>
              <Rows rows={[["Dwell, typical", m.dwellDays?.mean != null ? `${m.dwellDays.mean} days` : null, na("not provided")], ["Dwell, slow (p90)", m.dwellDays?.p90 != null ? `${m.dwellDays.p90} days` : null, na("not provided")], ["Congestion", m.congestion != null ? fmtPct(m.congestion, 0) : null, na("not provided")]]} />
              <div className="twin-chips" style={{ marginTop: 10 }}>{[...(index.inEdges.get(node.id) ?? []), ...(index.outEdges.get(node.id) ?? [])].map((e) => <EdgeLink key={e.id} id={e.id} onPick={pick} />)}</div>
            </Detail>
          )}
          {node && node.kind === "customer" && (
            <Detail title="Demand" open={details}>
              <Rows rows={[["Demand per week", m.demandPerWeek != null ? `${fmt(m.demandPerWeek)} units` : null, na("needs order history")], ["Service target", m.serviceTarget != null ? fmtPct(m.serviceTarget, 1) : null, na("not set")], ["Account type", m.tier ?? null, na("not set")]]} />
            </Detail>
          )}
          {edge && (
            <Detail title="Lane" open={details}>
              <Rows rows={[
                ["Usual transit", edge.leadDays.normal != null ? `${edge.leadDays.normal} days` : null, na("needs receipts")],
                ["Current transit", edge.leadDays.current != null ? `${edge.leadDays.current} days` : null, na("needs receipts against open orders")],
                ["Slow transit (p90)", edge.leadDays.p90 != null ? `${edge.leadDays.p90} days` : null, na("needs receipts")],
                ["Capacity per week", edge.capacityPerWeek != null ? `${fmt(edge.capacityPerWeek)} units` : null, na("not provided")],
                ["Transport cost", edge.transportCostPerUnit != null ? `$${edge.transportCostPerUnit.toFixed(2)} per unit` : null, na("not provided")],
              ]} />
            </Detail>
          )}
          <Detail title="Affected inventory" open={details} count={(m.shortages?.length ?? 0) + (m.excess?.length ?? 0) || a.skus.length}>
            {m.shortages?.length ? <ul className="twin-list">{m.shortages.map((s) => <li key={s.sku}><span className="twin-chip bad">short</span> {shortName(s.sku)}{s.units ? ` · ${fmt(s.units)} units` : ""} · {s.when}</li>)}</ul> : null}
            {m.excess?.length ? <ul className="twin-list" style={{ marginTop: 6 }}>{m.excess.map((s) => <li key={s.sku}><span className="twin-chip warn">excess</span> {shortName(s.sku)} · {fmt(s.units)} units · {s.weeksOfCover} weeks of cover</li>)}</ul> : null}
            {m.transferOpportunities?.length ? <ul className="twin-list" style={{ marginTop: 6 }}>{m.transferOpportunities.map((t) => <li key={t.sku + t.to}><span className="twin-chip">transfer</span> {fmt(t.units)} units of {shortName(t.sku)} to {t.to}</li>)}</ul> : null}
            {a.skus.length ? <div style={{ marginTop: 8 }}><div className="xsmall muted" style={{ marginBottom: 4 }}>SKUs on this {type === "edge" ? "lane" : KIND_LABEL[node!.kind].toLowerCase()}</div><div className="twin-chips">{a.skus.map((s) => <span className="twin-chip" key={s}>{s}</span>)}</div></div> : <div className="twin-quiet">No SKU list is available here.</div>}
            {a.stockNodes.length ? <div className="xsmall muted" style={{ marginTop: 8 }}>Stock downstream: {fmt(a.stockNodes.reduce((s, x) => s + (x.metrics.onHandUnits ?? 0), 0))} units across {a.stockNodes.map((x) => x.name).join(", ")}</div> : null}
          </Detail>
          <Detail title="Orders and shipments" open={details} count={(m.openPOs?.length ?? 0) + ships.length}>
            {m.openPOs?.length ? <ul className="twin-list">{m.openPOs.map((po) => <li key={po.id}><b>{po.id}</b> · {fmt(po.units)} units · {shortName(po.sku)} · <span className={po.status === "late" ? "twin-chip bad" : "twin-chip"}>{po.status.replace("_", " ")}{po.due ? ` · ${po.due}` : ""}</span></li>)}</ul> : null}
            {ships.length ? <ul className="twin-list">{ships.map((s) => <li key={s.id}><b>{s.ref}</b> · {fmt(s.units)} units · <span className={`twin-chip ${s.status === "delayed" ? "bad" : s.status === "customs" || s.status === "at_port" ? "warn" : ""}`}>{s.status.replace("_", " ")}</span>{s.eta ? ` · arriving ${s.eta}` : ""}{s.etaOriginal && s.etaOriginal !== s.eta ? ` (was ${s.etaOriginal})` : ""}</li>)}</ul> : null}
            {!m.openPOs?.length && !ships.length && <div className="twin-quiet">{node?.kind === "supplier" ? (m.openPOs ? "No open orders." : "Open orders are not available until purchase orders are uploaded.") : model.shipments.length ? "Nothing in transit here." : "Shipment positions are not part of the current upload."}</div>}
          </Detail>
          <Detail title="Alternatives" open={details} count={alts.length + altEdges.length}>
            {alts.length ? <div className="twin-chips">{alts.map((x) => <NodeLink key={x!.id} id={x!.id} onPick={pick} />)}</div> : null}
            {altEdges.map((alt) => {
              const dCost = alt!.transportCostPerUnit != null && edge!.transportCostPerUnit != null ? alt!.transportCostPerUnit - edge!.transportCostPerUnit : null;
              const dDays = alt!.leadDays.normal != null && edge!.leadDays.normal != null ? alt!.leadDays.normal - edge!.leadDays.normal : null;
              return <div key={alt!.id} style={{ marginBottom: 8 }}><EdgeLink id={alt!.id} onPick={pick} /><div className="xsmall muted" style={{ marginTop: 4 }}>{dDays != null ? `${dDays >= 0 ? "+" : ""}${dDays} days` : "transit time not known"} · {dCost != null ? `${dCost >= 0 ? "+" : "−"}$${Math.abs(dCost).toFixed(2)} per unit` : "extra cost not known"}</div></div>;
            })}
            {!alts.length && !altEdges.length && <div className="twin-quiet">No approved alternative is recorded.</div>}
          </Detail>
          <Detail title="Evidence" open={details} count={evidence.length}>
            {evidence.length ? <ul className="twin-list">{evidence.map((r) => <li key={r}>{r}</li>)}</ul> : <div className="twin-quiet">Nothing unusual has been observed.</div>}
            {target.risk.evidence.length ? <div className="twin-chips" style={{ marginTop: 8 }}>{target.risk.evidence.map((e) => <span className="twin-chip" key={e}>{e}</span>)}</div> : null}
          </Detail>
          <Detail title="Advanced" open={false}>
            <Rows rows={[
              ["Risk", `${RISK_LABEL[target.risk.level]} · ${Math.round(target.risk.score * 100)} / 100`],
              ["Engine state", `${STATE_TECHNICAL[target.state]} · ${STATE_LABEL[target.state]}`],
              ["Data source", model.provenance === "workspace" ? "Your workspace" : "Illustrative development data"],
            ]} />
            {target.missing?.length ? <div style={{ marginTop: 10 }}><div className="xsmall muted" style={{ marginBottom: 4 }}>Not yet in your data</div><ul className="twin-list">{target.missing.map((x) => <li key={x}>{x}</li>)}</ul></div> : null}
          </Detail>
        </div>
      </div>
    </>
  );
}

// ── Simulation ────────────────────────────────────────────────────────────────

const money = (v: number | null) => (v == null ? null : `$${fmt(v)}`);
const cmpClass = (v: number | null, base: number | null, lowerIsBetter: boolean) => {
  if (v == null || base == null || Math.abs(v - base) < 1e-9) return "";
  return (lowerIsBetter ? v < base : v > base) ? "good" : "bad";
};

function Presets({ subject, type, onDone }: { subject: NetworkNode | NetworkEdge; type: "node" | "edge"; onDone?: () => void }) {
  const { dispatch } = useTwin();
  const presets = PRESETS.filter((p) => p.appliesTo(subject, type));
  const [chosen, setChosen] = useState(presets[0]?.id ?? "");
  const [severity, setSeverity] = useState<Severity>("moderate");
  const [advanced, setAdvanced] = useState(false);
  const specs = OVERRIDE_SPECS.filter((s) => s.appliesTo(subject, type));
  const [kind, setKind] = useState<OverrideKind>(specs[0]?.kind ?? "lead_time_delay");
  const spec = SPEC_BY_KIND[kind];
  const [value, setValue] = useState<number>(spec?.input?.initial ?? 0);
  const preset = presets.find((p) => p.id === chosen) ?? presets[0];
  if (!preset) return null;
  const run = () => {
    if (advanced) dispatch({ type: "override:add", overrides: [{ kind, targetType: type, targetId: subject.id, value: spec.input ? value : undefined }] });
    else dispatch({ type: "override:add", overrides: preset.build(subject.id, type, severity) });
    onDone?.();
  };
  return (
    <div className="twin-presets">
      {!advanced && (
        <>
          <div className="twin-preset-list" role="radiogroup" aria-label="What happens">
            {presets.map((p) => (
              <label key={p.id} className={`twin-preset ${chosen === p.id ? "on" : ""}`}>
                <input type="radio" name="preset" value={p.id} checked={chosen === p.id} onChange={() => setChosen(p.id)} />
                <span className="l">{p.label}</span><span className="d">{p.description}</span>
              </label>
            ))}
          </div>
          {preset.hasSeverity && (
            <div className="twin-seg small" role="group" aria-label="How severe">
              {(["mild", "moderate", "severe"] as Severity[]).map((s) => <button key={s} aria-pressed={severity === s} onClick={() => setSeverity(s)}>{SEVERITY_LABEL[s]}</button>)}
            </div>
          )}
        </>
      )}
      {advanced && (
        <div className="twin-advanced">
          <select aria-label="Change type" value={kind} onChange={(e) => { setKind(e.target.value as OverrideKind); setValue(SPEC_BY_KIND[e.target.value as OverrideKind].input?.initial ?? 0); }}>
            {specs.map((s) => <option key={s.kind} value={s.kind}>{s.label}</option>)}
          </select>
          <div className="xsmall muted" style={{ marginTop: 4 }}>{spec.hint}</div>
          {spec.input && (
            <div className="twin-sim-row">
              <input type="range" aria-label={spec.label} min={spec.input.min} max={spec.input.max} step={spec.input.step} value={value} onChange={(e) => setValue(Number(e.target.value))} />
              <span className="val">{spec.input.format(value)}</span>
            </div>
          )}
        </div>
      )}
      <div className="twin-actions">
        <button className="tbtn primary" onClick={run}>Run simulation</button>
        <button className="tbtn ghost" onClick={() => setAdvanced((v) => !v)}>{advanced ? "Back to presets" : "Advanced scenario"}</button>
      </div>
    </div>
  );
}

function SimulationPanel() {
  const { state, dispatch, model, index, scenario, engine, select } = useTwin();
  const subjectRef = state.subject ?? state.selection;
  const subject = subjectRef ? (subjectRef.type === "node" ? index.nodeById.get(subjectRef.id) : index.edgeById.get(subjectRef.id)) : null;
  const [adding, setAdding] = useState(false);
  const [more, setMore] = useState(false);
  const c = scenario?.comparison ?? null;
  const summary = scenario ? summarizeResult(scenario) : null;
  const row = (label: string, key: keyof ScenarioMetrics, fmtv: (v: number | null) => ReactNode, lowerIsBetter: boolean) => {
    const cur = c!.current[key], dn = c!.doNothing[key], z = c!.zaad[key];
    return (
      <div key={key} style={{ display: "contents" }}>
        <span className="l">{label}</span>
        <span className={`v ${cur == null ? "na" : ""}`}>{cur == null ? "—" : fmtv(cur)}</span>
        <span className={`v ${dn == null ? "na" : cmpClass(dn, cur, lowerIsBetter)}`}>{dn == null ? "—" : fmtv(dn)}</span>
        <span className={`v ${z == null ? "na" : cmpClass(z, cur, lowerIsBetter)}`}>{z == null ? "—" : fmtv(z)}</span>
      </div>
    );
  };
  const exposedCustomers = scenario ? model.nodes.filter((n) => n.kind === "customer" && scenario.exposed.nodes.has(n.id)) : [];
  return (
    <>
      <div className="twin-panel-head sim">
        <div className="twin-panel-kind">Simulation</div>
        <div className="twin-panel-title">{subject ? subject.name : "Choose something to disrupt"}</div>
        <div className="twin-panel-sub">{subject ? "What if something goes wrong here? Nothing here changes your data." : "Select a supplier, port, lane or site on the network."}</div>
        <button className="twin-icon twin-close" aria-label="Exit simulation" onClick={() => dispatch({ type: "simulate:exit" })}><X size={14} /></button>
      </div>
      <div className="twin-panel-body">
        {subject && (!state.overrides.length || adding) && (
          <Presets subject={subject} type={subjectRef!.type} onDone={() => setAdding(false)} />
        )}
        {state.overrides.length > 0 && !adding && (
          <>
            {summary && <p className="twin-summary">{summary}</p>}
            {exposedCustomers.length > 0 && <div className="twin-facts"><div className="twin-fact"><b>{exposedCustomers.length}</b><span>customer group{exposedCustomers.length === 1 ? "" : "s"} exposed</span></div><div className="twin-fact"><b>{scenario!.exposed.nodes.size}</b><span>sites affected</span></div></div>}
            {c && (
              <div className="twin-cmp">
                <span /><span className="h">Current</span><span className="h">Do nothing</span><span className="h zaad">ZAAD</span>
                {row("Service", "service", (v) => fmtPct(v, 1), false)}
                {row("Inventory", "inventoryUnits", (v) => `${fmt(v)} u`, true)}
                {row("Expected shortage", "shortageUnits", (v) => `${fmt(v)} u`, true)}
                {row("Extra cost", "expediteCost", money, true)}
                {more && row("Total modelled cost", "totalCost", money, true)}
              </div>
            )}
            {scenario && scenario.recommendations.length > 0 && (
              <Section title="ZAAD's response">
                {scenario.recommendations.map((r) => <div key={r.id}><button className="twin-chip-btn" onClick={() => select({ type: r.targetType, id: r.targetId }, true)}>{r.targetType === "node" ? index.nodeById.get(r.targetId)?.name : index.edgeById.get(r.targetId)?.name}</button><Rec r={r} /></div>)}
              </Section>
            )}
            <Section title="Changes in this simulation" aside={<button className="twin-chip-btn" onClick={() => setAdding(true)}>Add another</button>}>
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
            </Section>
            <div className="twin-actions">
              <button className="tbtn ghost" onClick={() => setMore((v) => !v)}>{more ? "Less detail" : "More detail"}</button>
              <button className="tbtn ghost" onClick={() => dispatch({ type: "simulate:exit" })}>Exit simulation</button>
            </div>
            {more && scenario && <div className="twin-quiet" style={{ marginTop: 8 }}>{scenario.notes.join(" ")}</div>}
            <div className="twin-simlabel">{scenario?.label ?? engine.label}</div>
          </>
        )}
      </div>
    </>
  );
}

// ── Overview when nothing is selected ─────────────────────────────────────────

function Overview() {
  const { model, areas, status, select, load, dispatch } = useTwin();
  const pick = (r: SelectionRef) => select(r, true);
  const attention = areas.filter((a) => a.level === "attention"), watch = areas.filter((a) => a.level === "watch");
  return (
    <>
      <div className="twin-panel-head">
        <div className="twin-panel-kind">{model.name}</div>
        <div className="twin-panel-title">{status.headline}</div>
        <div className="twin-panel-sub">{model.nodes.filter((n) => n.kind === "supplier").length} suppliers · {model.nodes.filter((n) => n.kind === "dc" || n.kind === "branch").length} sites · {model.nodes.filter((n) => n.kind === "customer").length} customer groups</div>
        <button className="twin-icon twin-close" aria-label="Close" onClick={() => dispatch({ type: "panel", open: false })}><X size={14} /></button>
      </div>
      <div className="twin-panel-body">
        {attention.length > 0 && (
          <Section title="Needs attention">
            {attention.map((a) => (
              <button key={a.id} className={`twin-area st-${a.lead.type === "node" ? model.nodes.find((n) => n.id === a.lead.id)?.state : model.edges.find((e) => e.id === a.lead.id)?.state}`} onClick={() => pick(a.lead)}>
                <div className="t">{a.title}</div>
                <div className="s">{a.summary.split(". ")[0]}.</div>
                {a.recommendation && <div className="r">ZAAD: {a.recommendation.action}</div>}
              </button>
            ))}
          </Section>
        )}
        {watch.length > 0 && (
          <Section title="Worth watching">
            {watch.map((a) => <button key={a.id} className="twin-area quiet" onClick={() => pick(a.lead)}><div className="t">{a.title}</div><div className="s">{a.summary.split(". ")[0]}.</div></button>)}
          </Section>
        )}
        {!areas.length && <div className="twin-quiet">Supply is stable everywhere. Select any supplier, lane or site to see how it is doing.</div>}
        <Detail title="About this data" open={false}>
          <ul className="twin-list">{model.notes.map((n) => <li key={n}>{n}</li>)}{load.workspaceError && <li>{load.workspaceError}</li>}</ul>
        </Detail>
      </div>
    </>
  );
}

export function IntelligencePanel() {
  const { state, index } = useTwin();
  const sel = state.selection;
  const node = sel?.type === "node" ? index.nodeById.get(sel.id) : undefined;
  const edge = sel?.type === "edge" ? index.edgeById.get(sel.id) : undefined;
  if (state.mode === "simulate") return <aside className="twin-panel" aria-label="Simulation"><SimulationPanel /></aside>;
  if (!node && !edge) return <aside className="twin-panel" aria-label="Network overview"><Overview /></aside>;
  const target = (node ?? edge)!;
  return (
    <aside className="twin-panel" aria-label={`${node ? KIND_LABEL[node.kind] : EDGE_LABEL[edge!.kind]} details`}>
      <SelectionPanel key={target.id} target={target} type={node ? "node" : "edge"} />
    </aside>
  );
}
