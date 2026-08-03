"""Comprehensive tests for under-covered optimization variants.

Covers:
  * optimization.cvar_extension.CVaRStochasticLP   (mean-CVaR SP)
  * optimization.scenario_reduction.reduce_scenarios (fast-forward selection)
  * optimization.gamma_robust_lp.GammaRobustLP      (Γ-robust LP sweep)
  * optimization.naive_lastyear_policy             (no-AI baseline)
  * optimization.order_up_to_policy                (order-up-to baseline)
  * optimization.recourse_simulator                (cost decomposition / SL)

Solver stack: Pyomo + HiGHS (appsi_highs). Each solve-based test skips
cleanly if the solver is unavailable so the suite stays green on machines
without HiGHS. All randomness is seeded; no network / LLM.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from optimization.cvar_extension import CVaRStochasticLP
from optimization.gamma_robust_lp import GammaRobustLP
from optimization.lp_baseline import LPBaseline
from optimization.naive_lastyear_policy import (
    NaivePolicyConfig,
    naive_lastyear_commitments,
)
from optimization.order_up_to_policy import order_up_to_commitments
from optimization.recourse_simulator import simulate_recourse
from optimization.scenario_reduction import reduce_scenarios


def _solver_available() -> bool:
    try:
        import pyomo.environ  # noqa: F401  (registers the appsi_highs plugin)
        from pyomo.opt import SolverFactory

        return bool(SolverFactory("appsi_highs").available(exception_flag=False))
    except Exception:
        return False


requires_solver = pytest.mark.skipif(
    not _solver_available(), reason="HiGHS (appsi_highs) solver not available"
)

OPTIMAL = ("optimal", "locallyOptimal")


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def cvar_scenarios():
    """Two-scenario single-product demand: 100 kg vs 200 kg, equal weight.

    Shaped for CVaRStochasticLP.solve: columns
    [scenario_index, scenario_weight, product_id, demand_kg].
    """
    dem = pd.DataFrame(
        [
            {"scenario_index": 0, "scenario_weight": 0.5, "product_id": "P1", "demand_kg": 100.0},
            {"scenario_index": 1, "scenario_weight": 0.5, "product_id": "P1", "demand_kg": 200.0},
        ]
    )
    supply = pd.DataFrame(
        [{"supplier_id": "S1", "product_id": "P1", "capacity_kg": 150.0, "price_per_kg": 2.0}]
    )
    return dem, supply


@pytest.fixture
def lp_demand():
    """10 products × 1 week LP fixture (mirrors test_gamma_robust conventions)."""
    products = [f"PRD-{i:03d}" for i in range(1, 11)]
    demand = pd.DataFrame(
        [
            {"product_id": p, "week_start": "2026-01-01", "demand_kg": 100.0 + i * 20}
            for i, p in enumerate(products)
        ]
    )
    supply = pd.DataFrame(
        [
            {
                "supplier_id": "SUP-001",
                "product_id": p,
                "week_start": "2026-01-01",
                "capacity_kg": 500.0,
                "price_per_kg": 2.0,
            }
            for p in products
        ]
    )
    return demand, supply


def _yield_scenarios(n: int, seed: int = 0) -> pd.DataFrame:
    """N equally weighted single-feature yield scenarios."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(n):
        rows.append(
            {
                "scenario_index": s,
                "scenario_weight": 1.0 / n,
                "yield_kg": float(rng.normal(100.0, 25.0)),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# CVaR extension
# --------------------------------------------------------------------------- #
@requires_solver
def test_cvar_solve_return_shape(cvar_scenarios):
    """Solve returns the documented objective/return-shape contract."""
    dem, supply = cvar_scenarios
    res = CVaRStochasticLP(lambda_weight=0.5).solve(dem, supply)
    for key in ("status", "objective", "x", "spot", "waste", "unmet",
                "eta_var", "cvar", "expected_cost", "lambda", "alpha"):
        assert key in res
    assert res["status"] in OPTIMAL
    assert res["objective"] is not None
    assert res["lambda"] == 0.5
    # x is keyed by (supplier, product); spot/waste keyed by (product, scenario)
    assert all(isinstance(k, tuple) and len(k) == 2 for k in res["x"])
    assert all(isinstance(k, tuple) and len(k) == 2 for k in res["spot"])


@requires_solver
def test_cvar_lambda1_objective_equals_expected_cost(cvar_scenarios):
    """At λ=1 the objective is the pure risk-neutral expected cost.

    With cap=150 kg the risk-neutral plan commits the low-demand level
    (100 kg). Expected cost = first-stage commit (100·$2=200) plus expected
    recourse. In scenario 0 demand is met exactly (cost 0). In scenario 1
    there is a 100 kg gap, and the model now has TWO ways to handle it:
    buy spot at avg_price·multiplier = 2·1.3 = $2.60/kg, or accept the lost
    sale at the default $2.50/kg. It correctly takes the cheaper option, so
    the gap costs 100·2.50 = 250; weighted 0.5·0 + 0.5·250 = 125.
    Total 200 + 125 = 325.

    This test previously asserted 330, which assumed the gap HAD to be
    covered by spot — an artefact of the model lacking an unmet variable
    entirely. Preferring a $2.50 lost sale over a $2.60 spot buy is the
    correct economic call and matches the main two-stage model.
    """
    dem, supply = cvar_scenarios
    rn = CVaRStochasticLP(lambda_weight=1.0).solve(dem, supply)
    assert rn["status"] in OPTIMAL
    assert rn["objective"] == pytest.approx(325.0, abs=1e-4)
    assert rn["expected_cost"] == pytest.approx(325.0, abs=1e-4)
    # Risk-neutral commits the low scenario (100 kg), not the worst case.
    assert sum(rn["x"].values()) == pytest.approx(100.0, abs=1e-4)


@requires_solver
def test_cvar_prefers_cheaper_of_spot_and_lost_sale(cvar_scenarios):
    """The unmet variable must actually be usable, not decorative."""
    dem, supply = cvar_scenarios
    # Lost sale dearer than spot ($9 vs $2.60) -> cover the gap with spot.
    dear = CVaRStochasticLP(lambda_weight=1.0, lost_sale_per_kg_usd=9.0).solve(dem, supply)
    assert sum(v for v in dear["spot"].values() if v) > 1e-6
    assert sum(v for v in dear["unmet"].values() if v) == pytest.approx(0.0, abs=1e-6)
    # Lost sale cheaper than spot -> take the lost sale.
    cheap = CVaRStochasticLP(lambda_weight=1.0, lost_sale_per_kg_usd=0.10).solve(dem, supply)
    assert sum(v for v in cheap["unmet"].values() if v) > 1e-6


@requires_solver
def test_cvar_risk_averse_reduces_recourse_tail(cvar_scenarios):
    """λ=0 (pure CVaR) drives the cost tail no higher than λ=1.

    Minimizing the tail directly cannot produce a larger tail than the
    risk-neutral solution that ignores it.
    """
    dem, supply = cvar_scenarios
    rn = CVaRStochasticLP(lambda_weight=1.0, alpha=0.95).solve(dem, supply)
    ra = CVaRStochasticLP(lambda_weight=0.0, alpha=0.95).solve(dem, supply)
    assert rn["status"] in OPTIMAL and ra["status"] in OPTIMAL
    assert ra["cvar"] <= rn["cvar"] + 1e-6


@requires_solver
def test_cvar_risk_averse_commits_at_least_as_much(cvar_scenarios):
    """A risk-averse (λ=0) plan commits ≥ the risk-neutral (λ=1) plan.

    Hedging against the worst-case (200 kg) scenario means buying more in the
    first stage, not less.
    """
    dem, supply = cvar_scenarios
    rn = CVaRStochasticLP(lambda_weight=1.0).solve(dem, supply)
    ra = CVaRStochasticLP(lambda_weight=0.0).solve(dem, supply)
    rn_commit = sum(v for v in rn["x"].values())
    ra_commit = sum(v for v in ra["x"].values())
    assert ra_commit >= rn_commit - 1e-6


@requires_solver
def test_cvar_single_scenario_degenerate(cvar_scenarios):
    """A single scenario: CVaR == expected cost == realized cost (no tail)."""
    _, supply = cvar_scenarios
    dem = pd.DataFrame(
        [{"scenario_index": 0, "scenario_weight": 1.0, "product_id": "P1", "demand_kg": 120.0}]
    )
    res = CVaRStochasticLP(lambda_weight=0.5, alpha=0.95).solve(dem, supply)
    assert res["status"] in OPTIMAL
    assert res["objective"] is not None
    # Commit exactly meets the lone demand (120 kg ≤ 150 cap) → objective is the
    # first-stage commit cost 120·$2 = 240·0.5(λ) + 0·... ; with no spot/waste the
    # recourse-cost tail (cvar_95) is zero.
    assert sum(res["x"].values()) == pytest.approx(120.0, abs=1e-4)
    # With one scenario there is no tail: CVaR equals the expected cost.
    assert res["cvar"] == pytest.approx(res["expected_cost"], abs=1e-6)


@requires_solver
def test_cvar_zero_demand_is_zero_cost(cvar_scenarios):
    """Zero demand across all scenarios → nothing to commit, objective 0."""
    _, supply = cvar_scenarios
    dem = pd.DataFrame(
        [
            {"scenario_index": 0, "scenario_weight": 0.5, "product_id": "P1", "demand_kg": 0.0},
            {"scenario_index": 1, "scenario_weight": 0.5, "product_id": "P1", "demand_kg": 0.0},
        ]
    )
    res = CVaRStochasticLP(lambda_weight=1.0).solve(dem, supply)
    assert res["status"] in OPTIMAL
    assert res["objective"] == pytest.approx(0.0, abs=1e-6)


@requires_solver
def test_cvar_lambda_sweep_frontier_shape(cvar_scenarios):
    """lambda_sweep returns one row per λ with the documented columns."""
    dem, supply = cvar_scenarios
    frontier = CVaRStochasticLP.lambda_sweep([0.0, 0.5, 1.0], dem, supply)
    assert list(frontier.columns) == [
        "lambda", "objective", "status", "expected_cost", "cvar", "var"]
    assert len(frontier) == 3
    assert frontier["lambda"].tolist() == [0.0, 0.5, 1.0]
    assert frontier["status"].isin(OPTIMAL).all()


# --------------------------------------------------------------------------- #
# Scenario reduction
# --------------------------------------------------------------------------- #
def test_scenario_reduction_reduces_count_and_preserves_mass():
    """Reduces N→K and the retained weights still sum to 1."""
    df = _yield_scenarios(12, seed=1)
    red = reduce_scenarios(df, target_k=4, value_col="yield_kg")
    assert red["scenario_index"].nunique() == 4
    weight_sum = red.drop_duplicates("scenario_index")["scenario_weight"].sum()
    assert weight_sum == pytest.approx(1.0, abs=1e-9)
    # Index is remapped to 0..K-1.
    assert sorted(red["scenario_index"].unique()) == [0, 1, 2, 3]


def test_scenario_reduction_passthrough_when_n_le_k():
    """N ≤ target_k → returns the input unchanged (same scenario count)."""
    df = _yield_scenarios(5, seed=2)
    red = reduce_scenarios(df, target_k=10, value_col="yield_kg")
    assert red["scenario_index"].nunique() == 5
    assert len(red) == len(df)


def test_scenario_reduction_single_target():
    """Reducing to a single scenario collapses all weight onto it."""
    df = _yield_scenarios(8, seed=3)
    red = reduce_scenarios(df, target_k=1, value_col="yield_kg")
    assert red["scenario_index"].nunique() == 1
    assert red["scenario_weight"].drop_duplicates().iloc[0] == pytest.approx(1.0, abs=1e-9)


def test_scenario_reduction_group_cols_path():
    """FIXED: the group_cols branch normalizes over unique scenarios, so the
    per-scenario weights sum to 1.0 (not 1/n_group_members)."""
    rng = np.random.default_rng(7)
    rows = []
    n = 10
    for s in range(n):
        for prod in ("P1", "P2"):
            rows.append(
                {
                    "scenario_index": s,
                    "scenario_weight": 1.0 / n,
                    "product_id": prod,
                    "yield_kg": float(rng.normal(100.0, 20.0)),
                }
            )
    df = pd.DataFrame(rows)
    red = reduce_scenarios(df, target_k=3, value_col="yield_kg", group_cols=["product_id"])
    assert red["scenario_index"].nunique() == 3
    assert red.drop_duplicates("scenario_index")["scenario_weight"].sum() == pytest.approx(
        1.0, abs=1e-9
    )


# --------------------------------------------------------------------------- #
# Γ-robust LP
# --------------------------------------------------------------------------- #
@requires_solver
def test_gamma_zero_matches_deterministic(lp_demand):
    """Γ=0 reduces to the deterministic LP exactly."""
    demand, supply = lp_demand
    det = LPBaseline().solve(demand, supply)["objective"]
    rob = GammaRobustLP(gamma=0).solve(demand, supply)["objective"]
    assert rob == pytest.approx(det, rel=1e-6)


@requires_solver
def test_gamma_sweep_monotone_more_conservative(lp_demand):
    """Cost is non-decreasing as Γ rises (more conservative hedging)."""
    demand, supply = lp_demand
    frontier = GammaRobustLP.gamma_sweep([0, 1, 2, 4, 8, 12], demand, supply)
    assert frontier["status"].isin(OPTIMAL).all()
    objs = frontier["objective"].tolist()
    for prev, curr in zip(objs, objs[1:]):
        assert curr >= prev - 1e-6, f"non-monotone objective: {objs}"
    # Protection saturates once Γ ≥ n (=10 here): every product is fully
    # protected, which is the Soyster (1973) fully-conservative extreme.
    assert frontier.loc[frontier["gamma"] == 12, "n_fully_protected"].iloc[0] == 10
    # And the violation-probability bound tightens as the budget grows.
    bounds = frontier["violation_probability_bound"].tolist()
    for prev, curr in zip(bounds, bounds[1:]):
        assert curr <= prev + 1e-12


@requires_solver
def test_gamma_never_undercuts_deterministic(lp_demand):
    """Γ-robust objective never beats the nominal LP (no free-supply arbitrage)."""
    demand, supply = lp_demand
    det = LPBaseline().solve(demand, supply)["objective"]
    for g in [0, 2, 6, 12]:
        rob = GammaRobustLP(gamma=g).solve(demand, supply)["objective"]
        assert rob >= det - 1e-6


# --------------------------------------------------------------------------- #
# Order-up-to policy
# --------------------------------------------------------------------------- #
def test_order_up_to_includes_safety_buffer():
    """S = mean + z·std; with variability S strictly exceeds the mean."""
    weeks = [date(2026, 1, 5) + timedelta(weeks=i) for i in range(6)]
    vals = [80, 120, 90, 130, 100, 110]
    df = pd.DataFrame(
        [{"product_id": "P1", "week_start": w, "demand_kg": v} for w, v in zip(weeks, vals)]
    )
    levels = order_up_to_commitments(df, service_level=0.95)
    assert set(levels) == {"P1"}
    assert levels["P1"] > float(np.mean(vals))  # buffer added at 95% service


def test_order_up_to_single_observation_no_buffer():
    """< 2 observations → mean only (no invented variance, no buffer)."""
    df = pd.DataFrame([{"product_id": "P1", "week_start": date(2026, 1, 5), "demand_kg": 100.0}])
    levels = order_up_to_commitments(df, service_level=0.95)
    assert levels["P1"] == pytest.approx(100.0)


def test_order_up_to_higher_service_means_higher_level():
    """Raising service level raises the order-up-to level (larger z)."""
    weeks = [date(2026, 1, 5) + timedelta(weeks=i) for i in range(8)]
    rng = np.random.default_rng(11)
    vals = rng.normal(100.0, 30.0, size=8)
    df = pd.DataFrame(
        [{"product_id": "P1", "week_start": w, "demand_kg": float(v)} for w, v in zip(weeks, vals)]
    )
    low = order_up_to_commitments(df, service_level=0.50)["P1"]
    high = order_up_to_commitments(df, service_level=0.95)["P1"]
    assert high > low


def test_order_up_to_lookback_window_limits_history():
    """Only the trailing lookback_weeks of history feed the estimate."""
    weeks = [date(2025, 1, 1) + timedelta(weeks=i) for i in range(30)]
    # Old weeks huge, recent weeks small — a short lookback must ignore the spike.
    vals = [1000.0] * 20 + [50.0] * 10
    df = pd.DataFrame(
        [{"product_id": "P1", "week_start": w, "demand_kg": v} for w, v in zip(weeks, vals)]
    )
    level = order_up_to_commitments(df, service_level=0.90, lookback_weeks=5)
    # Trailing 5 weeks are all 50 → mean ~50, zero variance → level ~50, not ~1000.
    assert level["P1"] == pytest.approx(50.0, abs=1e-6)


# --------------------------------------------------------------------------- #
# Naive last-year policy
# --------------------------------------------------------------------------- #
def _deliveries(rows):
    return pd.DataFrame(
        rows,
        columns=["supplier_id", "product_id", "delivery_date", "qty_received_kg", "qty_rejected_kg"],
    )


def test_naive_empty_input_returns_empty_shaped_frame():
    """Empty training data → empty frame with the solver-output columns."""
    empty = pd.DataFrame(
        columns=["supplier_id", "product_id", "delivery_date", "qty_received_kg", "qty_rejected_kg"]
    )
    out = naive_lastyear_commitments(empty, date(2026, 6, 1), [date(2026, 6, 1)])
    assert list(out.columns) == ["supplier_id", "product_id", "committed_kg", "price_per_kg"]
    assert out.empty


def test_naive_uses_same_week_last_year():
    """A delivery 364 days before the horizon week drives the commitment."""
    horizon = date(2026, 6, 3)
    last_year = horizon - timedelta(days=364)
    train = _deliveries(
        [
            ("S1", "P1", last_year, 100.0, 10.0),  # accepted = 90
            ("S1", "P1", last_year, 50.0, 0.0),  # accepted = 50
        ]
    )
    out = naive_lastyear_commitments(train, date(2026, 6, 1), [horizon])
    row = out[(out["supplier_id"] == "S1") & (out["product_id"] == "P1")].iloc[0]
    assert row["committed_kg"] == pytest.approx(140.0)  # 90 + 50
    assert row["price_per_kg"] == 2.0


def test_naive_fallback_to_trailing_weekly_runrate():
    """No same-week-last-year history → trailing weekly run-rate fallback."""
    decision = date(2026, 6, 1)
    # Four trailing weeks of deliveries, total accepted 400 over 4 weeks → 100/wk.
    rows = []
    for i in range(4):
        rows.append(("S1", "P1", decision - timedelta(weeks=i + 1), 100.0, 0.0))
    train = _deliveries(rows)
    # Horizon week has NO data 364 days prior → fallback path.
    out = naive_lastyear_commitments(
        train, decision, [date(2026, 6, 8)], fallback_lookback_weeks=4
    )
    row = out.iloc[0]
    # weekly run-rate = 400 / 4 = 100, one horizon week → 100 committed.
    assert row["committed_kg"] == pytest.approx(100.0)


def test_naive_deterministic_under_seed():
    """Noise injection is reproducible for a fixed seed."""
    horizon = date(2026, 6, 3)
    last_year = horizon - timedelta(days=364)
    train = _deliveries([("S1", "P1", last_year, 100.0, 0.0)])
    cfg = NaivePolicyConfig(noise_cv=0.3, seed=123)
    a = naive_lastyear_commitments(train, date(2026, 6, 1), [horizon], config=cfg)
    b = naive_lastyear_commitments(
        train, date(2026, 6, 1), [horizon], config=NaivePolicyConfig(noise_cv=0.3, seed=123)
    )
    assert a["committed_kg"].iloc[0] == pytest.approx(b["committed_kg"].iloc[0])


# --------------------------------------------------------------------------- #
# Recourse simulator: cost decomposition + service-level bounds
# --------------------------------------------------------------------------- #
def _avail(*rows):
    return pd.DataFrame(rows, columns=["supplier_id", "product_id", "actual_available_kg"])


def test_recourse_cost_components_sum_to_total():
    """total_cost == commit + spot + waste + lost_sale across mixed products."""
    commit = pd.DataFrame(
        [
            {"supplier_id": "S1", "product_id": "P1", "committed_kg": 60.0, "price_per_kg": 2.0},
            {"supplier_id": "S1", "product_id": "P2", "committed_kg": 100.0, "price_per_kg": 2.0},
        ]
    )
    demand = pd.DataFrame(
        [{"product_id": "P1", "demand_kg": 100.0}, {"product_id": "P2", "demand_kg": 60.0}]
    )
    supply = _avail(("S1", "P1", 60.0), ("S1", "P2", 100.0))
    rec = simulate_recourse(
        commit,
        demand,
        supply,
        spot_capacity={"P1": 20.0},  # P1 shortfall partly lost
        lost_sale_per_kg=3.0,
        spot_cost_multiplier=1.0,
        waste_cost_per_kg=0.5,
    )
    parts = rec["commit_cost"] + rec["spot_cost"] + rec["waste_cost"] + rec["lost_sale_cost"]
    assert rec["total_cost"] == pytest.approx(parts, abs=0.01)
    # All-regime sanity: spot, waste and lost-sale are each exercised.
    assert rec["spot_kg"] == 20.0  # P1 gap 40, capped at 20
    assert rec["lost_sale_kg"] == 20.0  # residual P1 gap
    assert rec["waste_kg"] == 40.0  # P2 oversupply


def test_recourse_service_level_bounds():
    """Service level is always within [0, 100]."""
    # All-spot regime (commit nothing, supply nothing) with finite spot cap.
    commit = pd.DataFrame(columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 100.0}])
    supply = _avail(("S1", "P1", 0.0))
    full_lost = simulate_recourse(
        commit, demand, supply, spot_capacity={"P1": 0.0}, lost_sale_per_kg=1.0
    )
    assert full_lost["service_level_pct"] == 0.0

    full_met = simulate_recourse(commit, demand, supply)  # unlimited spot
    assert full_met["service_level_pct"] == 100.0
    for rec in (full_lost, full_met):
        assert 0.0 <= rec["service_level_pct"] <= 100.0


def test_recourse_all_waste_regime():
    """Demand far below committed supply → pure waste, full service, no spot."""
    commit = pd.DataFrame(
        [{"supplier_id": "S1", "product_id": "P1", "committed_kg": 100.0, "price_per_kg": 2.0}]
    )
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 30.0}])
    supply = _avail(("S1", "P1", 100.0))
    rec = simulate_recourse(commit, demand, supply, waste_cost_per_kg=0.5)
    assert rec["spot_kg"] == 0.0
    assert rec["lost_sale_kg"] == 0.0
    assert rec["waste_kg"] == 70.0
    assert rec["waste_cost"] == pytest.approx(35.0)
    assert rec["service_level_pct"] == 100.0


def test_recourse_zero_demand_full_service():
    """Zero total demand → 100% service by convention, zero recourse."""
    commit = pd.DataFrame(columns=["supplier_id", "product_id", "committed_kg", "price_per_kg"])
    demand = pd.DataFrame([{"product_id": "P1", "demand_kg": 0.0}])
    supply = _avail(("S1", "P1", 0.0))
    rec = simulate_recourse(commit, demand, supply)
    assert rec["service_level_pct"] == 100.0
    assert rec["total_cost"] == 0.0
