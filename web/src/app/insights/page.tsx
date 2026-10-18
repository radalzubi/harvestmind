"use client";
/**
 * INSIGHTS — your records, aggregated on the server, and the latest completed ZAAD plan read back.
 *
 * Six tabs, one filter bar, one rule: nothing on this page starts a run. Every chart says which
 * rows it is made of ("Data & scope"), a missing number is shown as the reason it is missing, and
 * every important chart leads somewhere — a period opens to the customers and products behind it,
 * a supplier leads to its page, stock leads to Inventory, an open order to Purchase orders, a
 * ZAAD verdict to the decision. Optimizer numbers are read verbatim from the plan; the page says
 * when the workspace's data has moved since that plan finished.
 */
import { Suspense, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Gate } from "@/components/workspace/Gate";
import { ButtonLink, Loading, Notice, PageHead } from "@/components/workspace/ui";
import { Drawer, NotAvailable, SelectField } from "@/components/workspace/Table";
import { HBars, MultiLine, StackedBars } from "@/components/charts";
import { ChartCard } from "@/components/insights/ChartCard";
import { useLocale } from "@/lib/i18n";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { COUNT, DATE, MONEY, NUMBER, PERCENT, fetchDatasetValues, track } from "@/lib/zaad/product";
import {
  BUCKETS, EMPTY, FILTER_KEYS, TABS, activeFilters, fetchConnectivity, fetchDecisionInsights, fetchDemand, fetchDemandPeriod,
  fetchInventoryInsights, fetchOverview, fetchPlan, fetchService, fetchSupplierInsights, fetchSupply, fetchValue,
  filtersFromParams, linksFor, periodLabel, planSentence, reasonLabel, shown, VALUE_REGISTER_LABEL,
  type Bucket, type Connectivity, type Decisions, type Demand, type DemandPeriod, type Filters, type Inventory, type Overview,
  type PlanSummary, type Service, type Suppliers, type Supply, type Tab, type Value,
} from "@/lib/zaad/insights";

type Setter = (changes: Record<string, string | null>) => void;

function useLoad<T>(load: () => Promise<T>, deps: unknown[]): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    setData(null); setError(null);
    load().then((d) => alive && setData(d)).catch((e: Error) => alive && setError(e.message));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error };
}

function Stat({ label, value, note, href }: { label: string; value: string; note?: string | null; href?: string }) {
  const body = <><dt>{label}</dt><dd><span className="ins-num">{value}</span>{note && <small>{note}</small>}</dd></>;
  return <div>{href ? <Link href={href} style={{ color: "inherit", textDecoration: "none" }}>{body}</Link> : body}</div>;
}

function Stats({ children }: { children: ReactNode }) { return <dl className="ins-stat">{children}</dl>; }

function PlanLine({ plan }: { plan: PlanSummary | null }) {
  const { t, locale } = useLocale();
  if (!plan) return null;
  const copy = t.workspace.insights;
  const sentence = locale === "en"
    ? planSentence(plan, DATE)
    : !plan.available
      ? copy.noPlan
      : `${copy.latestPlan}: ${plan.finished_at ? DATE(plan.finished_at) : "—"}${plan.products != null ? ` · ${plan.products}` : ""}.${plan.stale ? ` ${copy.dataChanged}` : ""}`;
  return (
    <p className="ins-plan" data-stale={plan.stale ? "true" : "false"} aria-live="polite">
      <strong>{sentence}</strong>
      {plan.available && plan.job_id && <Link href="/decisions">Open Decisions</Link>}
      {!plan.available && <Link href="/home">{t.workspace.insights.runFromHome}</Link>}
    </p>
  );
}

// ── filters ───────────────────────────────────────────────────────────────────

function FilterBar({ filters, set, dates }: { filters: Filters; set: Setter; dates: boolean }) {
  const { t } = useLocale();
  const copy = t.workspace.insights;
  const [options, setOptions] = useState<Partial<Record<(typeof FILTER_KEYS)[number], string[]>>>({});
  useEffect(() => {
    let alive = true;
    const sources: Array<[(typeof FILTER_KEYS)[number], string, string]> = [
      ["category", "products", "category"], ["brand", "products", "brand"], ["customer", "customer_orders", "customer_id"],
      ["location", "inventory", "location_id"], ["supplier", "products", "supplier_id"],
    ];
    Promise.all(sources.map(([key, dataset, column]) => fetchDatasetValues(dataset, column).then((v) => [key, v] as const).catch(() => [key, []] as const)))
      .then((pairs) => { if (alive) setOptions(Object.fromEntries(pairs.map(([k, v]) => [k, (v as { values?: string[] })?.values ?? (Array.isArray(v) ? v : [])]))); });
    return () => { alive = false; };
  }, []);
  const [sku, setSku] = useState(filters.sku ?? "");
  useEffect(() => { setSku(filters.sku ?? ""); }, [filters.sku]);
  const active = activeFilters(filters);
  return (
    <div className="ins-filters" role="group" aria-label="Filters">
      <SelectField label="Period" value={filters.bucket} all="" onChange={(v) => set({ bucket: v || null })}
                   options={BUCKETS.map((b) => ({ value: b, label: copy.bucket[b] }))} />
      {dates && (
        <>
          <label className="fld-wrap"><span className="sr-only">{copy.filters.start}</span>
            <input className="fld" type="date" aria-label={copy.filters.start} value={filters.start ?? ""} onChange={(e) => set({ start: e.target.value || null })} /></label>
          <label className="fld-wrap"><span className="sr-only">{copy.filters.end}</span>
            <input className="fld" type="date" aria-label={copy.filters.end} value={filters.end ?? ""} onChange={(e) => set({ end: e.target.value || null })} /></label>
        </>
      )}
      <label className="fld-wrap"><span className="sr-only">{copy.filters.sku}</span>
        <input className="fld" placeholder={copy.filters.sku} aria-label={copy.filters.sku} value={sku} dir="ltr"
               onChange={(e) => setSku(e.target.value)} onBlur={() => set({ sku: sku.trim() || null })}
               onKeyDown={(e) => { if (e.key === "Enter") set({ sku: sku.trim() || null }); }} /></label>
      {(["category", "brand", "customer", "location", "supplier"] as const).map((key) => (
        <SelectField key={key} label={copy.filters[key]} value={filters[key] ?? ""} all={copy.filters[key]} onChange={(v) => set({ [key]: v || null })}
                     options={(options[key] ?? (filters[key] ? [filters[key] as string] : [])).map((v) => ({ value: v, label: v }))} />
      ))}
      {active.length > 0 && (
        <button type="button" className="zb zb--tertiary zb--sm" onClick={() => set(Object.fromEntries(FILTER_KEYS.map((k) => [k, null])))}>{copy.filters.clear}</button>
      )}
    </div>
  );
}

// ── tabs ──────────────────────────────────────────────────────────────────────

