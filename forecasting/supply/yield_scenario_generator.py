"""Yield scenario generator for two-stage stochastic programming.

Generates N scenarios of supplier×product×week supply availability,
incorporating ENSO phase, drought index, historical yield CV, and
seasonal indices. Uses Sample Average Approximation (SAA).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import date, timedelta

from synthetic.archetypes import PRODUCT_ARCHETYPES, SUPPLIER_PRODUCT_MAP
from synthetic.seasonality import enso_yield_adjustment, seasonal_index


ENSO_TRANSITION = {
    "el_nino":  {"el_nino": 0.60, "neutral": 0.35, "la_nina": 0.05},
    "la_nina":  {"el_nino": 0.05, "neutral": 0.35, "la_nina": 0.60},
    "neutral":  {"el_nino": 0.20, "neutral": 0.60, "la_nina": 0.20},
}


class YieldScenarioGenerator:
    def __init__(
        self,
        n_scenarios: int = 100,
        horizon_weeks: int = 12,
        seed: int = 42,
    ) -> None:
        self.n_scenarios = n_scenarios
        self.horizon_weeks = horizon_weeks
        self.rng = np.random.default_rng(seed)

    def generate(
        self,
        planning_week: date,
        yield_history: pd.DataFrame | None = None,
        current_enso: str = "neutral",
    ) -> pd.DataFrame:
        """Generate SAA scenarios.

        Parameters
        ----------
        planning_week  : Monday of the planning period (first delivery week)
        yield_history  : optional [supplier_id, product_id, harvest_week,
                          realized_yield_kg_per_ha, planned_ha, total_kg_harvested]
        current_enso   : current ENSO phase for Markov chain seed

        Returns
        -------
        DataFrame with columns:
          scenario_index, scenario_weight, supplier_id, product_id,
          week_start, yield_kg, yield_kg_per_ha, enso_phase
        """
        rows = []
        scenario_weight = 1.0 / self.n_scenarios

        for scen in range(self.n_scenarios):
            enso_path = self._draw_enso_path(current_enso)

            for week_offset in range(self.horizon_weeks):
                week = planning_week + timedelta(weeks=week_offset)
                iso_week = week.isocalendar()[1]
                enso = enso_path[week_offset]

                for sup_id, prod_ids in SUPPLIER_PRODUCT_MAP.items():
                    for prod_id in prod_ids:
                        arch = PRODUCT_ARCHETYPES.get(prod_id)
                        if arch is None:
                            continue

                        si = seasonal_index(arch.seasonality, iso_week)
                        if si < 0.15:  # deep off-season: zero supply
                            rows.append({
                                "scenario_index": scen,
                                "scenario_weight": scenario_weight,
                                "supplier_id": sup_id,
                                "product_id": prod_id,
                                "week_start": week,
                                "yield_kg": 0.0,
                                "yield_kg_per_ha": 0.0,
                                "enso_phase": enso,
                            })
                            continue

                        # Calibrate yield distribution from history if available
                        mu_kgha, cv = self._calibrate(yield_history, sup_id, prod_id)
                        enso_adj = enso_yield_adjustment(enso, _crop_cat(arch.crop_name))
                        mu_adj = mu_kgha * si * enso_adj

                        # Log-normal draw: preserves non-negativity
                        sigma_log = np.sqrt(np.log(1 + cv ** 2))
                        mu_log = np.log(max(mu_adj, 1.0)) - sigma_log ** 2 / 2
                        kgha = float(self.rng.lognormal(mu_log, sigma_log))

                        # Planned hectares: small perturbation around archetype
                        base_ha = self.rng.uniform(3.0, 15.0)
                        total_kg = kgha * base_ha

                        rows.append({
                            "scenario_index": scen,
                            "scenario_weight": scenario_weight,
                            "supplier_id": sup_id,
                            "product_id": prod_id,
                            "week_start": week,
                            "yield_kg": round(total_kg, 1),
                            "yield_kg_per_ha": round(kgha, 1),
                            "enso_phase": enso,
                        })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------

    def _draw_enso_path(self, start: str) -> list[str]:
        path = [start]
        for _ in range(self.horizon_weeks - 1):
            probs = ENSO_TRANSITION.get(path[-1], ENSO_TRANSITION["neutral"])
            phases = list(probs.keys())
            weights = list(probs.values())
            path.append(str(self.rng.choice(phases, p=weights)))
        return path

    @staticmethod
    def _calibrate(
        history: pd.DataFrame | None,
        supplier_id: str,
        product_id: str,
    ) -> tuple[float, float]:
        """Return (mean_yield_kg_per_ha, cv) from history or defaults."""
        if history is not None and not history.empty:
            mask = (history["supplier_id"] == supplier_id) & (history["product_id"] == product_id)
            sub = history[mask]["realized_yield_kg_per_ha"].dropna()
            if len(sub) >= 4:
                mu = float(sub.mean())
                cv = float(sub.std() / mu) if mu > 0 else 0.20
                return mu, min(cv, 0.60)
        arch = PRODUCT_ARCHETYPES.get(product_id)
        return 8000.0, arch.yield_cv if arch else 0.20


def _crop_cat(crop_name: str) -> str:
    name = crop_name.lower()
    if any(x in name for x in ("lettuce","spinach","kale","arugula")):
        return "leafy_green"
    if "tomato" in name:
        return "tomato"
    if "pepper" in name:
        return "pepper"
    if any(x in name for x in ("squash","zucchini")):
        return "squash"
    if any(x in name for x in ("berry","strawberry")):
        return "berry"
    if any(x in name for x in ("onion","garlic","shallot","leek")):
        return "allium"
    return "other"
