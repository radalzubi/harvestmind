/**
 * Simulation: an ephemeral scenario layer over a live model.
 *
 * `ScenarioOverride`s describe what the user changed. A `ScenarioEngine`
 * turns the live model plus overrides into a derived view, the exposed set,
 * recommendations and a CURRENT / DO NOTHING / ZAAD comparison. The live
 * model is never mutated: engines return new objects for whatever changed.
 *
 * Two engines exist. `illustrativeEngine` is a development demo adapter with
 * a deterministic, clearly labelled propagation; it is not the optimizer.
 * `optimizerEngine` is the hook for the real ZAAD scenario API and reports
 * itself unavailable until that endpoint exists. Both satisfy the same
 * interface, so swapping is a one-line change in `pickEngine`.
 */
import type { NetworkIndex } from "./graph";
import type { NetworkEdge, NetworkModel, NetworkNode, NetworkRecommendation, RiskState, ZaadState } from "./model";
import { riskLevel } from "./model";

export type OverrideKind =
  | "supplier_fill" | "lead_time_delay" | "supplier_unavailable" | "port_closure" | "lane_unavailable"
  | "lane_capacity" | "freight_cost" | "demand_change" | "route_reopened" | "alternate_supplier_enabled";

export interface ScenarioOverride {
  id: string;
  kind: OverrideKind;
  targetType: "node" | "edge";
  targetId: string;
  /** Numeric parameter where the kind has one (fill rate, days, factor). */
  value?: number;
}

export interface OverrideSpec {
  kind: OverrideKind;
  label: string;
  hint: string;
  appliesTo: (t: NetworkNode | NetworkEdge, type: "node" | "edge") => boolean;
  input?: { min: number; max: number; step: number; unit: string; initial: number; format: (v: number) => string };
}

const isKind = (k: NetworkNode["kind"][]) => (t: NetworkNode | NetworkEdge, type: "node" | "edge") => type === "node" && k.includes((t as NetworkNode).kind);
const isEdge = (t: NetworkNode | NetworkEdge, type: "node" | "edge") => type === "edge";
const pct = (v: number) => `${Math.round(v * 100)}%`;

export const OVERRIDE_SPECS: OverrideSpec[] = [
  { kind: "supplier_fill", label: "Fill rate", hint: "Share of ordered units this supplier delivers", appliesTo: isKind(["supplier"]),
    input: { min: 0.3, max: 1, step: 0.05, unit: "", initial: 0.7, format: pct } },
  { kind: "lead_time_delay", label: "Lead-time delay", hint: "Extra days on every arrival", appliesTo: (t, type) => type === "edge" || isKind(["supplier", "port"])(t, type),
    input: { min: 1, max: 45, step: 1, unit: "d", initial: 7, format: (v) => `+${v} d` } },
  { kind: "supplier_unavailable", label: "Supplier unavailable", hint: "No deliveries until reopened", appliesTo: isKind(["supplier"]) },
  { kind: "port_closure", label: "Port closure", hint: "Nothing lands here", appliesTo: isKind(["port"]) },
  { kind: "lane_unavailable", label: "Lane unavailable", hint: "No flow on this lane", appliesTo: isEdge },
  { kind: "lane_capacity", label: "Capacity reduction", hint: "Lane carries a fraction of normal", appliesTo: isEdge,
    input: { min: 0.1, max: 0.9, step: 0.1, unit: "", initial: 0.5, format: (v) => `${pct(v)} of normal` } },
  { kind: "freight_cost", label: "Freight cost increase", hint: "Transport cost multiplier", appliesTo: isEdge,
    input: { min: 1.1, max: 3, step: 0.1, unit: "×", initial: 1.5, format: (v) => `×${v.toFixed(1)}` } },
  { kind: "demand_change", label: "Demand change", hint: "Multiplier on demand downstream of here", appliesTo: isKind(["dc", "branch", "customer"]),
    input: { min: 0.5, max: 2, step: 0.1, unit: "×", initial: 1.3, format: (v) => `×${v.toFixed(1)}` } },
  { kind: "route_reopened", label: "Route reopened", hint: "Lane returns to its normal lead time", appliesTo: isEdge },
  { kind: "alternate_supplier_enabled", label: "Alternate supplier enabled", hint: "Approve the listed alternative for this supplier's SKUs", appliesTo: isKind(["supplier"]) },
];

