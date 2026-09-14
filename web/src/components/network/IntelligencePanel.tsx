"use client";

/**
 * One panel for whatever is selected. It adapts to the object — supplier, lane, site, port,
 * customer — but the reading order never changes: what this is, what ZAAD recommends about it,
 * what is known, then the technical detail. Anything the workspace does not carry is stated as
 * missing rather than left to look like a zero.
 */
import Link from "next/link";
import { ArrowUpRight, X } from "lucide-react";
import { describe, edgeTitle, affectedBy } from "@/lib/network/attention";
import { EDGE_LABEL, KIND_LABEL, RISK_LABEL, STATE_LABEL, STATE_SENTENCE } from "@/lib/network/model";
import type { NetworkEdge, NetworkNode } from "@/lib/network/model";
import { Disclosure, Evidence, Facts, TechnicalDetails } from "@/components/workspace/ui";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { money } from "@/lib/zaad/decisions";
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
            <ArrowUpRight size={14} style={{ marginInlineStart: "auto", color: "var(--ink-400)" }} aria-hidden />
          </div>
          <h4 className="dec-h" style={{ fontSize: 14 }}>{d.headline}</h4>
        </Link>
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
        { label: "Delivery reliability", value: m.fill?.mean != null ? `${(m.fill.mean * 100).toFixed(1)}%` : null, note: m.fill?.n != null ? `from ${m.fill.n} deliveries` : "not enough history yet" },
        { label: "Lead time", value: m.leadDays?.mean != null ? `${Math.round(m.leadDays.mean)} days` : null },
        { label: "Open orders", value: m.openPOs?.length ? String(m.openPOs.length) : "0" },
        { label: "Weekly capacity", value: m.capacityPerWeek != null ? m.capacityPerWeek.toLocaleString("en-US") : null },
      ]
    : node.kind === "dc" || node.kind === "branch"
      ? [
          { label: "Stock on hand", value: m.onHandUnits != null ? `${m.onHandUnits.toLocaleString("en-US")} units` : null },
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
      </div>

      <div style={{ marginTop: 16 }}>
        {node.kind === "supplier" && (m.openPOs?.length ?? 0) > 0 && (
          <Disclosure summary="Open orders" hint={`${m.openPOs!.length}`}>
            <dl className="evid">
              {m.openPOs!.map((po) => (
                <div className="evid-row" key={po.id}>
                  <dt>{po.id}</dt>
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
          { label: "Usual transit", value: edge.leadDays.normal != null ? `${edge.leadDays.normal} days` : null },
          { label: "Capacity", value: edge.capacityPerWeek != null ? `${edge.capacityPerWeek.toLocaleString("en-US")} / week` : null },
          { label: "Cost per unit", value: edge.transportCostPerUnit != null ? money(edge.transportCostPerUnit, currency) : null },
          { label: "Products carried", value: edge.skus.length ? String(edge.skus.length) : null },
        ]} />
      </div>

      <div style={{ marginTop: 18 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>What ZAAD recommends here</h3>
        <Recommendations targetId={edge.id} />
      </div>

      <div style={{ marginTop: 16 }}>
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
