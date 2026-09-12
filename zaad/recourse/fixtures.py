"""Pre-registered P4 fixtures: request builders, world builders (scenario trees and handcrafted
branches) and the semantic principle each fixture must satisfy. Written before the matrix was run;
no fixture is retuned after a failure.

Change log (pre-authoritative): A2 declared its late confirmation through `confirmation_lag` (the
fixture text said "not confirmed until later" but the first spec omitted the lag); I2's surge was
1.6x, which left the STATIC comparator infeasible under the service floors (an ill-posed comparison),
now 1.3x, and its two-period lanes need 300 opening units per branch for any static plan to bridge period 1 (150 was infeasible at any surge); S4 keeps its 1.3x demand because it shows adaptation restoring feasibility where no static
plan exists (ordering not applicable), and S5 adds the milder mixed case where both plans exist."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from zaad.full.contracts import Request
from zaad.full.worlds import World, draw
from zaad.meio.fixtures_p2 import p2_request
from zaad.recourse.contracts import Recourse, resolve
from zaad.recourse.worlds import draw_tree

DECL = "OPERATOR_DECLARED"
SEED = 41001


def with_recourse(req: Request, **spec: Any) -> Request:
    payload = req.model_dump(mode="json")
    payload["recourse"] = {"enabled": True, "review_periods": [3], "observables": ["demand", "receipts"], "actions": ["purchase", "transfer"],
                           "demand_grid": 5., "fill_grid": .05, "continuations": 2, **spec}
    return Request.model_validate(payload)


def _base_world(req: Request, seed: int = SEED) -> World:
    return draw(req, seed, 1, deterministic=True)[0]


def _noise(world: World, req: Request, seed: int, k: int, scale: float = .05) -> World:
    """A future continuation: deterministic demand perturbed by a fixed pattern (no RNG needed)."""
    demand = {s: tuple(d * (1. + scale * ((-1) ** (t + k)) * (1 + (t % 3)) / 3.) for t, d in enumerate(v)) for s, v in world.demand.items()}
    return replace(world, demand=demand)


def branches(req: Request, rc: Recourse, edits: list[tuple[str, float, Any]], epoch: int, continuations: int = 2) -> list[World]:
    """Two-or-more branch tree from the mean world: each branch is (name, weight, edit) with `edit`
    a function World -> World applied to the whole path; every branch gets `continuations` futures
    that share the branch's history through epoch-1 exactly."""
    base = _base_world(req)
    out: list[World] = []
    for name, weight, edit in edits:
        path = edit(base) if edit is not None else base
        for k in range(continuations):
            future = _noise(path, req, SEED, k)
            demand = {s: tuple(path.demand[s][t] if t < epoch else future.demand[s][t] for t in range(req.horizon)) for s in path.demand}
            out.append(replace(path, name=f"{name}.{k}", weight=weight / continuations, demand=demand))
    total = sum(w.weight for w in out)
    return [replace(w, weight=w.weight / total) for w in out]


# ---- branch edits -------------------------------------------------------------------------------
def scale_demand(factor: float, from_period: int = 0):
    def edit(w: World) -> World:
        return replace(w, demand={s: tuple(d * (factor if t >= from_period else 1.) for t, d in enumerate(v)) for s, v in w.demand.items()})
    return edit


def short_fill(source: str, periods: tuple[int, ...], fill: float):
    def edit(w: World) -> World:
        return replace(w, fills={k: (fill if (k[0] == source and k[1] in periods) else v) for k, v in w.fills.items()})
    return edit


def late_arrival(source: str, placed: int, extra: int):
    def edit(w: World) -> World:
        return replace(w, arrival={k: (v + extra if (k[0] == source and k[1] == placed) else v) for k, v in w.arrival.items()})
    return edit


def compose(*edits):
    def edit(w: World) -> World:
        for e in edits:
            w = e(w)
        return w
    return edit


# ---- request families ---------------------------------------------------------------------------
def p2_base(**kw) -> Request:
    return p2_request(**{"seed": SEED, "demand_sd_hint": .15, **kw})


def sourcing_base(name: str, **kw) -> Request:
    from zaad.sourcing.fixtures import build
    return build(name, SEED, **kw)


def sector_base(name: str, **kw) -> Request:
    from zaad.sectors.fixtures import build
    return build(name, SEED, **kw)


