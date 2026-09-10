"""Indicator loaders, the leading outlook, the lead/lag check and the
efficiency/protection modes end to end through the engine."""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone

import numpy as np

from adaptive.indicators import load_chokepoints, load_fred_like
from adaptive.leading import Outlook, demand_outlook, disruption_outlook, lead_lag
from adaptive.signals import Signal, SignalStore
from adaptive.state_estimator import supplier_state

AS_OF = datetime(2024, 3, 1, tzinfo=timezone.utc)


def _add(store, et, eid, metric, value, days_ago=3, quality=0.8):
    store.add(Signal(AS_OF - timedelta(days=days_ago), et, eid, metric, value, "REAL_PUBLIC", quality))


def test_outlook_is_low_at_norm_and_rises_with_chokepoint_and_port_evidence():
    st_ = SignalStore(max_age_days=75)
    _add(st_, "chokepoint", "BAB EL-MANDEB STRAIT", "chokepoint_transit_index", 1.0)
    _add(st_, "chokepoint", "SUEZ CANAL", "chokepoint_transit_index", 1.0)
    _add(st_, "port", "AQABA", "throughput_index", 1.0)
    _add(st_, "region", "GLOBAL", "gscpi", 0.0)
    _add(st_, "region", "GLOBAL", "fuel_index", 1.0)
    _add(st_, "region", "US", "freight_index_yoy", 0.0)
    _add(st_, "topic", "RED_SEA_SHIPPING", "conflict_index", 1.0)
    calm = disruption_outlook(st_, "red_sea", AS_OF)
    assert calm.risk < 0.2 and calm.quality > 0.9 and not calm.missing
    hot = SignalStore(max_age_days=75)
    _add(hot, "chokepoint", "BAB EL-MANDEB STRAIT", "chokepoint_transit_index", 0.45)
    _add(hot, "chokepoint", "SUEZ CANAL", "chokepoint_transit_index", 0.6)
    _add(hot, "port", "AQABA", "throughput_index", 0.9)
    _add(hot, "topic", "RED_SEA_SHIPPING", "conflict_index", 3.0)
    h = disruption_outlook(hot, "red_sea", AS_OF)
    assert h.risk > 0.8 and h.quality < calm.quality          # three feeds missing lowers quality
    assert any("transits" in r for r in h.reasons) and h.missing


def test_missing_feeds_reduce_quality_never_read_as_normal():
    empty = SignalStore()
    o = disruption_outlook(empty, "red_sea", AS_OF)
    assert o.quality == 0.0 and any("UNAVAILABLE" in r for r in o.reasons)
    # an unknown lane has no chokepoints, port or topic: only the global feeds could contribute
    u = disruption_outlook(empty, "moon", AS_OF)
    assert u.quality == 0.0


def test_stale_feed_counts_half():
    fresh = SignalStore(max_age_days=30)
    _add(fresh, "chokepoint", "SUEZ CANAL", "chokepoint_transit_index", 0.5, days_ago=3)
    stale = SignalStore(max_age_days=30)
    _add(stale, "chokepoint", "SUEZ CANAL", "chokepoint_transit_index", 0.5, days_ago=60)
    assert disruption_outlook(fresh, "suez", AS_OF).risk > disruption_outlook(stale, "suez", AS_OF).risk


def test_outlook_feeds_the_supplier_state_as_watch_evidence():
    fills, leads = [0.96] * 12, [2] * 12
    base = supplier_state("S", fills, leads, None, None)
    o = Outlook("red_sea", risk=0.7, quality=0.9, reasons=["Bab el-Mandeb transits at 45% of their trailing norm"])
    warned = supplier_state("S", fills, leads, None, None, outlook=o)
    assert warned.probabilities["WATCH"] > base.probabilities["WATCH"]
    assert warned.stress > base.stress
    assert any("leading indicators" in r for r in warned.reasons)
    weak = supplier_state("S", fills, leads, None, None, outlook=Outlook("red_sea", risk=0.7, quality=0.1))
    assert weak.probabilities["WATCH"] < warned.probabilities["WATCH"]


def test_demand_outlook_uses_retail_and_sentiment():
    st_ = SignalStore()
    _add(st_, "region", "US", "demand_index_yoy", 0.12)
    _add(st_, "region", "US", "sentiment_z", 1.0)
    hot = demand_outlook(st_, "US", AS_OF)
    assert hot.risk > 0.6 and hot.quality == 1.0
    assert demand_outlook(SignalStore(), "US", AS_OF).quality == 0.0


def test_lead_lag_finds_a_planted_lead_and_rejects_noise():
    rng = np.random.default_rng(0)
    t0 = AS_OF - timedelta(weeks=120)
    base = rng.normal(0, 1, 120)
    ind = [(t0 + timedelta(weeks=k), float(base[k])) for k in range(120)]
    out = [(t0 + timedelta(weeks=k), float(base[k - 4]) + rng.normal(0, 0.3)) for k in range(4, 120)]
    r = lead_lag(ind, out, max_lead_weeks=8)
    assert r["best_lead_weeks"] == 4 and r["leads"]
    noise = [(t0 + timedelta(weeks=k), float(rng.normal())) for k in range(120)]
    assert not lead_lag(ind, noise, max_lead_weeks=8)["leads"]


def test_chokepoint_loader_indexes_against_own_norm(tmp_path):
    p = tmp_path / "cp.csv"
    with p.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "portname", "n_total"])
        d0 = datetime(2023, 1, 1)
        for k in range(500):
            n = 60 if k < 430 else 30                        # halves for the last 70 days
            w.writerow([(d0 + timedelta(days=k)).strftime("%Y-%m-%d"), "Suez Canal", n])
    st_ = SignalStore()
    n = load_chokepoints(st_, p, names=("Suez Canal",), step_days=7)
    assert n > 0
    xs = st_.series("chokepoint", "SUEZ CANAL", "chokepoint_transit_index")
    assert abs(xs[-1].value - 0.5) < 0.05 and abs(xs[len(xs) // 2].value - 1.0) < 0.05
    assert xs[-1].provenance == "REAL_PUBLIC" and "PortWatch" in xs[-1].transform


def test_fred_like_yoy_and_z(tmp_path, monkeypatch):
    import adaptive.indicators as ind
    monkeypatch.setattr(ind, "IND", tmp_path)
    with (tmp_path / "retail.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "value"])
        for k in range(36):
            y, m = 2021 + k // 12, k % 12 + 1
            w.writerow([f"{y}-{m:02d}-01", 100 * (1.1 ** (k // 12))])
    st_ = SignalStore()
    assert load_fred_like(st_, "retail", "region", "US", "demand_index_yoy", "yoy") == 24
    assert abs(st_.latest("region", "US", "demand_index_yoy").value - 0.1) < 1e-9
