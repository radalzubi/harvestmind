"use client";

/**
 * One panel for whatever is selected. It adapts to the object — supplier, lane, site, port,
 * customer — but the reading order never changes: what this is, what ZAAD recommends about it,
 * what is known, then the technical detail. Anything the workspace does not carry is stated as
 * missing rather than left to look like a zero.
 */
import Link from "next/link";
import { ArrowUpRight, X } from "lucide-react";
import { ButtonLink } from "@/components/workspace/ui";
import { describe, edgeTitle, affectedBy } from "@/lib/network/attention";
import { EDGE_LABEL, KIND_LABEL, RISK_LABEL, STATE_LABEL, STATE_SENTENCE } from "@/lib/network/model";
import type { NetworkEdge, NetworkNode } from "@/lib/network/model";
import { Disclosure, Evidence, Facts, TechnicalDetails } from "@/components/workspace/ui";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { money } from "@/lib/zaad/decisions";
import { COUNT, NUMBER } from "@/lib/zaad/product";
import { useTwin } from "./store";

function Recommendations({ targetId }: { targetId: string }) {
  const { decisions } = useWorkspaceData();
  const mine = decisions.filter((d) => d.target.networkId === targetId);
  if (!mine.length) {
    return <p style={{ margin: 0, fontSize: 13, color: "var(--ink-500)" }}>ZAAD recommends no change here.</p>;
  }
  return (
    <div className="dec-list">
      {mine.map((d) => (
        <Link key={d.id} href={`/decisions?decision=${encodeURIComponent(d.id)}`} className="dec" style={{ textDecoration: "none", color: "inherit" }}>
          <div className="dec-top">
            <span className="dec-verb" data-tone={d.verb === "KEEP" ? "keep" : "change"}>{d.verb}</span>
            <span className="dec-cat">{d.category}</span>
            <ArrowUpRight size={14} style={{ marginInlineStart: "auto", color: "var(--ink-500)" }} aria-hidden />
          </div>
          <h4 className="dec-h" style={{ fontSize: 14 }}>{d.headline}</h4>
        </Link>
      ))}
    </div>
  );
}

/**
 * Where a selected object leads.
 *
 * The twin used to be a diagram: it told you a supplier was late and left you to find it again
 * somewhere else. Every action here opens a surface that already exists — the supplier's
 * diagnostics, its products, its orders, a proposed order against it. Nothing here executes
 * anything, and there is no control that implies ZAAD would contact a supplier.
 */
