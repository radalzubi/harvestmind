"use client";

/**
 * DIAGNOSTICS — why is performance changing, and where is the exposure?
 *
 * Commercial diagnosis, not engineering telemetry. Four questions a distributor actually asks:
 * which suppliers are letting me down, where does lateness concentrate, what physical risk do my
 * products carry, and what is any of this worth.
 *
 * The value tab is where a product is most tempted to lie, so it is the most carefully worded page
 * in ZAAD. It reports the *modelled difference between two plans* and calls it exactly that. It is
 * not a backtest, it is not realized savings, and the page says so in its own words rather than
 * leaving a number to be misread.
 */
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Disclosure, EmptyState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { Column, DataTable, NotAvailable, Pager, SearchField, SelectField, Toolbar } from "@/components/workspace/Table";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { money } from "@/lib/zaad/decisions";
import {
  DATE, MONEY, NUMBER, PERCENT, fetchCorridors, fetchSector, fetchSuppliers,
  type SectorRow, type SupplierRow,
} from "@/lib/zaad/product";

const PAGE = 50;

function rate(value: number | null | undefined, sample: number | null | undefined, thin: number) {
  if (value == null) return <NotAvailable why="Not enough matched deliveries to measure." />;
  const tone = value >= 0.3 ? "bad" : value >= 0.1 ? "warn" : "good";
  return (
    <span className="chip" data-tone={tone} title={sample ? `${sample} matched orders` : undefined}>
      {PERCENT(value, 0)}{sample != null && sample < thin ? "*" : ""}
    </span>
  );
}

function Suppliers({ params, set }: { params: URLSearchParams; set: (c: Record<string, string | null>) => void }) {
  const { request } = useWorkspaceData();
  const q = params.get("q") ?? "";
  const sort = params.get("sort") ?? "late_rate";
  const direction = params.get("dir") ?? "desc";
  const offset = Number(params.get("offset") ?? 0);
  const [page, setPage] = useState<Awaited<ReturnType<typeof fetchSuppliers>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState(q);

  useEffect(() => { setTyped(q); }, [q]);
  useEffect(() => {
    const handle = window.setTimeout(() => { if (typed !== q) set({ q: typed || null }); }, 250);
    return () => window.clearTimeout(handle);
  }, [typed, q, set]);

  useEffect(() => {
    let alive = true;
    fetchSuppliers({ q: q || undefined, sort, direction, limit: PAGE, offset, as_of: request?.as_of?.slice(0, 10) })
      .then((p) => alive && setPage(p)).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [q, sort, direction, offset, request]);

  const columns: Column<SupplierRow>[] = useMemo(() => {
    const thin = page?.thin_sample ?? 6;
    return [
      { key: "supplier_id", label: "Supplier", sortable: true, width: 200,
        render: (r) => <Link href={`/diagnostics/supplier/${encodeURIComponent(r.supplier_id)}`} onClick={(e) => e.stopPropagation()}>
          <strong style={{ fontWeight: 500 }}>{r.name || r.supplier_id}</strong>
        </Link> },
      { key: "origin", label: "Origin", hideBelow: 1100, render: (r) => r.origin ?? <span className="na">—</span> },
      { key: "route", label: "Route", hideBelow: 900, render: (r) => r.route ?? <span className="na">—</span> },
      { key: "matched_orders", label: "Measured on", numeric: true, sortable: true, hideBelow: 1100,
        render: (r) => r.matched_orders != null ? `${NUMBER(r.matched_orders)} orders` : <span className="na">—</span> },
      { key: "late_rate", label: "Arrived late", numeric: true, sortable: true,
        render: (r) => rate(r.late_rate, r.orders_with_promise, thin) },
      { key: "mean_late_days", label: "Days late", numeric: true, sortable: true, hideBelow: 700,
        render: (r) => r.mean_late_days != null ? NUMBER(r.mean_late_days, 1) : <span className="na">—</span> },
      { key: "fill_rate", label: "Quantity arrived", numeric: true, sortable: true,
        render: (r) => r.fill_rate != null ? PERCENT(r.fill_rate) : <NotAvailable /> },
      { key: "p90_lead_days", label: "Slow lead (p90)", numeric: true, sortable: true, hideBelow: 900,
        render: (r) => r.p90_lead_days != null ? `${NUMBER(r.p90_lead_days)} d` : <span className="na">—</span> },
      { key: "open_orders", label: "Open", numeric: true, sortable: true,
        render: (r) => r.open_orders ? NUMBER(r.open_orders) : <span className="na">—</span> },
      { key: "late_open_orders", label: "Open and late", numeric: true, sortable: true, hideBelow: 700,
        render: (r) => r.late_open_orders ? <span className="chip" data-tone="warn">{NUMBER(r.late_open_orders)}</span> : <span className="na">—</span> },
    ];
  }, [page]);

  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!page) return <Loading label="Measuring your suppliers…" cards={2} />;
  if (!page.served) {
    return <EmptyState title="Nothing to measure yet"
      actions={<ButtonLink href="/upload" role="primary">Add purchase orders and receipts</ButtonLink>}>
      {page.note}
    </EmptyState>;
  }

  return (
    <>
      <Toolbar>
        <SearchField value={typed} onChange={setTyped} label="Search suppliers" placeholder="Search supplier code or name" />
      </Toolbar>
      <DataTable caption="Suppliers with what the receipt history measures" columns={columns} rows={page.rows}
        rowKey={(r) => r.supplier_id} sort={sort} direction={direction}
        onSort={(key) => set({ sort: key, dir: sort === key && direction === "desc" ? "asc" : "desc" })}
        onSelect={(r) => { window.location.href = `/diagnostics/supplier/${encodeURIComponent(r.supplier_id)}`; }}
        empty={<EmptyState title="No supplier matches that">Clear the search to see every supplier.</EmptyState>} />
      <Pager total={page.total} limit={PAGE} offset={offset} unit="suppliers"
        onOffset={(next) => set({ offset: String(next) })} />
      <p className="zhelp" style={{ marginTop: 10 }}>
        Every figure is measured from your own purchase orders matched to your own receipts. An asterisk means
        fewer than {page.thin_sample} matched orders — arithmetic, not yet evidence. &ldquo;Quantity arrived&rdquo; counts short
        deliveries below {PERCENT(page.short_fill_tolerance, 0)} of what was ordered.
      </p>
    </>
  );
}

