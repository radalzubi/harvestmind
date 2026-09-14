"""Writing an approved order out in the shape the operator's own system expects.

Export is the last mile of this release. ZAAD recommends, a person approves, and the workspace
produces a file the buyer puts into their ERP or sends to their supplier themselves. **Exporting is
not transmitting** — nothing in this module contacts a supplier, an ERP or any network at all — and
the interface says so wherever a file is produced.

The value is the mapping. Every distributor's import template is different, so a workspace defines
its own: which column carries the PO number, what the date format is, what fixed values every row
needs. The mapping is deterministic and stored; a spreadsheet is never handed to a model to
interpret.

Two safety properties this file is responsible for:

  * **No formula ever leaves here.** A value that begins with `=`, `+`, `-` or `@` is a formula to
    Excel, Sheets and LibreOffice regardless of what produced the file. Every text cell is written
    as text and prefixed when it would otherwise be interpreted. This is the CSV/XLSX injection
    class, and it is closed at the point of writing, not at the point of reading.
  * **Bounded input.** Reading an operator's template reads headers and nothing else: bounded
    bytes, bounded sheets, bounded columns, bounded cell length. Formulas in an uploaded workbook
    are read as their cached text, never evaluated.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Any, Callable

FORMATS = ("csv", "xlsx", "print")

#: A cell that starts with one of these is a formula to every spreadsheet application.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")

MAX_TEMPLATE_BYTES = 2 * 1024 * 1024
MAX_TEMPLATE_COLUMNS = 200
MAX_TEMPLATE_SHEETS = 20
MAX_CELL_CHARS = 500


class ExportRefused(ValueError):
    """The file cannot be produced as asked."""


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="minutes")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def safe_cell(value: Any) -> str:
    """The one function that decides what reaches a spreadsheet. Never bypass it."""
    out = _text(value)
    if out[:1] in _FORMULA_START:
        return "'" + out
    return out[:MAX_CELL_CHARS]


_DATE_STYLES = {"iso": "%Y-%m-%d", "dmy": "%d/%m/%Y", "mdy": "%m/%d/%Y", "compact": "%Y%m%d"}


def _fmt_date(value: Any, style: str) -> str:
    if value in (None, ""):
        return ""
    try:
        day = value if isinstance(value, date) and not isinstance(value, datetime) else \
            datetime.fromisoformat(str(value)[:19]).date()
    except ValueError:
        return _text(value)
    return day.strftime(_DATE_STYLES.get(style, _DATE_STYLES["iso"]))


def _fmt_number(value: Any, style: str) -> str:
    if value in (None, ""):
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    if style == "grouped":
        return f"{number:,.2f}" if number % 1 else f"{number:,.0f}"
    return f"{number:.2f}" if number % 1 else f"{number:.0f}"


#: The vocabulary a mapping may name. Anything outside it is refused when the profile is saved, so
#: an export can never be asked for a field the product does not hold.
EXPORT_FIELDS: dict[str, str] = {
    "po_number": "PO number (your reference, or the ZAAD id when you have not set one)",
    "zaad_id": "ZAAD proposal id",
    "revision": "Revision",
    "supplier_id": "Supplier code",
    "supplier_name": "Supplier name",
    "destination_id": "Deliver to",
    "currency": "Currency",
    "order_date": "Order date",
    "need_by_date": "Requested receipt date",
    "line_no": "Line number",
    "sku": "Product code",
    "sku_name": "Product description",
    "quantity": "Quantity (units)",
    "units_per_case": "Units per case",
    "cases": "Cases (quantity ÷ units per case, when both are known)",
    "unit_price": "Unit price",
    "line_value": "Line value (quantity × unit price, when a price is declared)",
    "uom": "Unit of measure",
    "notes": "Order notes",
    "line_notes": "Line notes",
    "source_po_id": "Order this amends",
    "amendment_action": "Amendment (keep, defer, expedite, reduce, cancel, split)",
    "approved_by": "Approved by",
    "approved_at": "Approved at",
    "origin": "Where the proposal came from",
}

DEFAULT_COLUMNS = [
    {"header": "PO Number", "field": "po_number"},
    {"header": "Supplier", "field": "supplier_id"},
    {"header": "Deliver To", "field": "destination_id"},
    {"header": "Order Date", "field": "order_date"},
    {"header": "Need By Date", "field": "need_by_date"},
    {"header": "Line", "field": "line_no"},
    {"header": "SKU", "field": "sku"},
    {"header": "Description", "field": "sku_name"},
    {"header": "Quantity", "field": "quantity"},
    {"header": "UOM", "field": "uom"},
    {"header": "Unit Price", "field": "unit_price"},
    {"header": "Currency", "field": "currency"},
]


def default_profile() -> dict[str, Any]:
    """What a workspace exports before it has defined anything of its own."""
    return {"profile_id": None, "name": "ZAAD standard order", "format": "csv", "sheet_name": "Purchase Order",
            "delimiter": ",", "date_format": "iso", "number_format": "plain",
            "filename_template": "{reference}_{supplier}_{date}", "supplier_id": None,
            "columns": DEFAULT_COLUMNS, "built_in": True}


def _resolvers(head: dict[str, Any], names: dict[str, str], profile: dict[str, Any]) -> dict[str, Callable[[dict[str, Any]], Any]]:
    date_style = str(profile.get("date_format") or "iso")
    number_style = str(profile.get("number_format") or "plain")

    def order_value(key: str) -> Any:
        return head.get(key)

    def cases(line: dict[str, Any]) -> Any:
        pack = line.get("units_per_case")
        if not pack:
            return ""
        try:
            return _fmt_number(float(line.get("quantity") or 0) / float(pack), number_style)
        except (TypeError, ValueError, ZeroDivisionError):
            return ""

    def line_value(line: dict[str, Any]) -> Any:
        price = line.get("unit_price")
        if price is None:
            return ""
        return _fmt_number(float(line.get("quantity") or 0) * float(price), number_style)

    return {
        "po_number": lambda _l: order_value("reference") or head.get("draft_id"),
        "zaad_id": lambda _l: head.get("draft_id"),
        "revision": lambda _l: head.get("revision"),
        "supplier_id": lambda _l: order_value("supplier_id"),
        "supplier_name": lambda _l: names.get(str(head.get("supplier_id") or ""), ""),
        "destination_id": lambda _l: order_value("destination_id"),
        "currency": lambda _l: order_value("currency"),
        "order_date": lambda _l: _fmt_date(head.get("requested_order_date"), date_style),
        "need_by_date": lambda line: _fmt_date(line.get("requested_receipt_date")
                                               or head.get("requested_receipt_date"), date_style),
        "line_no": lambda line: line.get("line_no"),
        "sku": lambda line: line.get("sku"),
        "sku_name": lambda line: line.get("sku_name", ""),
        "quantity": lambda line: _fmt_number(line.get("quantity"), number_style),
        "units_per_case": lambda line: _fmt_number(line.get("units_per_case"), number_style),
        "cases": cases,
        "unit_price": lambda line: _fmt_number(line.get("unit_price"), number_style),
        "line_value": line_value,
        "uom": lambda _l: "EACH",
        "notes": lambda _l: order_value("notes"),
        "line_notes": lambda line: line.get("notes"),
        "source_po_id": lambda _l: order_value("source_po_id"),
        "amendment_action": lambda _l: order_value("amendment_action"),
        "approved_by": lambda _l: order_value("approved_by"),
        "approved_at": lambda _l: _fmt_date(head.get("approved_at"), date_style),
        "origin": lambda _l: order_value("origin"),
    }


def build_rows(draft: dict[str, Any], profile: dict[str, Any], *, supplier_names: dict[str, str] | None = None
               ) -> tuple[list[str], list[list[str]]]:
    """The header row and the body, one row per order line, in the profile's column order."""
    columns = list(profile.get("columns") or DEFAULT_COLUMNS)
    resolvers = _resolvers(draft, supplier_names or {}, profile)
    headers = [str(c.get("header") or "") for c in columns]
    body: list[list[str]] = []
    for line in draft.get("lines") or []:
        row: list[str] = []
        for column in columns:
            field = column.get("field")
            if field:
                resolve = resolvers.get(field)
                row.append(safe_cell(resolve(line) if resolve else ""))
            else:
                row.append(safe_cell(column.get("constant")))
        body.append(row)
    return headers, body


