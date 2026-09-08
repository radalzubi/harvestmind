"""P1 development fixtures A-T with pre-registered expectations.

Each fixture is a small, fully specified purchasing situation (one branch, one supplier, one or two
SKUs, weekly periods, twelve-period horizon) built from `zaad.full.fixtures_p1.p1_request`. Every
economic input is a CONFIGURED_ASSUMPTION for development; none is customer economics. The
expectations below were written before the runner was executed and are checked by it verbatim."""
from __future__ import annotations

from typing import Any

TIERS = [{"up_to_pallets": 4, "charge": 800.}, {"up_to_pallets": 9, "charge": 1100.}, {"up_to_pallets": 20, "charge": 1500.}]

# expectation keys:
#   best_policy_in   the policies among which the cheapest total modelled cost should fall
#   zaad_not_worse   ZAAD's total cost must not exceed the best baseline's by more than this fraction
#   action           "yes" if ZAAD should intervene on the incumbent at most reviews, "no" if it should mostly abstain, "either"
#   categories       attribution categories expected to carry units in ZAAD's period-0 orders on at least one review
#   service_floor    every policy's mean service must stay at or above this (the fixture's target minus tolerance)
FIXTURES: dict[str, dict[str, Any]] = {
    "A_no_terms_good_incumbent": {"args": {"incumbent_rule": "reorder_point"},
        "expect": {"best_policy_in": ["reorder_point", "gated", "periodic:2", "economic_lot"], "zaad_not_worse": .02, "action": "no", "categories": ["DEMAND_CYCLE"]},
        "why": "with no order-level economics a reorder-point rule is already near the optimum; ZAAD should mostly say NO MATERIAL IMPROVEMENT"},
    "B_fixed_order_cost_replace_sold": {"args": {"incumbent_rule": "replace_sold", "supplier_terms": {"fixed_order_cost": 250.}},
        "expect": {"best_policy_in": ["gated", "economic_lot", "periodic:2", "reorder_point"], "zaad_not_worse": .02, "action": "yes", "categories": ["DEMAND_CYCLE"]},
        "why": "a $250 order cost makes weekly re-buying expensive; ZAAD should order less often than the incumbent"},
    "C_moq_four_weeks": {"args": {"incumbent_rule": "replace_sold", "minimum": 400.},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "yes", "categories": ["MOQ"]},
        "why": "a 400-unit MOQ against 100/week demand forces lumpy orders; the top-up must be attributed to MOQ"},
    "D_case_multiple": {"args": {"incumbent_rule": "reorder_point", "case_multiple": 48.},
        "expect": {"best_policy_in": ["reorder_point", "gated", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["CASE_ROUNDING"]},
        "why": "case rounding is a small, visible cost; attribution must show it and nothing should be invented beyond it"},
    "E_pallet_multiple": {"args": {"incumbent_rule": "reorder_point", "pallet_multiple": 200., "supplier_terms": {"units_per_pallet": {"A": 200.}, "freight_per_pallet": 60.}},
        "expect": {"best_policy_in": ["reorder_point", "gated", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["PALLET_ROUNDING"]},
        "why": "full-pallet ordering at two weeks of demand per pallet; attribution must show PALLET_ROUNDING"},
    "F_mov_two_skus": {"args": {"skus": ("A", "B"), "incumbent_rule": "replace_sold", "supplier_terms": {"minimum_order_value": 2000.}},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "yes", "categories": ["MOV"]},
        "why": "a $2,000 MOV against $1,000/week of combined demand forces coordination across the two SKUs"},
    "G_freight_tiers": {"args": {"skus": ("A", "B"), "incumbent_rule": "replace_sold", "supplier_terms": {"fixed_order_cost": 100., "freight_tiers": TIERS, "units_per_pallet": {"A": 100., "B": 100.}}},
        "expect": {"best_policy_in": ["gated", "economic_lot", "periodic:2", "reorder_point"], "zaad_not_worse": .02, "action": "yes", "categories": ["DEMAND_CYCLE"]},
        "why": "stepped freight makes a 4-pallet load cost the same as a 1-pallet load; consolidation should win"},
    "H_per_pallet_freight": {"args": {"incumbent_rule": "reorder_point", "supplier_terms": {"units_per_pallet": {"A": 100.}, "freight_per_pallet": 60.}},
        "expect": {"best_policy_in": ["reorder_point", "gated", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "linear per-pallet freight gives no consolidation incentive beyond filling the last pallet"},
    "I_max_pallets_ftl_cap": {"args": {"incumbent_rule": "reorder_point", "supplier_terms": {"units_per_pallet": {"A": 50.}, "freight_tiers": TIERS[:2], "max_pallets": 9., "fixed_order_cost": 150.}},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "a 9-pallet cap (450 units) bounds every shipment; no plan may exceed it"},
    "J_net60_cost_of_capital": {"args": {"incumbent_rule": "reorder_point", "balance_trigger": "arrival", "net_days": 60, "cost_of_capital_per_year": .12, "supplier_terms": {"fixed_order_cost": 150.}},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "net-60 terms mean stock is sold before it is paid for; financing cost must be lower than fixture K"},
    "K_deposit_early_cash": {"args": {"incumbent_rule": "reorder_point", "deposit_fraction": .3, "balance_trigger": "order", "net_days": 0, "cost_of_capital_per_year": .12, "supplier_terms": {"fixed_order_cost": 150.}},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "cash at order with a 12% cost of capital penalises early and large orders; financing must exceed fixture J"},
    "L_high_holding_rate": {"args": {"incumbent_rule": "replace_sold", "holding_per_year": .30, "supplier_terms": {"fixed_order_cost": 150.}},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "a 30%/yr holding rate should pull the lot size down relative to fixture B"},
    "M_order_calendar_wednesday": {"args": {"incumbent_rule": "reorder_point", "order_weekdays": (2,), "ship_weekdays": (0, 1, 2, 3, 4)},
        "expect": {"best_policy_in": ["reorder_point", "gated", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "Wednesday-only ordering with weekday shipping shifts every arrival; the timing audit must reflect the calendar, not the period grid"},
    "N_long_lead_21_days": {"args": {"incumbent_rule": "reorder_point", "lead_days": 21, "opening_units": 350.},
        "expect": {"best_policy_in": ["reorder_point", "gated", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["LEAD_TIME_EXPOSURE", "DEMAND_CYCLE"]},
        "why": "three weeks of lead time makes lead-time exposure the dominant reason to order"},
    "O_low_opening_stock": {"args": {"incumbent_rule": "periodic:2", "opening_units": 20.},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["LEAD_TIME_EXPOSURE", "DEMAND_CYCLE"], "service_floor": .80},
        "why": "with a week of demand on hand and a one-week lead, an early stockout is unavoidable for every policy; ZAAD must not pretend otherwise"},
    "P_high_opening_stock": {"args": {"incumbent_rule": "replace_sold", "opening_units": 600.},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "yes", "categories": []},
        "why": "six weeks of stock on hand: ordering nothing for several reviews is the right answer and the replace-sold incumbent is wrong"},
    "Q_volatile_demand_high_target": {"args": {"incumbent_rule": "reorder_point", "demand_sd_hint": .4, "target": .98},
        "expect": {"best_policy_in": ["reorder_point", "gated", "economic_lot", "periodic:2"], "zaad_not_worse": .03, "action": "either", "categories": ["SERVICE_PROTECTION", "DEMAND_CYCLE"]},
        "why": "volatile demand at a 98% target needs visible service protection in the attribution"},
    "R_asymmetric_prices_mov": {"args": {"skus": ("A", "B"), "incumbent_rule": "reorder_point", "supplier_terms": {"minimum_order_value": 3000.}, "extra": None},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .02, "action": "either", "categories": ["MOV"]},
        "why": "with B ten times the price of A, the MOV top-up should land on the line that is cheaper to hold (A)"},
    # Revised before the final run: the first draft (opening cash 1,500, credit 1,500, no dated
    # receivables) left every policy, the incumbent included, unable to finance week 6, because the
    # model counts only dated known receivables as cash in. Dated receivables of 450/week make
    # financing binding rather than impossible. The revision is a fixture-design correction and
    # is recorded here rather than hidden.
    "S_cash_constrained": {"args": {"incumbent_rule": "reorder_point", "opening_cash": 1500., "credit_limit": 1500., "interest_per_year": .12,
                                    "receivables_per_period": 450., "supplier_terms": {"fixed_order_cost": 100.}},
        "expect": {"best_policy_in": ["gated", "reorder_point", "economic_lot", "periodic:2"], "zaad_not_worse": .03, "action": "either", "categories": ["DEMAND_CYCLE"]},
        "why": "cash and credit together cover three weeks of purchases; financing must be visible and no plan may breach the credit limit"},
    "T_combined_realistic": {"args": {"skus": ("A", "B"), "incumbent_rule": "replace_sold", "case_multiple": 24., "net_days": 30, "balance_trigger": "arrival", "cost_of_capital_per_year": .10, "holding_per_year": .18,
                                       "supplier_terms": {"fixed_order_cost": 200., "minimum_order_value": 1500., "freight_tiers": TIERS, "units_per_pallet": {"A": 96., "B": 96.}, "receiving_fee_per_receipt": 25.}},
        "expect": {"best_policy_in": ["gated", "economic_lot", "periodic:2", "reorder_point"], "zaad_not_worse": .02, "action": "yes", "categories": ["DEMAND_CYCLE", "CASE_ROUNDING"]},
        "why": "every mechanism at once; ZAAD must reconcile and explain each order and beat weekly re-buying"},
}
POLICIES = ("incumbent", "reorder_point", "periodic:2", "economic_lot", "gated")
POLICY_LABEL = {"incumbent": "INCUMBENT", "reorder_point": "REORDER_POINT+PROTECTION", "periodic:2": "PERIODIC_REVIEW(2)",
                "economic_lot": "EOQ_LIKE", "gated": "ZAAD_P1"}
SEEDS = (41001, 41002, 41003)
REVIEWS = 8


def build(name: str, seed: int, stresses: str = "none"):
    from zaad.full.fixtures_p1 import p1_request
    args = dict(FIXTURES[name]["args"])
    args.pop("extra", None)
    req = p1_request(seed=seed, stresses=stresses, **args)
    if name == "R_asymmetric_prices_mov":
        data = req.model_dump(mode="python")
        for s in data["sources"]:
            if s["sku"] == "B":
                s["unit_price"] = 50.
        for s in data["skus"]:
            if s["id"] == "B":
                s["asset_value"], s["terminal_value"] = 50., 40.
        for s in data["services"]:
            if s["sku"] == "B":
                s["selling_price"], s["sla_per_unmet"] = 100., 25.
        from zaad.full.contracts import Request
        req = Request.model_validate(data)
    return req