export const SPEC_BY_KIND = Object.fromEntries(OVERRIDE_SPECS.map((s) => [s.kind, s])) as Record<OverrideKind, OverrideSpec>;

// ── Plain-language presets ────────────────────────────────────────────────────

export type Severity = "mild" | "moderate" | "severe";
export const SEVERITY_LABEL: Record<Severity, string> = { mild: "Mild", moderate: "Moderate", severe: "Severe" };

export interface ScenarioPreset {
  id: string;
  label: string;
  description: string;
  appliesTo: (t: NetworkNode | NetworkEdge, type: "node" | "edge") => boolean;
  /** Presets with a magnitude take a severity; the others are on/off. */
  build: (targetId: string, type: "node" | "edge", severity: Severity) => Omit<ScenarioOverride, "id">[];
  hasSeverity: boolean;
}

const sev = <T,>(s: Severity, mild: T, moderate: T, severe: T) => (s === "mild" ? mild : s === "severe" ? severe : moderate);

export const PRESETS: ScenarioPreset[] = [
  { id: "supplier_delayed", label: "Supplier delayed", description: "Every delivery from this supplier arrives late", appliesTo: isKind(["supplier"]), hasSeverity: true,
    build: (id, type, s) => [{ kind: "lead_time_delay", targetType: type, targetId: id, value: sev(s, 3, 7, 14) }] },
  { id: "supplier_short", label: "Deliveries falling short", description: "The supplier ships only part of what is ordered", appliesTo: isKind(["supplier"]), hasSeverity: true,
    build: (id, type, s) => [{ kind: "supplier_fill", targetType: type, targetId: id, value: sev(s, 0.85, 0.7, 0.5) }] },
  { id: "supplier_unavailable", label: "Supplier unavailable", description: "No deliveries until further notice", appliesTo: isKind(["supplier"]), hasSeverity: false,
    build: (id, type) => [{ kind: "supplier_unavailable", targetType: type, targetId: id }] },
  { id: "port_closed", label: "Port closed", description: "Nothing lands here", appliesTo: isKind(["port"]), hasSeverity: false,
    build: (id, type) => [{ kind: "port_closure", targetType: type, targetId: id }] },
  { id: "port_congested", label: "Port congested", description: "Containers wait longer to clear", appliesTo: isKind(["port"]), hasSeverity: true,
    build: (id, type, s) => [{ kind: "lead_time_delay", targetType: type, targetId: id, value: sev(s, 2, 5, 10) }] },
  { id: "route_disrupted", label: "Route disrupted", description: "Transit takes longer than usual", appliesTo: isEdge, hasSeverity: true,
    build: (id, type, s) => [{ kind: "lead_time_delay", targetType: type, targetId: id, value: sev(s, 4, 10, 21) }] },
  { id: "route_unavailable", label: "Route unavailable", description: "No flow on this lane", appliesTo: isEdge, hasSeverity: false,
    build: (id, type) => [{ kind: "lane_unavailable", targetType: type, targetId: id }] },
  { id: "freight_up", label: "Freight cost up", description: "Transport on this lane gets more expensive", appliesTo: isEdge, hasSeverity: true,
    build: (id, type, s) => [{ kind: "freight_cost", targetType: type, targetId: id, value: sev(s, 1.25, 1.5, 2) }] },
  { id: "demand_spike", label: "Demand spike", description: "Customers order more than usual", appliesTo: isKind(["dc", "branch", "customer"]), hasSeverity: true,
    build: (id, type, s) => [{ kind: "demand_change", targetType: type, targetId: id, value: sev(s, 1.15, 1.3, 1.6) }] },
  { id: "demand_drop", label: "Demand drop", description: "Customers order less than usual", appliesTo: isKind(["dc", "branch", "customer"]), hasSeverity: true,
    build: (id, type, s) => [{ kind: "demand_change", targetType: type, targetId: id, value: sev(s, 0.85, 0.7, 0.5) }] },
];