function OverviewTab({ filters, currency }: { filters: Filters; currency: string }) {
  const { t } = useLocale();
  const copy = t.workspace.insights;
  const { data, error } = useLoad<Overview>(() => fetchOverview(filters), [JSON.stringify(filters)]);
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Loading label="Reading your records…" cards={3} />;
  const d = data.demand; const inv = data.inventory; const sup = data.supply; const dec = data.decisions;
  const series = d.series.map((p) => ({ label: periodLabel(p.period, "week"), ordered: p.ordered, shipped: p.shipped, unfulfilled: p.unfulfilled }));
  const verbs = dec.recommended ? Object.entries({ ...dec.recommended.open_po_by_verb, ...dec.recommended.other }).filter(([, n]) => n > 0) : [];
  return (
    <>
      <PlanLine plan={data.plan} />
      <div className="ins-grid">
        <ChartCard title={`${copy.observed} — last 12 weeks`} description={copy.notDemand}
                   empty={!d.available} emptyReason={d.available ? null : "NO_DATA"} emptyWhy="No customer orders have been uploaded."
                   table={[{ key: "label", label: "Week" }, { key: "ordered", label: copy.ordered, format: (v) => NUMBER(v as number), align: "end" }, { key: "shipped", label: copy.shipped, format: (v) => shown(v as number, NUMBER, "NOT_MEASURED"), align: "end" }]}
                   rows={series} leads={[{ href: linksFor.insights("demand", filters), label: "Open Demand" }]}>
          <MultiLine data={series} series={[{ key: "ordered", name: copy.ordered }, { key: "shipped", name: copy.shipped }, { key: "unfulfilled", name: copy.unfulfilled }]} />
          {d.totals && (
            <Stats>
              <Stat label={copy.ordered} value={NUMBER(d.totals.ordered)} note={`${NUMBER(d.totals.lines)} lines · ${NUMBER(d.totals.customers)} customers`} />
              <Stat label={copy.unfulfilled} value={d.fulfilment === "MEASURED" && d.totals.shipped != null && d.totals.ordered != null ? NUMBER(d.totals.ordered - d.totals.shipped) : reasonLabel("NOT_MEASURED")} />
              {d.period_over_period && <Stat label={`${periodLabel(d.period_over_period.period, "week")} vs ${periodLabel(d.period_over_period.previous, "week")}`} value={shown(d.period_over_period.change_share, (v) => PERCENT(v, 1), "UNKNOWN")} note={`${NUMBER(d.period_over_period.ordered)} vs ${NUMBER(d.period_over_period.previous_ordered)} units`} />}
              {d.concentration && <Stat label="Largest customer" value={shown(d.concentration.top_1_share, (v) => PERCENT(v, 0), "NO_DATA")} note="share of units ordered" />}
            </Stats>
          )}
        </ChartCard>
        <ChartCard title="Inventory position" description="Units on hand at the latest snapshot, what is inbound on open orders, and the cover that implies."
                   empty={!inv.available} emptyReason="NO_DATA" emptyWhy="No inventory snapshots have been uploaded."
                   table={[{ key: "id", label: "Site" }, { key: "units", label: "Units", format: (v) => NUMBER(v as number), align: "end" }, { key: "value", label: "Value", format: (v) => shown(v as number, (x) => MONEY(x, currency), "NOT_MEASURED"), align: "end" }]}
                   rows={inv.by_site} leads={[{ href: linksFor.insights("inventory", filters), label: "Open Inventory insights" }, { href: linksFor.inventory(filters), label: "Open Inventory" }]}>
          {inv.position && (
            <Stats>
              <Stat label="On hand" value={shown(inv.position.on_hand, NUMBER, "NO_DATA")} note={inv.latest_snapshot ? `as counted ${DATE(inv.latest_snapshot)}` : null} />
              <Stat label="Inbound on open orders" value={shown(inv.position.inbound_units, NUMBER, "NO_DATA")} />
              <Stat label="Weeks of cover" value={shown(inv.position.weeks_of_cover, (v) => NUMBER(v, 1), inv.position.cover_reason)} note="on hand ÷ weekly orders, last 12 weeks" />
            </Stats>
          )}
          {inv.by_site.length > 0 && <HBars data={inv.by_site.map((r) => ({ reason: r.id, v: r.units }))} format={(v) => NUMBER(v)} height={Math.max(120, 36 * inv.by_site.length + 40)} />}
        </ChartCard>
        <ChartCard title="Open supply" description="Units still owed on open purchase orders, by supplier; an order is open until its first receipt."
                   empty={!sup.available} emptyReason="NO_DATA" emptyWhy="No purchase orders have been uploaded."
                   table={[{ key: "id", label: "Supplier" }, { key: "open_units", label: "Open units", format: (v) => NUMBER(v as number), align: "end" }, { key: "open_orders", label: "Open orders", format: (v) => NUMBER(v as number), align: "end" }]}
                   rows={sup.by_supplier} leads={[{ href: linksFor.insights("supply", filters), label: "Open Supply & suppliers" }, { href: linksFor.purchaseOrders(), label: "Open Purchase orders" }]}>
          {sup.totals && (
            <Stats>
              <Stat label="Open orders" value={NUMBER(sup.totals.open_orders)} note={`${NUMBER(sup.totals.open_units)} units`} />
              <Stat label="Past their date" value={NUMBER(sup.late_open?.orders)} note={sup.late_open?.orders_without_eta ? `${NUMBER(sup.late_open.orders_without_eta)} without a promised date (not counted as late)` : null} />
              <Stat label="Open value" value={shown(sup.totals.open_value, (v) => MONEY(v, currency), "NOT_MEASURED")} />
            </Stats>
          )}
          {sup.by_supplier.length > 0 && <HBars data={sup.by_supplier.map((r) => ({ reason: r.id, v: r.open_units }))} format={(v) => NUMBER(v)} height={Math.max(120, 36 * sup.by_supplier.length + 40)} />}
        </ChartCard>
        <ChartCard title="What ZAAD recommended, and what happened" description="Verdicts in the latest plan by verb, and the responses, proposals, external actions and outcomes recorded since."
                   empty={!data.plan.available && !(dec.proposals_by_state?.length)} emptyReason="NOT_IN_PLAN" emptyWhy={data.plan.why ?? "No completed plan exists yet."}
                   leads={[{ href: linksFor.insights("decisions", filters), label: "Open Decisions & value" }, { href: "/decisions", label: "Open Decisions" }]}>
          <Stats>
            <Stat label="Recommendations" value={NUMBER(dec.recommended?.total)} note={verbs.map(([k, n]) => `${k} ${n}`).join(" · ") || null} />
            <Stat label="Responses" value={NUMBER((dec.responses ?? []).reduce((a, r) => a + r.n, 0))} note={(dec.responses ?? []).map((r) => `${r.status.toLowerCase()} ${r.n}`).join(" · ") || null} />
            <Stat label="Proposals" value={NUMBER((dec.proposals_by_state ?? []).reduce((a, r) => a + r.n, 0))} note={(dec.proposals_by_state ?? []).map((r) => `${r.state.toLowerCase().replace(/_/g, " ")} ${r.n}`).join(" · ") || null} />
            <Stat label="Placed externally" value={NUMBER((dec.external_status ?? []).reduce((a, r) => a + r.n, 0))} note={dec.outcomes ? `${NUMBER(dec.outcomes.recorded)} outcomes recorded` : null} />
          </Stats>
        </ChartCard>
      </div>
    </>
  );
}

