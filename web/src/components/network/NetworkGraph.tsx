"use client";

/**
 * NETWORK view: the supply graph as a stable, layered diagram (React Flow).
 * Positions come from `layoutNodes`, never from a force simulation, so the
 * picture is the same every time and people can remember where things are.
 * Normal things stay quiet; only exceptions carry colour or extra text.
 */
import { memo, useCallback, useEffect, useMemo, useRef } from "react";
import {
  Background, BackgroundVariant, BaseEdge, EdgeLabelRenderer, Handle, Position, ReactFlow, ReactFlowProvider, getBezierPath, useReactFlow,
  type Edge, type EdgeChange, type EdgeProps, type Node, type NodeChange, type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Anchor, Factory, Store, Users, Warehouse } from "lucide-react";
import { isGroupId } from "@/lib/network/groups";
import type { NetworkEdge, NetworkNode, NodeKind, ZaadState } from "@/lib/network/model";
import { STATE_LABEL } from "@/lib/network/model";
import { useTwin } from "./store";

type TNodeData = { node: NetworkNode; dim: boolean; exposed: boolean; active: boolean; metric: string | null; group: boolean; open: boolean };
type TEdgeData = { edge: NetworkEdge; dim: boolean; exposed: boolean; showLabel: boolean };
type TNode = Node<TNodeData, "twin">;
type TEdge = Edge<TEdgeData, "twin">;

const ICON: Record<NodeKind, typeof Factory> = { supplier: Factory, port: Anchor, dc: Warehouse, branch: Store, customer: Users };
const NODE_W = 176, NODE_H = 54;

/** One number a node is willing to state. Anything unmeasured simply says nothing. */
function metricFor(n: NetworkNode): string | null {
  const m = n.metrics;
  switch (n.kind) {
    case "supplier": return m.fill?.mean != null ? `${Math.round(m.fill.mean * 100)}% delivered` : m.leadDays?.mean != null ? `${Math.round(m.leadDays.mean)} d lead` : null;
    case "port": return null;
    case "dc": case "branch": return m.onHandUnits != null ? `${m.onHandUnits.toLocaleString()} on hand` : null;
    case "customer": return m.serviceTarget != null ? `${(m.serviceTarget * 100).toFixed(0)}% target` : null;
  }
}

const TwinNode = memo(function TwinNode({ data, selected }: NodeProps<TNode>) {
  const { node, dim, exposed, active, metric, group, open } = data;
  const Icon = ICON[node.kind];
  const exception = node.state !== "LEAN";
  return (
    <div className={`tn kind-${node.kind} st-${node.state} ${selected ? "selected" : ""} ${dim ? "dim" : ""} ${exposed ? "exposed" : ""} ${exception ? "exception" : ""} ${group ? "group" : ""}`} title={node.name}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <div className="tn-ico"><Icon size={14} strokeWidth={1.8} /></div>
      <div className="tn-name">{node.name}</div>
      <div className="tn-sub">{group ? `${node.subtitle} · click to ${open ? "collapse" : "expand"}` : node.subtitle ?? " "}</div>
      {(exception || active) && (
        <div className="tn-foot">
          {exception ? <span className="state-pill"><i />{STATE_LABEL[node.state]}</span> : <span />}
          {active && metric && <span className="tn-metric">{metric}</span>}
        </div>
      )}
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  );
});

const EDGE_STROKE: Record<ZaadState, string> = { LEAN: "#B8B8B2", PROTECT: "#D97706", ALLOCATE: "#C2410C", RECOVER: "#1D4ED8" };

