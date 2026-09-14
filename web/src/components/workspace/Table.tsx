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
import { NUMBER, TALLY } from "@/lib/zaad/product";
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

/**
 * Offset paging over a server-side total. Always says where you are, never guesses the count.
 *
 * `shown` is how many rows this page actually rendered, and it is what makes the pager truthful in
 * the two cases arithmetic over `total` gets wrong:
 *
 *   * **Past the end.** A stale bookmark or the back button lands on a page beyond the results.
 *     `offset + 1` then reads past `total`, and one table printed "101–1 of 1 product" under an
 *     empty list saying nothing matched — when the search matched and the page number did not.
 *   * **A floored total.** The data explorer stops counting at 100,000 rows (`COUNT_CEILING`) and
 *     says "more than", but the *rows* keep coming: at offset 150,000 a 371,140-row dataset still
 *     serves a full page. Ending the range at `total` would have read "150,001–100,000", and
 *     disabling Next at the ceiling would have put 271,140 records out of reach of the one control
 *     that reaches them.
 */
export function Pager({ total, limit, offset, onOffset, unit = "rows", one, isFloor, shown }: {
  total: number; limit: number; offset: number; onOffset: (next: number) => void;
  unit?: string; one?: string; isFloor?: boolean; shown?: number;
}) {
  // A filtered list of one used to read "1 proposals". Every unit this takes is a regular plural,
  // so dropping the "s" is right; `one` is there for the day one of them is not.
  const noun = total === 1 ? (one ?? unit.replace(/s$/, "")) : unit;
  const rows = shown ?? Math.max(0, Math.min(limit, total - offset));
  if (!isFloor && total <= limit && offset === 0) {
    return <p className="tbl-count">{total.toLocaleString("en-US")} {noun}</p>;
  }
  if (offset > 0 && rows === 0) {
    return (
      <div className="tbl-pager">
        <p className="tbl-count">
          Page {(Math.floor(offset / limit) + 1).toLocaleString("en-US")} is past the end of{" "}
          {isFloor ? `these ${noun}` : `${total.toLocaleString("en-US")} ${noun}`}. Nothing is
          missing; this link points beyond them.
        </p>
        <Button size="sm" role="secondary" onClick={() => onOffset(0)}>Back to the first page</Button>
      </div>
    );
  }
  const from = offset + 1;
  const to = offset + rows;
  return (
    <div className="tbl-pager">
      <p className="tbl-count">
        {from.toLocaleString("en-US")}–{to.toLocaleString("en-US")} of {isFloor ? "more than " : ""}
        {total.toLocaleString("en-US")} {noun}
      </p>
      <div style={{ display: "flex", gap: 6 }}>
        <Button size="sm" role="tertiary" icon={<ChevronLeft size={15} aria-hidden />} label="Previous page"
          disabled={offset === 0} onClick={() => onOffset(Math.max(0, offset - limit))} />
        {/* A short page is always the last one. An exact total ends the list too — but a *floored*
            total does not, which is why it is not enough on its own: at the explorer's ceiling a
            full page is still a full page and there are more behind it. A last page that happens
            to be exactly full needs the second clause, or Next walks off the end. */}
        <Button size="sm" role="tertiary" icon={<ChevronRight size={15} aria-hidden />} label="Next page"
          disabled={rows < limit || (!isFloor && to >= total)} onClick={() => onOffset(offset + limit)} />
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
  const opener = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    // Where the keyboard was before the drawer took focus. Without putting it back, closing a
    // product in a fifty-row table dropped the caret on <body> and the reader had to tab from the
    // top of the page to get back to where they were.
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const escape = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", escape);
    panel.current?.focus();
    return () => {
      document.removeEventListener("keydown", escape);
      const back = opener.current;
      // The row may have been re-rendered away while the drawer was open; only a node still in the
      // document can take focus, and forcing it on a detached one silently does nothing anyway.
      if (back?.isConnected) back.focus();
      opener.current = null;
    };
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
/**
 * A number that does not exist, and — where there is room to say it — why.
 *
 * In a dense table the reason is a `title`: printing it in every cell would drown the table. On a
 * definition list or a panel, where the whole point is the explanation, pass `shown` and the reason
 * is read without hovering, which is the only way it reaches a phone or a screen reader.
 */
/**
 * A measured count, where zero is an answer and absence is not.
 *
 * `value ? NUMBER(value) : "—"` collapses the two, and every table that wrote it said the same
 * wrong thing: a supplier whose every order has arrived rendered exactly like a supplier ZAAD has
 * never seen an order for, and a product with nothing on the water exactly like one whose inbound
 * ZAAD cannot see. On a workspace where every order is received that is a whole column of dashes
 * claiming ignorance of something the vault states plainly.
 *
 * So zero is a word, `null` is the dash, and the reason for the dash rides along as its title.
 */
export function Tally({ value, none = "none", why }: { value: number | null | undefined; none?: string; why?: string }) {
  const said = TALLY(value, none);
  if (!said.muted) return <>{said.text}</>;
  return <span className="na" title={value == null ? why : undefined}>{said.text}</span>;
}

export function NotAvailable({ why, shown }: { why?: string; shown?: boolean }) {
  if (shown && why) {
    return (
      <span className="na">
        Not available
        <small style={{ display: "block", fontWeight: 400, marginTop: 2, lineHeight: 1.45 }}>{why}</small>
      </span>
    );
  }
  return <span className="na" title={why}>Not available</span>;
}
