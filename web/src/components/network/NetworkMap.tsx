"use client";

/**
 * MAP view: MapLibre basemap with deck.gl layers for facilities, lanes,
 * shipments and labels. Progressive disclosure is screen-space: at every
 * zoom the most important facilities take their place first, and anything
 * that would sit on top of them waits for a closer zoom. Selection and
 * hover live in the store, so the NETWORK view and the panel stay in step.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MapGL, { NavigationControl, useControl, type MapRef } from "react-map-gl/maplibre";
import { setWorkerUrl } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapboxOverlay, type MapboxOverlayProps } from "@deck.gl/mapbox";
import { PathLayer, ScatterplotLayer, TextLayer } from "@deck.gl/layers";
import type { PickingInfo } from "@deck.gl/core";
import { bounds as geoBounds, pointAlong, type LonLat } from "@/lib/network/geo";
import type { NetworkEdge, NetworkNode, Shipment } from "@/lib/network/model";
import { reduceMotionNow } from "@/lib/motion";
import { INK, STATE_RGB, useTwin } from "./store";

// MapLibre parses tiles in a web worker; serve it from a plain URL (vendored
// at install and build time by scripts/vendor-maplibre-worker.mjs) rather
// than trusting the bundler to expose a worker from inside node_modules.
const WORKER_URL = "/vendor/maplibre-gl-worker.mjs";
setWorkerUrl(WORKER_URL);
/** How long the basemap may take before the view says so instead of staying blank. */
const LOAD_TIMEOUT_MS = 15000;

/** Confirms the vendored worker is actually served as JavaScript before the map depends on it. */
async function probeWorker(): Promise<string | null> {
  try {
    const r = await fetch(WORKER_URL, { method: "HEAD", cache: "no-store" });
    if (!r.ok) return `worker script ${WORKER_URL} returned HTTP ${r.status}`;
    const ct = r.headers.get("content-type") ?? "";
    if (!/javascript|ecmascript/i.test(ct)) return `worker script ${WORKER_URL} is served as "${ct || "unknown"}", not JavaScript`;
    return null;
  } catch (e) {
    return `worker script ${WORKER_URL} could not be fetched (${e instanceof Error ? e.message : String(e)})`;
  }
}

const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL || "https://tiles.openfreemap.org/styles/positron";
const ACCENT: [number, number, number] = [14, 159, 110];
const NODE_PX: Record<NetworkNode["kind"], number> = { dc: 9, port: 8, supplier: 7, branch: 6, customer: 5 };
const KIND_INK: Record<NetworkNode["kind"], [number, number, number]> = { dc: INK[900], port: INK[700], supplier: INK[900], branch: INK[700], customer: INK[500] };
/** Importance a node needs to be drawn / labelled at each zoom tier (world, regional, local). */
const SHOW_AT = [0.65, 0.35, 0], LABEL_AT = [0.85, 0.55, 0];
const FONT = "Instrument Sans, system-ui, sans-serif";

function DeckOverlay(props: MapboxOverlayProps) {
  const overlay = useControl<MapboxOverlay>(() => new MapboxOverlay(props));
  overlay.setProps(props);
  return null;
}

type NodeDatum = NetworkNode & { at: LonLat };
type ShipDatum = Shipment & { at: LonLat; edge: NetworkEdge };
type Box = [number, number, number, number];
const overlaps = (a: Box, b: Box) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
const sameSet = (a: Set<string>, b: Set<string>) => a.size === b.size && [...a].every((x) => b.has(x));