function Corridors() {
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchCorridors>> | null>(null);
  useEffect(() => { fetchCorridors().then(setData).catch(() => setData({ served: false, rows: [], note: "" })); }, []);
  if (!data) return <Loading label="Grouping arrivals by route…" cards={1} />;
  if (!data.served) return <EmptyState title="No route is declared">{data.note}</EmptyState>;
  return (
    <>
      <DataTable caption="Arrivals grouped by declared route" rows={data.rows} rowKey={(r) => r.route}
        columns={[
          { key: "route", label: "Route", render: (r) => r.route },
          { key: "suppliers", label: "Suppliers", numeric: true, render: (r) => NUMBER(r.suppliers) },
          { key: "orders", label: "Matched orders", numeric: true, render: (r) => NUMBER(r.orders) },
          { key: "late_orders", label: "Arrived late", numeric: true, render: (r) => NUMBER(r.late_orders) },
          { key: "mean_late_days", label: "Days late", numeric: true, render: (r) => r.mean_late_days != null ? NUMBER(r.mean_late_days, 1) : <span className="na">—</span> },
          { key: "mean_lead_days", label: "Lead (days)", numeric: true, render: (r) => r.mean_lead_days != null ? NUMBER(r.mean_lead_days, 1) : <span className="na">—</span> },
        ]} />
      <div style={{ marginTop: 12 }}><Notice>{data.note}</Notice></div>
      <p className="zhelp" style={{ marginTop: 10 }}>
        ZAAD does not choose routes. Route and port optimisation is not part of the released engine, so this is a
        diagnostic over the paths your suppliers declare, not a recommendation to move to another one.
      </p>
    </>
  );
}

