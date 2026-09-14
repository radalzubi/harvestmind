/**
 * The executive layer: which parts of the network need attention, and a
 * plain-English account of any node or lane built from the structured data.
 * Nothing here invents a number; every sentence is assembled from fields that
 * exist, and a field that does not exist is simply not mentioned.
 */
import type { NetworkIndex } from "./graph";
import type { NetworkEdge, NetworkModel, NetworkNode, NetworkRecommendation, SelectionRef } from "./model";
import { ATTENTION_SCORE, WATCH_SCORE } from "./model";

export interface AttentionArea {
  id: string;
  /** The item that leads the area, usually the most exposed one. */
  lead: SelectionRef;
  title: string;
  /** "needs attention" or the quieter "watch". */
  level: "attention" | "watch";
  score: number;
  members: SelectionRef[];
  summary: string;
  affected: Affected;
  recommendation: NetworkRecommendation | null;
}

export interface Affected {
  skus: string[];
  customers: NetworkNode[];
  stockNodes: NetworkNode[];
  openOrders: number;
  delayedShipments: number;
}

// Prose says whole units: a warehouse does not hold a quarter of a case.
const n = (v: number) => Math.round(v).toLocaleString("en-US");
const pct = (v: number, d = 0) => `${(v * 100).toFixed(d)}%`;
const list = (items: string[], max = 3) => items.length <= max ? items.join(", ") : `${items.slice(0, max).join(", ")} and ${items.length - max} more`;
const lower = (s: string) => (s ? s[0].toLowerCase() + s.slice(1) : s);

export function affectedBy(ref: SelectionRef, model: NetworkModel, index: NetworkIndex): Affected {
  const start = ref.type === "node" ? ref.id : index.edgeById.get(ref.id)?.to;
  const own = ref.type === "node" ? index.nodeById.get(ref.id) : index.edgeById.get(ref.id);
  const down = start ? index.downstream(start) : { nodes: new Set<string>(), edges: new Set<string>() };
  const ids = new Set(down.nodes);
  if (start && ref.type === "edge") ids.add(start);
  const nodes = [...ids].map((id) => index.nodeById.get(id)!).filter(Boolean);
  const customers = nodes.filter((x) => x.kind === "customer");
  const stockNodes = nodes.filter((x) => x.kind === "dc" || x.kind === "branch");
  const skus = own?.skus ?? [];
  // orders that travel a lane come from the suppliers behind its origin, not everything upstream of its destination
  const upstreamFrom = ref.type === "edge" ? index.edgeById.get(ref.id)?.from ?? "" : ref.id;
  const supplierNodes = ref.type === "node" && own && (own as NetworkNode).kind === "supplier" ? [own as NetworkNode]
    : [...index.upstream(upstreamFrom).nodes, upstreamFrom].map((id) => index.nodeById.get(id)!).filter((x) => x?.kind === "supplier");
  const openOrders = supplierNodes.reduce((s, x) => s + (x.metrics.openPOs?.length ?? 0), 0);
  const laneIds = ref.type === "edge" ? [ref.id] : [...(index.outEdges.get(ref.id) ?? []), ...(index.inEdges.get(ref.id) ?? [])].map((e) => e.id);
  const delayedShipments = model.shipments.filter((s) => laneIds.includes(s.edgeId) && s.status === "delayed").length;
  return { skus, customers, stockNodes, openOrders, delayedShipments };
}

/** Group exposed items that touch each other into areas, most serious first. */
export function attentionAreas(model: NetworkModel, index: NetworkIndex): AttentionArea[] {
  const items: Array<{ ref: SelectionRef; score: number; name: string }> = [
    ...model.nodes.filter((x) => x.risk.score >= WATCH_SCORE).map((x) => ({ ref: { type: "node" as const, id: x.id }, score: x.risk.score, name: x.name })),
    ...model.edges.filter((x) => x.risk.score >= WATCH_SCORE).map((x) => ({ ref: { type: "edge" as const, id: x.id }, score: x.risk.score, name: x.name })),
  ];
  const key = (r: SelectionRef) => `${r.type}:${r.id}`;
  const parent = new Map(items.map((i) => [key(i.ref), key(i.ref)]));
  const find = (k: string): string => { const p = parent.get(k)!; if (p === k) return k; const r = find(p); parent.set(k, r); return r; };
  const union = (a: string, b: string) => { if (parent.has(a) && parent.has(b)) parent.set(find(a), find(b)); };
  // one problem, one area: an exposed lane joins the items at its ends and their neighbours,
  // so a disrupted lane, the supplier behind it and the sites it starves read as one story
  const neighbours = (id: string) => [...(index.outEdges.get(id) ?? []), ...(index.inEdges.get(id) ?? [])];
  for (const i of items) {
    if (i.ref.type === "edge") {
      const e = index.edgeById.get(i.ref.id)!;
      for (const end of [e.from, e.to]) {
        union(key(i.ref), `node:${end}`);
        for (const n2 of neighbours(end)) { union(key(i.ref), `edge:${n2.id}`); union(key(i.ref), `node:${n2.from === end ? n2.to : n2.from}`); }
      }
    } else {
      for (const e of neighbours(i.ref.id)) union(key(i.ref), `edge:${e.id}`);
    }
  }
  const groups = new Map<string, typeof items>();
  for (const i of items) { const r = find(key(i.ref)); if (!groups.has(r)) groups.set(r, []); groups.get(r)!.push(i); }
  const areas: AttentionArea[] = [];
  for (const members of groups.values()) {
    members.sort((a, b) => b.score - a.score);
    const lead = members[0];
    const level: AttentionArea["level"] = lead.score >= ATTENTION_SCORE ? "attention" : "watch";
    const affected = affectedBy(lead.ref, model, index);
    const rec = model.recommendations.find((r) => members.some((m) => m.ref.type === r.targetType && m.ref.id === r.targetId)) ?? null;
    areas.push({ id: members.map((m) => key(m.ref)).sort().join("|"), lead: lead.ref, title: lead.name, level, score: lead.score,
      members: members.map((m) => m.ref), summary: describe(lead.ref, model, index), affected, recommendation: rec });
  }
  return areas.sort((a, b) => b.score - a.score);
}