def to_csv(draft: dict[str, Any], profile: dict[str, Any], *, supplier_names: dict[str, str] | None = None) -> bytes:
    headers, body = build_rows(draft, profile, supplier_names=supplier_names)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=(str(profile.get("delimiter") or ",")[:1] or ","),
                        lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    writer.writerows(body)
    return buffer.getvalue().encode("utf-8-sig")


def to_xlsx(draft: dict[str, Any], profile: dict[str, Any], *, supplier_names: dict[str, str] | None = None) -> bytes:
    """One sheet, header row, one row per line. Every cell is written as text through `safe_cell`."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers, body = build_rows(draft, profile, supplier_names=supplier_names)
    book = Workbook()
    sheet = book.active
    sheet.title = re.sub(r"[\\/*?:\[\]]", " ", str(profile.get("sheet_name") or "Purchase Order"))[:31]
    sheet.append([safe_cell(h) for h in headers])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.data_type = "s"
    for row in body:
        sheet.append(row)
        for cell in sheet[sheet.max_row]:
            cell.data_type = "s"  # never let a value be re-typed as a formula or a date
    for index, header in enumerate(headers, start=1):
        width = max(len(str(header)), *(len(str(r[index - 1])) for r in body)) if body else len(str(header))
        sheet.column_dimensions[sheet.cell(row=1, column=index).column_letter].width = min(40, max(10, width + 2))
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


def to_pdf(draft: dict[str, Any], profile: dict[str, Any], *, supplier_names: dict[str, str] | None = None,
           workspace: str = "") -> bytes:
    """A printable order a person can read, sign and send themselves."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    headers, body = build_rows(draft, profile, supplier_names=supplier_names)
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title="Purchase order")
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.5, leading=11,
                           textColor=colors.HexColor("#5A5A55"))
    story: list[Any] = [
        Paragraph(f"<b>Purchase order</b> {safe_cell(draft.get('reference') or draft.get('draft_id'))}", styles["Title"]),
        Paragraph(" · ".join(x for x in [
            workspace,
            f"Supplier {safe_cell(draft.get('supplier_id'))}" if draft.get("supplier_id") else "",
            f"Deliver to {safe_cell(draft.get('destination_id'))}" if draft.get("destination_id") else "",
            f"Revision {draft.get('revision')}" if draft.get("revision") else "",
        ] if x), small),
        Spacer(1, 8),
    ]
    table = Table([headers, *body], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2EE")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1A1A18")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E2DC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))
    if draft.get("notes"):
        story.append(Paragraph(safe_cell(draft["notes"]), small))
        story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This document was produced by ZAAD for the operator to place themselves. ZAAD has not sent it "
        "to the supplier and does not place orders.", small))
    doc.build(story)
    return out.getvalue()