const TwinEdge = memo(function TwinEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, selected }: EdgeProps<TEdge>) {
  const [path, lx, ly] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, curvature: 0.28 });
  if (!data) return null;
  const { edge, dim, exposed, showLabel } = data;
  const standby = edge.name.toLowerCase().includes("alternative");
  const stroke = selected ? "#0E9F6E" : exposed || edge.state !== "LEAN" ? EDGE_STROKE[edge.state] : standby ? "#DCDCD6" : "#B8B8B2";
  const dash = edge.kind === "transfer" ? "6 5" : edge.kind === "supply" || edge.kind === "service" ? "2 4" : standby ? "3 5" : undefined;
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
  const { display, layout, state, related, select, hover, dispatch } = useTwin();
  const rf = useReactFlow<TNode, TEdge>();
  const sel = state.selection, hov = state.hover;

  const nodes = useMemo<TNode[]>(() => display.nodes.map((n) => {
    const p = layout.get(n.id) ?? { x: 0, y: 0 };
    const selected = sel?.type === "node" && sel.id === n.id;
    const hovered = hov?.type === "node" && hov.id === n.id;
    return {
      id: n.id, type: "twin", position: { x: p.x, y: p.y }, width: NODE_W, height: NODE_H, draggable: false, selectable: true, focusable: true, selected,
      // React Flow labels a focusable node from its id, and an id here is `sup:SUP-001`. Someone
      // tabbing the graph with a screen reader would hear the internal key rather than the name.
      ariaLabel: n.subtitle ? `${n.name}, ${n.subtitle}` : n.name,
      data: { node: n, dim: related != null && !related.nodes.has(n.id), exposed: false, active: selected || hovered,
        metric: metricFor(n), group: isGroupId(n.id), open: state.expandedGroups.has(n.id) },
    };
  }), [display, layout, sel, hov, related, state.expandedGroups]);

  const edges = useMemo<TEdge[]>(() => display.edges.map((e) => ({
    id: e.id, type: "twin", source: e.from, target: e.to, selectable: true, focusable: true,
    selected: sel?.type === "edge" && sel.id === e.id,
    // Otherwise "Edge from sup:SUP-001 to port:aqaba". Every edge already carries the sentence a
    // person would say: "Rheinland Handels GmbH → Port of Aqaba".
    ariaLabel: e.name,
    data: { edge: e, dim: related != null && !related.edges.has(e.id), exposed: false,
      showLabel: (sel?.type === "edge" && sel.id === e.id) || (hov?.type === "edge" && hov.id === e.id) },
  })), [display, sel, hov, related]);

  // keyboard and mouse selection both arrive as 'select' changes; a group node opens instead
  const onNodesChange = useCallback((changes: NodeChange<TNode>[]) => {
    for (const c of changes) if (c.type === "select" && c.selected) {
      if (isGroupId(c.id)) dispatch({ type: "group:toggle", id: c.id }); else select({ type: "node", id: c.id });
      return;
    }
  }, [select, dispatch]);
  const onEdgesChange = useCallback((changes: EdgeChange<TEdge>[]) => {
    for (const c of changes) if (c.type === "select" && c.selected) { select({ type: "edge", id: c.id }); return; }
  }, [select]);

  useEffect(() => {
    const el = document.querySelector(".twin-fill");
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => { rf.fitView({ padding: 0.12, duration: 0 }); });
    ro.observe(el);
    return () => ro.disconnect();
  }, [rf]);

  const fitSeen = useRef(state.fitSignal);
  useEffect(() => {
    if (fitSeen.current === state.fitSignal) return;
    fitSeen.current = state.fitSignal;
    rf.fitView({ padding: 0.12, duration: 300 });
  }, [state.fitSignal, rf]);

  const focusSeen = useRef(state.focusSignal);
  useEffect(() => {
    if (focusSeen.current === state.focusSignal || !sel) return;
    focusSeen.current = state.focusSignal;
    if (sel.type === "node") {
      const p = layout.get(sel.id);
      if (p) rf.setCenter(p.x + NODE_W / 2, p.y + NODE_H / 2, { zoom: Math.max(rf.getZoom(), 0.9), duration: 350 });
    } else {
      const e = display.edges.find((x) => x.id === sel.id);
      if (e) rf.fitView({ nodes: [{ id: e.from }, { id: e.to }], padding: 0.35, duration: 350 });
    }
  }, [state.focusSignal, sel, layout, display.edges, rf]);

  return (
    <ReactFlow<TNode, TEdge>
      nodes={nodes} edges={edges} nodeTypes={nodeTypes} edgeTypes={edgeTypes}
      onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
      onPaneClick={() => { select(null); dispatch({ type: "panel", open: false }); }}
      onNodeMouseEnter={(_, n) => hover({ type: "node", id: n.id })} onNodeMouseLeave={() => hover(null)}
      onEdgeMouseEnter={(_, e) => hover({ type: "edge", id: e.id })} onEdgeMouseLeave={() => hover(null)}
      fitView fitViewOptions={{ padding: 0.12 }} minZoom={0.08} maxZoom={2}
      nodesDraggable={false} nodesConnectable={false} elementsSelectable panOnScroll zoomOnPinch selectionOnDrag={false}
      deleteKeyCode={null} multiSelectionKeyCode={null}
      onlyRenderVisibleElements
      aria-label="Supply network graph"
    >
      <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#DDDDD7" />
    </ReactFlow>
  );
}

export default function NetworkGraph() {
  return <ReactFlowProvider><Graph /></ReactFlowProvider>;
}