export default function NetworkMap() {
  const { model, state, related, scenario, select, hover, dispatch } = useTwin();
  const mapRef = useRef<MapRef>(null);
  const [styleError, setStyleError] = useState<string | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [slow, setSlow] = useState(false);
  // fail loudly: a missing worker or a basemap that never loads is reported, never a blank map
  useEffect(() => {
    let alive = true;
    probeWorker().then((err) => { if (alive && err) setMapError(err); });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    if (loaded) return;
    const t = window.setTimeout(() => setSlow(true), LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(t);
  }, [loaded]);
  const [hovering, setHovering] = useState(false);
  const [shown, setShown] = useState<{ nodes: Set<string>; labels: Set<string> }>({ nodes: new Set(), labels: new Set() });
  const sel = state.selection, hov = state.hover;
  const reduce = typeof window !== "undefined" && reduceMotionNow();

  const geoNodes = useMemo<NodeDatum[]>(() => model.nodes.filter((n) => n.geo).map((n) => ({ ...n, at: [n.geo!.lon, n.geo!.lat] as LonLat })), [model]);
  const geoEdges = useMemo(() => model.edges.filter((e) => e.path && e.path.length >= 2), [model]);
  /** Lanes that only exist as someone else's alternative are drawn thin until they matter. */
  const standby = useMemo(() => { const s = new Set<string>(); for (const e of model.edges) for (const a of e.alternatives) s.add(a); for (const e of model.edges) if (e.state !== "LEAN") s.delete(e.id); return s; }, [model]);
  const edgeById = useMemo(() => new Map(model.edges.map((e) => [e.id, e])), [model]);
  const ships = useMemo<ShipDatum[]>(() => model.shipments.flatMap((s) => {
    const edge = edgeById.get(s.edgeId);
    if (!edge?.path || s.progress == null) return [];
    return [{ ...s, edge, at: pointAlong(edge.path, s.progress) }];
  }), [model.shipments, edgeById]);
  const noGeo = model.nodes.length - geoNodes.length;

  const isSel = useCallback((type: "node" | "edge", id: string) => sel?.type === type && sel.id === id, [sel]);
  const isHov = useCallback((type: "node" | "edge", id: string) => hov?.type === type && hov.id === id, [hov]);
  const forced = useCallback((n: NetworkNode) => isSel("node", n.id) || isHov("node", n.id) || (related?.nodes.has(n.id) ?? false)
    || (scenario?.exposed.nodes.has(n.id) ?? false) || n.risk.level === "critical" || n.risk.level === "high", [isSel, isHov, related, scenario]);

  // Screen-space disclosure: project every facility, take them in priority
  // order, and let each claim its dot and, if there is room, its label.
  const declutter = useCallback(() => {
    const m = mapRef.current;
    if (!m) return;
    const z = m.getZoom();
    const tier = z < 3.6 ? 0 : z < 6.5 ? 1 : 2;
    const ranked = [...geoNodes].sort((a, b) => (Number(forced(b)) * 2 + b.importance) - (Number(forced(a)) * 2 + a.importance));
    const nodeBoxes: Box[] = [], labelBoxes: Box[] = [];
    const nodes = new Set<string>(), labels = new Set<string>();
    for (const n of ranked) {
      const f = forced(n);
      if (!f && n.importance < SHOW_AT[tier]) continue;
      const p = m.project(n.at);
      const r = NODE_PX[n.kind] + 4;
      const box: Box = [p.x - r, p.y - r, p.x + r, p.y + r];
      if (!f && nodeBoxes.some((b) => overlaps(b, box))) continue;
      nodes.add(n.id); nodeBoxes.push(box);
      if (!(f || n.importance >= LABEL_AT[tier])) continue;
      const w = n.name.length * 6.6 + 12, h = 18;
      const lb: Box = [p.x - w / 2, p.y - r - h - 2, p.x + w / 2, p.y - r - 2];
      if (labelBoxes.some((b) => overlaps(b, lb)) || nodeBoxes.some((b) => overlaps(b, lb))) continue;
      labels.add(n.id); labelBoxes.push(lb);
    }
    setShown((cur) => (sameSet(cur.nodes, nodes) && sameSet(cur.labels, labels) ? cur : { nodes, labels }));
  }, [geoNodes, forced]);
  useEffect(() => { declutter(); }, [declutter]);
  const raf = useRef(0);
  const onMove = useCallback(() => {
    if (raf.current) return;
    raf.current = requestAnimationFrame(() => { raf.current = 0; declutter(); });
  }, [declutter]);
  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current); }, []);

  const visibleNodes = useMemo(() => geoNodes.filter((n) => shown.nodes.has(n.id)), [geoNodes, shown]);
  const labelled = useMemo(() => geoNodes.filter((n) => shown.labels.has(n.id)), [geoNodes, shown]);
  const laneLabel = useMemo(() => geoEdges.filter((e) => isSel("edge", e.id) || isHov("edge", e.id)).map((e) => ({ e, at: pointAlong(e.path!, 0.5) })), [geoEdges, isSel, isHov]);

  const layers = useMemo(() => {
    const dimNode = (id: string) => related != null && !related.nodes.has(id);
    const dimEdge = (id: string) => related != null && !related.edges.has(id);
    const triggers = [sel, hov, related, scenario];
    const nodeColor = (n: NodeDatum): [number, number, number, number] => {
      const alpha = dimNode(n.id) ? 70 : n.geo?.precision === "approximate" ? 190 : 255;
      if (isSel("node", n.id)) return [...ACCENT, 255];
      if (n.state !== "LEAN" || scenario?.exposed.nodes.has(n.id)) return [...STATE_RGB[n.state], alpha];
      return [...KIND_INK[n.kind], alpha];
    };
    const laneColor = (e: NetworkEdge): [number, number, number, number] => {
      const alpha = dimEdge(e.id) ? 45 : 235;
      if (isSel("edge", e.id)) return [...ACCENT, 255];
      if (isHov("edge", e.id)) return [...INK[900], 255];
      if (e.state !== "LEAN" || scenario?.exposed.edges.has(e.id)) return [...STATE_RGB[e.state], alpha];
      if (standby.has(e.id)) return [...INK[300], alpha];
      return [...INK[400], alpha];
    };
    return [
      new PathLayer<NetworkEdge>({
        id: "lanes", data: geoEdges, getPath: (e) => e.path!, getColor: laneColor, widthUnits: "pixels",
        getWidth: (e) => (isSel("edge", e.id) ? 3 : isHov("edge", e.id) || e.state !== "LEAN" ? 2.4 : standby.has(e.id) ? 1 : 1.6),
        capRounded: true, jointRounded: true, pickable: true,
        onClick: (i: PickingInfo<NetworkEdge>) => { if (i.object) { select({ type: "edge", id: i.object.id }); return true; } },
        updateTriggers: { getColor: triggers, getWidth: triggers },
      }),
      new ScatterplotLayer<ShipDatum>({
        id: "shipments", data: ships, getPosition: (s) => s.at, radiusUnits: "pixels", getRadius: 4.2, stroked: true, getLineColor: [255, 255, 255, 255], lineWidthMinPixels: 1.5,
        getFillColor: (s) => (s.status === "delayed" ? [194, 65, 12, 255] : s.status === "customs" || s.status === "at_port" ? [217, 119, 6, 255] : [...INK[700], 255]),
        pickable: true, onClick: (i: PickingInfo<ShipDatum>) => { if (i.object) { select({ type: "edge", id: i.object.edgeId }); return true; } },
      }),
      new ScatterplotLayer<NodeDatum>({
        id: "nodes", data: visibleNodes, getPosition: (n) => n.at, radiusUnits: "pixels",
        getRadius: (n) => NODE_PX[n.kind] + (isSel("node", n.id) ? 2 : 0) + (isHov("node", n.id) ? 1 : 0),
        getFillColor: nodeColor, stroked: true, getLineColor: [255, 255, 255, 255], lineWidthMinPixels: 1.5, pickable: true,
        onClick: (i: PickingInfo<NodeDatum>) => { if (i.object) { select({ type: "node", id: i.object.id }); return true; } },
        updateTriggers: { getFillColor: triggers, getRadius: triggers },
      }),
      new ScatterplotLayer<NodeDatum>({
        id: "selection-ring", data: visibleNodes.filter((n) => isSel("node", n.id)), getPosition: (n) => n.at, radiusUnits: "pixels",
        getRadius: (n) => NODE_PX[n.kind] + 7, filled: false, stroked: true, getLineColor: [...ACCENT, 200], lineWidthMinPixels: 2,
      }),
      new TextLayer<NodeDatum>({
        id: "labels", data: labelled, getPosition: (n) => n.at, getText: (n) => n.name, getSize: 12, sizeUnits: "pixels",
        getColor: (n) => (dimNode(n.id) ? [...INK[400], 200] : [...INK[900], 255]), getPixelOffset: (n) => [0, -(NODE_PX[n.kind] + 9)],
        getTextAnchor: "middle", getAlignmentBaseline: "bottom", fontFamily: FONT, fontWeight: 600, characterSet: "auto",
        background: true, getBackgroundColor: [255, 255, 255, 215], backgroundPadding: [5, 2, 5, 2], updateTriggers: { getColor: triggers },
      }),
      new TextLayer<{ e: NetworkEdge; at: LonLat }>({
        id: "lane-labels", data: laneLabel, getPosition: (d) => d.at, getText: (d) => `${d.e.name}${d.e.leadDays.current != null ? ` · ${d.e.leadDays.current} d` : ""}`,
        getSize: 11.5, sizeUnits: "pixels", getColor: [...INK[900], 255], fontFamily: FONT, fontWeight: 500, characterSet: "auto",
        background: true, getBackgroundColor: [255, 255, 255, 235], backgroundPadding: [6, 3, 6, 3], getPixelOffset: [0, -10],
      }),
    ];
  }, [geoEdges, ships, visibleNodes, labelled, laneLabel, sel, hov, related, scenario, standby, select, isSel, isHov]);

  const onHover = useCallback((i: PickingInfo<NodeDatum | NetworkEdge | ShipDatum>) => {
    const o = i.object as (NodeDatum | NetworkEdge | ShipDatum) | undefined;
    setHovering(Boolean(o));
    if (!o) { hover(null); return; }
    if ("edgeId" in o) hover({ type: "edge", id: o.edgeId });
    else if ("geo" in o) hover({ type: "node", id: o.id });
    else hover({ type: "edge", id: o.id });
  }, [hover]);

  const getTooltip = useCallback(({ object }: PickingInfo<NodeDatum | NetworkEdge | ShipDatum>) => {
    if (!object) return null;
    const text = "edgeId" in object ? `${object.ref} · ${object.status.replace("_", " ")} · ETA ${object.eta ?? "n/a"}`
      : "geo" in object ? `${object.name}${object.subtitle ? ` · ${object.subtitle}` : ""}` : object.name;
    return { text, style: { background: "#18181B", color: "#fff", fontSize: "12px", padding: "5px 8px", borderRadius: "6px", fontFamily: FONT } };
  }, []);

  const initialBounds = useMemo(() => geoBounds([...geoNodes.map((n) => n.at), ...geoEdges.flatMap((e) => e.path!)]), [geoNodes, geoEdges]);

  const fit = useCallback((animate: boolean) => {
    const m = mapRef.current;
    if (!m || !initialBounds) return;
    m.fitBounds(initialBounds, { padding: 70, maxZoom: 9, duration: animate && !reduce ? 650 : 0 });
  }, [initialBounds, reduce]);

  const fitSeen = useRef(state.fitSignal);
  useEffect(() => { if (fitSeen.current !== state.fitSignal) { fitSeen.current = state.fitSignal; fit(true); } }, [state.fitSignal, fit]);

  const focusSeen = useRef(state.focusSignal);
  useEffect(() => {
    if (focusSeen.current === state.focusSignal || !sel) return;
    focusSeen.current = state.focusSignal;
    const m = mapRef.current;
    if (!m) return;
    const dur = reduce ? 0 : 700;
    if (sel.type === "node") {
      const n = geoNodes.find((x) => x.id === sel.id);
      if (n) m.flyTo({ center: n.at, zoom: Math.max(m.getZoom(), 6.5), duration: dur });
    } else {
      const e = edgeById.get(sel.id);
      const b = e?.path ? geoBounds(e.path) : null;
      if (b) m.fitBounds(b, { padding: 90, maxZoom: 9, duration: dur });
    }
  }, [state.focusSignal, sel, geoNodes, edgeById, reduce]);

  return (
    <>
      <MapGL
        ref={mapRef} mapStyle={STYLE_URL} reuseMaps
        initialViewState={initialBounds ? { bounds: initialBounds, fitBoundsOptions: { padding: 70, maxZoom: 9 } } : { longitude: 40, latitude: 25, zoom: 3 }}
        style={{ width: "100%", height: "100%" }} cursor={hovering ? "pointer" : "grab"}
        onMove={onMove} onLoad={() => { setLoaded(true); declutter(); }} onError={(e) => setStyleError(e.error?.message ?? "basemap failed to load")}
        onClick={() => select(null)} attributionControl={{ compact: true }}
      >
        <NavigationControl position="top-left" showCompass={false} />
        <DeckOverlay layers={layers} onHover={onHover} getTooltip={getTooltip} pickingRadius={6} />
      </MapGL>
      {(mapError || (styleError && !loaded)) && (
        <div className="twin-maperror" role="alert">
          <b>The map could not start.</b>
          <div>{mapError ?? styleError}</div>
          <div className="row" style={{ marginTop: 10 }}>
            <button className="tbtn" onClick={() => dispatch({ type: "view", view: "network" })}>Open the NETWORK view</button>
            <button className="tbtn ghost" onClick={() => window.location.reload()}>Retry</button>
          </div>
        </div>
      )}
      {!mapError && !loaded && slow && !styleError && <div className="twin-notice warn">The basemap is taking longer than expected ({LOAD_TIMEOUT_MS / 1000}s). Lanes and facilities appear once it loads; the NETWORK view does not need it.</div>}
      {!mapError && loaded && styleError && <div className="twin-notice warn">Some basemap tiles failed ({styleError}); facilities and lanes still draw.</div>}
      {!mapError && !styleError && noGeo > 0 && <div className="twin-notice">{noGeo} node{noGeo === 1 ? "" : "s"} without coordinates are shown only in the NETWORK view.</div>}
    </>
  );
}
