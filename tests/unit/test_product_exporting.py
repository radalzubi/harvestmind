"""Export and import of an operator's own order formats: the pure functions.

The property these tests exist for is the one a spreadsheet cannot be trusted with: a value that
starts with `=`, `+`, `-` or `@` is a formula to Excel, Sheets and LibreOffice no matter what wrote
the file. Everything ZAAD writes goes through one function, and these tests hold it there.
"""
from __future__ import annotations

import io

import pytest

from api.product.exporting import (
    DEFAULT_COLUMNS, EXPORT_FIELDS, ExportRefused, build_rows, default_profile, filename,
    read_table, read_template_headers, rows_to_lines, safe_cell, suggest_import_mapping,
    suggest_mapping, to_csv, to_pdf, to_xlsx,
)

DRAFT = {
    "draft_id": "draft_abc", "reference": "PO-9001", "revision": 1, "supplier_id": "SUP-001",
    "destination_id": "DC", "currency": "USD", "requested_order_date": "2026-01-05",
    "requested_receipt_date": "2026-02-02", "notes": "trial", "origin": "MANUAL",
    "approved_by": "buyer", "approved_at": "2026-01-06T09:00:00",
    "lines": [
        {"line_no": 1, "sku": "SKU-0001", "sku_name": "Rice 5kg", "quantity": 2400.0,
         "unit_price": 4.5, "units_per_case": 24.0, "requested_receipt_date": None, "notes": None},
        {"line_no": 2, "sku": "SKU-0002", "sku_name": "Oil 1L", "quantity": 600.0,
         "unit_price": None, "units_per_case": None, "requested_receipt_date": "2026-02-09", "notes": "air"},
    ],
}


@pytest.mark.parametrize("value", ["=1+1", "+A1", "-cmd", "@SUM(A1)", "\tstart"])
def test_a_formula_is_never_written_as_one(value):
    assert safe_cell(value).startswith("'")


def test_ordinary_text_and_numbers_are_untouched(t=safe_cell):
    assert t("SKU-0001") == "SKU-0001"
    assert t(2400.0) == "2400"
    assert t(None) == ""


def test_the_built_in_format_writes_one_row_per_line():
    headers, body = build_rows(DRAFT, default_profile())
    assert headers == [c["header"] for c in DEFAULT_COLUMNS]
    assert len(body) == 2
    assert body[0][headers.index("SKU")] == "SKU-0001"
    assert body[0][headers.index("Quantity")] == "2400"
    assert body[1][headers.index("Unit Price")] == "", "a price nobody declared is blank, never zero"


def test_a_line_date_overrides_the_order_date():
    headers, body = build_rows(DRAFT, default_profile())
    column = headers.index("Need By Date")
    assert body[0][column] == "2026-02-02"
    assert body[1][column] == "2026-02-09"


def test_a_company_format_maps_and_constants():
    profile = {**default_profile(), "date_format": "dmy", "columns": [
        {"header": "PO_NUM", "field": "po_number"}, {"header": "ITEM", "field": "sku"},
        {"header": "CASES", "field": "cases"}, {"header": "ORG", "constant": "JOR01"}]}
    headers, body = build_rows(DRAFT, profile)
    assert headers == ["PO_NUM", "ITEM", "CASES", "ORG"]
    assert body[0] == ["PO-9001", "SKU-0001", "100", "JOR01"]
    assert body[1][2] == "", "cases needs a declared pack size; it is not invented"


def test_every_declared_field_resolves():
    profile = {**default_profile(),
               "columns": [{"header": name, "field": name} for name in sorted(EXPORT_FIELDS)]}
    headers, body = build_rows(DRAFT, profile)
    assert len(headers) == len(EXPORT_FIELDS) and len(body[0]) == len(EXPORT_FIELDS)


def test_csv_xlsx_and_pdf_are_all_produced():
    csv_bytes = to_csv(DRAFT, default_profile())
    assert csv_bytes.startswith(b"\xef\xbb\xbf"), "a BOM, so Excel reads UTF-8 without being asked"
    assert b"SKU-0001" in csv_bytes
    xlsx = to_xlsx(DRAFT, default_profile())
    assert xlsx[:2] == b"PK", "an xlsx is a zip"
    pdf = to_pdf(DRAFT, default_profile(), workspace="Test workspace")
    assert pdf[:5] == b"%PDF-"


def test_the_file_name_comes_from_the_template_and_is_safe():
    profile = {**default_profile(), "filename_template": "{reference} / {supplier} {date}"}
    assert filename(DRAFT, profile) == "PO-9001_SUP-001_20260105"
    assert "/" not in filename({**DRAFT, "reference": "../../etc/passwd"}, profile)


