"use client";

/**
 * The right-hand configuration of one analysis: visual type (only the types the result's shape
 * allows), time grain, top-N, comparison, sort, totals. Everything here changes the spec, never
 * the numbers.
 */
import { useLocale } from "@/lib/i18n";
import type { Grain, VisualType } from "@/lib/analytics/client";
import type { BuilderState } from "@/lib/analytics/spec";

export function ConfigPanel({ state, onChange, allowedVisuals, recommended, memberDimensions, timeAllowed, measures }: {
  state: BuilderState; onChange: (next: Partial<BuilderState>) => void; allowedVisuals: VisualType[]; recommended: VisualType | null;
  memberDimensions: string[]; timeAllowed: boolean; measures: Array<{ id: string; label: string }>;
}) {
  const { t } = useLocale();
  const copy = t.analytics.explore;
  const grains: Grain[] = ["day", "week", "month", "quarter", "year"];
  return (
    <div className="ex-config" aria-label={copy.configure}>
      <h3 className="ex-model-h">{copy.visual}</h3>
      <div className="ex-visuals" role="radiogroup" aria-label={copy.visual}>
        {allowedVisuals.map((v) => (
          <button key={v} type="button" role="radio" aria-checked={state.visual === v || (!state.visual && v === recommended)} className="chip"
                  aria-pressed={state.visual === v || (!state.visual && v === recommended)} onClick={() => onChange({ visual: v })}>
            {t.analytics.visuals[v]}{v === recommended ? " ★" : ""}
          </button>
        ))}
      </div>
      {recommended && <p className="ex-hint">★ {copy.recommended}</p>}

      <h3 className="ex-model-h">{copy.grain}</h3>
      <select className="fld fld--block" aria-label={copy.grain} value={state.grain ?? ""} disabled={!timeAllowed} onChange={(e) => onChange({ grain: (e.target.value || null) as Grain | null, comparison: e.target.value ? state.comparison : false })}>
        <option value="">{copy.noGrain}</option>
        {grains.map((g) => <option key={g} value={g}>{t.analytics.grains[g]}</option>)}
      </select>
      <label className="ex-check"><input type="checkbox" disabled={!state.grain} checked={state.comparison} onChange={(e) => onChange({ comparison: e.target.checked })} /> {copy.comparison}</label>

      <h3 className="ex-model-h">{copy.topN}</h3>
      <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
        <select className="fld" aria-label={copy.topN} value={state.topN ?? ""} disabled={!memberDimensions.length} onChange={(e) => onChange({ topN: e.target.value ? Number(e.target.value) : null })}>
          <option value="">—</option>
          {[5, 10, 20, 50].map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <select className="fld" aria-label={copy.sort} value={state.topBy ?? ""} disabled={!state.topN} onChange={(e) => onChange({ topBy: e.target.value || null })}>
          {measures.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
        </select>
      </div>
      <label className="ex-check"><input type="checkbox" disabled={!state.topN} checked={state.others} onChange={(e) => onChange({ others: e.target.checked })} /> {copy.others}</label>

      <h3 className="ex-model-h">{copy.sort}</h3>
      <div style={{ display: "flex", gap: 6 }}>
        <select className="fld" aria-label={copy.sort} value={state.sortField ?? ""} onChange={(e) => onChange({ sortField: e.target.value || null })}>
          <option value="">—</option>
          {measures.map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
          {memberDimensions.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select className="fld" aria-label="direction" value={state.sortDir} onChange={(e) => onChange({ sortDir: e.target.value as "asc" | "desc" })}>
          <option value="desc">↓</option><option value="asc">↑</option>
        </select>
      </div>
    </div>
  );
}