# ---- the matrix ---------------------------------------------------------------------------------
# family, request, recourse overrides, worlds ("tree" or a branch list), principle
FIXTURES: dict[str, dict[str, Any]] = {
    # neutrality
    "N1_disabled_is_frozen": {"family": "neutrality", "request": lambda: p2_base(), "recourse": {"enabled": False}, "worlds": "tree", "principle": "frozen_identity"},
    "N2_no_epochs_is_static": {"family": "neutrality", "request": lambda: p2_base(), "recourse": {"review_periods": []}, "worlds": "tree", "principle": "equals_static"},
    "N3_zero_information": {"family": "neutrality", "request": lambda: p2_base(), "recourse": {"review_periods": [3], "observables": ["demand"]},
                            "worlds": [("normal", .5, None), ("high_later", .5, scale_demand(1.4, from_period=3))], "principle": "one_set_equals_static"},
    # non-anticipativity
    "A1_demand_visible_at_epoch": {"family": "non_anticipativity", "request": lambda: p2_base(), "recourse": {"review_periods": [3], "observables": ["demand"]},
                                   "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.4))], "principle": "same_before_diverge_after"},
    "A2_delayed_information": {"family": "non_anticipativity", "request": lambda: p2_base(), "recourse": {"review_periods": [2, 4], "observables": ["receipts"], "confirmation_lag": 2},
                               "worlds": [("on_time", .5, None), ("late", .5, late_arrival("src_A", 0, 2))], "principle": "no_branch_until_observed"},
    # observation classes
    "D1_demand_recourse": {"family": "demand", "request": lambda: p2_base(), "recourse": {"review_periods": [3], "observables": ["demand"]},
                           "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.5))], "principle": "high_branch_buys_more"},
    "D2_two_epochs": {"family": "demand", "request": lambda: p2_base(), "recourse": {"review_periods": [3, 6], "observables": ["demand"]},
                      "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.4))], "principle": "high_branch_buys_more"},
    "R1_supplier_short_fill": {"family": "receipts", "request": lambda: sourcing_base("E2_landed_beats_unit_price"), "recourse": {"review_periods": [3], "observables": ["receipts"]},
                               "worlds": [("full", .5, None), ("short", .5, short_fill("src_A", (0, 1, 2, 3, 4, 5), .5))], "principle": "short_branch_replaces_supply"},
    "R2_shipment_delay": {"family": "receipts", "request": lambda: p2_base(), "recourse": {"review_periods": [3], "observables": ["receipts"]},
                          "worlds": [("on_time", .5, None), ("late", .5, late_arrival("src_A", 1, 3))], "principle": "late_branch_covers_gap"},
    "V1_recovery": {"family": "recovery", "request": lambda: sourcing_base("E2_landed_beats_unit_price"), "recourse": {"review_periods": [4], "observables": ["receipts"]},
                    "worlds": [("recovered", .5, short_fill("src_A", (0, 1), .6)), ("persistent", .5, short_fill("src_A", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), .6))], "principle": "recovered_branch_buys_less"},
    # value of waiting
    "W1_waiting_has_value": {"family": "waiting", "request": lambda: p2_base(), "recourse": {"review_periods": [2], "observables": ["demand"]},
                             "worlds": [("low", .5, scale_demand(.7)), ("high", .5, scale_demand(1.5))], "principle": "waiting_value"},
    "W2_no_benefit": {"family": "waiting", "request": lambda: p2_base(), "recourse": {"review_periods": [3], "observables": ["demand"]},
                      "worlds": [("a", .5, None), ("b", .5, None)], "principle": "no_benefit"},
    "W3_flexibility_costs_mov": {"family": "waiting", "request": lambda: p2_base(fixed_order_cost=150., minimum=0.), "recourse": {"review_periods": [3], "observables": ["demand"]},
                                 "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.4))], "principle": "ordering_only"},
    # P1 / P2 / P3 interactions
    "I1_p1_fixed_cost_lots": {"family": "p1", "request": lambda: p2_base(fixed_order_cost=120., minimum=300.), "recourse": {"review_periods": [3], "observables": ["demand"]},
                              "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.4))], "principle": "moq_in_every_branch"},
    "I2_p2_transfer_recourse": {"family": "p2", "request": lambda: p2_base(lane_lead_periods=2, opening_branch=300.), "recourse": {"review_periods": [3], "observables": ["demand"], "actions": ["transfer"]},
                                "worlds": [("normal", .5, None), ("north_surge", .5, scale_demand(1.3))], "principle": "transfers_adapt_conserved"},
    "I3_p3_source_mix": {"family": "p3", "request": lambda: sourcing_base("E2_landed_beats_unit_price"), "recourse": {"review_periods": [3], "observables": ["demand", "receipts"]},
                         "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.4))], "principle": "capacity_in_every_branch"},
    "I4_p3_shares_hold": {"family": "p3", "request": lambda: sourcing_base("C2_declared_min_max_share"), "recourse": {"review_periods": [3], "observables": ["demand"]},
                          "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.3))], "principle": "shares_in_every_branch"},
    "I5_p3_switching_cost": {"family": "p3", "request": lambda: sourcing_base("E6_switching_cost_retains_incumbent"), "recourse": {"review_periods": [3], "observables": ["receipts"]},
                             "worlds": [("full", .5, None), ("short", .5, short_fill("src_A", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), .4))], "principle": "ordering_only"},
    "I6_multi_sku_shared_capacity": {"family": "p3", "request": lambda: sourcing_base("C5_shared_capacity_multi_sku"), "recourse": {"review_periods": [3], "observables": ["demand"]},
                                     "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.3))], "principle": "capacity_in_every_branch"},
    "I7_correlated_plant": {"family": "correlated", "request": lambda: sourcing_base("R4_shared_plant_no_fake_diversification"), "recourse": {"review_periods": [3], "observables": ["receipts"]},
                            "worlds": [("plant_up", .5, None), ("plant_down", .5, compose(short_fill("src_A", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), .5), short_fill("src_B", (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), .5)))],
                            "principle": "plant_observed_once"},
    # sectors
    "S1_commercial_packs": {"family": "sector", "request": lambda: sector_base("C1_case_pack_rounding"), "recourse": {"review_periods": [3], "observables": ["demand"]},
                            "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.4))], "principle": "packs_in_every_branch"},
    "S2_produce_sell_through": {"family": "sector", "request": lambda: sector_base("P2_near_expiry_inventory"), "recourse": {"review_periods": [2], "observables": ["demand"]},
                                "worlds": [("slow", .5, scale_demand(.7)), ("fast", .5, scale_demand(1.3))], "principle": "feasible_every_world"},
    "S3_meat_cold_chain": {"family": "sector", "request": lambda: sector_base("M1_chilled_shelf_life"), "recourse": {"review_periods": [3], "observables": ["demand", "receipts"]},
                           "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.3))], "principle": "feasible_every_world"},
    "S4_mixed_sectors_static_infeasible": {"family": "sector", "request": lambda: sector_base("X1_commercial_plus_produce"), "recourse": {"review_periods": [3], "observables": ["demand"]},
                         "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.3))], "principle": "feasible_every_world"},
    "S5_mixed_sectors": {"family": "sector", "request": lambda: sector_base("X1_commercial_plus_produce"), "recourse": {"review_periods": [3], "observables": ["demand"]},
                         "worlds": [("normal", .5, None), ("high", .5, scale_demand(1.15))], "principle": "feasible_every_world"},
    # scale / tree
    "T1_tree_three_histories": {"family": "tree", "request": lambda: p2_base(), "recourse": {"review_periods": [3], "observables": ["demand", "receipts"], "continuations": 2}, "worlds": "tree", "principle": "ordering_only"},
    "T2_tree_two_epochs": {"family": "tree", "request": lambda: p2_base(), "recourse": {"review_periods": [3, 6], "observables": ["demand", "receipts"], "continuations": 2}, "worlds": "tree", "principle": "ordering_only"},
    "T3_perfect_information_bound": {"family": "tree", "request": lambda: p2_base(), "recourse": {"review_periods": [2, 5], "observables": ["demand"], "continuations": 2}, "worlds": "tree", "principle": "pi_ordering"},
}


def build(name: str) -> tuple[Request, Recourse | None, list[World]]:
    spec = FIXTURES[name]
    req = with_recourse(spec["request"](), **spec["recourse"])
    rc = resolve(req)
    if spec["worlds"] == "tree":
        worlds = draw_tree(req, rc, SEED, 3, rc.spec.continuations) if rc is not None and rc.epochs else draw(req, SEED, 3)
    else:
        assert rc is not None and rc.epochs, name
        worlds = branches(req, rc, spec["worlds"], rc.epochs[0], continuations=rc.spec.continuations)
    return req, rc, worlds
