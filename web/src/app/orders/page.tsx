"use client";

/**
 * PURCHASE ORDERS — what have I ordered, what should change, and what should I order next?
 *
 * Two lists, deliberately separate and deliberately next to each other:
 *
 *   **Proposals** are documents this workspace owns. A buyer creates one, ZAAD can evaluate it, a
 *   person approves it, and it is exported in the company's own format. Five things can start one
 *   — a ZAAD recommendation, the current ordering rule, a buyer typing it, a spreadsheet, or a
 *   change to an existing order — and they all produce the same object.
 *
 *   **Your system's orders** are evidence. They came from an upload and are never edited here. To
 *   change one you create a proposal *against* it, which is what the P4B amendment vocabulary is
 *   for: keep, arrive later, arrive sooner, reduce, cancel, split.
 *
 * Nothing on this page sends anything to a supplier. Approve and export are the end of the loop.
 */
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FileText, Plus, RefreshCw, Upload } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, EmptyState, ErrorState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { Column, DataTable, Drawer, Pager, SearchField, SelectField, Toolbar } from "@/components/workspace/Table";
import {
  AMENDMENT_LABEL, DATE, MONEY, NUMBER, ORIGIN_LABEL, STATE_LABEL,
  fetchImportedOrder, fetchImportedOrders, listDrafts,
  type DraftState, type DraftSummary, type ImportedOrderDetail, type ImportedOrderRow,
} from "@/lib/zaad/product";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";

const PAGE = 50;

const STATE_TONE: Record<DraftState, string> = {
  DRAFT: "", READY_FOR_REVIEW: "high", APPROVED: "good", REJECTED: "", EXPORTED: "good", SUPERSEDED: "",
};

function StateChip({ state }: { state: DraftState }) {
  return <span className="chip" data-tone={STATE_TONE[state] || undefined}>{STATE_LABEL[state]}</span>;
}

// ── proposals ─────────────────────────────────────────────────────────────────

function Proposals({ params, set }: { params: URLSearchParams; set: (c: Record<string, string | null>) => void }) {
  const state = params.get("state") ?? "";
  const origin = params.get("origin") ?? "";
  const q = params.get("q") ?? "";
  const offset = Number(params.get("offset") ?? 0);
  const [page, setPage] = useState<Awaited<ReturnType<typeof listDrafts>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState(q);

  useEffect(() => { setTyped(q); }, [q]);
  useEffect(() => {
    const handle = window.setTimeout(() => { if (typed !== q) set({ q: typed || null }); }, 250);
    return () => window.clearTimeout(handle);
  }, [typed, q, set]);

  useEffect(() => {
    let alive = true;
    setError(null);
    listDrafts({ state: state || undefined, origin: origin || undefined, q: q || undefined, limit: PAGE, offset })
      .then((p) => alive && setPage(p))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [state, origin, q, offset]);

  const columns: Column<DraftSummary>[] = useMemo(() => [
    { key: "reference", label: "Reference", width: 200,
      render: (r) => <strong style={{ fontWeight: 500, color: "var(--ink-950)" }}>{r.reference || r.draft_id.replace(/^draft_/, "")}</strong> },
    { key: "state", label: "Status", render: (r) => <StateChip state={r.state} /> },
    { key: "origin", label: "Where from", hideBelow: 900, render: (r) => ORIGIN_LABEL[r.origin] },
    { key: "supplier_id", label: "Supplier", hideBelow: 700, render: (r) => r.supplier_id ?? <span className="na">—</span> },
    { key: "lines", label: "Lines", numeric: true, sortable: true, render: (r) => NUMBER(r.lines) },
    { key: "units", label: "Units", numeric: true, sortable: true, render: (r) => r.units != null ? NUMBER(r.units) : <span className="na">—</span> },
    { key: "value", label: "Value", numeric: true, sortable: true, hideBelow: 700,
      title: (r) => r.value_incomplete ? "Some lines carry no price, so this is the value of the lines that do." : undefined,
      render: (r) => r.value ? <>{MONEY(r.value, r.currency ?? "USD")}{r.value_incomplete && <span className="na"> +</span>}</> : <span className="na">—</span> },
    { key: "updated_at", label: "Updated", sortable: true, hideBelow: 1100, render: (r) => DATE(r.updated_at) },
  ], []);

  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!page) return <Loading label="Reading your proposals…" cards={2} />;

  return (
    <>
      <Toolbar>
        <SearchField value={typed} onChange={setTyped} label="Search proposals" placeholder="Search reference, supplier or order" />
        <SelectField value={state} onChange={(v) => set({ state: v })} label="Status" all="Any status"
          options={(Object.keys(STATE_LABEL) as DraftState[]).map((s) => ({ value: s, label: STATE_LABEL[s] }))} />
        <SelectField value={origin} onChange={(v) => set({ origin: v })} label="Where from" all="Any origin"
          options={Object.entries(ORIGIN_LABEL).map(([value, label]) => ({ value, label }))} />
      </Toolbar>
      <DataTable
        caption="Proposed purchase orders" columns={columns} rows={page.rows}
        rowKey={(r) => r.draft_id}
        onSelect={(r) => { window.location.href = `/orders/${encodeURIComponent(r.draft_id)}`; }}
        empty={<EmptyState title="No proposed orders yet"
          actions={<><ButtonLink href="/orders/new" role="primary" icon={<Plus size={14} aria-hidden />}>Create a purchase order</ButtonLink>
            <ButtonLink href="/decisions">See what ZAAD recommends</ButtonLink></>}>
          A proposal can start from a ZAAD recommendation, from your current ordering rule, from a spreadsheet
          you upload, or from scratch. Whichever way it starts, it ends the same way: someone approves it and
          you export it in your own format.
        </EmptyState>}
      />
      <Pager total={page.total} limit={page.limit} offset={page.offset} unit="proposals"
        onOffset={(next) => set({ offset: String(next) })} />
    </>
  );
}

