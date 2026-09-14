/**
 * Collapsing for large networks: when one facility feeds many customer
 * nodes, the graph shows a single "Customers · N" node until it is opened.
 * The map keeps real points; only the NETWORK view is grouped. The live
 * model is untouched; this is a display projection.
 */
import type { NetworkEdge, NetworkModel, NetworkNode } from "./model";
import { riskLevel } from "./model";

export const GROUP_THRESHOLD = 4;
export const GROUP_PREFIX = "group:";

export interface GroupInfo { id: string; feederId: string; memberIds: string[] }

export function isGroupId(id: string): boolean { return id.startsWith(GROUP_PREFIX); }

/** Returns the display model plus which groups exist, honouring the expanded set. */
export function groupCustomers(model: NetworkModel, expanded: Set<string>): { model: NetworkModel; groups: GroupInfo[] } {
  const byFeeder = new Map<string, NetworkNode[]>();
  const feederOf = new Map<string, string>();
  for (const e of model.edges) {
    const to = model.nodes.find((x) => x.id === e.to);
    if (!to || to.kind !== "customer") continue;
    // a customer with several feeders belongs to none of the groups
    if (feederOf.has(to.id) && feederOf.get(to.id) !== e.from) { feederOf.set(to.id, ""); continue; }
    feederOf.set(to.id, e.from);
  }
  for (const [cid, fid] of feederOf) {
    if (!fid) continue;
    if (!byFeeder.has(fid)) byFeeder.set(fid, []);
    byFeeder.get(fid)!.push(model.nodes.find((x) => x.id === cid)!);
  }
  const groups: GroupInfo[] = [];
  const hidden = new Set<string>();
  const added: NetworkNode[] = [];
  const addedEdges: NetworkEdge[] = [];
  for (const [fid, members] of byFeeder) {
    if (members.length < GROUP_THRESHOLD) continue;
    const id = `${GROUP_PREFIX}${fid}`;
    groups.push({ id, feederId: fid, memberIds: members.map((m) => m.id) });
    if (expanded.has(id)) continue;
    members.forEach((m) => hidden.add(m.id));
    const score = Math.max(...members.map((m) => m.risk.score));
    const worst = members.reduce((a, b) => (b.risk.score > a.risk.score ? b : a));
    const demand = members.reduce((s, m) => s + (m.metrics.demandPerWeek ?? 0), 0);
    added.push({
      id, kind: "customer", name: "Customers", subtitle: `${members.length} customers`, geo: null, importance: 0.6,
      state: worst.state, risk: { level: riskLevel(score), score, reasons: score >= 0.25 ? [`${worst.name}: ${worst.risk.reasons[0] ?? "at risk"}`] : [], evidence: [] },
      metrics: { demandPerWeek: demand || null, serviceTarget: null }, skus: [...new Set(members.flatMap((m) => m.skus))],
    });
    const laneEdges = model.edges.filter((e) => e.from === fid && members.some((m) => m.id === e.to));
    const worstEdge = laneEdges.reduce((a, b) => (b.risk.score > a.risk.score ? b : a), laneEdges[0]);
    addedEdges.push({ ...worstEdge, id: `${GROUP_PREFIX}edge:${fid}`, to: id, name: `Deliveries to ${members.length} customers`, skus: [...new Set(laneEdges.flatMap((e) => e.skus))], alternatives: [] });
  }
  if (!groups.length) return { model, groups };
  return {
    groups,
    model: {
      ...model,
      nodes: [...model.nodes.filter((x) => !hidden.has(x.id)), ...added],
      edges: [...model.edges.filter((e) => !hidden.has(e.to) && !hidden.has(e.from)), ...addedEdges],
    },
  };
}
