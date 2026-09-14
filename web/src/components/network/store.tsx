"use client";

/**
 * Network Twin state: which view, what is selected, what is hovered.
 *
 * The model comes from the one workspace read the whole product shares, so the Twin can never
 * show a different picture from Decisions or Home. There is no simulation here: the released
 * system has no scenario endpoint, and an authenticated workspace must not show a made-up
 * optimizer result. Selection and filters survive a view switch.
 */
import { createContext, useCallback, useContext, useMemo, useReducer, type ReactNode } from "react";
import { attentionAreas, statusLine, type AttentionArea } from "@/lib/network/attention";
import { groupCustomers, isGroupId, type GroupInfo } from "@/lib/network/groups";
import { layoutNodes, type Placed } from "@/lib/network/layout";
import type { NetworkModel, SelectionRef } from "@/lib/network/model";
import type { NetworkIndex } from "@/lib/network/graph";
import { buildIndex } from "@/lib/network/graph";

export type View = "network" | "map";

interface TwinState {
  view: View;
  selection: SelectionRef | null;
  hover: SelectionRef | null;
  /** A SKU filter carried between views. */
  sku: string | null;
  panelOpen: boolean;
  expandedGroups: Set<string>;
  fitSignal: number;
  focusSignal: number;
}

type Action =
  | { type: "view"; view: View }
  | { type: "select"; ref: SelectionRef | null; focus?: boolean }
  | { type: "hover"; ref: SelectionRef | null }
  | { type: "sku"; sku: string | null }
  | { type: "group:toggle"; id: string }
  | { type: "panel"; open: boolean }
  | { type: "fit" };

function reducer(s: TwinState, a: Action): TwinState {
  switch (a.type) {
    // A view switch keeps the selection, the SKU filter and the panel; only the camera refits.
    case "view": return s.view === a.view ? s : { ...s, view: a.view, fitSignal: s.fitSignal + 1 };
    case "select": {
      const same = s.selection?.type === a.ref?.type && s.selection?.id === a.ref?.id;
      if (same && !a.focus) return s;
      return { ...s, selection: a.ref, panelOpen: a.ref != null, focusSignal: a.focus ? s.focusSignal + 1 : s.focusSignal };
    }
    case "hover": return (s.hover?.id === a.ref?.id && s.hover?.type === a.ref?.type) ? s : { ...s, hover: a.ref };
    case "sku": return { ...s, sku: a.sku, fitSignal: s.fitSignal + 1 };
    case "group:toggle": { const next = new Set(s.expandedGroups); if (next.has(a.id)) next.delete(a.id); else next.add(a.id); return { ...s, expandedGroups: next }; }
    case "panel": return { ...s, panelOpen: a.open };
    case "fit": return { ...s, fitSignal: s.fitSignal + 1 };
  }
}

export interface Twin {
  state: TwinState;
  dispatch: (a: Action) => void;
  /** The operator's own network, untouched. */
  model: NetworkModel;
  index: NetworkIndex;
  /** What the NETWORK view draws: the model with large customer sets collapsed. */
  display: NetworkModel;
  groups: GroupInfo[];
  layout: Map<string, Placed>;
  areas: AttentionArea[];
  status: ReturnType<typeof statusLine>;
  related: { nodes: Set<string>; edges: Set<string> } | null;
  select: (ref: SelectionRef | null, focus?: boolean) => void;
  hover: (ref: SelectionRef | null) => void;
}

const TwinContext = createContext<Twin | null>(null);

/** Keep only what carries a SKU, plus everything structurally between what is left. */
function filterBySku(model: NetworkModel, sku: string | null): NetworkModel {
  if (!sku) return model;
  const nodes = model.nodes.filter((n) => n.skus.includes(sku) || n.kind === "port");
  const keep = new Set(nodes.map((n) => n.id));
  const edges = model.edges.filter((e) => keep.has(e.from) && keep.has(e.to) && (e.skus.length === 0 || e.skus.includes(sku)));
  const connected = new Set(edges.flatMap((e) => [e.from, e.to]));
  return { ...model, nodes: nodes.filter((n) => n.kind !== "port" || connected.has(n.id)), edges };
}

export function TwinProvider({ model: source, index: sourceIndex, initial, children }: {
  model: NetworkModel;
  index: NetworkIndex;
  initial?: Partial<Pick<TwinState, "view" | "selection" | "sku">>;
  children: ReactNode;
}) {
  const [state, dispatch] = useReducer(reducer, {
    view: initial?.view ?? "network",
    selection: initial?.selection ?? null,
    hover: null,
    sku: initial?.sku ?? null,
    panelOpen: initial?.selection != null,
    expandedGroups: new Set<string>(),
    fitSignal: 0,
    focusSignal: 0,
  });

  const model = useMemo(() => filterBySku(source, state.sku), [source, state.sku]);
  const index = useMemo(() => (model === source ? sourceIndex : buildIndex(model)), [model, source, sourceIndex]);
  const grouped = useMemo(() => groupCustomers(model, state.expandedGroups), [model, state.expandedGroups]);
  const layout = useMemo(() => layoutNodes(grouped.model), [grouped.model]);
  const areas = useMemo(() => attentionAreas(model, index), [model, index]);
  const status = useMemo(() => statusLine(areas), [areas]);
  const selection = state.selection && (state.selection.type === "node"
    ? (index.nodeById.has(state.selection.id) || isGroupId(state.selection.id))
    : index.edgeById.has(state.selection.id)) ? state.selection : null;
  const related = useMemo(() => index.related(selection), [index, selection]);
  const select = useCallback((ref: SelectionRef | null, focus = false) => dispatch({ type: "select", ref, focus }), []);
  const hover = useCallback((ref: SelectionRef | null) => dispatch({ type: "hover", ref }), []);

  const value = useMemo<Twin>(() => ({
    state: { ...state, selection }, dispatch, model, index,
    display: grouped.model, groups: grouped.groups, layout, areas, status, related, select, hover,
  }), [state, selection, model, index, grouped, layout, areas, status, related, select, hover]);

  return <TwinContext.Provider value={value}>{children}</TwinContext.Provider>;
}

export function useTwin(): Twin {
  const ctx = useContext(TwinContext);
  if (!ctx) throw new Error("useTwin must be used inside <TwinProvider>");
  return ctx;
}

/** One palette for both views, taken from the design tokens. */
export const STATE_COLOR: Record<string, string> = {
  LEAN: "#0E9F6E", PROTECT: "#D97706", ALLOCATE: "#C2410C", RECOVER: "#1D4ED8",
};
export const INK = { 950: "#0A0A0F", 900: "#18181B", 700: "#3F3F46", 500: "#71717A", 400: "#A1A1AA", 300: "#D4D4D8" };
