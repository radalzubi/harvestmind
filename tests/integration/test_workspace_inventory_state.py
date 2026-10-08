"""Opening inventory as a proven physical state (HARDENING V1, H2).

A request uses an inventory state only when its effective state at the decision origin is causally
available and reconstructable (`zaad/full/inventory_state.py`). Nothing falls back to zero, to a stale
count, to one of several locations or to the last physical row; a cell that is not READY blocks the
request and names itself.

Crafted rows are inserted into the SYNTHETIC sample vault inside a transaction and rolled back."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time, timedelta, timezone

import duckdb
import pandas as pd
import pytest

from api.routers.intake import load_fmcg_sample_into
from scripts.setup_db import setup_db
from synthetic.fmcg.distributor_sim import build_history, closing_inventory_rows
from zaad.full import causal, inventory_state
from zaad.full.workspace import WorkspaceError, build_request

OP = "tenant_test"
ORIGIN = datetime(2024, 9, 2, tzinfo=timezone.utc)           # a Monday inside the sample's history
T = date(2024, 9, 2)
SKU, SKU2 = "SKU-0001", "SKU-0002"
EOD, SOD = "END_OF_DAY", "START_OF_DAY"
COLS = "(snapshot_date, sku, location_id, on_hand, in_transit, snapshot_basis, expiry_date, source_known_at, snapshot_at, lot_id)"
KNOWN = time(23, 59, 59)          # the crafted rows' declared knowledge time: the last second of the snapshot day (an explicit declaration, as every row must carry)


@pytest.fixture(scope="module")
def vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    load_fmcg_sample_into(conn, seed=7, archetype="A_stable")
    yield conn
    conn.close()


@contextmanager
def _transaction(conn):
    conn.execute("BEGIN TRANSACTION")
    try:
        yield conn
    finally:
        conn.execute("ROLLBACK")


def _rows(conn, rows, skus=(SKU,), economics=(), declare_known=True):
    """Replace the planned SKUs' inventory with crafted rows: (date, sku, location, on_hand, in_transit, basis, expiry, known_at, snapshot_at, lot_id).
    Rows without a knowledge time get the explicit declaration `snapshot_date 23:59:59` unless `declare_known` is False."""
    conn.execute(f"DELETE FROM stg_fmcg_inventory WHERE sku IN ({', '.join('?' for _ in skus)})", list(skus))
    conn.execute("DELETE FROM stg_fmcg_economics WHERE key LIKE 'inventory_%'")
    for row in rows:
        full = list(row) + [None] * (10 - len(row))
        if declare_known and full[7] is None:
            full[7] = datetime.combine(full[0], KNOWN)
        conn.execute(f"INSERT INTO stg_fmcg_inventory {COLS} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", full)
    for key, value in economics:
        conn.execute("INSERT INTO stg_fmcg_economics (key, value, provenance) VALUES (?, ?, 'test')", [key, value])


def _build(conn, skus=(SKU,), **kw):
    return build_request(conn, OP, as_of=ORIGIN, horizon=8, skus=list(skus), **kw)


def _stock(req):
    return {s.id: s.quantity for s in req.stock}


def _blocks(conn, status, *, skus=(SKU,), **kw):
    with pytest.raises(WorkspaceError, match=status) as err:
        _build(conn, skus=skus, **kw)
    return str(err.value)


# ── A: per-cell latest usable state, no global latest day ──
def test_a_each_cell_resolves_on_its_own_date(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD), (T - timedelta(days=1), SKU2, "MAIN", 200., 0, EOD)], skus=(SKU, SKU2))
        req, build = _build(conn, skus=(SKU, SKU2))
        assert _stock(req) == {f"open_{SKU}": 100., f"open_{SKU2}": 200.}
        cells = build["inventory_state"]["cells"]
        assert {k: v["status"] for k, v in cells.items()} == {f"{SKU}|main": "READY_DIRECT", f"{SKU2}|main": "READY_DIRECT"}
        assert build["inventory_state"]["status"] == "READY" and build["inventory_state"]["rolled_forward_cells"] == 0
    with _transaction(vault) as conn:
        # SKU-0002's latest count closes two days before the origin: not the state at the origin, not rolled forward
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD), (T - timedelta(days=2), SKU2, "MAIN", 200., 0, EOD)], skus=(SKU, SKU2))
        message = _blocks(conn, "NOT_READY_INCOMPLETE_MOVEMENTS", skus=(SKU, SKU2))
        assert SKU2 in message and "main" in message


# ── B: several real locations in a single-site build ──
def test_b_single_site_refuses_to_choose_among_locations_unless_sum_is_declared(vault):
    rows = [(T - timedelta(days=1), SKU, "DC", 100., 0, EOD), (T - timedelta(days=1), SKU, "BRANCH", 40., 0, EOD)]
    with _transaction(vault) as conn:
        _rows(conn, rows)
        message = _blocks(conn, "NOT_READY_LOCATION_AMBIGUITY")
        assert "BRANCH" in message and "DC" in message and "inventory_single_site_aggregation" in message
    with _transaction(vault) as conn:
        _rows(conn, rows, economics=[("inventory_single_site_aggregation", "SUM")])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}": 140.}
        cell = build["inventory_state"]["cells"][f"{SKU}|main"]
        assert cell["status"] == "READY_DIRECT" and "SUM" in cell["reason"] and build["inventory_state"]["aggregation"] == "SUM"
    with _transaction(vault) as conn:
        # SUM needs every location READY: a stale branch blocks the sum rather than being dropped
        _rows(conn, [rows[0], (T - timedelta(days=3), SKU, "BRANCH", 40., 0, EOD)], economics=[("inventory_single_site_aggregation", "SUM")])
        assert "BRANCH" in _blocks(conn, "NOT_READY_INCOMPLETE_MOVEMENTS")


# ── C: repeated rows for one cohort block, conflicting or identical, in either physical order ──
def test_c_repeated_rows_for_one_cohort_block_whatever_their_quantities_or_order(vault):
    for order in ((100., 70.), (70., 100.), (100., 100.)):
        with _transaction(vault) as conn:
            _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", q, 0, EOD) for q in order])
            message = _blocks(conn, "NOT_READY_AMBIGUOUS")
            assert f"{sorted(set(order))}" in message and "lot_id" in message
    with _transaction(vault) as conn:
        # a repeated lot_id has no duplicate contract either, equal quantities or not
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, None, None, None, "L1")] * 2)
        assert "repeated lot_id" in _blocks(conn, "NOT_READY_AMBIGUOUS")


def test_c_distinct_lot_ids_are_two_real_lots(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, T + timedelta(days=20), None, None, "L1"),
                     (T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, T + timedelta(days=20), None, None, "L2")])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}#{(T + timedelta(days=20)).isoformat()}~L1": 100., f"open_{SKU}#{(T + timedelta(days=20)).isoformat()}~L2": 100.}
        assert build["inventory_state"]["cells"][f"{SKU}|main"]["quantity_at_origin"] == 200.


# ── D: unknown is not zero ──
def test_d_a_planned_sku_without_any_count_blocks_instead_of_opening_at_zero(vault):
    with _transaction(vault) as conn:
        _rows(conn, [])
        assert "NOT_READY_NO_SNAPSHOT" in _blocks(conn, "NOT_READY_NO_SNAPSHOT")


# ── E: an earlier count is not rolled forward on an unproven ledger ──
def test_e_an_old_count_with_receipts_since_is_not_rolled_forward(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=30), SKU, "MAIN", 500., 0, EOD)])
        supplier = conn.execute("SELECT supplier_id FROM stg_fmcg_skus WHERE sku = ?", [SKU]).fetchone()[0]
        conn.execute("INSERT INTO stg_fmcg_purchase_orders (po_id, po_date, supplier_id, sku, qty_ordered, unit_cost) VALUES ('H2-E', ?, ?, ?, 300, 1.0)",
                     [T - timedelta(days=20), supplier, SKU])
        conn.execute("INSERT INTO stg_fmcg_receipts (po_id, receipt_date, sku, qty_received) VALUES ('H2-E', ?, ?, 300)", [T - timedelta(days=10), SKU])
        message = _blocks(conn, "NOT_READY_INCOMPLETE_MOVEMENTS")
        assert "adjustments" in message and "cannot be rolled forward" in message


# ── F: an explicit zero is a fact ──
def test_f_explicit_zero_is_ready_with_quantity_zero(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 0., 0, EOD)])
        req, build = _build(conn)
        assert _stock(req) == {}
        cell = build["inventory_state"]["cells"][f"{SKU}|main"]
        assert cell["status"] == "READY_DIRECT" and cell["quantity_at_origin"] == 0. and "explicit zero" in cell["reason"]
        assert build["inventory_state"]["zero_cells"] == 1


# ── G: a date-only row does not describe an instant ──
def test_g_date_only_rows_need_a_declared_basis(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, None)])
        _blocks(conn, "NOT_READY_AMBIGUOUS_TIMING")
    with _transaction(vault) as conn:
        # the workspace-level declaration reads every date-only row
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, None)], economics=[("inventory_snapshot_basis", EOD)])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}": 100.} and build["inventory_state"]["cells"][f"{SKU}|main"]["basis"] == EOD
    with _transaction(vault) as conn:
        # START_OF_DAY on the origin day is the state at the origin; END_OF_DAY on it would be a future state
        _rows(conn, [(T, SKU, "MAIN", 100., 0, SOD, None, datetime(2024, 9, 1, 22, 0))])      # a count of Monday's opening state, posted Sunday evening
        assert _stock(_build(conn)[0]) == {f"open_{SKU}": 100.}
    with _transaction(vault) as conn:
        _rows(conn, [(T, SKU, "MAIN", 100., 0, EOD)])
        _blocks(conn, "NOT_READY_NO_SNAPSHOT")


# ── H: expiry cohorts are distinct stock rows with deterministic ids ──
def test_h_expiry_cohorts_are_separate_stock_rows(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 60., 0, EOD, T + timedelta(days=13)), (T - timedelta(days=1), SKU, "MAIN", 40., 0, EOD, T + timedelta(days=34))])
        req, build = _build(conn)
        by_id = {s.id: s for s in req.stock}
        assert set(by_id) == {f"open_{SKU}#{(T + timedelta(days=13)).isoformat()}", f"open_{SKU}#{(T + timedelta(days=34)).isoformat()}"}
        assert sorted(s.quantity for s in req.stock) == [40., 60.] and len({s.expires_in for s in req.stock}) == 2
        assert build["provenance"]["stock.expiry"] == "CUSTOMER_PROVIDED"
    with _transaction(vault) as conn:
        # a cohort beside a row without an expiry cannot be told from a total
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 60., 0, EOD, T + timedelta(days=13)), (T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, None)])
        assert "cohort" in _blocks(conn, "NOT_READY_AMBIGUOUS")


# ── I: H1b causality applies to counts ──
def test_i_a_count_known_after_the_decision_does_not_exist_for_it(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, None, datetime(2024, 9, 3, 9, 0))])
        message = _blocks(conn, "NOT_READY_NO_SNAPSHOT")
        assert "known before the decision" in message
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, None, datetime(2024, 9, 1, 23, 30))])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}": 100.}
        assert req.stock[0].known_at == datetime(2024, 9, 1, 23, 30, tzinfo=timezone.utc)      # the real knowledge time, not backdated
        assert build["inventory_state"]["cells"][f"{SKU}|main"]["source_known_at"] == "2024-09-01T23:30:00"


# ── J: an exact instant ──
def test_j_point_in_time_snapshot_at_is_the_instant_itself(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T, SKU, "MAIN", 123., 0, None, None, datetime(2024, 9, 1, 22, 0), datetime(2024, 9, 2, 0, 0))])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}": 123.} and build["inventory_state"]["cells"][f"{SKU}|main"]["basis"] == "POINT_IN_TIME"
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 123., 0, None, None, None, datetime(2024, 9, 1, 17, 45))])
        _blocks(conn, "NOT_READY_INCOMPLETE_MOVEMENTS")


# ── K: in_transit is a signal, never stock or an order ──
def test_k_in_transit_is_reported_and_never_counted(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD)])
        plain, _ = _build(conn)
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 999., EOD)])
        loaded, build = _build(conn)
        assert _stock(loaded) == {f"open_{SKU}": 100.}
        assert len(loaded.pipeline) == len(plain.pipeline) and sum(p.ordered for p in loaded.pipeline) == sum(p.ordered for p in plain.pipeline)
        assert build["inventory_state"]["cells"][f"{SKU}|main"]["in_transit_declared"] == 999.
        assert causal.fingerprint(loaded).hash == causal.fingerprint(plain).hash


# ── L: physical order and ingestion time are not state ──
def test_l_physical_reorder_and_import_time_change_nothing(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 60., 0, EOD, T + timedelta(days=13)), (T - timedelta(days=1), SKU, "MAIN", 40., 0, EOD, T + timedelta(days=34))])
        first = causal.fingerprint(_build(conn)[0]).hash
        conn.execute("CREATE TEMP TABLE reordered_ AS SELECT * FROM stg_fmcg_inventory ORDER BY rowid DESC")
        conn.execute("DELETE FROM stg_fmcg_inventory")
        conn.execute("INSERT INTO stg_fmcg_inventory SELECT * FROM reordered_")
        conn.execute("DROP TABLE reordered_")
        conn.execute("UPDATE stg_fmcg_inventory SET imported_at = TIMESTAMP '2030-01-01 00:00:00'")
        assert causal.fingerprint(_build(conn)[0]).hash == first


# ── M: network cells resolve per location ──
def test_m_network_cells_resolve_per_location():
    frame = pd.DataFrame([{"snapshot_date": T - timedelta(days=1), "sku": SKU, "location_id": "DC", "on_hand": 10., "in_transit": 0., "snapshot_basis": EOD, "source_known_at": datetime.combine(T - timedelta(days=1), KNOWN)},
                          {"snapshot_date": T - timedelta(days=8), "sku": SKU, "location_id": "SOUTH", "on_hand": 5., "in_transit": 0., "snapshot_basis": EOD, "source_known_at": datetime.combine(T - timedelta(days=8), KNOWN)},
                          {"snapshot_date": T - timedelta(days=1), "sku": SKU, "location_id": "NORTH", "on_hand": 0., "in_transit": 0., "snapshot_basis": EOD, "source_known_at": datetime.combine(T - timedelta(days=1), KNOWN)}])
    out = inventory_state.resolve(frame, decision_at=pd.Timestamp(T), skus=[SKU], locations=["DC", "NORTH", "SOUTH"])
    statuses = {k: c.status for k, c in out["cells"].items()}
    assert statuses == {f"{SKU}|DC": "READY_DIRECT", f"{SKU}|NORTH": "READY_DIRECT", f"{SKU}|SOUTH": "NOT_READY_INCOMPLETE_MOVEMENTS"}
    assert out["status"] == "NOT_READY" and [(e["location"], e["quantity"]) for e in out["stock"]] == [("DC", 10.)]


def test_m_network_workspace_blocks_on_a_stale_site(tmp_path):
    from scripts.zaad_network_workspace_smoke import make_network_vault
    from zaad.meio.workspace import build_network_request
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    make_network_vault(conn, seed=7)
    req, build = build_network_request(conn, "tenant_n", skus=[SKU], max_solve_seconds=5.)
    cells = build["inventory_state"]["cells"]
    assert {k.split("|")[1] for k in cells} == {"DC", "NORTH", "SOUTH"} and all(c["status"] == "READY_DIRECT" for c in cells.values())
    assert {s.location for s in req.stock} <= {"DC", "NORTH", "SOUTH"} and all(s.id.startswith(f"open_{SKU}@") for s in req.stock)
    # SOUTH's count is a week older in every respect: its date, its exact instant and when it was known
    conn.execute("UPDATE stg_fmcg_inventory SET snapshot_date = snapshot_date - INTERVAL 7 DAY, snapshot_at = snapshot_at - INTERVAL 7 DAY, "
                 "source_known_at = source_known_at - INTERVAL 7 DAY WHERE sku = ? AND location_id = 'SOUTH'", [SKU])
    with pytest.raises(WorkspaceError, match="SOUTH"):
        build_network_request(conn, "tenant_n", skus=[SKU], max_solve_seconds=5.)
    conn.close()


# ── N: the report says what the request rests on ──
def test_n_build_report_carries_the_inventory_state_section(vault):
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 100., 7., EOD)])
        _, build = _build(conn)
        section = build["inventory_state"]
        assert section["status"] == "READY" and section["required_cells"] == section["ready_cells"] == section["direct_snapshot_cells"] == 1
        assert section["movement_coverage"]["roll_forward_performed"] is False and section["movement_coverage"]["completeness_declared"] is False
        cell = section["cells"][f"{SKU}|main"]
        assert cell["snapshot_effective_at"] == "2024-09-02T00:00:00" and cell["basis"] == EOD
        assert cell["quantity_at_snapshot"] == cell["quantity_at_origin"] == 100. and cell["roll_forward"] is None and cell["age_days"] == 0.
        assert not any("inventory snapshot" in w for w in build["warnings"])       # age is metadata, not a warning rule
    with _transaction(vault) as conn:
        # a 30-day-old count that IS the state at the origin (an exact instant) is READY; its age is reported, not judged
        _rows(conn, [(T - timedelta(days=30), SKU, "MAIN", 100., 0., None, None, datetime(2024, 9, 1, 18, 0), datetime(2024, 9, 2, 0, 0))])
        _, build = _build(conn)
        assert build["inventory_state"]["status"] == "READY" and build["inventory_state"]["latest_snapshot_age_days"] == 0.


# ── O: the synthetic sample declares its own semantics ──
def test_o_synthetic_snapshots_are_declared_as_closing_counts(vault):
    hist = build_history("A_stable", seed=7)
    rows = closing_inventory_rows(hist.inventory_snapshots)
    week = pd.Timestamp(hist.inventory_snapshots["week_start"].iloc[0])
    assert (rows["snapshot_basis"] == EOD).all() and rows["snapshot_date"].iloc[0] == week + pd.Timedelta(days=6) and rows["snapshot_at"].iloc[0] == week + pd.Timedelta(days=7)
    assert rows["source_known_at"].iloc[0] == week + pd.Timedelta(days=6, hours=23, minutes=59, seconds=59) and (rows["source_known_at"] < rows["snapshot_at"]).all()
    # in the loaded vault: the count labelled week w holds that week's receipts, so it is the state that opens week w + 1
    sku = SKU
    last_week = pd.Timestamp(hist.inventory_snapshots["week_start"].max())
    stored = vault.execute("SELECT snapshot_date, snapshot_basis, snapshot_at, on_hand FROM stg_fmcg_inventory WHERE sku = ? ORDER BY snapshot_date DESC LIMIT 1", [sku]).fetchone()
    assert pd.Timestamp(stored[0]) == last_week + pd.Timedelta(days=6) and stored[1] == EOD and pd.Timestamp(stored[2]) == last_week + pd.Timedelta(days=7)
    assert vault.execute("SELECT value, provenance FROM stg_fmcg_economics WHERE key = 'inventory_snapshot_basis'").fetchone() == (EOD, "SYNTHETIC")
    assert vault.execute("SELECT value, provenance FROM stg_fmcg_economics WHERE key = 'inventory_source_known_rule'").fetchone() == ("CLOSE_OF_SNAPSHOT_DAY", "SYNTHETIC")
    assert vault.execute("SELECT min(source_known_at) IS NOT NULL AND max(source_known_at < snapshot_at) FROM stg_fmcg_inventory").fetchone()[0]
    sim = hist.inventory_snapshots[(hist.inventory_snapshots["sku"] == sku) & (pd.to_datetime(hist.inventory_snapshots["week_start"]) == last_week)]["on_hand"].iloc[0]
    assert float(stored[3]) == float(sim)
    # the week after the last snapshot plans directly from it; the week before cannot use it (it is not yet known)
    req, build = build_request(vault, OP, as_of=(last_week + pd.Timedelta(days=7)).to_pydatetime().replace(tzinfo=timezone.utc), horizon=8, skus=[sku])
    assert build["inventory_state"]["cells"][f"{sku}|main"]["status"] == "READY_DIRECT" and _stock(req) == {f"open_{sku}": float(sim)}
    assert build["inventory_state"]["cells"][f"{sku}|main"]["knowledge_basis"] == "EXPLICIT_SOURCE_KNOWN"
    assert all(s.known_at < req.as_of for s in req.stock)         # the H1b inequality on every fact-derived Stock, strict


# ── P: the strict knowledge boundary (H1b, unchanged for inventory) ──
def test_p_the_knowledge_boundary_is_strict(vault):
    physical = (T - timedelta(days=1), SKU, "MAIN", 100., 0, EOD, None)
    with _transaction(vault) as conn:                                       # A: known one second before T
        _rows(conn, [physical + (datetime(2024, 9, 1, 23, 59, 59),)])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}": 100.} and req.stock[0].known_at == datetime(2024, 9, 1, 23, 59, 59, tzinfo=timezone.utc) < req.as_of
    with _transaction(vault) as conn:                                       # B: known exactly at T: unavailable
        _rows(conn, [physical + (datetime(2024, 9, 2, 0, 0, 0),)])
        message = _blocks(conn, "NOT_READY_NO_SNAPSHOT")
        assert "known before the decision" in message
    with _transaction(vault) as conn:                                       # C: known one second after T: unavailable
        _rows(conn, [physical + (datetime(2024, 9, 2, 0, 0, 1),)])
        _blocks(conn, "NOT_READY_NO_SNAPSHOT")
    with _transaction(vault) as conn:                                       # D: no knowledge time and no declared contract
        _rows(conn, [physical], declare_known=False)
        message = _blocks(conn, "NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE")
        assert "source_known_at" in message and "inventory_source_known_rule" in message
    with _transaction(vault) as conn:                                       # D': an explicit workspace-declared knowledge rule is a contract, not a fallback
        _rows(conn, [physical], declare_known=False, economics=[("inventory_source_known_rule", "CLOSE_OF_SNAPSHOT_DAY")])
        req, build = _build(conn)
        cell = build["inventory_state"]["cells"][f"{SKU}|main"]
        assert cell["knowledge_basis"] == "DECLARED_RULE:CLOSE_OF_SNAPSHOT_DAY" and cell["source_known_at"] == "2024-09-01T23:59:59"
        assert req.stock[0].known_at == datetime(2024, 9, 1, 23, 59, 59, tzinfo=timezone.utc) < req.as_of
    with _transaction(vault) as conn:                                       # E: import time is not knowledge
        _rows(conn, [physical], declare_known=False)
        conn.execute("UPDATE stg_fmcg_inventory SET imported_at = TIMESTAMP '2020-01-01 00:00:00'")
        _blocks(conn, "NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE")
    with _transaction(vault) as conn:                                       # the effective instant alone never admits a count
        _rows(conn, [(T, SKU, "MAIN", 100., 0, None, None, None, datetime(2024, 9, 2, 0, 0))], declare_known=False)
        _blocks(conn, "NOT_READY_KNOWLEDGE_TIME_UNAVAILABLE")


def test_p_every_fact_derived_stock_of_the_sample_request_is_known_before_the_decision(vault):
    req, build = build_request(vault, OP, as_of=ORIGIN, horizon=8)          # the whole planned catalogue
    assert req.stock and all(s.known_at < req.as_of for s in req.stock)
    assert build["inventory_state"]["status"] == "READY" and build["inventory_state"]["knowledge_rule"].startswith("source_known_at < decision_at")


# ── Q: cohort-level knowledge provenance ──
def test_q_each_cohort_carries_its_own_knowledge_time(vault):
    early, late = datetime(2024, 9, 1, 8, 0), datetime(2024, 9, 1, 20, 0)
    with _transaction(vault) as conn:
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 60., 0, EOD, T + timedelta(days=13), early), (T - timedelta(days=1), SKU, "MAIN", 40., 0, EOD, T + timedelta(days=34), late)])
        req, build = _build(conn)
        known = {s.id: s.known_at for s in req.stock}
        assert known == {f"open_{SKU}#{(T + timedelta(days=13)).isoformat()}": early.replace(tzinfo=timezone.utc),
                         f"open_{SKU}#{(T + timedelta(days=34)).isoformat()}": late.replace(tzinfo=timezone.utc)}
        cell = build["inventory_state"]["cells"][f"{SKU}|main"]
        assert [c["source_known_at"] for c in cell["cohorts"]] == ["2024-09-01T08:00:00", "2024-09-01T20:00:00"] and cell["source_known_at"] == "2024-09-01T20:00:00"
    with _transaction(vault) as conn:
        # the later cohort is known only at T: it alone is excluded, the earlier one stands on its own time
        _rows(conn, [(T - timedelta(days=1), SKU, "MAIN", 60., 0, EOD, T + timedelta(days=13), early), (T - timedelta(days=1), SKU, "MAIN", 40., 0, EOD, T + timedelta(days=34), datetime(2024, 9, 2, 0, 0))])
        req, build = _build(conn)
        assert _stock(req) == {f"open_{SKU}#{(T + timedelta(days=13)).isoformat()}": 60.} and build["inventory_state"]["cells"][f"{SKU}|main"]["rows_excluded_not_known"] == 1
    with _transaction(vault) as conn:
        # a declared SUM of locations is known only when all of its components are: the aggregate takes the latest time
        _rows(conn, [(T - timedelta(days=1), SKU, "DC", 100., 0, EOD, None, early), (T - timedelta(days=1), SKU, "BRANCH", 40., 0, EOD, None, late)],
              economics=[("inventory_single_site_aggregation", "SUM")])
        req, _ = _build(conn)
        assert [(s.quantity, s.known_at) for s in req.stock] == [(140., late.replace(tzinfo=timezone.utc))]