function DemandTab({ filters, set, plan }: { filters: Filters; set: Setter; plan: PlanSummary | null }) {
  const { t } = useLocale();
  const copy = t.workspace.insights;
  const { data, error } = useLoad<Demand>(() => fetchDemand(filters), [JSON.stringify(filters)]);
  const [period, setPeriod] = useState<string | null>(null);
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Loading label="Aggregating customer orders…" cards={2} />;
  if (!data.available) return <ChartCard title={copy.observed} description={copy.notDemand} empty emptyReason={data.reason} emptyWhy={data.why} provenance={data.provenance} leads={[{ href: "/upload", label: "Open Upload" }]} />;
  const series = data.series.map((p) => ({ label: periodLabel(p.period, filters.bucket), period: p.period, ordered: p.ordered, shipped: p.shipped, unfulfilled: p.unfulfilled, lines: p.lines, customers: p.customers }));
  const openPeriod = (label: string) => {
    const hit = series.find((p) => p.label === label);
    if (hit) { setPeriod(hit.period.slice(0, 10)); track("insights_period_opened", { tab: "demand" }); }
  };
  const topCard = (key: "customers" | "skus" | "categories" | "brands" | "locations", title: string, filterKey: (typeof FILTER_KEYS)[number]) => {
    const block = data.top?.[key];
    const rows = block?.rows ?? [];
    return (
      <ChartCard key={key} title={title} description={`Top ${rows.length || 10} by units ordered over the selected range. Click a bar to filter by it.`}
                 empty={!rows.length} emptyReason={block?.reason ?? "NO_DATA"} emptyWhy={block?.why ?? "No rows in this scope."}
                 table={[{ key: "id", label: title }, { key: "ordered", label: copy.ordered, format: (v) => NUMBER(v as number), align: "end" }, { key: "unfulfilled", label: copy.unfulfilled, format: (v) => shown(v as number, NUMBER, "NOT_MEASURED"), align: "end" }]}
                 rows={rows as unknown as Array<Record<string, unknown>>}
                 leads={key === "skus" ? [{ href: linksFor.inventory(filters), label: "See these products in Inventory" }] : key === "customers" ? [{ href: linksFor.data("customer_orders"), label: "Open the customer orders" }] : undefined}>
        <HBars data={rows.map((r) => ({ reason: String(r.id ?? "—"), v: r.ordered ?? 0 }))} format={(v) => NUMBER(v)} height={Math.max(140, 34 * rows.length + 40)} />
        <div className="ins-chips">{rows.slice(0, 10).map((r) => r.id && <button key={String(r.id)} type="button" className="chip" onClick={() => set({ [filterKey]: String(r.id) })}>{String(r.id)}</button>)}</div>
      </ChartCard>
    );
  };
  return (
    <>
      <PlanLine plan={plan} />
      <div className="ins-grid">
        <div className="ins-card" data-wide="true" style={{ padding: 0, border: 0, background: "transparent" }}>
          <ChartCard title={data.label ?? copy.observed} description={`${copy.notDemand} ${data.fulfilment_note ?? ""}`} provenance={data.provenance} rowsCount={data.totals?.lines}
                     table={[{ key: "label", label: "Period" }, { key: "ordered", label: copy.ordered, format: (v) => NUMBER(v as number), align: "end" }, { key: "shipped", label: copy.shipped, format: (v) => shown(v as number, NUMBER, "NOT_MEASURED"), align: "end" }, { key: "unfulfilled", label: copy.unfulfilled, format: (v) => shown(v as number, NUMBER, "NOT_MEASURED"), align: "end" }, { key: "lines", label: "Lines", format: (v) => NUMBER(v as number), align: "end" }]}
                     rows={series} leads={[{ href: linksFor.data("customer_orders", filters.customer ? "customer_id" : null, filters.customer), label: "Open the rows in Data" }]}
                     aside={<p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>{copy.openPeriod}: click a point on the line, or a period in the table.{data.truncated ? " The series is capped at 400 points; narrow the range or widen the period." : ""}</p>}>
            <MultiLine data={series} onPoint={openPeriod} area
                       series={[{ key: "ordered", name: copy.ordered }, ...(data.fulfilment === "MEASURED" ? [{ key: "shipped", name: copy.shipped }, { key: "unfulfilled", name: copy.unfulfilled }] : [])]} />
            {data.totals && (
              <Stats>
                <Stat label={copy.ordered} value={NUMBER(data.totals.ordered)} note={`${NUMBER(data.totals.lines)} lines · ${DATE(data.totals.first_order)} → ${DATE(data.totals.last_order)}`} />
                <Stat label={copy.shipped} value={shown(data.totals.shipped, NUMBER, "NOT_MEASURED")} note={data.totals.lines_unmeasured ? `${NUMBER(data.totals.lines_unmeasured)} lines without a shipped quantity` : null} />
                {data.period_over_period && <Stat label={`${periodLabel(data.period_over_period.period, filters.bucket)} vs ${periodLabel(data.period_over_period.previous, filters.bucket)}`} value={shown(data.period_over_period.change_share, (v) => PERCENT(v, 1), "UNKNOWN")} note={`${NUMBER(data.period_over_period.ordered)} vs ${NUMBER(data.period_over_period.previous_ordered)} units${data.partial_last_period ? " · the newest period is partial and left out" : ""}`} />}
                {data.concentration && <Stat label="Concentration" value={shown(data.concentration.top_5_share, (v) => PERCENT(v, 0), "NO_DATA")} note={`top 5 of ${NUMBER(data.concentration.customers)} customers · HHI ${shown(data.concentration.hhi, (v) => NUMBER(v, 2))}`} />}
              </Stats>
            )}
            <div className="ins-chips" aria-label="Periods">
              {series.slice(-8).map((p) => <button key={p.period} type="button" className="chip" onClick={() => openPeriod(p.label)}>{p.label}</button>)}
            </div>
          </ChartCard>
        </div>
        {topCard("customers", "Top customers", "customer")}
        {topCard("skus", "Top products", "sku")}
        {topCard("categories", "Top categories", "category")}
        {topCard("locations", "Demand by site", "location")}
      </div>
      <PeriodDrawer filters={filters} period={period} onClose={() => setPeriod(null)} />
    </>
  );
}

function PeriodDrawer({ filters, period, onClose }: { filters: Filters; period: string | null; onClose: () => void }) {
  const { data, error } = useLoad<DemandPeriod | null>(() => (period ? fetchDemandPeriod(filters, period) : Promise.resolve(null)), [period, JSON.stringify(filters)]);
  const list = (title: string, rows: Array<{ id?: string | null; sku?: string; ordered?: number | null; change?: number; previous?: number | null }>, link?: (id: string) => string) => (
    <section style={{ marginTop: 14 }}>
      <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>{title}</h4>
      {rows.length === 0 ? <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-500)" }}>None in this period.</p> : (
        <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13 }}>
          {rows.slice(0, 8).map((r) => {
            const id = String(r.id ?? r.sku ?? "—");
            return <li key={id}>{link ? <Link href={link(id)}>{id}</Link> : id} — <span className="ins-num">{r.change != null ? `${r.change > 0 ? "+" : ""}${NUMBER(r.change)} (${shown(r.previous, NUMBER, "NO_DATA")} → ${shown(r.ordered, NUMBER, "NO_DATA")})` : NUMBER(r.ordered)}</span></li>;
          })}
        </ul>
      )}
    </section>
  );
  return (
    <Drawer open={period != null} title={period ? `Period ${periodLabel(period, filters.bucket)}` : ""} sub="Who and what drove it, what sits behind it, and what ZAAD says" onClose={onClose} wide>
      {error && <Notice tone="warn">{error}</Notice>}
      {period && !data && !error && <Loading label="Opening the period…" cards={1} />}
      {data && (
        <div className="ins-drill">
          {list("Top products", data.top_skus, (id) => linksFor.inventory(filters, id))}
          {list("Top customers", data.top_customers, (id) => linksFor.data("customer_orders", "customer_id", id))}
          {data.top_locations.length > 0 && list("By site", data.top_locations, (id) => linksFor.inventory({ ...filters, location: id }))}
          {list("Largest increases vs the period before", data.largest_increases, (id) => linksFor.inventory(filters, id))}
          {list("Largest declines vs the period before", data.largest_declines, (id) => linksFor.inventory(filters, id))}
          <section style={{ marginTop: 14 }}>
            <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Affected inventory (now)</h4>
            {data.affected_inventory.length === 0 ? <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-500)" }}>No stock rows for these products.</p> : (
              <table className="tbl ins-table"><thead><tr><th scope="col">Product</th><th scope="col" data-align="end">On hand</th><th scope="col" data-align="end">Weeks of cover</th></tr></thead>
                <tbody>{data.affected_inventory.map((r) => <tr key={r.sku}><td><Link href={linksFor.inventory(filters, r.sku)}>{r.sku}</Link></td><td data-align="end">{NUMBER(r.on_hand)}</td><td data-align="end">{shown(r.weeks_of_cover, (v) => NUMBER(v, 1), "NOT_MEASURED")}</td></tr>)}</tbody></table>
            )}
          </section>
          <section style={{ marginTop: 14 }}>
            <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Open purchase orders on these products</h4>
            {data.open_purchase_orders.length === 0 ? <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-500)" }}>None open.</p> : (
              <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13 }}>
                {data.open_purchase_orders.map((po) => <li key={po.po_id}><Link href={linksFor.purchaseOrders(po.po_id)}>{po.po_id}</Link> · {po.sku} · {po.supplier_id} · <span className="ins-num">{NUMBER(po.open_units)}</span> units · {po.eta ? `expected ${DATE(po.eta)}` : "no promised date"}</li>)}
              </ul>
            )}
          </section>
          <section style={{ marginTop: 14 }}>
            <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Related ZAAD decisions</h4>
            {data.related_decisions.length === 0 ? <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-500)" }}>{data.provenance.plan ? "The latest plan carries no decision on these products." : "No completed plan yet, so nothing is claimed."}</p> : (
              <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13 }}>
                {data.related_decisions.map((d) => <li key={d.id}><Link href={linksFor.decision(d.id)}>{d.verb} {d.target}</Link>{d.sku ? ` · ${d.sku}` : ""}{d.quantity != null ? ` · ${NUMBER(d.quantity)} units` : ""}</li>)}
              </ul>
            )}
          </section>
          <p className="ins-leads" style={{ marginTop: 16 }}>
            <Link className="zb zb--secondary zb--sm" href={linksFor.data("customer_orders")}>Open the rows in Data</Link>
            <Link className="zb zb--secondary zb--sm" href="/decisions">Open Decisions</Link>
          </p>
        </div>
      )}
    </Drawer>
  );
}

