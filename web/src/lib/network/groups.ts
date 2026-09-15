/**
 * Collapsing for large networks.
 *
 * A twin is only worth looking at while a person can read it. Two crowds appear in a real
 * importer's network and both are collapsed here until they are opened:
 *
 *   * **Customers behind one site.** A branch serving forty shops is one relationship to an
 *     operator, not forty.
 *   * **Suppliers behind one entry point.** Thirty suppliers landing at Aqaba is a corridor. Drawn
 *     individually they make the canvas eight thousand pixels tall, and the view zooms out until
 *     every label is unreadable — which is worse than not drawing them, because the reader cannot
 *     tell that anything is missing.
 *
 * The map keeps real points; only the NETWORK view is grouped. The live model is untouched — this
 * is a display projection, and the group carries the worst risk among its members so a collapsed
 * crowd can never hide a supplier that needs attention.
 */
import type { NetworkEdge, NetworkModel, NetworkNode } from "./model";
import { riskLevel } from "./model";

/** Above this many siblings behind one object, the crowd is drawn as one node. */
export const GROUP_THRESHOLD = 4;
/** Suppliers crowd a port faster than customers crowd a site, and matter more individually. */
export const SUPPLIER_GROUP_THRESHOLD = 8;
export const GROUP_PREFIX = "group:";

export interface GroupInfo { id: string; feederId: string; memberIds: string[] }

export function isGroupId(id: string): boolean { return id.startsWith(GROUP_PREFIX); }

interface Crowd {
  /** The object the crowd hangs off: the feeder for customers, the destination for suppliers. */
  anchor: string;
  members: NetworkNode[];
}

/** Members of `kind` that attach to exactly one counterpart, keyed by that counterpart. */
function crowdsOf(model: NetworkModel, kind: NetworkNode["kind"], direction: "downstream" | "upstream"): Crowd[] {
  const byId = new Map(model.nodes.map((n) => [n.id, n]));
  const anchorOf = new Map<string, string>();
  for (const edge of model.edges) {
    const member = direction === "downstream" ? byId.get(edge.to) : byId.get(edge.from);
    const anchor = direction === "downstream" ? edge.from : edge.to;
    if (!member || member.kind !== kind) continue;
    // a member attached to several counterparts belongs to none of the crowds
    if (anchorOf.has(member.id) && anchorOf.get(member.id) !== anchor) { anchorOf.set(member.id, ""); continue; }
    anchorOf.set(member.id, anchor);
  }
  const byAnchor = new Map<string, NetworkNode[]>();
  for (const [memberId, anchor] of anchorOf) {
    if (!anchor) continue;
    if (!byAnchor.has(anchor)) byAnchor.set(anchor, []);
    byAnchor.get(anchor)!.push(byId.get(memberId)!);
  }
  return [...byAnchor].map(([anchor, members]) => ({ anchor, members }));
}

/** Returns the display model plus which groups exist, honouring the expanded set. */
export function groupCustomers(model: NetworkModel, expanded: Set<string>): { model: NetworkModel; groups: GroupInfo[] } {
  const groups: GroupInfo[] = [];
  const hidden = new Set<string>();
  const added: NetworkNode[] = [];
  const addedEdges: NetworkEdge[] = [];

  const collapse = (
    crowd: Crowd,
    direction: "downstream" | "upstream",
    kind: NetworkNode["kind"],
    label: (n: number) => string,
    subtitle: (n: number) => string,
    edgeLabel: (n: number) => string,
  ) => {
    const { anchor, members } = crowd;
    const id = `${GROUP_PREFIX}${kind}:${anchor}`;
    groups.push({ id, feederId: anchor, memberIds: members.map((m) => m.id) });
    if (expanded.has(id)) return;
    members.forEach((m) => hidden.add(m.id));
    const score = Math.max(...members.map((m) => m.risk.score));
    const worst = members.reduce((a, b) => (b.risk.score > a.risk.score ? b : a));
    const demand = members.reduce((s, m) => s + (m.metrics.demandPerWeek ?? 0), 0);
    const openPOs = members.flatMap((m) => m.metrics.openPOs ?? []);
    added.push({
      id, kind, name: label(members.length), subtitle: subtitle(members.length),
      geo: null, importance: 0.6, state: worst.state,
      risk: {
        level: riskLevel(score), score,
        // The group speaks for its worst member, so collapsing can never hide a problem.
        reasons: score >= 0.25 ? [`${worst.name}: ${worst.risk.reasons[0] ?? "at risk"}`] : [],
        evidence: [`${members.length} grouped; the most exposed is ${worst.name}`],
      },
      metrics: {
        demandPerWeek: demand || null, serviceTarget: null,
        openPOs: openPOs.length ? openPOs : undefined,
      },
      skus: [...new Set(members.flatMap((m) => m.skus))],
    });
    const memberIds = new Set(members.map((m) => m.id));
    const lanes = model.edges.filter((e) =>
      direction === "downstream" ? e.from === anchor && memberIds.has(e.to) : e.to === anchor && memberIds.has(e.from));
    if (!lanes.length) return;
    const worstEdge = lanes.reduce((a, b) => (b.risk.score > a.risk.score ? b : a), lanes[0]);
    addedEdges.push({
      ...worstEdge, id: `${GROUP_PREFIX}edge:${kind}:${anchor}`,
      ...(direction === "downstream" ? { to: id } : { from: id }),
      name: edgeLabel(members.length),
      skus: [...new Set(lanes.flatMap((e) => e.skus))], alternatives: [], path: null,
    });
  };

  for (const crowd of crowdsOf(model, "customer", "downstream")) {
    if (crowd.members.length >= GROUP_THRESHOLD) {
      collapse(crowd, "downstream", "customer",
        () => "Customers", (n) => `${n} customers`, (n) => `Deliveries to ${n} customers`);
    }
  }
  for (const crowd of crowdsOf(model, "supplier", "upstream")) {
    if (crowd.members.length >= SUPPLIER_GROUP_THRESHOLD) {
      collapse(crowd, "upstream", "supplier",
        (n) => `${n} suppliers`, () => "grouped by where they land",
        (n) => `${n} suppliers on this route`);
    }
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
