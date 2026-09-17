"""Exports of a result: CSV and XLSX with the provenance every number needs to travel with.

The rows are the `ResultSet`'s rows with null cells written as their reason word (never as 0 or
blank); the metadata — generated at, dataset version, data cutoff, filters, time range, metric
definitions, coverage — is written as a second block (CSV: a preamble of `#` lines; XLSX: a
"Data & scope" sheet). Cells go through `exporting.safe_cell`, so a member that begins with `=`
cannot become a formula in someone's spreadsheet.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from api.product.exporting import safe_cell

MAX_EXPORT_ROWS = 10_000


def _cell_text(cell: Any) -> str:
    if isinstance(cell, dict):
        if cell.get("value") is None:
            return str(cell.get("reason") or "UNKNOWN")
        value = cell["value"]
        return f"{value}" + (" (INSUFFICIENT_COVERAGE)" if cell.get("reason") == "INSUFFICIENT_COVERAGE" else "")
    if cell is None:
        return "UNKNOWN"
    return str(cell)


def _metadata_lines(result: dict[str, Any], locale: str = "en") -> list[tuple[str, str]]:
    prov = result.get("provenance") or {}
    lines: list[tuple[str, str]] = [
        ("generated_at", str(result.get("generated_at"))), ("semantic_model_version", str(result.get("semantic_model_version"))),
        ("dataset_version", str((result.get("dataset_version") or {}).get("dataset_version_id"))), ("last_updated", str(prov.get("last_updated"))),
        ("data_cutoff", str(prov.get("data_cutoff"))), ("time_grain", str((prov.get("time") or {}).get("grain"))),
        ("time_range", f"{(prov.get('time') or {}).get('start')} → {(prov.get('time') or {}).get('end')}"),
        ("filters", "; ".join(f"{f['dimension_id']} {f['op']} {', '.join(f['values'])}" for f in prov.get("filters", [])) or "none"),
    ]
    for d in prov.get("definitions", []):
        lines.append((f"metric {d['ref']}", f"{d['display_name'].get(locale) or d['display_name']['en']}: {d['business_definition']} "
                      f"[numerator: {d['numerator']}; denominator: {d['denominator']}; evidence: {d['evidence_class']}]"))
    for metric_id, cov in (result.get("coverage") or {}).items():
        lines.append((f"coverage {metric_id}", f"{cov.get('measure')}: rows={cov.get('rows')} measured_share={cov.get('measured_share')} insufficient={cov.get('insufficient')}"))
    if prov.get("plan"):
        lines.append(("plan", str(prov["plan"])))
    for dim, why in (prov.get("blocked") or {}).items():
        lines.append((f"blocked {dim}", f"{why.get('reason')}: {why.get('why')}"))
    lines.append(("note", "Null cells are written as their reason (UNKNOWN, NOT_MEASURED, NOT_APPLICABLE, NO_DATA, BLOCKED_BY_DATA, NOT_IN_PLAN, INSUFFICIENT_COVERAGE); never as zero."))
    return lines


def _headers(result: dict[str, Any], locale: str) -> list[str]:
    out = []
    for c in result["columns"]:
        label = c.get("label") or {}
        out.append(str(label.get(locale) or label.get("en") or c["id"]))
    return out


def to_csv(result: dict[str, Any], *, locale: str = "en") -> bytes:
    buffer = io.StringIO()
    for key, value in _metadata_lines(result, locale):
        buffer.write(f"# {key}: {value}\n")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow([safe_cell(h) for h in _headers(result, locale)])
    for row in result["rows"][:MAX_EXPORT_ROWS]:
        writer.writerow([safe_cell(_cell_text(c)) for c in row])
    return buffer.getvalue().encode("utf-8-sig")


def to_xlsx(result: dict[str, Any], *, locale: str = "en", title: str = "analysis") -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Result"
    sheet.append([safe_cell(h) for h in _headers(result, locale)])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in result["rows"][:MAX_EXPORT_ROWS]:
        values = []
        for c in row:
            if isinstance(c, dict) and c.get("value") is not None and c.get("reason") != "INSUFFICIENT_COVERAGE":
                values.append(c["value"])
            elif isinstance(c, (int, float)) and not isinstance(c, bool):
                values.append(c)
            else:
                values.append(safe_cell(_cell_text(c)))
        sheet.append(values)
    scope = wb.create_sheet("Data & scope")
    scope.append(["field", "value"])
    for cell in scope[1]:
        cell.font = Font(bold=True)
    for key, value in _metadata_lines(result, locale):
        scope.append([safe_cell(key), safe_cell(value)])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def filename(name: str, fmt: str) -> str:
    import re
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "analysis"
    return f"{stem[:60]}.{fmt}"
