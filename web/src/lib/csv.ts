type Cell = string | number | null | undefined;

/**
 * A cell that starts with = + - @ or a tab / carriage return is a formula to Excel, Sheets and LibreOffice,
 * whatever produced the file. Such a cell is prefixed with an apostrophe (the spreadsheet convention for
 * "this is text") and quoted, so a customer-controlled product or supplier name can never execute
 * (security review 2026-09, SEC-013).
 */
export function escape(v: Cell): string {
  if (v == null) return "";
  let s = String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

export function toCSV<T extends Record<string, Cell>>(
  rows: T[],
  columns: { key: keyof T; label: string }[],
): string {
  const header = columns.map((c) => escape(c.label)).join(",");
  const body = rows
    .map((r) => columns.map((c) => escape(r[c.key])).join(","))
    .join("\n");
  return `${header}\n${body}\n`;
}

export function downloadCSV(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
