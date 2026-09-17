"use client";

/**
 * One dashboard: view, edit (rename, add / remove / reorder / resize tiles, visibility), full
 * screen, dashboard-level filters, refresh with the data's freshness stated, duplicate, delete.
 * Filters live in the URL so a filtered board can be sent to someone.
 */
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Copy, Maximize2, Minimize2, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, Loading, Notice, PageHead } from "@/components/workspace/ui";
import { Drawer } from "@/components/workspace/Table";
import { useToast } from "@/components/Toast";
import { useLocale } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { DATE } from "@/lib/zaad/product";
import {
  deleteDashboard, duplicateDashboard, fetchDatasetVersion, fetchModel, listAnalyses, readDashboard, updateDashboard,
  type Dashboard, type DashboardTile, type Filter, type ModelDoc, type ResultSet, type SavedAnalysis,
} from "@/lib/analytics/client";
import { stateFromParams, stateToParams, EMPTY_BUILDER } from "@/lib/analytics/spec";
import { DashboardGrid } from "@/components/analytics/DashboardGrid";
import { FilterBar } from "@/components/analytics/FilterBar";

function Body() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const session = useSession();
  const toast = useToast();
  const { locale, t } = useLocale();
  const copy = t.analytics.dashboards;
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [model, setModel] = useState<ModelDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(search.get("edit") === "1");
  const [full, setFull] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshedAt, setRefreshedAt] = useState<string | null>(null);
  const [crossFilters, setCrossFilters] = useState<Filter[]>([]);
  const [urlFilters, setUrlFilters] = useState<Filter[]>(() => stateFromParams(search).filters);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [candidates, setCandidates] = useState<SavedAnalysis[]>([]);
  const [name, setName] = useState("");
  const [dirtyTiles, setDirtyTiles] = useState<DashboardTile[] | null>(null);
  const [moved, setMoved] = useState<{ stale: boolean; tables_moved: string[] } | null>(null);
  const [latest, setLatest] = useState<Record<string, ResultSet>>({});

  const load = useCallback(() => {
    readDashboard(params.id).then((d) => { setDashboard(d); setName(d.name); setDirtyTiles(null); }).catch((e: Error) => setError(e.message));
  }, [params.id]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { fetchModel(locale).then(setModel).catch((e: Error) => setError(e.message)); }, [locale]);
  useEffect(() => {
    const next = stateToParams({ ...EMPTY_BUILDER, filters: urlFilters }).toString();
    const current = new URLSearchParams(search.toString());
    current.delete("f"); current.delete("edit");
    const base = current.toString();
    router.replace(`/dashboards/${encodeURIComponent(params.id)}${next || base ? `?${[base, next].filter(Boolean).join("&")}` : ""}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlFilters]);

  const sharedFilters = useMemo(() => {
    const own = dashboard?.spec.shared_filters ?? [];
    const overridden = new Set(urlFilters.map((f) => f.dimension_id));
    return [...own.filter((f) => !overridden.has(f.dimension_id)), ...urlFilters];
  }, [dashboard, urlFilters]);

  const tiles = dirtyTiles ?? dashboard?.spec.tiles ?? [];
  const canEdit = dashboard && (session.can("manageAnalytics") || (session.can("editOwnAnalysis") && dashboard.owner === session.actor?.id));

  const save = async () => {
    if (!dashboard) return;
    try {
      const updated = await updateDashboard(dashboard.dashboard_id, { name: name.trim() || dashboard.name, spec: { ...dashboard.spec, tiles, shared_filters: sharedFilters } });
      setDashboard(updated); setDirtyTiles(null); setEditing(false); toast.push(copy.saved);
    } catch (e) { toast.push((e as Error).message, "warn"); }
  };
  const openPicker = async () => {
    setPickerOpen(true);
    try { setCandidates((await listAnalyses({ limit: 100 })).rows.filter((a) => a.compatibility.compatible)); } catch { setCandidates([]); }
  };
  const addTile = (a: SavedAnalysis) => {
    setDirtyTiles([...tiles, { tile_id: `t_${a.analysis_id.slice(3)}_${tiles.length}`, analysis_id: a.analysis_id, x: 0, y: tiles.length, w: a.visual.visual_type === "kpi" ? 1 : 2, h: 1 }]);
    setDashboard((d) => (d ? { ...d, analyses: { ...(d.analyses ?? {}), [a.analysis_id]: a } } : d));
    setPickerOpen(false);
  };
  const refresh = async () => {
    setRefreshKey((k) => k + 1);
    setRefreshedAt(new Date().toISOString());
    try {
      const recorded = Object.values(latest)[0]?.dataset_version.dataset_version_id;
      const v = await fetchDatasetVersion(recorded);
      setMoved(v.moved ? { stale: v.moved.stale, tables_moved: v.moved.tables_moved } : null);
    } catch { /* freshness is a courtesy */ }
  };
  const duplicate = async () => { if (!dashboard) return; try { const d = await duplicateDashboard(dashboard.dashboard_id); router.push(`/dashboards/${encodeURIComponent(d.dashboard_id)}`); } catch (e) { toast.push((e as Error).message, "warn"); } };
  const remove = async () => { if (!dashboard || !window.confirm(copy.confirmDelete)) return; try { await deleteDashboard(dashboard.dashboard_id); router.push("/dashboards"); } catch (e) { toast.push((e as Error).message, "warn"); } };
  const toggleShare = async () => {
    if (!dashboard) return;
    try { setDashboard(await updateDashboard(dashboard.dashboard_id, { visibility: dashboard.visibility === "workspace" ? "private" : "workspace" })); }
    catch (e) { toast.push((e as Error).message, "warn"); }
  };

  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!dashboard || !model) return <Loading label={copy.title} cards={2} />;
  const stamp = Object.values(latest)[0];
  return (
    <div className={full ? "db-full" : undefined}>
      <PageHead title={editing ? "" : dashboard.name} sub={editing ? undefined : (dashboard.description ?? undefined)} actions={
        <>
          {editing ? (
            <>
              <input className="zinput" style={{ width: 260 }} aria-label={copy.name} value={name} onChange={(e) => setName(e.target.value)} maxLength={160} />
              <Button role="secondary" size="sm" icon={<Plus size={14} aria-hidden />} onClick={openPicker}>{copy.addVisual}</Button>
              {session.can("shareAnalysis") && <Button role="secondary" size="sm" onClick={toggleShare}>{dashboard.visibility === "workspace" ? copy.unshare : copy.share}</Button>}
              <Button role="primary" size="sm" onClick={save}>{copy.done}</Button>
            </>
          ) : (
            <>
              <Button role="secondary" size="sm" icon={<RefreshCw size={14} aria-hidden />} onClick={refresh}>{copy.refresh}</Button>
              <Button role="secondary" size="sm" icon={full ? <Minimize2 size={14} aria-hidden /> : <Maximize2 size={14} aria-hidden />} onClick={() => setFull((f) => !f)}>{full ? copy.exit : copy.fullScreen}</Button>
              {session.can("createAnalysis") && <Button role="secondary" size="sm" icon={<Copy size={14} aria-hidden />} onClick={duplicate}>{copy.duplicate}</Button>}
              {canEdit && <Button role="secondary" size="sm" icon={<Pencil size={14} aria-hidden />} onClick={() => setEditing(true)}>{copy.edit}</Button>}
              {canEdit && <Button role="danger" size="sm" icon={<Trash2 size={14} aria-hidden />} onClick={remove}>{copy.delete}</Button>}
            </>
          )}
        </>
      } />
      <p className="ins-plan" data-stale={moved?.stale ? "true" : "false"}>
        <span className="tag">{dashboard.visibility === "workspace" ? copy.workspace : copy.private}</span>
        {stamp && <span>{t.analytics.explore.dataCutoff}: <span className="fig">{stamp.dataset_version.data_cutoff ? DATE(stamp.dataset_version.data_cutoff) : "—"}</span> · {t.analytics.explore.lastUpdated}: <span className="fig">{stamp.dataset_version.last_updated ? DATE(stamp.dataset_version.last_updated) : "—"}</span></span>}
        {refreshedAt && <span>{copy.refreshed} {DATE(refreshedAt)}</span>}
        {moved?.stale && <strong>{copy.dataMoved} ({moved.tables_moved.join(", ")})</strong>}
        {dashboard.missing && dashboard.missing.length > 0 && <strong>{copy.missing}</strong>}
      </p>
      <FilterBar model={model} filters={sharedFilters} allowed={null} onChange={setUrlFilters} compact />
      <DashboardGrid dashboard={{ ...dashboard, spec: { ...dashboard.spec, tiles } }} model={model} editing={Boolean(editing && canEdit)} sharedFilters={sharedFilters} crossFilters={crossFilters}
                     onCrossFilters={setCrossFilters} onTiles={setDirtyTiles} refreshKey={refreshKey} onResults={setLatest} />
      <Drawer open={pickerOpen} title={copy.pick} onClose={() => setPickerOpen(false)}>
        {candidates.length === 0 ? <p className="zhelp">{copy.noAnalyses}</p> : (
          <ul className="db-pick">
            {candidates.map((a) => <li key={a.analysis_id}><button type="button" className="zb zb--tertiary zb--block" style={{ justifyContent: "flex-start" }} onClick={() => addTile(a)}>{a.name} <span className="dec-cat" style={{ marginInlineStart: "auto" }}>{t.analytics.visuals[a.visual.visual_type]}</span></button></li>)}
          </ul>
        )}
      </Drawer>
    </div>
  );
}

export default function DashboardPage() {
  return <Gate needsWorkspace={false}><Suspense fallback={<Loading label="Dashboard" cards={2} />}><Body /></Suspense></Gate>;
}
