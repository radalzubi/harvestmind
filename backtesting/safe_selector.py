"""SAFE_SELECTED: optimization that knows when not to optimize.

The question every call answers is not "which policy is best?" but "is
there credible evidence that departing from what the operator already
does will improve the operator's objective?" If not, the answer is the
incumbent, and that answer is a success.

HOW A CANDIDATE DISPLACES THE INCUMBENT
  1. Multiple leakage-free rolling folds are built INSIDE the training
     window. Each fold's origin sees only history before it; its truth is
     the demand that followed and the supplier fills and leads that were
     actually recorded after it (``FoldInputs.supply_events``). Nothing at
     or after the real origin is touched
     nothing after a fold's own origin
     reaches that fold's training.
  2. Every candidate and the incumbent are settled on the same truth with
     the same settlement, capacity binding all of them alike.
  3. delta_cost = incumbent_cost - candidate_cost per fold (positive =
     candidate better), with a block bootstrap over folds (adjacent
     outcomes can be dependent even though their truth windows do not overlap).
  4. A candidate wins only if ALL of: its conservative one-sided lower
     bound on relative improvement exceeds the configured threshold
     service is non-inferior within the tolerance
     downside regret (the
     worst / p5 fold) is inside the risk budget; there were enough folds;
     its solves were usable without fallbacks. Ties go to the simpler
     policy
     the incumbent is simplest.
  5. Winner's curse: the candidate that wins the inner folds is then
     RE-EVALUATED on a held-out set of folds it was not chosen on
     (nested). If it does not beat the incumbent there as well, the
     incumbent is returned.

Insufficient history returns the incumbent, never the stochastic model.
"""

from __future__ import annotations

import os

from typing import Any

import math
from dataclasses import dataclass, field, replace

import numpy as np

from backtesting.counterfactual import (
    FoldInputs, FoldTruth, _mean, policy_deterministic_sp, policy_order_up_to,
    policy_stochastic_sp, policy_service_target, settle,
)
from backtesting.incumbent import IncumbentPolicy, configured_incumbent

INCUMBENT = "incumbent"
COMPLEXITY = {"incumbent": 0, "order_up_to": 1, "deterministic_sp": 2, "anchored_sp": 3, "adaptive_sp": 3,
              "service_target": 3, "stochastic_sp": 4, "dro": 5}


@dataclass
class SafeSelectionConfig:
    n_folds: int = 4                     # inner selection folds
    n_holdout_folds: int = 2             # nested re-check folds, not used for choosing
    holdout: int = 4                     # periods per fold truth
    min_history: int = 26                # periods before any candidate may be considered
    min_rel_improvement: float = 0.03    # conservative lower bound must exceed this (3% of incumbent cost)
    service_tolerance: float = 0.01      # candidate fill may be at most this far below incumbent
    max_regret_share: float = 0.10       # worst-fold relative loss vs incumbent allowed
    confidence: float = 0.80             # one-sided lower bound level
    block_length: int = 2                # folds per block in the bootstrap
    n_boot: int = 1000
    n_scen: int = 30
    prefer_simpler_within: float = 0.01  # ties within this relative margin go to the simpler policy
    allow_state_evidence: bool = False  # experimental bypass; never a default no-harm recommendation

    def __post_init__(self) -> None:
        if self.n_folds < 2 or self.holdout < 1 or self.n_holdout_folds < 2:
            raise ValueError("need at least 2 folds of at least 1 period")
        for k in ("n_folds", "n_holdout_folds", "holdout", "min_history", "block_length", "n_boot", "n_scen"):
            v = getattr(self, k)
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                raise ValueError(f"{k} must be a positive integer")
        if not 0.5 <= self.confidence < 1.0:
            raise ValueError("confidence must be in [0.5, 1)")
        for k in ("min_rel_improvement", "service_tolerance", "max_regret_share", "prefer_simpler_within"):
            if not math.isfinite(getattr(self, k)) or getattr(self, k) < 0:
                raise ValueError(f"{k} must be finite and >= 0")


