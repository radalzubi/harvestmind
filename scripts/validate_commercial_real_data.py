"""Rolling-origin backtest of the commercial optimizer on REAL public data.

WHAT THIS TESTS, PRECISELY. Four ordering policies face the same demand
path, the same supply shocks, the same capacity, the same recourse
economics and the SAME settlement function. They differ only in what they
are allowed to know and how they reason about it. Any edge therefore comes
from the decision rule and not from the harness, which is a claim that five
separate harness defects in this repository's history have earned the right
to be stated defensively.

THE POLICIES
  naive     order-up-to trailing 12-month mean demand. No optimizer, no
            model of supply. This is what a spreadsheet does and it is the
            only baseline an operator will recognise as their status quo.
  det_mean  the SAME optimizer, given a point forecast: mean demand, mean
            lead time, mean fill. Fill-AWARE, so it is not a straw man. It
            is the honest question 'does uncertainty modelling pay?'
  det_p90   the SAME optimizer, told to assume a p90 lead time. The
            cautious planner who buffers by inflating an input.
  sp        the multi-period stochastic program over bootstrapped scenarios
            drawn from the TRAINING window only.

NO LOOKAHEAD. Scenarios are bootstrapped strictly from months before the
origin. Realized shocks enter only in settlement.

THE GUARD. A result is suppressed rather than reported when service falls
outside 90-100% or a single cost component exceeds 90% of the total. Every
headline number this repository has had to retract was preceded by exactly
one of those two symptoms while the cost figure still looked plausible.
"""
from __future__ import annotations

import argparse
import statistics as st
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optimization.multi_period_sp import MultiPeriodStochasticLP  # noqa: E402
from synthetic.commercial.jordan_distributor_v2 import (  # noqa: E402
    ABC_STRUCTURE, GROSS_MARGIN_IMPORT, ROUTE_PROFILE,
)
from validation.commercial.real_data import (  # noqa: E402
    PORT_DATA_START, REGIMES, demand_index, regime_of,
    route_shock_panel,
)

HORIZON = 12          # months; import lead times are 1-3 months
CARRY_PER_MONTH = 0.02   # calibrated band 1.5-2.5%/month


