"use client";

/**
 * Filters, always visible: dimension-member filters with searchable value lists from the server,
 * a date range (absolute or relative), clear. Every active filter is a chip with its own remove.
 * Nothing is filtered that is not shown here.
 */
import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import { fetchMembers, type Filter, type FilterOp, type Grain, type ModelDoc } from "@/lib/analytics/client";

export interface RangeState { start: string | null; end: string | null; last: number | null; unit: Grain | null }

export function FilterBar({ model, filters, allowed, onChange, range, onRange, compact }: {
  model: ModelDoc; filters: Filter[]; allowed: string[] | null; onChange: (next: Filter[]) => void;
  range?: RangeState; onRange?: (next: RangeState) => void; compact?: boolean;
}) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const [adding, setAdding] = useState<string | null>(null);
  const [op, setOp] = useState<FilterOp>("in");
  const [members, setMembers] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [typed, setTyped] = useState("");
  const dims = model.dimensions.filter((d) => d.queryable && d.kind === "member" && (allowed === null || allowed.includes(d.id)));

  useEffect(() => {
    if (!adding) return;
    let alive = true;
    const handle = window.setTimeout(() => {
      fetchMembers(adding, search || undefined, 100).then((r) => { if (alive) setMembers(r.members); }).catch(() => { if (alive) setMembers([]); });
    }, 150);
    return () => { alive = false; window.clearTimeout(handle); };
  }, [adding, search]);

  const label = (id: string) => model.dimensions.find((d) => d.id === id)?.label[lc] ?? id;
  const commit = () => {
    if (!adding) return;
    const values = op === "in" ? picked : op === "is_null" || op === "not_null" ? [] : [typed.trim()];
    if ((op === "in" && !values.length) || (["eq", "ne", "contains"].includes(op) && !values[0])) return;
    onChange([...filters.filter((f) => f.dimension_id !== adding), { dimension_id: adding, op, values }]);
    setAdding(null); setPicked([]); setTyped(""); setSearch(""); setOp("in");
  };
  const remove = (f: Filter) => onChange(filters.filter((x) => x !== f));

  return (
    <div className={compact ? "ex-filters ex-filters--compact" : "ex-filters"} role="group" aria-label={copy.filters}>
      {filters.map((f) => (
        <span key={`${f.dimension_id}:${f.op}`} className="chip ex-chip">
          <span>{label(f.dimension_id)} {t.analytics.ops[f.op]} {f.values.length > 3 ? `${f.values.slice(0, 3).join(", ")} +${f.values.length - 3}` : f.values.join(", ")}</span>
          <button type="button" aria-label={`${copy.remove} ${label(f.dimension_id)}`} onClick={() => remove(f)}><X size={12} aria-hidden /></button>
        </span>
      ))}
      {range && onRange && (
        <span className="ex-range">
          <select className="fld" aria-label={copy.range} value={range.last && range.unit ? `${range.last}${range.unit[0]}` : range.start || range.end ? "custom" : ""}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === "") onRange({ start: null, end: null, last: null, unit: null });
                    else if (v === "custom") onRange({ ...range, last: null, unit: null, start: range.start ?? "", end: range.end ?? "" });
                    else { const m = v.match(/^(\d+)([dwmqy])$/); if (m) onRange({ start: null, end: null, last: Number(m[1]), unit: ({ d: "day", w: "week", m: "month", q: "quarter", y: "year" } as Record<string, Grain>)[m[2]] }); }
                  }}>
            <option value="">{lc === "ar" ? "كامل السجل" : "Whole history"}</option>
            <option value="12w">{copy.last} 12 {t.analytics.grains.week.toLowerCase()}s</option>
            <option value="26w">{copy.last} 26 {t.analytics.grains.week.toLowerCase()}s</option>
            <option value="6m">{copy.last} 6 {t.analytics.grains.month.toLowerCase()}s</option>
            <option value="12m">{copy.last} 12 {t.analytics.grains.month.toLowerCase()}s</option>
            <option value="1y">{copy.last} 1 {t.analytics.grains.year.toLowerCase()}</option>
            <option value="custom">{copy.from} / {copy.to}</option>
          </select>
          {(range.start !== null || range.end !== null) && !range.last && (
            <>
              <input className="fld" type="date" aria-label={copy.from} value={range.start ?? ""} onChange={(e) => onRange({ ...range, start: e.target.value || null })} />
              <input className="fld" type="date" aria-label={copy.to} value={range.end ?? ""} onChange={(e) => onRange({ ...range, end: e.target.value || null })} />
            </>
          )}
        </span>
      )}
      {adding === null ? (
        <select className="fld" aria-label={copy.addFilter} value="" onChange={(e) => { setAdding(e.target.value || null); setPicked([]); setTyped(""); }}>
          <option value="">{copy.addFilter}…</option>
          {dims.map((d) => <option key={d.id} value={d.id}>{d.label[lc] ?? d.label.en}</option>)}
        </select>
      ) : (
        <div className="ex-filter-editor" role="group" aria-label={`${copy.addFilter}: ${label(adding)}`}>
          <strong>{label(adding)}</strong>
          <select className="fld" aria-label="op" value={op} onChange={(e) => setOp(e.target.value as FilterOp)}>
            {(["in", "eq", "ne", "contains", "is_null", "not_null"] as FilterOp[]).map((o) => <option key={o} value={o}>{t.analytics.ops[o]}</option>)}
          </select>
          {op === "in" ? (
            <>
              <input className="fld" placeholder={copy.search} aria-label={copy.search} value={search} onChange={(e) => setSearch(e.target.value)} />
              <div className="ex-members" role="listbox" aria-multiselectable="true" aria-label={label(adding)}>
                {members.map((m) => (
                  <label key={m} className="ex-member-opt">
                    <input type="checkbox" checked={picked.includes(m)} onChange={(e) => setPicked((p) => (e.target.checked ? [...p, m] : p.filter((x) => x !== m)))} /> <span dir="auto">{m}</span>
                  </label>
                ))}
                {members.length === 0 && <span style={{ fontSize: 12, color: "var(--ink-500)" }}>{lc === "ar" ? "لا قيم" : "No values"}</span>}
              </div>
            </>
          ) : op === "is_null" || op === "not_null" ? null : (
            <input className="fld" aria-label={label(adding)} value={typed} onChange={(e) => setTyped(e.target.value)} dir="auto" />
          )}
          <button type="button" className="zb zb--primary zb--sm" onClick={commit}>{copy.add}</button>
          <button type="button" className="zb zb--tertiary zb--sm" onClick={() => { setAdding(null); setPicked([]); }}>{t.commands.cancel}</button>
        </div>
      )}
      {filters.length > 0 && <button type="button" className="zb zb--tertiary zb--sm" onClick={() => onChange([])}>{copy.clear}</button>}
    </div>
  );
}
