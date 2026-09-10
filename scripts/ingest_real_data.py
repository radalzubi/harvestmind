#!/usr/bin/env python3
"""HarvestMind real-data ingestion.

Validates a directory of partner CSVs, applies column mapping + unit
conversion + missing-column inference, then loads into harvestmind.duckdb.

Usage:
  python scripts/ingest_real_data.py --data-dir ~/Downloads/partner/ \
      --partner-name "Hoosier Harvest Market"

  python scripts/ingest_real_data.py --data-dir ./partner --dry-run
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.column_mapper import (  # noqa: E402  (sys.path set above so the script runs from any cwd)
    align_to_table_schema,
    auto_map_columns,
    detect_and_convert_units,
    infer_missing_columns,
)
from ingestion.csv_ingestor import ingest_csv  # noqa: E402  (sys.path set above so the script runs from any cwd)

# Reuse validator helpers
from scripts.validate_real_data import detect_schema, validate_file  # noqa: E402  (sys.path set above so the script runs from any cwd)


SCHEMA_TO_TABLE = {
    "orders":          "fact_orders",
    "order_lines":     "fact_order_lines",
    "deliveries":      "fact_deliveries",
    "purchase_orders": "fact_purchase_orders",
    "waste_events":    "fact_waste_events",
}

# Date columns per schema (for ingest_csv's date-parser)
DATE_COLS_BY_SCHEMA = {
    "orders":          ["order_date", "week_start"],
    "order_lines":     ["delivery_date"],
    "deliveries":      ["delivery_date"],
    "purchase_orders": ["po_date", "week_start"],
    "waste_events":    ["event_date"],
}


def _print_header(partner: str, data_dir: Path) -> None:
    print("══════════════════════════════════════════════════")
    print("HarvestMind Real Data Ingestion")
    print(f"Partner: {partner}")
    print(f"Source:  {data_dir}")
    print("══════════════════════════════════════════════════\n")


def _print_data_quality(conn) -> None:
    from dashboard.lib.metrics import data_quality_breakdown
    breakdown = data_quality_breakdown(conn)
    print("\nData quality after ingestion:")
    for r in breakdown:
        glyph = {"Strong": "✓", "Usable with caveats": "⚠",
                 "Weak": "⚠", "Not enough data": "✗"}.get(r.status, "·")
        print(f"  {glyph}  {r.dataset:<28} {r.rows:>6,} rows — {r.status}")


def _check_minimum_requirements(conn) -> list[str]:
    warnings: list[str] = []
    n_orders = conn.execute("SELECT COUNT(*) FROM fact_orders").fetchone()[0]
    n_deliv = conn.execute("SELECT COUNT(*) FROM fact_deliveries").fetchone()[0]
    n_weeks = conn.execute(
        "SELECT COUNT(DISTINCT week_start) FROM fact_orders"
    ).fetchone()[0]

    if n_orders == 0:
        warnings.append("No orders loaded — backtest cannot run.")
    elif n_weeks < 26:
        warnings.append(
            f"Only {n_weeks} weeks of orders. Recommend 26+ weeks "
            f"(6 months) for a meaningful backtest."
        )
    if n_deliv == 0:
        warnings.append("No deliveries loaded — recourse simulator cannot score commitments.")
    return warnings


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", required=True, help="Directory of partner CSVs")
    p.add_argument("--db", default="harvestmind.duckdb", help="DuckDB path")
    p.add_argument("--partner-name", default="Partner", help="Display name for logs")
    p.add_argument("--dry-run", action="store_true", help="Validate + map but do not insert")
    p.add_argument("--verbose", action="store_true", help="Show column mapping decisions")
    args = p.parse_args()

    data_dir = Path(args.data_dir).expanduser().resolve()
    if not data_dir.is_dir():
        print(f"[ERROR] data dir not found: {data_dir}", file=sys.stderr)
        sys.exit(2)

    csv_files = sorted(data_dir.glob("*.csv"))
    if not csv_files:
        print(f"[ERROR] no CSV files in {data_dir}", file=sys.stderr)
        sys.exit(2)

    _print_header(args.partner_name, data_dir)

    # 1) Validate first; bail if errors
    print("Scanning files...")
    plan: list[tuple[Path, str]] = []
    any_errors = False
    for csv in csv_files:
        schema = detect_schema(csv.name)
        n_rows, n_errors, errors, warnings = validate_file(csv)
        if schema is None:
            print(f"  ?  {csv.name:<32} unrecognised schema — skipped")
            continue
        if n_errors > 0:
            print(f"  ✗  {csv.name:<32} {n_rows} rows — {n_errors} ERRORS")
            for e in errors[:10]:
                print(f"      {e}")
            any_errors = True
            continue
        print(f"  ✓  {csv.name:<32} {n_rows} rows — schema OK")
        plan.append((csv, schema))

    if any_errors:
        print("\n✗  Validation failed. Fix errors and re-run.")
        sys.exit(1)

    if not plan:
        print("\n[ERROR] no recognised CSV files in data dir.", file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        print("\n--dry-run: skipping insert. Mapping per file:")
        for csv, schema in plan:
            df = pd.read_csv(csv)
            renamed, mapping, warnings = auto_map_columns(df, schema)
            df_units, conversions = detect_and_convert_units(renamed, df.columns)
            df_inferred, inferences = infer_missing_columns(df_units, schema)
            print(f"  {csv.name} → {schema}")
            for o, t in mapping.items():
                print(f"    {o!r:<28} → {t}")
            for c in conversions:
                print(f"    [unit] {c}")
            for inf in inferences:
                print(f"    [infer] {inf}")
            for w in warnings:
                print(f"    ⚠ {w}")
        sys.exit(0)

    # 2) Real ingest
    print("\nInserting...")
    conn = duckdb.connect(args.db)
    insert_counts: dict[str, int] = {}

    for csv, schema in plan:
        df = pd.read_csv(csv)
        renamed, mapping, mapping_warnings = auto_map_columns(df, schema)
        df_units, conversions = detect_and_convert_units(renamed, df.columns)
        df_inferred, inferences = infer_missing_columns(df_units, schema)

        if args.verbose:
            for o, t in mapping.items():
                print(f"      map  {o!r} → {t}")
            for c in conversions:
                print(f"      unit {c}")
            for i in inferences:
                print(f"      infer {i}")
            for w in mapping_warnings:
                print(f"      ⚠ {w}")

        if df_inferred.empty:
            print(f"  ·  {csv.name}: 0 rows after mapping")
            continue

        target_table = SCHEMA_TO_TABLE[schema]
        df_aligned = align_to_table_schema(conn, target_table, df_inferred)

        # Write to a tmp CSV so we can reuse ingest_csv (DuckDB treats it
        # safely with allowlisted table names + ignore-on-conflict).
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="",
        ) as tmp:
            df_aligned.to_csv(tmp.name, index=False)
            tmp_path = Path(tmp.name)

        try:
            n = ingest_csv(
                tmp_path,
                target_table,
                conn,
                column_map={},  # already renamed
                date_cols=DATE_COLS_BY_SCHEMA.get(schema, []),
                if_exists="ignore",
            )
            insert_counts[target_table] = insert_counts.get(target_table, 0) + n
            print(f"  ✓  {target_table:<24} {n:>6,} rows inserted (from {csv.name})")
        finally:
            tmp_path.unlink(missing_ok=True)

    # 3) Data quality + minimum requirements
    _print_data_quality(conn)

    warnings = _check_minimum_requirements(conn)
    if warnings:
        print("\nMinimum-requirement warnings:")
        for w in warnings:
            print(f"  ⚠ {w}")

    print("\n══════════════════════════════════════════════════")
    print(" Ready. Run a backtest:")
    print("   python scripts/run_backtest.py --db", args.db)
    print(" Or generate a partner pilot summary:")
    print(f"   python scripts/generate_pilot_summary.py "
          f"--partner '{args.partner_name}' --gmv 3000000 --stress-test")
    print("══════════════════════════════════════════════════")

    conn.close()


if __name__ == "__main__":
    main()
