"""Statistical validation of the per-period stratified sampler against iid draws of the same fitted
distribution (P1 final closure, step D). Writes docs/zaad_full/evidence/p1/closure/sampler_validation.json."""
from __future__ import annotations
import json, sys
import numpy as np
sys.path.insert(0, "scripts")
from zaad.full.worlds import draw, forecast_all
from zaad.full.fixtures_p1 import p1_request

def stats(paths: np.ndarray, label: str, ref_q: dict | None = None) -> dict:
    flat = paths.reshape(-1)
    q = {k: float(np.quantile(flat, p)) for k, p in (("q50", .5), ("q79", .79), ("q90", .9), ("q95", .95), ("q99", .99))}
    # lag-1 autocorrelation within each world path, averaged
    lags = []
    for p in paths:
        if p.std() > 0:
            lags.append(float(np.corrcoef(p[:-1], p[1:])[0, 1]))
    out = {"label": label, "mean": float(flat.mean()), "sd": float(flat.std()), **q, "lag1_autocorr": float(np.mean(lags)) if lags else 0.}
    if ref_q:
        tail = flat > ref_q["q95"]
        out["tail_frequency_above_ref_q95"] = float(tail.mean())
        # per-world tail runs: consecutive periods above the reference q95
        runs = []
        for p in paths:
            r = 0
            for x in p:
                if x > ref_q["q95"]:
                    r += 1
                else:
                    if r: runs.append(r)
                    r = 0
            if r: runs.append(r)
        out["tail_run_max"] = max(runs) if runs else 0
        out["tail_run_mean"] = float(np.mean(runs)) if runs else 0.
        out["tail_runs_ge3_per_world"] = sum(1 for r in runs if r >= 3) / max(1, len(paths))
        # per-period coverage: share of periods in which at least one of the S worlds is above the ref q79
        S = 3
        by_seed = paths.reshape(-1, S, paths.shape[1])
        out["periods_with_a_world_above_ref_q79"] = float((by_seed.max(axis=1) > ref_q["q79"]).mean())
        out["periods_with_a_world_above_ref_q90"] = float((by_seed.max(axis=1) > ref_q["q90"]).mean())
    return out

def main():
    req = p1_request()
    sid = req.services[0].id
    seeds = range(1000, 1400)      # 400 seeds x 3 worlds x 12 periods = 14,400 period-draws per sampler
    iid = np.array([w.demand[sid] for s in seeds for w in draw(req.model_copy(update={"stratified_scenarios": False}), s, 3)])
    lhs = np.array([w.demand[sid] for s in seeds for w in draw(req.model_copy(update={"stratified_scenarios": True}), s, 3)])
    fitted = np.array([w.demand[sid] for s in range(5000, 6000) for w in draw(req.model_copy(update={"stratified_scenarios": False}), s, 1)])
    ref = stats(fitted, "fitted (1,000 single-world truth-style draws)")
    rows = [ref, stats(iid, "iid 3-world draws", ref), stats(lhs, "per-period LHS 3-world draws", ref)]
    # stream preservation
    same = all(a.fills == b.fills and a.arrival == b.arrival and a.po_due == b.po_due
               for s in range(1000, 1050) for a, b in zip(draw(req.model_copy(update={"stratified_scenarios": False}), s, 3), draw(req, s, 3)))
    truth_same = all(draw(req, s + 10000, 1)[0].demand == draw(req.model_copy(update={"stratified_scenarios": False}), s + 10000, 1)[0].demand for s in range(1000, 1050))
    weights = sorted({round(w.weight, 6) for w in draw(req, 7, 3)})
    out = {"rows": rows, "supply_streams_identical_50_seeds": same, "truth_paths_identical_50_seeds": truth_same, "weights": weights}
    json.dump(out, open("docs/zaad_full/evidence/p1/closure/sampler_validation.json", "w"), indent=1)
    for r in rows:
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()})
    print("supply identical:", same, "truth identical:", truth_same, "weights:", weights)

if __name__ == "__main__":
    main()