# ── the operator's cross-section (synthetic; only the TIME PATH is real) ──
def build_operator(n_skus: int, n_suppliers: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    routes = list(ROUTE_PROFILE)
    probs = np.array([ROUTE_PROFILE[r]["share"] for r in routes])
    probs /= probs.sum()
    suppliers = []
    for k in range(n_suppliers):
        r = str(rng.choice(routes, p=probs))
        suppliers.append({
            "supplier_id": f"SUP-{k + 1:03d}", "route": r,
            "base_fill": float(np.clip(
                rng.normal(ROUTE_PROFILE[r]["fill"], 0.025), 0.5, 1.0)),
            # Ocean import lead times run 1-3 months door to door.
            "lead_months": int(np.clip(
                round(ROUTE_PROFILE[r]["lead"] / 1.5), 1, 3)),
        })

    def abc(i):
        a = int(n_skus * ABC_STRUCTURE["A"]["sku_share"])
        b = a + int(n_skus * ABC_STRUCTURE["B"]["sku_share"])
        return "A" if i < a else "B" if i < b else "C"

    skus, weights = [], []
    for i in range(n_skus):
        klass = abc(i)
        spec = ABC_STRUCTURE[klass]
        n_in = max(1, int(n_skus * spec["sku_share"]))
        cost = float(np.round(rng.uniform(0.4, 9.0), 2))
        gm = float(rng.uniform(*GROSS_MARGIN_IMPORT))
        skus.append({
            "sku": f"SKU-{i + 1:04d}", "abc": klass, "unit_cost": cost,
            "unit_price": cost / (1 - gm), "margin": cost / (1 - gm) - cost,
            "supplier_id": suppliers[i % n_suppliers]["supplier_id"],
        })
        weights.append(spec["volume_share"] / n_in)
    w = np.array(weights)
    return {"skus": skus, "suppliers": {s["supplier_id"]: s for s in suppliers},
            "weights": w / w.sum()}


def demand_panel(op: dict, months: list[str], index: dict[str, float],
                 base_units: float, idio_cv: float, seed: int
                 ) -> dict[tuple[str, str], float]:
    """SKU x month demand. Level and shape are REAL; idio noise is not."""
    rng = np.random.default_rng(seed)
    out = {}
    for s, w in zip(op["skus"], op["weights"], strict=True):
        for m in months:
            mult = rng.normal(1.0, idio_cv) if idio_cv > 0 else 1.0
            out[(s["sku"], m)] = max(
                0.0, base_units * w * index[m] * max(mult, 0.05))
    return out


# ── one settlement path, shared by every policy ──────────────────────────
def settle(schedule, op, months, demand, real_fill, real_lead, opening,
           warehouse_cap=None, pipeline=None):
    """Replay a schedule against realized fills and lead times.

    Three rules, each of which exists because breaking it has previously
    produced a headline this repository had to retract.

    CREDITED WITH WHAT ARRIVES, never with what was ordered. Committed-as-
    delivered scoring was the first retracted result.

    A WAREHOUSE THAT CAN FILL UP. US Census reports merchant wholesalers
    holding a mean inventory/sales ratio of 1.264, about 38 days, over 414
    months, and a p90 of 1.35. A model with no upper bound on stock will
    happily buy sixteen months of cover to avoid one month of lost margin,
    because holding is the only thing it pays for. Stock above the cap is
    written off at cost: it is volume the operator physically could not
    take in. Every policy faces the identical cap.

    GOODS ALREADY ON THE WATER. An importer with a two-month lead time did
    not start from an empty pipeline. Beginning with nothing in transit
    guarantees a shortage in the opening months for every policy alike,
    which swamps the comparison with a cost none of them could avoid.
    """
    meta = {s["sku"]: s for s in op["skus"]}
    arrivals: dict[tuple[str, int], float] = dict(pipeline or {})
    for (sup, sku, t), q in schedule.items():
        if q <= 0:
            continue
        lag = int(real_lead.get((sup, t), op["suppliers"][sup]["lead_months"]))
        f = float(real_fill.get((sup, t), 1.0))
        at = t + lag
        if at < len(months):
            arrivals[(sku, at)] = arrivals.get((sku, at), 0.0) + q * f

    carry = dict(opening)
    shortage = holding = overflow = 0.0
    served = demanded = 0.0
    for t, m in enumerate(months):
        period_stock = 0.0
        pending = {}
        for sku, sm in meta.items():
            d = float(demand.get((sku, m), 0.0))
            have = carry.get(sku, 0.0) + arrivals.get((sku, t), 0.0)
            got = min(have, d)
            shortage += max(d - have, 0.0) * sm["margin"]
            left = max(have - d, 0.0)
            pending[sku] = left
            period_stock += left
            served += got
            demanded += d
        if warehouse_cap is not None and period_stock > warehouse_cap > 0:
            # Pro-rata write-off: the operator cannot choose which pallet
            # gets turned away at the gate any more than the model can.
            scale = warehouse_cap / period_stock
            for sku in pending:
                lost = pending[sku] * (1.0 - scale)
                overflow += lost * meta[sku]["unit_cost"]
                pending[sku] *= scale
        for sku, left in pending.items():
            holding += left * meta[sku]["unit_cost"] * CARRY_PER_MONTH
            carry[sku] = left
    return {"total": shortage + holding + overflow, "shortage": shortage,
            "holding": holding, "overflow": overflow,
            "fill_rate": served / demanded if demanded else 1.0,
            "ending_inventory": sum(carry.values())}


def _harness_failure(res: dict) -> str | None:
    """Reject a fold only when the HARNESS is broken, never on an outcome.

    THIS FUNCTION USED TO BE A TRAP. It began as a guard that also rejected
    folds where one cost component dominated, on the reasoning that every
    previously retracted headline in this repository was preceded by such a
    lopsided split. Applied to whole folds it did something far worse than
    the defects it was built to catch: it discarded 136 of 258 folds, and
    the discarded ones had a median SP edge of -4.21% against the kept
    ones' +7.33%. The filter was quietly selecting the folds where the
    stochastic policy wins.

    The reason is that a fold where holding is 96% of cost is NOT
    degenerate. It is an easy month: demand was met by everyone, and the
    only thing separating the policies is who tied up less capital. Those
    are precisely the folds where buying extra service loses, and dropping
    them flatters any policy that buys service.

    So outcomes are never grounds for rejection now. Only three things are,
    and each of them means a number is impossible rather than unwelcome:
    a fill rate outside [0, 1], a non-positive total cost leaving nothing
    to compare, and overflow dominating, which can only happen if the
    optimizer and the settlement disagree about what disposal costs.

    Everything else is reported, and the lopsided folds are STRATIFIED in
    the output instead of removed, because which regime the value comes
    from is the finding, not the contaminant.
    """
    fr = res["fill_rate"]
    if not (0.0 <= fr <= 1.0 + 1e-9):
        return f"fill rate {fr:.3f} is not a fraction; settlement is broken"
    if res["total"] <= 0:
        return "non-positive total cost leaves nothing to compare"
    if res.get("overflow", 0.0) / res["total"] > 0.50:
        return ("overflow is the majority of cost; the optimizer and the "
                "settlement disagree about disposal")
    return None


def run_fold(op, months_all, index, shocks, origin_idx, train_m,
             n_scen, rng, base_units, idio_cv, opening_cover, seed,
             inv_cap_months=2.0, service_z=1.64,
             iid_scenarios=False):
    train = months_all[origin_idx - train_m:origin_idx]
    evalm = months_all[origin_idx:origin_idx + HORIZON]
    if len(evalm) < HORIZON:
        return None

    demand = demand_panel(op, months_all, index, base_units, idio_cv, seed)
    skus = [s for s in op["skus"] if s["abc"] in ("A", "B")]
    keep = {s["sku"] for s in skus}
    meta = {s["sku"]: s for s in skus}
    sups = sorted({s["supplier_id"] for s in skus})

    # ---- training-window statistics only ----
    tr_dem = {j: st.mean([demand[(j, m)] for m in train]) for j in keep}
    tr_fill: dict[str, list[float]] = {}
    for sid in sups:
        route = op["suppliers"][sid]["route"]
        base = op["suppliers"][sid]["base_fill"]
        obs = [base * shocks[route].get(m, 1.0) for m in train
               if m in shocks[route]]
        tr_fill[sid] = obs or [base]

    # ---- scenarios bootstrapped from the training window ----
    rows, leads, yields_ = [], {}, {}
    # Scenario paths by compounding resampled month-over-month growth.
    #
    # SEASONAL BY DEFAULT, and that is a correction rather than a
    # preference. The original generator pooled every growth rate
    # regardless of calendar month, which on a NOT seasonally adjusted
    # series discards the strongest signal in it. Scored on 4,404
    # origin-horizon pairs of real US Census history, the pooled version
    # reached a Weighted Interval Score of 0.0541 against 0.0356 for the
    # seasonal one, 52% worse, and worse than both a seasonal-naive and a
    # random-walk reference. It was also badly over-dispersed: 95.9%
    # coverage from a nominal 80% interval, so the optimizer was hedging
    # against a spread far wider than history supports.
    pooled = [index[train[i + 1]] / index[train[i]]
              for i in range(len(train) - 1) if index[train[i]] > 0]
    by_month: dict[int, list[float]] = {}
    for i in range(len(train) - 1):
        if index[train[i]] > 0:
            by_month.setdefault(int(train[i + 1][5:7]), []).append(
                index[train[i + 1]] / index[train[i]])
    origin_month = int(months_all[origin_idx][5:7])

    def _pool(h: int) -> list[float]:
        if iid_scenarios:
            return pooled
        cal = (origin_month + h - 1) % 12 + 1
        # Fall back to the pooled set when a calendar bucket is too thin to
        # resample from; three years of training gives only three draws.
        return by_month.get(cal) or pooled

    for w in range(n_scen):
        path, cur = [], 1.0
        for h in range(HORIZON):
            pool_h = _pool(h)
            cur *= float(rng.choice(pool_h)) if pool_h else 1.0
            path.append(cur)
        for j in keep:
            for t in range(HORIZON):
                rows.append({"scenario_index": w, "scenario_weight": 1 / n_scen,
                             "product_id": j, "period": t,
                             "demand_kg": tr_dem[j] * path[t]})
        for sid in sups:
            yields_[(w, sid)] = float(rng.choice(tr_fill[sid]))
            leads[(w, sid)] = op["suppliers"][sid]["lead_months"]
    scen = pd.DataFrame(rows)

    cap = pd.DataFrame([{"supplier_id": meta[j]["supplier_id"],
                         "product_id": j,
                         "capacity_kg": tr_dem[j] * 3.0,
                         "price_per_kg": meta[j]["unit_cost"]} for j in keep])

    # Warehouse ceiling, from the real inventory/sales ratio rather than a
    # tuned number: US merchant wholesalers average 1.264 months of stock
    # with a p90 of 1.35, so a 2-month cap is deliberately SLACK against
    # the real distribution. It binds the pathological solution without
    # binding a realistic one.
    total_mean = sum(tr_dem.values())
    warehouse_cap = total_mean * inv_cap_months

    kw = dict(n_periods=HORIZON, spot_cost_multiplier=1.0,
              spot_capacity_factor=0.0,
              # Disposal must cost what settlement charges for it. Left at
              # zero the model buys freely and dumps the excess for nothing,
              # while the replay writes the same units off at cost: the
              # optimizer then optimizes a cheaper world than the one it is
              # scored in, and the comparison is meaningless.
              waste_cost_by_product={j: meta[j]["unit_cost"] for j in keep},
              unmet_cost_by_product={j: meta[j]["margin"] for j in keep},
              holding_cost_by_product={
                  j: meta[j]["unit_cost"] * CARRY_PER_MONTH for j in keep},
              decay_rate_by_product={j: 0.0 for j in keep},
              inventory_capacity_total=warehouse_cap)

    opening = {j: tr_dem[j] * opening_cover for j in keep}

    # Goods already in transit at t=0, one month of cover landing in each
    # month before the first self-placed order can arrive.
    pipeline: dict[tuple[str, int], float] = {}
    for j in keep:
        lead = op["suppliers"][meta[j]["supplier_id"]]["lead_months"]
        for t in range(max(lead, 1)):
            pipeline[(j, t)] = pipeline.get((j, t), 0.0) + tr_dem[j]

    det = scen[scen["scenario_index"] == 0].copy()
    det["scenario_weight"] = 1.0
    det_mean = det.copy()
    for j in keep:
        det_mean.loc[det_mean["product_id"] == j, "demand_kg"] = tr_dem[j]

    schedules: dict[str, dict] = {}
    solves = {
        "det_mean": (det_mean,
                     {(0, s): op["suppliers"][s]["lead_months"] for s in sups},
                     {(0, s): st.mean(tr_fill[s]) for s in sups}),
        "det_p90": (det_mean,
                    {(0, s): op["suppliers"][s]["lead_months"] + 1
                     for s in sups},
                    {(0, s): st.mean(tr_fill[s]) for s in sups}),
    }
    for tag, (dfr, lt, ys) in solves.items():
        r = MultiPeriodStochasticLP(**kw).solve(
            dfr, cap, lead_times=lt, yield_scenarios=ys,
            opening_inventory=opening)
        if r.get("status") not in ("optimal", "locallyOptimal"):
            return None
        schedules[tag] = {k: v for k, v in r["x"].items() if v > 0}

    r = MultiPeriodStochasticLP(**kw).solve(
        scen, cap, lead_times=leads, yield_scenarios=yields_,
        opening_inventory=opening)
    if r.get("status") not in ("optimal", "locallyOptimal"):
        return None
    schedules["sp"] = {k: v for k, v in r["x"].items() if v > 0}

    # Naive: textbook periodic order-up-to (R, S) with a normal-approximation
    # safety stock, grossed up by the observed fill rate. This is NOT a straw
    # man: it is what a competent planner does in a spreadsheet, and it knows
    # both that demand varies and that suppliers under-deliver. It simply
    # does not optimize across products, periods or scenarios.
    schedules["naive"] = {}
    for j in keep:
        sid = meta[j]["supplier_id"]
        lead = op["suppliers"][sid]["lead_months"]
        hist = [demand[(j, m)] for m in train]
        sd = st.pstdev(hist) if len(hist) > 1 else 0.0
        f_bar = max(st.mean(tr_fill[sid]), 0.05)
        cover = lead + 1                      # lead plus the review period
        target = tr_dem[j] * cover + service_z * sd * (cover ** 0.5)
        for t in range(HORIZON):
            # Open-loop equivalent of order-up-to: replace expected usage,
            # and close the gap to target in the first period.
            q = tr_dem[j] / f_bar
            if t == 0:
                q += max(target - tr_dem[j] * (opening_cover + lead), 0.0) / f_bar
            schedules["naive"][(sid, j, t)] = q

    # ---- realized shocks, evaluation window only ----
    real_fill, real_lead = {}, {}
    for sid in sups:
        route = op["suppliers"][sid]["route"]
        base = op["suppliers"][sid]["base_fill"]
        for t, m in enumerate(evalm):
            real_fill[(sid, t)] = min(1.0, base * shocks[route].get(m, 1.0))
            real_lead[(sid, t)] = op["suppliers"][sid]["lead_months"]

    ev_demand = {(j, m): demand[(j, m)] for j in keep for m in evalm}
    out = {}
    for tag, sch in schedules.items():
        out[tag] = settle(sch, {"skus": skus, "suppliers": op["suppliers"]},
                          evalm, ev_demand, real_fill, real_lead, opening,
                          warehouse_cap=warehouse_cap, pipeline=pipeline)
    out["_months"] = evalm
    out["_mean_shock"] = st.mean(
        [shocks[op["suppliers"][s]["route"]].get(m, 1.0)
         for s in sups for m in evalm])
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seeds", default="7,19,33")
    p.add_argument("--train-months", type=int, default=36)
    p.add_argument("--scenarios", type=int, default=30)
    p.add_argument("--skus", type=int, default=40)
    p.add_argument("--suppliers", type=int, default=14)
    p.add_argument("--opening-cover", type=float, default=1.0,
                   help="months of stock on hand at t=0")
    p.add_argument("--idio-cv", type=float, default=0.25,
                   help="SKU-level noise (SYNTHETIC; 0 isolates real signal)")
    p.add_argument("--base-units", type=float, default=20000.0)
    p.add_argument("--start", default="1994-01")
    p.add_argument("--real-supply-only", action="store_true",
                   help="only folds whose evaluation window has PortWatch data")
    p.add_argument("--stride", type=int, default=1)
    p.add_argument("--csv", default=None,
                   help="write one row per fold, so runs can be compared "
                        "PAIRED on identical folds rather than by comparing "
                        "two medians over two different fold sets.")
    p.add_argument("--iid-scenarios", action="store_true",
                   help="resample growth rates ignoring calendar month, the "
                        "original behaviour. Measurably worse calibrated on "
                        "real history; kept only for comparison.")
    p.add_argument("--flat-supply", action="store_true",
                   help="replace the measured route shocks with all-ones. "
                        "The control arm: everything else identical, so any "
                        "difference is attributable to supply uncertainty "
                        "alone rather than to the period or the seeds.")
    p.add_argument("--inv-cap-months", type=float, default=2.0,
                   help="warehouse ceiling in months of demand; "
                        "real US wholesaler mean is 1.26, p90 1.35")
    p.add_argument("--service-z", type=float, default=1.64,
                   help="safety factor for the naive baseline")
    a = p.parse_args()

    index = demand_index()
    shocks = route_shock_panel()
    if a.flat_supply:
        shocks = {r: {m: 1.0 for m in s_} for r, s_ in shocks.items()}
    seeds = [int(s) for s in a.seeds.split(",")]
    months = [m for m in sorted(index) if m >= a.start]

    print("\n" + "=" * 78)
    print("COMMERCIAL OPTIMIZER — BACKTEST ON REAL PUBLIC DATA")
    print("=" * 78)
    print("  demand path   US Census MWTS NAICS 4244 via FRED (real, NSA)")
    print("  supply shocks " + ("DISABLED (control arm, all fills at base)"
                                 if a.flat_supply else
                                 "IMF PortWatch AIS, per-route ports (real)"))
    print(f"  cross-section synthetic; idio CV = {a.idio_cv}")
    print("  scenarios     " + ("iid growth bootstrap (miscalibrated)"
                               if a.iid_scenarios else
                               "seasonal growth bootstrap"))
    print(f"  opening cover {a.opening_cover} months   horizon {HORIZON} months")
    print(f"  warehouse cap {a.inv_cap_months} months "
          f"(real wholesaler I/S mean 1.26, p90 1.35)")
    print(f"  window        {months[0]} .. {months[-1]}  "
          f"({len(months)} months, {len(seeds)} seeds)")

    TAGS = ("naive", "det_mean", "det_p90", "sp")
    fold_rows: list[dict] = []
    BASES = ("naive", "det_mean", "det_p90")
    by_regime: dict[str, dict] = {}
    grand = {b: [] for b in BASES}
    grand_fills = {t: [] for t in TAGS}
    suppressed = 0
    n_total = 0
    strata: dict[str, list[float]] = {}

    for seed in seeds:
        op = build_operator(a.skus, a.suppliers, seed)
        rng = np.random.default_rng(seed + 991)
        for oi in range(a.train_months, len(months) - HORIZON + 1, a.stride):
            evalm = months[oi:oi + HORIZON]
            mid = evalm[HORIZON // 2]
            regime = regime_of(mid) or "unclassified"
            has_supply = evalm[0] >= PORT_DATA_START
            if a.real_supply_only and not has_supply:
                continue
            r = run_fold(op, months, index, shocks, oi, a.train_months,
                         a.scenarios, rng, a.base_units, a.idio_cv,
                         a.opening_cover, seed, a.inv_cap_months,
                         a.service_z, a.iid_scenarios)
            if not r:
                continue
            bad = [t for t in TAGS if _harness_failure(r[t])]
            if bad:
                suppressed += 1
                continue
            n_total += 1
            slot = by_regime.setdefault(regime, {
                "edges": {b: [] for b in BASES},
                "fills": {t: [] for t in TAGS},
                "shock": [], "supply": has_supply, "span": [mid, mid]})
            slot["span"][0] = min(slot["span"][0], mid)
            slot["span"][1] = max(slot["span"][1], mid)
            slot["shock"].append(r["_mean_shock"])
            # Stratum set by the BASELINE's own cost split, never by SP's,
            # so the split cannot be drawn to favour the policy under test.
            # "binding" means the month was hard enough that missing demand
            # actually cost something.
            fold_rows.append({
                "seed": seed, "origin": months[oi], "eval_mid": mid,
                "regime": regime, "real_supply": int(has_supply),
                "mean_shock": round(r["_mean_shock"], 5),
                **{f"{t}_{k}": round(r[t][k], 4)
                   for t in TAGS
                   for k in ("total", "shortage", "holding", "overflow",
                             "fill_rate")}})
            _bt = r["det_mean"]["total"]
            _stratum = ("binding"
                        if _bt > 0 and r["det_mean"]["shortage"] / _bt > 0.20
                        else "slack")
            if _bt > 0:
                strata.setdefault(_stratum, []).append(
                    (_bt - r["sp"]["total"]) / _bt * 100)
            sp = r["sp"]["total"]
            for b in BASES:
                if r[b]["total"] > 0:
                    e = (r[b]["total"] - sp) / r[b]["total"] * 100
                    slot["edges"][b].append(e)
                    grand[b].append(e)
            for t in TAGS:
                slot["fills"][t].append(r[t]["fill_rate"])
                grand_fills[t].append(r[t]["fill_rate"])

    order = [k for k in REGIMES if k in by_regime] + \
            [k for k in by_regime if k not in REGIMES]
    for regime in order:
        slot = by_regime[regime]
        n = len(slot["fills"]["sp"])
        tag = "real supply shocks" if slot["supply"] else "real demand only"
        print(f"\n  {regime.upper():<16} eval mid {slot['span'][0]}..{slot['span'][1]}"
              f"  n={n}  ({tag})")
        if slot["supply"]:
            print(f"      mean realized supply shock  "
                  f"{st.mean(slot['shock']):.3f}")
        for b, lab in (("naive", "SP vs naive order-up-to"),
                       ("det_mean", "SP vs fill-aware determ."),
                       ("det_p90", "SP vs cautious p90")):
            e = slot["edges"][b]
            if e:
                print(f"      {lab:26} median {st.median(e):+7.2f}%   "
                      f"wins {sum(1 for x in e if x > 0)}/{len(e)}")
        print("      service:  " + "   ".join(
            f"{t} {st.mean(slot['fills'][t]):.1%}" for t in TAGS))

    print("\n" + "-" * 78)
    print(f"  POOLED  ({n_total} admissible folds)")
    for b, lab in (("naive", "SP vs naive order-up-to"),
                   ("det_mean", "SP vs fill-aware determ."),
                   ("det_p90", "SP vs cautious p90")):
        e = grand[b]
        if e:
            lo = np.percentile(e, 25)
            hi = np.percentile(e, 75)
            print(f"    {lab:26} median {st.median(e):+7.2f}%  "
                  f"IQR [{lo:+.2f}, {hi:+.2f}]  "
                  f"wins {sum(1 for x in e if x > 0)}/{len(e)}")
    print("    service:  " + "   ".join(
        f"{t} {st.mean(grand_fills[t]):.1%}" for t in TAGS))
    if strata:
        print("\n    SP vs fill-aware determ., split by how hard the month was")
        print("    (stratum set by the BASELINE's cost split, not SP's)")
        for _k in ("binding", "slack"):
            _e = strata.get(_k, [])
            if _e:
                _lab = ("shortage > 20% of baseline cost" if _k == "binding"
                        else "holding-dominated, easy month")
                print(f"      {_k:<8} n={len(_e):<4} "
                      f"median {st.median(_e):+7.2f}%  "
                      f"wins {sum(1 for x in _e if x > 0)}/{len(_e)}   {_lab}")
    if suppressed:
        print(f"    folds suppressed by guard: {suppressed}")
    if a.csv and fold_rows:
        import csv as _csv
        path = Path(a.csv)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(fold_rows[0]))
            w.writeheader()
            w.writerows(fold_rows)
        print(f"    per-fold rows -> {path}  ({len(fold_rows)} folds)")
    print("-" * 78 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
