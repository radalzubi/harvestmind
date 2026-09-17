"use client";

/**
 * EXPLORE — build an analysis from governed parts.
 *
 * Left: the semantic model. Centre: the analysis with its table twin and Data & scope. Right:
 * the visual and query configuration. Top: filters and the way to Ask ZAAD. Every choice is a
 * measure id, a dimension id, a grain or a bounded filter; the server validates and runs the spec;
 * the browser draws what came back. The state lives in the URL, so an analysis in progress can be
 * sent to someone before it is saved.
 */
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, MessageSquareText, Save } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, EmptyState, Loading, Notice, PageHead } from "@/components/workspace/ui";
import { Drawer } from "@/components/workspace/Table";
import { useToast } from "@/components/Toast";
import { useLocale } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { track } from "@/lib/zaad/product";
import {
  AnalyticsError, createAnalysis, exportResult, fetchModel, listDashboards, readAnalysis, runQuery, updateDashboard, validateQuery,
  type Dashboard, type ModelDoc, type ResultSet, type VisualSpec, type VisualType,
} from "@/lib/analytics/client";
import { EMPTY_BUILDER, allowedDimensionsFor, applyCrossFilter, fromSpec, metricLabel, stateFromParams, stateToParams, toSpec, type BuilderState } from "@/lib/analytics/spec";
import { allowedVisuals, recommendVisual } from "@/lib/analytics/visual";
import { drillThrough, recordsBehind } from "@/lib/analytics/links";
import { AnalysisCard } from "@/components/analytics/AnalysisCard";
import { ConfigPanel } from "@/components/analytics/ConfigPanel";
import { FilterBar } from "@/components/analytics/FilterBar";
import { ModelPanel } from "@/components/analytics/ModelPanel";

function useModel(): { model: ModelDoc | null; error: string | null } {
  const { locale } = useLocale();
  const [model, setModel] = useState<ModelDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    fetchModel(locale).then((m) => alive && setModel(m)).catch((e: Error) => alive && setError(e.message));
    return () => { alive = false; };
  }, [locale]);
  return { model, error };
}

function visualFor(state: BuilderState, result: ResultSet | null, title: string, description: string, chosen: VisualType | null, spec: NonNullable<ReturnType<typeof toSpec>>): VisualSpec {
  const type = chosen ?? (result ? recommendVisual(result) : "table");
  const dims = [...state.dimensions, ...(state.grain ? ["date"] : [])];
  const enc = type === "pivot" ? { rows: dims.slice(0, 1), columns: dims.slice(1, 2), y: state.measures }
    : type === "heatmap" ? { rows: dims.slice(0, 1), columns: dims.slice(1, 2), y: state.measures.slice(0, 1) }
    : type === "scatter" ? { x: state.measures[0], y: state.measures.slice(1, 2), color: state.dimensions[0] }
    : { x: state.grain ? "date" : state.dimensions[0], series: state.grain ? state.dimensions[0] : state.dimensions[1], y: state.measures };
  return { visual_type: type, title: { en: title, ar: title }, description: { en: description, ar: description }, query: spec, encoding: enc, formatting: { show_totals: true }, interactions: "both" };
}

