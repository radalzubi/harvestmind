"""P2 network fixture matrix A-T with pre-registered qualitative expectations.

Every fixture is one central location fed by one supplier and (unless stated) two branches fed by
lanes, built from `zaad.meio.fixtures_p2.p2_request`; every input is a CONFIGURED_ASSUMPTION.
Expectations were written before the authoritative run and are checked verbatim by
`scripts.p2_benchmark`. Quantitative gates are in
`docs/zaad_full/evidence/p2/P2_PREREGISTRATION.md`.

expectation keys
  zaad_not_worse   ZAAD's continuation-valued cost must not exceed the best baseline's by more than this fraction
  service          "target": every branch at or above its target (less the tolerance) under ZAAD;
                   "incumbent": every branch no worse than the incumbent network policy (less the tolerance);
                   "feasible": no severe starvation and priority-consistent (targets jointly impossible)
  action           "yes" ZAAD intervenes on most reviews; "no" ZAAD mostly abstains; "either"
  network          a named network principle the fixture exists to test (checked by name in the runner)
"""
from __future__ import annotations

from typing import Any

from zaad.full.fixtures_p1 import NOW

SEEDS = (41001, 41002)
POLICIES = ("network_rop", "central_pool", "independent", "echelon_base_stock", "gated")
REVIEWS = 8

_shock = [{"id": "south_shock", "known_at": NOW, "service": "svc_south", "start": 1, "end": 3, "multiplier": 1.8, "label": "declared one-branch surge"}]

