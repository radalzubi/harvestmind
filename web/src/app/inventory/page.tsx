"use client";

/**
 * INVENTORY — what do I have, what is coming, where is it, and what is at risk?
 *
 * A distributor with ten thousand products does not browse. They search, they filter, they sort by
 * the column that matters this morning, and they open one product. So this page is a dense
 * server-side table and a detail panel, and the browser never holds more than one page of it.
 *
 * Everything in the table is either a column the operator uploaded or arithmetic over two of them:
 * stock × unit cost is value, stock ÷ average weekly demand is weeks of cover. Nothing here is an
 * optimizer output, and nothing pretends to be — what ZAAD *recommends* lives in Decisions, over
 * the products the last run covered, and this page links to it rather than implying the whole
 * catalogue was evaluated.
 */
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FileText, RefreshCw, Share2 } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Disclosure, EmptyState, ErrorState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { Column, DataTable, Drawer, NotAvailable, Pager, SearchField, SelectField, Toolbar } from "@/components/workspace/Table";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import {
  DATE, MONEY, NUMBER, fetchDatasetValues, fetchInventory, fetchSku,
  type InventoryPage, type InventoryRow, type SkuDetail,
} from "@/lib/zaad/product";

const PAGE = 50;

const COVER_CHOICES = [
  { value: "out", label: "Out of stock" },
  { value: "under2", label: "Under 2 weeks' cover" },
  { value: "under4", label: "Under 4 weeks' cover" },
  { value: "over12", label: "Over 12 weeks' cover" },
  { value: "unknown", label: "Cover not measurable" },
];

function coverChip(weeks: number | null | undefined, onHand: number | null | undefined) {
  if (onHand != null && onHand <= 0) return <span className="chip" data-tone="bad">Out of stock</span>;
  if (weeks == null) return <NotAvailable why="Weeks of cover needs both a stock count and customer order history." />;
  const tone = weeks < 2 ? "bad" : weeks < 4 ? "warn" : weeks > 12 ? "high" : "good";
  return <span className="chip" data-tone={tone}>{weeks < 10 ? weeks.toFixed(1) : Math.round(weeks)} wks</span>;
}

/**
 * Filter values a workspace actually has, read once from the product master.
 *
 * A filter is offered only when the column exists and has values: a workspace that declares no
 * brand never sees a brand filter with nothing in it.
 */
function useFacets() {
  const [facets, setFacets] = useState<{ category: string[]; brand: string[]; supplier: string[] }>({
    category: [], brand: [], supplier: [],
  });
  useEffect(() => {
    let alive = true;
    const load = (column: string) => fetchDatasetValues("products", column)
      .then((r) => r.values).catch(() => [] as string[]);
    Promise.all([load("category"), load("brand"), load("supplier_id")])
      .then(([category, brand, supplier]) => { if (alive) setFacets({ category, brand, supplier }); });
    return () => { alive = false; };
  }, []);
  return facets;
}