function Sector() {
  const [sort, setSort] = useState("supply_uncertainty");
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchSector>> | null>(null);
  useEffect(() => { fetchSector({ sort, limit: PAGE }).then(setData).catch(() => setData(null)); }, [sort]);

  if (!data) return <Loading label="Reading declared physics…" cards={1} />;
  if (!data.served) return <EmptyState title="No sector physics declared">{data.note}</EmptyState>;

  const columns: Column<SectorRow>[] = [
    { key: "sku", label: "Product", render: (r) => <Link href={`/inventory?sku=${encodeURIComponent(r.sku)}`}>{r.sku_name || r.sku}</Link> },
    { key: "sector", label: "Sector", hideBelow: 900, render: (r) => (r.sector ?? "").replaceAll("_", " ").toLowerCase() },
    { key: "storage_state", label: "Storage", hideBelow: 1100, render: (r) => (r.storage_state ?? "—").toLowerCase() },
    { key: "fill_sd", label: "Quantity variability", numeric: true,
      render: (r) => r.fill_sd != null ? PERCENT(r.fill_sd) : <NotAvailable why="Needs matched deliveries for this product." /> },
    { key: "lead_sd_days", label: "Lead variability", numeric: true,
      render: (r) => r.lead_sd_days != null ? `${NUMBER(r.lead_sd_days, 1)} d` : <NotAvailable /> },
    { key: "remaining_life_at_receipt_days", label: "Life on arrival", numeric: true, hideBelow: 700,
      render: (r) => r.remaining_life_at_receipt_days != null ? `${NUMBER(r.remaining_life_at_receipt_days)} d` : <NotAvailable why="Needs shelf life and age at receipt on the product master." /> },
    { key: "days_to_expiry", label: "Nearest expiry", numeric: true, hideBelow: 700,
      render: (r) => r.days_to_expiry != null ? `${NUMBER(r.days_to_expiry)} d` : <NotAvailable why="Needs an expiry date on the stock snapshot." /> },
    { key: "demand_cv", label: "Demand variability", numeric: true, hideBelow: 900,
      render: (r) => r.demand_cv != null ? PERCENT(r.demand_cv, 0) : <NotAvailable /> },
  ];

  return (
    <>
      <Toolbar>
        <SelectField value={sort} onChange={setSort} label="Sort by" all=""
          options={[
            { value: "supply_uncertainty", label: "Highest quantity uncertainty" },
            { value: "lead_uncertainty", label: "Highest lead-time variability" },
            { value: "remaining_life_receipt", label: "Least life on arrival" },
            { value: "days_to_expiry", label: "Closest to expiry" },
            { value: "demand_variability", label: "Most variable demand" },
          ]} />
      </Toolbar>
      <DataTable caption="Physical uncertainty per product" columns={columns} rows={data.rows} rowKey={(r) => r.sku} />
      {data.absent && (
        <div style={{ marginTop: 12 }}>
          <Notice>
            <strong>Not measured here:</strong>
            <ul style={{ margin: "6px 0 0", paddingInlineStart: 18 }}>
              {data.absent.map((a) => <li key={a}>{a}</li>)}
            </ul>
          </Notice>
        </div>
      )}
    </>
  );
}

/**
 * The value tab. Every word here is load-bearing.
 *
 * ZAAD is engineering-validated on synthetic and demo-scale states and has no real-data customer
 * validation. So this page reports the one thing it genuinely has — the difference between two
 * plans the optimizer produced over the same information — and names the two categories it is not.
 */
