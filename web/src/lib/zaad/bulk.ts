/**
 * Bulk purchase creation from selected recommendations — the pure part.
 *
 * A BUY decision carries one source (supplier, product, destination) and the quantity ZAAD
 * recommends this week. Selected decisions are grouped deterministically into proposals: one per
 * supplier and destination, lines ordered by product code, groups ordered by supplier then
 * destination. Anything that cannot be turned into a line without guessing — a decision whose
 * source is not in the request, a HOLD (order nothing), a MOVE (a transfer, not a purchase), an
 * amendment — is returned as *asked*, with the reason, and is never created silently.
 */
import type { Decision } from "@/lib/zaad/decisions";
import type { ZaadSource } from "@/lib/zaad/types";

export interface ProposalLine { sku: string; quantity: number; unit_price: number | null; units_per_case: number | null }

export interface ProposalGroup {
  key: string;
  supplier_id: string;
  destination_id: string | null;
  lines: ProposalLine[];
  decision_ids: string[];
}

export interface Asked { decision: Decision; reason: string }

export interface BulkPlan { groups: ProposalGroup[]; asked: Asked[] }

function sourceOf(decision: Decision): ZaadSource | null {
  const src = decision.technical?.source;
  return src && typeof src === "object" && "supplier" in src && "sku" in src ? (src as ZaadSource) : null;
}

/** One proposal's worth of a single decision, or the reason it cannot be one. */
export function proposalFromDecision(decision: Decision): { group: ProposalGroup } | { reason: string } {
  if (!decision.id.startsWith("buy:")) {
    if (decision.id.startsWith("move:")) return { reason: "A transfer between your own sites is not a purchase order." };
    if (decision.id.startsWith("po:")) return { reason: "A change to an existing order is proposed from that order, not created as a new one." };
    return { reason: "This recommendation is not a purchase." };
  }
  const selected = Number(decision.technical?.selected ?? NaN);
  if (!Number.isFinite(selected) || selected <= 0) return { reason: "ZAAD recommends ordering nothing here; there is no quantity to create." };
  const src = sourceOf(decision);
  if (!src) return { reason: "The source ZAAD priced is not in the current request, so the product and price cannot be filled in." };
  const supplier = String(src.supplier);
  const destination = src.destination ? String(src.destination) : null;
  return {
    group: {
      key: `${supplier}|${destination ?? ""}`,
      supplier_id: supplier,
      destination_id: destination,
      lines: [{ sku: String(src.sku), quantity: Math.round(selected), unit_price: src.unit_price ?? null,
        units_per_case: src.case_multiple ?? null }],
      decision_ids: [decision.id],
    },
  };
}

/** Deterministic grouping: one proposal per supplier and destination, in a stable order. */
export function planBulk(decisions: Decision[]): BulkPlan {
  const groups = new Map<string, ProposalGroup>();
  const asked: Asked[] = [];
  for (const d of [...decisions].sort((a, b) => a.id.localeCompare(b.id))) {
    const made = proposalFromDecision(d);
    if ("reason" in made) { asked.push({ decision: d, reason: made.reason }); continue; }
    const g = made.group;
    const hit = groups.get(g.key);
    if (hit) {
      // the same product twice in one group is one line with the quantities summed — and said so
      const same = hit.lines.find((l) => l.sku === g.lines[0].sku);
      if (same) same.quantity += g.lines[0].quantity; else hit.lines.push(...g.lines);
      hit.decision_ids.push(...g.decision_ids);
    } else {
      groups.set(g.key, { ...g, lines: [...g.lines], decision_ids: [...g.decision_ids] });
    }
  }
  const out = [...groups.values()].sort((a, b) => a.supplier_id.localeCompare(b.supplier_id) || (a.destination_id ?? "").localeCompare(b.destination_id ?? ""));
  for (const g of out) g.lines.sort((a, b) => a.sku.localeCompare(b.sku));
  return { groups: out, asked };
}

/** The request bodies `POST /api/zaad/orders/bulk` takes, one per group. */
export function bulkBodies(plan: BulkPlan, currency: string): Array<Record<string, unknown>> {
  return plan.groups.map((g) => ({
    origin: "ZAAD_RECOMMENDATION",
    supplier_id: g.supplier_id,
    destination_id: g.destination_id,
    currency,
    // the first decision is the provenance the ledger records; the rest are in the notes
    source_decision_id: g.decision_ids[0],
    notes: g.decision_ids.length > 1 ? `From ${g.decision_ids.length} recommendations: ${g.decision_ids.join(", ")}` : null,
    lines: g.lines.map((l) => ({ sku: l.sku, quantity: l.quantity, unit_price: l.unit_price, units_per_case: l.units_per_case })),
  }));
}
