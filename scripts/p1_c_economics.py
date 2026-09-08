"""Objective 3: C as a finite-horizon economics problem. Diagnostic only; nothing here changes a default.
Writes docs/zaad_full/evidence/p1/closure/c_economics.json and prints the reconciliation."""
from __future__ import annotations
import json
from statistics import mean
import numpy as np
from scripts.p1_fixtures import build, REVIEWS, SEEDS
from zaad.full.planner import plan, protection_profile, supply_profiles
from zaad.full.replay import replay
from zaad.full.worlds import draw, forecast_all

FIX = "C_moq_four_weeks"
EXTRA = 12   # post-window periods simulated for consumption of residual stock


def run(seed, policy):
    req = build(FIX, seed); truth = draw(req, seed + 10000, 1)[0]
    kept = []
    out = replay(req, truth, REVIEWS, policy, keep_requests=kept)
    price, salvage = req.skus[0].asset_value, req.skus[0].terminal_value
    h = req.locations[0].holding_per_value_period + req.liquidity.cost_of_capital_per_period
    mu = forecast_all(req)[req.services[0].id]["mean"]
    led = out["ledger"]
    purchases = [sum(p["quantity"] for p in r["purchases"]) for r in out["reviews"]]
    on_hand_end = sum(x["quantity"] for x in out["reviews"][-1]["settlement"]["end_stock"])
    # residual stock at the window end, on hand plus in transit, is what closing_assets credits at salvage
    ending = -led["closing_assets"] / salvage if salvage else on_hand_end
    in_transit = ending - on_hand_end
    served = sum(x["served"] for r in out["reviews"] for x in r["settlement"]["service_by_period"])
    demand = sum(x["demand"] for r in out["reviews"] for x in r["settlement"]["service_by_period"])
    prot = 0.
    moq_units = 0.
    if policy == "gated":
        for r in kept:
            rep = plan(r)
            for o in rep["economics"]["orders"]:
                moq_units += o["attribution"]["MOQ"]
            prot = max(prot, max((row["protection_units"] for row in rep["protection"]), default=0.))
    lot_residual = max(0., ending - (mu + 15.))      # residual above one period of demand plus lean protection
    # terminal valuations of the ending inventory
    salvage_total = out["economic_cost"]
    full_total = salvage_total - ending * (price - salvage)
    k = np.arange(1, int(round(ending)) + 1)
    continuation_credit = float(np.sum(price * (1 - h * k / mu))) if ending > 0 else 0.
    continuation_total = salvage_total + ending * salvage - continuation_credit
    # extended-horizon consumption: draw further truth periods and draw the residual down
    ext_req = req.model_copy(update={"horizon": EXTRA})
    ext_world = draw(ext_req, seed + 20000, 1)[0]
    stock, consumed, held = ending, 0., 0.
    for t in range(EXTRA):
        d = ext_world.demand[req.services[0].id][t]
        take = min(stock, d); consumed += take; stock -= take
        held += stock
    empirical_total = salvage_total + ending * salvage - consumed * price + held * h * price - stock * salvage
    return {"seed": seed, "policy": policy, "ledger": led, "total_salvage": salvage_total, "total_full_value": full_total,
            "total_continuation": continuation_total, "total_extended_empirical": empirical_total,
            "purchased_units": sum(purchases), "purchases": purchases, "served": served, "demand": demand,
            "ending_units": ending, "on_hand_end": on_hand_end, "in_transit_end": in_transit, "terminal_credit_salvage": ending * salvage, "moq_attributed_units": moq_units,
            "lot_residual_units": lot_residual, "post_window_consumed": consumed, "post_window_left": stock, "periods_to_consume": (ending / mu if mu else None)}


rows = [run(s, p) for s in SEEDS for p in ("gated", "reorder_point")]
json.dump(rows, open("docs/zaad_full/evidence/p1/closure/c_economics.json", "w"), indent=1, default=float)
g = [r for r in rows if r["policy"] == "gated"]; b = [r for r in rows if r["policy"] == "reorder_point"]
def m(key, rs): return mean(r[key] for r in rs)
def ml(key, rs): return mean(r["ledger"].get(key, 0.) for r in rs)
print("C reconciliation (means over 3 seeds), ZAAD minus reorder_point:")
for key in ("procurement", "holding", "sla", "lost_sales_opportunity", "order_fees", "closing_assets"):
    print(f"  {key:24s} zaad {ml(key,g):9.1f}  base {ml(key,b):9.1f}  delta {ml(key,g)-ml(key,b):+8.1f}")
print(f"  {'purchased units':24s} zaad {m('purchased_units',g):9.1f}  base {m('purchased_units',b):9.1f}")
print(f"  {'residual units (end)':24s} zaad {m('ending_units',g):9.1f}  base {m('ending_units',b):9.1f}   (on hand zaad {m('on_hand_end',g):.0f} base {m('on_hand_end',b):.0f}; in transit zaad {m('in_transit_end',g):.0f} base {m('in_transit_end',b):.0f})")
print(f"  {'lot residual above need':24s} zaad {m('lot_residual_units',g):9.1f}  base {m('lot_residual_units',b):9.1f}   MOQ units attributed in ZAAD's period-0 orders {m('moq_attributed_units',g):.0f}")
print(f"  {'served / demand':24s} zaad {m('served',g):9.1f}/{m('demand',g):.1f}  base {m('served',b):9.1f}/{m('demand',b):.1f}")
for key, label in (("total_salvage", "80% salvage (current)"), ("total_full_value", "100% purchase value / zero haircut"), ("total_continuation", "continuation value (derived)"), ("total_extended_empirical", "extended horizon, empirical consumption")):
    zg, zb = m(key, g), m(key, b)
    print(f"  {label:40s} zaad {zg:8.0f}  base {zb:8.0f}  delta {100*(zg-zb)/zb:+.2f}%")
print(f"  post-window: zaad consumed {m('post_window_consumed',g):.0f} of {m('ending_units',g):.0f} (left {m('post_window_left',g):.0f}); base consumed {m('post_window_consumed',b):.0f} of {m('ending_units',b):.0f} (left {m('post_window_left',b):.0f}); periods to consume zaad {m('periods_to_consume',g):.1f} base {m('periods_to_consume',b):.1f}")