function Actions({ node, edge, index }: {
  node: NetworkNode | null; edge: NetworkEdge | null; index: ReturnType<typeof useTwin>["index"];
}) {
  const links: Array<{ href: string; label: string; primary?: boolean }> = [];
  if (node) {
    const bare = node.id.split(":").slice(1).join(":");
    if (node.kind === "supplier") {
      links.push({ href: `/diagnostics/supplier/${encodeURIComponent(bare)}`, label: "Supplier diagnostics", primary: true });
      links.push({ href: `/inventory?supplier=${encodeURIComponent(bare)}`, label: "Its products" });
      links.push({ href: `/orders?tab=imported&poq=${encodeURIComponent(bare)}`, label: "Its orders" });
      links.push({ href: `/orders/new?supplier=${encodeURIComponent(bare)}`, label: "Propose an order" });
    } else if (node.kind === "dc" || node.kind === "branch") {
      // Inventory sums stock across every site per product and offers no site filter, and the
      // open-orders list is not per destination either — so "Stock held here" and "Arriving here"
      // both opened a list about the whole business. The labels say what opens. Per-site stock
      // does exist, one product at a time, in the product drawer's "Where it is".
      links.push({ href: "/inventory", label: "Stock (all sites)", primary: true });
      links.push({ href: "/orders?tab=imported&postate=open", label: "Open orders (all sites)" });
    } else if (node.kind === "customer") {
      // A customer node's id is the *planning request's* grouping key, not a customer id in the
      // upload — on both QA workspaces it is the single aggregate "customers" — so searching the
      // customer-orders dataset for it returned "No record matches that" from the panel's one
      // primary action. Its channel is no better a bridge: one vault's request declares
      // "wholesale" over 371,140 order lines whose channel column is NULL throughout, so filtering
      // by it is a second dead link. Nothing the panel holds is guaranteed to exist in the
      // dataset, so the link opens the orders themselves and says that is what it does; the
      // explorer's own filters are on the page it lands on.
      links.push({ href: "/data?dataset=customer_orders", label: "Customer orders", primary: true });
    }
    if (node.skus.length === 1) {
      links.push({ href: `/inventory?sku=${encodeURIComponent(node.skus[0])}`, label: node.skus[0] });
    }
  } else if (edge) {
    const from = index.nodeById.get(edge.from);
    const to = index.nodeById.get(edge.to);
    if (from?.kind === "supplier") {
      const bare = from.id.split(":").slice(1).join(":");
      links.push({ href: `/diagnostics/supplier/${encodeURIComponent(bare)}`, label: `${from.name} diagnostics`, primary: true });
      links.push({ href: `/orders?tab=imported&poq=${encodeURIComponent(bare)}`, label: "Orders on this route" });
    }
    if (to?.kind === "dc" || to?.kind === "branch") {
      links.push({ href: "/inventory", label: "What arrives here" });
    }
    // A button labelled "Products carried" opened Inventory filtered to ONE of them — the first —
    // two lines below a fact reading "Products carried: 150". Inventory takes a search, not a list,
    // so the link is only offered where it can keep its promise; the rest are named below instead.
    if (edge.skus.length === 1) {
      links.push({ href: `/inventory?q=${encodeURIComponent(edge.skus[0])}`, label: `Product ${edge.skus[0]}` });
    }
  }
  if (!links.length) return null;
  return (
    <div style={{ marginTop: 16, display: "flex", gap: 8, flexWrap: "wrap" }}>
      {links.slice(0, 4).map((l) => (
        <ButtonLink key={l.href + l.label} size="sm" role={l.primary ? "secondary" : "tertiary"} href={l.href}>
          {l.label}
        </ButtonLink>
      ))}
    </div>
  );
}

