"""Correctness properties of the stochastic optimization stack.

These test MATHEMATICAL PROPERTIES that must hold regardless of data —
theorems, not behaviours. Each references the result it enforces, so a
failure points at the violated theory rather than at a magic number.

References
----------
Birge, J.R. & Louveaux, F. (1997). *Introduction to Stochastic
    Programming*, Springer. Ch. 4 "The Value of Information and the
    Stochastic Solution", pp. 137-152.
    - Proposition 1 (p. 140):  WS <= RP <= EEV
    - Proposition 5 (p. 142):  VSS >= 0 and EVPI >= 0 for any program
    - p. 142: VSS = 0 when the optimal first-stage decision does not
      depend on the realisation.
    - Section 1.1e (pp. 15-18): newsvendor, x* = F^-1(c_u/(c_u+c_o)).
Rockafellar, R.T. & Uryasev, S. (2000). "Optimization of conditional
    value-at-risk." *Journal of Risk* 2(3):21-42.
    - Theorem 1: CVaR_a(Z) = min_eta { eta + (1-a)^-1 E[(Z-eta)+] };
      CVaR >= VaR, and CVaR >= E[Z].
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from optimization.cvar_extension import CVaRStochasticLP
from optimization.lp_baseline import LPBaseline
from optimization.two_stage_sp import TwoStageStochasticLP, _normalized_weights


def _solver_available() -> bool:
    try:
        import pyomo.environ  # noqa: F401
        from pyomo.opt import SolverFactory
        return bool(SolverFactory("appsi_highs").available(exception_flag=False))
    except Exception:
        return False


requires_solver = pytest.mark.skipif(
    not _solver_available(), reason="HiGHS (appsi_highs) solver not available")

WEEK = pd.Timestamp("2024-06-03")


def _normal_scenarios(mu=1000.0, sd=250.0, n=200, seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    draws = rng.normal(mu, sd, size=n)
    return pd.DataFrame([
        {"scenario_index": k, "scenario_weight": 1.0 / n, "product_id": "P1",
         "week_start": WEEK, "demand_kg": float(max(v, 0.0))}
        for k, v in enumerate(draws)
    ])


def _ample_supply(price=2.0) -> pd.DataFrame:
    return pd.DataFrame([{
        "supplier_id": "S1", "product_id": "P1", "week_start": WEEK,
        "capacity_kg": 50_000.0, "price_per_kg": price,
    }])


def _newsvendor(cu: float, co: float) -> TwoStageStochasticLP:
    """Pure newsvendor: overage co, underage cu, spot priced out of reach."""
    return TwoStageStochasticLP(
        newsvendor_objective=True,
        waste_cost_by_product={"P1": co},
        unmet_cost_by_product={"P1": cu},
        spot_cost_multiplier=99.0,
    )


# ── VSS: the property that was previously computed wrong ────────────────────

class TestValueOfStochasticSolution:
    """VSS = EEV - RP (Birge & Louveaux Ch. 4).

    The previous implementation returned EV_objective - RP, a different
    quantity that is typically NEGATIVE (EV solves an easier, averaged
    problem, so EV <= RP). It reported a negative "value" for stochastic
    modelling; measured at -5,383 on an asymmetric instance before the fix.
    """

    @requires_solver
    def test_vss_is_nonnegative(self):
        """Proposition 5(a): VSS >= 0 for any stochastic program."""
        out = _newsvendor(6.0, 2.0).compute_vss(_normal_scenarios(), _ample_supply())
        assert out["vss"] is not None
        assert out["vss"] >= -1e-6, f"VSS must be nonnegative, got {out['vss']}"

    @requires_solver
    def test_ordering_ev_le_rp_le_eev(self):
        """Proposition 1: RP <= EEV; and EV <= RP for fixed recourse."""
        out = _newsvendor(6.0, 2.0).compute_vss(_normal_scenarios(), _ample_supply())
        ev, rp, eev = out["ev_objective"], out["rp_objective"], out["eev_objective"]
        assert ev <= rp + 1e-6, f"EV ({ev}) must not exceed RP ({rp})"
        assert rp <= eev + 1e-6, f"RP ({rp}) must not exceed EEV ({eev})"

    @requires_solver
    def test_vss_grows_with_cost_asymmetry(self):
        """The structural driver of VSS.

        VSS = 0 when the EV first-stage decision is already optimal for the
        distribution. For a newsvendor the RP optimum is the critical
        fractile F^-1(c_u/(c_u+c_o)) while EV commits the mean, so the two
        coincide exactly when that fractile lands on the mean — symmetric
        costs over a symmetric distribution. Push the costs apart and VSS
        must grow.
        """
        scen, supply = _normal_scenarios(), _ample_supply()
        vss = [_newsvendor(cu, co).compute_vss(scen, supply)["vss"]
               for cu, co in ((3.0, 3.0), (4.0, 2.0), (6.0, 2.0), (9.0, 1.0))]
        assert all(a <= b + 1e-6 for a, b in zip(vss, vss[1:])), vss
        assert vss[0] < 0.02 * vss[-1], (
            f"symmetric-cost VSS should be near zero next to the most "
            f"asymmetric case, got {vss}")

    @requires_solver
    def test_symmetric_costs_give_near_zero_vss(self):
        """Symmetric costs + symmetric demand -> deterministic plan is optimal."""
        out = _newsvendor(3.0, 3.0).compute_vss(_normal_scenarios(), _ample_supply())
        assert out["vss_pct_of_eev"] < 1.0, (
            "with a critical fractile of 0.5 over symmetric demand the EV "
            "solution is already optimal, so VSS should be ~0 "
            f"(got {out['vss_pct_of_eev']}%)")
        assert "essentially zero" in out["interpretation"]

    @requires_solver
    def test_reports_components_for_audit(self):
        out = _newsvendor(6.0, 2.0).compute_vss(_normal_scenarios(), _ample_supply())
        for key in ("vss", "rp_objective", "ev_objective", "eev_objective",
                    "vss_pct_of_eev", "definition", "interpretation"):
            assert key in out


# ── The SP must reproduce the analytical newsvendor ─────────────────────────

class TestNewsvendorRecovery:
    @requires_solver
    @pytest.mark.parametrize("cu,co", [(4.0, 2.0), (6.0, 2.0), (9.0, 1.0)])
    def test_recovers_critical_fractile(self, cu, co):
        """The LP's commitment must match F^-1(c_u/(c_u+c_o)).

        Checked against the EMPIRICAL quantile of the sampled scenarios,
        not the theoretical normal one, since SAA optimises the sample.
        """
        scen = _normal_scenarios(n=400)
        demands = scen["demand_kg"].to_numpy()
        fractile = cu / (cu + co)
        expected = float(np.quantile(demands, fractile))

        result = _newsvendor(cu, co).solve(scen, _ample_supply())
        committed = sum(v for v in result["x"].values() if v)
        assert committed == pytest.approx(expected, rel=0.05), (
            f"critical fractile {fractile:.3f} implies {expected:,.0f} kg, "
            f"solver committed {committed:,.0f} kg")

    @requires_solver
    def test_commitment_increases_with_underage_cost(self):
        """Costlier stockouts must never reduce the commitment."""
        scen, supply = _normal_scenarios(), _ample_supply()
        commits = []
        for cu in (3.0, 5.0, 8.0, 12.0):
            r = _newsvendor(cu, 2.0).solve(scen, supply)
            commits.append(sum(v for v in r["x"].values() if v))
        assert all(a <= b + 1e-6 for a, b in zip(commits, commits[1:])), commits


# ── Spot pricing: the fallback-key defect ───────────────────────────────────

class TestSpotPricing:
    """LPBaseline priced spot from price[(None, j, t)] — a key that can never
    exist, so every spot purchase silently used the 2.0 fallback. With real
    prices above 2.0 spot looked cheaper than any contract, and the LP
    committed nothing and bought everything on spot."""

    @requires_solver
    def test_spot_priced_from_real_contract_prices(self):
        supply = _ample_supply(price=10.0)
        demand = pd.DataFrame([{"product_id": "P1", "week_start": WEEK,
                                "demand_kg": 1000.0}])
        r = LPBaseline(lost_sale_per_kg_usd=50.0).solve(demand, supply)
        committed = sum(v for v in r["x"].values() if v)
        spot = sum(v for v in r["spot"].values() if v)
        assert committed == pytest.approx(1000.0, abs=1e-3)
        assert spot == pytest.approx(0.0, abs=1e-6)
        # 1000 kg at the real 10.00/kg, NOT at the 2.0 fallback.
        assert r["objective"] == pytest.approx(10_000.0, rel=1e-6)

    @requires_solver
    def test_spot_used_when_genuinely_cheaper_than_lost_sale(self):
        supply = _ample_supply(price=1.0)     # spot = 1.30/kg
        demand = pd.DataFrame([{"product_id": "P1", "week_start": WEEK,
                                "demand_kg": 100.0}])
        # No contract capacity at all -> must choose spot vs lost sale.
        supply.loc[0, "capacity_kg"] = 0.0
        r = LPBaseline(lost_sale_per_kg_usd=5.0).solve(demand, supply)
        assert sum(v for v in r["spot"].values() if v) == pytest.approx(100.0, abs=1e-3)


# ── Scenario weights ────────────────────────────────────────────────────────

class TestScenarioWeights:
    def test_missing_weight_gets_uniform_share(self):
        w = _normalized_weights({0: 0.5}, [0, 1])
        assert set(w) == {0, 1}
        assert sum(w.values()) == pytest.approx(1.0)

    def test_unnormalized_weights_are_rescaled(self):
        w = _normalized_weights({0: 5.0, 1: 5.0, 2: 10.0}, [0, 1, 2])
        assert sum(w.values()) == pytest.approx(1.0)
        assert w[2] == pytest.approx(0.5)

    def test_degenerate_zero_weights_fall_back_to_uniform(self):
        w = _normalized_weights({0: 0.0, 1: 0.0}, [0, 1])
        assert w == {0: 0.5, 1: 0.5}

    def test_relative_proportions_preserved(self):
        w = _normalized_weights({0: 1.0, 1: 3.0}, [0, 1])
        assert w[1] == pytest.approx(3.0 * w[0])

    @requires_solver
    def test_unnormalized_input_does_not_change_the_decision(self):
        """Scaling every weight by a constant must not move the optimum.

        Without normalisation the expectation term is multiplied by that
        constant while the first-stage cost is not, which silently changes
        the trade-off between them.
        """
        scen = _normal_scenarios(n=60)
        doubled = scen.copy()
        doubled["scenario_weight"] = doubled["scenario_weight"] * 2.0
        sp = _newsvendor(6.0, 2.0)
        a = sum(v for v in sp.solve(scen, _ample_supply())["x"].values() if v)
        b = sum(v for v in sp.solve(doubled, _ample_supply())["x"].values() if v)
        assert a == pytest.approx(b, rel=1e-6)


# ── CVaR properties ─────────────────────────────────────────────────────────

class TestOutOfSampleVSS:
    """VSS measured on common held-out scenarios, with a bootstrap CI.

    ``compute_vss`` is in-sample: both decisions are optimised against the
    same scenarios they are scored on, which flatters the richer model. And
    a single point estimate hides sampling noise that, at our scenario
    counts, is worth several percent of the objective.
    """

    @requires_solver
    def test_reports_a_bootstrap_interval(self):
        from optimization.vss_evaluation import out_of_sample_vss

        res = out_of_sample_vss(
            _newsvendor(9.0, 1.0), _normal_scenarios(n=60), _ample_supply(),
            n_bootstrap=40, seed=1)
        assert res is not None
        # A percentile bootstrap interval is ordered, but does NOT
        # mathematically guarantee it contains the point estimate — asserting
        # that was brittle. Check the properties that do hold.
        assert res.ci_low <= res.ci_high
        d = res.to_dict()
        for k in ("vss_out_of_sample", "ci_low", "ci_high", "verdict",
                  "beneficial", "harmful", "inconclusive", "significant",
                  "n_eval_scenarios", "definition", "interpretation"):
            assert k in d
        assert "common out-of-sample" in d["definition"]

    def test_three_states_are_mutually_exclusive_and_exhaustive(self):
        """Regression: a wholly NEGATIVE interval is evidence of harm.

        The earlier classification had only `significant = ci_low > 0` and
        described everything else as "includes zero" — so [-9.70, -0.92],
        which excludes zero entirely and shows the stochastic policy losing
        out-of-sample, was reported as merely not significant. That turned
        evidence of harm into a null result.
        """
        from optimization.vss_evaluation import VSSResult

        def mk(lo, hi, vss):
            return VSSResult(vss=vss, vss_pct_of_eev=0.0, rp_cost_oos=100.0,
                             eev_cost_oos=100.0, ci_low=lo, ci_high=hi,
                             ci_level=0.9, n_bootstrap=100,
                             n_train_scenarios=30, n_eval_scenarios=30)

        good = mk(140.0, 314.0, 230.0)
        bad = mk(-9.70, -0.92, -5.52)
        null = mk(-50.0, 80.0, 12.0)

        assert good.verdict == "beneficial" and good.beneficial
        assert bad.verdict == "harmful" and bad.harmful
        assert null.verdict == "inconclusive" and null.inconclusive

        for r in (good, bad, null):
            flags = [r.beneficial, r.harmful, r.inconclusive]
            assert sum(flags) == 1, "states must be mutually exclusive"

        # A wholly negative interval is SIGNIFICANT, and must say so.
        assert bad.significant is True
        assert "WORSE" in bad.interpretation()
        assert "includes zero" not in bad.interpretation()
        assert "contains zero" in null.interpretation()
        assert "IMPROVED" in good.interpretation()

    @requires_solver
    def test_rejects_non_uniform_scenario_weights(self):
        """Reduced scenario sets carry unequal probabilities this path
        cannot honour; refusing beats returning a number computed against
        the wrong measure."""
        from optimization.vss_evaluation import (
            NonUniformWeightsUnsupported,
            out_of_sample_vss,
        )

        scen = _normal_scenarios(n=40)
        scen.loc[scen["scenario_index"] < 10, "scenario_weight"] = 0.05
        with pytest.raises(NonUniformWeightsUnsupported, match="not uniform"):
            out_of_sample_vss(_newsvendor(6.0, 2.0), scen, _ample_supply(),
                              n_bootstrap=5)

    def test_weighted_mean_demand_respects_probabilities(self):
        """A plain groupby mean silently assumes equiprobability."""
        from optimization.vss_evaluation import _weighted_mean_demand

        df = pd.DataFrame([
            {"scenario_index": 0, "scenario_weight": 0.9,
             "product_id": "P1", "demand_kg": 100.0},
            {"scenario_index": 1, "scenario_weight": 0.1,
             "product_id": "P1", "demand_kg": 200.0},
        ])
        out = _weighted_mean_demand(df)
        assert float(out.loc[0, "demand_kg"]) == pytest.approx(110.0)
        # The unweighted mean would have been 150.
        assert float(out.loc[0, "demand_kg"]) != pytest.approx(150.0)

    def test_reindex_preserves_relative_probabilities(self):
        from optimization.vss_evaluation import _reindex

        df = pd.DataFrame([
            {"scenario_index": 0, "scenario_weight": 0.6,
             "product_id": "P1", "demand_kg": 1.0},
            {"scenario_index": 1, "scenario_weight": 0.2,
             "product_id": "P1", "demand_kg": 2.0},
        ])
        out = _reindex(df, np.array([0, 1]))
        w = out.drop_duplicates("scenario_index")["scenario_weight"].to_numpy()
        assert w.sum() == pytest.approx(1.0)
        assert w[0] / w[1] == pytest.approx(3.0)      # 0.6 : 0.2 preserved

    @requires_solver
    def test_train_and_eval_sets_are_disjoint(self):
        from optimization.vss_evaluation import out_of_sample_vss

        res = out_of_sample_vss(
            _newsvendor(6.0, 2.0), _normal_scenarios(n=60), _ample_supply(),
            n_bootstrap=20, train_fraction=0.5, seed=2)
        assert res.n_train_scenarios + res.n_eval_scenarios == 60

    @requires_solver
    def test_symmetric_costs_do_not_show_a_benefit(self):
        """At symmetric costs the deterministic plan is already optimal, so
        the honest out-of-sample verdict must not be 'beneficial'."""
        from optimization.vss_evaluation import out_of_sample_vss

        res = out_of_sample_vss(
            _newsvendor(3.0, 3.0), _normal_scenarios(n=60), _ample_supply(),
            n_bootstrap=60, seed=3)
        assert res is not None
        assert res.verdict in ("inconclusive", "harmful")
        assert not res.beneficial
        assert res.verdict == "harmful" or "contains zero" in res.interpretation()

    @requires_solver
    def test_asymmetric_costs_show_a_benefit(self):
        from optimization.vss_evaluation import out_of_sample_vss

        res = out_of_sample_vss(
            _newsvendor(9.0, 1.0), _normal_scenarios(n=80), _ample_supply(),
            n_bootstrap=80, seed=4)
        assert res is not None and res.verdict == "beneficial"
        assert "IMPROVED" in res.interpretation()

    @requires_solver
    def test_refuses_when_too_few_scenarios(self):
        from optimization.vss_evaluation import out_of_sample_vss

        assert out_of_sample_vss(
            _newsvendor(6.0, 2.0), _normal_scenarios(n=3), _ample_supply(),
            n_bootstrap=5) is None


class TestSAABounds:
    """Kleywegt, Shapiro & Homem-de-Mello (2002) §2.3, §3.2-3.3.

    The SAA objective is downward-biased for a minimisation problem
    (E[v_N] <= v*), so a solved objective on few scenarios looks better
    than the truth. These check the diagnostic that surfaces it.
    """

    @requires_solver
    def test_objective_rises_and_spread_falls_with_n(self):
        """The bias shrinks and replications agree more as N grows."""
        from optimization.saa_bounds import scenario_count_curve

        pool = _normal_scenarios(n=300, seed=3)
        curve = scenario_count_curve(
            _newsvendor(6.0, 2.0), pool, _ample_supply(),
            counts=(10, 50, 200), n_replications=5)
        assert len(curve) == 3
        # Downward bias shrinks: the mean objective trends up with N.
        assert curve.iloc[-1]["mean_objective"] > curve.iloc[0]["mean_objective"]
        # And the replications converge: coefficient of variation falls.
        assert curve.iloc[-1]["cv_pct"] < curve.iloc[0]["cv_pct"]

    @requires_solver
    def test_gap_shrinks_with_scenario_count(self):
        """A larger N must not leave a wider optimality gap."""
        from optimization.saa_bounds import estimate_optimality_gap

        pool = _normal_scenarios(n=300, seed=3)
        small = estimate_optimality_gap(
            _newsvendor(6.0, 2.0), pool, _ample_supply(),
            n_scenarios=10, n_replications=6)
        large = estimate_optimality_gap(
            _newsvendor(6.0, 2.0), pool, _ample_supply(),
            n_scenarios=200, n_replications=6)
        assert small is not None and large is not None
        assert large.gap_pct < small.gap_pct

    @requires_solver
    def test_lower_bound_below_upper_bound(self):
        """LB estimates v* from below, UB evaluates a feasible decision."""
        from optimization.saa_bounds import estimate_optimality_gap

        res = estimate_optimality_gap(
            _newsvendor(6.0, 2.0), _normal_scenarios(n=300, seed=3),
            _ample_supply(), n_scenarios=50, n_replications=6)
        assert res is not None
        assert res.lower_bound <= res.upper_bound + 1e-6
        assert res.gap >= -1e-6

    @requires_solver
    def test_result_reports_sufficiency_verdict(self):
        from optimization.saa_bounds import estimate_optimality_gap

        res = estimate_optimality_gap(
            _newsvendor(6.0, 2.0), _normal_scenarios(n=300, seed=3),
            _ample_supply(), n_scenarios=10, n_replications=6)
        d = res.to_dict()
        for key in ("lower_bound", "upper_bound", "optimality_gap_pct",
                    "sufficient", "interpretation", "method"):
            assert key in d
        # A 10-scenario run must not be declared sufficient.
        assert d["sufficient"] is False


class TestCVaRProperties:
    @requires_solver
    def test_cvar_at_least_expected_cost(self):
        """CVaR_a(Z) >= E[Z] for any a in (0,1) — a tail average cannot sit
        below the overall mean."""
        scen = _normal_scenarios(n=100)
        r = CVaRStochasticLP(lambda_weight=0.5, alpha=0.90).solve(scen, _ample_supply())
        assert r["cvar"] >= r["expected_cost"] - 1e-6

    @requires_solver
    def test_cvar_at_least_var(self):
        """CVaR >= VaR: the tail mean dominates the tail threshold."""
        scen = _normal_scenarios(n=100)
        r = CVaRStochasticLP(lambda_weight=0.5, alpha=0.90).solve(scen, _ample_supply())
        assert r["cvar"] >= r["eta_var"] - 1e-6

    @requires_solver
    def test_non_uniform_weights_change_the_cvar(self):
        """The risk term must use the scenario probabilities.

        It previously averaged the tail with a uniform 1/N while the
        expectation term used p_w — so with the non-uniform weights that
        scenario reduction produces, the estimator was simply wrong.
        Concentrating probability on the worst scenarios must raise CVaR.
        """
        scen = _normal_scenarios(n=60)
        skewed = scen.copy()
        worst = skewed["demand_kg"] >= skewed["demand_kg"].quantile(0.8)
        skewed.loc[worst, "scenario_weight"] = 4.0
        skewed.loc[~worst, "scenario_weight"] = 1.0

        solver = CVaRStochasticLP(lambda_weight=0.0, alpha=0.90,
                                  lost_sale_per_kg_usd=9.0)
        base = solver.solve(scen, _ample_supply())
        tilted = solver.solve(skewed, _ample_supply())
        assert tilted["cvar"] != pytest.approx(base["cvar"], rel=1e-9)

    @requires_solver
    def test_risk_aversion_never_lowers_commitment(self):
        """A risk-averse plan hedges by committing at least as much."""
        scen = _normal_scenarios(n=80)
        kw = dict(lost_sale_per_kg_usd=9.0, waste_cost_per_kg=1.0)
        rn = CVaRStochasticLP(lambda_weight=1.0, **kw).solve(scen, _ample_supply())
        ra = CVaRStochasticLP(lambda_weight=0.0, **kw).solve(scen, _ample_supply())
        assert (sum(v for v in ra["x"].values() if v)
                >= sum(v for v in rn["x"].values() if v) - 1e-6)
