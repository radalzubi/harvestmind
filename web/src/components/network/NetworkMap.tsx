"use client";

/**
 * MAP view: where imported supply actually comes from.
 *
 * MapLibre draws the basemap and the lanes and places as GeoJSON layers. Labels are a symbol
 * layer, so MapLibre's own collision detection decides what fits at each zoom — better, and a
 * great deal less code, than the hand-rolled screen-space box test this replaces. deck.gl is
 * not used: three packages and a second renderer bought nothing that a line, a circle and a
 * symbol layer do not already do here.
 *
 * Honesty rules the map keeps:
 *  - a place with no declared coordinates is not drawn, and the view says how many are missing;
 *  - a place placed from a country is drawn hollow and labelled approximate;
 *  - a lane path is the published shipping route for the operator's declared route tag, never a
 *    tracked vessel, and nothing is animated along it.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { GeoJSONSource, Map as MapLibreMap, MapGeoJSONFeature, StyleSpecification } from "maplibre-gl";
import { bounds as geoBounds, type LonLat } from "@/lib/network/geo";
import type { NetworkEdge, NetworkNode } from "@/lib/network/model";
import { INK, STATE_COLOR, useTwin } from "./store";

const STYLE_URL = process.env.NEXT_PUBLIC_MAP_STYLE_URL || "https://tiles.openfreemap.org/styles/positron";
const WORKER_URL = "/vendor/maplibre-gl-worker.mjs";
/**
 * How long the basemap may take before the view says so instead of staying blank.
 *
 * Measured: a cold load of the style, its sprite, its glyphs and the first tiles took a little over
 * fifteen seconds, so the original fifteen-second limit reported a failure for a map that was about
 * to appear. Thirty is long enough not to lie about a slow connection and short enough that nobody
 * sits in front of an empty rectangle wondering.
 */
const LOAD_TIMEOUT_MS = 30000;

/** Confirms the vendored worker is served as JavaScript before the map depends on it. */
async function probeWorker(): Promise<string | null> {
  try {
    const r = await fetch(WORKER_URL, { method: "HEAD", cache: "no-store" });
    if (!r.ok) return `the map's worker script returned HTTP ${r.status}`;
    const type = r.headers.get("content-type") ?? "";
    if (!/javascript|ecmascript/i.test(type)) return `the map's worker script is served as "${type || "an unknown type"}", not JavaScript`;
    return null;
  } catch (e) {
    return `the map's worker script could not be fetched (${e instanceof Error ? e.message : String(e)})`;
  }
}

const RADIUS: Record<NetworkNode["kind"], number> = { dc: 8, port: 7, supplier: 6.5, branch: 6, customer: 5 };

function placeFeatures(nodes: NetworkNode[], selectedId: string | null) {
  return nodes.filter((n) => n.geo).map((n) => ({
    type: "Feature" as const,
    id: n.id,
    geometry: { type: "Point" as const, coordinates: [n.geo!.lon, n.geo!.lat] },
    properties: {
      id: n.id, name: n.name, kind: n.kind,
      color: n.state === "LEAN" ? INK[900] : STATE_COLOR[n.state],
      radius: RADIUS[n.kind] * (selectedId === n.id ? 1.5 : 1),
      approximate: n.geo!.precision === "approximate" ? 1 : 0,
      importance: n.importance,
      selected: selectedId === n.id ? 1 : 0,
    },
  }));
}

function laneFeatures(edges: NetworkEdge[], selectedId: string | null, dim: Set<string> | null) {
  return edges.filter((e) => e.path && e.path.length > 1).map((e) => ({
    type: "Feature" as const,
    id: e.id,
    geometry: { type: "LineString" as const, coordinates: e.path as LonLat[] },
    properties: {
      id: e.id, name: e.name,
      color: selectedId === e.id ? "#0E9F6E" : e.state === "LEAN" ? INK[300] : STATE_COLOR[e.state],
      width: selectedId === e.id ? 3.2 : e.state === "LEAN" ? 1.4 : 2.2,
      opacity: dim && !dim.has(e.id) ? 0.18 : 0.95,
      dashed: e.kind === "road" ? 1 : 0,
    },
  }));
}

