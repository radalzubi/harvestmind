import type { NetworkEdge, NetworkModel, NetworkNode, SelectionRef } from "./model";

/** Adjacency and dependency queries over one model, built once per model. */
export interface NetworkIndex {
  nodeById: Map<string, NetworkNode>;
  edgeById: Map<string, NetworkEdge>;
  outEdges: Map<string, NetworkEdge[]>;
  inEdges: Map<string, NetworkEdge[]>;
  /** Everything that feeds this node, transitively. */
  upstream(id: string): { nodes: Set<string>; edges: Set<string> };
  /** Everything this node feeds, transitively. */
  downstream(id: string): { nodes: Set<string>; edges: Set<string> };
  /** The dependency neighbourhood of a selection: the selection, its upstream and its downstream. */
  related(sel: SelectionRef | null): { nodes: Set<string>; edges: Set<string> } | null;
  /** Nodes the model marks as alternatives to the selection (standby suppliers, alternative lanes). */
  alternativesOf(sel: SelectionRef): string[];
}

export function buildIndex(model: NetworkModel): NetworkIndex {
  const nodeById = new Map(model.nodes.map((n) => [n.id, n]));
  const edgeById = new Map(model.edges.map((e) => [e.id, e]));
  const outEdges = new Map<string, NetworkEdge[]>();
  const inEdges = new Map<string, NetworkEdge[]>();
  for (const e of model.edges) {
    if (!outEdges.has(e.from)) outEdges.set(e.from, []);
    if (!inEdges.has(e.to)) inEdges.set(e.to, []);
    outEdges.get(e.from)!.push(e);
    inEdges.get(e.to)!.push(e);
  }
  const memo = new Map<string, { nodes: Set<string>; edges: Set<string> }>();

  function walk(start: string, dir: "up" | "down") {
    const key = `${dir}:${start}`;
    const hit = memo.get(key);
    if (hit) return hit;
    const nodes = new Set<string>(), edges = new Set<string>();
    const stack = [start];
    while (stack.length) {
      const id = stack.pop()!;
      const next = dir === "down" ? outEdges.get(id) ?? [] : inEdges.get(id) ?? [];
      for (const e of next) {
        edges.add(e.id);
        const other = dir === "down" ? e.to : e.from;
        if (!nodes.has(other) && other !== start) { nodes.add(other); stack.push(other); }
      }
    }
    const out = { nodes, edges };
    memo.set(key, out);
    return out;
  }

  return {
    nodeById, edgeById, outEdges, inEdges,
    upstream: (id) => walk(id, "up"),
    downstream: (id) => walk(id, "down"),
    related(sel) {
      if (!sel) return null;
      const nodes = new Set<string>(), edges = new Set<string>();
      const add = (r: { nodes: Set<string>; edges: Set<string> }) => { r.nodes.forEach((n) => nodes.add(n)); r.edges.forEach((e) => edges.add(e)); };
      if (sel.type === "node") {
        if (!nodeById.has(sel.id)) return null;
        nodes.add(sel.id);
        add(walk(sel.id, "up")); add(walk(sel.id, "down"));
      } else {
        const e = edgeById.get(sel.id);
        if (!e) return null;
        edges.add(e.id); nodes.add(e.from); nodes.add(e.to);
        add(walk(e.from, "up")); add(walk(e.to, "down"));
      }
      return { nodes, edges };
    },
    alternativesOf(sel) {
      if (sel.type === "node") return nodeById.get(sel.id)?.alternatives ?? [];
      return edgeById.get(sel.id)?.alternatives ?? [];
    },
  };
}

/** Case-insensitive search over names, places, SKUs, open orders and shipment references. */
export function searchModel(model: NetworkModel, q: string, limit = 8): SelectionRef[] {
  const needle = q.trim().toLowerCase();
  if (!needle) return [];
  const score = (hay: string[], q = needle) => {
    let best = 0;
    for (const h of hay) {
      const s = h.toLowerCase();
      if (s === q) best = Math.max(best, 3);
      else if (s.startsWith(q)) best = Math.max(best, 2);
      else if (s.includes(q)) best = Math.max(best, 1);
    }
    return best;
  };
  // a hit on the name outranks a hit on a place, id or SKU; nodes win ties with lanes
  const hits: Array<{ ref: SelectionRef; s: number }> = [];
  const po = needle.replace(/^po[\s-]*/, "");
  for (const n of model.nodes) {
    const orders = (n.metrics.openPOs ?? []).flatMap((o) => [o.id, o.id.replace(/^PO-?/i, "")]);
    const s = Math.max(score([n.name]) * 1.5, score([n.id, n.subtitle ?? "", n.region ?? "", ...n.skus]), po ? score(orders.map((o) => o.replace(/^PO-?/i, "")), po) * 1.5 : 0);
    if (s) hits.push({ ref: { type: "node", id: n.id }, s: s + 0.25 });
  }
  for (const e of model.edges) {
    const refs = model.shipments.filter((sh) => sh.edgeId === e.id).flatMap((sh) => [sh.ref, ...sh.ref.split(/[\s·]+/)]);
    const s = Math.max(score([e.name]) * 1.5, score([e.id, ...e.skus, ...refs]));
    if (s) hits.push({ ref: { type: "edge", id: e.id }, s });
  }
  return hits.sort((a, b) => b.s - a.s).slice(0, limit).map((h) => h.ref);
}
