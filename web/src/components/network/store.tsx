"use client";

/**
 * Network Twin state: which view, the selection, hover, an optional
 * simulation, and the derived model the visuals read. LIVE data is never
 * written; a simulation is a derived view computed from the live model plus
 * overrides and thrown away on exit.
 */
import { createContext, useCallback, useContext, useMemo, useReducer, type ReactNode } from "react";
import { attentionAreas, statusLine, type AttentionArea } from "@/lib/network/attention";
import { buildIndex, type NetworkIndex } from "@/lib/network/graph";
import { groupCustomers, isGroupId, type GroupInfo } from "@/lib/network/groups";
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
  /** What the simulation was started from; the panel offers presets for it. */
  subject: SelectionRef | null;
  panelOpen: boolean;
  expandedGroups: Set<string>;
  fitSignal: number;
  focusSignal: number;
}

type Action =
  | { type: "view"; view: View }
  | { type: "select"; ref: SelectionRef | null; focus?: boolean }
  | { type: "hover"; ref: SelectionRef | null }
  | { type: "simulate:start"; subject: SelectionRef | null }
  | { type: "simulate:exit" }
  | { type: "override:add"; overrides: Array<Omit<ScenarioOverride, "id">> }
  | { type: "override:remove"; id: string }
  | { type: "override:clear" }
  | { type: "group:toggle"; id: string }
  | { type: "panel"; open: boolean }
  | { type: "fit" };

let seq = 0;

function reducer(s: TwinState, a: Action): TwinState {
  switch (a.type) {
    case "view": return s.view === a.view ? s : { ...s, view: a.view, fitSignal: s.fitSignal + 1 };
    case "select": {
      const same = s.selection?.type === a.ref?.type && s.selection?.id === a.ref?.id;
      if (same && !a.focus) return s;
      return { ...s, selection: a.ref, panelOpen: a.ref != null || s.mode === "simulate", focusSignal: a.focus ? s.focusSignal + 1 : s.focusSignal };
    }
    case "hover": return (s.hover?.id === a.ref?.id && s.hover?.type === a.ref?.type) ? s : { ...s, hover: a.ref };
    case "simulate:start": return { ...s, mode: "simulate", subject: a.subject ?? s.selection, panelOpen: true };
    case "simulate:exit": return { ...s, mode: "live", overrides: [], subject: null, panelOpen: s.selection != null };
    case "override:add": return { ...s, mode: "simulate", overrides: [...s.overrides, ...a.overrides.map((o) => ({ ...o, id: `${o.kind}_${o.targetId}_${++seq}` }))], panelOpen: true };
    case "override:remove": return { ...s, overrides: s.overrides.filter((o) => o.id !== a.id) };
    case "override:clear": return { ...s, overrides: [] };
    case "group:toggle": { const next = new Set(s.expandedGroups); if (next.has(a.id)) next.delete(a.id); else next.add(a.id); return { ...s, expandedGroups: next }; }
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
  /** What the panel and map read: the live model, or the scenario view in a simulation. */
  model: NetworkModel;
  index: NetworkIndex;
  /** What the NETWORK view draws: `model` with large customer sets collapsed. */
  display: NetworkModel;
  groups: GroupInfo[];
  layout: Map<string, Placed>;
  scenario: ScenarioResult | null;
  engine: ScenarioEngine;
  areas: AttentionArea[];
  status: ReturnType<typeof statusLine>;
  related: { nodes: Set<string>; edges: Set<string> } | null;
  select: (ref: SelectionRef | null, focus?: boolean) => void;
  hover: (ref: SelectionRef | null) => void;
}

const TwinContext = createContext<Twin | null>(null);

export function TwinProvider({ children }: { children: ReactNode }) {
  const load = useNetworkModel();
  const [state, dispatch] = useReducer(reducer, { view: "network", mode: "live", selection: null, hover: null, overrides: [], subject: null, panelOpen: false, expandedGroups: new Set<string>(), fitSignal: 0, focusSignal: 0 });
  const live = load.model;
  const liveIndex = useMemo(() => buildIndex(live), [live]);
  const engine = useMemo(() => pickEngine(), []);
  const scenario = useMemo(() => state.mode === "simulate" && state.overrides.length ? engine.evaluate(live, state.overrides, liveIndex) : null, [state.mode, state.overrides, live, liveIndex, engine]);
  const model = scenario ? scenario.view : live;
  const index = useMemo(() => (model === live ? liveIndex : buildIndex(model)), [model, live, liveIndex]);
  const grouped = useMemo(() => groupCustomers(model, state.expandedGroups), [model, state.expandedGroups]);
  const layout = useMemo(() => layoutNodes(groupCustomers(live, state.expandedGroups).model), [live, state.expandedGroups]);
  const areas = useMemo(() => attentionAreas(model, index), [model, index]);
  const status = useMemo(() => statusLine(areas), [areas]);
  const selection = state.selection && (state.selection.type === "node" ? (index.nodeById.has(state.selection.id) || isGroupId(state.selection.id)) : index.edgeById.has(state.selection.id)) ? state.selection : null;
  const related = useMemo(() => index.related(selection), [index, selection]);
  const select = useCallback((ref: SelectionRef | null, focus = false) => dispatch({ type: "select", ref, focus }), []);
  const hover = useCallback((ref: SelectionRef | null) => dispatch({ type: "hover", ref }), []);
  const value = useMemo<Twin>(() => ({ state: { ...state, selection }, dispatch, load, live, model, index, display: grouped.model, groups: grouped.groups, layout, scenario, engine, areas, status, related, select, hover }),
    [state, selection, load, live, model, index, grouped, layout, scenario, engine, areas, status, related, select, hover]);
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
