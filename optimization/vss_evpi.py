"""Value of the Stochastic Solution and Expected Value of Perfect Information
for the multi-period model. Diagnostics, not guarantees.

Definitions, for a MINIMISATION over scenarios omega with weights p:

  RP   = min_x  E_p[ cost(x, omega) ]                  (recourse problem)
  x_EV = argmin_x cost(x, E[omega])                     (expected-value solution:
                                                         mean demand, mean fill,
                                                         modal lead)
  EEV  = E_p[ cost(x_EV, omega) ]                       (expected result of
                                                         using the EV solution)
  VSS  = EEV - RP  >= 0
  WS   = E_p[ min_x cost(x, omega) ]                    (wait-and-see)
  EVPI = RP - WS   >= 0

Both inequalities are properties of the definitions and are asserted in
tests. All three objectives are recourse costs on the SAME scenario set,
in sample. A relative figure divides by RP. Interpretation is in
`classify`, and it is deliberately coarse.
"""

from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field

import pandas as pd

from optimization.multi_period_sp import MultiPeriodStochasticLP


@dataclass
class InformationValue:
    rp: float
    eev: float
    ws: float
    vss: float
    evpi: float
    vss_rel: float
    evpi_rel: float
    classification: str
    explanation: str
    n_scenarios: int
    statuses: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


def _ev_inputs(scen: pd.DataFrame, leads: dict, fills: dict, products, sups, T):
    """Collapse the scenario set to its expectation."""
    w = {int(r.scenario_index): float(r.scenario_weight)
         for r in scen.drop_duplicates("scenario_index").itertuples()}
    tot = sum(w.values()) or 1.0
    w = {k: v / tot for k, v in w.items()}
    mean_d = (scen.assign(wd=scen["scenario_weight"] * scen["demand_kg"] / tot)
              .groupby(["product_id", "period"])["wd"].sum())
    rows = [{"scenario_index": 0, "scenario_weight": 1.0, "product_id": j, "period": t,
             "demand_kg": float(mean_d.get((j, t), 0.0))} for j in products for t in range(T)]
    ev_leads, ev_fills = {}, {}
    for s_ in sups:
        for t in range(T):
            ls = [leads.get((k, s_, t), leads.get((k, s_), 0)) for k in w]
            fs = [fills.get((k, s_, t), fills.get((k, s_), 1.0)) for k in w]
            # modal lead (an integer), weighted-mean fill
            ev_leads[(0, s_, t)] = int(st.mode(ls)) if ls else 0
            ev_fills[(0, s_, t)] = float(sum(w[k] * f for k, f in zip(w, fs))) if fs else 1.0
    return pd.DataFrame(rows), ev_leads, ev_fills


def classify(vss_rel: float, evpi_rel: float, distribution_confidence: str = "unknown") -> tuple[str, str]:
    """Coarse, documented buckets. Thresholds are stated, not tuned."""
    if evpi_rel < 0.02:
        return ("LOW_INFORMATION_VALUE",
                "Even perfect information would change expected cost by under 2%; "
                "uncertainty currently has low economic value. Retaining the incumbent is reasonable.")
    if vss_rel < 0.02:
        return ("LOW_VSS",
                "Perfect information would help, but the stochastic solution barely improves "
                "on the expected-value one; the deterministic twin is nearly as good here.")
    if distribution_confidence == "low":
        return ("HIGH_VSS_LOW_CONFIDENCE",
                "Uncertainty is materially changing the preferred decision, but the scenario "
                "distribution is weakly supported; a robust candidate is the safer choice.")
    return ("HIGH_VSS",
            "Supply/demand uncertainty is materially changing the economically preferred decision.")


def value_of_information(model_kwargs: dict, scen: pd.DataFrame, supply: pd.DataFrame,
                         lead_times: dict, yield_scenarios: dict, opening_inventory: dict | None = None,
                         distribution_confidence: str = "unknown") -> InformationValue:
    kw = {k: v for k, v in model_kwargs.items()
          if k not in ("fixed_schedule", "baseline_schedule", "anchor_rho_by_product",
                       "regret_cvar_lambda", "regret_cvar_budget", "baseline_scenario_costs")}
    T = int(kw["n_periods"])
    products = list(scen["product_id"].unique())
    sups = sorted(supply["supplier_id"].unique())
    statuses = {}

    rp_res = MultiPeriodStochasticLP(**kw).solve(scen, supply, lead_times=lead_times,
                                                 yield_scenarios=yield_scenarios,
                                                 opening_inventory=opening_inventory)
    statuses["RP"] = rp_res["status"]
    if not rp_res["usable"]:
        raise ValueError(f"RP not solvable: {rp_res['status']}")
    rp = float(rp_res["expected_cost"])

    ev_scen, ev_leads, ev_fills = _ev_inputs(scen, lead_times, yield_scenarios, products, sups, T)
    ev_res = MultiPeriodStochasticLP(**kw).solve(ev_scen, supply, lead_times=ev_leads,
                                                 yield_scenarios=ev_fills, opening_inventory=opening_inventory)
    statuses["EV"] = ev_res["status"]
    if not ev_res["usable"]:
        raise ValueError(f"EV not solvable: {ev_res['status']}")
    # EEV and WS are EVALUATIONS of a decision, not optimisations over x: a
    # service floor (a constraint on recourse) can make a fixed schedule
    # infeasible on scenarios it was never chosen for. The floors are
    # dropped for those two solves and the classification says so.
    kw_eval = {k: v for k, v in kw.items() if k != "service_floor_by_product"}
    eev_res = MultiPeriodStochasticLP(**{**kw_eval, "fixed_schedule": ev_res["x"]}).solve(
        scen, supply, lead_times=lead_times, yield_scenarios=yield_scenarios,
        opening_inventory=opening_inventory)
    statuses["EEV"] = eev_res["status"]
    if not eev_res["usable"]:
        raise ValueError(f"EEV not solvable: {eev_res['status']}")
    eev = float(eev_res["expected_cost"])

    ws_parts = []
    weights = rp_res["scenario_weights"]
    for w_idx in sorted(weights):
        one = scen[scen["scenario_index"] == w_idx].copy()
        one["scenario_weight"] = 1.0
        lt1 = {k: v for k, v in lead_times.items() if k[0] == w_idx}
        ys1 = {k: v for k, v in yield_scenarios.items() if k[0] == w_idx}
        r1 = MultiPeriodStochasticLP(**kw_eval).solve(one, supply, lead_times=lt1, yield_scenarios=ys1,
                                                 opening_inventory=opening_inventory)
        if not r1["usable"]:
            raise ValueError(f"WS scenario {w_idx} not solvable: {r1['status']}")
        ws_parts.append(weights[w_idx] * float(r1["expected_cost"]))
    ws = float(sum(ws_parts))

    vss = max(eev - rp, 0.0) if abs(eev - rp) > 1e-7 * max(1.0, abs(rp)) else 0.0
    evpi = max(rp - ws, 0.0) if abs(rp - ws) > 1e-7 * max(1.0, abs(rp)) else 0.0
    denom = max(abs(rp), 1e-9)
    cls, why = classify(vss / denom, evpi / denom, distribution_confidence)
    return InformationValue(rp=rp, eev=eev, ws=ws, vss=vss, evpi=evpi, vss_rel=vss / denom,
                            evpi_rel=evpi / denom, classification=cls, explanation=why,
                            n_scenarios=len(weights), statuses=statuses)
