"use client";

/**
 * NETWORK view: the supply graph as a stable, layered diagram (React Flow).
 * Positions come from `layoutNodes`, never from a force simulation, so the
 * picture is the same every time and people can remember where things are.
 */
import { memo, useCallback, useEffect, useMemo, useRef } from "react";
import {
  Background, BackgroundVariant, BaseEdge, EdgeLabelRenderer, Handle, Position, ReactFlow, ReactFlowProvider, getBezierPath, useReactFlow,
  type Edge, type EdgeChange, type EdgeProps, type Node, type NodeChange, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Anchor, Factory, Store, Users, Warehouse } from "lucide-react";
import type { NetworkEdge, NetworkNode, NodeKind, ZaadState } from "@/lib/network/model";
import { STATE_LABEL } from "@/lib/network/model";
import { useTwin } from "./store";

type TNodeData = { node: NetworkNode; dim: boolean; exposed: boolean; metric: string | null };
type TEdgeData = { edge: NetworkEdge; dim: boolean; exposed: boolean; showLabel: boolean };
type TNode = Node<TNodeData, "twin">;
type TEdge = Edge<TEdgeData, "twin">;

const ICON: Record<NodeKind, typeof Factory> = { supplier: Factory, port: Anchor, dc: Warehouse, branch: Store, customer: Users };
const NODE_W = 208, NODE_H = 66;

function metricFor(n: NetworkNode): string | null {
  const m = n.metrics;
  switch (n.kind) {
    case "supplier": return m.fill?.mean != null ? `fill ${Math.round(m.fill.mean * 100)}%` : m.leadDays?.mean != null ? `lead ${Math.round(m.leadDays.mean)} d` : null;
    case "port": return m.dwellDays?.mean != null ? `dwell ${m.dwellDays.mean} d` : null;
    case "dc": case "branch": return m.onHandUnits != null ? `${m.onHandUnits.toLocaleString()} on hand` : null;
    case "customer": return m.demandPerWeek != null ? `${m.demandPerWeek.toLocaleString()} / wk` : null;
  }
}

const TwinNode = memo(function TwinNode({ data, selected }: NodeProps<TNode>) {
  const { node, dim, exposed, metric } = data;
  const Icon = ICON[node.kind];
  return (
    <div className={`tn kind-${node.kind} st-${node.state} ${selected ? "selected" : ""} ${dim ? "dim" : ""} ${exposed ? "exposed" : ""}`} title={node.name}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <div className="tn-ico"><Icon size={14} strokeWidth={1.8} /></div>
      <div className="tn-name">{node.name}</div>
      <div className="tn-sub">{node.subtitle ?? " "}</div>
      <div className="tn-foot">
        <span className="state-pill"><i />{STATE_LABEL[node.state]}</span>
        {metric && <span className="tn-metric">{metric}</span>}
      </div>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  );
});

const EDGE_STROKE: Record<ZaadState, string> = { LEAN: "#A1A1AA", PROTECT: "#D97706", ALLOCATE: "#C2410C", RECOVER: "#1D4ED8" };