function SkuPanel({ sku, onClose }: { sku: string; onClose: () => void }) {
  const [detail, setDetail] = useState<SkuDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { decisions } = useWorkspaceData();

  useEffect(() => {
    let alive = true;
    setDetail(null);
    setError(null);
    fetchSku(sku).then((d) => alive && setDetail(d)).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [sku]);

  const related = useMemo(
    () => decisions.filter((d) => JSON.stringify(d.target).includes(sku) || d.headline.includes(sku)),
    [decisions, sku]);

  const overview = detail?.overview ?? {};
  return (
    <Drawer
      open
      title={detail?.overview?.sku_name || sku}
      sub={detail ? <>{sku}{overview.category ? ` · ${overview.category}` : ""}{overview.supplier_id ? ` · ${overview.supplier_id}` : ""}</> : sku}
      onClose={onClose}
      actions={detail ? (
        <>
          <ButtonLink role="primary" size="sm" href={`/orders/new?sku=${encodeURIComponent(sku)}${overview.supplier_id ? `&supplier=${encodeURIComponent(String(overview.supplier_id))}` : ""}`} icon={<FileText size={14} aria-hidden />}>
            Create a proposed order
          </ButtonLink>
          {overview.supplier_id && (
            <ButtonLink size="sm" href={`/diagnostics/supplier/${encodeURIComponent(String(overview.supplier_id))}`}>
              Supplier
            </ButtonLink>
          )}
          <ButtonLink size="sm" href={`/network?q=${encodeURIComponent(sku)}`} icon={<Share2 size={14} aria-hidden />}>
            In the network
          </ButtonLink>
        </>
      ) : undefined}
    >
      {error && <Notice tone="warn">{error}</Notice>}
      {!detail && !error && <Loading label="Reading this product…" cards={1} />}
      {detail && (
        <>
          <dl className="kv">
            <dt>On hand</dt><dd>{overview.on_hand != null ? `${NUMBER(overview.on_hand)} units` : <NotAvailable />}</dd>
            <dt>On order</dt><dd>{overview.inbound_units != null ? `${NUMBER(overview.inbound_units)} units on ${NUMBER(overview.open_pos)} open order${overview.open_pos === 1 ? "" : "s"}` : <NotAvailable />}</dd>
            <dt>Weekly demand</dt><dd>{overview.weekly_demand != null ? `${NUMBER(overview.weekly_demand)} units` : <NotAvailable why="Needs customer order history." />}</dd>
            <dt>Weeks of cover</dt><dd>{coverChip(overview.cover_weeks, overview.on_hand)}</dd>
            <dt>Stock value</dt><dd>{overview.inventory_value != null ? MONEY(overview.inventory_value) : <NotAvailable why="Needs a unit cost on the product master." />}</dd>
            <dt>Pack</dt><dd>{overview.units_per_case ? `${NUMBER(overview.units_per_case)} per case` : <NotAvailable />}</dd>
            {overview.moq_units ? <><dt>Minimum order</dt><dd>{NUMBER(overview.moq_units)} units</dd></> : null}
            {overview.shelf_life_days ? <><dt>Shelf life</dt><dd>{NUMBER(overview.shelf_life_days)} days</dd></> : null}
          </dl>

          {related.length > 0 && (
            <Section title="What ZAAD recommends">
              <div className="dec-list">
                {related.slice(0, 3).map((d) => (
                  <Link key={d.id} href={`/decisions?decision=${encodeURIComponent(d.id)}`} style={{ textDecoration: "none", color: "inherit" }}>
                    <div className="dec">
                      <div className="dec-top"><span className="dec-verb" data-tone="change">{d.verb}</span></div>
                      <h3 className="dec-h" style={{ fontSize: 13.5 }}>{d.headline}</h3>
                    </div>
                  </Link>
                ))}
              </div>
            </Section>
          )}

          <Section title="Where it is">
            {detail.stock_by_site.length ? (
              <DataTable
                caption={`Stock of ${sku} by site`} dense
                rows={detail.stock_by_site} rowKey={(r) => r.location_id}
                columns={[
                  { key: "location_id", label: "Site", render: (r) => r.location_id },
                  { key: "on_hand", label: "On hand", numeric: true, render: (r) => NUMBER(r.on_hand) },
                  { key: "in_transit", label: "In transit", numeric: true, render: (r) => NUMBER(r.in_transit) },
                  { key: "snapshot_date", label: "As at", render: (r) => DATE(r.snapshot_date) },
                ]}
              />
            ) : <Notice>No stock snapshot has been uploaded for this product.</Notice>}
          </Section>

          <Section title="Recent purchase orders">
            {detail.purchase_orders.length ? (
              <DataTable
                caption={`Purchase orders for ${sku}`} dense
                rows={detail.purchase_orders.slice(0, 12)} rowKey={(r) => r.po_id}
                columns={[
                  { key: "po_id", label: "PO", render: (r) => <Link href={`/orders?po=${encodeURIComponent(r.po_id)}`}>{r.po_id}</Link> },
                  { key: "po_date", label: "Ordered on", render: (r) => DATE(r.po_date) },
                  { key: "qty_ordered", label: "Quantity", numeric: true, render: (r) => NUMBER(r.qty_ordered) },
                  { key: "qty_received", label: "Received", numeric: true, render: (r) => r.qty_received != null ? NUMBER(r.qty_received) : "—" },
                  { key: "first_receipt", label: "Arrived", render: (r) => r.first_receipt ? DATE(r.first_receipt) : <span className="chip" data-tone="warn">Open</span> },
                ]}
              />
            ) : <Notice>No purchase orders have been uploaded for this product.</Notice>}
          </Section>

          <Section title="What customers ordered">
            {detail.demand_by_week.length ? (
              <>
                <Sparkline rows={detail.demand_by_week} />
                <p className="tbl-count">
                  {detail.short_shipped_lines ? `${NUMBER(detail.short_shipped_lines)} order lines shipped short of what was ordered.` : "No order line was shipped short."}
                </p>
              </>
            ) : <Notice>No customer order history has been uploaded for this product.</Notice>}
          </Section>

          {detail.declared_sources.length > 0 && (
            <Section title="Declared sources">
              <DataTable
                caption={`Declared sources for ${sku}`} dense
                rows={detail.declared_sources} rowKey={(r) => String(r.supplier_id)}
                columns={[
                  { key: "supplier_id", label: "Supplier", render: (r) => <Link href={`/diagnostics/supplier/${encodeURIComponent(String(r.supplier_id))}`}>{String(r.supplier_id)}</Link> },
                  { key: "unit_cost", label: "Unit cost", numeric: true, render: (r) => r.unit_cost != null ? MONEY(Number(r.unit_cost)) : "—" },
                  { key: "lead_time_promised_weeks", label: "Lead (wks)", numeric: true, render: (r) => r.lead_time_promised_weeks != null ? NUMBER(Number(r.lead_time_promised_weeks), 1) : "—" },
                  { key: "approved", label: "Approved", render: (r) => String(r.approved) === "true" ? "Yes" : "No" },
                ]}
              />
            </Section>
          )}

          {detail.missing.length > 0 && (
            <Section title="What ZAAD does not have">
              <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13, color: "var(--ink-600)", lineHeight: 1.6 }}>
                {detail.missing.map((m) => <li key={m}>{m}</li>)}
              </ul>
            </Section>
          )}

          <div style={{ marginTop: 18 }}>
            <Disclosure summary="Technical details" hint="the record as uploaded">
              <pre className="disc-tech">{JSON.stringify(detail.master, null, 2)}</pre>
            </Disclosure>
          </div>
        </>
      )}
    </Drawer>
  );
}

