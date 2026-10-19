"""FreshRetailNet pilot integrity (public-data evaluation, first run).

Most tests build synthetic series in memory through the same `SeriesDays`/`DayRecord` types the loader produces, so
they run without the dataset; the few that need the loaded files skip when `data/public/freshretailnet/frn.duckdb`
is absent. Nothing here touches an operator vault, the staging tables or the optimizer."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import duckdb
import numpy as np
import pytest

from zaad.full.contracts import Request
from zaad.full.evaluation import endpoint
from zaad.full.replay import replay
from zaad.full.worlds import dates
from zaad.public.freshretailnet import loader, recovery, request_builder as RB, selection, truth as T
from zaad.public.freshretailnet.declaration import DEFAULT, Declaration, Economics

DB = Path(loader.DEFAULT_DB)
needs_dataset = pytest.mark.skipif(not DB.exists(), reason="FreshRetailNet is not loaded in this checkout")


# ── synthetic series: the loader's own record types, no dataset needed ─────────────────────────────────────────────
def _day(day: date, hourly: list[float], out_hours: set[int] = frozenset()) -> recovery.DayRecord:
    sales = np.asarray(hourly, dtype=float)
    flags = np.zeros(24, dtype=int)
    for h in out_hours:
        flags[h] = 1
        sales[h] = 0.                       # nothing sells while out of stock
    return recovery.DayRecord(day, float(sales.sum()), sales, flags)


def _profile_day(total: float) -> list[float]:
    """A plausible diurnal shape: nothing at night, a morning peak."""
    weights = np.zeros(24)
    weights[6:22] = np.array([1, 2, 4, 6, 7, 6, 4, 3, 3, 3, 4, 5, 5, 4, 2, 1], dtype=float)
    return list(total * weights / weights.sum())


def synthetic_series(days: int = 97, start: date = date(2024, 3, 28), level: float = 4.0, seed: int = 1, stockout_every: int | None = None) -> RB.SeriesDays:
    rng = np.random.default_rng(seed)
    records = []
    for i in range(days):
        d = start + timedelta(days=i)
        total = max(0., level + rng.normal(0, 0.8))
        out = set(range(16, 22)) if (stockout_every and i % stockout_every == 0) else set()
        records.append(_day(d, _profile_day(total), out))
    return RB.SeriesDays(store_id=1, product_id=2, records=records)


ORIGIN = date(2024, 5, 13)


def test_stockout_interpretation_is_flag_one_over_business_hours():
    rec = _day(date(2024, 4, 1), _profile_day(10.), out_hours={18, 19, 20, 21})
    assert rec.out_hours == 4 and loader.OUT_OF_STOCK_FLAG == 1 and list(loader.BUSINESS_HOURS) == list(range(6, 22))
    assert rec.sales < 10. and rec.hourly_sales[18:22].sum() == 0.


def test_loader_refuses_a_file_that_is_not_the_audited_release(tmp_path):
    bogus = tmp_path / "train.parquet"
    bogus.write_bytes(b"not a parquet file")
    with pytest.raises(loader.DatasetMismatch):
        loader.verify(bogus, "train.parquet")
    with pytest.raises(loader.DatasetMismatch):
        loader.verify(bogus, "other.parquet")


def test_loader_invariants_fail_closed_on_an_inconsistent_panel():
    conn = duckdb.connect(":memory:")
    conn.execute("""CREATE TABLE frn_daily AS SELECT 1 AS store_id, 1 AS product_id, DATE '2024-03-28' AS d, 5.0 AS sale_amount,
                    3 AS stock_hours_out, list_transform(range(24), x -> 0.0) AS hours_sale,
                    list_transform(range(24), x -> 0) AS hours_stock_status""")     # sum(hours)=0 != 5, cnt 3 != 0 flags
    with pytest.raises(loader.DatasetMismatch) as exc:
        loader._check_invariants(conn)
    assert "sum(hours_sale) != sale_amount" in str(exc.value) and "stock_hours_out" in str(exc.value)


def test_selection_is_deterministic_and_training_only():
    conn = duckdb.connect(":memory:")
    rows = []
    rng = np.random.default_rng(3)
    for s in range(40):
        for p in range(6):
            level = rng.choice([0.3, 1.0, 4.0])
            for i in range(97):
                d = date(2024, 3, 28) + timedelta(days=i)
                split = "train" if i < 90 else "eval"
                rows.append((split, s % 3, s, p, d, float(max(0., level + rng.normal(0, 0.5))), int(rng.integers(0, 17)) if rng.random() < 0.4 else 0,
                             float(0.9 if rng.random() < 0.5 else 1.0), int(rng.random() < 0.3), p, p % 4, p))
    conn.execute("""CREATE TABLE frn_daily (split VARCHAR, city_id INT, store_id INT, product_id INT, d DATE, sale_amount DOUBLE, stock_hours_out INT,
                    discount DOUBLE, activity_flag INT, management_group_id INT, first_category_id INT, third_category_id INT)""")
    conn.executemany("INSERT INTO frn_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    a = selection.select(conn, count=12, seed=5)
    b = selection.select(conn, count=12, seed=5)
    assert a["selection_hash"] == b["selection_hash"] and len(a["series"]) == 12 and len({(r["store_id"], r["product_id"]) for r in a["series"]}) == 12
    assert all(r["days"] == 90 for r in a["series"])                      # features come from the 90 training days only
    conn.execute("UPDATE frn_daily SET sale_amount = sale_amount * 10 WHERE split = 'eval'")
    assert selection.select(conn, count=12, seed=5)["selection_hash"] == a["selection_hash"]   # the evaluation week cannot move the selection
    assert selection.select(conn, count=12, seed=6)["selection_hash"] != a["selection_hash"]


def test_recovery_never_lowers_demand_uses_pre_origin_profile_only_and_caps():
    series = synthetic_series(stockout_every=5, seed=2)
    rec = recovery.recover_series(series.records, origin=ORIGIN)
    by_day = {r.day: r for r in rec}
    for r in rec:
        assert r.recovered >= r.observed - 1e-12 and r.naive >= r.observed - 1e-12
        assert r.recovered <= max(r.observed, r.observed * 3.0) + 1e-9
    clean = [r for r in series.records if r.out_hours == 0]
    assert all(by_day[d.day].method == "observed" and by_day[d.day].recovered == d.sales for d in clean)
    censored = [r for r in series.records if r.out_hours > 0 and r.day >= ORIGIN]
    assert censored and all(by_day[d.day].recovered > d.sales for d in censored)
    # the profile for a post-origin day uses pre-origin days only: changing post-origin clean days changes nothing before or at the origin
    tampered = [replace(r, hourly_sales=r.hourly_sales * 3, sales=r.sales * 3) if (r.day > ORIGIN and r.out_hours == 0) else r for r in series.records]
    rec2 = {r.day: r for r in recovery.recover_series(tampered, origin=ORIGIN)}
    for r in rec:
        if r.day <= ORIGIN:
            assert rec2[r.day].recovered == pytest.approx(r.recovered)
    # a censored post-origin day's own recovery depends on its in-stock hours and the pre-origin profile, not on later days
    first_censored = min(d.day for d in censored)
    assert rec2[first_censored].recovered == pytest.approx(by_day[first_censored].recovered)
    s = recovery.summary(rec)
    assert s["recovered_total"] >= s["observed_total"] and s["evidence"].startswith("DERIVED")


def test_daily_request_units_and_knowledge_boundary():
    series = synthetic_series()
    req, record = RB.build_request(series, ORIGIN, track="observed", scenario="stable")
    assert req.period_days == 1 and req.horizon == DEFAULT.horizon_days and req.as_of == datetime(2024, 5, 13, tzinfo=timezone.utc)
    assert len(req.history) == min(DEFAULT.history_days, 46) == 46 and [h.period for h in req.history] == list(range(-46, 0))
    assert all(h.known_at < req.as_of for h in req.history) and req.history[-1].known_at == datetime(2024, 5, 12, 23, 59, 59, tzinfo=timezone.utc)
    assert req.history[-1].quantity == series.before(ORIGIN)[-1].sales
    loc, sku, src = req.locations[0], req.skus[0], req.sources[0]
    assert loc.holding_per_value_period == pytest.approx((0.08 + 0.10) / 365)          # a DAILY rate from annual assumptions, never a weekly rate
    assert sku.shelf_life == DEFAULT.economics.shelf_life_days and req.stock[0].expires_in == DEFAULT.economics.shelf_life_days   # periods are days
    assert src.lead_days == 1 and dates(req, src, 0) == (0, 1) and dates(req, src, 3) == (3, 4)   # an order on day t arrives on day t+1
    uncertain = RB.build_request(series, ORIGIN, track="observed", scenario="uncertain")[0].sources[0]
    assert uncertain.lead_days == 2 and dates(req.model_copy(update={"sources": (uncertain,)}), uncertain, 0) == (0, 2)
    assert record["opening_stock"] == pytest.approx(2.0 * np.mean([r.sales for r in series.before(ORIGIN)[-46:]]))
    assert record["evidence"]["supply"] == "SYNTHETIC" and req.sources[0].quote_reference.startswith("SYNTHETIC:")


def test_no_future_information_reaches_the_request():
    series = synthetic_series()
    base = RB.build_request(series, ORIGIN, track="observed", scenario="stable")[0].model_dump_json()
    base_rec = RB.build_request(series, ORIGIN, track="recovered", scenario="stable")[0].model_dump_json()
    future_changed = RB.SeriesDays(1, 2, [replace(r, sales=r.sales * 7, hourly_sales=r.hourly_sales * 7) if r.day >= ORIGIN else r for r in series.records])
    assert RB.build_request(future_changed, ORIGIN, track="observed", scenario="stable")[0].model_dump_json() == base
    assert RB.build_request(future_changed, ORIGIN, track="recovered", scenario="stable")[0].model_dump_json() == base_rec
    with pytest.raises(ValueError, match="needs 16"):
        RB.build_request(series, date(2024, 4, 5), track="observed", scenario="stable")


def test_history_cap_keeps_the_estimator_below_the_weekly_seasonal_candidate():
    series = synthetic_series(days=97)
    req, _ = RB.build_request(series, date(2024, 6, 26), track="observed", scenario="stable")
    assert len(req.history) == DEFAULT.history_days == 63 < 68


def test_truth_shares_one_supply_draw_across_tracks_and_never_uses_the_retailers_stockouts():
    series = synthetic_series(stockout_every=4, seed=4)
    req_a, _ = RB.build_request(series, ORIGIN, track="observed", scenario="uncertain")
    req_b, _ = RB.build_request(series, ORIGIN, track="recovered", scenario="uncertain")
    world, rec = T.truth_world(req_a, series, ORIGIN, track="observed", periods=10, seed=11)
    path_b, _ = T.demand_path(series, ORIGIN, track="recovered", periods=10)
    world_b = T.with_demand(world, req_b, path_b, "b")
    assert world.arrival == world_b.arrival and world.fills == world_b.fills                       # identical supply realization
    svc = req_a.services[0].id
    assert list(world.demand[svc]) == [r.sales for r in series.from_(ORIGIN)[:10]]                 # track A is the observed path
    assert all(b >= a for a, b in zip(world.demand[svc], world_b.demand[svc])) and world_b.demand[svc] != world.demand[svc]
    assert all(world.arrival[k] > k[1] for k in world.arrival) and all(0 <= f <= 1 for f in world.fills.values())
    again, _ = T.truth_world(req_a, series, ORIGIN, track="observed", periods=10, seed=11)
    assert again.arrival == world.arrival and again.fills == world.fills                           # reproducible for a seed
    assert T.truth_world(req_a, series, ORIGIN, track="observed", periods=10, seed=12)[0].fills != world.fills or rec["fill_min"] == rec["fill_max"]


def test_replay_fairness_independent_state_conservation_and_arrival_timing():
    series = synthetic_series(seed=5)
    req, _ = RB.build_request(series, ORIGIN, track="observed", scenario="stable")
    world, _ = T.truth_world(req, series, ORIGIN, track="observed", periods=3 - 1 + req.horizon, seed=1)
    outs = {m: replay(req, world, 3, m, rolling=True) for m in ("order_up_to", "base_stock", "reorder_point")}
    for m, out in outs.items():
        assert out["status"] == "COMPLETE", (m, out.get("failure"))
        for r in out["reviews"]:
            assert abs(float(r["settlement"]["conservation_residual"])) < 1e-9          # stock conservation per review
        # an order placed at review t arrives at t+1 under the stable scenario: it is in the pipeline at t and on hand by t+1's settlement
        q0 = sum(p["quantity"] for p in out["reviews"][0]["purchases"])
        if q0 > 1e-9:
            pending0 = out["reviews"][0]["settlement"]["pending"]
            assert any(abs(p[4] - q0) < 1e-9 for p in pending0)
    # independent state: the policies bought different quantities and ended with different stock, from one identical truth
    bought = {m: round(sum(sum(p["quantity"] for p in r["purchases"]) for r in o["reviews"]), 6) for m, o in outs.items()}
    assert len(set(bought.values())) >= 2
    assert endpoint(req, outs["base_stock"]["reviews"], 3)["W"] == 3
    # reproducibility: the same inputs give identical decisions and settlements (timing fields aside)
    again = replay(req, world, 3, "base_stock", rolling=True)

    def frozen(out):
        return json.dumps([{"purchases": r["purchases"], "ledger": r["settlement"]["ledger"], "end_stock": r["settlement"]["end_stock"],
                            "service": r["settlement"]["service_by_period"]} for r in out["reviews"]], sort_keys=True, default=str)
    assert frozen(again) == frozen(outs["base_stock"])


def test_a_failing_policy_is_recorded_not_dropped(monkeypatch):
    from scripts import frn_pilot
    series = synthetic_series(seed=6)
    req, rec = RB.build_request(series, ORIGIN, track="observed", scenario="stable")
    world, _ = T.truth_world(req, series, ORIGIN, track="observed", periods=2 - 1 + req.horizon, seed=1)
    window = {"origin": ORIGIN, "reviews": 2, "rolling": True, "role": "test"}
    monkeypatch.setitem(frn_pilot.WINDOWS, "test", window)

    def boom(*a, **k):
        raise RuntimeError("solver exploded")
    monkeypatch.setattr(frn_pilot, "replay", boom)
    row = {"store_id": 1, "product_id": 2, "stratum": "x", "volume_class": "a", "stockout_class": "b", "regularity_class": "c", "promo_class": "d"}
    result = frn_pilot.run_one(series, row, "test", "observed", "stable", "gated", req_by_track={"observed": (req, rec)}, world=world, stage_dir=Path("."))
    assert result["status"] == "EXCEPTION" and "solver exploded" in result["error"] and result["policy"] == "gated"


def test_declaration_is_versioned_hashed_and_daily():
    d = DEFAULT.as_dict()
    assert d["version"] == "frn-declaration-1" and d["period_days"] == 1 and len(d["hash"]) == 64
    assert {s["name"] for s in d["supply"]} >= {"stable", "uncertain"}
    assert d["economics"]["holding_per_value_day"] == pytest.approx(0.18 / 365)
    assert Declaration(economics=Economics(unit_cost=2.0)).hash() != DEFAULT.hash()
    assert "SYNTHETIC" in d["evidence"]["supply"] and "UNAVAILABLE" in d["evidence"]["prices_costs_units"]


@needs_dataset
def test_loaded_dataset_matches_the_audited_manifest_and_selection_is_frozen():
    conn = loader.connect()
    m = loader.manifest_record(conn)
    for name, spec in loader.MANIFEST.items():
        assert m[name]["sha256"] == spec["sha256"] and m[name]["rows"] == spec["rows"]
    frozen = json.loads(Path("docs/remodel/evidence/frn/SELECTION_MANIFEST.json").read_text())
    assert selection.select(conn, count=frozen["count"], seed=frozen["seed"])["selection_hash"] == frozen["selection_hash"]
    assert len(frozen["series"]) == 50 and len({(r["store_id"], r["product_id"]) for r in frozen["series"]}) == 50
    conn.close()