function ExploreBody() {
  const params = useSearchParams();
  const router = useRouter();
  const session = useSession();
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const toast = useToast();
  const { model, error: modelError } = useModel();
  const [state, setState] = useState<BuilderState>(() => stateFromParams(params));
  const [result, setResult] = useState<ResultSet | null>(null);
  const [running, setRunning] = useState(false);
  const [refusal, setRefusal] = useState<{ code: string | null; message: string } | null>(null);
  const [saveOpen, setSaveOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"private" | "workspace">("private");
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [targetDashboard, setTargetDashboard] = useState("");
  const [drillStack, setDrillStack] = useState<BuilderState[]>([]);
  const lastSpec = useRef<string>("");

  useEffect(() => { track("insights_opened", { surface: "explore" }); }, []);

  // a saved analysis opened from the list: `?open=an_…`
  useEffect(() => {
    const open = params.get("open");
    if (!open) return;
    readAnalysis(open).then((a) => { setState(fromSpec(a.visual.query, a.visual.visual_type)); setName(a.name); setDescription(a.description ?? ""); }).catch((e: Error) => toast.push?.(e.message) ?? undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  // the URL follows the state
  useEffect(() => {
    const next = stateToParams(state).toString();
    if (next !== params.toString()) router.replace(`/explore${next ? `?${next}` : ""}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const spec = useMemo(() => toSpec(state), [state]);
  const allowedDims = useMemo(() => (model && state.measures.length ? allowedDimensionsFor(model.metrics, state.measures) : null), [model, state.measures]);
  const timeAllowed = allowedDims === null ? true : allowedDims.includes("date");

  // run when the spec changes (debounced), validated first so a refusal is worded by the server
  useEffect(() => {
    if (!spec) { setResult(null); setRefusal(null); return; }
    const key = JSON.stringify(spec);
    if (key === lastSpec.current) return;
    lastSpec.current = key;
    let alive = true;
    setRunning(true);
    const handle = window.setTimeout(() => {
      runQuery(spec).then((r) => { if (!alive) return; setResult(r); setRefusal(null); })
        .catch((e: unknown) => { if (!alive) return; setResult(null); setRefusal(e instanceof AnalyticsError ? { code: e.code, message: e.message } : { code: null, message: String((e as Error).message ?? e) }); })
        .finally(() => alive && setRunning(false));
    }, 250);
    return () => { alive = false; window.clearTimeout(handle); };
  }, [spec]);

  const update = useCallback((changes: Partial<BuilderState>) => setState((s) => ({ ...s, ...changes })), []);
  const toggleMeasure = useCallback((id: string) => setState((s) => {
    if (s.measures.includes(id)) return { ...s, measures: s.measures.filter((m) => m !== id), topBy: s.topBy === id ? null : s.topBy, sortField: s.sortField === id ? null : s.sortField };
    const fact = model?.metrics.find((m) => m.metric_id === id)?.fact;
    const currentFact = s.measures.length ? model?.metrics.find((m) => m.metric_id === s.measures[0])?.fact : null;
    if (currentFact && fact !== currentFact) return { ...EMPTY_BUILDER, measures: [id] };   // a different record: a new query
    if (s.measures.length >= 6) return s;
    const measures = [...s.measures, id];
    const allowed = model ? allowedDimensionsFor(model.metrics, measures) : [];
    return { ...s, measures, dimensions: s.dimensions.filter((d) => allowed.includes(d)), grain: allowed.includes("date") ? s.grain : null };
  }), [model]);
  const toggleDimension = useCallback((id: string) => setState((s) => {
    if (id === "date") return { ...s, grain: s.grain ? null : "month" };
    if (s.dimensions.includes(id)) return { ...s, dimensions: s.dimensions.filter((d) => d !== id), topN: s.dimensions.length === 1 ? null : s.topN };
    if (s.dimensions.length >= (s.grain ? 2 : 3)) return s;
    return { ...s, dimensions: [...s.dimensions, id] };
  }), []);

  // a click on a member: drill down where a path exists, else filter (cross-filter on the canvas)
  const onMember = useCallback((dimension: string, member: string) => {
    if (!model) return;
    const next = dimension === "date" ? null : model.drill_paths[dimension];
    setState((s) => {
      const filtered = { ...s, filters: applyCrossFilter(s.filters, dimension, member) };
      if (next && (allowedDims === null || allowedDims.includes(next)) && s.dimensions.includes(dimension)) {
        setDrillStack((stack) => [...stack, s]);
        return { ...filtered, dimensions: s.dimensions.map((d) => (d === dimension ? next : d)), topN: null };
      }
      if (dimension === "date" && s.grain && model.drill_paths[s.grain]) {
        setDrillStack((stack) => [...stack, s]);
        const [start] = member.split("T");
        return { ...s, grain: model.drill_paths[s.grain] as BuilderState["grain"], start, end: null, last: null, unit: null };
      }
      return filtered;
    });
  }, [model, allowedDims]);

  const drillUp = () => setDrillStack((stack) => { const prev = stack[stack.length - 1]; if (prev) setState(prev); return stack.slice(0, -1); });

  const visual = useMemo(() => (spec ? visualFor(state, result, name || autoTitle(state, model, lc), description || autoDescription(state, model, lc), state.visual, spec) : null), [spec, state, result, name, description, model, lc]);
  const allowed = result ? allowedVisuals(result) : [];
  const recommended = result ? recommendVisual(result) : null;

  const openSave = async () => {
    setSaveOpen(true);
    try { setDashboards((await listDashboards({ limit: 50 })).rows); } catch { setDashboards([]); }
  };
  const save = async () => {
    if (!visual || !name.trim()) return;
    try {
      const saved = await createAnalysis({ name: name.trim(), description: description.trim() || null, visual: { ...visual, visual_type: state.visual ?? recommended ?? "table" }, visibility, origin: "user" });
      if (targetDashboard) {
        const board = dashboards.find((d) => d.dashboard_id === targetDashboard);
        if (board) {
          const tiles = [...board.spec.tiles, { tile_id: `t_${saved.analysis_id.slice(3)}`, analysis_id: saved.analysis_id, x: 0, y: board.spec.tiles.length, w: 2, h: 1 }];
          await updateDashboard(board.dashboard_id, { spec: { ...board.spec, tiles } });
        }
      }
      toast.push?.(`${copy.saved}: ${saved.name}`);
      setSaveOpen(false);
      router.replace(`/explore?${stateToParams(state).toString()}&open=${encodeURIComponent(saved.analysis_id)}`);
    } catch (e) { toast.push?.((e as Error).message); }
  };
  const doExport = async (fmt: "csv" | "xlsx") => {
    if (!spec) return;
    try { await exportResult(spec, fmt, name || "analysis", lc); } catch (e) { toast.push?.((e as Error).message); }
  };
  const askHref = spec ? `/ask?spec=${encodeURIComponent(JSON.stringify(spec))}` : "/ask";

  if (modelError) return <Notice tone="warn">{modelError}</Notice>;
  if (!model) return <Loading label={copy.title} cards={2} />;
  const canSave = session.can("createAnalysis");
  const canExport = session.can("exportAnalytics");
  const leads: Array<{ href: string; label: string }> = [];
  if (result) { const r = recordsBehind(result); if (r) leads.push({ href: r.href, label: `${copy.openRecords} · ${r.label}` }); }
  for (const f of state.filters) if (f.values.length === 1) { const d = drillThrough(f.dimension_id, f.values[0]); if (d) leads.push(d); }

  return (
    <div className="ex">
      <PageHead title={copy.title} sub={copy.sub} actions={
        <>
          <Link href="/dashboards" className="zb zb--secondary zb--sm">{t.workspace.nav.dashboards}</Link>
          {session.can("askZaad") && <Link href={askHref} className="zb zb--secondary zb--sm"><MessageSquareText size={14} aria-hidden /> {copy.ask}</Link>}
          {canExport && spec && <Button role="secondary" size="sm" icon={<Download size={14} aria-hidden />} onClick={() => doExport("csv")}>{copy.export} {copy.csv}</Button>}
          {canExport && spec && <Button role="secondary" size="sm" onClick={() => doExport("xlsx")}>{copy.xlsx}</Button>}
          {canSave && spec && <Button role="primary" size="sm" icon={<Save size={14} aria-hidden />} onClick={openSave}>{copy.save}</Button>}
        </>
      } />
      <FilterBar model={model} filters={state.filters} allowed={allowedDims} onChange={(filters) => update({ filters })}
                 range={{ start: state.start, end: state.end, last: state.last, unit: state.unit }} onRange={(r) => update({ start: r.start, end: r.end, last: r.last, unit: r.unit })} />
      <div className="ex-grid">
        <ModelPanel model={model} selectedMeasures={state.measures} selectedDimensions={[...state.dimensions, ...(state.grain ? ["date"] : [])]} allowedDimensions={allowedDims}
                    onToggleMeasure={toggleMeasure} onToggleDimension={toggleDimension} />
        <div className="ex-canvas" aria-busy={running}>
          {!spec ? (
            <EmptyState title={copy.empty}>{copy.emptyHint}</EmptyState>
          ) : refusal ? (
            <Notice tone="warn"><strong>{copy.refused}{refusal.code ? ` (${refusal.code})` : ""}.</strong> {refusal.message}</Notice>
          ) : visual ? (
            <AnalysisCard visual={visual} result={result} height={340} onMember={onMember} leads={leads} wide
              actions={drillStack.length > 0 ? <button type="button" className="zb zb--tertiary zb--sm" onClick={drillUp}>← {copy.drillUp}</button> : undefined}>
              {result?.bounds.truncated && <p className="ex-hint">{copy.truncated.replace("{n}", String(result.bounds.limit_applied))}</p>}
              {result && Object.values(result.coverage).some((c) => c.thin_sample) && <p className="ex-hint">{copy.thin}</p>}
              {result && Object.values(result.coverage).some((c) => c.insufficient) && <p className="ex-hint">{copy.insufficient}</p>}
            </AnalysisCard>
          ) : null}
        </div>
        <ConfigPanel state={state} onChange={update} allowedVisuals={allowed.length ? allowed : ["table"]} recommended={recommended}
                     memberDimensions={state.dimensions} timeAllowed={timeAllowed}
                     measures={state.measures.map((id) => ({ id, label: (() => { const m = model.metrics.find((x) => x.metric_id === id); return m ? metricLabel(m, lc) : id; })() }))} />
      </div>
      <Drawer open={saveOpen} title={copy.save} onClose={() => setSaveOpen(false)} actions={<Button role="primary" onClick={save} disabled={!name.trim()}>{copy.save}</Button>}>
        <div className="zfield"><label className="zlabel" htmlFor="an-name">{copy.name}</label><input id="an-name" className="zinput" value={name} onChange={(e) => setName(e.target.value)} maxLength={160} /></div>
        <div className="zfield"><label className="zlabel" htmlFor="an-desc">{copy.description}</label><textarea id="an-desc" className="zinput" rows={3} value={description} onChange={(e) => setDescription(e.target.value)} maxLength={600} /></div>
        <div className="zfield"><label className="zlabel" htmlFor="an-vis">{copy.visibility}</label>
          <select id="an-vis" className="zinput" value={visibility} onChange={(e) => setVisibility(e.target.value as "private" | "workspace")} disabled={!session.can("shareAnalysis")}>
            <option value="private">{copy.private}</option><option value="workspace">{copy.workspace}</option>
          </select></div>
        <div className="zfield"><label className="zlabel" htmlFor="an-dash">{copy.addToDashboard}</label>
          <select id="an-dash" className="zinput" value={targetDashboard} onChange={(e) => setTargetDashboard(e.target.value)}>
            <option value="">—</option>{dashboards.map((d) => <option key={d.dashboard_id} value={d.dashboard_id}>{d.name}</option>)}
          </select></div>
      </Drawer>
    </div>
  );
}

function autoTitle(state: BuilderState, model: ModelDoc | null, lc: "en" | "ar"): string {
  if (!model) return "";
  const measures = state.measures.map((id) => { const m = model.metrics.find((x) => x.metric_id === id); return m ? metricLabel(m, lc) : id; }).join(", ");
  const dims = [...state.dimensions.map((d) => model.dimensions.find((x) => x.id === d)?.label[lc] ?? d), ...(state.grain ? [lc === "ar" ? "الزمن" : state.grain] : [])];
  return dims.length ? `${measures} ${lc === "ar" ? "حسب" : "by"} ${dims.join(" × ")}` : measures;
}

function autoDescription(state: BuilderState, model: ModelDoc | null, lc: "en" | "ar"): string {
  if (!model) return "";
  return state.measures.map((id) => model.metrics.find((x) => x.metric_id === id)).filter(Boolean).map((m) => `${metricLabel(m!, lc)}: ${m!.description[lc] ?? m!.description.en}`).join(" ");
}

export default function ExplorePage() {
  return (
    <Gate needsWorkspace={false}>
      <Suspense fallback={<Loading label="Explore" cards={2} />}>
        <ExploreBody />
      </Suspense>
    </Gate>
  );
}