export function statusLine(areas: AttentionArea[]): { headline: string; detail: string | null; tone: "ok" | "watch" | "attention" } {
  const attention = areas.filter((a) => a.level === "attention"), watch = areas.filter((a) => a.level === "watch");
  if (attention.length) return { headline: `${attention.length} area${attention.length === 1 ? "" : "s"} need${attention.length === 1 ? "s" : ""} attention`, detail: watch.length ? `${watch.length} more to watch` : null, tone: "attention" };
  if (watch.length) return { headline: "Everything looks normal", detail: `${watch.length} thing${watch.length === 1 ? "" : "s"} to watch`, tone: "watch" };
  return { headline: "Everything looks normal", detail: null, tone: "ok" };
}

/** One paragraph a person could read aloud, from the fields that exist. */
export function describe(ref: SelectionRef, model: NetworkModel, index: NetworkIndex): string {
  const a = affectedBy(ref, model, index);
  const parts: string[] = [];
  if (ref.type === "edge") {
    const e = index.edgeById.get(ref.id);
    if (!e) return "";
    const from = index.nodeById.get(e.from)?.name ?? "", to = index.nodeById.get(e.to)?.name ?? "";
    const standing = e.risk.level === "critical" ? "is severely disrupted" : e.risk.level === "high" ? "is disrupted" : e.risk.level === "medium" ? "is showing early signs of strain" : "is running normally";
    parts.push(`The lane from ${from} to ${to} ${standing}${e.risk.reasons[0] && e.risk.level !== "low" ? `: ${lower(e.risk.reasons[0])}` : ""}.`);
    if (e.leadDays.current != null && e.leadDays.normal != null && e.leadDays.current !== e.leadDays.normal)
      parts.push(`Transit is taking ${e.leadDays.current} ${e.leadDays.current === 1 ? "day" : "days"} against a usual ${e.leadDays.normal}.`);
    const ships = model.shipments.filter((s) => s.edgeId === e.id);
    const delayed = ships.filter((s) => s.status === "delayed");
    if (delayed.length) parts.push(`${delayed.length === 1 ? "One shipment is" : `${delayed.length} shipments are`} delayed (${list(delayed.map((s) => `${s.ref}, ${n(s.units)} units`), 2)}).`);
    else if (ships.length) parts.push(`${ships.length === 1 ? "One shipment is" : `${ships.length} shipments are`} on the way.`);
    if (a.skus.length || a.customers.length) parts.push(`${a.skus.length ? `${a.skus.length} SKU${a.skus.length === 1 ? "" : "s"}` : "Stock"}${a.customers.length ? ` and ${a.customers.length} customer${a.customers.length === 1 ? "" : " groups"}` : ""} depend on this lane.`);
    const alt = e.alternatives.map((id) => index.edgeById.get(id)).find(Boolean);
    if (alt) parts.push(`${alt.name.replace(/ \(alternative\)$/i, "")} is approved as an alternative${alt.leadDays.normal != null && e.leadDays.normal != null ? ` (${alt.leadDays.normal - e.leadDays.normal >= 0 ? "+" : ""}${alt.leadDays.normal - e.leadDays.normal} days)` : ""}.`);
    return parts.join(" ");
  }
  const x = index.nodeById.get(ref.id);
  if (!x) return "";
  const m = x.metrics;
  const reason = x.risk.reasons[0] && x.risk.level !== "low" ? `: ${lower(x.risk.reasons[0])}` : "";
  if (x.kind === "supplier") {
    const standing = x.risk.level === "critical" ? "is at risk of failing to deliver" : x.risk.level === "high" ? "is delivering less reliably than usual" : x.risk.level === "medium" ? "is showing early signs of strain" : "is delivering reliably";
    parts.push(`${x.name} ${standing}${reason}.`);
    const deps: string[] = [];
    if (m.openPOs?.length) deps.push(`${m.openPOs.length} open order${m.openPOs.length === 1 ? "" : "s"}`);
    if (x.skus.length) deps.push(`${x.skus.length} SKU${x.skus.length === 1 ? "" : "s"}`);
    if (deps.length) parts.push(`${deps.join(" and ")} depend on this supplier.`);
    const late = m.openPOs?.filter((po) => po.status === "late") ?? [];
    if (late.length) parts.push(`${late.length === 1 ? `${late[0].id} is` : `${late.length} orders are`} already late.`);
    const alts = (x.alternatives ?? []).map((id) => index.nodeById.get(id)).filter((y): y is NetworkNode => !!y);
    if (alts.length) {
      const alt = alts[0];
      const shared = x.skus.filter((s) => alt.skus.includes(s)).length;
      parts.push(`${alt.name} can cover ${shared ? `${shared} of the ${x.skus.length} SKUs` : "part of this volume"}.`);
    } else if (x.risk.level !== "low") parts.push("No alternative supplier is approved.");
    return parts.join(" ");
  }
  if (x.kind === "port") {
    const lanes = index.inEdges.get(x.id) ?? [];
    const standing = x.risk.level === "critical" || x.risk.level === "high" ? "is disrupted" : x.risk.level === "medium" ? "is congested" : "is operating normally";
    parts.push(`${x.name} ${standing}${reason}.`);
    if (lanes.length) parts.push(`${lanes.length === 1 ? "One inbound lane lands" : `${lanes.length} inbound lanes land`} here.`);
    if (m.dwellDays?.mean != null) parts.push(`Containers dwell about ${m.dwellDays.mean} day${m.dwellDays.mean === 1 ? "" : "s"}.`);
    if (a.customers.length) parts.push(`${a.customers.length} customer group${a.customers.length === 1 ? "" : "s"} downstream.`);
    return parts.join(" ");
  }
  if (x.kind === "dc" || x.kind === "branch") {
    parts.push(`${x.name}${m.onHandUnits != null ? ` holds ${n(m.onHandUnits)} units${m.onHandValue != null ? ` (about $${n(Math.round(m.onHandValue))})` : ""}` : ""}${m.inboundUnits != null ? `, with ${n(m.inboundUnits)} on the way` : ""}.`);
    // "QA-001209 runs short no replenishment route" — the clause is written by whoever knows what
    // the flag means, not assembled from a verb this file guesses at.
    if (m.shortages?.length) parts.push(`${list(m.shortages.map((s) => `${shortName(s.sku)} ${s.said}`), 2)}.`);
    if (m.serviceProjected != null && m.serviceTarget != null) parts.push(`Service is projected at ${pct(m.serviceProjected, 1)} against a ${pct(m.serviceTarget, 1)} target${m.serviceProjected < m.serviceTarget ? ", below where it should be" : ""}.`);
    if (m.excess?.length) parts.push(`${list(m.excess.map((s) => `${shortName(s.sku)} has ${s.weeksOfCover} ${s.weeksOfCover === 1 ? "week" : "weeks"} of cover`), 2)}.`);
    // The service sentence above may already be the risk reason; do not say it twice.
    const reasonSaid = x.risk.reasons[0] && parts.some((p) => p.toLowerCase().includes("service is projected"));
    if (x.risk.level !== "low" && x.risk.reasons[0] && !reasonSaid) parts.push(`${x.risk.reasons[0]}.`.replace(/\.\.$/, "."));
    return parts.join(" ");
  }
  const up = [...index.upstream(x.id).nodes].map((id) => index.nodeById.get(id)!).filter((y) => y && (y.kind === "branch" || y.kind === "dc"));
  parts.push(`${x.name}${m.demandPerWeek != null ? ` orders about ${n(m.demandPerWeek)} units a week` : ""}${m.serviceTarget != null ? ` at a ${pct(m.serviceTarget, m.serviceTarget >= 0.99 ? 1 : 0)} service target` : ""}.`);
  if (up.length) parts.push(`Served from ${up[0].name}.`);
  if (x.risk.level !== "low" && x.risk.reasons[0]) parts.push(`${x.risk.reasons[0]}.`);
  return parts.join(" ");
}

/** "SKU-3120 Nappies M 44s" -> "Nappies M 44s" for prose. */
export function shortName(sku: string): string {
  return sku.replace(/^SKU-\d+\s+/, "");
}

/** The one recommendation to lead with for a selection, if any. */
export function leadRecommendation(ref: SelectionRef, model: NetworkModel): NetworkRecommendation | null {
  return model.recommendations.find((r) => r.targetType === ref.type && r.targetId === ref.id) ?? null;
}

export function edgeTitle(e: NetworkEdge, index: NetworkIndex): string {
  return `${index.nodeById.get(e.from)?.name ?? e.from} → ${index.nodeById.get(e.to)?.name ?? e.to}`;
}