function Value() {
  const { summary, planPhase, scope } = useWorkspaceData();
  if (planPhase !== "ready" || !summary) {
    return <EmptyState title="No plan to price yet"
      actions={<ButtonLink href="/decisions" role="primary">Run a plan</ButtonLink>}>
      A modelled difference needs a plan. Run one and it appears here.
    </EmptyState>;
  }
  const priced = summary.costBreakdown.filter((row) => row.delta != null);
  return (
    <>
      <Section title="Modelled difference vs your current plan">
        <p style={{ margin: "0 0 14px", fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.65, maxWidth: "66ch" }}>
          What the optimizer projects for the plan it selected, against what it projects for your own declared
          ordering rule, over the same products and the same information. Both figures come from the engine&rsquo;s
          own settlement ledger.
        </p>
        <dl className="kv">
          <dt>Modelled cost difference</dt>
          <dd>{summary.valueVsCurrent == null
            ? <NotAvailable why="The selector kept your current plan and priced no alternative against it." />
            : Math.abs(summary.valueVsCurrent) < 0.005 ? "no difference"
            : `${summary.valueVsCurrent >= 0 ? "lower by " : "higher by "}${money(Math.abs(summary.valueVsCurrent), summary.currency)}`}</dd>
          <dt>Cash tied up</dt>
          <dd>{summary.workingCapitalDelta == null ? <NotAvailable />
            : Math.abs(summary.workingCapitalDelta) < 0.005 ? "no difference"
            : `${summary.workingCapitalDelta >= 0 ? "+" : "−"}${money(Math.abs(summary.workingCapitalDelta), summary.currency)}`}</dd>
          <dt>Products covered</dt>
          <dd>{scope ? `${scope.skus.length} of ${scope.total}` : "every product in the workspace"}</dd>
          <dt>As at</dt><dd>{DATE(summary.asOf)}</dd>
        </dl>
        {priced.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <DataTable caption="Where the modelled difference sits" dense rows={priced} rowKey={(r) => r.component}
              columns={[
                { key: "component", label: "", render: (r) => r.component },
                { key: "current", label: "Your current plan", numeric: true, render: (r) => r.current != null ? MONEY(r.current, summary.currency) : <span className="na">—</span> },
                { key: "recommended", label: "ZAAD's plan", numeric: true, render: (r) => r.recommended != null ? MONEY(r.recommended, summary.currency) : <span className="na">—</span> },
                { key: "delta", label: "Difference", numeric: true,
                  render: (r) => r.delta != null ? <span data-sign={r.delta > 0 ? "up" : "down"}>{r.delta > 0 ? "+" : "−"}{MONEY(Math.abs(r.delta), summary.currency)}</span> : <span className="na">—</span> },
              ]} />
          </div>
        )}
      </Section>

      <Section title="What this is not">
        <Notice>
          <ul style={{ margin: 0, paddingInlineStart: 18, lineHeight: 1.7 }}>
            <li><strong>Not realized savings.</strong> Nothing above has happened. It is what a model projects for
              two plans, one of which nobody has run.</li>
            <li><strong>Not a backtest.</strong> ZAAD has no held-out replay of your history wired into this
              product. The engine is validated against synthetic and demo-scale states in the repository&rsquo;s
              engineering evidence, which is engineering validation, not commercial proof.</li>
            <li><strong>Not a percentage.</strong> ZAAD makes no claim about a saving rate, an ROI multiple or a
              forecast accuracy, because none is established by anything it has measured on your data.</li>
          </ul>
        </Notice>
        <div style={{ marginTop: 12 }}>
          <Disclosure summary="Why ZAAD will not show a savings percentage" hint="the short version">
            <p style={{ margin: 0, fontSize: 13, color: "var(--ink-700)", lineHeight: 1.7 }}>
              A savings figure is only meaningful against a measured counterfactual: what your business would
              actually have spent. That needs your real history replayed against a policy you did not run, with
              the outcome compared to what happened. ZAAD can build that, and until it has, a number here would
              be a claim rather than a measurement. The modelled difference above is the honest version of the
              same question, and it is labelled as what it is.
            </p>
          </Disclosure>
        </div>
      </Section>
    </>
  );
}

const TABS = [
  { key: "suppliers", label: "Suppliers" },
  { key: "corridors", label: "Routes" },
  { key: "sector", label: "Product physics" },
  { key: "value", label: "Value" },
];

function DiagnosticsBody() {
  const params = useSearchParams();
  const router = useRouter();
  const tab = params.get("tab") ?? "suppliers";
  const set = useCallback((changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    router.replace(`/diagnostics?${next.toString()}`, { scroll: false });
  }, [params, router]);

  return (
    <>
      <PageHead title="Diagnostics"
        sub="Why performance is changing, measured from your own history — and separated from what cannot be measured from it." />
      <div className="tabs" role="tablist" aria-label="Diagnostics">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key}
            onClick={() => set({ tab: t.key, offset: null })}>{t.label}</button>
        ))}
      </div>
      <div role="tabpanel" style={{ marginTop: 16 }}>
        {tab === "suppliers" && <Suppliers params={params} set={set} />}
        {tab === "corridors" && <Corridors />}
        {tab === "sector" && <Sector />}
        {tab === "value" && <Value />}
      </div>
    </>
  );
}

export default function DiagnosticsPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <Suspense fallback={<Loading label="Opening diagnostics…" cards={2} />}>
        <DiagnosticsBody />
      </Suspense>
    </Gate>
  );
}
