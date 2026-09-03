"""A known promotion is an input the plan must respond to."""
import numpy as np

from backtesting.counterfactual import FoldInputs, policy_deterministic_sp, policy_order_up_to
from domain.economics import CostConfig
from domain.model import fmcg_policy
from domain.uom import PackSpec


def _fi(promo):
    pol = fmcg_policy({"A": PackSpec(1)}, cost_config=CostConfig(
        holding_rate_per_period=0.005, shortage_cost_per_unit={"A": 2.0}, waste_cost_per_unit={"A": 5.0}))
    return FoldInputs(origin=60, horizon=6, products=["A"], supplier_of={"A": "S"}, lead_of={"S": 1},
                      train_demand={"A": [100.0] * 60}, train_fill={"S": [1.0]}, unit_cost={"A": 5.0},
                      margin={"A": 2.0}, capacity={"A": 1000.0}, opening={"A": 100.0}, pipeline={("A", 0): 100.0},
                      policy=pol, promo_multiplier=promo)


def test_planned_promotion_raises_orders_for_optimizer_and_heuristic():
    base_opt, _ = policy_deterministic_sp(_fi({}), None, np.random.default_rng(0))
    promo_opt, _ = policy_deterministic_sp(_fi({("A", 3): 2.5}), None, np.random.default_rng(0))
    assert sum(promo_opt.values()) > sum(base_opt.values()) + 100
    base_h = policy_order_up_to(_fi({}))
    promo_h = policy_order_up_to(_fi({("A", 3): 2.5}))
    assert sum(promo_h.values()) > sum(base_h.values())