// ── the orders already in the operator's system ───────────────────────────────

function ImportedPanel({ poId, onClose }: { poId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<ImportedOrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { report } = useWorkspaceData();

  useEffect(() => {
    let alive = true;
    setDetail(null);
    fetchImportedOrder(poId).then((d) => alive && setDetail(d)).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [poId]);

  // What the engine's own commitment block says about this order, if the last run covered it.
  const commitment = useMemo(
    () => (report?.commitments?.orders ?? []).find((o) => String(o.po) === poId) ?? null,
    [report, poId]);

  const lines = detail?.lines ?? [];
  const supplier = detail?.supplier?.supplier_id ? String(detail.supplier.supplier_id) : null;

  return (
    <Drawer open title={poId} onClose={onClose}
      sub={detail ? <>From your system · never edited by ZAAD</> : undefined}
      actions={detail ? (
        <ButtonLink role="primary" size="sm"
          href={`/orders/new?amend=${encodeURIComponent(poId)}${supplier ? `&supplier=${encodeURIComponent(supplier)}` : ""}`}>
          Propose a change to this order
        </ButtonLink>
      ) : undefined}
    >
      {error && <Notice tone="warn">{error}</Notice>}
      {!detail && !error && <Loading label="Reading this order…" cards={1} />}
      {detail && (
        <>
          <dl className="kv">
            <dt>Supplier</dt>
            <dd>{supplier ? <Link href={`/diagnostics/supplier/${encodeURIComponent(supplier)}`}>{String(detail.supplier?.supplier_name || supplier)}</Link> : <span className="na">Not recorded</span>}</dd>
            <dt>Lines</dt><dd>{lines.length}</dd>
            <dt>Received</dt>
            <dd>{detail.receipts.length ? `${detail.receipts.length} receipt${detail.receipts.length === 1 ? "" : "s"}, first on ${DATE(String(detail.receipts[0].receipt_date))}` : "Nothing has arrived yet"}</dd>
          </dl>

          <Section title="Lines">
            <DataTable caption={`Lines on ${poId}`} dense rows={lines} rowKey={(r) => String(r.sku)}
              columns={[
                { key: "sku", label: "Product", render: (r) => <Link href={`/inventory?sku=${encodeURIComponent(String(r.sku))}`}>{String(r.sku)}</Link> },
                { key: "qty_ordered", label: "Ordered", numeric: true, render: (r) => NUMBER(Number(r.qty_ordered)) },
                { key: "unit_cost", label: "Unit cost", numeric: true, render: (r) => r.unit_cost != null ? MONEY(Number(r.unit_cost)) : <span className="na">—</span> },
                { key: "expected_delivery_date", label: "Expected", render: (r) => r.expected_delivery_date ? DATE(String(r.expected_delivery_date)) : <span className="na">Not given</span> },
              ]} />
          </Section>

          <Section title="What you may change">
            {detail.amendment_rights_declared ? (
              <>
                <DataTable caption={`Declared amendment rights on ${poId}`} dense
                  rows={detail.declared_options} rowKey={(r) => String(r.option_id)}
                  columns={[
                    { key: "action", label: "Right", render: (r) => String(r.action).replaceAll("_", " ") },
                    { key: "fee_per_unit", label: "Fee/unit", numeric: true, render: (r) => r.fee_per_unit != null ? MONEY(Number(r.fee_per_unit)) : "—" },
                    { key: "deadline", label: "By", render: (r) => r.deadline ? DATE(String(r.deadline)) : "—" },
                    { key: "contract_reference", label: "Contract", render: (r) => String(r.contract_reference ?? "—") },
                  ]} />
                {commitment && (
                  <div style={{ marginTop: 12 }}>
                    <Notice>
                      ZAAD&rsquo;s last plan recommends <strong>{AMENDMENT_LABEL[commitment.recommended_action] ?? commitment.recommended_action}</strong> for this order.{" "}
                      <Link href="/decisions">See the reasoning</Link>.
                    </Notice>
                  </div>
                )}
              </>
            ) : (
              <Notice>
                No right to change this order has been declared, so ZAAD will not price a change to it. It never
                infers that an order can be cancelled, deferred or reduced from the fact that others were.
                Declare the terms your contract gives you and ZAAD will evaluate them.
              </Notice>
            )}
          </Section>
        </>
      )}
    </Drawer>
  );
}

function Imported({ params, set }: { params: URLSearchParams; set: (c: Record<string, string | null>) => void }) {
  const { request } = useWorkspaceData();
  const q = params.get("poq") ?? "";
  const state = params.get("postate") ?? "open";
  const offset = Number(params.get("pooffset") ?? 0);
  const selected = params.get("po");
  const [page, setPage] = useState<Awaited<ReturnType<typeof fetchImportedOrders>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [typed, setTyped] = useState(q);

  useEffect(() => { setTyped(q); }, [q]);
  useEffect(() => {
    const handle = window.setTimeout(() => { if (typed !== q) set({ poq: typed || null }); }, 250);
    return () => window.clearTimeout(handle);
  }, [typed, q, set]);

  useEffect(() => {
    let alive = true;
    setError(null);
    fetchImportedOrders({ q: q || undefined, state: state || undefined, limit: PAGE, offset,
      as_of: request?.as_of?.slice(0, 10) })
      .then((p) => alive && setPage(p))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [q, state, offset, request]);

  const columns: Column<ImportedOrderRow>[] = useMemo(() => [
    { key: "po_id", label: "PO", width: 160, render: (r) => <strong style={{ fontWeight: 500, color: "var(--ink-950)" }}>{r.po_id}</strong> },
    { key: "po_date", label: "Ordered", sortable: true, render: (r) => DATE(r.po_date) },
    { key: "supplier_id", label: "Supplier", sortable: true, hideBelow: 700, render: (r) => r.supplier_id ?? <span className="na">—</span> },
    { key: "lines", label: "Lines", numeric: true, sortable: true, hideBelow: 1100, render: (r) => NUMBER(r.lines) },
    { key: "ordered_units", label: "Ordered", numeric: true, render: (r) => NUMBER(r.ordered_units) },
    { key: "open_units", label: "Still owed", numeric: true, sortable: true,
      render: (r) => r.open_units ? NUMBER(r.open_units) : <span className="chip" data-tone="good">Received</span> },
    { key: "expected_delivery_date", label: "Expected", sortable: true, hideBelow: 900,
      render: (r) => r.eta ? DATE(r.eta) : <span className="na">Not given</span> },
    { key: "value", label: "Value", numeric: true, sortable: true, hideBelow: 900,
      render: (r) => r.value ? MONEY(r.value) : <span className="na">—</span> },
  ], []);

  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!page) return <Loading label="Reading your purchase orders…" cards={2} />;
  if (!page.served) {
    return <EmptyState title="No purchase orders uploaded"
      actions={<ButtonLink href="/upload" role="primary">Add your purchase orders</ButtonLink>}>
      {page.note ?? "Once your purchase orders are in, ZAAD can measure supplier reliability and evaluate changes to open orders."}
    </EmptyState>;
  }

  return (
    <>
      <Toolbar>
        <SearchField value={typed} onChange={setTyped} label="Search purchase orders" placeholder="Search PO, supplier or product" />
        <SelectField value={state} onChange={(v) => set({ postate: v })} label="Status" all="Every order"
          options={[{ value: "open", label: "Still open" }, { value: "late", label: "Open and past its date" }, { value: "received", label: "Received" }]} />
      </Toolbar>
      <Notice>
        These came from your system and ZAAD never changes them. An order counts as open until its first receipt
        is recorded — the same rule the planner uses, so the units here are the units it plans with.
      </Notice>
      <div style={{ marginTop: 12 }}>
        <DataTable caption="Purchase orders from your system" columns={columns} rows={page.rows}
          rowKey={(r) => r.po_id} selected={selected} onSelect={(r) => set({ po: r.po_id })}
          sort={page.sort} direction={page.direction}
          onSort={(key) => set({ posort: key })}
          empty={<EmptyState title="No order matches that">Change the search or the status filter.</EmptyState>} />
      </div>
      <Pager total={page.total} limit={page.limit} offset={page.offset} unit="orders"
        onOffset={(next) => set({ pooffset: String(next) })} />
      {selected && <ImportedPanel poId={selected} onClose={() => set({ po: null })} />}
    </>
  );
}

// ── the page ──────────────────────────────────────────────────────────────────

function OrdersBody() {
  const params = useSearchParams();
  const router = useRouter();
  const tab = params.get("po") ? "imported" : (params.get("tab") ?? "proposals");

  const set = useCallback((changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
    }
    router.replace(`/orders?${next.toString()}`, { scroll: false });
  }, [params, router]);

  return (
    <>
      <PageHead
        title="Purchase orders"
        sub="What you have ordered, what ZAAD suggests changing, and what to order next."
        actions={
          <>
            <ButtonLink size="sm" href="/orders/upload" icon={<Upload size={14} aria-hidden />}>Upload a proposal</ButtonLink>
            <ButtonLink size="sm" href="/orders/formats" icon={<FileText size={14} aria-hidden />}>Export formats</ButtonLink>
            <ButtonLink role="primary" href="/orders/new" icon={<Plus size={15} aria-hidden />}>Create a purchase order</ButtonLink>
          </>
        }
      />

      <div className="tabs" role="tablist" aria-label="Purchase orders">
        <button role="tab" aria-selected={tab === "proposals"} onClick={() => set({ tab: "proposals", po: null })}>Proposals</button>
        <button role="tab" aria-selected={tab === "imported"} onClick={() => set({ tab: "imported" })}>Your system&rsquo;s orders</button>
      </div>

      <div role="tabpanel" style={{ marginTop: 16 }}>
        {tab === "proposals" ? <Proposals params={params} set={set} /> : <Imported params={params} set={set} />}
      </div>
    </>
  );
}

export default function OrdersPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <Suspense fallback={<Loading label="Reading your orders…" cards={2} />}>
        <OrdersBody />
      </Suspense>
    </Gate>
  );
}