def test_reading_a_template_takes_the_headings_only():
    found = read_template_headers(b"PO Number,Vendor,Item,Quantity\n=EVIL(),1,2,3\n", "t.csv")
    assert found["headers"] == ["PO Number", "Vendor", "Item", "Quantity"]
    suggested = {c["header"]: c["field"] for c in suggest_mapping(found["headers"])}
    assert suggested == {"PO Number": "po_number", "Vendor": "supplier_id",
                         "Item": "sku", "Quantity": "quantity"}


def test_an_empty_or_headingless_template_is_refused():
    with pytest.raises(ExportRefused):
        read_template_headers(b"\n", "t.csv")
    with pytest.raises(ExportRefused):
        read_template_headers(b"x", "t.docx")


def test_a_template_larger_than_the_bound_is_refused():
    with pytest.raises(ExportRefused):
        read_template_headers(b"a" * (3 * 1024 * 1024), "t.csv")


def test_an_uploaded_order_is_read_row_by_row():
    content = b"Item Code,Order Qty,Unit Price,Required Date\nSKU-1,600,4.10,2026-02-10\nSKU-2,oops,,\n,,,\n"
    table = read_table(content, "p.csv")
    mapping = suggest_import_mapping(table["headers"])
    lines, order, problems = rows_to_lines(table["headers"], table["rows"], mapping)
    assert [line["sku"] for line in lines] == ["SKU-1"]
    assert lines[0]["unit_price"] == 4.10 and lines[0]["requested_receipt_date"] == "2026-02-10"
    assert any("Row 3" in p and "oops" in p for p in problems)
    assert order == {}


def test_an_upload_must_name_a_product_and_a_quantity():
    with pytest.raises(ExportRefused):
        rows_to_lines(["A", "B"], [["1", "2"]], {"unit_price": "A"})


def test_a_mapping_cannot_name_a_field_zaad_does_not_hold():
    with pytest.raises(ExportRefused):
        rows_to_lines(["A"], [["1"]], {"margin": "A"})


def test_a_mapping_cannot_name_a_column_the_file_does_not_have():
    with pytest.raises(ExportRefused):
        rows_to_lines(["A"], [["1"]], {"sku": "A", "quantity": "Nope"})


def test_an_xlsx_upload_is_read_without_evaluating_it():
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.append(["Item", "Qty"])
    sheet.append(["SKU-7", 42])
    buffer = io.BytesIO()
    book.save(buffer)
    table = read_table(buffer.getvalue(), "order.xlsx")
    assert table["headers"] == ["Item", "Qty"]
    lines, _order, problems = rows_to_lines(table["headers"], table["rows"],
                                            {"sku": "Item", "quantity": "Qty"})
    assert lines == [{"sku": "SKU-7", "quantity": 42.0, "unit_price": None, "units_per_case": None,
                      "requested_receipt_date": None, "notes": None}]
    assert problems == []


# ── the printable order has to fit the page ───────────────────────────────────

def test_the_printable_order_fits_the_page_it_is_printed_on():
    """The twelve columns of the standard format ran off the right edge of A4 portrait.

    reportlab does not complain when a table is wider than its frame — it clips it. So the one
    output a person is meant to print, sign and send lost the unit price to "1.01" and the currency
    column entirely. The page turns sideways for a wide format, and the columns are measured and
    scaled so every one of them is on it.
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm

    from api.product.exporting import PDF_LANDSCAPE_COLUMNS, pdf_column_widths

    headers, body = build_rows(DRAFT, default_profile())
    assert len(headers) > PDF_LANDSCAPE_COLUMNS, "the standard format is the wide case"
    frame = landscape(A4)[0] - 36 * mm
    widths = pdf_column_widths(headers, body, frame)
    assert len(widths) == len(headers)
    assert sum(widths) <= frame + 0.5
    assert all(w > 0 for w in widths)


def test_a_narrow_format_keeps_its_natural_widths():
    """Nothing is stretched or squeezed when it already fits."""
    from api.product.exporting import pdf_column_widths

    widths = pdf_column_widths(["A", "B"], [["x", "y"]], 500.0)
    assert sum(widths) < 500.0


def test_columns_too_numerous_for_any_minimum_still_fit():
    """Fitting the page wins over per-column comfort: cells wrap, they do not fall off the edge."""
    from api.product.exporting import pdf_column_widths

    headers = [f"Column {i}" for i in range(40)]
    widths = pdf_column_widths(headers, [[f"value {i}" for i in range(40)]], 600.0)
    assert sum(widths) <= 600.5


def test_no_columns_is_no_widths():
    from api.product.exporting import pdf_column_widths

    assert pdf_column_widths([], [], 500.0) == []


def test_a_cell_containing_markup_does_not_become_markup_in_the_pdf():
    """Cells are paragraphs now so they wrap; a paragraph parses XML, so cells are escaped."""
    draft = {**DRAFT, "lines": [{**DRAFT["lines"][0], "sku_name": "<b>Rice</b> & 5kg"}]}
    out = to_pdf(draft, default_profile(), workspace="op_1")
    assert out[:5] == b"%PDF-"
    assert len(out) > 800
