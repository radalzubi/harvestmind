"use client";

/**
 * The table, the drawer and the pager — the three primitives every operational surface uses.
 *
 * Tables became essential the moment ZAAD stopped being four summary pages. Thousands of products
 * and orders are not cards: a buyer scans a column, not a paragraph. So the rules are the boring
 * ones that make a dense table readable — a sticky header, numbers right-aligned with tabular
 * figures, a truncated value that still carries its full text, one row height, and no zebra
 * stripes fighting the hairline borders ZAAD already uses.
 *
 * Three properties every caller gets for free:
 *
 *   * **The server sorts and pages.** `sort` is a column key the server declared; clicking a
 *     header asks the server again. Nothing is sorted in the browser, because the browser only
 *     ever holds one page.
 *   * **A row is a link, and also a button.** Clicking opens the detail beside the list; the same
 *     row is reachable by keyboard with Enter, and the selection lives in the address bar so it
 *     can be sent to a colleague.
 *   * **Wide content scrolls inside the table, never the page.** The body scrolls horizontally on
 *     its own so a narrow screen keeps the rest of the interface where it was.
 */
import { useEffect, useRef, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, X } from "lucide-react";
import { Button } from "./ui";

export interface Column<T> {
  /** The server's own column name when sortable; any stable string otherwise. */
  key: string;
  label: string;
  align?: "start" | "end";
  /** Numbers use tabular figures and align to the end by default. */
  numeric?: boolean;
  sortable?: boolean;
  width?: number | string;
  /** Hidden below this viewport width, so a phone shows the columns that matter. */
  hideBelow?: 1100 | 900 | 700;
  render: (row: T) => ReactNode;
  /** The full value for a cell that may be visually truncated. */
  title?: (row: T) => string | undefined;
}

export function DataTable<T>({
  columns, rows, rowKey, selected, onSelect, sort, direction, onSort, empty, caption, dense,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  selected?: string | null;
  onSelect?: (row: T) => void;
  sort?: string;
  direction?: string;
  onSort?: (key: string) => void;
  empty?: ReactNode;
  /** Describes the table for a screen reader; never shown. */
  caption: string;
  dense?: boolean;
}) {
  if (!rows.length && empty) return <>{empty}</>;
  return (
    <div className="tbl-wrap">
      <table className={dense ? "tbl tbl--dense" : "tbl"}>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => {
              const active = sort === column.key;
              const Arrow = direction === "desc" ? ArrowDown : ArrowUp;
              return (
                <th
                  key={column.key}
                  scope="col"
                  data-align={column.align ?? (column.numeric ? "end" : "start")}
                  data-hide={column.hideBelow}
                  style={column.width ? { width: typeof column.width === "number" ? `${column.width}px` : column.width } : undefined}
                  aria-sort={active ? (direction === "desc" ? "descending" : "ascending") : undefined}
                >
                  {column.sortable && onSort ? (
                    <button type="button" className="tbl-sort" onClick={() => onSort(column.key)}
                      aria-label={`Sort by ${column.label}`}>
                      {column.label}
                      {active && <Arrow size={12} aria-hidden />}
                    </button>
                  ) : column.label}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const key = rowKey(row);
            return (
              <tr
                key={key}
                aria-selected={selected === key ? true : undefined}
                data-selected={selected === key ? "" : undefined}
                tabIndex={onSelect ? 0 : undefined}
                onClick={onSelect ? () => onSelect(row) : undefined}
                onKeyDown={onSelect ? (e) => {
                  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(row); }
                } : undefined}
                className={onSelect ? "tbl-row--clickable" : undefined}
              >
                {columns.map((column) => (
                  <td key={column.key}
                    data-align={column.align ?? (column.numeric ? "end" : "start")}
                    data-num={column.numeric ? "" : undefined}
                    data-hide={column.hideBelow}
                    title={column.title?.(row)}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Offset paging over a server-side total. Always says where you are, never guesses the count. */
export function Pager({ total, limit, offset, onOffset, unit = "rows", one, isFloor }: {
  total: number; limit: number; offset: number; onOffset: (next: number) => void;
  unit?: string; one?: string; isFloor?: boolean;
}) {
  // A filtered list of one used to read "1 proposals". Every unit this takes is a regular plural,
  // so dropping the "s" is right; `one` is there for the day one of them is not.
  const noun = total === 1 ? (one ?? unit.replace(/s$/, "")) : unit;
  if (total <= limit && offset === 0) {
    return <p className="tbl-count">{total.toLocaleString("en-US")} {noun}</p>;
  }
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="tbl-pager">
      <p className="tbl-count">
        {from.toLocaleString("en-US")}–{to.toLocaleString("en-US")} of {isFloor ? "more than " : ""}
        {total.toLocaleString("en-US")} {noun}
      </p>
      <div style={{ display: "flex", gap: 6 }}>
        <Button size="sm" role="tertiary" icon={<ChevronLeft size={15} aria-hidden />} label="Previous page"
          disabled={offset === 0} onClick={() => onOffset(Math.max(0, offset - limit))} />
        <Button size="sm" role="tertiary" icon={<ChevronRight size={15} aria-hidden />} label="Next page"
          disabled={to >= total} onClick={() => onOffset(offset + limit)} />
      </div>
    </div>
  );
}

/**
 * The detail beside the list.
 *
 * A drawer rather than a page, because exploring a catalogue means opening twenty things and
 * losing your place twenty times otherwise. The selection is still in the address bar, so a deep
 * link opens the same thing.
 */
export function Drawer({ open, title, sub, onClose, children, actions, wide }: {
  open: boolean; title: string; sub?: ReactNode; onClose: () => void;
  children: ReactNode; actions?: ReactNode; wide?: boolean;
}) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", escape);
    panel.current?.focus();
    return () => document.removeEventListener("keydown", escape);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <>
      <div className="drw-scrim" onClick={onClose} aria-hidden />
      <aside className={wide ? "drw drw--wide" : "drw"} role="dialog" aria-modal="false" aria-label={title}
        ref={panel} tabIndex={-1}>
        <header className="drw-h">
          <div style={{ minWidth: 0 }}>
            <h2>{title}</h2>
            {sub && <p>{sub}</p>}
          </div>
          <Button size="sm" role="tertiary" icon={<X size={16} aria-hidden />} label="Close" onClick={onClose} />
        </header>
        <div className="drw-b">{children}</div>
        {actions && <footer className="drw-f">{actions}</footer>}
      </aside>
    </>
  );
}

/** The one row of controls above a table: search, filters, then the page's own actions. */
export function Toolbar({ children }: { children: ReactNode }) {
  return <div className="tbar">{children}</div>;
}

export function SearchField({ value, onChange, placeholder, label }: {
  value: string; onChange: (next: string) => void; placeholder: string; label: string;
}) {
  return (
    <input className="fld fld--search" type="search" value={value} placeholder={placeholder}
      aria-label={label} onChange={(e) => onChange(e.target.value)} />
  );
}

export function SelectField({ value, onChange, options, label, all = "All" }: {
  value: string; onChange: (next: string) => void;
  options: Array<{ value: string; label: string }>; label: string; all?: string;
}) {
  return (
    <label className="fld-wrap">
      <span className="sr-only">{label}</span>
      <select className="fld" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        <option value="">{all}</option>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

/** A value the record does not carry. Never a zero, never a dash without meaning. */
export function NotAvailable({ why }: { why?: string }) {
  return <span className="na" title={why}>Not available</span>;
}
