"use client";

/**
 * The table twin of every visual, and the pivot. Sortable in the browser over the one page the
 * server sent (the server has already bounded it), paginated in steps of fifty, with totals only
 * where the contract says the measure may be summed — a ratio's total is the ratio of sums the
 * server computed, a snapshot's is not shown, and the reason is written where the number is not.
 */
import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useLocale } from "@/lib/i18n";
import type { Cell, Encoding, ResultColumn, ResultSet } from "@/lib/analytics/client";
import { cellReason, cellValue, cellWhy, formatCell, formatDimension, isNull, reasonLabel } from "@/lib/analytics/spec";

const PAGE = 50;

export function PivotTable({ result, pivot, encoding, showTotals = true, onMember, compact }: {
  result: ResultSet; pivot?: boolean; encoding?: Encoding; showTotals?: boolean; onMember?: (dimension: string, member: string) => void; compact?: boolean;
}) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const [sort, setSort] = useState<{ col: number; dir: "asc" | "desc" } | null>(null);
  const [page, setPage] = useState(0);
  const dims = result.columns.map((c, i) => ({ c, i })).filter(({ c }) => c.kind === "dimension");
  const measures = result.columns.map((c, i) => ({ c, i })).filter(({ c }) => c.kind !== "dimension");

  const rows = useMemo(() => {
    const out = [...result.rows];
    if (sort) {
      const { col, dir } = sort;
      const isMeasure = result.columns[col].kind !== "dimension";
      out.sort((a, b) => {
        const av = isMeasure ? cellValue(a[col]) : (isNull(a[col]) ? null : String(a[col]));
        const bv = isMeasure ? cellValue(b[col]) : (isNull(b[col]) ? null : String(b[col]));
        if (av === null && bv === null) return 0;
        if (av === null) return 1;
        if (bv === null) return -1;
        const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
        return dir === "asc" ? cmp : -cmp;
      });
    }
    return out;
  }, [result.rows, result.columns, sort]);

  if (pivot && dims.length === 2 && measures.length >= 1) {
    return <Pivot result={result} rows={rows} rowDim={dims.find(({ c }) => c.id === encoding?.rows?.[0]) ?? dims[0]}
                  colDim={dims.find(({ c }) => c.id === encoding?.columns?.[0] && c.id !== (encoding?.rows?.[0] ?? dims[0].c.id)) ?? dims[1]} measure={measures[0]} showTotals={showTotals} onMember={onMember} />;
  }

  const pageRows = rows.slice(page * PAGE, page * PAGE + PAGE);
  const pages = Math.ceil(rows.length / PAGE);
  const click = (i: number) => setSort((s) => (s && s.col === i ? { col: i, dir: s.dir === "asc" ? "desc" : "asc" } : { col: i, dir: result.columns[i].kind === "dimension" ? "asc" : "desc" }));
  return (
    <div>
      <div className="tbl-wrap">
        <table className={compact ? "tbl tbl--dense ex-table" : "tbl ex-table"}>
          <caption className="sr-only">{result.provenance.metric}</caption>
          <thead>
            <tr>
              {result.columns.map((c, i) => (
                <th key={c.id} scope="col" data-align={c.kind === "dimension" ? "start" : "end"} aria-sort={sort?.col === i ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}>
                  <button type="button" className="tbl-sort" onClick={() => click(i)} aria-label={`${copy.sort} ${c.label[lc] ?? c.label.en}`}>
                    {c.label[lc] ?? c.label.en}{c.kind === "comparison" ? "" : ""}
                    {sort?.col === i && (sort.dir === "asc" ? <ArrowUp size={12} aria-hidden /> : <ArrowDown size={12} aria-hidden />)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, i) => <CellView key={i} cell={cell} column={result.columns[i]} onMember={onMember} locale={lc} />)}
              </tr>
            ))}
          </tbody>
          {showTotals && result.rows.length > 1 && (
            <tfoot>
              <tr>
                {result.columns.map((c, i) => <TotalCell key={c.id} column={c} first={i === 0} result={result} locale={lc} label={copy.total} overall={copy.overall} none={copy.totalNotAdditive} />)}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      {(pages > 1 || result.bounds.truncated) && (
        <div className="tbl-pager">
          <p className="tbl-count">{rows.length.toLocaleString("en-US")} {copy.rows}{result.bounds.truncated ? ` · ${copy.truncated.replace("{n}", String(result.bounds.limit_applied))}` : ""}</p>
          {pages > 1 && (
            <div style={{ display: "flex", gap: 6 }}>
              <button type="button" className="zb zb--secondary zb--sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>‹</button>
              <span style={{ fontSize: 12.5, color: "var(--ink-500)", alignSelf: "center" }}>{page + 1} / {pages}</span>
              <button type="button" className="zb zb--secondary zb--sm" disabled={page >= pages - 1} onClick={() => setPage((p) => p + 1)}>›</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CellView({ cell, column, onMember, locale }: { cell: Cell; column: ResultColumn; onMember?: (d: string, m: string) => void; locale: "en" | "ar" }) {
  if (column.kind === "dimension") {
    const text = formatDimension(cell, column, locale);
    if (isNull(cell)) return <td data-align="start"><span className="na" title={cell.why}>{text}</span></td>;
    const member = String(cell);
    return <td data-align="start">{onMember && column.dimension_kind !== "time" ? <button type="button" className="ex-member" onClick={() => onMember(column.id, member)}>{text}</button> : text}</td>;
  }
  const v = cellValue(cell);
  const reason = cellReason(cell);
  const why = cellWhy(cell) ?? undefined;
  const thin = typeof cell === "object" && cell !== null && (cell as { thin?: boolean }).thin;
  return (
    <td data-align="end" data-num title={why ?? (thin ? "thin sample" : undefined)}>
      {v === null ? <span className="na">{reasonLabel(reason, locale)}</span> : <span className={reason === "INSUFFICIENT_COVERAGE" ? "ex-weak" : undefined}>{formatCell(cell, column, locale)}{thin ? "†" : ""}</span>}
    </td>
  );
}

function TotalCell({ column, first, result, locale, label, overall, none }: { column: ResultColumn; first: boolean; result: ResultSet; locale: "en" | "ar"; label: string; overall: string; none: string }) {
  if (column.kind === "dimension") return <th scope="row" data-align="start">{first ? label : ""}</th>;
  if (column.kind === "comparison" || !column.metric_id) return <td data-align="end" />;
  const total = result.coverage[column.metric_id]?.total;
  if (total === undefined) return <td data-align="end" />;
  const v = cellValue(total);
  if (v === null) return <td data-align="end"><span className="na" title={cellWhy(total) ?? undefined}>{none}</span></td>;
  const basis = typeof total === "object" && total !== null && (total as { basis?: string }).basis === "overall";
  return <td data-align="end" data-num title={basis ? overall : undefined}><strong>{formatCell(total, column, locale)}</strong>{basis ? <small style={{ color: "var(--ink-500)" }}> ({overall.toLowerCase()})</small> : null}</td>;
}

function Pivot({ result, rows, rowDim, colDim, measure, showTotals, onMember }: {
  result: ResultSet; rows: Cell[][]; rowDim: { c: ResultColumn; i: number }; colDim: { c: ResultColumn; i: number }; measure: { c: ResultColumn; i: number };
  showTotals: boolean; onMember?: (d: string, m: string) => void;
}) {
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.explore;
  const rowKeys: string[] = [], colKeys: string[] = [];
  const lookup = new Map<string, Cell>();
  for (const row of rows) {
    const r = formatDimension(row[rowDim.i], rowDim.c, lc), c = formatDimension(row[colDim.i], colDim.c, lc);
    if (!rowKeys.includes(r)) rowKeys.push(r);
    if (!colKeys.includes(c)) colKeys.push(c);
    lookup.set(`${r} ${c}`, row[measure.i]);
  }
  if (rowDim.c.dimension_kind === "time") rowKeys.sort();
  if (colDim.c.dimension_kind === "time") colKeys.sort();
  const additive = Boolean(measure.c.additive);
  const rowTotal = (r: string) => colKeys.reduce((acc, c) => { const v = cellValue(lookup.get(`${r} ${c}`) ?? null); return v === null ? acc : (acc ?? 0) + v; }, null as number | null);
  return (
    <div className="tbl-wrap">
      <table className="tbl ex-table">
        <caption className="sr-only">{measure.c.label[lc] ?? measure.c.label.en} · {rowDim.c.label[lc] ?? rowDim.c.label.en} × {colDim.c.label[lc] ?? colDim.c.label.en}</caption>
        <thead>
          <tr>
            <th scope="col">{rowDim.c.label[lc] ?? rowDim.c.label.en} \ {colDim.c.label[lc] ?? colDim.c.label.en}</th>
            {colKeys.map((c) => <th key={c} scope="col" data-align="end">{c}</th>)}
            {showTotals && additive && <th scope="col" data-align="end">{copy.total}</th>}
          </tr>
        </thead>
        <tbody>
          {rowKeys.map((r) => (
            <tr key={r}>
              <th scope="row">{onMember && rowDim.c.dimension_kind !== "time" ? <button type="button" className="ex-member" onClick={() => onMember(rowDim.c.id, r)}>{r}</button> : r}</th>
              {colKeys.map((c) => {
                const cell = lookup.get(`${r} ${c}`);
                if (cell === undefined) return <td key={c} data-align="end"><span className="na">—</span></td>;
                const v = cellValue(cell);
                return <td key={c} data-align="end" data-num title={cellWhy(cell) ?? undefined}>{v === null ? <span className="na">{reasonLabel(cellReason(cell), lc)}</span> : formatCell(cell, measure.c, lc)}</td>;
              })}
              {showTotals && additive && <td data-align="end" data-num><strong>{rowTotal(r) === null ? "—" : formatCell(rowTotal(r), measure.c, lc)}</strong></td>}
            </tr>
          ))}
        </tbody>
        {showTotals && (
          <tfoot>
            <tr>
              <th scope="row">{copy.total}</th>
              {colKeys.map((c) => {
                if (!additive) return <td key={c} data-align="end"><span className="na">{copy.totalNotAdditive}</span></td>;
                const total = rowKeys.reduce((acc, r) => { const v = cellValue(lookup.get(`${r} ${c}`) ?? null); return v === null ? acc : (acc ?? 0) + v; }, null as number | null);
                return <td key={c} data-align="end" data-num><strong>{total === null ? "—" : formatCell(total, measure.c, lc)}</strong></td>;
              })}
              {additive && <td data-align="end" data-num><strong>{(() => { const tot = result.coverage[measure.c.metric_id ?? ""]?.total; return tot !== undefined && cellValue(tot) !== null ? formatCell(tot, measure.c, lc) : "—"; })()}</strong></td>}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  );
}