const TwinEdge = memo(function TwinEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, selected }: EdgeProps<TEdge>) {
  const [path, lx, ly] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.28 });
  if (!data) return null;
  const { edge, dim, exposed, showLabel } = data;
  const standby = edge.name.toLowerCase().includes("alternative");
  const stroke = selected ? "#0E9F6E" : exposed || edge.state !== "LEAN" ? EDGE_STROKE[edge.state] : standby ? "#D4D4D8" : "#A1A1AA";
  const dash = edge.kind === "transfer" ? "6 5" : edge.kind === "supply" ? "2 4" : standby ? "3 5" : undefined;
  return (
    <>
      <BaseEdge id={id} path={path} interactionWidth={18} className="twin-edge-path"
        style={{ stroke, strokeWidth: selected ? 2.5 : exposed ? 2.2 : 1.5, strokeDasharray: dash, opacity: dim ? 0.18 : 1, transition: "opacity .18s, stroke .18s" }} />
      {showLabel && (
        <EdgeLabelRenderer>
          <div className="twin-edge-label" style={{ left: lx, top: ly }}>
            {edge.name}{edge.leadDays.current != null ? ` · ${edge.leadDays.current} d` : ""}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
});

const nodeTypes = { twin: TwinNode };
const edgeTypes = { twin: TwinEdge };

function Graph() {
  const { model, layout, state, related, scenario, select, hover, dispatch } = useTwin();
  const rf = useReactFlow<TNode, TEdge>();
  const sel = state.selection, hov = state.hover;

  const nodes = useMemo<TNode[]>(() => model.nodes.map((n) => {
    const p = layout.get(n.id) ?? { x: 0, y: 0 };
    return {
      id: n.id, type: "twin", position: { x: p.x, y: p.y }, width: NODE_W, height: NODE_H, draggable: false, selectable: true, focusable: true,
      selected: sel?.type === "node" && sel.id === n.id,
      data: { node: n, dim: related != null && !related.nodes.has(n.id), exposed: scenario?.exposed.nodes.has(n.id) ?? false, metric: metricFor(n) },
    };
  }), [model, layout, sel, related, scenario]);

  const edges = useMemo<TEdge[]>(() => model.edges.map((e) => ({
    id: e.id, type: "twin", source: e.from, target: e.to, selectable: true, focusable: true,
    selected: sel?.type === "edge" && sel.id === e.id,
    data: { edge: e, dim: related != null && !related.edges.has(e.id), exposed: scenario?.exposed.edges.has(e.id) ?? false,
      showLabel: (sel?.type === "edge" && sel.id === e.id) || (hov?.type === "edge" && hov.id === e.id) },
  })), [model, sel, hov, related, scenario]);

  // keyboard and mouse selection both arrive as 'select' changes
  const onNodesChange = useCallback((changes: NodeChange<TNode>[]) => {
    for (const c of changes) if (c.type === "select" && c.selected) { select({ type: "node", id: c.id }); return; }
  }, [select]);
  const onEdgesChange = useCallback((changes: EdgeChange<TEdge>[]) => {
    for (const c of changes) if (c.type === "select" && c.selected) { select({ type: "edge", id: c.id }); return; }
  }, [select]);

  // refit when the stage changes size (panel toggled, window resized, phone rotated)
  useEffect(() => {
    const el = document.querySelector(".twin-fill");
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => { rf.fitView({ padding: 0.18, duration: 0 }); });
    ro.observe(el);
    return () => ro.disconnect();
  }, [rf]);

  const fitSeen = useRef(state.fitSignal);
  useEffect(() => {
    if (fitSeen.current === state.fitSignal) return;
    fitSeen.current = state.fitSignal;
    rf.fitView({ padding: 0.18, duration: 300 });
  }, [state.fitSignal, rf]);

  const focusSeen = useRef(state.focusSignal);
  useEffect(() => {
    if (focusSeen.current === state.focusSignal || !sel) return;
    focusSeen.current = state.focusSignal;
    if (sel.type === "node") {
      const p = layout.get(sel.id);
      if (p) rf.setCenter(p.x + NODE_W / 2, p.y + NODE_H / 2, { zoom: Math.max(rf.getZoom(), 0.9), duration: 350 });
    } else {
      const e = model.edges.find((x) => x.id === sel.id);
      if (e) rf.fitView({ nodes: [{ id: e.from }, { id: e.to }], padding: 0.35, duration: 350 });
    }
  }, [state.focusSignal, sel, layout, model.edges, rf]);

  return (
    <ReactFlow<TNode, TEdge>
      nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
      onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
      onPaneClick={() => select(null)}
      onNodeMouseEnter={(_, n) => hover({ type: "node", id: n.id })} onNodeMouseLeave={() => hover(null)}
      onEdgeMouseEnter={(_, e) => hover({ type: "edge", id: e.id })} onEdgeMouseLeave={() => hover(null)}
      fitView fitViewOptions={{ padding: 0.18 }} minZoom={0.08} maxZoom={2}
      nodesDraggable={false} nodesConnectable={false} elementsSelectable panOnScroll zoomOnPinch selectionOnDrag={false}
      deleteKeyCode={null} multiSelectionKeyCode={null}
      onlyRenderVisibleElements
      onKeyDown={(e) => { if (e.key === "Escape") { select(null); dispatch({ type: "panel", open: true }); } }}
      aria-label="Supply network graph"
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#D9D9D2" />
    </ReactFlow>
  );
}

export default function NetworkGraph() {
  return <ReactFlowProvider><Graph /></ReactFlowProvider>;
}