def render(draft: dict[str, Any], profile: dict[str, Any], *, supplier_names: dict[str, str] | None = None,
           workspace: str = "") -> tuple[bytes, str, str]:
    """(bytes, media type, filename) for the requested format."""
    fmt = str(profile.get("format") or "csv").lower()
    if fmt not in FORMATS:
        raise ExportRefused(f"{fmt!r} is not a format ZAAD writes.")
    name = filename(draft, profile)
    if fmt == "csv":
        return to_csv(draft, profile, supplier_names=supplier_names), "text/csv; charset=utf-8", f"{name}.csv"
    if fmt == "xlsx":
        return (to_xlsx(draft, profile, supplier_names=supplier_names),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{name}.xlsx")
    return to_pdf(draft, profile, supplier_names=supplier_names, workspace=workspace), "application/pdf", f"{name}.pdf"


_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def filename(draft: dict[str, Any], profile: dict[str, Any]) -> str:
    """A file name from the profile's template, reduced to characters every system accepts."""
    template = str(profile.get("filename_template") or "{reference}_{supplier}_{date}")
    values = {
        "reference": str(draft.get("reference") or draft.get("draft_id") or "order"),
        "supplier": str(draft.get("supplier_id") or "supplier"),
        "date": _fmt_date(draft.get("requested_order_date") or datetime.now().date(), "compact"),
        "revision": str(draft.get("revision") or 1),
        "id": str(draft.get("draft_id") or "order"),
    }
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", value)
    out = _UNSAFE_NAME.sub("_", out).strip("._-")
    return (out or "purchase_order")[:120]


# ── reading an operator's own import template ─────────────────────────────────

def read_template_headers(content: bytes, filename_hint: str) -> dict[str, Any]:
    """The column headings of an uploaded CSV or XLSX, so a person can map them by hand.

    Only the header row is read. No cell is evaluated, no macro is run, and the file is never sent
    anywhere: the mapping a buyer builds from this is stored as data and applied deterministically.
    """
    if len(content) > MAX_TEMPLATE_BYTES:
        raise ExportRefused(f"That file is larger than {MAX_TEMPLATE_BYTES // (1024 * 1024)} MB. "
                            "A template only needs its heading row.")
    lower = (filename_hint or "").lower()
    if lower.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            book = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001 - a workbook we cannot open is a user-facing message
            raise ExportRefused("That workbook could not be read. Save it as .xlsx or .csv and try again.") from exc
        if len(book.sheetnames) > MAX_TEMPLATE_SHEETS:
            raise ExportRefused(f"That workbook has {len(book.sheetnames)} sheets; at most {MAX_TEMPLATE_SHEETS} are read.")
        sheet = book[book.sheetnames[0]]
        headers: list[str] = []
        for row in sheet.iter_rows(min_row=1, max_row=1, values_only=True):
            headers = [str(v).strip() for v in row[:MAX_TEMPLATE_COLUMNS] if v is not None and str(v).strip()]
            break
        book.close()
        if not headers:
            raise ExportRefused("The first row of that sheet is empty, so there are no column headings to map.")
        return {"headers": headers, "sheets": book.sheetnames, "format": "xlsx"}
    if lower.endswith(".csv") or lower.endswith(".txt") or not lower:
        text = content.decode("utf-8-sig", errors="replace")
        first = text.splitlines()[0] if text.splitlines() else ""
        if not first.strip():
            raise ExportRefused("The first line of that file is empty, so there are no column headings to map.")
        try:
            delimiter = csv.Sniffer().sniff(first, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        headers = [h.strip() for h in next(csv.reader([first], delimiter=delimiter)) if h.strip()]
        if len(headers) > MAX_TEMPLATE_COLUMNS:
            raise ExportRefused(f"That file has {len(headers)} columns; at most {MAX_TEMPLATE_COLUMNS} are read.")
        return {"headers": headers, "delimiter": delimiter, "format": "csv"}
    raise ExportRefused("ZAAD reads a .csv or .xlsx template.")


#: Header text ZAAD recognises without being told, as a starting point for a mapping the operator
#: then confirms. A suggestion is never applied on its own.
_SUGGESTIONS: dict[str, tuple[str, ...]] = {
    "po_number": ("po", "po number", "po no", "purchase order", "order number", "order no", "document number"),
    "supplier_id": ("supplier", "supplier code", "vendor", "vendor code", "vendor no", "supplier no"),
    "supplier_name": ("supplier name", "vendor name"),
    "destination_id": ("deliver to", "ship to", "destination", "warehouse", "site", "location"),
    "order_date": ("order date", "po date", "document date", "created"),
    "need_by_date": ("need by", "need by date", "required date", "delivery date", "requested date", "eta"),
    "line_no": ("line", "line no", "line number", "item no", "seq"),
    "sku": ("sku", "item", "item code", "product", "product code", "material", "article"),
    "sku_name": ("description", "item name", "product name", "material description"),
    "quantity": ("qty", "quantity", "order qty", "quantity ordered", "units"),
    "units_per_case": ("units per case", "case pack", "pack size"),
    "cases": ("cases", "case qty", "cartons"),
    "unit_price": ("price", "unit price", "unit cost", "net price"),
    "line_value": ("amount", "line total", "value", "net amount"),
    "uom": ("uom", "unit", "unit of measure"),
    "currency": ("currency", "curr", "ccy"),
    "notes": ("notes", "comment", "remarks", "header text"),
}


def suggest_mapping(headers: list[str]) -> list[dict[str, Any]]:
    """A first guess at each column, for the operator to confirm or change. Never applied silently."""
    out: list[dict[str, Any]] = []
    for header in headers:
        key = re.sub(r"[^a-z0-9 ]+", " ", header.lower()).strip()
        key = re.sub(r"\s+", " ", key)
        field = None
        for candidate, aliases in _SUGGESTIONS.items():
            if key in aliases:
                field = candidate
                break
        if field is None:
            for candidate, aliases in _SUGGESTIONS.items():
                if any(key.startswith(a) or a in key for a in aliases):
                    field = candidate
                    break
        out.append({"header": header, "field": field, "constant": None})
    return out


# ── reading a proposed order a buyer has in a spreadsheet ─────────────────────

MAX_IMPORT_ROWS = 2000

#: The fields a proposed-order upload can fill. A narrower vocabulary than the export mapping:
#: an upload supplies lines and the order's identity, never an approval or an export record.
IMPORT_FIELDS: dict[str, str] = {
    "sku": "Product code (required)",
    "quantity": "Quantity in units (required)",
    "unit_price": "Unit price",
    "units_per_case": "Units per case",
    "need_by_date": "Requested receipt date",
    "supplier_id": "Supplier code",
    "destination_id": "Deliver to",
    "po_number": "Your own order reference",
    "line_notes": "Line notes",
}


def read_table(content: bytes, filename_hint: str, *, limit: int = MAX_IMPORT_ROWS) -> dict[str, Any]:
    """Headers and bounded rows from a CSV or XLSX a buyer uploads.

    Values are read as text. A cell that holds a formula is read as its cached result, never
    evaluated, and no macro in an uploaded workbook is run: openpyxl does not execute either.
    """
    if len(content) > MAX_TEMPLATE_BYTES * 4:
        raise ExportRefused("That file is larger than 8 MB. Split it, or upload the order lines only.")
    lower = (filename_hint or "").lower()
    rows: list[list[str]] = []
    if lower.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook
        try:
            book = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001
            raise ExportRefused("That workbook could not be read. Save it as .xlsx or .csv and try again.") from exc
        sheet = book[book.sheetnames[0]]
        for record in sheet.iter_rows(max_row=limit + 1, max_col=MAX_TEMPLATE_COLUMNS, values_only=True):
            rows.append(["" if v is None else _text(v)[:MAX_CELL_CHARS] for v in record])
        book.close()
    else:
        text = content.decode("utf-8-sig", errors="replace")
        lines = text.splitlines()
        if not lines:
            raise ExportRefused("That file is empty.")
        try:
            delimiter = csv.Sniffer().sniff(lines[0], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
        for record in csv.reader(lines[: limit + 1], delimiter=delimiter):
            rows.append([str(v).strip()[:MAX_CELL_CHARS] for v in record[:MAX_TEMPLATE_COLUMNS]])
    if not rows:
        raise ExportRefused("That file has no rows.")
    headers = [h.strip() for h in rows[0]]
    while headers and not headers[-1]:
        headers.pop()  # a sheet reports its declared width; trailing blanks are not columns
    if not headers:
        raise ExportRefused("The first row has no column headings, so ZAAD cannot tell what the columns mean.")
    width = len(headers)
    body = [list(r[:width]) + [""] * max(0, width - len(r))
            for r in rows[1:] if any(str(c).strip() for c in r[:width])]
    return {"headers": headers, "rows": body[:limit], "truncated": len(rows) - 1 > limit}


def rows_to_lines(headers: list[str], rows: list[list[str]], mapping: dict[str, str]
                  ) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """Apply a confirmed mapping to uploaded rows. Returns (lines, order fields, problems).

    A row ZAAD cannot read is reported by its row number and left out; it is never guessed at and
    never silently dropped. The caller shows the problems before anything is stored.
    """
    unknown = [f for f in mapping if f not in IMPORT_FIELDS]
    if unknown:
        raise ExportRefused(f"ZAAD does not hold {', '.join(sorted(unknown))}. "
                            f"Map to one of: {', '.join(sorted(IMPORT_FIELDS))}.")
    index = {h: i for i, h in enumerate(headers)}
    for field, header in mapping.items():
        if header not in index:
            raise ExportRefused(f"The file has no column called {header!r} (mapped to {field}).")
    if "sku" not in mapping or "quantity" not in mapping:
        raise ExportRefused("A proposed order needs at least a product column and a quantity column.")

    def cell(row: list[str], field: str) -> str:
        header = mapping.get(field)
        if header is None:
            return ""
        position = index[header]
        return str(row[position]).strip() if position < len(row) else ""

    lines: list[dict[str, Any]] = []
    problems: list[str] = []
    order: dict[str, Any] = {}
    for number, row in enumerate(rows, start=2):
        sku = cell(row, "sku")
        raw_quantity = cell(row, "quantity").replace(",", "")
        if not sku and not raw_quantity:
            continue
        if not sku:
            problems.append(f"Row {number}: no product code.")
            continue
        try:
            quantity = float(raw_quantity)
        except ValueError:
            problems.append(f"Row {number} ({sku}): {raw_quantity!r} is not a quantity.")
            continue
        if quantity <= 0:
            problems.append(f"Row {number} ({sku}): quantity {raw_quantity} is not more than zero.")
            continue

        def maybe_number(field: str, row: list[str] = row, number: int = number, sku: str = sku) -> float | None:
            raw = cell(row, field).replace(",", "")
            if not raw:
                return None
            try:
                return float(raw)
            except ValueError:
                problems.append(f"Row {number} ({sku}): {raw!r} is not a number for {field.replace('_', ' ')}.")
                return None

        lines.append({"sku": sku, "quantity": quantity, "unit_price": maybe_number("unit_price"),
                      "units_per_case": maybe_number("units_per_case"),
                      "requested_receipt_date": cell(row, "need_by_date") or None,
                      "notes": cell(row, "line_notes") or None})
        for field, key in (("supplier_id", "supplier_id"), ("destination_id", "destination_id"),
                           ("po_number", "reference")):
            value = cell(row, field)
            if value and key not in order:
                order[key] = value
    if not lines:
        problems.append("No usable order lines were found in that file.")
    return lines, order, problems


def suggest_import_mapping(headers: list[str]) -> dict[str, str]:
    """A first guess at which uploaded column is which, for the buyer to confirm."""
    guessed = suggest_mapping(headers)
    out: dict[str, str] = {}
    for column in guessed:
        field = column.get("field")
        if field == "po_number":
            field = "po_number"
        if field in IMPORT_FIELDS and field not in out:
            out[field] = column["header"]
    return out
