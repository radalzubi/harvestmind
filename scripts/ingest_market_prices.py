#!/usr/bin/env python3
"""Pull USDA market prices + food-hub directory and load into the local DB.

Usage:
  USDA_AMS_API_KEY=...   USDA_LOCALFOOD_API_KEY=...  \
      python scripts/ingest_market_prices.py --weeks 52

  python scripts/ingest_market_prices.py --skip-hubs
  python scripts/ingest_market_prices.py --skip-prices

The script is safe to run without API keys — both connectors fall back to
empty DataFrames when a key is unset, so the script reports "0 rows" and
exits 0.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingestion.usda_ams_connector import (
    TARGET_COMMODITIES,
    TARGET_MARKETS,
    fetch_and_store as fetch_prices_and_store,
)
from ingestion.usda_food_hub_directory import (
    DEFAULT_STATES,
    fetch_and_store as fetch_hubs_and_store,
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default="harvestmind.duckdb")
    p.add_argument("--weeks", type=int, default=52, help="Weeks of price history to pull")
    p.add_argument("--skip-prices", action="store_true")
    p.add_argument("--skip-hubs", action="store_true")
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    conn = duckdb.connect(str(db_path))

    print("══════════════════════════════════════════════════")
    print(" HarvestMind — External Data Ingestion")
    print("══════════════════════════════════════════════════")

    # ── USDA AMS prices ─────────────────────────────────────────────────────
    if not args.skip_prices:
        if not os.getenv("USDA_AMS_API_KEY"):
            print("\n  ⚠ USDA_AMS_API_KEY not set — skipping price fetch.")
            n_price_rows = 0
        else:
            print(f"\n  ↪ Pulling MyMarketNews prices "
                  f"({len(TARGET_MARKETS)} markets × {len(TARGET_COMMODITIES)} commodities, "
                  f"last {args.weeks} weeks)...")
            n_price_rows = fetch_prices_and_store(
                conn,
                markets=tuple(TARGET_MARKETS.keys()),
                commodities=TARGET_COMMODITIES,
                weeks_back=args.weeks,
            )

        # Summary
        n_total = conn.execute("SELECT COUNT(*) FROM fact_usda_prices").fetchone()[0]
        n_weeks = conn.execute(
            "SELECT COUNT(DISTINCT date_trunc('week', report_date)) FROM fact_usda_prices"
        ).fetchone()[0]
        n_products = conn.execute(
            "SELECT COUNT(DISTINCT commodity) FROM fact_usda_prices"
        ).fetchone()[0]
        print(f"  ✓ inserted {n_price_rows:,} rows this run "
              f"({n_total:,} total · {n_weeks} weeks · {n_products} commodities)")

    # ── USDA Local Food Portal hubs ────────────────────────────────────────
    if not args.skip_hubs:
        if not os.getenv("USDA_LOCALFOOD_API_KEY"):
            print("\n  ⚠ USDA_LOCALFOOD_API_KEY not set — skipping hub directory fetch.")
            n_hub_rows = 0
        else:
            print(f"\n  ↪ Pulling Local Food Portal hub directory "
                  f"({len(DEFAULT_STATES)} states)...")
            n_hub_rows = fetch_hubs_and_store(conn, states=DEFAULT_STATES)

        n_hub_total = conn.execute(
            "SELECT COUNT(*) FROM dim_prospect_hubs"
        ).fetchone()[0]
        n_hub_in = conn.execute(
            "SELECT COUNT(*) FROM dim_prospect_hubs WHERE state = 'Indiana'"
        ).fetchone()[0]
        print(f"  ✓ inserted {n_hub_rows:,} hubs this run "
              f"({n_hub_total:,} total · {n_hub_in} Indiana)")

    print()
    print("══════════════════════════════════════════════════")
    print(" Next: re-run benchmarks to use live USDA pricing")
    print("   python scripts/validate_against_benchmarks.py")
    print("══════════════════════════════════════════════════")
    conn.close()


if __name__ == "__main__":
    main()