export interface ScenarioMetrics {
  service: number | null;
  inventoryUnits: number | null;
  shortageUnits: number | null;
  expediteCost: number | null;
  totalCost: number | null;
}

export interface ScenarioResult {
  view: NetworkModel;
  exposed: { nodes: Set<string>; edges: Set<string> };
  recommendations: NetworkRecommendation[];
  comparison: { current: ScenarioMetrics; doNothing: ScenarioMetrics; zaad: ScenarioMetrics } | null;
  source: "optimizer" | "illustrative";
  label: string;
  notes: string[];
}

export interface ScenarioEngine {
  id: "illustrative" | "optimizer";
  label: string;
  available: boolean;
  evaluate(model: NetworkModel, overrides: ScenarioOverride[], index: NetworkIndex): ScenarioResult;
}

// ── Illustrative demo adapter ─────────────────────────────────────────────────

function seedSeverity(o: ScenarioOverride, target: NetworkNode | NetworkEdge): { severity: number; recovering: boolean; cost: number } {
  const v = o.value ?? 0;
  switch (o.kind) {
    case "supplier_fill": {
      const base = (target as NetworkNode).metrics.fill?.mean ?? 0.95;
      return { severity: Math.max(0, Math.min(1, (base - v) / base * 1.6)), recovering: false, cost: 0 };
    }
    case "lead_time_delay": {
      const normal = "leadDays" in target && target.leadDays && "normal" in target.leadDays ? (target.leadDays as { normal: number | null }).normal ?? 7
        : (target as NetworkNode).metrics.leadDays?.mean ?? 7;
      return { severity: Math.max(0, Math.min(1, v / (normal + 10))), recovering: false, cost: 0 };
    }
    case "supplier_unavailable": case "port_closure": case "lane_unavailable": return { severity: 1, recovering: false, cost: 0 };
    case "lane_capacity": return { severity: Math.max(0, Math.min(1, 1 - v)), recovering: false, cost: 0 };
    case "freight_cost": return { severity: Math.max(0, Math.min(0.4, (v - 1) * 0.25)), recovering: false, cost: v - 1 };
    case "demand_change": return { severity: Math.max(0, Math.min(1, Math.abs(v - 1) * 1.2)), recovering: v < 1, cost: 0 };
    case "route_reopened": case "alternate_supplier_enabled": return { severity: 0, recovering: true, cost: 0 };
  }
}

function withRisk(base: RiskState, severity: number, reason: string): RiskState {
  const score = Math.max(base.score, severity);
  return { level: riskLevel(score), score, reasons: severity > 0 ? [reason, ...base.reasons] : base.reasons, evidence: base.evidence };
}

function stateFor(live: ZaadState, severity: number, recovering: boolean): ZaadState {
  if (recovering) return "RECOVER";
  if (severity >= 0.6) return "ALLOCATE";
  if (severity >= 0.25) return live === "ALLOCATE" ? "ALLOCATE" : "PROTECT";
  return live;
}

