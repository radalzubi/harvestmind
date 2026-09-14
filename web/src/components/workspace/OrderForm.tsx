"use client";

/**
 * The order editor a buyer actually uses.
 *
 * Not a JSON form: a supplier, a destination, two dates and a list of lines, with product search
 * that works at catalogue scale because it asks the server. Pack sizes, minimum order quantities
 * and supplier capacity produce **warnings**, never prohibitions — a buyer has reasons, and a
 * system that refuses a 2,401-unit order because cases are 24 is a system people work around.
 *
 * The same component serves all five origins. A proposal created from a ZAAD recommendation is
 * edited here, and so is one typed from scratch, so the two can never drift apart.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Plus, Search, Trash2 } from "lucide-react";
import { Button } from "./ui";
import { NotAvailable } from "./Table";
import { MONEY, NUMBER, fetchInventory, type DraftLine, type InventoryRow } from "@/lib/zaad/product";

export interface OrderHeader {
  reference: string;
  supplier_id: string;
  destination_id: string;
  currency: string;
  requested_order_date: string;
  requested_receipt_date: string;
  notes: string;
}

export const EMPTY_HEADER: OrderHeader = {
  reference: "", supplier_id: "", destination_id: "", currency: "USD",
  requested_order_date: new Date().toISOString().slice(0, 10), requested_receipt_date: "", notes: "",
};

export function HeaderFields({ value, onChange, locations, disabled }: {
  value: OrderHeader; onChange: (next: OrderHeader) => void; locations: string[]; disabled?: boolean;
}) {
  const set = (key: keyof OrderHeader) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    onChange({ ...value, [key]: event.target.value });
  return (
    <div className="fld-row">
      <label><span className="fld-label">Your reference</span>
        <input className="fld fld--block" value={value.reference} onChange={set("reference")} disabled={disabled}
          placeholder="Your own PO number" /></label>
      <label><span className="fld-label">Supplier</span>
        <input className="fld fld--block" value={value.supplier_id} onChange={set("supplier_id")} disabled={disabled}
          placeholder="Supplier code" /></label>
      <label><span className="fld-label">Deliver to</span>
        {locations.length ? (
          <select className="fld fld--block" value={value.destination_id} onChange={set("destination_id")} disabled={disabled}>
            <option value="">Not set</option>
            {locations.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
        ) : (
          <input className="fld fld--block" value={value.destination_id} onChange={set("destination_id")} disabled={disabled} placeholder="Site" />
        )}
      </label>
      <label><span className="fld-label">Currency</span>
        <input className="fld fld--block" value={value.currency} onChange={set("currency")} disabled={disabled}
          maxLength={3} style={{ textTransform: "uppercase" }} /></label>
      <label><span className="fld-label">Order date</span>
        <input className="fld fld--block" type="date" value={value.requested_order_date} onChange={set("requested_order_date")} disabled={disabled} /></label>
      <label><span className="fld-label">Requested receipt date</span>
        <input className="fld fld--block" type="date" value={value.requested_receipt_date} onChange={set("requested_receipt_date")} disabled={disabled} /></label>
    </div>
  );
}

/** Server-side product search: a catalogue of fifty thousand is never held in the browser. */
function ProductPicker({ onPick, disabled }: { onPick: (row: InventoryRow) => void; disabled?: boolean }) {
  const [term, setTerm] = useState("");
  const [hits, setHits] = useState<InventoryRow[]>([]);
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!term.trim()) { setHits([]); return; }
    let alive = true;
    const handle = window.setTimeout(() => {
      fetchInventory({ q: term.trim(), limit: 8 })
        .then((page) => { if (alive) { setHits(page.rows); setOpen(true); } })
        .catch(() => { if (alive) setHits([]); });
    }, 200);
    return () => { alive = false; window.clearTimeout(handle); };
  }, [term]);

  useEffect(() => {
    const away = (e: MouseEvent) => { if (!box.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("click", away);
    return () => document.removeEventListener("click", away);
  }, []);

  return (
    <div ref={box} style={{ position: "relative", flex: "1 1 280px", minWidth: 0 }}>
      <div style={{ position: "relative" }}>
        <Search size={14} aria-hidden style={{ position: "absolute", insetInlineStart: 9, top: 10, color: "var(--ink-400)" }} />
        <input className="fld fld--block" style={{ paddingInlineStart: 28 }} value={term} disabled={disabled}
          placeholder="Add a product — search code or description"
          aria-label="Search products to add" onFocus={() => hits.length && setOpen(true)}
          onChange={(e) => setTerm(e.target.value)} />
      </div>
      {open && hits.length > 0 && (
        <ul role="listbox" aria-label="Matching products" style={{
          position: "absolute", insetInline: 0, top: "calc(100% + 4px)", zIndex: 30, margin: 0, padding: 4,
          listStyle: "none", background: "var(--surface)", border: "1px solid var(--line)",
          borderRadius: "var(--radius)", boxShadow: "var(--shadow-lg)", maxHeight: 280, overflow: "auto",
        }}>
          {hits.map((row) => (
            <li key={row.sku}>
              <button type="button" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start", height: 38 }}
                onClick={() => { onPick(row); setTerm(""); setHits([]); setOpen(false); }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>
                  <strong style={{ fontWeight: 500 }}>{row.sku_name || row.sku}</strong>
                  <span style={{ color: "var(--ink-400)", marginInlineStart: 6, fontSize: 12 }}>{row.sku}</span>
                </span>
                <span style={{ marginInlineStart: "auto", color: "var(--ink-500)", fontSize: 12 }}>
                  {row.on_hand != null ? `${NUMBER(row.on_hand)} on hand` : "no stock count"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function LineEditor({ lines, onChange, currency, disabled }: {
  lines: DraftLine[]; onChange: (next: DraftLine[]) => void; currency: string; disabled?: boolean;
}) {
  const set = useCallback((index: number, patch: Partial<DraftLine>) => {
    onChange(lines.map((line, i) => (i === index ? { ...line, ...patch } : line)));
  }, [lines, onChange]);

  const total = useMemo(() => {
    let value = 0;
    let complete = true;
    for (const line of lines) {
      if (line.unit_price == null) { complete = false; continue; }
      value += Number(line.quantity || 0) * Number(line.unit_price);
    }
    return { value, complete };
  }, [lines]);

  return (
    <>
      {lines.length > 0 && (
        <div className="tbl-wrap">
          <table className="tbl tbl--dense">
            <caption className="sr-only">Lines on this proposal</caption>
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col" data-align="end">Quantity</th>
                <th scope="col" data-align="end" data-hide="700">Per case</th>
                <th scope="col" data-align="end">Unit price</th>
                <th scope="col" data-align="end" data-hide="900">Line value</th>
                <th scope="col"><span className="sr-only">Remove</span></th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={`${line.sku}-${index}`}>
                  <td title={line.sku}>{line.sku}</td>
                  <td data-align="end">
                    <input className="fld" type="number" min={0} step="any" style={{ width: 110, textAlign: "end" }}
                      aria-label={`Quantity for ${line.sku}`} disabled={disabled}
                      value={Number.isFinite(line.quantity) ? line.quantity : ""}
                      onChange={(e) => set(index, { quantity: Number(e.target.value) })} />
                  </td>
                  <td data-align="end" data-num data-hide="700">{line.units_per_case ? NUMBER(line.units_per_case) : <span className="na">—</span>}</td>
                  <td data-align="end">
                    <input className="fld" type="number" min={0} step="any" style={{ width: 110, textAlign: "end" }}
                      aria-label={`Unit price for ${line.sku}`} disabled={disabled} placeholder="—"
                      value={line.unit_price ?? ""}
                      onChange={(e) => set(index, { unit_price: e.target.value === "" ? null : Number(e.target.value) })} />
                  </td>
                  <td data-align="end" data-num data-hide="900">
                    {line.unit_price != null ? MONEY(Number(line.quantity || 0) * Number(line.unit_price), currency) : <NotAvailable why="No price is declared on this line." />}
                  </td>
                  <td data-align="end">
                    <Button size="sm" role="tertiary" icon={<Trash2 size={14} aria-hidden />} label={`Remove ${line.sku}`}
                      disabled={disabled} onClick={() => onChange(lines.filter((_, i) => i !== index))} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {lines.length > 0 && (
        <p className="tbl-count">
          {lines.length} line{lines.length === 1 ? "" : "s"} · {NUMBER(lines.reduce((a, l) => a + Number(l.quantity || 0), 0))} units
          {total.value > 0 && <> · {MONEY(total.value, currency)}{!total.complete && " for the lines that carry a price"}</>}
        </p>
      )}
      {!disabled && (
        <div className="tbar" style={{ marginTop: 12 }}>
          <ProductPicker disabled={disabled} onPick={(row) => onChange([...lines, {
            sku: row.sku,
            quantity: row.units_per_case ? Number(row.units_per_case) : 1,
            unit_price: row.unit_cost ?? null,
            units_per_case: row.units_per_case ?? null,
          }])} />
          <Button size="sm" role="tertiary" icon={<Plus size={14} aria-hidden />}
            onClick={() => onChange([...lines, { sku: "", quantity: 1, unit_price: null }])}>Blank line</Button>
        </div>
      )}
    </>
  );
}

/** Warnings from the server, shown where they are acted on and never as a blocker. */
export function Warnings({ items }: { items: Array<{ level: string; message: string }> }) {
  if (!items.length) return null;
  return (
    <div className="notice" data-tone="warn" style={{ marginTop: 12 }}>
      <strong>Worth checking before you approve</strong>
      <ul style={{ margin: "6px 0 0", paddingInlineStart: 18 }}>
        {items.map((item, index) => <li key={index}>{item.message}</li>)}
      </ul>
    </div>
  );
}
