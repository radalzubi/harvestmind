"use client";

/**
 * DATA — inspect what ZAAD actually holds.
 *
 * The previous version showed row counts. A row count is not evidence: an operator who suspects a
 * number is wrong needs to see the record behind it, and 474,795 rows they cannot open is a claim,
 * not a demonstration. So this is a real explorer over the operator's own vault — paged, sorted and
 * filtered on the server, with one record at a time openable in full.
 *
 * Two boundaries the page keeps visible:
 *
 *   * **This is evidence, not a workbench.** Uploaded records are read-only here. Operating on the
 *     business happens in Inventory, Purchase orders, Decisions and Network.
 *   * **Only declared datasets and declared columns.** The server refuses any name it did not
 *     publish, so nothing typed into this page can reach the database as an identifier.
 */
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Download, RefreshCw } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Disclosure, EmptyState, ErrorState, Loading, Notice, PageHead, Section, TechnicalDetails } from "@/components/workspace/ui";
import { Column, DataTable, Drawer, Pager, SearchField, SelectField, Toolbar } from "@/components/workspace/Table";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useReadiness } from "@/lib/zaad/readiness";
import {
  DATE, NUMBER, fetchDataset, fetchDatasetValues, fetchDatasets,
  type DatasetInfo, type DatasetPage,
} from "@/lib/zaad/product";

const PAGE = 50;

