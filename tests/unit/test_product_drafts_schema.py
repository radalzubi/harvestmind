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


# ── bounded numbers ───────────────────────────────────────────────────────────

def _vault():
    conn = duckdb.connect(":memory:")
    ensure_tables(conn)
    return conn


@pytest.mark.parametrize("field", ["quantity", "unit_price", "units_per_case"])
def test_a_number_too_large_to_be_an_order_is_refused_in_words(field):
    """A quintillion units reached the optimizer as a number it had to solve with.

    Whatever came back — nonsense or a solver failure — would not have said which line was wrong or
    why. The refusal happens where the person who typed it is looking.
    """
    from api.product.drafts import MAX_LINE_VALUE, create_draft

    conn = _vault()
    line = {"sku": "SKU-1", "quantity": 10.0}
    line[field] = MAX_LINE_VALUE * 10
    with pytest.raises(DraftRefused) as caught:
        create_draft(conn, "op_1", {"origin": "MANUAL", "lines": [line]}, actor="op_1")
    assert "Line 1" in str(caught.value)
    assert "typo" in str(caught.value)
    conn.close()


def test_a_number_at_the_bound_is_still_an_order():
    from api.product.drafts import MAX_LINE_VALUE, create_draft, read_draft

    conn = _vault()
    draft_id = create_draft(conn, "op_1", {"origin": "MANUAL",
                                           "lines": [{"sku": "SKU-1", "quantity": MAX_LINE_VALUE}]}, actor="op_1")
    assert read_draft(conn, "op_1", draft_id)["lines"][0]["quantity"] == MAX_LINE_VALUE
    conn.close()


def test_a_refused_line_leaves_the_proposal_exactly_as_it_was():
    """The refusal must change nothing — the same property the validate-then-write order protects."""
    from api.product.drafts import MAX_LINE_VALUE, create_draft, read_draft, update_draft

    conn = _vault()
    draft_id = create_draft(conn, "op_1", {"origin": "MANUAL",
                                           "lines": [{"sku": "SKU-1", "quantity": 100.0}]}, actor="op_1")
    with pytest.raises(DraftRefused):
        update_draft(conn, "op_1", draft_id,
                     {"lines": [{"sku": "SKU-1", "quantity": MAX_LINE_VALUE * 2}]}, actor="op_1")
    after = read_draft(conn, "op_1", draft_id)
    assert [(row["sku"], row["quantity"]) for row in after["lines"]] == [("SKU-1", 100.0)]
    conn.close()


def test_a_vault_survives_a_hard_stop_right_after_ensure_tables(tmp_path):
    """Schema changes never wait in the write-ahead log (Fable V1 audit).

    The vault's connection is held open for the life of the process, so nothing checkpoints on
    close. A DuckDB file whose WAL holds an `ALTER TABLE` on a product table cannot be opened after
    a hard stop — replay fails with an internal error — which is exactly what a deploy followed by a
    restart would do to every existing vault. `ensure_tables` checkpoints after any DDL it ran.
    """
    import os
    import subprocess
    import sys
    import textwrap

    import duckdb

    from scripts.setup_db import setup_db

    path = tmp_path / "vault.db"
    conn = duckdb.connect(str(path))
    setup_db(conn)
    # a vault as an earlier release left it: migrated to 023, without the 024 columns
    conn.execute("ALTER TABLE zaad_evaluations DROP COLUMN draft_hash")
    conn.execute("ALTER TABLE zaad_evaluations DROP COLUMN workspace_version")
    conn.execute("ALTER TABLE zaad_draft_orders DROP COLUMN approved_evaluation_id")
    conn.execute("ALTER TABLE zaad_draft_orders DROP COLUMN approval_evaluation_state")
    conn.close()

    code = textwrap.dedent(f"""
        import os, sys
        sys.path.insert(0, {os.getcwd()!r})
        import duckdb
        from api.product.drafts import ensure_tables
        conn = duckdb.connect({str(path)!r})
        ensure_tables(conn)          # runs the 024 ALTERs on this vault, then checkpoints
        os._exit(0)                  # a hard stop: no close, no shutdown hook
    """)
    subprocess.run([sys.executable, "-c", code], check=True)
    reopened = duckdb.connect(str(path))
    present = {row[1] for row in reopened.execute("PRAGMA table_info('zaad_evaluations')").fetchall()}
    assert "draft_hash" in present
    reopened.close()