@dataclass
class CandidateEvidence:
    name: str
    n_folds: int
    deltas_rel: list                     # (incumbent - candidate) / incumbent per fold
    service_diff: list                   # candidate fill - incumbent fill per fold
    inventory_diff: list                 # candidate avg inventory - incumbent
    solves_usable: int
    fallbacks: int
    stats: dict = field(default_factory=dict)
    gates: dict = field(default_factory=dict)
    passed: bool = False
    holdout_delta_rel: float | None = None
    holdout_gates: dict = field(default_factory=dict)
    holdout_stats: dict = field(default_factory=dict)


@dataclass
class SafeDecision:
    mode_run: str
    schedule: dict
    reason: str
    incumbent_label: str
    evidence: dict                       # name -> CandidateEvidence
    gates_config: dict
    history_periods: int
    warnings: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"mode_run": self.mode_run, "reason": self.reason, "incumbent": self.incumbent_label,
                "history_periods": self.history_periods, "gates": self.gates_config,
                "warnings": self.warnings,
                "candidates": {k: {"n_folds": v.n_folds, "stats": v.stats, "gates": v.gates,
                                   "passed": v.passed, "holdout_delta_rel": v.holdout_delta_rel,
                                   "holdout_gates": v.holdout_gates, "holdout_stats": v.holdout_stats,
                                   "solves_usable": v.solves_usable, "fallbacks": v.fallbacks}
                               for k, v in self.evidence.items()}}


# ── inner folds with REAL supplier outcomes ─────────────────────────────────
def inner_folds(fi: FoldInputs, n_folds: int, holdout: int, offset: int = 0) -> list:
    """Folds ending at -offset, -offset-holdout, ... Each fold's training is
    strictly before its origin (demand AND supply events)
    its truth is the
    demand and the recorded supplier outcomes in [origin, origin+holdout)."""
    folds = []
    n_hist = min(len(v) for v in fi.train_demand.values()) if fi.train_demand else 0
    for k in range(n_folds):
        end = -offset - k * holdout            # exclusive end of truth, relative to the real origin
        start = end - holdout                  # inner origin
        if -start > n_hist or start >= 0 and end > 0:
            break
        if n_hist + start < 8:                 # too little history before this inner origin
            break
        train = {j: fi.train_demand[j][:n_hist + start] for j in fi.products}
        truth_d = {(j, t): fi.train_demand[j][n_hist + start + t] for j in fi.products for t in range(holdout)
                   if n_hist + start + t < n_hist}
        sups = set(fi.supplier_of.values())
        ev_train = {s_: {p: v for p, v in fi.supply_events.get(s_, {}).items() if p < start} for s_ in sups}
        # An undated aggregate can contain the very holdout being evaluated.
        # No pre-origin supplier record means no defensible fold.
        if any(not ev_train[s_] for s_ in sups):
            continue
        train_fill = {s_: [v[0] for p, v in sorted(ev_train[s_].items())] for s_ in sups}
        inner_lead = {s_: max(0, int(round(_mean([v[1] for v in ev_train[s_].values()]))))
                      for s_ in sups}
        truth_f, truth_l, replayed, carried = {}, {}, 0, 0
        for s_ in sups:
            last_f = _mean(train_fill[s_])
            last_l = inner_lead[s_]
            for t in range(holdout):
                ev = fi.supply_events.get(s_, {}).get(start + t)
                if ev is not None:
                    last_f, last_l = float(ev[0]), int(ev[1])
                    replayed += 1
                else:
                    carried += 1
                truth_f[(s_, t)] = last_f
                truth_l[(s_, t)] = max(last_l, 0)
        mean_dem = {j: _mean(train[j]) for j in fi.products}
        # State-standardized replay, not a claimed reconstruction of historical
        # stock. Current stock and full-window mean must not leak backwards.
        opening = {j: mean_dem[j] for j in fi.products}
        pipeline = {(j, t): mean_dem[j] for j in fi.products
                    for t in range(inner_lead[fi.supplier_of[j]])}
        inner = FoldInputs(origin=fi.origin + start, horizon=holdout, products=fi.products,
                           supplier_of=fi.supplier_of, lead_of=inner_lead, train_demand=train,
                           train_fill=train_fill, unit_cost=fi.unit_cost, margin=fi.margin,
                           capacity=fi.capacity, opening=opening, pipeline=pipeline, policy=fi.policy,
                           promo_multiplier={}, supply_events={s_: {p - start: v for p, v in es.items()}
                                                               for s_, es in ev_train.items()}, incumbent=fi.incumbent,
                           route_of=fi.route_of, provenance=fi.provenance)
        folds.append((inner, FoldTruth(demand=truth_d, fill=truth_f, lead=truth_l),
                      {"start": start, "replayed_supply_events": replayed, "carried_forward": carried,
                       "state_basis": "standardized one-week opening plus mean lead pipeline"}))
    return folds


