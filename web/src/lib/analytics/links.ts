/**
 * Where an analysis leads: drill-through from a dimension member to the operating surface that
 * holds the records. Every link carries the member the person clicked and nothing invented.
 */
import type { ResultSet } from "./client";

const ID = /^[A-Za-z0-9 _.:@+\-\/&()'#,]{1,120}$/;

export function drillThrough(dimension: string, member: string): { href: string; label: string } | null {
  if (!ID.test(member)) return null;
  const m = encodeURIComponent(member);
  switch (dimension) {
    case "sku": case "product": return { href: `/inventory?sku=${m}`, label: "Inventory" };
    case "supplier": return { href: `/diagnostics/supplier/${m}`, label: "Supplier" };
    case "customer": return { href: `/data?dataset=customer_orders&fcol=customer_id&fval=${m}`, label: "Customer orders" };
    case "location": case "destination": return { href: `/inventory?location=${m}`, label: "Site" };
    case "category": return { href: `/inventory?category=${m}`, label: "Inventory" };
    case "brand": return { href: `/inventory?brand=${m}`, label: "Inventory" };
    case "po_status": return { href: `/orders?tab=imported&postate=${member === "received" ? "received" : member === "late" ? "late" : "open"}`, label: "Purchase orders" };
    case "decision_verb": return { href: "/decisions", label: "Decisions" };
    case "proposal_state": return { href: "/orders", label: "Proposals" };
    default: return null;
  }
}

/** The records behind a whole result: the fact's dataset in the Data explorer, filtered where a single member is filtered. */
export function recordsBehind(result: ResultSet): { href: string; label: string } | null {
  const dataset: Record<string, string> = {
    customer_order_line: "customer_orders", inventory_snapshot: "inventory", purchase_order_line: "purchase_orders", matched_purchase_order: "purchase_orders",
    receipt: "receipts", proposal: "", decision_response: "", outcome: "", decision: "", plan_value: "",
  };
  const ds = dataset[result.provenance.fact];
  if (!ds) return result.provenance.fact === "decision" || result.provenance.fact === "plan_value" ? { href: "/decisions", label: "Decisions" } : { href: "/history", label: "History" };
  const q = new URLSearchParams({ dataset: ds });
  const column: Record<string, string> = { sku: "sku", supplier: "supplier_id", customer: "customer_id", location: "location_id", category: "category", brand: "brand" };
  for (const f of result.provenance.filters) {
    if (f.values.length === 1 && column[f.dimension_id]) { q.set("fcol", column[f.dimension_id]); q.set("fval", f.values[0]); break; }
  }
  return { href: `/data?${q.toString()}`, label: "Data" };
}