export default function NetworkMap() {
  const { model, state, select, related } = useTwin();
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const placed = useMemo(() => model.nodes.filter((n) => n.geo), [model.nodes]);
  const unplaced = model.nodes.length - placed.length;
  const selectedId = state.selection?.id ?? null;

  const data = useMemo(() => ({
    places: { type: "FeatureCollection" as const, features: placeFeatures(model.nodes, selectedId) },
    lanes: { type: "FeatureCollection" as const, features: laneFeatures(model.edges, selectedId, related?.edges ?? null) },
  }), [model.nodes, model.edges, selectedId, related]);

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    (async () => {
      const problem = await probeWorker();
      if (!alive) return;
      if (problem) { setError(`The map cannot start because ${problem}.`); return; }
      const maplibre = await import("maplibre-gl");
      await import("maplibre-gl/dist/maplibre-gl.css");
      if (!alive || !container.current) return;
      // The bundler does not serve MapLibre's own worker from inside the package, so it is vendored
      // to a plain URL at install and build time. MapLibre v6 constructs it with {type:"module"},
      // which is what the vendored file is.
      maplibre.setWorkerUrl(WORKER_URL);

      const instance = new maplibre.Map({
        container: container.current,
        style: STYLE_URL as unknown as StyleSpecification,
        center: [40, 25], zoom: 1.6, attributionControl: { compact: true },
        // The map is a reference picture, not a flight simulator.
        pitchWithRotate: false, dragRotate: false, touchZoomRotate: true,
      });
      map.current = instance;
      instance.addControl(new maplibre.NavigationControl({ showCompass: false }), "top-right");
      instance.keyboard.enable();

      timer = window.setTimeout(() => { if (alive && !instance.isStyleLoaded()) setError("The map's background could not be loaded. Everything else on this page still works — the network view shows the same suppliers, lanes and sites."); }, LOAD_TIMEOUT_MS);

      instance.on("load", () => {
        if (!alive) return;
        window.clearTimeout(timer);
        instance.addSource("lanes", { type: "geojson", data: data.lanes });
        instance.addSource("places", { type: "geojson", data: data.places });
        instance.addLayer({
          id: "lanes-line", type: "line", source: "lanes",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: {
            "line-color": ["get", "color"], "line-width": ["get", "width"], "line-opacity": ["get", "opacity"],
            "line-dasharray": [2, 2],
          },
          filter: ["==", ["get", "dashed"], 1],
        });
        instance.addLayer({
          id: "lanes-solid", type: "line", source: "lanes",
          layout: { "line-cap": "round", "line-join": "round" },
          paint: { "line-color": ["get", "color"], "line-width": ["get", "width"], "line-opacity": ["get", "opacity"] },
          filter: ["==", ["get", "dashed"], 0],
        });
        instance.addLayer({
          id: "places-halo", type: "circle", source: "places",
          paint: {
            "circle-radius": ["+", ["get", "radius"], 4],
            "circle-color": "#FFFFFF", "circle-opacity": 0.85,
          },
        });
        instance.addLayer({
          id: "places-dot", type: "circle", source: "places",
          paint: {
            "circle-radius": ["get", "radius"],
            // A place put on the map from its country only is drawn hollow.
            "circle-color": ["case", ["==", ["get", "approximate"], 1], "#FFFFFF", ["get", "color"]],
            "circle-stroke-color": ["get", "color"],
            "circle-stroke-width": ["case", ["==", ["get", "selected"], 1], 3, 1.8],
          },
        });
        instance.addLayer({
          id: "places-label", type: "symbol", source: "places",
          layout: {
            "text-field": ["get", "name"],
            "text-size": 11.5,
            "text-font": ["Noto Sans Regular"],
            // MapLibre decides what fits; importance breaks ties so the big places win.
            "symbol-sort-key": ["-", 1, ["get", "importance"]],
            // Four positions are tried around the dot before a label is given up. With a single
            // fixed anchor, two facilities a few hundred kilometres apart lose one label outright —
            // an operator reading the map cannot tell a supplier that is absent from one whose name
            // did not fit. `text-optional` is off so the label is placed or dropped on its own
            // merits rather than because a paired icon won its slot.
            "text-variable-anchor": ["top", "bottom", "left", "right"],
            "text-radial-offset": 0.9,
            "text-justify": "auto",
            "text-allow-overlap": false, "text-optional": false,
            "text-padding": 3,
          },
          paint: { "text-color": INK[900], "text-halo-color": "#F7F7F4", "text-halo-width": 1.6 },
        });

        for (const layer of ["places-dot", "lanes-solid", "lanes-line"]) {
          instance.on("click", layer, (e) => {
            const feature = e.features?.[0] as MapGeoJSONFeature | undefined;
            const id = feature?.properties?.id as string | undefined;
            if (id) select({ type: layer === "places-dot" ? "node" : "edge", id });
          });
          instance.on("mouseenter", layer, () => { instance.getCanvas().style.cursor = "pointer"; });
          instance.on("mouseleave", layer, () => { instance.getCanvas().style.cursor = ""; });
        }
        instance.on("click", (e) => {
          const hits = instance.queryRenderedFeatures(e.point, { layers: ["places-dot", "lanes-solid", "lanes-line"] });
          if (!hits.length) select(null);
        });
        setReady(true);
      });
      instance.on("error", (e) => {
        // A missing glyph or tile is not worth blanking the page over; a style failure is.
        if (alive && !instance.isStyleLoaded()) setError(`The map's background could not be loaded (${e.error?.message ?? "unknown error"}). The network view shows the same information.`);
      });
    })();
    return () => { alive = false; window.clearTimeout(timer); map.current?.remove(); map.current = null; };
    // Sources are created once and updated below; re-running this effect would rebuild the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready) return;
    (instance.getSource("lanes") as GeoJSONSource | undefined)?.setData(data.lanes);
    (instance.getSource("places") as GeoJSONSource | undefined)?.setData(data.places);
  }, [data, ready]);

  /**
   * MapLibre reads its container's size once and decides which tiles to fetch from it. It has to be
   * told when that changes — when the details panel takes or gives back its column, and on the first
   * layout pass, where a container that is briefly zero-height leaves the map requesting no tiles at
   * all and painting nothing.
   */
  useEffect(() => {
    const element = container.current;
    const instance = map.current;
    if (!element || !instance || typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(element);
    return () => observer.disconnect();
  }, [ready]);

  const fit = useCallback(() => {
    const instance = map.current;
    if (!instance || !ready) return;
    const points: LonLat[] = [
      ...placed.map((n) => [n.geo!.lon, n.geo!.lat] as LonLat),
      ...model.edges.flatMap((e) => e.path ?? []),
    ];
    const box = geoBounds(points);
    if (box) instance.fitBounds(box, { padding: 64, duration: 400, maxZoom: 6 });
  }, [placed, model.edges, ready]);

  useEffect(() => { fit(); }, [fit, state.fitSignal]);

  useEffect(() => {
    const instance = map.current;
    if (!instance || !ready || !state.selection) return;
    if (state.selection.type === "node") {
      const node = model.nodes.find((n) => n.id === state.selection!.id);
      if (node?.geo) instance.easeTo({ center: [node.geo.lon, node.geo.lat], zoom: Math.max(instance.getZoom(), 3.2), duration: 500 });
    } else {
      const edge = model.edges.find((e) => e.id === state.selection!.id);
      const box = edge?.path ? geoBounds(edge.path) : null;
      if (box) instance.fitBounds(box, { padding: 90, duration: 500, maxZoom: 6 });
    }
  }, [state.focusSignal, state.selection, model.nodes, model.edges, ready]);

  if (error) {
    return (
      <div className="twin-fill" style={{ display: "grid", placeItems: "center", padding: 28 }}>
        <div className="state-box" style={{ maxWidth: 460 }} role="alert">
          <h3>The map could not be shown</h3>
          <p>{error}</p>
          <div className="actions">
            <button className="zb zb--primary" onClick={() => window.location.reload()}>Reload the page</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    // .twin-fill is absolutely positioned and inset to 0 by the stylesheet; setting position
    // inline here overrides that, `inset` stops applying and the map collapses to no height.
    <div className="twin-fill">
      <div ref={container} style={{ position: "absolute", inset: 0 }} aria-label="Map of suppliers, ports, routes and sites" role="application" />
      {(unplaced > 0 || placed.some((n) => n.geo!.precision === "approximate")) && (
        <div style={{
          position: "absolute", insetInlineStart: 12, bottom: 12, zIndex: 2, maxWidth: 340,
          background: "color-mix(in srgb, var(--surface) 94%, transparent)", border: "1px solid var(--line)",
          borderRadius: "var(--radius)", padding: "10px 12px", fontSize: 12, color: "var(--ink-600)", lineHeight: 1.5,
          backdropFilter: "blur(8px)",
        }}>
          <strong style={{ color: "var(--ink-950)", fontWeight: 600, display: "block", marginBottom: 3 }}>What this map shows</strong>
          Hollow circles are placed by country, not by address. Lines are the published shipping route for a
          declared route tag, not a tracked vessel.
          {unplaced > 0 && <> {unplaced} item{unplaced === 1 ? "" : "s"} in this network {unplaced === 1 ? "has" : "have"} no location and {unplaced === 1 ? "is" : "are"} shown in the network view only.</>}
        </div>
      )}
    </div>
  );
}
