import numpy as np
import pytest

from risk.supply_paths import build_supply_paths


def _hist(n=30, seed=0):
    rng = np.random.default_rng(seed)
    h = {}
    for s in ("S1", "S2", "S3"):
        h[s] = {}
        for t in range(-n, 0):
            base = 0.95 if t < -10 else 0.6        # a shared episode in the last 10 periods
            h[s][t] = (float(np.clip(rng.normal(base, 0.03), 0, 1)), int(2 if t < -10 else 4))
    h["S3"] = {t: v for t, v in h["S3"].items() if t % 2 == 0}   # sparse supplier
    return h


def test_keys_are_time_varying_and_complete():
    p = build_supply_paths(_hist(), ["S1", "S2", "S3"], n_scen=5, horizon=8, rng=np.random.default_rng(1))
    assert len(p.fills) == 5 * 3 * 8 and len(p.leads) == 5 * 3 * 8
    assert all(0 <= v <= 1 for v in p.fills.values()) and all(v >= 0 for v in p.leads.values())
    assert p.method == "moving_block_bootstrap" and any("last known" in a for a in p.assumptions)


def test_cross_supplier_comovement_is_preserved():
    """Blocks copy every supplier at once, so S1 and S2 share the episode."""
    p = build_supply_paths(_hist(), ["S1", "S2"], n_scen=200, horizon=6, rng=np.random.default_rng(2), block_length=3)
    a = np.array([p.fills[(w, "S1", 0)] for w in range(200)])
    b = np.array([p.fills[(w, "S2", 0)] for w in range(200)])
    assert np.corrcoef(a, b)[0, 1] > 0.8


def test_temporal_persistence_within_a_block():
    p = build_supply_paths(_hist(), ["S1"], n_scen=300, horizon=3, rng=np.random.default_rng(3), block_length=3)
    same = np.mean([abs(p.fills[(w, "S1", 0)] - p.fills[(w, "S1", 1)]) < 0.2 for w in range(300)])
    assert same > 0.85


def test_future_history_is_ignored():
    h = _hist()
    h["S1"][5] = (0.0, 50)          # a 'future' observation must never be used
    p = build_supply_paths(h, ["S1"], n_scen=50, horizon=4, rng=np.random.default_rng(4))
    assert all(v < 50 for v in p.leads.values()) and all(v > 0 for v in p.fills.values())


def test_route_overlay_hits_every_member_and_reports_assumptions():
    p = build_supply_paths(_hist(), ["S1", "S2", "S3"], n_scen=40, horizon=10, rng=np.random.default_rng(5),
                           route_of={"S1": "aqaba", "S2": "aqaba", "S3": "local"},
                           route_disruption={"aqaba": {"fill_mult": 0.5, "lead_mult": 2.0, "p_start": 0.5, "p_end": 0.2}})
    hit = [(w, t) for (w, r, t), on in p.disrupted.items() if on and r == "aqaba"]
    assert hit, "overlay never fired"
    w, t = hit[0]
    plain = build_supply_paths(_hist(), ["S1", "S2", "S3"], n_scen=40, horizon=10, rng=np.random.default_rng(5))
    assert p.fills[(w, "S1", t)] <= plain.fills[(w, "S1", t)] + 1e-9
    assert p.fills[(w, "S3", t)] == pytest.approx(plain.fills[(w, "S3", t)])   # local untouched
    assert any("ASSUMED" in a for a in p.assumptions)


def test_no_history_falls_back_to_labelled_defaults():
    p = build_supply_paths({}, ["S1"], n_scen=2, horizon=3, rng=np.random.default_rng(0))
    assert p.method == "defaults" and p.assumptions and p.coverage == {"S1": 0}
