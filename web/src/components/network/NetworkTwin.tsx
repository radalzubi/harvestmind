"use client";

/**
 * Network Twin: a calm shell. One status line answers "is anything wrong?",
 * one switch chooses NETWORK or MAP, one search finds anything. Everything
 * else appears on selection. The graph and map libraries load lazily and only
 * for the view in use; MAP is never fetched until it is asked for.
 */
import dynamic from "next/dynamic";
import { useEffect, useRef, useState, type ComponentType } from "react";
import { Maximize2, Search, X } from "lucide-react";
import { searchModel } from "@/lib/network/graph";
import { EDGE_LABEL, KIND_LABEL, type SelectionRef } from "@/lib/network/model";
import { IntelligencePanel } from "./IntelligencePanel";
import { TwinProvider, useTwin, type View } from "./store";
import "./network.css";

const Loading = ({ text }: { text: string }) => <div className="twin-loading">{text}</div>;

const VIEWS: Array<{ id: View; label: string; Component: ComponentType | null }> = [
  { id: "network", label: "Network", Component: dynamic(() => import("./NetworkGraph"), { ssr: false, loading: () => <Loading text="Drawing the network…" /> }) },
  { id: "map", label: "Map", Component: dynamic(() => import("./NetworkMap"), { ssr: false, loading: () => <Loading text="Opening the map…" /> }) },
  // A globe would be one more dynamic import reading the same store; it is not offered in V1.
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
    <div className="twin-search">
      <Search size={14} className="ico" />
      <input ref={input} value={q} placeholder="Search suppliers, lanes, SKUs, orders" aria-label="Search the network" role="combobox"
        aria-expanded={open && hits.length > 0} aria-haspopup="listbox" aria-autocomplete="list" aria-controls="twin-search-list"
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

function StatusLine() {
  const { status, state, dispatch, select } = useTwin();
  const open = () => { select(null); dispatch({ type: "panel", open: !(state.panelOpen && !state.selection) }); };
  return (
    <button className={`twin-status ${status.tone}`} onClick={open} aria-label={`${status.headline}. Show summary`}>
      <i />
      <span>{status.headline}</span>
      {status.detail && <span className="detail">· {status.detail}</span>}
    </button>
  );
}

function TwinInner() {
  const { state, dispatch, load, select, model } = useTwin();
  const view = VIEWS.find((v) => v.id === state.view) ?? VIEWS[0];
  const Stage = view.Component;
  const simulating = state.mode === "simulate";
  const subject = state.subject ? (state.subject.type === "node" ? model.nodes.find((n) => n.id === state.subject!.id)?.name : model.edges.find((e) => e.id === state.subject!.id)?.name) : null;
  return (
    <div className={`twin ${simulating ? "simulating" : ""}`} onKeyDown={(e) => { if (e.key === "Escape" && !(e.target instanceof HTMLInputElement)) { select(null); dispatch({ type: "panel", open: false }); } }}>
      <div className="twin-bar" role="toolbar" aria-label="Network Twin controls">
        {simulating ? (
          <div className="twin-simbadge">
            <span className="twin-simbadge-label">Simulation</span>
            {subject && <span className="twin-simbadge-subject">{subject}</span>}
            <button className="tbtn small" onClick={() => dispatch({ type: "simulate:exit" })}><X size={13} /> Exit simulation</button>
          </div>
        ) : <StatusLine />}
        <div className="twin-seg" role="group" aria-label="View">
          {VIEWS.map((v) => <button key={v.id} aria-pressed={state.view === v.id} onClick={() => dispatch({ type: "view", view: v.id })}>{v.label}</button>)}
        </div>
        <div className="twin-bar-spacer" />
        <SearchBox />
      </div>
      <div className={`twin-stage ${state.panelOpen ? "" : "no-panel"}`}>
        <div className="twin-canvas">
          <div className="twin-fill">{Stage ? <Stage /> : <Loading text="This view is not available." />}</div>
          <div className="twin-float">
            <button className="twin-icon" title="Fit to network" aria-label="Fit to network" onClick={() => dispatch({ type: "fit" })}><Maximize2 size={14} /></button>
          </div>
          <div className="twin-source">
            {load.source === "illustrative" ? (
              <>Illustrative development data{load.workspaceError == null && !load.loading ? <> · <button onClick={() => load.setSource("workspace")}>use my workspace</button></> : null}</>
            ) : (
              <>Your workspace data · <button onClick={() => load.setSource("illustrative")}>view the illustrative network</button></>
            )}
          </div>
        </div>
        {state.panelOpen && <IntelligencePanel />}
      </div>
    </div>
  );
}

export function NetworkTwin() {
  return <TwinProvider><TwinInner /></TwinProvider>;
}
