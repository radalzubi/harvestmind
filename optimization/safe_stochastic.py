"""Robust and baseline-anchored candidates built on the multi-period model.

Two candidates, both OPTIONAL and both behind explicit configuration:

  anchored   the stochastic program with an L1 penalty on deviating from
             the incumbent schedule and a CVaR term on baseline-relative
             regret. It is the stochastic optimizer that has to justify
             every departure from what the operator would have done.

  dro        distributionally robust by finite-scenario adversarial
             reweighting: the scenario weights are tilted toward the
             scenarios where the current decision is most expensive,
             within a total-variation ball of radius ``radius`` around the
             nominal weights, and the model is re-solved. A few rounds of
             this approximate a min-max over a small ambiguity set without
             leaving the LP/MILP the rest of the engine uses. It is
             EXPERIMENTAL: it has no out-of-sample guarantee and is not to
             be marketed until operator data support it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from optimization.multi_period_sp import MultiPeriodStochasticLP


@dataclass
class AnchorConfig:
    rho_by_product: dict = field(default_factory=dict)   # per-unit L1 penalty
    cvar_alpha: float = 0.90
    cvar_lambda: float = 0.0
    cvar_budget: float | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.cvar_alpha < 1.0:
            raise ValueError("cvar_alpha must be in (0, 1)")
        if self.cvar_lambda < 0:
            raise ValueError("cvar_lambda must be >= 0")
        if any(float(v) < 0 for v in self.rho_by_product.values()):
            raise ValueError("anchor penalties must be >= 0")


def solve_anchored(model_kwargs: dict, scen: pd.DataFrame, supply: pd.DataFrame, *,
                   baseline_schedule: dict, anchor: AnchorConfig, lead_times: dict,
                   yield_scenarios: dict, opening_inventory: dict | None = None) -> dict:
    kw = dict(model_kwargs)
    kw.update(baseline_schedule=baseline_schedule, anchor_rho_by_product=anchor.rho_by_product,
              regret_cvar_alpha=anchor.cvar_alpha, regret_cvar_lambda=anchor.cvar_lambda,
              regret_cvar_budget=anchor.cvar_budget)
    r = MultiPeriodStochasticLP(**kw).solve(scen, supply, lead_times=lead_times,
                                            yield_scenarios=yield_scenarios,
                                            opening_inventory=opening_inventory)
    if not r["usable"] and anchor.cvar_budget is not None:
        # A hard regret budget the model cannot meet is information, not a
        # reason to hand back nothing: relax it, keep the penalty, and say so.
        kw["regret_cvar_budget"] = None
        r = MultiPeriodStochasticLP(**kw).solve(scen, supply, lead_times=lead_times,
                                                yield_scenarios=yield_scenarios,
                                                opening_inventory=opening_inventory)
        r["warnings"] = list(r.get("warnings", [])) + ["regret CVaR budget infeasible; relaxed"]
        r["budget_relaxed"] = True
    r["candidate"] = "anchored_sp"
    return r


def _tilt(p: np.ndarray, cost: np.ndarray, radius: float) -> np.ndarray:
    """Weights q proportional to p*exp(theta*cost) with TV(q, p) = radius,
    theta found by bisection. radius=0 returns p."""
    if radius <= 0 or cost.max() - cost.min() < 1e-12:
        return p.copy()

    def tv(theta):
        z = cost - cost.max()
        q = p * np.exp(theta * z)
        q /= q.sum()
        return 0.5 * np.abs(q - p).sum(), q
    lo, hi = 0.0, 1.0
    while tv(hi)[0] < radius and hi < 1e6:
        hi *= 2
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if tv(mid)[0] < radius:
            lo = mid
        else:
            hi = mid
    return tv(lo)[1]


def solve_dro(model_kwargs: dict, scen: pd.DataFrame, supply: pd.DataFrame, *, radius: float,
              lead_times: dict, yield_scenarios: dict, opening_inventory: dict | None = None,
              rounds: int = 3) -> dict:
    """Finite-scenario adversarial reweighting within a total-variation ball."""
    if not 0.0 <= radius < 1.0:
        raise ValueError("radius must be in [0, 1)")
    kw = {k: v for k, v in model_kwargs.items() if k != "fixed_schedule"}
    base = scen.drop_duplicates("scenario_index").set_index("scenario_index")["scenario_weight"]
    idx = sorted(int(i) for i in base.index)
    p = np.array([float(base.loc[i]) for i in idx])
    p = p / p.sum()
    q = p.copy()
    r = None
    history = []
    for k in range(rounds + 1):
        s_ = scen.copy()
        s_["scenario_weight"] = s_["scenario_index"].map({i: float(q[n]) for n, i in enumerate(idx)})
        r = MultiPeriodStochasticLP(**kw).solve(s_, supply, lead_times=lead_times,
                                                yield_scenarios=yield_scenarios,
                                                opening_inventory=opening_inventory)
        if not r["usable"]:
            r["candidate"] = "dro"
            return r
        cost = np.array([r["scenario_costs"][i] for i in idx])
        history.append({"round": k, "objective": r["expected_cost"],
                        "nominal_cost": float((p * cost).sum()), "worst_weights_tv": float(0.5 * np.abs(q - p).sum())})
        if k == rounds:
            break
        q = _tilt(p, cost, radius)
    assert r is not None
    r["candidate"] = "dro"
    r["dro_radius"] = radius
    r["dro_history"] = history
    r["nominal_expected_cost"] = history[-1]["nominal_cost"]
    r["worst_case_expected_cost"] = r["expected_cost"]
    return r


def regret_summary(regret: dict, weights: dict, alpha: float = 0.9) -> dict:
    """Weighted statistics of scenario regret relative to the baseline."""
    if not regret:
        return {}
    ws = np.array([weights[w] for w in regret])
    rs = np.array([regret[w] for w in regret])
    order = np.argsort(rs)
    ws, rs = ws[order], rs[order]
    cum = np.cumsum(ws) / ws.sum()
    var = float(rs[np.searchsorted(cum, alpha, side="left").clip(0, len(rs) - 1)])
    tail = rs >= var
    cvar = float((ws[tail] * rs[tail]).sum() / max(ws[tail].sum(), 1e-12))
    return {"expected_regret": float((ws * rs).sum() / ws.sum()), "worst_regret": float(rs.max()),
            "best_regret": float(rs.min()), "p_regret_positive": float(ws[rs > 1e-9].sum() / ws.sum()),
            f"var_{int(alpha*100)}": var, f"cvar_{int(alpha*100)}": cvar}


def is_finite_dict(d: dict) -> bool:
    return all(math.isfinite(float(v)) for v in d.values())
