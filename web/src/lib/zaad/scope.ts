/**
 * How a plan's products are solved: as one joint problem, because the request ties them together.
 *
 * A reader seeing "this plan covers 10 of your 150 products" asks whether the ten were solved
 * one by one or together. The answer is in the request itself: products that share a supplier's
 * capacity resource, or a supplier whose order-level terms (minimum order value, fixed order
 * cost) apply across its products, cannot be planned apart without changing the problem. This
 * reads those couplings and says so in one sentence. It never claims a speed or a saving.
 */
import type { ZaadRequest } from "@/lib/zaad/types";

export interface SolveScope {
  catalogue: number | null;
  evaluated: number;
  /** Products tied to at least one other by a shared supplier resource or supplier-level terms. */
  coupled: number;
  /** Connected components over those ties: 1 means every evaluated product is in one joint problem. */
  components: number;
}

export function solveScope(
  request: Pick<ZaadRequest, "skus" | "sources"> & { supplier_terms?: Array<{ supplier: string }> },
  catalogue: number | null,
  /** The products the plan actually ran over, when narrower than the request held in memory. */
  only?: Iterable<string>,
): SolveScope {
  const wanted = only ? new Set(only) : null;
  const ids = request.skus.map((s) => s.id).filter((id) => !wanted || wanted.has(id));
  const parent = new Map<string, string>(ids.map((id) => [id, id]));
  const find = (x: string): string => {
    let cur = x;
    while (parent.get(cur) !== cur) cur = parent.get(cur)!;
    return cur;
  };
  const union = (a: string, b: string) => { const ra = find(a), rb = find(b); if (ra !== rb) parent.set(ra, rb); };
  const byResource = new Map<string, string[]>();
  const bySupplier = new Map<string, string[]>();
  for (const src of request.sources) {
    if (!parent.has(src.sku)) continue;
    for (const r of (src as { resources?: string[] }).resources ?? []) byResource.set(r, [...(byResource.get(r) ?? []), src.sku]);
    bySupplier.set(src.supplier, [...(bySupplier.get(src.supplier) ?? []), src.sku]);
  }
  const tied = new Set<string>();
  for (const group of byResource.values()) {
    const unique = [...new Set(group)];
    for (const s of unique.slice(1)) { union(unique[0], s); tied.add(unique[0]); tied.add(s); }
  }
  const terms = new Set((request.supplier_terms ?? []).map((t) => t.supplier));
  for (const [sup, group] of bySupplier) {
    if (!terms.has(sup)) continue;
    const unique = [...new Set(group)];
    for (const s of unique.slice(1)) { union(unique[0], s); tied.add(unique[0]); tied.add(s); }
  }
  const roots = new Set(ids.map(find));
  return { catalogue, evaluated: ids.length, coupled: tied.size, components: ids.length ? roots.size : 0 };
}

export function scopeSentence(s: SolveScope): string {
  const evaluated = s.evaluated.toLocaleString("en-US");
  const head = s.catalogue != null ? `Catalogue ${s.catalogue.toLocaleString("en-US")} · evaluated ${evaluated}` : `Evaluated ${evaluated}`;
  if (s.evaluated <= 1) return `${head} · solved on its own.`;
  if (s.coupled === 0) return `${head} · none of them share supplier capacity or order terms; they were planned in one run and each could be planned on its own.`;
  if (s.components === 1) return `${head} · solved together as one problem: ${s.coupled === s.evaluated ? "every product shares" : `${s.coupled} of them share`} supplier capacity or order terms with another.`;
  return `${head} · solved together; ${s.coupled} of them share supplier capacity or order terms, forming ${s.components} independent groups.`;
}
