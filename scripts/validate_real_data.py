#!/usr/bin/env python3
"""HarvestMind real-data validator.

Validates partner CSV exports without inserting anything. Detects file
schema by name, runs auto_map_columns + row-level checks, and prints
a clear pass/fail report with line numbers.

Usage:
  python scripts/validate_real_data.py --data-dir ~/Downloads/partner/
  python scripts/validate_real_data.py --data-dir ./partner --strict

Exit codes:
  0 — all files valid
  1 — at least one file has errors (or warnings, in --strict mode)
  2 — config error (missing data dir, etc.)
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.column_mapper import auto_map_columns  # noqa: E402  (sys.path set above so the script runs from any cwd)


# ── File-name → target schema ─────────────────────────────────────────────────

def detect_schema(filename: str) -> str | None:
    name = filename.lower()
    # Order matters: order_lines must match before "orders"
    if "lines" in name:
        return "order_lines"
    if "purchase_orders" in name or re.search(r"\bpo\b", name) or "purchase" in name:
        return "purchase_orders"
    if "deliveries" in name or "delivery" in name:
        return "deliveries"
    if "waste" in name or "loss" in name:
        return "waste_events"
    if "orders" in name or "order" in name:
        return "orders"
    return None


# ── Per-row checks ────────────────────────────────────────────────────────────

DATE_COLS = {"order_date", "delivery_date", "week_start", "po_date", "event_date"}
QTY_COLS = {
    "qty_ordered_kg", "qty_delivered_kg", "qty_received_kg",
    "qty_rejected_kg", "qty_committed_kg", "qty_wasted_kg",
}
ID_COLS = {
    "order_id", "buyer_id", "supplier_id", "product_id", "delivery_id",
    "po_id", "waste_id", "line_id",
}

_MIN_DATE = date(2015, 1, 1)
_INJECTION_RE = re.compile(r"['\";]|--")


def _check_row(row: pd.Series, target_schema: str, row_idx: int) -> list[str]:
    errs: list[str] = []
    today = date.today()

    for col in DATE_COLS & set(row.index):
        v = row[col]
        if pd.isna(v) or (isinstance(v, str) and not v.strip()):
            errs.append(f"Row {row_idx}: {col} is empty")
            continue
        try:
            d = pd.to_datetime(v).date()
        except (ValueError, TypeError):
            errs.append(f"Row {row_idx}: {col} ({v!r}) is not a valid date")
            continue
        if d > today + timedelta(days=7):
            errs.append(f"Row {row_idx}: {col} ({d}) is more than 7 days in the future")
        if d < _MIN_DATE:
            errs.append(f"Row {row_idx}: {col} ({d}) is before {_MIN_DATE}")

    for col in QTY_COLS & set(row.index):
        v = row[col]
        if pd.isna(v) or (isinstance(v, str) and not v.strip()):
            errs.append(f"Row {row_idx}: {col} is empty")
            continue
        try:
            n = float(v)
        except (ValueError, TypeError):
            errs.append(f"Row {row_idx}: {col} ({v!r}) is not numeric")
            continue
        if n < 0:
            errs.append(f"Row {row_idx}: {col} ({n}) is negative")
        if n > 100_000:
            errs.append(f"Row {row_idx}: {col} ({n}) is suspiciously large (>100,000)")

    for col in ID_COLS & set(row.index):
        v = row[col]
        if pd.isna(v) or (isinstance(v, str) and not v.strip()):
            errs.append(f"Row {row_idx}: {col} is empty")
            continue
        s = str(v)
        if _INJECTION_RE.search(s):
            errs.append(f"Row {row_idx}: {col} ({s!r}) contains illegal characters")

    # Cross-row: rejected ≤ received
    if "qty_rejected_kg" in row.index and "qty_received_kg" in row.index:
        try:
            rej = float(row["qty_rejected_kg"])
            rec = float(row["qty_received_kg"])
            if rej > rec:
                errs.append(
                    f"Row {row_idx}: qty_rejected_kg ({rej}) > qty_received_kg ({rec})"
                )
        except (ValueError, TypeError):
            pass  # already flagged above as non-numeric

    return errs


# ── Per-file driver ───────────────────────────────────────────────────────────

def validate_file(path: Path) -> tuple[int, int, list[str], list[str]]:
    """Returns (n_rows, n_errors, error_messages, warnings)."""
    schema = detect_schema(path.name)
    if schema is None:
        return 0, 0, [], [f"{path.name}: filename does not match any known schema; skipping"]

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return 0, 0, [], [f"{path.name}: empty file"]
    except Exception as e:
        return 0, 1, [f"{path.name}: failed to read ({type(e).__name__}: {e})"], []

    n_rows = len(df)
    if n_rows == 0:
        return 0, 0, [], [f"{path.name}: 0 rows"]

    renamed, mapping, mapping_warnings = auto_map_columns(df, schema)

    errors: list[str] = []
    for i, row in renamed.iterrows():
        errors.extend(_check_row(row, schema, row_idx=i + 2))  # +2 = header + 1-indexing

    return n_rows, len(errors), errors, mapping_warnings


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", required=True, help="Partner CSV directory")
    p.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    args = p.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.is_dir():
        print(f"[ERROR] data dir not found: {data_dir}", file=sys.stderr)
        sys.exit(2)

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] no CSV files in {data_dir}", file=sys.stderr)
        sys.exit(2)

    print("══════════════════════════════════════════════════")
    print("HarvestMind Real Data Validator")
    print(f"Source: {data_dir}")
    print("══════════════════════════════════════════════════\n")

    any_errors = False
    any_warnings = False

    for csv in csv_files:
        schema = detect_schema(csv.name)
        n_rows, n_errors, errors, warnings = validate_file(csv)
        if schema is None:
            print(f"  ?  {csv.name:<32} skipped (unrecognised schema)")
            continue
        status = "✓" if n_errors == 0 else "✗"
        print(f"  {status}  {csv.name:<32} {n_rows} rows  →  schema='{schema}'  errors={n_errors}")
        for w in warnings:
            print(f"      ⚠ {w}")
            any_warnings = True
        for err in errors[:20]:  # cap on display
            print(f"      ✗ {err}")
        if len(errors) > 20:
            print(f"      ... and {len(errors) - 20} more errors")
        if n_errors > 0:
            any_errors = True

    print()
    if any_errors:
        print("══════════════════════════════════════════════════")
        print(" ✗  VALIDATION FAILED — fix errors before ingestion.")
        print("══════════════════════════════════════════════════")
        sys.exit(1)
    if args.strict and any_warnings:
        print("══════════════════════════════════════════════════")
        print(" ⚠  WARNINGS PRESENT (--strict)")
        print("══════════════════════════════════════════════════")
        sys.exit(1)
    print("══════════════════════════════════════════════════")
    print(" ✓  All files valid. Run ingestion next.")
    print("══════════════════════════════════════════════════")
    sys.exit(0)


if __name__ == "__main__":
    main()
