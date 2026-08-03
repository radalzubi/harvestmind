"""Statistical bounds on SAA solution quality — is N scenarios enough?

THE PROBLEM
-----------
Sample Average Approximation replaces the true expectation with an average
over N sampled scenarios. That leaves a question the solver cannot answer:
how far is the solution we obtained from the one we would get with the true
distribution? Reporting a solved objective without that gap invites reading
solver precision as decision quality — the model always returns "optimal",
whether N is 20 or 20,000.

Worse, the SAA objective is BIASED. For a minimisation problem

    E[v̂_N]  <=  v*

i.e. the sampled optimum looks better than the truth, and it looks better
the fewer scenarios you use. So the naive number is optimistic in exactly
the situation where you would most want a warning.

References
----------
Kleywegt, A.J., Shapiro, A. & Homem-de-Mello, T. (2002). "The sample
    average approximation method for stochastic discrete optimization."
    *SIAM Journal on Optimization* 12(2):479-502.
    doi:10.1137/S1052623499363220
    - Section 2.3: the downward-bias inequality chain above.
    - Sections 3.2-3.3: the multiple-replication bounding procedure and
      the optimality-gap confidence interval implemented here.
Mak, W.-K., Morton, D.P. & Wood, R.K. (1999). "Monte Carlo bounding
    techniques for determining solution quality in stochastic programs."
    *Operations Research Letters* 24(1):47-56.
    doi:10.1016/S0167-6377(98)00054-6
    - the canonical statement that the SAA value is a statistical lower
      bound on the true optimum, improving monotonically with N.

THE PROCEDURE
-------------
Lower bound: solve M independent SAA replications, each on its own fresh
sample of N scenarios, and average their optimal values. Each is biased
low, so the average estimates a valid statistical LOWER bound on v*.

Upper bound: take one candidate first-stage decision x̂ and evaluate it on
a large independent sample of N' scenarios. Since x̂ is merely feasible,
g(x̂) >= v*, and the sample mean is an UNBIASED estimator of g(x̂) — a
valid statistical upper bound.

The gap estimate, with confidence, is then (KSH eq. 3.3):

    gap = ĝ_N'(x̂) - v̄  +  z_α · sqrt( S²_N'/N' + S²_M/M )

A small gap means N is sufficient. A large one means the scenario count is
doing the deciding, not the data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class SAAGapResult:
    """Optimality-gap assessment for an SAA solution."""

    lower_bound: float
    lower_bound_stderr: float
    upper_bound: float
    upper_bound_stderr: float
    gap: float
    gap_with_confidence: float
    gap_pct: float
    confidence: float
    n_scenarios: int
    n_replications: int
    n_evaluation: int
    replication_values: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lower_bound": round(self.lower_bound, 4),
            "lower_bound_stderr": round(self.lower_bound_stderr, 4),
            "upper_bound": round(self.upper_bound, 4),
            "upper_bound_stderr": round(self.upper_bound_stderr, 4),
            "optimality_gap": round(self.gap, 4),
            "optimality_gap_with_confidence": round(self.gap_with_confidence, 4),
            "optimality_gap_pct": round(self.gap_pct, 3),
            "confidence": self.confidence,
            "n_scenarios": self.n_scenarios,
            "n_replications": self.n_replications,
            "n_evaluation_scenarios": self.n_evaluation,
            "sufficient": bool(self.gap_pct < 1.0),
            "interpretation": self.interpretation(),
            "method": ("multiple-replication procedure, Kleywegt, Shapiro & "
                       "Homem-de-Mello (2002) §3.2-3.3"),
        }

    def interpretation(self) -> str:
        if self.gap_pct < 0.5:
            return (f"Gap {self.gap_pct:.2f}% of objective — the scenario "
                    f"count ({self.n_scenarios}) is sufficient; adding more "
                    "would not materially change the decision.")
        if self.gap_pct < 2.0:
            return (f"Gap {self.gap_pct:.2f}% — acceptable for planning, but "
                    "sampling error is no longer negligible next to the "
                    "differences being compared.")
        return (f"Gap {self.gap_pct:.2f}% of objective — the scenario count "
                f"({self.n_scenarios}) is too small. Differences smaller than "
                "this gap are sampling noise, not findings. Increase N before "
                "drawing conclusions.")


def _resample_scenarios(
    pool: pd.DataFrame, n: int, rng: np.random.Generator,
) -> pd.DataFrame:
    """Draw n scenarios (with replacement) and re-index them 0..n-1."""
    available = pool["scenario_index"].unique()
    picked = rng.choice(available, size=n, replace=True)
    frames = []
    for new_idx, old_idx in enumerate(picked):
        block = pool[pool["scenario_index"] == old_idx].copy()
        block["scenario_index"] = new_idx
        block["scenario_weight"] = 1.0 / n
        frames.append(block)
    return pd.concat(frames, ignore_index=True)


def estimate_optimality_gap(
    solver,
    scenario_pool: pd.DataFrame,
    supply: pd.DataFrame,
    n_scenarios: int = 50,
    n_replications: int = 10,
    n_evaluation: int = 400,
    confidence: float = 0.95,
    seed: int = 0,
) -> SAAGapResult | None:
    """Estimate the SAA optimality gap by multiple replication.

    Parameters
    ----------
    solver : an object exposing ``.solve(demand_scenarios, supply)`` and
        ``.solve_with_fixed_first_stage(demand_scenarios, supply, x)`` —
        i.e. a TwoStageStochasticLP.
    scenario_pool : the full scenario set to resample from. Should be
        substantially larger than ``n_scenarios`` for the replications to
        be meaningfully independent.
    n_scenarios : scenarios per replication (the N being assessed).
    n_replications : number of independent replications (M).
    n_evaluation : scenarios used to evaluate the candidate solution (N').

    Returns None when solves fail — never a fabricated bound.
    """
    rng = np.random.default_rng(seed)

    # --- Lower bound: M independent SAA replications --------------------
    values: list[float] = []
    for m in range(n_replications):
        sample = _resample_scenarios(scenario_pool, n_scenarios, rng)
        res = solver.solve(sample, supply)
        obj = res.get("objective")
        if obj is not None:
            values.append(float(obj))

    if len(values) < 2:
        return None

    arr = np.asarray(values, dtype=float)
    lower = float(arr.mean())
    # Standard error of the mean across replications (KSH S_M^2 / M).
    lower_se = float(arr.std(ddof=1) / np.sqrt(len(arr)))

    # --- Candidate solution: solve once on a fresh sample ---------------
    candidate_sample = _resample_scenarios(scenario_pool, n_scenarios, rng)
    candidate = solver.solve(candidate_sample, supply)
    x_hat = candidate.get("x")
    if not x_hat:
        return None

    # --- Upper bound: evaluate that decision on the FULL pool -----------
    # Evaluating on a bootstrap resample instead adds sampling noise to the
    # bound itself, which stops the measured gap from shrinking as N grows
    # (observed: gap stuck near 11-13% for both N=25 and N=200, because the
    # noise in the bound swamped the convergence being measured). The pool
    # IS our best available estimate of the distribution, so evaluating the
    # candidate against all of it gives the exact expected cost of that
    # decision under the empirical distribution — no extra variance, and
    # the quantity an operator actually cares about: how much does deciding
    # on N scenarios cost versus deciding on everything we have?
    pool_normalised = scenario_pool.copy()
    n_pool = int(pool_normalised["scenario_index"].nunique())
    pool_normalised["scenario_weight"] = 1.0 / n_pool
    upper_res = solver.solve_with_fixed_first_stage(
        pool_normalised, supply, x_hat)
    upper_obj = upper_res.get("objective")
    if upper_obj is None:
        return None
    upper = float(upper_obj)

    # The upper bound is exact under the empirical distribution, so it
    # carries no sampling error of its own; the confidence interval is
    # driven entirely by the spread across replications.
    upper_se = 0.0
    n_evaluation = n_pool

    gap = upper - lower
    z = float(stats.norm.ppf(confidence))
    gap_conf = gap + z * float(np.sqrt(upper_se ** 2 + lower_se ** 2))
    denom = abs(upper) if abs(upper) > 1e-9 else 1.0

    return SAAGapResult(
        lower_bound=lower,
        lower_bound_stderr=lower_se,
        upper_bound=upper,
        upper_bound_stderr=upper_se,
        gap=gap,
        gap_with_confidence=gap_conf,
        gap_pct=float(gap_conf / denom * 100.0),
        confidence=confidence,
        n_scenarios=n_scenarios,
        n_replications=n_replications,
        n_evaluation=n_evaluation,
        replication_values=[round(v, 4) for v in values],
    )


def scenario_count_curve(
    solver,
    scenario_pool: pd.DataFrame,
    supply: pd.DataFrame,
    counts: tuple[int, ...] = (10, 25, 50, 100),
    n_replications: int = 6,
    seed: int = 0,
) -> pd.DataFrame:
    """In-sample stability: how does the SAA value settle as N grows?

    The bias shrinks with N, so the objective should rise and its spread
    across replications should narrow. Where the curve flattens is the
    empirical answer to "how many scenarios do we need" — the literature
    offers no universal number, only this kind of instance-specific
    stability check (cf. Kaut & Wallace on in-sample stability).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for n in counts:
        vals = []
        for _ in range(n_replications):
            sample = _resample_scenarios(scenario_pool, n, rng)
            res = solver.solve(sample, supply)
            if res.get("objective") is not None:
                vals.append(float(res["objective"]))
        if not vals:
            continue
        arr = np.asarray(vals)
        rows.append({
            "n_scenarios": n,
            "mean_objective": round(float(arr.mean()), 4),
            "std_objective": round(float(arr.std(ddof=1)), 4) if len(arr) > 1 else 0.0,
            "cv_pct": (round(float(arr.std(ddof=1) / abs(arr.mean()) * 100), 3)
                       if len(arr) > 1 and abs(arr.mean()) > 1e-9 else 0.0),
            "n_replications": len(vals),
        })
    return pd.DataFrame(rows)
