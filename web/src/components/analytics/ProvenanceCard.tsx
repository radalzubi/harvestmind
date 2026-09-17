"use client";

/**
 * "Data & scope" for a ResultSet: the one provenance component every analytics surface uses.
 * Reuses the Insights disclosure by mapping the analytics provenance onto its shape, then adds
 * what the analytics layer knows on top: metric definitions with their versions, coverage per
 * measure, the dataset version and cutoff, blocked dimensions, and timing.
 */
import { Disclosure } from "@/components/workspace/ui";
import { DATE } from "@/lib/zaad/product";
import { useLocale } from "@/lib/i18n";
import type { ResultSet } from "@/lib/analytics/client";
import { cellValue, formatCell, reasonLabel } from "@/lib/analytics/spec";

export function ProvenanceCard({ result, defaultOpen }: { result: ResultSet; defaultOpen?: boolean }) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const p = result.provenance;
  const range = p.time.start || p.time.end ? `${p.time.start ?? "…"} → ${p.time.end ?? "…"}` : (lc === "ar" ? "كامل السجل" : "the whole history");
  const hint = `${range}${p.time.grain ? ` · ${t.analytics.grains[p.time.grain as keyof typeof t.analytics.grains] ?? p.time.grain}` : ""} · ${p.filters.length ? p.filters.map((f) => `${f.label[lc] ?? f.label.en} ${t.analytics.ops[f.op as keyof typeof t.analytics.ops] ?? f.op} ${f.values.join(", ")}`).join("; ") : (lc === "ar" ? "بلا مرشحات" : "no filters")} · ${result.bounds.rows} ${copy.rows}`;
  return (
    <Disclosure summary={copy.dataScope} hint={hint} defaultOpen={defaultOpen}>
      <dl className="kv ins-scope">
        {p.definitions.map((d) => (
          <div key={d.ref} style={{ display: "contents" }}>
            <dt>{d.display_name[lc] ?? d.display_name.en} <code className="ex-ref">{d.ref}</code></dt>
            <dd>{d.business_definition}<br /><span style={{ color: "var(--ink-500)" }}>{copy.aggregation}: {d.aggregation_rule} · {copy.evidence}: {d.evidence_class}{d.register ? ` · ${copy.register}: ${d.register}` : ""} · {copy.unit}: {d.unit}</span></dd>
          </div>
        ))}
        <dt>{lc === "ar" ? "البسط" : "Numerator"}</dt><dd>{p.numerator}</dd>
        <dt>{lc === "ar" ? "المقام" : "Denominator"}</dt><dd>{p.denominator}</dd>
        <dt>{lc === "ar" ? "مصدر البيانات" : "Source data"}</dt><dd><span dir="ltr">{p.source_data.join(", ") || p.fact}</span></dd>
        {Object.entries(result.coverage).map(([id, cov]) => {
          const col = result.columns.find((c) => c.metric_id === id);
          const total = cov.total;
          return (
            <div key={id} style={{ display: "contents" }}>
              <dt>{copy.coverage} · {col?.label[lc] ?? col?.label.en ?? id}</dt>
              <dd>{cov.measure}{cov.rows != null ? ` · ${cov.rows.toLocaleString("en-US")} ${copy.rows}` : ""}{cov.measured_share != null ? ` · ${(cov.measured_share * 100).toFixed(0)}%` : ""}
                {cov.insufficient ? ` · ${reasonLabel("INSUFFICIENT_COVERAGE", lc)}` : ""}{cov.thin_sample ? ` · ${copy.thin.replace("* ", "")}` : ""}
                {total !== undefined && col && (cellValue(total) !== null ? ` · ${copy.total}: ${formatCell(total, col, lc)}` : ` · ${copy.total}: ${reasonLabel((total as { reason?: string })?.reason, lc)}`)}</dd>
            </div>
          );
        })}
        {Object.entries(p.blocked).map(([dim, why]) => <div key={dim} style={{ display: "contents" }}><dt>{copy.blocked} · {dim}</dt><dd>{why.reason}: {why.why}</dd></div>)}
        <dt>{copy.datasetVersion}</dt><dd><code className="ex-ref">{result.dataset_version.dataset_version_id}</code></dd>
        <dt>{copy.dataCutoff}</dt><dd>{p.data_cutoff ? DATE(p.data_cutoff) : reasonLabel("UNKNOWN", lc)}</dd>
        <dt>{copy.lastUpdated}</dt><dd>{p.last_updated ? DATE(p.last_updated) : reasonLabel("UNKNOWN", lc)}</dd>
        {p.plan && <><dt>{lc === "ar" ? "الخطة" : "Plan"}</dt><dd>{p.plan.job_id} · {p.plan.finished_at ? DATE(p.plan.finished_at) : "—"}{p.plan.stale ? ` · ${p.plan.stale_reason ?? "stale"}` : ""}</dd></>}
        <dt>{copy.modelVersion}</dt><dd>{result.semantic_model_version} · {lc === "ar" ? "أُنشئ" : "generated"} {DATE(result.generated_at)} · {result.timing.executed_ms.toFixed(0)} {copy.ms}{result.timing.cache === "hit" ? ` · ${copy.cached}` : ""}</dd>
        {p.notes.length > 0 && <><dt>{lc === "ar" ? "ملاحظة" : "Note"}</dt><dd>{p.notes.join("; ")}</dd></>}
      </dl>
    </Disclosure>
  );
}