function NodeBody({ node }: { node: NetworkNode }) {
  const { model, index } = useTwin();
  const { request, summary } = useWorkspaceData();
  const m = node.metrics;
  const currency = summary?.currency ?? request?.currency ?? "USD";
  const affected = affectedBy({ type: "node", id: node.id }, model, index);

  const facts = node.kind === "supplier"
    ? [
        { label: "Delivery reliability", value: m.fill?.mean != null ? `${(m.fill.mean * 100).toFixed(1)}%` : null, note: m.fill?.n != null ? `from ${m.fill.n.toLocaleString("en-US")} ${m.fill.n === 1 ? "delivery" : "deliveries"}` : "not enough history yet" },
        // This is the *mean*, and it read "Lead time 15 days" beside a diagnostics page reading
        // "Typical lead 14 d" — the median of the same deliveries. Two numbers for what a reader
        // calls one thing. The label now says which, and carries the spread the distribution has.
        { label: "Average lead time", value: m.leadDays?.mean != null ? `${Math.round(m.leadDays.mean)} ${Math.round(m.leadDays.mean) === 1 ? "day" : "days"}` : null,
          note: m.leadDays?.p90 != null ? `one in ten takes ${Math.round(m.leadDays.p90)} days or more` : undefined },
        { label: "Open orders", value: m.openPOs?.length ? String(m.openPOs.length) : "0" },
        { label: "Weekly capacity", value: m.capacityPerWeek != null ? `${NUMBER(m.capacityPerWeek)} units` : null },
      ]
    : node.kind === "dc" || node.kind === "branch"
      ? [
          // "31,866.25 units" three lines under a sentence reading "NORTH holds 31,866 units" —
          // the same number at two precisions, on one screen. The engine works in continuous
          // units; the product prints whole ones, and `describe()` already did.
          { label: "Stock on hand", value: m.onHandUnits != null ? `${NUMBER(m.onHandUnits)} units` : null },
          { label: "Stock value", value: m.onHandValue != null ? money(m.onHandValue, currency) : null },
          { label: "Service target", value: m.serviceTarget != null ? `${(m.serviceTarget * 100).toFixed(1)}%` : null },
          { label: "Projected service", value: m.serviceProjected != null ? `${(m.serviceProjected * 100).toFixed(1)}%` : null },
        ]
      : node.kind === "customer"
        ? [
            { label: "Service agreed", value: m.serviceTarget != null ? `${(m.serviceTarget * 100).toFixed(1)}%` : null },
            { label: "Projected", value: m.serviceProjected != null ? `${(m.serviceProjected * 100).toFixed(1)}%` : null },
            { label: "Class", value: m.tier ?? null },
            { label: "Products", value: node.skus.length ? String(node.skus.length) : null },
          ]
        : [{ label: "Country", value: node.region ?? null }, { label: "Inbound lanes", value: String((index.inEdges.get(node.id) ?? []).length) }];

  return (
    <>
      <p style={{ margin: "10px 0 0", fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-700)" }}>
        {describe({ type: "node", id: node.id }, model, index) || STATE_SENTENCE[node.state]}
      </p>

      <div style={{ marginTop: 14 }}><Facts items={facts} /></div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>What ZAAD recommends here</h3>
        <Recommendations targetId={node.id} />
        <Actions node={node} edge={null} index={index} />
      </div>

      <div style={{ marginTop: 16 }}>
        {node.kind === "supplier" && (m.openPOs?.length ?? 0) > 0 && (
          <Disclosure summary="Open orders" hint={`${m.openPOs!.length}`}>
            <dl className="evid">
              {m.openPOs!.map((po) => (
                <div className="evid-row" key={po.id}>
                  <dt><Link href={`/orders?po=${encodeURIComponent(po.id)}`}>{po.id}</Link></dt>
                  <dd>
                    {po.units.toLocaleString("en-US")} units{po.sku ? ` of ${po.sku}` : ""}
                    {po.due ? `, due ${po.due}` : ""}
                    {po.status === "late" && <span className="evid-prov" style={{ color: "var(--bad)", borderColor: "var(--bad-line)" }}>past due</span>}
                    {po.status === "in_transit" && <span className="evid-prov">in transit</span>}
                  </dd>
                </div>
              ))}
            </dl>
          </Disclosure>
        )}

        <Disclosure summary="What depends on this" hint={`${affected.customers.length + affected.stockNodes.length} downstream`}>
          <Evidence items={[
            ...(node.skus.length ? [{ label: "Products", detail: node.skus.slice(0, 8).join(", ") + (node.skus.length > 8 ? ` and ${node.skus.length - 8} more` : "") }] : []),
            ...(affected.stockNodes.length ? [{ label: "Sites served", detail: affected.stockNodes.map((n) => n.name).join(", ") }] : []),
            ...(affected.customers.length ? [{ label: "Customers", detail: affected.customers.map((n) => n.name).join(", ") }] : []),
            ...(m.sharedFailureDomains?.length ? [{ label: "Shared exposure", detail: m.sharedFailureDomains.join(", "), provenance: "OPERATOR_DECLARED" }] : []),
          ]} />
        </Disclosure>

        {node.missing?.length ? (
          <Disclosure summary="What ZAAD does not know here" hint={`${node.missing.length}`}>
            <ul style={{ margin: 0, paddingInlineStart: 18 }}>
              {node.missing.map((x, i) => <li key={i} style={{ marginBottom: 4 }}>{x}</li>)}
            </ul>
          </Disclosure>
        ) : null}

        <TechnicalDetails value={node} hint="normalised model" />
      </div>
    </>
  );
}

function EdgeBody({ edge }: { edge: NetworkEdge }) {
  const { model, index } = useTwin();
  const { summary, request } = useWorkspaceData();
  const currency = summary?.currency ?? request?.currency ?? "USD";
  return (
    <>
      <p style={{ margin: "10px 0 0", fontSize: 13.5, lineHeight: 1.6, color: "var(--ink-700)" }}>
        {describe({ type: "edge", id: edge.id }, model, index)}
      </p>
      <div style={{ marginTop: 14 }}>
        <Facts items={[
          { label: "Usual transit", value: edge.leadDays.normal != null ? `${edge.leadDays.normal} ${edge.leadDays.normal === 1 ? "day" : "days"}` : null },
          // Every other unit figure in the product prints whole units; this one printed the
          // engine's continuous number, so a lane read "34,344.808 / week" — a precision nobody
          // declared and nobody can act on.
          { label: "Capacity", value: edge.capacityPerWeek != null ? `${NUMBER(edge.capacityPerWeek)} units / week` : null },
          { label: "Cost per unit", value: edge.transportCostPerUnit != null ? money(edge.transportCostPerUnit, currency) : null },
          { label: "Products carried", value: edge.skus.length ? String(edge.skus.length) : null },
        ]} />
      </div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>What ZAAD recommends here</h3>
        <Recommendations targetId={edge.id} />
        <Actions node={null} edge={edge} index={index} />
      </div>

      <div style={{ marginTop: 16 }}>
        {edge.skus.length > 1 && (
          <Disclosure summary="Products carried" hint={COUNT(edge.skus.length, "product")}>
            <p style={{ margin: 0, lineHeight: 1.7 }}>{edge.skus.join(", ")}</p>
          </Disclosure>
        )}
        {edge.missing?.length ? (
          <Disclosure summary="What ZAAD does not know here" hint={`${edge.missing.length}`}>
            <ul style={{ margin: 0, paddingInlineStart: 18 }}>
              {edge.missing.map((x, i) => <li key={i} style={{ marginBottom: 4 }}>{x}</li>)}
            </ul>
          </Disclosure>
        ) : null}
        <TechnicalDetails value={edge} hint="normalised model" />
      </div>
    </>
  );
}

export function IntelligencePanel() {
  const { state, index, select, model } = useTwin();
  const selection = state.selection;

  if (!selection) {
    return (
      <div className="side-b">
        <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--ink-950)" }}>Nothing selected</h2>
        <p style={{ margin: "8px 0 0", fontSize: 13.5, color: "var(--ink-600)", lineHeight: 1.6 }}>
          Pick a supplier, lane, site or customer to see its state, what depends on it and what ZAAD
          recommends about it. Tab moves through them from the keyboard.
        </p>
        {model.notes.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Disclosure summary="What this network is built from" hint={`${model.notes.length} notes`}>
              <ul style={{ margin: 0, paddingInlineStart: 18 }}>
                {model.notes.map((n, i) => <li key={i} style={{ marginBottom: 4 }}>{n}</li>)}
              </ul>
            </Disclosure>
          </div>
        )}
      </div>
    );
  }

  const node = selection.type === "node" ? index.nodeById.get(selection.id) : null;
  const edge = selection.type === "edge" ? index.edgeById.get(selection.id) : null;
  if (!node && !edge) return <div className="side-b"><p className="na">That item is no longer in this network.</p></div>;

  const title = node ? node.name : edgeTitle(edge!, index);
  const kind = node ? KIND_LABEL[node.kind] : EDGE_LABEL[edge!.kind];
  const risk = node ? node.risk : edge!.risk;
  const zstate = node ? node.state : edge!.state;

  return (
    <>
      <div className="side-h" style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <p style={{ margin: 0, fontSize: 12, color: "var(--ink-500)" }}>
            {kind}
            {node?.geo?.precision === "approximate" && <span className="tag" data-tone="approx" style={{ marginInlineStart: 8 }}>Placed by country</span>}
          </p>
          <h2 style={{ margin: "4px 0 0", fontSize: 17, fontWeight: 600, letterSpacing: "-.018em", color: "var(--ink-950)" }}>{title}</h2>
          <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>
            {STATE_LABEL[zstate]} · {RISK_LABEL[risk.level]}
          </p>
        </div>
        <button className="zb zb--tertiary zb--sm zb--icon" onClick={() => select(null)} aria-label="Close this panel">
          <X size={15} aria-hidden />
        </button>
      </div>
      <div className="side-b">
        {node ? <NodeBody node={node} /> : <EdgeBody edge={edge!} />}
      </div>
    </>
  );
}
