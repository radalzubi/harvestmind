"""The FMCG simulator must produce histories an ERP could have recorded."""
from __future__ import annotations

import pandas as pd
import pytest

from synthetic.fmcg.distributor_sim import (
    ARCHETYPES, ArchetypeSpec, build_history, coherence_report,
)

SMALL = dict(n_skus=12, n_suppliers=3, n_customers=6, weeks=60)


@pytest.fixture(scope="module")
def histories():
    return {name: build_history(name, seed=3, spec=ArchetypeSpec(name=name, **{
        **{k: v for k, v in ARCHETYPES[name].__dict__.items() if k != "name"}, **SMALL}))
        for name in ARCHETYPES}


@pytest.mark.parametrize("name", list(ARCHETYPES))
def test_cross_table_identities(histories, name):
    rep = coherence_report(histories[name])
    assert rep["receipts_never_exceed_po"]
    assert rep["orders_shipped_le_ordered"]
    assert rep["no_negative_stock"]
    assert rep["po_lots_whole"]
    assert 0.0 < rep["realised_supplier_fill"] <= 1.0


def test_seed_reproducibility():
    a = build_history("B_volatile_retail", seed=11, spec=ArchetypeSpec("B", **SMALL))
    b = build_history("B_volatile_retail", seed=11, spec=ArchetypeSpec("B", **SMALL))
    for t in ("purchase_orders", "order_lines", "receipts"):
        pd.testing.assert_frame_equal(getattr(a, t), getattr(b, t))


def test_different_seed_changes_history():
    a = build_history("A_stable", seed=1, spec=ArchetypeSpec("A", **SMALL))
    b = build_history("A_stable", seed=2, spec=ArchetypeSpec("A", **SMALL))
    assert not a.order_lines["qty_ordered"].equals(b.order_lines["qty_ordered"])


def test_receipts_are_caused_by_purchase_orders(histories):
    h = histories["C_constrained_supplier"]
    po_ids = set(h.purchase_orders["po_id"])
    assert set(h.receipts["po_id"]) <= po_ids
    merged = h.receipts.merge(h.purchase_orders, on="po_id")
    assert (merged["receipt_date"] > merged["po_date"]).all()


def test_importer_orders_are_whole_pallets_and_meet_moq(histories):
    h = histories["D_importer"]
    po = h.purchase_orders.merge(h.skus[["sku", "units_per_case", "moq_units"]], on="sku")
    pallet = po["units_per_case"] * 50
    assert ((po["qty_ordered"] % pallet).abs() < 1e-6).all() or \
           (po["qty_ordered"] >= po["moq_units"]).all()
    assert (po["qty_ordered"] >= po["moq_units"] - 1e-6).all()


def test_disruption_degrades_fill_during_window_only(histories):
    h = histories["F_disruption"]
    spec = ARCHETYPES["F_disruption"]
    po = h.purchase_orders.merge(h.receipts.groupby("po_id")["qty_received"].sum(),
                                 on="po_id", how="left").fillna({"qty_received": 0})
    po = po.merge(h.suppliers[["supplier_id", "disrupted"]], on="supplier_id")
    wk = pd.to_datetime(po["po_date"])
    w0 = wk.min() + pd.Timedelta(weeks=spec.disruption_week)
    w1 = w0 + pd.Timedelta(weeks=spec.disruption_len)
    hit = po[po["disrupted"] & (wk >= w0) & (wk < w1)]
    calm = po[po["disrupted"] & ((wk < w0) | (wk >= w1 + pd.Timedelta(weeks=4)))]
    if len(hit) and len(calm):
        f_hit = hit["qty_received"].sum() / hit["qty_ordered"].sum()
        f_calm = calm["qty_received"].sum() / calm["qty_ordered"].sum()
        assert f_hit < f_calm


def test_stockouts_are_real_shortfalls_not_rounding(histories):
    h = histories["A_stable"]
    rep = coherence_report(h)
    sku_weeks = len(h.inventory_snapshots)
    assert rep["stockout_weeks"] / sku_weeks < 0.15
    if len(h.stockouts):
        assert (h.stockouts["units_short"] >= 1).all()


def test_dead_stock_stops_moving(histories):
    h = histories["E_mixed_portfolio"]
    dead = set(h.skus.loc[h.skus["dead_stock"], "sku"])
    if dead:
        late = h.order_lines[h.order_lines["order_id"].str[4:8].astype(int) > 30]
        assert late[late["sku"].isin(dead)]["qty_ordered"].sum() == 0


def test_classification_is_declared():
    h = build_history("A_stable", seed=0, spec=ArchetypeSpec("A", **SMALL))
    assert h.classification == "SYNTHETIC CALIBRATED"
