"""Indiana scenario generator: reproducibility and minimum-history gates."""

import duckdb

from scripts.setup_db import setup_db
from synthetic.indiana_operator_sim import IndianaSimulationConfig, build_indiana_dataset


def _generated(seed: int):
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    meta = build_indiana_dataset(conn, IndianaSimulationConfig(seed=seed, weeks=60))
    return conn, meta


def test_indiana_dataset_has_required_scale_and_history():
    conn, meta = _generated(17)
    try:
        assert meta["products"] >= 12
        assert meta["suppliers"] >= 12
        assert meta["buyers"] >= 8
        assert meta["data_basis"].startswith("synthetic")
        assert conn.execute(
            "SELECT COUNT(DISTINCT DATE_TRUNC('week', delivery_date)) FROM stg_buyer_orders"
        ).fetchone()[0] == 60
        assert conn.execute("SELECT COUNT(*) FROM stg_waste_adjustments").fetchone()[0] > 0
    finally:
        conn.close()


def test_indiana_dataset_is_reproducible_for_same_seed():
    first, _ = _generated(29)
    second, _ = _generated(29)
    try:
        query = "SELECT ROUND(SUM(fulfilled_quantity), 4) FROM stg_buyer_orders"
        assert first.execute(query).fetchone() == second.execute(query).fetchone()
        query = "SELECT ROUND(AVG(accepted_quantity / ordered_quantity), 6) FROM stg_supplier_deliveries"
        assert first.execute(query).fetchone() == second.execute(query).fetchone()
    finally:
        first.close()
        second.close()
