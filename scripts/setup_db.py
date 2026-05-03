"""Initialize DuckDB schema by running all migrations in order."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "db" / "migrations"
SEEDS_DIR = ROOT / "db" / "seeds"


def setup_db(conn=None, load_seeds: bool = False):
    """Run migrations (and optionally seeds) against `conn`.

    If conn is None, opens a new connection using DUCKDB_PATH env var.
    Returns the connection.
    """
    import duckdb

    if conn is None:
        db_path = os.getenv("DUCKDB_PATH", str(ROOT / "harvestmind.duckdb"))
        conn = duckdb.connect(db_path)

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    for mf in migration_files:
        sql = mf.read_text()
        # DuckDB doesn't support multiple statements in execute(); split on semicolons
        _exec_statements(conn, sql, str(mf.name))

    if load_seeds:
        for sf in sorted(SEEDS_DIR.glob("*.sql")):
            sql = sf.read_text()
            _exec_statements(conn, sql, str(sf.name))

    return conn


def _split_sql(sql: str) -> list[str]:
    """Split a SQL script into individual statements, respecting string literals and -- comments."""
    stmts: list[str] = []
    current: list[str] = []
    in_string = False
    string_char = ""
    i = 0
    n = len(sql)

    while i < n:
        ch = sql[i]

        if in_string:
            current.append(ch)
            if ch == string_char:
                # Escaped quote ('' inside a string)
                if i + 1 < n and sql[i + 1] == string_char:
                    current.append(sql[i + 1])
                    i += 2
                    continue
                in_string = False
        elif ch in ("'", '"'):
            in_string = True
            string_char = ch
            current.append(ch)
        elif ch == "-" and i + 1 < n and sql[i + 1] == "-":
            # Line comment: skip to end of line
            while i < n and sql[i] != "\n":
                i += 1
            continue
        elif ch == ";":
            stmt = "".join(current).strip()
            if stmt:
                stmts.append(stmt)
            current = []
        else:
            current.append(ch)

        i += 1

    # Final statement without trailing semicolon
    last = "".join(current).strip()
    if last:
        stmts.append(last)

    return stmts


def _exec_statements(conn, sql: str, filename: str) -> None:
    """Split SQL on statement-terminating semicolons, ignoring those inside string literals or comments."""
    statements = _split_sql(sql)
    for stmt in statements:
        try:
            conn.execute(stmt)
        except Exception as e:
            # COMMENT ON and some DDL extensions are no-ops in DuckDB — skip gracefully
            if "COMMENT" in stmt.upper() or "not supported" in str(e).lower():
                continue
            raise RuntimeError(f"Error in {filename}:\n{stmt[:120]}\n{e}") from e


if __name__ == "__main__":
    load_seeds = "--seeds" in sys.argv
    conn = setup_db(load_seeds=load_seeds)
    print(f"Schema initialized. Seeds loaded: {load_seeds}")
    conn.close()
