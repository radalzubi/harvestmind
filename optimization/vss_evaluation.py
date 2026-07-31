"""Out-of-sample VSS with bootstrap uncertainty.

WHY THIS EXISTS SEPARATELY FROM compute_vss
-------------------------------------------
``TwoStageStochasticLP.compute_vss`` computes VSS = EEV - RP on ONE
scenario set — the same set used to fit the decisions. That is the textbook
definition and it is correct as far as it goes, but two things make a
single in-sample number unsafe to quote:

1. It is IN-SAMPLE. Both RP and the EV decision are optimised against the
   same scenarios they are then scored on, so the comparison flatters RP:
   the richer model has more freedom to fit that particular sample. The
   honest question is how the two decisions perform on scenarios neither
   of them saw.

2. It is a POINT ESTIMATE from one sample. With the scenario counts we
   actually run (~100), sampling noise alone moves the objective by several
   percent — measured at roughly 7% via `optimization/saa_bounds.py`. A
   single VSS figure smaller than that band is indistinguishable from
   noise, and reporting it without an interval invites exactly that
   mistake.

WHAT THIS DOES INSTEAD
----------------------
Train/evaluate split, then bootstrap:

    * fit the RP decision and the EV decision on a TRAINING scenario set;
    * evaluate BOTH, with their first stages FIXED, on a disjoint
      EVALUATION set — the "common out-of-sample scenarios";
    * VSS_oos = EEV_oos - RP_oos, both measured on the same held-out
      scenarios so the comparison is like-for-like;
    * resample the evaluation set with replacement B times and recompute,
      giving a percentile confidence interval for VSS.

If the interval contains zero, the correct conclusion is that stochastic
optimization has not been shown to help on this instance — which is a
finding, not a failure, and one the point estimate would have hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class VSSResult:
    """Out-of-sample VSS with a bootstrap interval."""

    vss: float
    vss_pct_of_eev: float
    rp_cost_oos: float
    eev_cost_oos: float
    ci_low: float
    ci_high: float
    ci_level: float
    n_bootstrap: int
    n_train_scenarios: int
    n_eval_scenarios: int
    bootstrap_values: list = field(default_factory=list)

    @property
    def significant(self) -> bool:
        """Does the interval exclude zero?"""
        return self.ci_low > 0.0

    def to_dict(self) -> dict:
        return {
            "vss_out_of_sample": round(self.vss, 4),
            "vss_pct_of_eev": round(self.vss_pct_of_eev, 3),
            "rp_cost_oos": round(self.rp_cost_oos, 4),
            "eev_cost_oos": round(self.eev_cost_oos, 4),
            "ci_low": round(self.ci_low, 4),
            "ci_high": round(self.ci_high, 4),
            "ci_level": self.ci_level,
            "n_bootstrap": self.n_bootstrap,
            "n_train_scenarios": self.n_train_scenarios,
            "n_eval_scenarios": self.n_eval_scenarios,
            "significant": self.significant,
            "definition": ("VSS = EEV - RP, both first stages FIXED and "
                           "evaluated on common out-of-sample scenarios"),
            "interpretation": self.interpretation(),
        }

    def interpretation(self) -> str:
        if not self.significant:
            return (
                f"VSS = {self.vss:,.2f} with a {int(self.ci_level*100)}% "
                f"interval of [{self.ci_low:,.2f}, {self.ci_high:,.2f}], "
                "which includes zero. Stochastic optimization has NOT been "
                "shown to beat the deterministic plan on this instance — "
                "treat the point estimate as noise, not a finding."
            )
        return (
            f"VSS = {self.vss:,.2f} ({self.vss_pct_of_eev:.2f}% of EEV), "
            f"{int(self.ci_level*100)}% interval "
            f"[{self.ci_low:,.2f}, {self.ci_high:,.2f}] excluding zero. "
            "Planning against the distribution beats planning against the "
            "mean on held-out scenarios."
        )


def _reindex(df: pd.DataFrame, ids: np.ndarray) -> pd.DataFrame:
    """Rebuild a scenario frame from a (possibly repeated) id list."""
    frames = []
    for new_idx, old in enumerate(ids):
        block = df[df["scenario_index"] == old].copy()
        block["scenario_index"] = new_idx
        block["scenario_weight"] = 1.0 / len(ids)
        frames.append(block)
    return pd.concat(frames, ignore_index=True)


def _subset_yields(yields: dict | None, ids: np.ndarray) -> dict | None:
    if yields is None:
        return None
    out: dict = {}
    for new_idx, old in enumerate(ids):
        for (omega, sid), v in yields.items():
            if omega == old:
                out[(new_idx, sid)] = v
    return out or None


def out_of_sample_vss(
    solver,
    demand_scenarios: pd.DataFrame,
    supply: pd.DataFrame,
    yield_scenarios: dict | None = None,
    train_fraction: float = 0.5,
    n_bootstrap: int = 200,
    ci_level: float = 0.90,
    seed: int = 0,
) -> VSSResult | None:
    """VSS measured out-of-sample, with a bootstrap confidence interval.

    ``solver`` must expose ``solve`` and ``solve_with_fixed_first_stage``
    (i.e. a TwoStageStochasticLP). Returns None if any required solve fails
    — never a fabricated number.
    """
    rng = np.random.default_rng(seed)
    ids = np.array(sorted(demand_scenarios["scenario_index"].unique()))
    if ids.size < 4:
        return None

    shuffled = rng.permutation(ids)
    n_train = max(2, int(round(ids.size * train_fraction)))
    train_ids, eval_ids = shuffled[:n_train], shuffled[n_train:]
    if eval_ids.size < 2:
        return None

    train_df = _reindex(demand_scenarios, train_ids)
    train_y = _subset_yields(yield_scenarios, train_ids)

    # --- decisions, both fitted on TRAIN only ---------------------------
    rp = solver.solve(train_df, supply, yield_scenarios=train_y)
    x_rp = rp.get("x")
    if not x_rp:
        return None

    mean_demand = (train_df.groupby("product_id", as_index=False)["demand_kg"]
                   .mean().assign(scenario_index=0, scenario_weight=1.0))
    if "week_start" in train_df.columns:
        mean_demand["week_start"] = train_df["week_start"].min()
    mean_y = None
    if train_y:
        by_sup: dict = {}
        for (_o, sid), v in train_y.items():
            by_sup.setdefault(sid, []).append(float(v))
        mean_y = {(0, sid): float(np.mean(v)) for sid, v in by_sup.items()}
    ev = solver.solve(mean_demand, supply, yield_scenarios=mean_y)
    x_ev = ev.get("x")
    if not x_ev:
        return None

    # --- evaluate BOTH on the same held-out scenarios -------------------
    def _cost(x_fixed, sub_ids) -> float | None:
        df = _reindex(demand_scenarios, sub_ids)
        ys = _subset_yields(yield_scenarios, sub_ids)
        res = solver.solve_with_fixed_first_stage(df, supply, x_fixed,
                                                  yield_scenarios=ys)
        obj = res.get("objective")
        return float(obj) if obj is not None else None

    rp_oos = _cost(x_rp, eval_ids)
    eev_oos = _cost(x_ev, eval_ids)
    if rp_oos is None or eev_oos is None:
        return None
    vss = eev_oos - rp_oos

    # --- bootstrap the evaluation set -----------------------------------
    boot: list[float] = []
    for _ in range(n_bootstrap):
        draw = rng.choice(eval_ids, size=eval_ids.size, replace=True)
        a = _cost(x_rp, draw)
        b = _cost(x_ev, draw)
        if a is not None and b is not None:
            boot.append(b - a)
    if len(boot) < 10:
        return None

    tail = (1.0 - ci_level) / 2.0
    lo = float(np.quantile(boot, tail))
    hi = float(np.quantile(boot, 1.0 - tail))

    return VSSResult(
        vss=float(vss),
        vss_pct_of_eev=float(vss / eev_oos * 100.0) if eev_oos else 0.0,
        rp_cost_oos=rp_oos,
        eev_cost_oos=eev_oos,
        ci_low=lo, ci_high=hi, ci_level=ci_level,
        n_bootstrap=len(boot),
        n_train_scenarios=int(train_ids.size),
        n_eval_scenarios=int(eval_ids.size),
        bootstrap_values=[round(v, 4) for v in boot[:50]],
    )
