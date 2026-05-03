"""CLI entry point: generate and load pilot synthetic dataset into DuckDB."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb

from scripts.setup_db import setup_db
from synthetic.generator import SyntheticGenerator


def main() -> None:
    db_path = os.getenv("DUCKDB_PATH", "harvestmind.duckdb")
    conn = duckdb.connect(db_path)
    setup_db(conn)

    gen = SyntheticGenerator(n_weeks=104)
    print("Generating synthetic pilot dataset (104 weeks)...")
    counts = gen.generate_all(conn)

    print("\nRows inserted:")
    for table, n in counts.items():
        print(f"  {table:<30} {n:>6}")

    conn.close()
    print(f"\nDone. Database: {db_path}")


if __name__ == "__main__":
    main()
