"use client";

/**
 * ONE SUPPLIER — and the question a distributor asks about one every week: *why is this late?*
 *
 * The answer is laid out in four registers, in this order and never blended:
 *
 *   WHAT IS MEASURED     counts and quantiles over orders matched to receipts.
 *   WHERE IT CONCENTRATES an association, labelled as an association. Not a cause.
 *   WHAT IS NOT KNOWN    named together with the fields that would settle it.
 *   WHAT YOU CAN DO      affected products, open orders, declared alternatives.
 *
 * That order is the product. A supplier page that opens with a root cause it cannot support is
 * worse than one that says plainly what it can and cannot see — the second is trusted the first
 * time somebody checks it against reality.
 */
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, Info } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Disclosure, ErrorState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { Column, DataTable, NotAvailable, Tally } from "@/components/workspace/Table";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import {
  COUNT, DATE, MONEY, NUMBER, PERCENT, fetchSupplier, type SupplierDetail,
} from "@/lib/zaad/product";

function Statement({ text, sample, thin, note, tone }: {
  text: string; sample?: number | null; thin?: boolean; note?: string; tone: "fact" | "association";
}) {
  return (
    <li style={{ marginBottom: 10 }}>
      <span style={{ color: "var(--ink-900)" }}>{text}</span>
      {thin && sample != null && (
        <span className="chip" data-tone="warn" style={{ marginInlineStart: 8 }}>only {COUNT(sample, "order")}</span>
      )}
      {tone === "association" && (
        <span className="chip" style={{ marginInlineStart: 8 }}>a pattern, not a cause</span>
      )}
      {note && <div style={{ marginTop: 3, fontSize: 12.5, color: "var(--ink-500)" }}>{note}</div>}
    </li>
  );
}

function Trend({ trend }: { trend: SupplierDetail["trend"] }) {
  if (!trend) return null;
  const rows = [
    { label: "Arrived late", key: "late_rate", percent: true },
    { label: "Quantity arrived", key: "fill_rate", percent: true },
    { label: "Days from order to arrival", key: "mean_lead_days", percent: false },
  ];
  return (
    <DataTable caption="Recent half against earlier half" dense rows={rows} rowKey={(r) => r.key}
      columns={[
        { key: "label", label: "", render: (r) => r.label },
        { key: "earlier", label: "Earlier orders", numeric: true,
          render: (r) => {
            const value = trend.earlier[r.key];
            return value == null ? <span className="na">—</span> : r.percent ? PERCENT(value) : NUMBER(value, 1);
          } },
        { key: "recent", label: "Recent orders", numeric: true,
          render: (r) => {
            const value = trend.recent[r.key];
            return value == null ? <span className="na">—</span> : r.percent ? PERCENT(value) : NUMBER(value, 1);
          } },
      ]} />
  );
}

