"use client";

/**
 * Network Twin state: which view, LIVE or SIMULATE, the selection, hover,
 * scenario overrides, and the derived model the visuals read. LIVE data is
 * never written; simulation is a derived view computed from the live model
 * plus overrides on every change and thrown away when the mode returns to LIVE.
 */
import { createContext, useCallback, useContext, useMemo, useReducer, type ReactNode } from "react";
import { buildIndex, type NetworkIndex } from "@/lib/network/graph";
import { layoutNodes, type Placed } from "@/lib/network/layout";
import type { NetworkModel, SelectionRef } from "@/lib/network/model";
import { pickEngine, type ScenarioEngine, type ScenarioOverride, type ScenarioResult } from "@/lib/network/scenario";
import { useNetworkModel, type NetworkLoad } from "@/lib/network/loader";

export type View = "network" | "map" | "globe";
export type Mode = "live" | "simulate";

interface TwinState {
  view: View;
  mode: Mode;
  selection: SelectionRef | null;
  hover: SelectionRef | null;
  overrides: ScenarioOverride[];
  panelOpen: boolean;
  /** Incremented when a view should re-fit to the whole network. */
  fitSignal: number;
  /** Incremented when a view should centre on the selection (search, alternatives). */
  focusSignal: number;
}

type Action =
  | { type: "view"; view: View }
  | { type: "mode"; mode: Mode }
  | { type: "select"; ref: SelectionRef | null; focus?: boolean }
  | { type: "hover"; ref: SelectionRef | null }
  | { type: "override:add"; override: ScenarioOverride }
  | { type: "override:remove"; id: string }
  | { type: "override:clear" }
  | { type: "panel"; open: boolean }
  | { type: "fit" };

function reducer(s: TwinState, a: Action): TwinState {
  switch (a.type) {
    case "view": return s.view === a.view ? s : { ...s, view: a.view, fitSignal: s.fitSignal + 1 };
    case "mode": return s.mode === a.mode ? s : { ...s, mode: a.mode, panelOpen: true };
    case "select": {
      const same = (s.selection?.type === a.ref?.type && s.selection?.id === a.ref?.id);
      if (same && !a.focus) return s;
      return { ...s, selection: a.ref, panelOpen: true, focusSignal: a.focus ? s.focusSignal + 1 : s.focusSignal };
    }
    case "hover": return (s.hover?.id === a.ref?.id && s.hover?.type === a.ref?.type) ? s : { ...s, hover: a.ref };
    case "override:add": return { ...s, overrides: [...s.overrides, a.override], mode: "simulate" };
    case "override:remove": return { ...s, overrides: s.overrides.filter((o) => o.id !== a.id) };
    case "override:clear": return { ...s, overrides: [] };
    case "panel": return { ...s, panelOpen: a.open };
    case "fit": return { ...s, fitSignal: s.fitSignal + 1 };
  }
}

export interface Twin {
  state: TwinState;
  dispatch: (a: Action) => void;
  load: NetworkLoad;
  /** The untouched model for the current source. */
  live: NetworkModel;
  /** What the visuals draw: the live model, or the scenario view in SIMULATE. */
  model: NetworkModel;
  index: NetworkIndex;
  layout: Map<string, Placed>;
  scenario: ScenarioResult | null;
  engine: ScenarioEngine;
  /** Dependency neighbourhood of the selection; null when nothing is selected. */
  related: { nodes: Set<string>; edges: Set<string> } | null;
  select: (ref: SelectionRef | null, focus?: boolean) => void;
  hover: (ref: SelectionRef | null) => void;
}

const TwinContext = createContext<Twin | null>(null);

export function TwinProvider({ children }: { children: ReactNode }) {
  const load = useNetworkModel();
  const [state, dispatch] = useReducer(reducer, { view: "network", mode: "live", selection: null, hover: null, overrides: [], panelOpen: true, fitSignal: 0, focusSignal: 0 });
  const live = load.model;
  const liveIndex = useMemo(() => buildIndex(live), [live]);
  const layout = useMemo(() => layoutNodes(live), [live]);
  const engine = useMemo(() => pickEngine(), []);
  const scenario = useMemo(() => state.mode === "simulate" ? engine.evaluate(live, state.overrides, liveIndex) : null, [state.mode, state.overrides, live, liveIndex, engine]);
  const model = scenario ? scenario.view : live;
  const index = useMemo(() => (model === live ? liveIndex : buildIndex(model)), [model, live, liveIndex]);
  // a selection that no longer exists (source switched) is dropped rather than shown stale
  const selection = state.selection && (state.selection.type === "node" ? index.nodeById.has(state.selection.id) : index.edgeById.has(state.selection.id)) ? state.selection : null;
  const related = useMemo(() => index.related(selection), [index, selection]);
  const select = useCallback((ref: SelectionRef | null, focus = false) => dispatch({ type: "select", ref, focus }), []);
  const hover = useCallback((ref: SelectionRef | null) => dispatch({ type: "hover", ref }), []);
  const value = useMemo<Twin>(() => ({ state: { ...state, selection }, dispatch, load, live, model, index, layout, scenario, engine, related, select, hover }),
    [state, selection, load, live, model, index, layout, scenario, engine, related, select, hover]);
  return <TwinContext.Provider value={value}>{children}</TwinContext.Provider>;
}

export function useTwin(): Twin {
  const ctx = useContext(TwinContext);
  if (!ctx) throw new Error("useTwin outside TwinProvider");
  return ctx;
}

/** Colour for a ZAAD state as an RGB triple, for deck.gl layers. */
export const STATE_RGB: Record<string, [number, number, number]> = {
  LEAN: [14, 159, 110], PROTECT: [217, 119, 6], ALLOCATE: [194, 65, 12], RECOVER: [29, 78, 216],
};
export const INK: Record<string, [number, number, number]> = { 900: [24, 24, 27], 700: [63, 63, 70], 500: [113, 113, 122], 400: [161, 161, 170], 300: [212, 212, 216] };
