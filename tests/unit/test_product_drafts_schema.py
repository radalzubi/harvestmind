"""The product's own tables, created on a vault that predates migration 023.

Per-operator vaults are migrated by `scripts/setup_db.py`, but a workspace created before this
release meets Purchase orders before it meets the migration runner, so `ensure_tables` is the
fallback that must work. It did not: the migration file carries `COMMENT ON ... IS '...;...'`
strings and `--` comments containing semicolons, and splitting the file on `";"` cut statements in
half. Every half failed to parse, every failure was swallowed, and the vault ended up with one of
the six tables and a raw DuckDB catalogue error — a 500 — on the first page load.

These tests pin the splitter and the outcome, not the implementation: after `ensure_tables`, every
product table exists, and a vault it cannot prepare is refused in words rather than crashing.
"""
from __future__ import annotations

import duckdb
import pytest

from api.product.drafts import PRODUCT_TABLES, DraftRefused, ensure_tables, list_profiles, statements


def test_semicolon_inside_a_quoted_string_does_not_end_a_statement():
    sql = "CREATE TABLE t (a INT);\nCOMMENT ON TABLE t IS 'one; two; three';\nCREATE TABLE u (b INT);"
    out = statements(sql)
    assert len(out) == 3
    assert out[1] == "COMMENT ON TABLE t IS 'one; two; three'"


def test_semicolon_inside_a_line_comment_does_not_end_a_statement():
    sql = "CREATE TABLE t (\n  a INT  -- the id; never null\n);\nCREATE TABLE u (b INT);"
    out = statements(sql)
    assert len(out) == 2
    assert out[0].startswith("CREATE TABLE t")
    assert "never null" not in out[0]  # the comment is dropped, not carried into the statement


def test_an_escaped_quote_does_not_open_a_string():
    sql = "COMMENT ON TABLE t IS 'it''s fine; really';\nCREATE TABLE u (b INT);"
    out = statements(sql)
    assert len(out) == 2
    assert out[0] == "COMMENT ON TABLE t IS 'it''s fine; really'"


def test_a_trailing_statement_without_a_semicolon_is_kept():
    assert statements("CREATE TABLE t (a INT)") == ["CREATE TABLE t (a INT)"]


def test_blank_input_produces_no_statements():
    assert statements("\n  -- only a comment\n\n") == []


def test_ensure_tables_creates_every_product_table_on_an_unmigrated_vault():
    conn = duckdb.connect(":memory:")
    ensure_tables(conn)
    present = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert set(PRODUCT_TABLES) <= present


def test_ensure_tables_is_idempotent_and_leaves_the_vault_readable():
    conn = duckdb.connect(":memory:")
    ensure_tables(conn)
    ensure_tables(conn)
    assert list_profiles(conn, "op_1") == []


def test_ensure_tables_never_touches_a_staging_table():
    """A page load prepares the product's own tables and nothing else."""
    conn = duckdb.connect(":memory:")
    ensure_tables(conn)
    present = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    assert not any(name.startswith("stg_") for name in present)


def test_a_vault_that_cannot_be_prepared_is_refused_in_words(tmp_path):
    """A read-only vault cannot create anything. The buyer is told; DuckDB is not quoted at them."""
    path = tmp_path / "vault.duckdb"
    duckdb.connect(str(path)).close()
    conn = duckdb.connect(str(path), read_only=True)
    with pytest.raises(DraftRefused) as caught:
        ensure_tables(conn)
    assert "zaad_draft_orders" in str(caught.value)
    assert "setup_db" in str(caught.value)
    conn.close()