def _block_bootstrap_lower(xs: list, confidence: float, block: int, n_boot: int, rng) -> float:
    x = np.asarray(xs, dtype=float)
    n = len(x)
    if n == 0:
        return float("nan")
    if n == 1:
        return float(x[0])
    # A block spanning the entire sample always returns the sample mean,
    # fabricating a zero-width interval (notably on two confirmation folds).
    # Require at least two resampled blocks. Small samples remain weak evidence.
    b = max(1, min(block, n // 2))
    means = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, n - b + 1, size=int(math.ceil(n / b)))
        idx = np.concatenate([np.arange(s_, s_ + b) for s_ in starts])[:n]
        means[i] = x[idx].mean()
    return float(np.percentile(means, 100 * (1 - confidence)))


def _stats(deltas: list, cfg: SafeSelectionConfig, rng) -> dict:
    x = np.asarray(deltas, dtype=float)
    if len(x) == 0:
        return {}
    return {"mean": float(x.mean()), "median": float(np.median(x)),
            "sd": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
            "p5": float(np.percentile(x, 5)), "p25": float(np.percentile(x, 25)),
            "p75": float(np.percentile(x, 75)), "p95": float(np.percentile(x, 95)),
            "worst": float(x.min()), "best": float(x.max()),
            "win_rate": float((x > 0).mean()),
            "lower_bound": _block_bootstrap_lower(list(x), cfg.confidence, cfg.block_length, cfg.n_boot, rng),
            "downside_regret": float(-min(x.min(), 0.0))}


def run_candidate(name: str, fi: FoldInputs, warehouse_cap, rng, n_scen: int,
                  extra: dict | None = None) -> tuple[dict | None, dict]:
    if name == INCUMBENT:
        inc: IncumbentPolicy = fi.incumbent or configured_incumbent(cover_weeks=2.0)
        return inc.build_schedule(fi), {"status": "heuristic"}
    if name == "order_up_to":
        return policy_order_up_to(fi), {"status": "heuristic"}
    if name == "deterministic_sp":
        return policy_deterministic_sp(fi, warehouse_cap, rng)
    if name == "stochastic_sp":
        return policy_stochastic_sp(fi, warehouse_cap, rng, n_scen)
    if name == "service_target":
        return policy_service_target(fi, warehouse_cap, rng, n_scen)
    if extra and name in extra:
        return extra[name](fi, warehouse_cap, rng, n_scen)
    raise ValueError(f"unknown candidate {name}")



# ── candidate fan-out ────────────────────────────────────────────────────────
def _gate_workers() -> int:
    """Processes to solve a fold's candidates in parallel; 1 = sequential.
    Each process uses one HiGHS thread, so this is a count of cores."""
    try:
        return max(1, int(os.environ.get("HARVESTMIND_GATE_WORKERS", "1")))
    except ValueError:
        return 1


def _picklable_meta(meta: dict) -> dict:
    """Solver metadata carries the pyomo model and closures; the gate only
    reads plain values, so keep what crosses a process boundary."""
    import pickle
    out = {}
    for k, v in (meta or {}).items():
        if k == "model":
            continue
        try:
            pickle.dumps(v)
        except Exception:  # noqa: BLE001
            continue
        out[k] = v
    return out


def _run_candidate_seeded(args):
    name, fi, warehouse_cap, seed, n_scen, extra = args
    sched, meta = run_candidate(name, fi, warehouse_cap, np.random.default_rng(seed), n_scen, extra)
    return name, (sched, _picklable_meta(meta))


def _run_candidates(names, inner, warehouse_cap, rng, n_scen, extra, workers: int) -> dict:
    """Sequential mode consumes ``rng`` exactly as before (validation runs are
    reproducible). Parallel mode draws one child seed per candidate from
    ``rng`` and solves them in separate processes; results are deterministic
    for a given seed but not bit-identical to the sequential stream."""
    if workers <= 1 or len(names) <= 1:
        return {n: run_candidate(n, inner, warehouse_cap, rng, n_scen, extra) for n in names}
    import concurrent.futures as cf
    import multiprocessing as mp
    seeds = {n: int(rng.integers(0, 2**32 - 1)) for n in names}
    jobs = [(n, inner, warehouse_cap, seeds[n], n_scen, extra) for n in names]
    out: dict = {}
    try:
        with cf.ProcessPoolExecutor(max_workers=min(workers, len(names)), mp_context=mp.get_context("spawn")) as ex:
            for name, res in ex.map(_run_candidate_seeded, jobs):
                out[name] = res
    except Exception as exc:  # noqa: BLE001  pickling or pool failure: the sequential path is always available
        # fall back to sequential with the same child seeds so the answer is
        # the same as a healthy parallel run would have given
        import logging
        logging.getLogger("harvestmind.gate").warning("parallel gate unavailable (%s); solving sequentially", type(exc).__name__)
        out = {n: run_candidate(n, inner, warehouse_cap, np.random.default_rng(seeds[n]), n_scen, extra) for n in names}
    return out

def safe_select(fi: FoldInputs, warehouse_cap, rng, cfg: SafeSelectionConfig | None = None,
                candidates: tuple = ("order_up_to", "deterministic_sp", "stochastic_sp"),
                extra_candidates: dict | None = None, posture: Any = None) -> SafeDecision:
    """``posture`` (adaptive.controller.Posture) makes the gate state-
    dependent: the improvement threshold and confidence come from the
    posture, the candidate set is the posture's admitted set intersected
    with what the caller offers, and the decision records the posture."""
    cfg = cfg or SafeSelectionConfig()
    posture_meta: dict = {}
    if posture is not None:
        cfg = replace(cfg, min_rel_improvement=float(posture.min_rel_improvement),
                      confidence=float(posture.confidence))
        admitted = set(posture.candidates)
        candidates = tuple(c for c in candidates if c in admitted)
        extra_candidates = {k: v for k, v in (extra_candidates or {}).items() if k in admitted}
        posture_meta = {"posture": posture.as_dict(), "candidates_admitted": sorted(admitted)}
    if fi.incumbent is None:
        fi.incumbent = configured_incumbent(cover_weeks=max(fi.lead_of.values()) + 1 if fi.lead_of else 2.0)
        inc_note = "no incumbent supplied; a lead+1 order-up-to stands in and is labelled so"
    else:
        inc_note = None
    label = fi.incumbent.label if isinstance(fi.incumbent, IncumbentPolicy) else "incumbent"  # type: ignore[union-attr]
    n_hist = min(len(v) for v in fi.train_demand.values()) if fi.train_demand else 0
    warnings = [w for w in [inc_note] if w]

    def decide_incumbent(reason, evidence=None):
        sched, _ = run_candidate(INCUMBENT, fi, warehouse_cap, rng, cfg.n_scen)
        return SafeDecision(mode_run=INCUMBENT, schedule=sched, reason=reason, incumbent_label=label,
                            evidence=evidence or {}, gates_config=cfg.__dict__.copy(),
                            history_periods=n_hist, warnings=warnings, meta=dict(posture_meta))

    if n_hist < cfg.min_history:
        return decide_incumbent(f"insufficient history ({n_hist} < {cfg.min_history} periods); "
                                "no candidate can be evidenced, incumbent retained")

    # ── state-evidence selection ──────────────────────────────────────────
    # When a large share of value has just had a demand level shift, every
    # backtest fold predates the shift and cannot evidence a response to it;
    # the gate would retain an incumbent that is now under-ordering. The
    # state itself is the evidence here: run the state-conditioned candidate
    # with a HARD regret budget relative to the incumbent under the
    # conditioned scenarios, and accept it only if that budget held.
    if (cfg.allow_state_evidence and posture is not None and "adaptive_sp" in (extra_candidates or {})
            and float(getattr(posture, "demand_severity", 0.0)) >= 0.5
            and float(getattr(posture, "demand_shift_fresh_share", 0.0)) >= 0.3):
        sched, m = run_candidate("adaptive_sp", fi, warehouse_cap, rng, cfg.n_scen, extra_candidates)
        share = float(getattr(posture, "demand_shift_fresh_share", 0.0))
        if sched is not None and _usable_candidate(sched, m):
            return SafeDecision(
                mode_run="adaptive_sp", schedule=sched,
                reason=(f"state-evidence selection: a demand level shift within the last 12 periods covers "
                        f"{share:.0%} of value, so backtest folds predate it and cannot evidence a response; "
                        f"the state-conditioned candidate ran with a hard regret budget of "
                        f"{posture.regret_budget_share:.0%} of incumbent expected cost, which held"),
                incumbent_label=label, evidence={}, gates_config=cfg.__dict__.copy(), history_periods=n_hist,
                warnings=warnings + ["selection based on the estimated state, not on backtest folds"],
                meta={**m, **posture_meta, "selection_basis": "state"})
        warnings.append("state-evidence selection attempted but the regret budget did not hold; "
                        "falling through to the backtest gate")
    sel_folds = inner_folds(fi, cfg.n_folds, cfg.holdout, offset=cfg.n_holdout_folds * cfg.holdout)
    hold_folds = inner_folds(fi, cfg.n_holdout_folds, cfg.holdout, offset=0)
    if len(sel_folds) < cfg.n_folds or len(hold_folds) < cfg.n_holdout_folds:
        return decide_incumbent(f"only {len(sel_folds)} usable inner fold(s); incumbent retained")
    if not candidates and not extra_candidates:
        return decide_incumbent("the current posture admits no candidate beyond the incumbent")

    workers = _gate_workers()

    def evaluate(folds, names):
        base_costs, base_fill, base_inv = [], [], []
        per = {n: {"delta": [], "svc": [], "inv": [], "usable": 0, "fallback": 0} for n in names}
        for inner, truth, meta in folds:
            inc_sched, _ = run_candidate(INCUMBENT, inner, warehouse_cap, rng, cfg.n_scen)
            b = settle(inc_sched, inner, truth, warehouse_cap)
            base_costs.append(b.total)
            base_fill.append(b.fill_rate)
            base_inv.append(b.inventory_periods)
            results = _run_candidates(names, inner, warehouse_cap, rng, cfg.n_scen, extra_candidates, workers)
            for n in names:
                sched, m = results[n]
                if not _usable_candidate(sched, m):
                    per[n]["fallback"] += 1
                    continue
                per[n]["usable"] += 1
                c = settle(sched, inner, truth, warehouse_cap)
                per[n]["delta"].append((b.total - c.total) / b.total if b.total > 0 else 0.0)
                per[n]["svc"].append(c.fill_rate - b.fill_rate)
                per[n]["inv"].append(c.inventory_periods - b.inventory_periods)
        return per

    per = evaluate(sel_folds, list(candidates) + list((extra_candidates or {}).keys()))
    evidence: dict = {}
    passing = []
    for n, d in per.items():
        ev = CandidateEvidence(name=n, n_folds=len(d["delta"]), deltas_rel=d["delta"], service_diff=d["svc"],
                               inventory_diff=d["inv"], solves_usable=d["usable"], fallbacks=d["fallback"])
        ev.stats = _stats(d["delta"], cfg, rng)
        if ev.stats:
            svc_min = min(d["svc"]) if d["svc"] else 0.0
            ev.gates = {
                "enough_folds": ev.n_folds == len(sel_folds),
                "lower_bound_exceeds_threshold": ev.stats["lower_bound"] > cfg.min_rel_improvement,
                "service_non_inferior": svc_min >= -cfg.service_tolerance,
                "downside_within_budget": ev.stats["downside_regret"] <= cfg.max_regret_share,
                "no_fallbacks": ev.fallbacks == 0,
            }
            ev.passed = all(ev.gates.values())
        evidence[n] = ev
        if ev.passed:
            passing.append(n)

    if not passing:
        return decide_incumbent("No candidate cleared the conservative improvement threshold; "
                                "incumbent retained", evidence)

    # Prefer the simpler policy when within the tie margin of the best lower bound.
    best_lb = max(evidence[n].stats["lower_bound"] for n in passing)
    tied = [n for n in passing if evidence[n].stats["lower_bound"] >= best_lb - cfg.prefer_simpler_within]
    winner = min(tied, key=lambda n: COMPLEXITY.get(n, 9))

    # Nested re-check on folds the winner was not chosen on (winner's curse).
    if hold_folds:
        hold = evaluate(hold_folds, [winner])
        hd = hold[winner]["delta"]
        evidence[winner].holdout_delta_rel = float(np.mean(hd)) if hd else None
        hs = _stats(hd, cfg, rng)
        evidence[winner].holdout_stats = hs
        hg = {
            "complete": len(hd) == len(hold_folds),
            "no_fallbacks": hold[winner]["fallback"] == 0,
            "lower_bound_exceeds_threshold": bool(hs) and hs["lower_bound"] > cfg.min_rel_improvement,
            "service_non_inferior": bool(hold[winner]["svc"]) and min(hold[winner]["svc"]) >= -cfg.service_tolerance,
            "downside_within_budget": bool(hs) and hs["downside_regret"] <= cfg.max_regret_share,
        }
        evidence[winner].holdout_gates = hg
        if not all(hg.values()):
            return decide_incumbent(f"{winner} won the selection folds but did not beat the incumbent "
                                    f"on {len(hd)} held-out fold(s) (mean {evidence[winner].holdout_delta_rel}); "
                                    "incumbent retained", evidence)

    sched, meta = run_candidate(winner, fi, warehouse_cap, rng, cfg.n_scen, extra_candidates)
    if sched is None or not _usable_candidate(sched, meta):
        return decide_incumbent(f"{winner} was selected but its live solve was unusable ({meta.get('status')}); "
                                "incumbent retained", evidence)
    lb = evidence[winner].stats["lower_bound"]
    return SafeDecision(mode_run=winner, schedule=sched,
                        reason=f"{winner} clears the gate: conservative lower bound {lb:+.1%} of incumbent cost "
                               f"over {evidence[winner].n_folds} folds, service non-inferior, downside within budget, "
                               f"confirmed on held-out folds",
                        incumbent_label=label, evidence=evidence, gates_config=cfg.__dict__.copy(),
                        history_periods=n_hist, warnings=warnings, meta={**meta, **posture_meta})


def _usable_candidate(schedule, meta: dict) -> bool:
    """An empty valid schedule means order nothing; it is not solve failure."""
    return (schedule is not None and meta.get("usable", True)
            and meta.get("status", "heuristic") in ("optimal", "feasible", "heuristic")
            and not any(meta.get(k) for k in ("floor_relaxed", "budget_relaxed", "trust_region_relaxed"))
            and all(math.isfinite(float(q)) and q >= 0 for q in schedule.values()))