export const illustrativeEngine: ScenarioEngine = {
  id: "illustrative",
  label: "Development demo adapter",
  available: true,
  evaluate(model, overrides, index) {
    const nodeSev = new Map<string, { s: number; why: string; recovering: boolean }>();
    const edgeSev = new Map<string, { s: number; why: string; recovering: boolean }>();
    const bump = (m: typeof nodeSev, id: string, s: number, why: string, recovering: boolean) => {
      const cur = m.get(id);
      if (!cur || s > cur.s || (recovering && s === cur.s)) m.set(id, { s, why, recovering: cur ? cur.recovering || recovering : recovering });
    };
    const recs: NetworkRecommendation[] = [];
    let expedite = 0, shortageUnits = 0, serviceDrop = 0, freightExtra = 0;
    const demand = (id: string) => {
      const n = index.nodeById.get(id);
      if (!n) return 0;
      if (n.kind === "customer") return n.metrics.demandPerWeek ?? 0;
      return [...index.downstream(id).nodes].reduce((s, d) => s + (index.nodeById.get(d)?.metrics.demandPerWeek ?? 0), 0);
    };
    const totalDemand = model.nodes.filter((n) => n.kind === "customer").reduce((s, n) => s + (n.metrics.demandPerWeek ?? 0), 0) || 1;

    for (const o of overrides) {
      const target = o.targetType === "node" ? index.nodeById.get(o.targetId) : index.edgeById.get(o.targetId);
      if (!target) continue;
      const spec = SPEC_BY_KIND[o.kind];
      const { severity, recovering, cost } = seedSeverity(o, target);
      const why = `${spec.label}${o.value != null && spec.input ? ` ${spec.input.format(o.value)}` : ""} (simulated)`;
      // the change itself, then everything downstream at a decaying share
      if (o.targetType === "node") bump(nodeSev, o.targetId, severity, why, recovering);
      else bump(edgeSev, o.targetId, severity, why, recovering);
      const start = o.targetType === "node" ? o.targetId : (target as NetworkEdge).to;
      const frontier: Array<[string, number]> = [[start, o.targetType === "node" ? severity * 0.85 : severity * 0.9]];
      const seen = new Set<string>();
      while (frontier.length) {
        const [id, s] = frontier.shift()!;
        if (seen.has(id) || s < 0.05) continue;
        seen.add(id);
        if (id !== o.targetId || o.targetType === "edge") bump(nodeSev, id, s, `Downstream of ${target.name}: ${why}`, recovering);
        for (const e of index.outEdges.get(id) ?? []) {
          bump(edgeSev, e.id, s * 0.8, `Carries the effect of ${why}`, recovering);
          frontier.push([e.to, s * 0.75]);
        }
      }
      // consequence and a recommendation, all illustrative
      const exposedDemand = demand(start);
      const share = exposedDemand / totalDemand;
      if (o.kind === "freight_cost") freightExtra += cost * ((target as NetworkEdge).transportCostPerUnit ?? 0.3) * exposedDemand * 4;
      if (o.kind === "demand_change" && (o.value ?? 1) < 1) {
        recs.push({ id: `rec_${o.id}`, targetType: o.targetType, targetId: o.targetId, state: "LEAN", source: "illustrative",
          action: `Cut the next two orders for ${target.name} by ${Math.round((1 - (o.value ?? 1)) * 100)}% and let cover drain.`,
          rationale: "Lower demand turns today's protection into excess within three weeks.",
          noAction: `About ${Math.round(exposedDemand * (1 - (o.value ?? 1)) * 3).toLocaleString()} units of excess build over three weeks.` });
        continue;
      }
      if (recovering) {
        recs.push({ id: `rec_${o.id}`, targetType: o.targetType, targetId: o.targetId, state: "RECOVER", source: "illustrative",
          action: o.kind === "route_reopened" ? `Phase flow back onto ${target.name} over two orders; keep the alternative on standby for four clean arrivals.`
            : `Dual-source: move 30% of ${target.name}'s volume to the approved alternate for the next quarter.`,
          rationale: "Recovery is staged so temporary protection stock drains without a second shock.",
          noAction: "Protection stock stays on the balance sheet for another cycle." });
        continue;
      }
      serviceDrop += severity * share * 0.14;
      const lost = severity * exposedDemand * 2.5;
      shortageUnits += lost;
      const altEdge = o.targetType === "edge" ? (target as NetworkEdge).alternatives.map((a) => index.edgeById.get(a)).find(Boolean) : undefined;
      const altNode = o.targetType === "node" ? ((target as NetworkNode).alternatives ?? []).map((a) => index.nodeById.get(a)).find(Boolean) : undefined;
      if (altEdge) {
        const extra = Math.max(0, (altEdge.transportCostPerUnit ?? 0) - ((target as NetworkEdge).transportCostPerUnit ?? 0));
        expedite += extra * exposedDemand * 4 + severity * exposedDemand * 0.12;
        for (const id of [altEdge.id]) bump(edgeSev, id, 0, "Recommended alternative (simulated)", true);
        bump(nodeSev, altEdge.to, 0, "Recommended alternative entry (simulated)", true);
        recs.push({ id: `rec_${o.id}`, targetType: "edge", targetId: o.targetId, state: severity >= 0.6 ? "ALLOCATE" : "PROTECT", source: "illustrative",
          action: `Route ${Math.round(Math.min(100, severity * 100))}% of ${target.name} volume via ${altEdge.name.replace(/ \(alternative\)$/i, "")} (${altEdge.leadDays.normal != null && (target as NetworkEdge).leadDays.normal != null ? `${altEdge.leadDays.normal - (target as NetworkEdge).leadDays.normal! >= 0 ? "+" : ""}${altEdge.leadDays.normal - (target as NetworkEdge).leadDays.normal!} days` : "transit time not known"}${extra > 0 ? `, about $${extra.toFixed(2)} more per unit` : ", no extra cost per unit"}) and hold protection at the DC.`,
          rationale: "The alternative avoids the disrupted failure domain; the DC is the cheapest place to carry the extra cover.",
          noAction: `About ${Math.round(lost).toLocaleString()} units short downstream over the next cycle; service on exposed accounts falls by roughly ${Math.round(severity * share * 14)} points.` });
      } else if (altNode) {
        expedite += severity * exposedDemand * 0.22;
        bump(nodeSev, altNode.id, 0, "Recommended alternate supplier (simulated)", true);
        recs.push({ id: `rec_${o.id}`, targetType: "node", targetId: o.targetId, state: severity >= 0.6 ? "ALLOCATE" : "PROTECT", source: "illustrative",
          action: `Move ${Math.round(Math.min(100, severity * 100))}% of ${target.name}'s open volume to ${altNode.name} and expedite the first order.`,
          rationale: "An approved alternate exists; switching share is cheaper than carrying the shortage.",
          noAction: `About ${Math.round(lost).toLocaleString()} units short; exposed customers lose roughly ${Math.round(severity * share * 14)} service points.` });
      } else {
        expedite += severity * exposedDemand * 0.35;
        recs.push({ id: `rec_${o.id}`, targetType: o.targetType, targetId: o.targetId, state: severity >= 0.6 ? "ALLOCATE" : "PROTECT", source: "illustrative",
          action: severity >= 0.6 ? `Allocate remaining stock by customer priority and expedite the next inbound; no alternative is approved for ${target.name}.`
            : `Raise protection downstream of ${target.name} by ${Math.round(severity * 12)} days of cover at the DC.`,
          rationale: "Without an alternative source or lane, the only levers are priority and time.",
          noAction: `About ${Math.round(lost).toLocaleString()} units short; the highest-value accounts are served last if nothing is allocated.` });
      }
    }

    const nodes = model.nodes.map((n) => {
      const s = nodeSev.get(n.id);
      if (!s) return n;
      return { ...n, state: stateFor(n.state, s.s, s.recovering), risk: withRisk(n.risk, s.s, s.why) };
    });
    const edges = model.edges.map((e) => {
      const s = edgeSev.get(e.id);
      if (!s) return e;
      return { ...e, state: stateFor(e.state, s.s, s.recovering), risk: withRisk(e.risk, s.s, s.why) };
    });
    const exposed = {
      nodes: new Set([...nodeSev.entries()].filter(([, v]) => v.s >= 0.2 || v.recovering).map(([k]) => k)),
      edges: new Set([...edgeSev.entries()].filter(([, v]) => v.s >= 0.2 || v.recovering).map(([k]) => k)),
    };
    const stockNodes = model.nodes.filter((n) => n.kind === "dc" || n.kind === "branch");
    const baseService = stockNodes.length ? stockNodes.reduce((s, n) => s + (n.metrics.serviceProjected ?? n.metrics.serviceTarget ?? 0.97), 0) / stockNodes.length : null;
    const inventory = stockNodes.reduce((s, n) => s + (n.metrics.onHandUnits ?? 0), 0) || null;
    const holding = inventory ? inventory * 0.04 : 0;
    const comparison = overrides.length === 0 ? null : {
      current: { service: baseService, inventoryUnits: inventory, shortageUnits: 0, expediteCost: 0, totalCost: holding },
      doNothing: { service: baseService == null ? null : Math.max(0.5, baseService - serviceDrop), inventoryUnits: inventory == null ? null : Math.round(inventory * (1 - Math.min(0.35, serviceDrop * 2))),
        shortageUnits: Math.round(shortageUnits), expediteCost: Math.round(freightExtra), totalCost: Math.round(holding + freightExtra + shortageUnits * 3.2) },
      zaad: { service: baseService == null ? null : Math.max(0.5, baseService - serviceDrop * 0.3), inventoryUnits: inventory == null ? null : Math.round(inventory * (1 + Math.min(0.2, serviceDrop * 1.1))),
        shortageUnits: Math.round(shortageUnits * 0.3), expediteCost: Math.round(expedite + freightExtra), totalCost: Math.round(holding * (1 + Math.min(0.2, serviceDrop * 1.1)) + expedite + freightExtra + shortageUnits * 0.3 * 3.2) },
    };
    return {
      view: { ...model, nodes, edges, recommendations: recs.length ? recs : model.recommendations },
      exposed, recommendations: recs, comparison, source: "illustrative",
      label: "Illustrative scenario result · development demo adapter, not the ZAAD optimizer",
      notes: ["Propagation is a fixed decay downstream of each change; costs use flat illustrative rates.", "Replace `illustrativeEngine` with `optimizerEngine` once /fmcg scenario evaluation exists."],
    };
  },
};

