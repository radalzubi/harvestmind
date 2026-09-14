"use client";

/**
 * The Digital Network Twin: two views of one model, one panel, one selection.
 *
 * NETWORK is the relationship graph, MAP is where imported supply comes from. Switching
 * between them keeps the selection, the product filter and the panel — it is a change of
 * lens, not a change of place. The heavy renderers load only when their view is first shown.
 */
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Map as MapIcon, Search, Share2 } from "lucide-react";
import { searchModel } from "@/lib/network/graph";
import type { SelectionRef } from "@/lib/network/model";
import { IntelligencePanel } from "./IntelligencePanel";
import { useTwin } from "./store";
import "./network.css";

const NetworkGraph = dynamic(() => import("./NetworkGraph"), {
  ssr: false,
  loading: () => <div className="twin-fill" style={{ display: "grid", placeItems: "center" }}><p className="phase"><span className="spin" aria-hidden />Drawing your network…</p></div>,
});
const NetworkMap = dynamic(() => import("./NetworkMap"), {
  ssr: false,
  loading: () => <div className="twin-fill" style={{ display: "grid", placeItems: "center" }}><p className="phase"><span className="spin" aria-hidden />Loading the map…</p></div>,
});

function ViewSwitch() {
  const { state, dispatch } = useTwin();
  return (
    <div role="tablist" aria-label="View" className="twin-views">
      {([["network", "Network", Share2], ["map", "Map", MapIcon]] as const).map(([id, label, Icon]) => (
        <button key={id} role="tab" aria-selected={state.view === id} className="twin-view-tab"
          onClick={() => dispatch({ type: "view", view: id })}>
          <Icon size={14} aria-hidden />{label}
        </button>
      ))}
    </div>
  );
}

function TwinSearch() {
  const { model, select } = useTwin();
  const [q, setQ] = useState("");
  const hits = useMemo<SelectionRef[]>(() => (q.trim() ? searchModel(model, q, 6) : []), [q, model]);
  const label = (ref: SelectionRef) =>
    ref.type === "node" ? model.nodes.find((n) => n.id === ref.id)?.name ?? ref.id : model.edges.find((e) => e.id === ref.id)?.name ?? ref.id;

  return (
    <div className="twin-search">
      <Search size={14} aria-hidden />
      <input
        value={q} onChange={(e) => setQ(e.target.value)}
        placeholder="Find a supplier, lane, product or order"
        aria-label="Find a supplier, lane, product or order in this network"
        onKeyDown={(e) => { if (e.key === "Enter" && hits[0]) { select(hits[0], true); setQ(""); } if (e.key === "Escape") setQ(""); }}
      />
      {hits.length > 0 && (
        <ul className="twin-search-hits" role="listbox" aria-label="Matches">
          {hits.map((h) => (
            <li key={`${h.type}:${h.id}`}>
              <button onClick={() => { select(h, true); setQ(""); }}>{label(h)}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SkuFilter() {
  const { model, state, dispatch } = useTwin();
  const skus = useMemo(() => [...new Set(model.nodes.flatMap((n) => n.skus))].sort().slice(0, 250), [model.nodes]);
  if (skus.length < 2) return null;
  return (
    <label className="twin-filter">
      <span className="sr-only">Filter by product</span>
      <select value={state.sku ?? ""} onChange={(e) => dispatch({ type: "sku", sku: e.target.value || null })} aria-label="Filter by product">
        <option value="">All products</option>
        {skus.map((s) => <option key={s} value={s}>{s}</option>)}
      </select>
    </label>
  );
}

export function NetworkTwin() {
  const { state, status, areas, select, dispatch } = useTwin();
  const router = useRouter();
  const params = useSearchParams();

  // The selection lives in the address bar, so a decision can hand the Twin a place to open at
  // and a Twin selection can be sent to someone else.
  useEffect(() => {
    const q = new URLSearchParams(params.toString());
    if (state.selection?.type === "node") { q.set("node", state.selection.id); q.delete("edge"); }
    else if (state.selection?.type === "edge") { q.set("edge", state.selection.id); q.delete("node"); }
    else { q.delete("node"); q.delete("edge"); }
    if (state.sku) q.set("sku", state.sku); else q.delete("sku");
    if (state.view !== "network") q.set("view", state.view); else q.delete("view");
    const next = q.toString();
    if (next !== params.toString()) router.replace(next ? `/network?${next}` : "/network", { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.selection, state.sku, state.view]);

  const attention = areas.filter((a) => a.level === "attention");

  return (
    <div className="twin">
      <header className="twin-bar">
        <div className="twin-standing">
          <span className="status-dot" data-tone={status.tone} aria-hidden />
          <div>
            <strong>{status.headline}</strong>
            {status.detail && <span className="twin-standing-sub"> · {status.detail}</span>}
          </div>
        </div>
        <div className="twin-bar-spacer" />
        <TwinSearch />
        <SkuFilter />
        <ViewSwitch />
      </header>

      {attention.length > 0 && (
        <div className="twin-areas" role="list" aria-label="Areas needing attention">
          {attention.slice(0, 5).map((a) => (
            <button key={a.id} role="listitem" className="twin-area" onClick={() => select(a.lead, true)}>
              <span className="twin-area-dot" aria-hidden />{a.title}
            </button>
          ))}
        </div>
      )}

      <div className="twin-stage">
        <div className="twin-canvas">
          {state.view === "network" ? <NetworkGraph /> : <NetworkMap />}
        </div>
        {state.panelOpen && (
          <button className="twin-panel-scrim" aria-label="Close the details panel" onClick={() => dispatch({ type: "panel", open: false })} />
        )}
        <aside className={`twin-panel${state.panelOpen ? " open" : ""}`} aria-label="Details">
          <IntelligencePanel />
        </aside>
      </div>
    </div>
  );
}