function cell(value: unknown, kind: string) {
  if (value === null || value === undefined || value === "") return <span className="na">—</span>;
  if (kind === "number") {
    const number = Number(value);
    return Number.isFinite(number) ? NUMBER(number, Math.abs(number) < 100 && number % 1 !== 0 ? 2 : 0) : String(value);
  }
  if (kind === "date" || kind === "timestamp") return DATE(String(value));
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

/** One record, every column, for when a person needs to check a single row. */
function RecordPanel({ row, columns, onClose }: {
  row: Record<string, unknown>; columns: DatasetPage["columns"]; onClose: () => void;
}) {
  return (
    <Drawer open title="One record" onClose={onClose} sub="Exactly as it was uploaded">
      <dl className="kv">
        {columns.map((column) => (
          <div key={column.name} style={{ display: "contents" }}>
            <dt>{column.label}</dt>
            <dd>{cell(row[column.name], column.kind)}</dd>
          </div>
        ))}
      </dl>
      <div style={{ marginTop: 18 }}>
        <Disclosure summary="Technical details" hint="raw values and column names">
          <pre className="disc-tech">{JSON.stringify(row, null, 2)}</pre>
        </Disclosure>
      </div>
    </Drawer>
  );
}

function Explorer({ datasets }: { datasets: DatasetInfo[] }) {
  const params = useSearchParams();
  const router = useRouter();
  const dataset = params.get("dataset") ?? datasets.find((d) => (d.rows ?? 0) > 0)?.key ?? datasets[0]?.key ?? "products";
  const q = params.get("q") ?? "";
  const sort = params.get("sort") ?? "";
  const direction = params.get("dir") ?? "asc";
  const offset = Number(params.get("offset") ?? 0);
  const filterColumn = params.get("fcol") ?? "";
  const filterValue = params.get("fval") ?? "";
  const openRow = params.get("row");

  const [page, setPage] = useState<DatasetPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState(q);
  const [values, setValues] = useState<string[]>([]);

  const info = useMemo(() => datasets.find((d) => d.key === dataset), [datasets, dataset]);

  const set = useCallback((changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("offset" in changes)) next.delete("offset");
    router.replace(`/data?${next.toString()}`, { scroll: false });
  }, [params, router]);

  useEffect(() => { setTyped(q); }, [q]);
  useEffect(() => {
    const handle = window.setTimeout(() => { if (typed !== q) set({ q: typed || null }); }, 250);
    return () => window.clearTimeout(handle);
  }, [typed, q, set]);

  useEffect(() => {
    if (!filterColumn) { setValues([]); return; }
    let alive = true;
    fetchDatasetValues(dataset, filterColumn).then((r) => alive && setValues(r.values)).catch(() => alive && setValues([]));
    return () => { alive = false; };
  }, [dataset, filterColumn]);

  useEffect(() => {
    let alive = true;
    setError(null);
    fetchDataset(dataset, {
      q: q || undefined, sort: sort || undefined, direction, limit: PAGE, offset,
      where: filterColumn && filterValue ? [`${filterColumn}:${filterValue}`] : [],
    })
      .then((p) => alive && setPage(p))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [dataset, q, sort, direction, offset, filterColumn, filterValue]);

  const columns: Column<Record<string, unknown>>[] = useMemo(() => {
    if (!page) return [];
    return page.columns.map((column, index) => ({
      key: column.name,
      label: column.label,
      numeric: column.kind === "number",
      sortable: true,
      hideBelow: index > 5 ? 900 : undefined,
      title: (row) => (row[column.name] == null ? undefined : String(row[column.name])),
      render: (row) => cell(row[column.name], column.kind),
    }));
  }, [page]);

  const selected = useMemo(() => {
    if (!openRow || !page) return null;
    const index = Number(openRow);
    return Number.isFinite(index) ? page.rows[index] ?? null : null;
  }, [openRow, page]);

  return (
    <>
      <Toolbar>
        <SelectField value={dataset} onChange={(v) => set({ dataset: v, fcol: null, fval: null, sort: null, q: null })}
          label="What to look at" all=""
          options={datasets.map((d) => ({
            value: d.key,
            label: `${d.label}${d.rows != null ? ` · ${d.rows.toLocaleString("en-US")}` : ""}`,
          }))} />
        <SearchField value={typed} onChange={setTyped} label="Search records" placeholder="Search these records" />
        {info?.filters.length ? (
          <SelectField value={filterColumn} onChange={(v) => set({ fcol: v, fval: null })}
            label="Filter column" all="No filter"
            options={info.filters.map((f) => ({ value: f, label: f.replaceAll("_", " ") }))} />
        ) : null}
        {filterColumn && values.length > 0 && (
          <SelectField value={filterValue} onChange={(v) => set({ fval: v })}
            label={`Value for ${filterColumn}`} all="Any value"
            options={values.map((v) => ({ value: v, label: v }))} />
        )}
        <div className="tbar-spacer" />
        <Button size="sm" role="tertiary" icon={<RefreshCw size={14} aria-hidden />} onClick={() => set({})}>Refresh</Button>
      </Toolbar>

      {error && <Notice tone="warn">{error}</Notice>}
      {!page && !error && <Loading label="Reading these records…" cards={2} />}
      {page && !page.served && (
        <EmptyState title={`No ${page.label.toLowerCase()} in this workspace`}
          actions={<ButtonLink href="/upload" role="primary">Add this source</ButtonLink>}>
          {page.description}
        </EmptyState>
      )}
      {page?.served && (
        <>
          <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--ink-600)", maxWidth: "72ch", lineHeight: 1.6 }}>
            {page.description}
          </p>
          <DataTable caption={`${page.label} as uploaded`} columns={columns} rows={page.rows}
            rowKey={(row) => String(page.rows.indexOf(row))}
            selected={openRow} onSelect={(row) => set({ row: String(page.rows.indexOf(row)), offset: String(offset) })}
            sort={page.sort} direction={page.direction}
            onSort={(key) => set({ sort: key, dir: page.sort === key && page.direction === "asc" ? "desc" : "asc" })}
            empty={page.offset >= page.total && page.total > 0 ? undefined
              : <EmptyState title="No record matches that">Clear the search or the filter.</EmptyState>} />
          <Pager total={page.total} limit={page.limit} offset={page.offset} unit="records"
            isFloor={page.total_is_floor} onOffset={(next) => set({ offset: String(next) })} />
        </>
      )}

      {selected && page && (
        <RecordPanel row={selected} columns={page.columns} onClose={() => set({ row: null, offset: String(offset) })} />
      )}
    </>
  );
}

