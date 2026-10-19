"""A series with no sales in its history window is a recorded BUILD_FAILED run, never a planned one (it has no demand to
plan and produced a KeyError in replay before the ledger fix); a coupled group drops such an item with a recorded reason."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from zaad.public.m5 import coupled as C, request_builder as RB
from zaad.public.m5.request_builder import SeriesWeeks, WeekRecord


def _series(item, store, sales, price, start=date(2014, 1, 4), weeks=60):
    rows = [WeekRecord(start + timedelta(weeks=i), start + timedelta(weeks=i, days=6), float(sales(i)), price) for i in range(weeks)]
    return SeriesWeeks(id=f"{item}_{store}", item_id=item, store_id=store, dept_id="FOODS_3", cat_id="FOODS", weeks=rows)


def test_single_sku_builder_refuses_a_zero_sales_history():
    origin = date(2014, 1, 4) + timedelta(weeks=40)
    dead = _series("FOODS_3_900", "CA_1", lambda i: 0. if i < 45 else 5., 2.0)          # launches after the origin
    with pytest.raises(ValueError, match="no sales in the"):
        RB.build_request(dead, origin, scenario="stable")
    live = _series("FOODS_3_901", "CA_1", lambda i: 3. + (i % 3), 2.0)
    req, _ = RB.build_request(live, origin, scenario="stable")
    assert req.stock and req.stock[0].quantity > 0


def test_coupled_group_drops_the_zero_sales_item_with_a_reason():
    origin = date(2014, 1, 4) + timedelta(weeks=40)
    dead = _series("FOODS_3_900", "CA_1", lambda i: 0. if i < 45 else 5., 2.0)
    live = [_series(f"FOODS_3_90{k}", "CA_1", lambda i, k=k: 3. + k + (i % 3), 2.0) for k in (1, 2)]
    req, record = C.build_group_request([dead, *live], origin, scenario="stable", coupling=C.DEFAULT)
    assert record["group_size"] == 2 and record["dropped_items"] == [{"series_id": "FOODS_3_900_CA_1", "reason": f"no sales in the history before {origin}"}]
    assert {s.sku for s in req.sources} == {"FOODS_3_901", "FOODS_3_902"}
