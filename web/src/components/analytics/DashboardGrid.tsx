"use client";

/**
 * A dashboard: saved analyses on a three-column grid, dashboard-level filters applied to every
 * tile whose metrics allow them, and a cross-filter bus — clicking a member on one tile filters
 * the others through a governed dimension-member event, shown as a chip, cleared with one click.
 * Edit mode reorders, resizes (1–3 columns) and removes tiles; view mode is what the board is for.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, ExternalLink, Minus, Plus, X } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import { runQuery, type Dashboard, type DashboardTile, type Filter, type ModelDoc, type ResultSet, type SavedAnalysis } from "@/lib/analytics/client";
import { allowedDimensionsFor, applyCrossFilter, mergeFilters } from "@/lib/analytics/spec";
import { drillThrough } from "@/lib/analytics/links";
import { AnalysisCard } from "./AnalysisCard";

export interface GridProps {
  dashboard: Dashboard;
  model: ModelDoc;
  editing: boolean;
  sharedFilters: Filter[];
  crossFilters: Filter[];
  onCrossFilters: (next: Filter[]) => void;
  onTiles: (tiles: DashboardTile[]) => void;
  refreshKey: number;
  onResults?: (results: Record<string, ResultSet>) => void;
}

export function DashboardGrid({ dashboard, model, editing, sharedFilters, crossFilters, onCrossFilters, onTiles, refreshKey, onResults }: GridProps) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.dashboards;
  const [results, setResults] = useState<Record<string, ResultSet>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const allowed = useCallback((ids: string[]) => allowedDimensionsFor(model.metrics, ids), [model]);
  const tiles = dashboard.spec.tiles;
  const analyses = dashboard.analyses ?? {};
  const active = useMemo(() => [...sharedFilters, ...crossFilters], [sharedFilters, crossFilters]);
  const inflight = useRef(0);

  useEffect(() => {
    let alive = true;
    const run = ++inflight.current;
    const next: Record<string, ResultSet> = {};
    const errs: Record<string, string> = {};
    Promise.all(tiles.map(async (tile) => {
      const a = analyses[tile.analysis_id];
      if (!a || !a.compatibility.compatible) return;
      const query = mergeFilters(a.visual.query, active, allowed);
      try { next[tile.tile_id] = await runQuery({ ...query, purpose: "dashboard" }, { noCache: refreshKey > 0 }); }
      catch (e) { errs[tile.tile_id] = (e as Error).message; }
    })).then(() => { if (alive && run === inflight.current) { setResults(next); setErrors(errs); onResults?.(next); } });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tiles, analyses, active, refreshKey]);

  const move = (i: number, dir: -1 | 1) => {
    const j = i + dir;
    if (j < 0 || j >= tiles.length) return;
    const next = [...tiles];
    [next[i], next[j]] = [next[j], next[i]];
    onTiles(next.map((tl, k) => ({ ...tl, y: k })));
  };
  const resize = (i: number, dw: -1 | 1) => onTiles(tiles.map((tl, k) => (k === i ? { ...tl, w: Math.max(1, Math.min(3, tl.w + dw)) } : tl)));
  const remove = (i: number) => onTiles(tiles.filter((_, k) => k !== i).map((tl, k) => ({ ...tl, y: k })));
  const onMember = (dimension: string, member: string) => onCrossFilters(applyCrossFilter(crossFilters, dimension, member));

  if (!tiles.length) return <div className="state-box"><h3>{copy.empty}</h3><p>{copy.emptyHint}</p></div>;
  return (
    <>
      {crossFilters.length > 0 && (
        <p className="ex-crossfilters" role="status">
          <span>{copy.crossFilterOn}:</span>
          {crossFilters.map((f) => (
            <span key={f.dimension_id} className="chip ex-chip">{model.dimensions.find((d) => d.id === f.dimension_id)?.label[lc] ?? f.dimension_id} = {f.values.join(", ")}
              <button type="button" aria-label={copy.remove} onClick={() => onCrossFilters(crossFilters.filter((x) => x !== f))}><X size={12} aria-hidden /></button></span>
          ))}
          <button type="button" className="zb zb--tertiary zb--sm" onClick={() => onCrossFilters([])}>{copy.clearFilters}</button>
        </p>
      )}
      <div className="db-grid">
        {tiles.map((tile, i) => {
          const a: SavedAnalysis | undefined = analyses[tile.analysis_id];
          const result = results[tile.tile_id] ?? null;
          const lead = crossFilters.length === 1 ? drillThrough(crossFilters[0].dimension_id, crossFilters[0].values[0]) : null;
          return (
            <div key={tile.tile_id} className="db-tile" style={{ gridColumn: `span ${Math.max(1, Math.min(3, tile.w))}` }}>
              {!a ? (
                <div className="state-box"><h3>{copy.missing}</h3></div>
              ) : !a.compatibility.compatible ? (
                <div className="state-box" data-tone="error"><h3>{a.name}</h3><p>{a.compatibility.message ?? a.compatibility.codes.join(", ")}</p></div>
              ) : errors[tile.tile_id] ? (
                <div className="state-box" data-tone="error"><h3>{a.name}</h3><p>{errors[tile.tile_id]}</p></div>
              ) : (
                <AnalysisCard visual={a.visual} result={result} height={tile.h >= 2 ? 420 : 240} compact onMember={a.visual.interactions === "none" || a.visual.interactions === "receive" ? undefined : onMember}
                  leads={lead ? [lead] : undefined}
                  badge={a.origin === "ask_zaad" ? <span className="tag" data-tone="approx">Ask ZAAD</span> : null}
                  actions={editing ? (
                    <span className="db-tile-tools" role="group" aria-label={copy.layout}>
                      <button type="button" className="zb zb--tertiary zb--sm" aria-label={copy.moveUp} onClick={() => move(i, -1)} disabled={i === 0}><ArrowUp size={13} aria-hidden /></button>
                      <button type="button" className="zb zb--tertiary zb--sm" aria-label={copy.moveDown} onClick={() => move(i, 1)} disabled={i === tiles.length - 1}><ArrowDown size={13} aria-hidden /></button>
                      <button type="button" className="zb zb--tertiary zb--sm" aria-label={copy.narrower} onClick={() => resize(i, -1)} disabled={tile.w <= 1}><Minus size={13} aria-hidden /></button>
                      <button type="button" className="zb zb--tertiary zb--sm" aria-label={copy.wider} onClick={() => resize(i, 1)} disabled={tile.w >= 3}><Plus size={13} aria-hidden /></button>
                      <button type="button" className="zb zb--tertiary zb--sm" aria-label={copy.remove} onClick={() => remove(i)}><X size={13} aria-hidden /></button>
                    </span>
                  ) : (
                    <Link href={`/explore?open=${encodeURIComponent(a.analysis_id)}`} className="zb zb--tertiary zb--sm" aria-label={`${copy.open} ${a.name}`}><ExternalLink size={13} aria-hidden /></Link>
                  )} />
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
