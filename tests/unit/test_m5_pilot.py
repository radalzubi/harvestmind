"""M5 weekly harness integrity. Synthetic series run without the dataset; dataset-backed checks skip when it is absent."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import duckdb
import numpy as np
import pytest

from zaad.full.replay import replay
from zaad.full.worlds import dates
from zaad.public.m5 import loader, request_builder as RB, selection, truth as T
from zaad.public.m5.declaration import DEFAULT, VARIANTS, WINDOWS

DB = Path(loader.DEFAULT_DB)
needs_dataset = pytest.mark.skipif(not DB.exists(), reason="M5 is not loaded in this checkout")
ORIGIN = date(2014, 8, 2)                       # a Saturday


def synthetic_weeks(n: int = 120, level: float = 30., seed: int = 1, price: float = 2.5) -> RB.SeriesWeeks:
    rng = np.random.default_rng(seed)
    start = ORIGIN - timedelta(weeks=80)
    weeks = [RB.WeekRecord(start + timedelta(weeks=i), start + timedelta(weeks=i, days=6), float(max(0., round(level + rng.normal(0, 6)))), price + (0.2 if i % 10 == 0 else 0.))
             for i in range(n)]
    return RB.SeriesWeeks("FOODS_1_001_CA_1_evaluation", "FOODS_1_001", "CA_1", "FOODS_1", "FOODS", weeks)


def test_walmart_week_alignment_and_origins():
    assert selection.week_start(date(2016, 1, 30)) == date(2016, 1, 30) and selection.week_start(date(2016, 2, 3)) == date(2016, 1, 30)
    assert all(w["origin"].weekday() == 5 for w in WINDOWS.values())          # every origin is a Saturday
    assert (WINDOWS["final"]["origin"] - loader.FIRST_DAY).days % 7 == 0       # on the d_1 week grid
    last_sales_day = loader.FIRST_DAY + timedelta(days=loader.DAYS - 1)
    assert last_sales_day == date(2016, 5, 22)
    assert WINDOWS["final"]["origin"] + timedelta(weeks=20) - timedelta(days=1) == date(2016, 5, 20) <= last_sales_day


def test_weekly_request_units_knowledge_boundary_and_observed_price():
    series = synthetic_weeks()
    req, rec = RB.build_request(series, ORIGIN, scenario="uncertain")
    assert req.period_days == 7 and req.horizon == 8 and len(req.history) == 52
    assert [h.period for h in req.history] == list(range(-52, 0)) and all(h.known_at < req.as_of for h in req.history)
    assert req.history[-1].known_at == datetime.combine(ORIGIN - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=23, minutes=59, seconds=59)
    src, loc = req.sources[0], req.locations[0]
    assert src.lead_days == 14 and src.lead_sd_days == 7. and dates(req, src, 0) == (0, 2)        # two-week lead lands in week t+2
    assert loc.holding_per_value_period == pytest.approx(0.35 / 52)                             # weekly rate from annual assumptions
    assert rec["price_at_origin"] == series.price_at(ORIGIN) and req.services[0].selling_price == rec["price_at_origin"]
    assert req.skus[0].asset_value == pytest.approx(rec["price_at_origin"] * 0.7) and src.maximum == pytest.approx(max(20., 20. * rec["mean_weekly_demand"]))
    assert req.liquidity.opening_cash is None and req.incumbent_rule == "reorder_point"
    with_cash = RB.build_request(series, ORIGIN, scenario="stable", declaration=VARIANTS["cash_4w"])[0]
    assert with_cash.liquidity.opening_cash == pytest.approx(4 * rec["mean_weekly_demand"] * rec["unit_cost"]) and with_cash.liquidity.credit_limit == 0.
    with pytest.raises(ValueError, match="Saturday"):
        RB.build_request(series, ORIGIN + timedelta(days=1), scenario="stable")


def test_no_future_information_and_price_knowledge():
    series = synthetic_weeks()
    base = RB.build_request(series, ORIGIN, scenario="stable")[0].model_dump_json()
    tampered = RB.SeriesWeeks(series.id, series.item_id, series.store_id, series.dept_id, series.cat_id,
                              [replace(w, sales=w.sales * 5, price=(w.price or 0) * 3) if w.start > ORIGIN else w for w in series.weeks])
    assert RB.build_request(tampered, ORIGIN, scenario="stable")[0].model_dump_json() == base
    # the origin week's own price is knowable at the origin (set at the week start); later weeks' prices are not used
    priced = RB.SeriesWeeks(series.id, series.item_id, series.store_id, series.dept_id, series.cat_id,
                            [replace(w, price=9.99) if w.start == ORIGIN else w for w in series.weeks])
    assert RB.build_request(priced, ORIGIN, scenario="stable")[1]["price_at_origin"] == 9.99


def test_truth_is_observed_weekly_sales_with_shared_declared_supply():
    series = synthetic_weeks(seed=4)
    req, _ = RB.build_request(series, ORIGIN, scenario="fill_only")
    world, rec = T.truth_world(req, series, ORIGIN, periods=12, seed=3)
    svc = req.services[0].id
    assert list(world.demand[svc]) == [w.sales for w in series.from_(ORIGIN)[:12]] and rec["track"] == "observed"
    assert all(world.arrival[k] - k[1] == 2 for k in world.arrival) and min(world.fills.values()) < 1.0   # no lead spread, short fills
    again, _ = T.truth_world(req, series, ORIGIN, periods=12, seed=3)
    assert again.fills == world.fills and again.arrival == world.arrival


def test_replay_conservation_and_independent_states_on_weekly_periods():
    series = synthetic_weeks(seed=6)
    req, _ = RB.build_request(series, ORIGIN, scenario="stable")
    world, _ = T.truth_world(req, series, ORIGIN, periods=3 - 1 + req.horizon, seed=1)
    outs = {m: replay(req.model_copy(update={"incumbent_rule": None}), world, 3, m, rolling=True) for m in ("reorder_point", "periodic:1", "order_up_to")}
    for m, out in outs.items():
        assert out["status"] == "COMPLETE", (m, out.get("failure"))
        assert all(abs(float(r["settlement"]["conservation_residual"])) < 1e-9 for r in out["reviews"])
    bought = {m: round(sum(sum(p["quantity"] for p in r["purchases"]) for r in o["reviews"]), 6) for m, o in outs.items()}
    assert len(set(bought.values())) >= 2


def test_selection_is_training_only_and_deterministic_on_a_synthetic_panel():
    conn = duckdb.connect(":memory:")
    rng = np.random.default_rng(5)
    days = [(loader.FIRST_DAY + timedelta(days=i)) for i in range(loader.DAYS)]
    conn.execute("CREATE TABLE m5_calendar (d DATE, wm_yr_wk INTEGER, dkey VARCHAR, dnum INTEGER)")
    conn.executemany("INSERT INTO m5_calendar VALUES (?, ?, ?, ?)", [(d, 11101 + i // 7, f"d_{i+1}", i + 1) for i, d in enumerate(days)])
    rows, prices = [], []
    for s in range(60):
        store, item, cat = f"CA_{s % 3 + 1}", f"FOODS_1_{s:03d}", "FOODS"
        level = rng.choice([0.5, 1.5, 4.0])
        for i, d in enumerate(days):
            rows.append((f"{item}_{store}_evaluation", item, "FOODS_1", cat, store, "CA", d, i + 1, float(max(0, round(level + rng.normal(0, 1))))))
        for wk in range(11101, 11101 + loader.DAYS // 7 + 1):
            prices.append((store, item, wk, 2.0))
    conn.execute("CREATE TABLE m5_daily (id VARCHAR, item_id VARCHAR, dept_id VARCHAR, cat_id VARCHAR, store_id VARCHAR, state_id VARCHAR, d DATE, dnum INTEGER, qty DOUBLE)")
    conn.executemany("INSERT INTO m5_daily VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.execute("CREATE TABLE m5_prices (store_id VARCHAR, item_id VARCHAR, wm_yr_wk INTEGER, sell_price DOUBLE)")
    conn.executemany("INSERT INTO m5_prices VALUES (?,?,?,?)", prices)
    a = selection.select(conn, count=8, seed=1)
    assert a["selection_hash"] == selection.select(conn, count=8, seed=1)["selection_hash"] and len(a["series"]) == 8
    assert all(r["mean_weekly"] >= selection.MIN_MEAN_WEEKLY and r["listed_throughout"] for r in a["series"])
    conn.execute("UPDATE m5_daily SET qty = qty * 10 WHERE d >= ?", [selection.HOLDOUT_ORIGIN])      # the holdout cannot move the selection
    assert selection.select(conn, count=8, seed=1)["selection_hash"] == a["selection_hash"]


def test_declaration_variants_are_distinct_and_weekly():
    d = DEFAULT.as_dict()
    assert d["period_days"] == 7 and d["history_weeks"] == 52 and d["horizon_weeks"] == 8 and len(d["hash"]) == 64
    assert len({v.hash() for v in VARIANTS.values()}) == len(VARIANTS)
    assert VARIANTS["cash_4w"].economics.cash_weeks == 4.0 and VARIANTS["no_incumbent"].zaad_incumbent_rule is None
    assert {s.name for s in DEFAULT.supply} >= {"stable", "uncertain", "lead_only", "fill_only", "mild_lead"}


@needs_dataset
def test_loaded_m5_matches_the_manifest_and_the_selection_is_frozen():
    conn = loader.connect()
    m = loader.manifest_record(conn)
    for name, spec in loader.MANIFEST.items():
        assert m[name]["sha256"] == spec["sha256"]
    frozen = json.loads(Path("docs/remodel/evidence/m5/SELECTION_MANIFEST.json").read_text())
    assert selection.select(conn, count=frozen["count"], seed=frozen["seed"])["selection_hash"] == frozen["selection_hash"]
    series = RB.load_series(conn, frozen["series"][0]["id"])
    assert all((w.end - w.start).days == 6 and w.start.weekday() == 5 for w in series.weeks)
    conn.close()