function DataBody() {
  const workspace = useWorkspaceData();
  const readiness = useReadiness();
  const [datasets, setDatasets] = useState<DatasetInfo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { fetchDatasets().then((d) => setDatasets(d.datasets)).catch((e) => setError(e.message)); }, []);

  if (error) {
    return <ErrorState title="Your data could not be read"
      affects="Nothing was changed; this page only reads."
      whatToDo="Try again in a moment."
      detail={error} actions={<ButtonLink href="/upload" role="primary">Go to Upload</ButtonLink>} />;
  }
  if (!datasets) return <Loading label="Reading what your workspace holds…" cards={2} />;

  const held = datasets.filter((d) => (d.rows ?? 0) > 0);
  const total = held.reduce((a, d) => a + (d.rows ?? 0), 0);
  const origin = workspace.build?.origin_monday;

  return (
    <>
      <PageHead
        title="Data"
        sub={`${total.toLocaleString("en-US")} records across ${held.length} source${held.length === 1 ? "" : "s"}${origin ? `, read up to ${DATE(origin)}` : ""}. These are the records ZAAD plans from.`}
        actions={<ButtonLink size="sm" href="/upload" icon={<Download size={14} aria-hidden style={{ transform: "rotate(180deg)" }} />}>Add or replace data</ButtonLink>}
      />

      <Notice>
        Everything here is read-only evidence, exactly as you uploaded it. To change what ZAAD does with it, work
        in <Link href="/inventory">Inventory</Link>, <Link href="/orders">Purchase orders</Link> or{" "}
        <Link href="/decisions">Decisions</Link> — a correction to a record belongs in the source system and a
        fresh upload.
      </Notice>

      <div style={{ marginTop: 18 }}>
        <Explorer datasets={datasets} />
      </div>

      <Section title="What ZAAD fitted from your history">
        {workspace.build?.fits && Object.keys(workspace.build.fits).length > 0 ? (
          <DataTable caption="Supplier reliability fitted from your own receipts" dense
            rows={Object.entries(workspace.build.fits).map(([supplier, fit]) => ({ supplier, ...fit }))}
            rowKey={(r) => r.supplier}
            columns={[
              { key: "supplier", label: "Supplier",
                render: (r) => <Link href={`/diagnostics/supplier/${encodeURIComponent(r.supplier)}`}>{r.supplier}</Link> },
              { key: "fill_mean", label: "Quantity arriving", numeric: true,
                render: (r) => r.fill_mean != null ? `${(r.fill_mean * 100).toFixed(1)}%` : <span className="na">not measured</span> },
              { key: "lead_days", label: "Lead (days)", numeric: true,
                render: (r) => r.lead_days != null ? NUMBER(Math.round(r.lead_days)) : <span className="na">—</span> },
              { key: "sample_size", label: "Deliveries", numeric: true,
                render: (r) => r.sample_size != null ? NUMBER(r.sample_size) : <span className="na">—</span> },
              { key: "provenance", label: "Where from", hideBelow: 700,
                render: (r) => (r.provenance ?? "").replaceAll("_", " ").toLowerCase() || <span className="na">—</span> },
            ]} />
        ) : (
          <Notice>Supplier reliability appears once goods received are matched to purchase orders.</Notice>
        )}
      </Section>

      <Section title="Data quality">
        {readiness.score != null ? (
          <dl className="snap">
            <div><dt>Overall</dt><dd>{Math.round(readiness.score)}<small>out of 100{readiness.scoreLabel ? ` · ${readiness.scoreLabel}` : ""}</small></dd></div>
            {/* "across the sources above" pointed at a page listing twelve datasets, while this
                number is the sum of the six the quality report covers — 474,795 against the
                474,848 in the heading, 53 apart, with the full list in between. It names its own
                set now, and the stat beside it already says "of 6". */}
            <div><dt>Rows read</dt><dd>{readiness.totalRows.toLocaleString("en-US")}<small>across the {readiness.sources.length} sources this report covers</small></dd></div>
            <div><dt>Sources with issues</dt><dd>{readiness.sources.filter((s) => s.issues.length).length}<small>of {readiness.sources.length}</small></dd></div>
          </dl>
        ) : <Notice>A quality report appears once a required source is loaded.</Notice>}
      </Section>

      <Section title="Advanced">
        <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "4px 16px 8px" }}>
          {/* The heading and the count are two table columns, not two spans that can overlap when a
              table name is long or a count is large. */}
          <Disclosure summary="Source names and row counts" hint="for a technical reader">
            <DataTable caption="Staging table names and their row counts" dense
              rows={datasets} rowKey={(d) => d.key}
              columns={[
                { key: "table", label: "Table", render: (d) => <code style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{d.table}</code> },
                { key: "label", label: "Source", hideBelow: 700, render: (d) => d.label },
                { key: "rows", label: "Rows", numeric: true, render: (d) => d.rows != null ? NUMBER(d.rows) : <span className="na">not created</span> },
              ]} />
          </Disclosure>
          <TechnicalDetails value={{
            rows_read: workspace.build?.rows_read, compact: workspace.build?.compact,
            leakage_guard: workspace.build?.leakage_guard, incumbent_rule: workspace.build?.incumbent_rule,
            warnings: workspace.build?.warnings,
          }} hint="build report" />
        </div>
      </Section>
    </>
  );
}

export default function DataPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <Suspense fallback={<Loading label="Reading what your workspace holds…" cards={2} />}>
        <DataBody />
      </Suspense>
    </Gate>
  );
}
