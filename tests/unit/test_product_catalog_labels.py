"""The contract vocabulary, named the way the engine names it.

`stg_po_options.action` is the contract's own word — `de_expedite`, `reschedule` — and it reached a
buyer's screen as "de expedite". P4B already decides what each option is called, so the product
reads that mapping rather than inventing a second one. These tests pin that it is read and not
re-derived, and that an option type the engine does not name still appears.
"""
from __future__ import annotations

import duckdb

from api.product.catalog import _action_label, purchase_order_detail


def test_the_contract_word_is_replaced_by_the_engines_own_name():
    from zaad.commitments.contracts import ACTION_LABEL

    assert _action_label("de_expedite") == ACTION_LABEL["de_expedite"].title() == "Defer"
    assert _action_label("reschedule") == "Defer"
    assert _action_label("expedite") == "Expedite"
    assert _action_label("cancel") == "Cancel"
    assert _action_label("keep") == "Keep"


def test_case_does_not_matter():
    assert _action_label("DE_EXPEDITE") == "Defer"


def test_an_option_the_engine_does_not_name_is_shown_not_dropped():
    """A new contract option must appear on screen, even unnamed. Silence would hide a right."""
    assert _action_label("part_ship") == "part ship"


def test_no_action_is_no_label():
    assert _action_label(None) is None


def _vault() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE stg_fmcg_purchase_orders (po_id VARCHAR, sku VARCHAR, supplier_id VARCHAR, "
                 "qty_ordered DOUBLE, unit_cost DOUBLE, po_date DATE, expected_delivery_date DATE)")
    conn.execute("INSERT INTO stg_fmcg_purchase_orders VALUES "
                 "('PO-1', 'SKU-1', 'SUP-1', 100, 2.5, DATE '2026-01-05', DATE '2026-02-01')")
    conn.execute("CREATE TABLE stg_po_options (po_id VARCHAR, option_id VARCHAR, action VARCHAR, "
                 "fee_per_unit DOUBLE, deadline TIMESTAMP, contract_reference VARCHAR)")
    conn.execute("INSERT INTO stg_po_options VALUES "
                 "('PO-1', 'opt_a', 'de_expedite', 0.2, TIMESTAMP '2026-01-20 00:00:00', 'MSA §7.2'), "
                 "('PO-1', 'opt_b', 'cancel', 0.0, TIMESTAMP '2026-01-20 00:00:00', 'MSA §7.2')")
    return conn


def test_the_detail_carries_the_label_beside_the_contract_word():
    conn = _vault()
    detail = purchase_order_detail(conn, "PO-1")
    by_id = {row["option_id"]: row for row in detail["declared_options"]}
    assert by_id["opt_a"]["action"] == "de_expedite"      # the contract's own word is kept
    assert by_id["opt_a"]["action_label"] == "Defer"      # and the engine's name is added
    assert by_id["opt_b"]["action_label"] == "Cancel"
    assert detail["amendment_rights_declared"] is True
    conn.close()


def test_an_order_with_no_declared_right_says_so_rather_than_implying_one():
    conn = _vault()
    conn.execute("DELETE FROM stg_po_options")
    detail = purchase_order_detail(conn, "PO-1")
    assert detail["declared_options"] == []
    assert detail["amendment_rights_declared"] is False
    conn.close()
