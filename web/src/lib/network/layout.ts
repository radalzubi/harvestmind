import type { NetworkModel, NodeKind } from "./model";

/**
 * A stable, layered layout: supply flows left to right, each node sits in
 * the column of its longest path from a source, and columns are ordered by
 * the barycentre of their feeders. Nothing here is random, so the same
 * network always draws the same way and people can remember where things are.
 */
export interface Placed { x: number; y: number; tier: number }

const RANK: Record<NodeKind, number> = { supplier: 0, port: 1, dc: 2, branch: 3, customer: 4 };
// Tuned so a five-tier network fits a 1440px canvas at a zoom that keeps node labels legible;
// a bigger network still fits, it just pans.
export const COLUMN_GAP = 236;
export const ROW_GAP = 88;

export function layoutNodes(model: NetworkModel): Map<string, Placed> {
  const ids = model.nodes.map((n) => n.id);
  const kind = new Map(model.nodes.map((n) => [n.id, n.kind]));
  // Only forward edges shape the layering; a transfer between two branches
  // or a back-haul would otherwise create a cycle.
  const forward = model.edges.filter((e) => {
    const a = kind.get(e.from), b = kind.get(e.to);
    return a != null && b != null && (RANK[a] < RANK[b] || (a === "port" && b === "port"));
  });
  const preds = new Map<string, string[]>(ids.map((id) => [id, []]));
  for (const e of forward) preds.get(e.to)!.push(e.from);

  const tier = new Map<string, number>();
  const visiting = new Set<string>();
  const tierOf = (id: string): number => {
    const hit = tier.get(id);
    if (hit != null) return hit;
    if (visiting.has(id)) return RANK[kind.get(id)!];
    visiting.add(id);
    const ps = preds.get(id) ?? [];
    let t = ps.length ? Math.max(...ps.map((p) => tierOf(p) + 1)) : 0;
    // keep kinds in their natural order even when a node has no feeder
    t = Math.max(t, ps.length ? t : RANK[kind.get(id)!] === 0 ? 0 : t);
    visiting.delete(id);
    tier.set(id, t);
    return t;
  };
  ids.forEach(tierOf);
  // Sources of later kinds (a DC with no modelled supplier) still sit to the right of suppliers.
  for (const n of model.nodes) if ((preds.get(n.id) ?? []).length === 0) tier.set(n.id, Math.max(tier.get(n.id)!, Math.min(RANK[n.kind], 2)));

  const columns = new Map<number, string[]>();
  for (const id of ids) {
    const t = tier.get(id)!;
    if (!columns.has(t)) columns.set(t, []);
    columns.get(t)!.push(id);
  }
  const tiers = [...columns.keys()].sort((a, b) => a - b);
  const name = new Map(model.nodes.map((n) => [n.id, n.name]));
  const y = new Map<string, number>();
  const placed = new Map<string, Placed>();
  const tallest = Math.max(...tiers.map((t) => columns.get(t)!.length));

  tiers.forEach((t, ci) => {
    const col = columns.get(t)!;
    const bary = (id: string) => {
      const ps = (preds.get(id) ?? []).filter((p) => y.has(p));
      return ps.length ? ps.reduce((s, p) => s + y.get(p)!, 0) / ps.length : Number.POSITIVE_INFINITY;
    };
    col.sort((a, b) => {
      const ka = RANK[kind.get(a)!], kb = RANK[kind.get(b)!];
      if (ka !== kb) return ka - kb;
      const ba = bary(a), bb = bary(b);
      if (ba !== bb) return ba - bb;
      return name.get(a)!.localeCompare(name.get(b)!);
    });
    const offset = ((tallest - col.length) * ROW_GAP) / 2;
    col.forEach((id, ri) => {
      const py = offset + ri * ROW_GAP;
      y.set(id, py);
      placed.set(id, { x: ci * COLUMN_GAP, y: py, tier: t });
    });
  });
  return placed;
}
