# Architecture and dependency map

## Decision: direct network stochastic LP/MILP with rolling replanning

The architecture skill guided a modular extension rather than replacing the
working signal, API authentication and legacy evidence layers. The security
skill guided tenant binding, bounded computation and persistent review guards.

```
operator CSV/JSON + dated licensed signals
  -> full/contracts.py + intake.py (one as-of snapshot)
  -> forecast.py (causal refit) + eta.py (censored survival)
  -> worlds.py (calendar paths, shared domains, declared stress)
  -> model.py (global quantities / inventory / amendments / cash)
  -> settlement.py (independent common physical/economic replay)
  -> planner.py (selection -> independent confirmation -> adverse confirmation)
  -> shadow.py -> authenticated API -> /zaad/network
                    human review only
```

The existing `zaad/signals.py` provides licensed as-of replay and a bounded NOAA
adapter. `zaad.forecast.point` supplies existing intermittent algorithms. The
old `optimization/`, `risk/`, and `backtesting/` packages remain in place and
their regression suite runs unchanged. PR20/21 remain stacked, unmerged drafts.

## Alternatives and trade-offs

- Guaranteed-service MEIO is efficient for strategic buffer placement, but
  bounded demand / guaranteed interstage service assumptions are poorly aligned
  with stochastic fill, late open POs, cancellation and cash constraints.
- Direct scenario network flow maps to actual purchases and stock movements.
  Age cohorts and physical work conservation introduce MILP variables even when
  order quantities themselves remain continuous.
- A full multistage tree grows rapidly. We use scenario-invariant purchase,
  transfer and amendment schedules with scenario inventory/service/cash recourse,
  then execute only the first review. It is not an optimal multistage policy.
- Wasserstein DRO would require an operationally meaningful calibrated radius,
  metric and support. We do **not** relabel a hand-picked stress set as DRO.
- Stress-envelope MPC is auditable and supports mismatched fill/lead/recovery
  assumptions. Protection costs money; it need not win in normal conditions.

HiGHS/SciPy is the default. CBC, GLPK, Gurobi and CPLEX adapters are allowlisted
and optional; unavailable binaries/licenses fail closed. Only proven optimal
solutions with checked primal/integrality residuals are used. A time-limit
incumbent is not silently promoted.

Primary references: [Graves–Willems guaranteed-service assumptions](https://pubsonline.informs.org/doi/abs/10.1287/msom.2.1.68.23267),
[SciPy MILP interface](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html),
[Wasserstein MPC research](https://arxiv.org/abs/2105.08414).