/** Hook for the real optimizer. No ZAAD endpoint evaluates overrides yet, so it reports unavailable. */
export const optimizerEngine: ScenarioEngine = {
  id: "optimizer",
  label: "ZAAD optimizer",
  available: false,
  evaluate(model) {
    return { view: model, exposed: { nodes: new Set(), edges: new Set() }, recommendations: [], comparison: null, source: "optimizer",
      label: "ZAAD optimizer scenario evaluation is not available in this build", notes: ["No /fmcg endpoint accepts scenario overrides yet."] };
  },
};

export function pickEngine(): ScenarioEngine {
  return optimizerEngine.available ? optimizerEngine : illustrativeEngine;
}


const money = (v: number) => `$${Math.round(v).toLocaleString("en-US")}`;
const pct1 = (v: number) => `${(v * 100).toFixed(1)}%`;

/** One sentence a person can act on, from the comparison alone. */
export function summarizeResult(r: ScenarioResult): string | null {
  const c = r.comparison;
  if (!c) return null;
  const cur = c.current, dn = c.doNothing, z = c.zaad;
  const first: string[] = [];
  if (cur.service != null && dn.service != null && dn.service < cur.service - 0.0005) first.push(`service falls from ${pct1(cur.service)} to ${pct1(dn.service)}`);
  if (dn.shortageUnits) first.push(`about ${dn.shortageUnits.toLocaleString("en-US")} units go short`);
  if (dn.expediteCost && !first.length) first.push(`costs rise by about ${money(dn.expediteCost)}`);
  const second: string[] = [];
  if (z.service != null && dn.service != null && z.service > dn.service + 0.0005) second.push(`holds service at ${pct1(z.service)}`);
  if (z.shortageUnits != null && dn.shortageUnits != null && z.shortageUnits < dn.shortageUnits) second.push(`limits the shortage to about ${z.shortageUnits.toLocaleString("en-US")} units`);
  const extra = (z.expediteCost ?? 0) - (cur.expediteCost ?? 0);
  const tail = extra > 0 ? ` for about ${money(extra)} of extra cost` : "";
  if (!first.length && !second.length) return "This change has no material effect on service or cost.";
  return `${first.length ? `Without action, ${first.join(" and ")}.` : ""} ${second.length ? `ZAAD's response ${second.join(" and ")}${tail}.` : "ZAAD proposes no change."}`.trim();
}
