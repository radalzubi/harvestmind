"use client";

/**
 * Network Twin: the page shell, the control strip, the stage and the panel.
 * The shell renders at once; the graph and map libraries load lazily and
 * only for the view in use. GLOBE is a registered view with no component
 * yet, so adding one later is a dynamic import in VIEWS and nothing else.
 */
import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type ComponentType } from "react";
import { Maximize2, PanelRightClose, PanelRightOpen, Search } from "lucide-react";
import { searchModel } from "@/lib/network/graph";
import { EDGE_LABEL, KIND_LABEL, STATE_LABEL, type SelectionRef, type ZaadState } from "@/lib/network/model";
import { IntelligencePanel } from "./IntelligencePanel";
import { TwinProvider, useTwin, type View } from "./store";
import "./network.css";

const Loading = ({ text }: { text: string }) => <div className="twin-loading">{text}</div>;

const VIEWS: Array<{ id: View; label: string; Component: ComponentType | null; title?: string }> = [
  { id: "network", label: "NETWORK", Component: dynamic(() => import("./NetworkGraph"), { ssr: false, loading: () => <Loading text="Drawing the network…" /> }) },
  { id: "map", label: "MAP", Component: dynamic(() => import("./NetworkMap"), { ssr: false, loading: () => <Loading text="Loading the map…" /> }) },
  // A globe would be: dynamic(() => import("./NetworkGlobe"), { ssr: false }) reading the same store.
  { id: "globe", label: "GLOBE", Component: null, title: "Globe view is planned; the architecture hook is in place" },
];

function SearchBox() {
  const { model, select } = useTwin();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const hits = open ? searchModel(model, q) : [];
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement)) { e.preventDefault(); input.current?.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const label = (r: SelectionRef) => r.type === "node" ? model.nodes.find((n) => n.id === r.id) : model.edges.find((e) => e.id === r.id);
  const choose = (r: SelectionRef) => { select(r, true); setOpen(false); setQ(""); input.current?.blur(); };
  return (
    <div className="twin-search" role="combobox" aria-expanded={open && hits.length > 0} aria-haspopup="listbox" aria-owns="twin-search-list">
      <Search size={14} className="ico" />
      <input ref={input} value={q} placeholder="Search nodes, lanes, SKUs  ( / )" aria-label="Search the network" aria-autocomplete="list" aria-controls="twin-search-list"
        onChange={(e) => { setQ(e.target.value); setOpen(true); setCursor(0); }} onFocus={() => setOpen(true)} onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { e.preventDefault(); setCursor((c) => Math.min(hits.length - 1, c + 1)); }
          else if (e.key === "ArrowUp") { e.preventDefault(); setCursor((c) => Math.max(0, c - 1)); }
          else if (e.key === "Enter" && hits[cursor]) { e.preventDefault(); choose(hits[cursor]); }
          else if (e.key === "Escape") { setOpen(false); input.current?.blur(); }
        }} />
      {open && hits.length > 0 && (
        <ul className="twin-search-list" id="twin-search-list" role="listbox">
          {hits.map((h, i) => {
            const t = label(h);
            if (!t) return null;
            const kind = h.type === "node" ? KIND_LABEL[(t as { kind: keyof typeof KIND_LABEL }).kind] : EDGE_LABEL[(t as { kind: keyof typeof EDGE_LABEL }).kind];
            return <li key={h.type + h.id} role="option" aria-selected={i === cursor} onMouseDown={() => choose(h)} onMouseEnter={() => setCursor(i)}>{t.name}<span className="kind">{kind}</span></li>;
          })}
        </ul>
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="twin-legend" aria-hidden>
      {(["LEAN", "PROTECT", "ALLOCATE", "RECOVER"] as ZaadState[]).map((s) => <span key={s} className={`st-${s}`}><i style={{ background: "var(--st)" }} />{STATE_LABEL[s]}</span>)}
    </div>
  );
}

function TwinInner() {
  const { state, dispatch, load, select } = useTwin();
  const view = VIEWS.find((v) => v.id === state.view) ?? VIEWS[0];
  const Stage = view.Component;
  return (
    <div className="twin" onKeyDown={(e) => { if (e.key === "Escape" && !(e.target instanceof HTMLInputElement)) select(null); }}>
      <div className="twin-bar" role="toolbar" aria-label="Network Twin controls">
        <div className="twin-bar-title">
          Network Twin
          {load.source === "workspace" ? <span className="twin-chip ws sub">Workspace data</span> : <span className="twin-chip illus sub">Illustrative development data</span>}
          {load.loading && <span className="twin-chip sub">Reading your workspace…</span>}
        </div>
        <div className="twin-seg" role="group" aria-label="View">
          {VIEWS.map((v) => <button key={v.id} aria-pressed={state.view === v.id} disabled={!v.Component} title={v.title} onClick={() => dispatch({ type: "view", view: v.id })}>{v.label}</button>)}
        </div>
        <div className="twin-seg mode" role="group" aria-label="Mode">
          <button data-mode="live" aria-pressed={state.mode === "live"} onClick={() => dispatch({ type: "mode", mode: "live" })}>LIVE</button>
          <button data-mode="simulate" aria-pressed={state.mode === "simulate"} onClick={() => dispatch({ type: "mode", mode: "simulate" })}>SIMULATE</button>
        </div>
        <div className="twin-bar-spacer" />
        {load.workspaceError == null && load.source === "workspace" && (
          <button className="twin-chip-btn" onClick={() => load.setSource("illustrative")}>Show illustrative network</button>
        )}
        {load.source === "illustrative" && !load.workspaceError && !load.loading && (
          <button className="twin-chip-btn" onClick={() => load.setSource("workspace")}>Show workspace network</button>
        )}
        <SearchBox />
        <button className="twin-icon" title="Fit to network" aria-label="Fit to network" onClick={() => dispatch({ type: "fit" })}><Maximize2 size={14} /></button>
        <button className="twin-icon" title={state.panelOpen ? "Hide panel" : "Show panel"} aria-label={state.panelOpen ? "Hide panel" : "Show panel"} onClick={() => dispatch({ type: "panel", open: !state.panelOpen })}>
          {state.panelOpen ? <PanelRightClose size={14} /> : <PanelRightOpen size={14} />}
        </button>
      </div>
      <div className={`twin-stage ${state.panelOpen ? "" : "no-panel"}`}>
        <div className="twin-canvas">
          <div className="twin-fill">{Stage ? <Stage /> : <Loading text="Globe view is not part of V1." />}</div>
          {state.mode === "simulate" && <div className="twin-notice warn" style={{ bottom: "auto", top: 16, left: "50%", transform: "translateX(-50%)" }}>Simulation: an ephemeral scenario over the live picture. Nothing here changes your data.</div>}
          {load.source === "illustrative" && <div className="twin-notice illus">Illustrative development data{load.workspaceError ? ` · ${load.workspaceError}` : ""}</div>}
          <Legend />
        </div>
        {state.panelOpen && <IntelligencePanel />}
      </div>
    </div>
  );
}

export function NetworkTwin() {
  return <TwinProvider><TwinInner /></TwinProvider>;
}