function InventoryTab({ filters, plan, currency }: { filters: Filters; plan: PlanSummary | null; currency: string }) {
  const { data, error } = useLoad<Inventory>(() => fetchInventoryInsights(filters), [JSON.stringify(filters)]);
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Loading label="Reading the snapshots…" cards={2} />;
  if (!data.available) return <ChartCard title="Inventory over time" description="From the uploaded snapshots." empty emptyReason={data.reason} emptyWhy={data.why} provenance={data.provenance} leads={[{ href: "/upload", label: "Open Upload" }]} />;
  const series = data.series.map((p) => ({ label: periodLabel(p.period, filters.bucket), units: p.units, value: p.value, in_transit: p.in_transit }));
  const sites = Array.from(new Set(data.by_site_series.map((r) => r.location_id)));
  const bySite = Object.values(data.by_site_series.reduce<Record<string, { label: string; [k: string]: number | string | null }>>((acc, r) => {
    const key = periodLabel(r.period, filters.bucket);
    acc[key] = acc[key] ?? { label: key };
    acc[key][r.location_id] = r.units;
    return acc;
  }, {}));
  const pos = data.position;
  return (
    <>
      <PlanLine plan={plan} />
      <div className="ins-grid">
        <ChartCard title="Units on hand over time" description="The last snapshot in each period, summed over products and sites. Historical snapshots as uploaded; nothing reconstructed." provenance={data.provenance} rowsCount={data.series.length}
                   table={[{ key: "label", label: "Period" }, { key: "units", label: "Units", format: (v) => NUMBER(v as number), align: "end" }, { key: "value", label: "Value", format: (v) => shown(v as number, (x) => MONEY(x, currency), "NOT_MEASURED"), align: "end" }]}
                   rows={series} leads={[{ href: linksFor.inventory(filters), label: "Open Inventory" }]}>
          <MultiLine data={series} series={[{ key: "units", name: "Units on hand" }]} area />
        </ChartCard>
        <ChartCard title="Inventory value over time" description="Units × unit cost from the SKU master, at each period's last snapshot. Rows without a cost are counted, not priced." provenance={data.provenance}
                   empty={series.every((p) => p.value == null)} emptyReason="NOT_MEASURED" emptyWhy="No unit cost is declared for these products, so value is not measured."
                   table={[{ key: "label", label: "Period" }, { key: "value", label: "Value", format: (v) => shown(v as number, (x) => MONEY(x, currency), "NOT_MEASURED"), align: "end" }]} rows={series}
                   leads={[{ href: "/inventory?sort=inventory_value&dir=desc", label: "Inventory by value" }]}>
          <MultiLine data={series} series={[{ key: "value", name: "Value" }]} yFormat={(v) => MONEY(v, currency)} area />
        </ChartCard>
        <ChartCard title="Inventory by site" description="Units at each site, period by period. Site figures are each site's own rows; they sum to the total." provenance={data.provenance}
                   empty={sites.length === 0} emptyReason="BLOCKED_BY_DATA" emptyWhy="Snapshots carry no site."
                   table={[{ key: "label", label: "Period" }, ...sites.map((s) => ({ key: s, label: s, format: (v: unknown) => NUMBER(v as number), align: "end" as const }))]} rows={bySite}
                   leads={data.by_site.map((s) => ({ href: linksFor.inventory({ ...filters, location: s.id }), label: `Inventory at ${s.id}` }))}>
          <StackedBars data={bySite} series={sites.map((s) => ({ key: s, name: s }))} />
        </ChartCard>
        <ChartCard title="Latest position" description={pos.cover_basis} provenance={data.provenance}
                   table={[{ key: "id", label: "Category" }, { key: "units", label: "Units", format: (v) => NUMBER(v as number), align: "end" }, { key: "value", label: "Value", format: (v) => shown(v as number, (x) => MONEY(x, currency), "NOT_MEASURED"), align: "end" }, { key: "products", label: "Products", format: (v) => NUMBER(v as number), align: "end" }]}
                   rows={data.by_category} leads={[{ href: linksFor.purchaseOrders(), label: "Open purchase orders" }, { href: "/inventory?cover=low", label: "Products with low cover" }]}>
          <Stats>
            <Stat label="On hand" value={shown(pos.on_hand, NUMBER, "NO_DATA")} note={data.latest_snapshot ? `as counted ${DATE(data.latest_snapshot)}` : null} />
            <Stat label="Inbound on open orders" value={shown(pos.inbound_units, NUMBER, "NO_DATA")} />
            <Stat label="Weekly orders (12 wk)" value={shown(pos.weekly_demand, (v) => NUMBER(v), "NOT_MEASURED")} note={pos.products_without_demand ? `${NUMBER(pos.products_without_demand)} products with no recent orders` : null} />
            <Stat label="Weeks of cover" value={shown(pos.weeks_of_cover, (v) => NUMBER(v, 1), pos.cover_reason)} />
          </Stats>
          <HBars data={data.by_category.map((r) => ({ reason: String(r.id ?? "uncategorised"), v: r.units }))} format={(v) => NUMBER(v)} height={Math.max(120, 34 * data.by_category.length + 40)} />
        </ChartCard>
      </div>
    </>
  );
}

