"""Reproduce base PR20 service/settlement mismatch; no database or core edits."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
import pyomo.environ as pyo  # noqa: E402
from backtesting.counterfactual import (  # noqa: E402
    _scenarios, _optimizer_kwargs, _supply_df, FoldTruth, settle,
)
from optimization.multi_period_sp import MultiPeriodStochasticLP  # noqa: E402
from optimization.service_frontier import solve_service_target  # noqa: E402
from scripts.run_commercial_remodel_audit import Cell, history, inputs  # noqa: E402


def main():
    cell = Cell(target=1.)
    demand, events = history(cell, 701)
    fi = inputs(cell, demand, events, 60, 12)
    scen, leads, fills = _scenarios(fi, 80, np.random.default_rng(701000))
    result = solve_service_target(
        MultiPeriodStochasticLP(**_optimizer_kwargs(fi, None)), scen, _supply_df(fi),
        targets={"A": 1., "B": 1.}, lead_times=leads, yield_scenarios=fills,
        opening_inventory=fi.opening, per_period=True)
    model = result["model"]
    planned = sum(pyo.value(model.u[j, t, w]) for j in model.J
                  for t in model.T if t >= 1 for w in model.W) / 80
    realized = 0.
    for w in range(80):
        rows = scen[scen.scenario_index == w]
        truth = FoldTruth(
            demand={(r.product_id, int(r.period)): float(r.demand_kg) for r in rows.itertuples()},
            lead={(s, t): leads[w, s, t] for s in ("S1", "S2") for t in range(12)},
            fill={(s, t): fills[w, s, t] for s in ("S1", "S2") for t in range(12)})
        score = settle(result["x"], fi, truth, None)
        realized += (score.components["demanded_units"] - score.components["served_units"]) / 80
    print({"planned_unmet_after_first_period": planned,
           "same_scenarios_greedy_unmet": realized,
           "planned_first_period_withholding": sum(pyo.value(model.u[j, 0, w])
                                                     for j in model.J for w in model.W) / 80})


if __name__ == "__main__":
    main()