/** Six months of weekly demand, as a shape rather than a table of numbers. */
function Sparkline({ rows }: { rows: Array<{ week: string; ordered: number; shipped: number }> }) {
  const max = Math.max(1, ...rows.map((r) => r.ordered));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 64, padding: "0 2px" }}
      role="img" aria-label={`Weekly customer demand over ${rows.length} weeks, highest ${Math.round(max).toLocaleString("en-US")} units`}>
      {rows.map((r) => (
        <div key={r.week} title={`${DATE(r.week)}: ${NUMBER(r.ordered)} ordered, ${NUMBER(r.shipped)} shipped`}
          style={{
            flex: 1, minWidth: 3, height: `${Math.max(2, (r.ordered / max) * 100)}%`,
            background: r.shipped < r.ordered * 0.995 ? "var(--warn)" : "var(--accent)",
            opacity: 0.85, borderRadius: 2,
          }} />
      ))}
    </div>
  );
}

function InventoryBody() {
  const params = useSearchParams();
  const router = useRouter();
  const facets = useFacets();
  const { scope, planPhase } = useWorkspaceData();

  const q = params.get("q") ?? "";
  const category = params.get("category") ?? "";
  const brand = params.get("brand") ?? "";
  const supplier = params.get("supplier") ?? "";
  const cover = params.get("cover") ?? "";
  const planned = params.get("planned") === "1";
  const sort = params.get("sort") ?? "sku";
  const direction = params.get("dir") ?? "asc";
  const offset = Number(params.get("offset") ?? 0);
  const selected = params.get("sku");

  const [page, setPage] = useState<InventoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [typed, setTyped] = useState(q);

  const set = useCallback((changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    if (!("offset" in changes)) next.delete("offset");
    router.replace(`/inventory?${next.toString()}`, { scroll: false });
  }, [params, router]);

  useEffect(() => { setTyped(q); }, [q]);
  useEffect(() => {
    const handle = window.setTimeout(() => { if (typed !== q) set({ q: typed || null }); }, 250);
    return () => window.clearTimeout(handle);
  }, [typed, q, set]);

  useEffect(() => {
    let alive = true;
    setBusy(true);
    setError(null);
    fetchInventory({
      q: q || undefined, category: category || undefined, brand: brand || undefined,
      supplier_id: supplier || undefined, cover: cover || undefined,
      skus: planned && scope?.skus.length ? scope.skus.join(",") : undefined,
      sort, direction, limit: PAGE, offset,
    })
      .then((p) => { if (alive) setPage(p); })
      .catch((e) => { if (alive) setError(e.message); })
      .finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [q, category, brand, supplier, cover, planned, sort, direction, offset, scope]);

  const columns: Column<InventoryRow>[] = useMemo(() => [
    { key: "sku", label: "Product", sortable: true, width: 240,
      title: (r) => `${r.sku}${r.sku_name ? ` — ${r.sku_name}` : ""}`,
      render: (r) => (
        <span>
          <strong style={{ fontWeight: 500, color: "var(--ink-950)" }}>{r.sku_name || r.sku}</strong>
          {r.sku_name && <span style={{ color: "var(--ink-400)", marginInlineStart: 6, fontSize: 12 }}>{r.sku}</span>}
        </span>
      ) },
    { key: "brand", label: "Brand", sortable: true, hideBelow: 1100, render: (r) => r.brand ?? <span className="na">—</span> },
    { key: "category", label: "Category", sortable: true, hideBelow: 900, render: (r) => r.category ?? <span className="na">—</span> },
    { key: "supplier_id", label: "Supplier", sortable: true, hideBelow: 900,
      render: (r) => r.supplier_id
        ? <Link href={`/diagnostics/supplier/${encodeURIComponent(r.supplier_id)}`} onClick={(e) => e.stopPropagation()}>{r.supplier_name || r.supplier_id}</Link>
        : <span className="na">—</span> },
    { key: "on_hand", label: "On hand", numeric: true, sortable: true, render: (r) => r.on_hand != null ? NUMBER(r.on_hand) : <span className="na">—</span> },
    { key: "inbound_units", label: "On order", numeric: true, sortable: true, hideBelow: 700, render: (r) => r.inbound_units ? NUMBER(r.inbound_units) : <span className="na">—</span> },
    { key: "weekly_demand", label: "Per week", numeric: true, sortable: true, hideBelow: 1100, render: (r) => r.weekly_demand != null ? NUMBER(r.weekly_demand) : <span className="na">—</span> },
    { key: "cover_weeks", label: "Cover", numeric: true, sortable: true, render: (r) => coverChip(r.cover_weeks, r.on_hand) },
    { key: "inventory_value", label: "Stock value", numeric: true, sortable: true, hideBelow: 700,
      render: (r) => r.inventory_value != null ? MONEY(r.inventory_value) : <span className="na">—</span> },
  ], []);

  if (error) {
    return <ErrorState title="Your inventory could not be read"
      affects="Nothing was changed; this page only reads."
      whatToDo="Try again. If it keeps failing, your access may have been rotated."
      detail={error} actions={<Button role="primary" onClick={() => set({})}>Try again</Button>} />;
  }
  if (!page) return <Loading label="Reading your product list…" cards={2} />;
  if (!page.served) {
    return <EmptyState title="No product list yet"
      actions={<ButtonLink href="/upload" role="primary">Add your product list</ButtonLink>}>
      {page.note ?? "ZAAD needs your product master before it can show your inventory."}
    </EmptyState>;
  }

  const filtered = Boolean(q || category || brand || supplier || cover || planned);

  return (
    <>
      <PageHead
        title="Inventory"
        sub={page.snapshot_date
          ? `Stock as counted on ${DATE(page.snapshot_date)}. Weeks of cover is your stock divided by average weekly demand over the last ${page.demand_weeks} weeks.`
          : "Your product list. Stock appears once a stock count is uploaded."}
        actions={<Button role="tertiary" size="sm" icon={<RefreshCw size={14} aria-hidden />} onClick={() => set({})}>Refresh</Button>}
      />

      <Toolbar>
        <SearchField value={typed} onChange={setTyped} label="Search products"
          placeholder="Search code, description, brand or category" />
        {facets.category.length > 0 && <SelectField value={category} onChange={(v) => set({ category: v })}
          label="Category" all="Every category" options={facets.category.map((c) => ({ value: c, label: c }))} />}
        {facets.brand.length > 0 && <SelectField value={brand} onChange={(v) => set({ brand: v })}
          label="Brand" all="Every brand" options={facets.brand.map((c) => ({ value: c, label: c }))} />}
        {facets.supplier.length > 0 && <SelectField value={supplier} onChange={(v) => set({ supplier: v })}
          label="Supplier" all="Every supplier" options={facets.supplier.map((c) => ({ value: c, label: c }))} />}
        <SelectField value={cover} onChange={(v) => set({ cover: v })} label="Weeks of cover"
          all="Any cover" options={COVER_CHOICES} />
        <div className="tbar-spacer" />
        {filtered && <Button size="sm" role="tertiary" onClick={() => router.replace("/inventory")}>Clear filters</Button>}
      </Toolbar>

      {scope && planPhase === "ready" && (
        <div style={{ marginBottom: 12 }}>
          <Notice>
            <p style={{ margin: 0 }}>
              ZAAD&rsquo;s last run covered {scope.skus.length} of your {scope.total} products.
              Recommendations for them are in <Link href="/decisions">Decisions</Link>.
            </p>
            <div style={{ marginTop: 10 }}>
              <Button size="sm" onClick={() => set({ planned: planned ? null : "1" })}>
                {planned ? "Show every product" : "Show only those products"}
              </Button>
            </div>
          </Notice>
        </div>
      )}

      <div style={{ opacity: busy ? 0.6 : 1, transition: "opacity .12s" }}>
        <DataTable
          caption="Products with their stock position"
          columns={columns} rows={page.rows} rowKey={(r) => r.sku}
          selected={selected} onSelect={(r) => set({ sku: r.sku, offset: String(offset) })}
          sort={page.sort} direction={page.direction}
          onSort={(key) => set({ sort: key, dir: page.sort === key && page.direction === "asc" ? "desc" : "asc" })}
          empty={<EmptyState title="No product matches that">
            {filtered ? "Change or clear the filters above." : "Your product list is empty."}
          </EmptyState>}
        />
      </div>
      <Pager total={page.total} limit={page.limit} offset={page.offset} unit="products"
        onOffset={(next) => set({ offset: String(next) })} />

      {selected && <SkuPanel sku={selected} onClose={() => set({ sku: null, offset: String(offset) })} />}
    </>
  );
}

export default function InventoryPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <Suspense fallback={<Loading label="Reading your product list…" cards={2} />}>
        <InventoryBody />
      </Suspense>
    </Gate>
  );
}