function SupplyTab({ filters, set, plan, currency }: { filters: Filters; set: Setter; plan: PlanSummary | null; currency: string }) {
  const sup = useLoad<Supply>(() => fetchSupply(filters), [JSON.stringify(filters)]);
  const sups = useLoad<Suppliers>(() => fetchSupplierInsights(filters), [JSON.stringify(filters)]);
  if (sup.error || sups.error) return <Notice tone="warn">{sup.error ?? sups.error}</Notice>;
  if (!sup.data || !sups.data) return <Loading label="Reading purchase orders and receipts…" cards={2} />;
  const s = sup.data; const r = sups.data;
  const eta = [...s.open_by_expected_arrival.map((p) => ({ label: periodLabel(p.period, filters.bucket), units: p.units, orders: p.orders })),
               ...(s.open_without_expected_date.units ? [{ label: "no promised date", units: s.open_without_expected_date.units, orders: s.open_without_expected_date.orders }] : [])];
  const received = s.received.map((p) => ({ label: periodLabel(p.period, filters.bucket), units: p.units, orders: p.orders }));
  const focus = filters.supplier ? r.trend.filter((t) => t.supplier_id === filters.supplier) : [];
  const trend = focus.map((t) => ({ label: periodLabel(t.period, "month"), fill_rate: t.fill_rate, late_rate: t.late_rate, p50_lead_days: t.p50_lead_days, matched: t.matched_orders, promised: t.orders_with_promise }));
  const ratio = (x: { value: number | null; numerator?: number | null; denominator?: number | null; thin?: boolean; reason?: string }, digits = 0) =>
    x.value == null ? <NotAvailable why={x.reason === "NOT_MEASURED" ? "No promised date on any matched order." : "Not measured."} />
      : <span className="chip" title={x.denominator != null ? `${NUMBER(x.numerator)} of ${NUMBER(x.denominator)}` : undefined}>{PERCENT(x.value, digits)}{x.thin ? "*" : ""}</span>;
  return (
    <>
      <PlanLine plan={plan} />
      {!s.available && <ChartCard title="Supply" description="" empty emptyReason={s.reason} emptyWhy={s.why} leads={[{ href: "/upload", label: "Open Upload" }]} />}
      {s.available && (
        <div className="ins-grid">
          <ChartCard title="Open orders by expected arrival" description="Units still owed on open orders, by the period they are promised for. Orders without a promised date are shown apart, never dated." provenance={s.provenance}
                     table={[{ key: "label", label: "Expected" }, { key: "units", label: "Units", format: (v) => NUMBER(v as number), align: "end" }, { key: "orders", label: "Orders", format: (v) => NUMBER(v as number), align: "end" }]} rows={eta}
                     leads={[{ href: linksFor.purchaseOrders(), label: "Open purchase orders" }]}>
            <StackedBars data={eta} series={[{ key: "units", name: "Open units" }]} />
            <Stats>
              <Stat label="Open orders" value={NUMBER(s.totals.open_orders)} note={`${NUMBER(s.totals.open_units)} units`} />
              <Stat label="Past their date" value={NUMBER(s.late_open.orders)} note={`${NUMBER(s.late_open.orders_without_eta)} without a promised date (not counted)`} />
              <Stat label="Open value" value={shown(s.totals.open_value, (v) => MONEY(v, currency), "NOT_MEASURED")} note={s.totals.open_lines_without_cost ? `${NUMBER(s.totals.open_lines_without_cost)} lines without a cost` : null} />
            </Stats>
          </ChartCard>
          <ChartCard title="Received per period" description="Units received against purchase orders, by receipt date." provenance={s.provenance} empty={received.length === 0} emptyReason="NO_DATA" emptyWhy="No receipts in this scope."
                     table={[{ key: "label", label: "Period" }, { key: "units", label: "Units", format: (v) => NUMBER(v as number), align: "end" }, { key: "orders", label: "Orders", format: (v) => NUMBER(v as number), align: "end" }]} rows={received}
                     leads={[{ href: linksFor.data("receipts"), label: "Open the receipts in Data" }]}>
            <MultiLine data={received} series={[{ key: "units", name: "Received" }]} area />
          </ChartCard>
          <ChartCard title="Open order aging" description="How long open orders have been open, from their order date to the selected end date." provenance={s.provenance}
                     table={[{ key: "age", label: "Age" }, { key: "units", label: "Units", format: (v) => NUMBER(v as number), align: "end" }, { key: "orders", label: "Orders", format: (v) => NUMBER(v as number), align: "end" }]} rows={s.aging}
                     leads={[{ href: linksFor.purchaseOrders(), label: "Open purchase orders" }]}>
            <HBars data={s.aging.map((a) => ({ reason: a.age, v: a.units }))} format={(v) => NUMBER(v)} height={160} />
          </ChartCard>
          <ChartCard title="Open supply by supplier and by destination" description="Where open units come from and where they are going. Click a supplier to filter the page." provenance={s.provenance}
                     table={[{ key: "id", label: "Supplier" }, { key: "open_units", label: "Open units", format: (v) => NUMBER(v as number), align: "end" }, { key: "open_orders", label: "Open orders", format: (v) => NUMBER(v as number), align: "end" }, { key: "open_value", label: "Open value", format: (v) => shown(v as number, (x) => MONEY(x, currency), "NOT_MEASURED"), align: "end" }]} rows={s.by_supplier}
                     leads={s.by_supplier.slice(0, 3).map((x) => ({ href: linksFor.supplier(x.id), label: `Supplier page: ${x.id}` }))}>
            <HBars data={s.by_supplier.map((x) => ({ reason: x.id, v: x.open_units }))} format={(v) => NUMBER(v)} height={Math.max(120, 34 * s.by_supplier.length + 40)} />
            <div className="ins-chips">{s.by_supplier.map((x) => <button key={x.id} type="button" className="chip" onClick={() => set({ supplier: x.id })}>{x.id}</button>)}</div>
            {Array.isArray(s.by_destination) ? (
              <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-700)" }}>By destination: {s.by_destination.map((d) => `${d.id} ${NUMBER(d.open_units)}`).join(" · ") || "none"}</p>
            ) : <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>By destination: {reasonLabel(s.by_destination.reason)} — {s.by_destination.why}</p>}
          </ChartCard>
        </div>
      )}
      <div className="ins-grid">
        <div className="ins-card" data-wide="true" style={{ padding: 0, border: 0, background: "transparent" }}>
          <ChartCard title="Suppliers" description={`Fill = units received ÷ units ordered on matched orders. Lateness = orders after their promised date ÷ orders that carry one — an order without a promised date is never counted on time. * fewer than ${r.thin_sample} orders.`}
                     provenance={r.provenance} empty={!r.available || r.suppliers.length === 0} emptyReason={r.reason ?? "NO_DATA"} emptyWhy={r.why ?? "No matched orders in this scope."}
                     leads={[{ href: "/diagnostics?tab=suppliers", label: "Open Diagnostics" }]}>
            <div className="tbl-wrap" style={{ overflowX: "auto" }}>
              <table className="tbl ins-table">
                <thead><tr>
                  <th scope="col">Supplier</th><th scope="col" data-align="end">Matched orders</th><th scope="col" data-align="end">Fill</th><th scope="col" data-align="end">Short fills</th>
                  <th scope="col" data-align="end">Lead p50 / p90 (days)</th><th scope="col" data-align="end">Late</th><th scope="col" data-align="end">Promised dates</th>
                  <th scope="col" data-align="end">Share of units</th><th scope="col" data-align="end">Open exposure</th><th scope="col" data-align="end">Rights</th><th scope="col" data-align="end">Alternatives</th>
                </tr></thead>
                <tbody>
                  {r.suppliers.map((x) => (
                    <tr key={x.supplier_id}>
                      <td><Link href={linksFor.supplier(x.supplier_id)}>{x.supplier_id}</Link> · <button type="button" className="chip" onClick={() => set({ supplier: x.supplier_id })}>trend</button></td>
                      <td data-align="end">{NUMBER(x.matched_orders)}</td>
                      <td data-align="end">{ratio(x.fill, 1)}</td>
                      <td data-align="end">{NUMBER(x.short_fills)}</td>
                      <td data-align="end">{shown(x.p50_lead_days, (v) => NUMBER(v))} / {shown(x.p90_lead_days, (v) => NUMBER(v))}</td>
                      <td data-align="end">{ratio(x.lateness)}</td>
                      <td data-align="end">{NUMBER(x.orders_with_promise)} of {NUMBER(x.matched_orders)}</td>
                      <td data-align="end">{shown(x.share_of_units_ordered, (v) => PERCENT(v, 0), "NO_DATA")}</td>
                      <td data-align="end"><Link href={linksFor.purchaseOrders(null, x.supplier_id)}>{NUMBER(x.exposure.open_units)} units</Link></td>
                      <td data-align="end">{NUMBER(x.amendment_rights_on_open_orders)}</td>
                      <td data-align="end">{NUMBER(x.products_with_declared_alternative)} products{x.alternative_for_products ? ` · alt. for ${NUMBER(x.alternative_for_products)}` : ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {r.sourcing && <p style={{ margin: "8px 0 0", fontSize: 12.5, color: "var(--ink-700)" }}>{r.sourcing.note} <Link href="/decisions">Open Decisions</Link></p>}
          </ChartCard>
        </div>
        {filters.supplier && (
          <div className="ins-card" data-wide="true" style={{ padding: 0, border: 0, background: "transparent" }}>
            <ChartCard title={`${filters.supplier} — month by month`} description="Fill rate and lateness per month with the orders behind each point; a month without promised dates has no lateness point, not a zero." provenance={r.provenance}
                       empty={trend.length === 0} emptyReason="NO_DATA" emptyWhy="No matched orders for this supplier in the range."
                       table={[{ key: "label", label: "Month" }, { key: "matched", label: "Matched", format: (v) => NUMBER(v as number), align: "end" }, { key: "fill_rate", label: "Fill", format: (v) => shown(v as number, (x) => PERCENT(x, 1), "NOT_MEASURED"), align: "end" }, { key: "late_rate", label: "Late", format: (v) => shown(v as number, (x) => PERCENT(x, 0), "NOT_MEASURED"), align: "end" }, { key: "promised", label: "With promised date", format: (v) => NUMBER(v as number), align: "end" }, { key: "p50_lead_days", label: "Lead p50", format: (v) => shown(v as number, (x) => NUMBER(x), "NOT_MEASURED"), align: "end" }]}
                       rows={trend} leads={[{ href: linksFor.supplier(filters.supplier), label: "Supplier page" }, { href: linksFor.purchaseOrders(null, filters.supplier), label: "Open orders with this supplier" }]}>
              <MultiLine data={trend} series={[{ key: "fill_rate", name: "Fill rate" }, { key: "late_rate", name: "Late rate" }]} yFormat={(v) => PERCENT(v, 0)} />
              <MultiLine data={trend} series={[{ key: "p50_lead_days", name: "Lead p50 (days)" }]} height={180} />
            </ChartCard>
          </div>
        )}
      </div>
    </>
  );
}

function ServiceTab({ filters, set, plan }: { filters: Filters; set: Setter; plan: PlanSummary | null }) {
  const { data, error } = useLoad<Service>(() => fetchService(filters), [JSON.stringify(filters)]);
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Loading label="Reading customer orders…" cards={2} />;
  if (!data.available) return <ChartCard title="Service" description="" empty emptyReason={data.reason} emptyWhy={data.why} leads={[{ href: "/upload", label: "Open Upload" }]} />;
  const series = data.series.map((p) => ({ label: periodLabel(p.period, filters.bucket), ordered: p.ordered, shipped: p.shipped, unfulfilled: p.unfulfilled, service_level: p.service_level }));
  return (
    <>
      <PlanLine plan={plan} />
      <div className="ins-grid">
        <ChartCard title="Ordered, shipped, unfulfilled" description={data.fulfilment === "MEASURED" ? "Per period, on lines that record a shipped quantity. Unfulfilled is the recorded shortfall; nothing is inferred about lost demand." : "The upload carries no shipped quantity, so fulfilment is not measured."} provenance={data.provenance}
                   table={[{ key: "label", label: "Period" }, { key: "ordered", label: "Ordered", format: (v) => NUMBER(v as number), align: "end" }, { key: "shipped", label: "Shipped", format: (v) => shown(v as number, NUMBER, "NOT_MEASURED"), align: "end" }, { key: "unfulfilled", label: "Unfulfilled", format: (v) => shown(v as number, NUMBER, "NOT_MEASURED"), align: "end" }, { key: "service_level", label: "Service level", format: (v) => shown(v as number, (x) => PERCENT(x, 1), "NOT_MEASURED"), align: "end" }]}
                   rows={series} leads={[{ href: linksFor.data("customer_orders"), label: "Open the customer orders" }]}>
          <StackedBars data={series} series={data.fulfilment === "MEASURED" ? [{ key: "shipped", name: "Shipped" }, { key: "unfulfilled", name: "Unfulfilled" }] : [{ key: "ordered", name: "Ordered" }]} />
        </ChartCard>
        <ChartCard title="Service level per period" description="Units shipped ÷ units ordered on measured lines." provenance={data.provenance} empty={data.fulfilment !== "MEASURED"} emptyReason="NOT_MEASURED" emptyWhy="No shipped quantities are recorded."
                   table={[{ key: "label", label: "Period" }, { key: "service_level", label: "Service level", format: (v) => shown(v as number, (x) => PERCENT(x, 1), "NOT_MEASURED"), align: "end" }]} rows={series}>
          <MultiLine data={series} series={[{ key: "service_level", name: "Service level" }]} yFormat={(v) => PERCENT(v, 0)} />
        </ChartCard>
        <div className="ins-card" data-wide="true" style={{ padding: 0, border: 0, background: "transparent" }}>
          <ChartCard title="By customer" description="Ordered, shipped and unfulfilled per customer, the service level with its denominator, and the declared service class where one exists. ZAAD does not score customers." provenance={data.provenance}
                     leads={[{ href: linksFor.data("customer_orders"), label: "Open the customer orders" }]}>
            <div className="tbl-wrap" style={{ overflowX: "auto" }}>
              <table className="tbl ins-table">
                <thead><tr><th scope="col">Customer</th><th scope="col">Class</th><th scope="col" data-align="end">Ordered</th><th scope="col" data-align="end">Shipped</th><th scope="col" data-align="end">Unfulfilled</th><th scope="col" data-align="end">Short lines</th><th scope="col" data-align="end">Service level</th></tr></thead>
                <tbody>
                  {data.by_customer.map((c) => (
                    <tr key={c.id}>
                      <td><button type="button" className="chip" onClick={() => set({ customer: c.id })}>{c.id}</button></td>
                      <td>{c.service_class ?? <NotAvailable why="No service class is declared for this customer." />}</td>
                      <td data-align="end">{NUMBER(c.ordered)}</td>
                      <td data-align="end">{shown(c.shipped, NUMBER, "NOT_MEASURED")}</td>
                      <td data-align="end">{shown(c.unfulfilled, NUMBER, "NOT_MEASURED")}</td>
                      <td data-align="end">{shown(c.lines_short, NUMBER, "NOT_MEASURED")}</td>
                      <td data-align="end">{c.service_level.value == null ? <NotAvailable why={c.service_level.why} /> : <span className="chip" title={`${NUMBER(c.service_level.numerator)} of ${NUMBER(c.service_level.denominator)} units`}>{PERCENT(c.service_level.value, 1)}</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </div>
        <ChartCard title="By declared service class" description="Customers grouped by the class declared for them (P5 declarations); customers without one are shown as not declared." provenance={data.provenance}
                   empty={data.by_service_class.length === 0} emptyReason="NO_DATA" emptyWhy="No customers in scope."
                   table={[{ key: "id", label: "Class" }, { key: "customers", label: "Customers", format: (v) => NUMBER(v as number), align: "end" }, { key: "ordered", label: "Ordered", format: (v) => NUMBER(v as number), align: "end" }, { key: "service_level", label: "Service level", format: (v) => shown(v as number, (x) => PERCENT(x, 1), "NOT_MEASURED"), align: "end" }]}
                   rows={data.by_service_class}>
          <HBars data={data.by_service_class.map((c) => ({ reason: c.id, v: c.ordered }))} format={(v) => NUMBER(v)} height={Math.max(120, 34 * data.by_service_class.length + 40)} />
          {data.declared_service_classes.length > 0 && <p style={{ margin: "6px 0 0", fontSize: 12.5, color: "var(--ink-700)" }}>Declared floors: {data.declared_service_classes.map((c) => `${c.class_id} ${shown(c.contractual_service_floor, (v) => PERCENT(v, 0), "UNKNOWN")}`).join(" · ")}</p>}
        </ChartCard>
        <ChartCard title="Customer allocation (ATP)" description="The latest plan's allocation block, read as written." provenance={data.provenance}
                   empty={!data.atp.present} emptyReason={data.atp.reason} emptyWhy={data.atp.why} leads={[{ href: "/decisions", label: "Open Decisions" }]}>
          {data.atp.present && (
            <>
              <p style={{ margin: 0, fontSize: 12.5, color: "var(--ink-700)" }}>{data.atp.note}</p>
              <dl className="kv" style={{ marginTop: 8 }}>{Object.entries(data.atp.summary ?? {}).map(([k, v]) => <div key={k}><dt>{k.replace(/_/g, " ")}</dt><dd>{String(v ?? "—")}</dd></div>)}</dl>
              <p style={{ margin: "8px 0 0", fontSize: 12.5 }}>{COUNT(data.atp.orders?.length ?? 0, "allocated order", "allocated orders")} in the block.</p>
            </>
          )}
        </ChartCard>
      </div>
      <p style={{ margin: "12px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>{data.risk_scores.why}</p>
    </>
  );
}

function DecisionsTab({ currency }: { currency: string }) {
  const dec = useLoad<Decisions>(() => fetchDecisionInsights(), []);
  const val = useLoad<Value>(() => fetchValue(), []);
  const con = useLoad<Connectivity>(() => fetchConnectivity(), []);
  if (dec.error || val.error || con.error) return <Notice tone="warn">{dec.error ?? val.error ?? con.error}</Notice>;
  if (!dec.data || !val.data || !con.data) return <Loading label="Reading the latest plan…" cards={3} />;
  const d = dec.data; const v = val.data; const c = con.data;
  const verbs = [...Object.entries(d.recommended.open_po_by_verb), ...Object.entries(d.recommended.other)].map(([k, n]) => ({ reason: k, v: n }));
  const money = (x: unknown) => shown(x as number, (n) => MONEY(n, v.currency ?? currency), "NOT_IN_PLAN");
  const register = (key: string) => {
    const r = v.registers[key];
    const label = VALUE_REGISTER_LABEL[key] ?? key;
    if (!r) return null;
    if (!r.available) return <ChartCard key={key} title={label} description={String(r.basis ?? "")} empty emptyReason={r.reason} emptyWhy={r.why} />;
    if (key === "MODELED_DIFFERENCE") {
      const ledger = (r.ledger as Array<{ component: string; incumbent: number | null; selected: number | null }>) ?? [];
      return (
        <ChartCard key={key} title={label} description={String(r.basis)} table={[{ key: "component", label: "Component" }, { key: "incumbent", label: "Decision reference", format: money, align: "end" }, { key: "selected", label: "Recommended", format: money, align: "end" }]} rows={ledger}
                   leads={[{ href: "/decisions", label: "Open Decisions" }]}>
          <Stats>
            <Stat label="Decision reference (modelled)" value={money(r.incumbent_total)} />
            <Stat label="Recommended (modelled)" value={money(r.selected_total)} />
            <Stat label="Modelled difference" value={money(r.difference)} note="a modelled difference, not a saving" />
          </Stats>
        </ChartCard>
      );
    }
    if (key === "APPROVED_EXPECTED_DIFFERENCE") {
      const rows = (r.proposals as Array<{ draft_id: string; reference: string | null; state?: string; available: boolean; proposal_vs_current: number | null; contract_net_difference: number | null; reason?: string; why?: string }>) ?? [];
      return (
        <ChartCard key={key} title={label} description={String(r.basis)} leads={[{ href: "/orders?state=APPROVED", label: "Approved proposals" }]}>
          <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13 }}>
            {rows.map((p) => <li key={p.draft_id}><Link href={`/orders/${encodeURIComponent(p.draft_id)}`}>{p.reference ?? p.draft_id}</Link> — {p.available ? <>proposal vs current <span className="ins-num">{money(p.proposal_vs_current)}</span>{p.contract_net_difference != null ? ` · net of contract terms ${money(p.contract_net_difference)}` : ""}</> : `${reasonLabel(p.reason)}: ${p.why}`}</li>)}
          </ul>
        </ChartCard>
      );
    }
    if (key === "OBSERVED_AFTER_ACTION") {
      const rows = (r.by_metric as Array<{ metric: string; unit: string | null; n: number; total: number | null }>) ?? [];
      return (
        <ChartCard key={key} title={label} description={String(r.basis)} table={[{ key: "metric", label: "Metric" }, { key: "n", label: "Outcomes", format: (x) => NUMBER(x as number), align: "end" }, { key: "total", label: "Total", format: (x) => shown(x as number, (n) => NUMBER(n), "NOT_MEASURED"), align: "end" }, { key: "unit", label: "Unit" }]} rows={rows}
                   leads={[{ href: "/history", label: "Open History" }]}>
          <HBars data={rows.map((m) => ({ reason: m.metric, v: m.n }))} format={(x) => NUMBER(x)} height={Math.max(100, 34 * rows.length + 40)} />
        </ChartCard>
      );
    }
    const rows = (r.rows as Array<{ draft_id: string; metric: string; unit: string | null; value: number | null; comparator_value: number | null; comparator_basis: string | null; difference: number | null; observed_at: string | null }>) ?? [];
    return (
      <ChartCard key={key} title={label} description={String(r.basis)} table={[{ key: "draft_id", label: "Proposal" }, { key: "metric", label: "Metric" }, { key: "value", label: "Observed", format: (x) => shown(x as number, (n) => NUMBER(n), "NOT_MEASURED"), align: "end" }, { key: "comparator_value", label: "Comparator", format: (x) => shown(x as number, (n) => NUMBER(n), "UNKNOWN"), align: "end" }, { key: "difference", label: "Difference", format: (x) => shown(x as number, (n) => NUMBER(n), "UNKNOWN"), align: "end" }, { key: "comparator_basis", label: "Basis" }]} rows={rows}
                 leads={[{ href: "/history", label: "Open History" }]}>
        <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13 }}>
          {rows.slice(0, 6).map((x, i) => <li key={i}><Link href={`/orders/${encodeURIComponent(x.draft_id)}`}>{x.draft_id}</Link> · {x.metric}: observed <span className="ins-num">{shown(x.value, (n) => NUMBER(n), "NOT_MEASURED")}</span> vs comparator <span className="ins-num">{shown(x.comparator_value, (n) => NUMBER(n), "UNKNOWN")}</span> ({x.comparator_basis})</li>)}
        </ul>
      </ChartCard>
    );
  };
  const statusTone = (s: string) => (s === "VISUALIZED" ? "good" : s === "NOT_IN_PLAN" || s === "IN_PLAN_NOT_VISUALIZED" ? "warn" : undefined);
  return (
    <>
      <PlanLine plan={d.plan} />
      <div className="ins-grid">
        <ChartCard title="ZAAD recommendations by action" description="Verdicts on open orders (KEEP · DEFER · EXPEDITE · REDUCE · CANCEL · SPLIT) and the purchases and moves in the latest plan, read verbatim." provenance={d.provenance}
                   empty={!d.plan.available} emptyReason="NOT_IN_PLAN" emptyWhy={d.plan.why}
                   table={[{ key: "reason", label: "Action" }, { key: "v", label: "Count", format: (x) => NUMBER(x as number), align: "end" }]} rows={verbs} leads={[{ href: "/decisions", label: "Open Decisions" }]}>
          <HBars data={verbs} format={(x) => NUMBER(x)} height={Math.max(160, 30 * verbs.length + 40)} />
          {d.decisions.length > 0 && (
            <ul style={{ margin: "8px 0 0", paddingInlineStart: 18, fontSize: 13 }}>
              {d.decisions.slice(0, 8).map((x) => <li key={x.id}><Link href={linksFor.decision(x.id)}>{x.verb} {x.target}</Link>{x.sku ? ` · ${x.sku}` : ""}{x.quantity != null ? ` · ${NUMBER(x.quantity)} units` : ""}</li>)}
            </ul>
          )}
        </ChartCard>
        <ChartCard title="Recommended, approved, rejected, overridden, executed, outcome" description="Each column is a count of rows of its own kind; they are not stages of one funnel." provenance={d.provenance}
                   leads={[{ href: "/history", label: "Open History" }, { href: "/orders", label: "Open proposals" }]}>
          <Stats>
            <Stat label="Recommended" value={NUMBER(d.recommended.total)} note={d.registers.recommended} href="/decisions" />
            <Stat label="Approved" value={NUMBER(d.proposals_by_state.filter((s) => s.state === "APPROVED" || s.state === "EXPORTED").reduce((a, s) => a + s.n, 0))} note={d.registers.approved} href="/orders?state=APPROVED" />
            <Stat label="Rejected" value={NUMBER(d.proposals_by_state.filter((s) => s.state === "REJECTED").reduce((a, s) => a + s.n, 0) + d.responses.filter((s) => s.status === "REJECTED").reduce((a, s) => a + s.n, 0))} note={d.registers.rejected} href="/history" />
            <Stat label="Overridden" value={NUMBER(d.responses.filter((s) => s.status === "OVERRIDDEN").reduce((a, s) => a + s.n, 0))} note={d.registers.overridden} href="/history" />
            <Stat label="Externally executed" value={NUMBER(d.external_status.reduce((a, s) => a + s.n, 0))} note={d.external_status.map((s) => `${s.external_status.toLowerCase().replace(/_/g, " ")} ${s.n}`).join(" · ") || d.registers.externally_executed} href="/orders?external_status=PLACED_EXTERNALLY" />
            <Stat label="Outcome available" value={NUMBER(d.outcomes.drafts_with_outcomes)} note={`${NUMBER(d.outcomes.recorded)} outcomes · ${NUMBER(d.outcomes.with_comparator)} with a comparator`} href="/history" />
          </Stats>
        </ChartCard>
      </div>
      <h3 style={{ margin: "20px 0 4px", fontSize: 14 }}>Value — five registers, never one number</h3>
      <p style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--ink-500)" }}>{v.never_combined}</p>
      <div className="ins-grid">{v.order.map(register)}</div>
      <h3 style={{ margin: "20px 0 4px", fontSize: 14 }}>Engine connectivity</h3>
      <p style={{ margin: "0 0 8px", fontSize: 12.5, color: "var(--ink-500)" }}>{c.note}</p>
      <div className="tbl-wrap" style={{ overflowX: "auto" }}>
        <table className="tbl ins-table">
          <thead><tr><th scope="col">Family</th><th scope="col">Backend source</th><th scope="col">API</th><th scope="col">Visualization</th><th scope="col">Drilldown</th><th scope="col">Status</th></tr></thead>
          <tbody>{c.families.map((f) => <tr key={f.family}><td><strong>{f.family}</strong> {f.name}</td><td><span dir="ltr">{f.backend_source}</span></td><td><span dir="ltr">{f.api}</span></td><td>{f.visualization}</td><td>{f.drilldown}</td><td><span className="chip" data-tone={statusTone(f.status)}>{f.status.replace(/_/g, " ")}</span></td></tr>)}</tbody>
        </table>
      </div>
    </>
  );
}

function PerishabilityTab() {
  return (
    <ChartCard title="Perishability" description="Declared sector physics (produce, meat and seafood) are diagnosed on the Diagnostics page; Insights adds no second reading of them."
               leads={[{ href: "/diagnostics?tab=sector", label: "Open sector diagnostics" }]}>
      <p style={{ margin: 0, fontSize: 13, color: "var(--ink-700)" }}>Remaining life at receipt, days to expiry and the physics each product declares are read from the SKU master on Diagnostics, per product.</p>
    </ChartCard>
  );
}

// ── page ──────────────────────────────────────────────────────────────────────

function Body() {
  const { t } = useLocale();
  const copy = t.workspace.insights;
  const params = useSearchParams();
  const router = useRouter();
  const { request } = useWorkspaceData();
  const currency = request?.currency ?? "USD";
  const filters = useMemo(() => filtersFromParams(params), [params]);
  const set = useCallback<Setter>((changes) => {
    const next = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(changes)) { if (v == null || v === "") next.delete(k); else next.set(k, v); }
    router.replace(`/insights?${next.toString()}`, { scroll: false });
  }, [params, router]);
  const tabParam = params.get("tab") ?? "overview";
  const con = useLoad<Connectivity>(() => fetchConnectivity(), []);
  const perishable = con.data?.families.some((f) => f.family === "Sector physics" && f.status === "VISUALIZED") ?? false;
  const tabs: Tab[] = perishable ? [...TABS, "perishability"] : TABS;
  const tab: Tab = (tabs as string[]).includes(tabParam) ? (tabParam as Tab) : "overview";
  const { data: plan } = useLoad<PlanSummary>(() => fetchPlan(), []);
  useEffect(() => { track("insights_opened", { tab }); }, [tab]);
  return (
    <>
      <PageHead title={copy.title} sub={copy.sub} actions={<ButtonLink href="/decisions" role="secondary" size="sm">Open Decisions</ButtonLink>} />
      <div className="tabs" role="tablist" aria-label={copy.title}>
        {tabs.map((k) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => set({ tab: k === "overview" ? null : k })}>{copy.tabs[k]}</button>)}
      </div>
      <FilterBar filters={filters} set={set} dates={tab !== "decisions"} />
      <div role="tabpanel" style={{ marginTop: 8 }}>
        {tab === "overview" && <OverviewTab filters={filters} currency={currency} />}
        {tab === "demand" && <DemandTab filters={filters} set={set} plan={plan} />}
        {tab === "inventory" && <InventoryTab filters={filters} plan={plan} currency={currency} />}
        {tab === "supply" && <SupplyTab filters={filters} set={set} plan={plan} currency={currency} />}
        {tab === "service" && <ServiceTab filters={filters} set={set} plan={plan} />}
        {tab === "decisions" && <DecisionsTab currency={currency} />}
        {tab === "perishability" && <PerishabilityTab />}
      </div>
    </>
  );
}

export default function InsightsPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <Suspense fallback={<Loading label="Opening Insights…" cards={2} />}>
        <Body />
      </Suspense>
    </Gate>
  );
}