function SupplierBody({ id }: { id: string }) {
  const { request } = useWorkspaceData();
  const [detail, setDetail] = useState<SupplierDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchSupplier(id, request?.as_of?.slice(0, 10))
      .then((d) => alive && setDetail(d))
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [id, request]);

  const alternatives = detail?.alternatives;
  const bySku = useMemo(() => (detail?.by_product ?? []).filter((r) => r.orders > 0), [detail]);

  if (error) {
    return <ErrorState title="That supplier could not be opened"
      affects="Nothing was changed; this page only reads."
      whatToDo="It may not be in this workspace."
      detail={error} actions={<ButtonLink role="primary" href="/diagnostics">Back to diagnostics</ButtonLink>} />;
  }
  if (!detail) return <Loading label="Measuring this supplier…" cards={3} />;

  const m = detail.measured;
  const master = detail.master ?? {};

  return (
    <>
      <PageHead
        title={String(master.supplier_name || m.name || id)}
        sub={[id, master.origin_iso3 ? `Origin ${master.origin_iso3}` : null, master.route ? `Route ${master.route}` : null]
          .filter(Boolean).join(" · ")}
        actions={<>
          <ButtonLink size="sm" href={`/inventory?supplier=${encodeURIComponent(id)}`}>Products</ButtonLink>
          <ButtonLink size="sm" href={`/orders?tab=imported&poq=${encodeURIComponent(id)}`}>Orders</ButtonLink>
          {/* A supplier is a node in the twin, not a product filter, and `?q=` was read by nothing —
              this button opened the network at whatever it would have shown anyway. */}
          <ButtonLink size="sm" href={`/network?node=${encodeURIComponent(`sup:${id}`)}`}>In the network</ButtonLink>
        </>}
      />

      <dl className="snap">
        <div><dt>Arrived late</dt><dd>{m.late_rate != null ? PERCENT(m.late_rate, 0) : "—"}
          <small>{m.orders_with_promise ? `of ${COUNT(m.orders_with_promise, "order")} with a promised date` : "no promised dates uploaded"}</small></dd></div>
        <div><dt>Quantity arrived</dt><dd>{m.fill_rate != null ? PERCENT(m.fill_rate) : "—"}
          <small>{m.matched_orders ? `across ${COUNT(m.matched_orders, "matched order")}` : "nothing matched yet"}</small></dd></div>
        <div><dt>Typical lead</dt><dd>{m.p50_lead_days != null ? `${NUMBER(m.p50_lead_days)} d` : "—"}
          <small>{m.p90_lead_days != null ? `one in ten takes ${COUNT(m.p90_lead_days, "day")}` : "not measured"}</small></dd></div>
        <div><dt>Open orders</dt><dd>{NUMBER(m.open_orders)}
          <small>{m.late_open_orders ? `${COUNT(m.late_open_orders, "order")} past their date` : "none past their date"}</small></dd></div>
        <div><dt>Products</dt><dd>{NUMBER(detail.exposure.skus)}
          <small>{detail.exposure.on_hand_value != null ? `${MONEY(detail.exposure.on_hand_value)} in stock` : "stock value not available"}</small></dd></div>
      </dl>

      <Section title="Why is this supplier late?">
        <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "16px 18px" }}>
          <h3 style={{ margin: "0 0 10px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>
            What is measured
          </h3>
          {detail.lateness.observed.length ? (
            <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13.5, lineHeight: 1.6 }}>
              {detail.lateness.observed.map((s, i) => (
                <Statement key={i} text={s.statement} sample={s.sample} thin={s.thin} tone="fact" />
              ))}
            </ul>
          ) : <p className="na" style={{ margin: 0, fontSize: 13.5 }}>Nothing is matched for this supplier yet.</p>}

          {detail.lateness.associations.length > 0 && (
            <>
              <h3 style={{ margin: "18px 0 10px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>
                Where it concentrates
              </h3>
              <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13.5, lineHeight: 1.6 }}>
                {detail.lateness.associations.map((s, i) => (
                  <Statement key={i} text={s.statement} note={s.note} tone="association" />
                ))}
              </ul>
            </>
          )}

          <h3 style={{ margin: "18px 0 8px", fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>
            What ZAAD cannot tell you
          </h3>
          <p style={{ margin: 0, fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.65 }}>
            <AlertTriangle size={14} aria-hidden style={{ verticalAlign: "-2px", marginInlineEnd: 6, color: "var(--warn)" }} />
            {detail.lateness.unknown.statement}
          </p>
          <div style={{ marginTop: 10 }}>
            <Disclosure summary="What would settle it" hint={`${detail.lateness.unknown.missing_fields.length} fields`}>
              <p style={{ margin: "0 0 8px", fontSize: 13, color: "var(--ink-700)" }}>{detail.lateness.driver_note}</p>
              <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13, color: "var(--ink-700)", lineHeight: 1.6 }}>
                {detail.lateness.unknown.missing_fields.map((f) => <li key={f}>{f}</li>)}
              </ul>
              <p style={{ margin: "10px 0 0", fontSize: 12.5, color: "var(--ink-500)" }}>
                ZAAD has: {detail.lateness.unknown.available_fields.join(", ")}.
              </p>
            </Disclosure>
          </div>
        </div>
      </Section>

      {detail.trend && (
        <Section title="Is it getting better or worse?">
          <Trend trend={detail.trend} />
          <p className="zhelp" style={{ marginTop: 10 }}>
            The most recent half of this supplier&rsquo;s matched orders against the earlier half. A direction, not a
            forecast.
          </p>
        </Section>
      )}

      {bySku.length > 0 && (
        <Section title="By product">
          <DataTable caption="Lateness and fill by product" dense rows={bySku} rowKey={(r) => r.sku}
            columns={[
              { key: "sku", label: "Product", render: (r) => <Link href={`/inventory?sku=${encodeURIComponent(r.sku)}`}>{r.sku}</Link> },
              { key: "orders", label: "Orders", numeric: true, render: (r) => NUMBER(r.orders) },
              // The page's own summary says lateness cannot be measured when no order carries a
              // promised date. This table printed 0 under the same heading, on the same screen.
              { key: "late_orders", label: "Arrived late", numeric: true,
                render: (r) => r.orders_with_promise === 0
                  ? <span className="na">not measurable</span>
                  : <Tally value={r.late_orders} none="none late" /> },
              { key: "mean_late_days", label: "Days late", numeric: true, render: (r) => r.mean_late_days != null ? NUMBER(r.mean_late_days, 1) : <span className="na">—</span> },
              { key: "fill_rate", label: "Quantity arrived", numeric: true, render: (r) => r.fill_rate != null ? PERCENT(r.fill_rate) : <NotAvailable /> },
            ]} />
        </Section>
      )}

      <Section title="If this supplier cannot deliver">
        {alternatives?.declared ? (
          <>
            <DataTable caption="Declared alternative sources for this supplier's products" dense
              rows={alternatives.rows} rowKey={(r) => `${r.sku}-${r.supplier_id}`}
              columns={[
                { key: "sku", label: "Product", render: (r) => <Link href={`/inventory?sku=${encodeURIComponent(String(r.sku))}`}>{String(r.sku)}</Link> },
                { key: "supplier_id", label: "Alternative", render: (r) => <Link href={`/diagnostics/supplier/${encodeURIComponent(String(r.supplier_id))}`}>{String(r.supplier_id)}</Link> },
                { key: "unit_cost", label: "Unit cost", numeric: true, render: (r) => r.unit_cost != null ? MONEY(Number(r.unit_cost)) : <NotAvailable /> },
                { key: "lead_time_promised_weeks", label: "Lead (wks)", numeric: true, render: (r) => r.lead_time_promised_weeks != null ? NUMBER(Number(r.lead_time_promised_weeks), 1) : <NotAvailable /> },
                { key: "capacity_per_week", label: "Capacity/wk", numeric: true, render: (r) => r.capacity_per_week != null ? NUMBER(Number(r.capacity_per_week)) : <NotAvailable /> },
                { key: "approved", label: "Approved", render: (r) => String(r.approved) === "true" ? "Yes" : "No" },
              ]} />
            <div style={{ marginTop: 12 }}>
              <Notice>
                <Info size={14} aria-hidden style={{ verticalAlign: "-2px", marginInlineEnd: 6 }} />
                These are sources you have declared, with the terms you declared for them. Whether ZAAD would
                actually buy from one is a decision the optimizer makes in a plan — it weighs cost, capacity,
                reliability and shared risk together, not unit price alone. <Link href="/decisions">See what it decided</Link>.
              </Notice>
            </div>
          </>
        ) : (
          <Notice>
            {alternatives?.note}
            {" "}Declare the sources you have qualified and ZAAD will consider them when it plans — including
            what it would cost to move volume if this supplier stops delivering.
          </Notice>
        )}
      </Section>

      <Section title="Recent deliveries">
        {detail.deliveries.length ? (
          <DataTable caption="Matched orders and receipts" dense rows={detail.deliveries.slice(0, 25)}
            rowKey={(r) => r.po_id}
            columns={[
              { key: "po_id", label: "PO", render: (r) => <Link href={`/orders?po=${encodeURIComponent(r.po_id)}`}>{r.po_id}</Link> },
              { key: "po_date", label: "Ordered on", render: (r) => DATE(r.po_date) },
              { key: "promised", label: "Promised", render: (r) => r.promised ? DATE(r.promised) : <span className="na">—</span> },
              { key: "first_receipt", label: "Arrived", render: (r) => DATE(r.first_receipt) },
              { key: "late_days", label: "Against promise", numeric: true,
                render: (r) => r.late_days == null ? <span className="na">no promised date</span>
                  : r.late_days > 0 ? <span className="chip" data-tone="warn">{NUMBER(r.late_days)} d late</span>
                  : r.late_days < 0 ? <span className="na">{NUMBER(-r.late_days)} d early</span>
                  : "on the day" },
              { key: "fill", label: "Quantity arrived", numeric: true, render: (r) => r.fill != null ? PERCENT(r.fill) : <NotAvailable /> },
            ]} />
        ) : <Notice>No order has been matched to a receipt for this supplier yet.</Notice>}
      </Section>

      <div style={{ marginTop: 22 }}>
        <Disclosure summary="Technical details" hint="the supplier record as uploaded">
          <pre className="disc-tech">{JSON.stringify({ master, measured: m }, null, 2)}</pre>
        </Disclosure>
      </div>
    </>
  );
}

export default function SupplierPage() {
  const params = useParams<{ id: string }>();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      {id ? <SupplierBody id={decodeURIComponent(id)} /> : <Loading label="Opening this supplier…" cards={2} />}
    </Gate>
  );
}
