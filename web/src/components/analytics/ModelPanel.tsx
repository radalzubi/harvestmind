"use client";

/**
 * The semantic data panel: governed measures and dimensions, grouped by domain, searchable, with
 * the definition on hover and on focus. Nobody has to know a column name. A measure that is
 * classified but not queryable is listed greyed with its status, so the catalogue is honest about
 * what the vault holds.
 */
import { useMemo, useState } from "react";
import { Plus, Check, Info } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import type { DimensionDoc, MetricDoc, ModelDoc } from "@/lib/analytics/client";
import { metricLabel } from "@/lib/analytics/spec";

const DOMAIN_AR: Record<string, string> = { Demand: "الطلب", Inventory: "المخزون", Purchasing: "المشتريات", Suppliers: "الموردون", Customers: "العملاء", Service: "الخدمة", Decisions: "القرارات", Value: "القيمة" };

export function ModelPanel({ model, selectedMeasures, selectedDimensions, allowedDimensions, onToggleMeasure, onToggleDimension }: {
  model: ModelDoc; selectedMeasures: string[]; selectedDimensions: string[]; allowedDimensions: string[] | null;
  onToggleMeasure: (id: string) => void; onToggleDimension: (id: string) => void;
}) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const [q, setQ] = useState("");
  const needle = q.trim().toLowerCase();
  const domains = useMemo(() => {
    const out: Array<{ domain: string; metrics: MetricDoc[] }> = [];
    for (const domain of model.domains) {
      const metrics = model.metrics.filter((m) => m.domain === domain && (!needle || matches(m, needle, lc)));
      if (metrics.length) out.push({ domain, metrics });
    }
    return out;
  }, [model, needle, lc]);
  const dimensions = useMemo(() => model.dimensions.filter((d) => d.queryable && d.kind !== "register" && (!needle || (d.label[lc] ?? d.label.en).toLowerCase().includes(needle) || d.id.includes(needle))), [model, needle, lc]);
  const selectedFact = selectedMeasures.length ? model.metrics.find((m) => m.metric_id === selectedMeasures[0])?.fact : null;

  return (
    <div className="ex-model" aria-label={copy.model}>
      <label className="fld-wrap" style={{ display: "block", padding: "10px 10px 6px" }}>
        <span className="sr-only">{copy.search}</span>
        <input className="fld fld--block" placeholder={copy.search} aria-label={copy.search} value={q} onChange={(e) => setQ(e.target.value)} />
      </label>
      <div className="ex-model-scroll">
        <h3 className="ex-model-h">{copy.measures}</h3>
        {domains.map(({ domain, metrics }) => (
          <section key={domain} className="ex-domain" aria-label={domain}>
            <h4>{lc === "ar" ? DOMAIN_AR[domain] ?? domain : domain}</h4>
            <ul>
              {metrics.map((m) => {
                const on = selectedMeasures.includes(m.metric_id);
                const otherFact = selectedFact != null && m.fact !== selectedFact && !on;
                const disabled = !m.queryable;
                return (
                  <li key={m.metric_id}>
                    <button type="button" className="ex-item" aria-pressed={on} disabled={disabled} data-other-fact={otherFact ? "true" : undefined}
                            title={`${m.description[lc] ?? m.description.en}${otherFact ? ` — ${lc === "ar" ? "على سجلات مختلفة؛ يحل محل الاختيار" : "on different records; selecting it starts a new query"}` : ""}`}
                            onClick={() => onToggleMeasure(m.metric_id)}>
                      <span className="ex-item-label">{metricLabel(m, lc)}</span>
                      <span className="ex-item-meta">{disabled ? copy.notQueryable : m.unit}{m.evidence_class !== "OBSERVED_FACT" ? ` · ${m.evidence_class.toLowerCase().replace("_", " ")}` : ""}</span>
                      {on ? <Check size={14} aria-hidden /> : <Plus size={14} aria-hidden className="ex-item-plus" />}
                    </button>
                    <details className="ex-def">
                      <summary aria-label={`${copy.definition}: ${metricLabel(m, lc)}`}><Info size={12} aria-hidden /></summary>
                      <p><strong>{copy.definition}.</strong> {m.business_definition}</p>
                      <p><strong>{copy.allowedDims}:</strong> {m.allowed_dimensions.map((d) => model.dimensions.find((x) => x.id === d)?.label[lc] ?? d).join(", ")}</p>
                      <p style={{ color: "var(--ink-500)" }}>{copy.aggregation}: {m.aggregation_rule} · {copy.evidence}: {m.evidence_class} · {m.status}{m.register ? ` · ${copy.register}: ${m.register}` : ""}</p>
                    </details>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
        <h3 className="ex-model-h">{copy.dimensions}</h3>
        <ul className="ex-dims">
          {dimensions.map((d: DimensionDoc) => {
            const on = selectedDimensions.includes(d.id) || (d.id === "date" && false);
            const allowed = allowedDimensions === null || allowedDimensions.includes(d.id);
            return (
              <li key={d.id}>
                <button type="button" className="ex-item" aria-pressed={on} disabled={!allowed} title={allowed ? d.description : (lc === "ar" ? "لا تسمح به المقاييس المختارة" : "Not allowed by the selected measures")}
                        onClick={() => onToggleDimension(d.id)}>
                  <span className="ex-item-label">{d.label[lc] ?? d.label.en}</span>
                  <span className="ex-item-meta">{d.kind === "time" ? (lc === "ar" ? "زمن" : "time") : d.entity}</span>
                  {on ? <Check size={14} aria-hidden /> : <Plus size={14} aria-hidden className="ex-item-plus" />}
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

function matches(m: MetricDoc, needle: string, lc: "en" | "ar"): boolean {
  return metricLabel(m, lc).toLowerCase().includes(needle) || m.metric_id.includes(needle) || (m.description[lc] ?? "").toLowerCase().includes(needle) || m.domain.toLowerCase().includes(needle);
}