FIXTURES: dict[str, dict[str, Any]] = {
    "A_independent_demand": {"args": {"demand_correlation": 0.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "pooling_has_value"},
        "why": "independent branches diversify: one pooled central stock should cover both with less total protection than isolated buffers"},
    "B_correlated_demand": {"args": {"demand_correlation": .9},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "pooling_benefit_shrinks"},
        "why": "branches that move together do not diversify; the pooling benefit measured against the independent baseline must be smaller than in A"},
    "C_short_transfer_lead": {"args": {"lane_lead_periods": 1},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "central_more_useful_than_D"},
        "why": "a one-review lane makes central stock reachable for next period's demand"},
    "D_long_transfer_lead": {"args": {"lane_lead_periods": 3, "opening_branch": 350.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "local_more_valuable_than_C"},
        "why": "a three-review lane cannot protect near-term branch demand; more must sit locally"},
    "E_high_transfer_cost": {"args": {"lane_cost": 2.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "no_churn"},
        "why": "at 40% of unit price per move nothing should be moved that demand does not need"},
    "F_low_transfer_cost": {"args": {"lane_cost": .01, "opening_central": 600., "opening_branch": 60.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "rebalance_before_purchase"},
        "why": "near-free moves and a well-stocked central: rebalancing should dominate purchasing early"},
    "G_central_supply_shortage": {"args": {"supplier_capacity": 120., "opening_central": 100., "opening_branch": 60.},
        "expect": {"zaad_not_worse": .03, "service": "feasible", "action": "either", "network": "principled_allocation"},
        "why": "the supplier delivers 60% of network demand: allocation, not purchasing, decides service"},
    "H_one_branch_demand_shock": {"args": {"extra": {"events": _shock}, "opening_central": 400.},
        "expect": {"zaad_not_worse": .03, "service": "incumbent", "action": "either", "network": "healthy_branch_not_starved"},
        "why": "a declared surge at south must be met from the pool without starving north"},
    "I_shared_supplier_disruption": {"args": {"stresses": "severe", "opening_central": 250.},
        "expect": {"zaad_not_worse": .05, "service": "incumbent", "action": "either", "network": "network_protection"},
        "why": "a declared shared supplier disruption: P0-style protection sized at the network, not per branch"},
    "J_asymmetric_service_targets": {"args": {"target": {"north": .99, "south": .90}, "priority": {"north": 2., "south": 1.}, "opening_central": 200.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "priority_branch_protected"},
        "why": "the 99% branch carries the protection; the 90% branch is not padded to 99%"},
    "K_unequal_demand_scale": {"args": {"demand": {"north": 300., "south": 50.}, "opening_branch": {"north": 400., "south": 60.}, "opening_central": 500., "supplier_capacity": 380.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "small_branch_not_starved"},
        "why": "the large branch must not mechanically consume the pool; the small branch keeps its target"},
    "L_already_efficient_network": {"args": {"opening_central": 400., "opening_branch": 250.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "no", "network": "abstain"},
        "why": "a well-run incumbent network policy with adequate stock: ZAAD should mostly report no material improvement"},
    "M_transfer_not_reachable_in_time": {"args": {"lane_lead_periods": 4, "opening_branch": 50., "opening_central": 800.},
        "expect": {"zaad_not_worse": .02, "service": "feasible", "action": "either", "network": "remote_stock_not_credited"},
        "why": "central stock four reviews away cannot serve the next four periods; the plan must not count it as protection now"},
    "N_pipeline_already_solves_shortage": {"args": {"opening_branch": 40., "opening_central": 400.,
                                                    "inbound_transfers": [{"id": "in_north", "known_at": NOW, "sku": "A", "origin": "central", "destination": "north", "accepted_quantity": 260., "due_in": 1, "expires_in": 52},
                                                                          {"id": "in_south", "known_at": NOW, "sku": "A", "origin": "central", "destination": "south", "accepted_quantity": 260., "due_in": 1, "expires_in": 52}]},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "no_over_transfer"},
        "why": "transfers already in flight cover the shortage; period-0 transfers should be small"},
    "O_multiple_transfer_options": {"args": {"lane_lead_periods": 2, "lane_cost": .1, "opening_branch": 220.,
                                             "extra_lanes": [{"id": "express_north", "origin": "central", "destination": "north", "lead_periods": 1, "capacity": 1e6, "cost_per_unit": 1.},
                                                             {"id": "express_south", "origin": "central", "destination": "south", "lead_periods": 1, "capacity": 1e6, "cost_per_unit": 1.}]},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "cheap_lane_when_time_allows"},
        "why": "a slow cheap lane and a fast dear lane: the cheap lane should carry the bulk when time allows"},
    "P_transfer_capacity_limit": {"args": {"lane_capacity": 70., "opening_branch": 120.},
        "expect": {"zaad_not_worse": .03, "service": "feasible", "action": "either", "network": "capacity_respected"},
        "why": "a lane that carries 70% of branch demand per period: capacity binds, service as feasible"},
    "Q_pack_constraint_on_transfer": {"args": {"lane_multiple": 24., "lane_fixed_cost": 15.},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "legal_packs"},
        "why": "moves in whole cases of 24 with a per-dispatch fee: only legal quantities, fewer dispatches"},
    "R_order_transfer_interaction": {"args": {"fixed_order_cost": 250., "local_sources": {"north": {"price_premium": .15, "lead_days": 7}, "south": {"price_premium": .15, "lead_days": 7}}},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "total_economic_sourcing"},
        "why": "central buying with an order cost plus a move, or dearer local buying: the total-economic answer, not a fixed rule"},
    "S_recovery_after_imbalance": {"args": {"opening_branch": {"north": 400., "south": 0.}, "opening_central": 400.},
        "expect": {"zaad_not_worse": .03, "service": "incumbent", "action": "either", "network": "recovery_then_steady"},
        "why": "south starts empty: the network recovers it from the pool, then settles without ping-pong or hoarding"},
    "T_single_node_network_off": {"args": {"branches": ("branch",), "opening_central": 0., "opening_branch": 150., "incumbent_rule": "reorder_point", "extra": {"_single_node": True}},
        "expect": {"zaad_not_worse": .02, "service": "target", "action": "either", "network": "frozen_identity"},
        "why": "one node, no lane: P2 must reduce to the frozen P1 / P0 decisions exactly"},
}


def build(name: str, seed: int, **overrides):
    from zaad.meio.fixtures_p2 import p2_request
    args = {**FIXTURES[name]["args"], **overrides}
    return p2_request(seed=seed, **args)
