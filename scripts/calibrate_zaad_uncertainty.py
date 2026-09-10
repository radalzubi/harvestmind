#!/usr/bin/env python3
"""History-versus-realized calibration of the uncertainty pipeline, forecast only (no solves).

For every development4 / validation4 cell and review, fit the demand model on the history
available at that review and compare its predicted spread with the realized next-period
demand; do the same for declared supply parameters against realized fills and lead times,
and for the scenario generator's occurrence rate and positive sizes on intermittent cells.

Demand: coverage of central 80% and 95% intervals built from the effective spread, PIT
histogram, absolute error by predicted-spread bucket, ratio of realized RMSE to predicted
spread, level-error contribution, and the same for the protection profile's total spread.
Supply: declared fill mean/sd and lead sd against realized; late-probability calibration.
Intermittent: realized zero share against the model's zero probability, realized positive
size quantiles against the bootstrap's.

    python scripts/calibrate_zaad_uncertainty.py --split development4 --output out.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_zaad_full_benchmark import SEEDS, cells, request_for, truth_for  # noqa: E402
from zaad.full.forecast import estimate, sample  # noqa: E402
from zaad.full.uncertainty import demand_uncertainty  # noqa: E402


def demand_calibration(cell: dict, seed: int, decay: bool) -> list[dict]:
    req = request_for(cell, seed)
    truth = truth_for(req, cell, seed)
    history = np.asarray([r.quantity for r in sorted(req.history, key=lambda r: r.period)])
    service = req.services[0]
    shortage = service.selling_price + service.sla_per_unmet
    holding = req.locations[0].holding_per_value_period * req.skus[0].asset_value
    out = []
    realized = list(truth.demand[service.id])
    for t in range(len(realized)):
        y = np.concatenate([history, realized[:t]])
        fit = estimate(y, shortage, holding, True, "symmetric")
        unc = demand_uncertainty(fit, y, decay)
        mean = fit["mean"]
        # Effective one-period predictive spread as the world generator uses it: sampled sizes
        # scaled by the calibration ratio plus a level error.
        rng = np.random.default_rng(seed + 1000 + t)
        fit_local = dict(fit)
        fit_local["uncertainty"] = unc
        draws = np.array([sample(fit_local, rng, 1)[0] for _ in range(400)])
        ratio = max(1., unc["calibration_ratio"])
        draws = np.maximum(0., mean + (draws - mean) * ratio)
        level = rng.normal(0., unc["level_se"], size=draws.shape)
        draws = np.maximum(0., draws + level)
        actual = realized[t]
        lo80, hi80 = np.quantile(draws, [.1, .9])
        lo95, hi95 = np.quantile(draws, [.025, .975])
        pit = float(np.mean(draws <= actual))
        out.append({"cell": cell["cell"], "seed": seed, "review": t, "demand": cell["demand"], "actual": actual, "mean": mean,
                    "sd_fitted": unc["sd_fitted"], "sd_effective": unc["sd_effective"], "level_se": unc["level_se"],
                    "calibration_ratio": unc["calibration_ratio"], "regime_age": unc.get("regime_age"),
                    "predicted_sd": float(np.std(draws)), "abs_error": abs(actual - mean),
                    "in80": bool(lo80 <= actual <= hi80), "in95": bool(lo95 <= actual <= hi95), "pit": pit,
                    "zero_probability": fit["zero_probability"], "actual_zero": actual == 0,
                    "positive_q90_model": float(np.quantile(draws[draws > 0], .9)) if np.any(draws > 0) else None})
    return out


def supply_calibration(cell: dict, seed: int) -> list[dict]:
    req = request_for(cell, seed)
    truth = truth_for(req, cell, seed)
    out = []
    for source in req.sources:
        for t in range(req.horizon):
            declared_lead = source.lead_days / req.period_days
            realized_lead = truth.arrival[source.id, t] - t
            out.append({"cell": cell["cell"], "seed": seed, "source": source.id, "period": t, "supply": cell["supply"],
                        "declared_fill_mean": source.fill_mean, "declared_fill_sd": source.fill_sd, "realized_fill": truth.fills[source.id, t],
                        "declared_lead_periods": declared_lead, "declared_lead_sd_periods": source.lead_sd_days / req.period_days,
                        "realized_lead_periods": realized_lead,
                        "late": realized_lead > declared_lead + .5,
                        "declared_late_probability": float(1 - norm.cdf((req.period_days / 2) / source.lead_sd_days)) if source.lead_sd_days > 0 else 0.})
    return out


def bucket(values, key, edges):
    result = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        rows = [v for v in values if lo <= v[key] < hi]
        if rows:
            result[f"[{lo},{hi})"] = {"n": len(rows), "mean_abs_error": float(np.mean([r["abs_error"] for r in rows])),
                                      "mean_predicted_sd": float(np.mean([r["predicted_sd"] for r in rows])),
                                      "coverage80": float(np.mean([r["in80"] for r in rows])), "coverage95": float(np.mean([r["in95"] for r in rows]))}
    return result


def summarize(demand_rows, supply_rows) -> dict:
    report: dict = {"demand": {}, "supply": {}, "intermittent": {}}
    for pattern in sorted({r["demand"] for r in demand_rows}):
        rows = [r for r in demand_rows if r["demand"] == pattern]
        rmse = float(np.sqrt(np.mean([(r["actual"] - r["mean"]) ** 2 for r in rows])))
        report["demand"][pattern] = {"n": len(rows), "coverage80": float(np.mean([r["in80"] for r in rows])), "coverage95": float(np.mean([r["in95"] for r in rows])),
                                     "realized_rmse": rmse, "mean_predicted_sd": float(np.mean([r["predicted_sd"] for r in rows])),
                                     "rmse_over_predicted_sd": rmse / max(1e-9, float(np.mean([r["predicted_sd"] for r in rows]))),
                                     "mean_sd_fitted": float(np.mean([r["sd_fitted"] for r in rows])), "mean_sd_effective": float(np.mean([r["sd_effective"] for r in rows])),
                                     "mean_level_se": float(np.mean([r["level_se"] for r in rows])), "mean_calibration_ratio": float(np.mean([r["calibration_ratio"] for r in rows])),
                                     "pit_histogram": np.histogram([r["pit"] for r in rows], bins=5, range=(0, 1))[0].tolist(),
                                     "by_predicted_sd": bucket(rows, "predicted_sd", [0, 3, 5, 8, 12, 1e9])}
    all_rows = demand_rows
    report["demand"]["ALL"] = {"n": len(all_rows), "coverage80": float(np.mean([r["in80"] for r in all_rows])), "coverage95": float(np.mean([r["in95"] for r in all_rows])),
                               "rmse_over_predicted_sd": float(np.sqrt(np.mean([(r["actual"] - r["mean"]) ** 2 for r in all_rows])) / max(1e-9, np.mean([r["predicted_sd"] for r in all_rows]))),
                               "by_predicted_sd": bucket(all_rows, "predicted_sd", [0, 3, 5, 8, 12, 1e9])}
    for pattern in sorted({r["supply"] for r in supply_rows}):
        rows = [r for r in supply_rows if r["supply"] == pattern and r["source"] == "main"]
        report["supply"][pattern] = {"n": len(rows), "declared_fill_mean": float(np.mean([r["declared_fill_mean"] for r in rows])),
                                     "realized_fill_mean": float(np.mean([r["realized_fill"] for r in rows])), "realized_fill_sd": float(np.std([r["realized_fill"] for r in rows])),
                                     "declared_fill_sd": float(np.mean([r["declared_fill_sd"] for r in rows])),
                                     "declared_late_probability": float(np.mean([r["declared_late_probability"] for r in rows])),
                                     "realized_late_share": float(np.mean([r["late"] for r in rows])),
                                     "realized_lead_p50": float(np.median([r["realized_lead_periods"] for r in rows])),
                                     "realized_lead_p90": float(np.quantile([r["realized_lead_periods"] for r in rows], .9)),
                                     "declared_lead": float(np.mean([r["declared_lead_periods"] for r in rows]))}
    inter = [r for r in demand_rows if r["demand"].startswith("intermittent")]
    if inter:
        report["intermittent"] = {"n": len(inter), "model_zero_probability": float(np.mean([r["zero_probability"] for r in inter])),
                                  "realized_zero_share": float(np.mean([r["actual_zero"] for r in inter])),
                                  "realized_positive_q90": float(np.quantile([r["actual"] for r in inter if r["actual"] > 0], .9)),
                                  "model_positive_q90": float(np.mean([r["positive_q90_model"] for r in inter if r["positive_q90_model"] is not None])),
                                  "coverage80": float(np.mean([r["in80"] for r in inter])), "coverage95": float(np.mean([r["in95"] for r in inter]))}
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["development4", "validation4"], default="development4")
    parser.add_argument("--decay", action="store_true", help="use protection_decay uncertainty (PR31 rules); default PR30")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    demand_rows, supply_rows = [], []
    for cell in cells("v4"):
        for seed in SEEDS[args.split]:
            demand_rows += demand_calibration(cell, seed, args.decay)
            supply_rows += supply_calibration(cell, seed)
    report = summarize(demand_rows, supply_rows)
    report["split"] = args.split
    report["decay"] = args.decay
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True))
    for pattern, r in report["demand"].items():
        print(f"{pattern:20s} n={r['n']:4d} cov80 {r['coverage80']:.2f} cov95 {r['coverage95']:.2f} rmse/pred_sd {r['rmse_over_predicted_sd']:.2f}"
              + (f" sd_fit {r['mean_sd_fitted']:.1f} sd_eff {r['mean_sd_effective']:.1f} level_se {r['mean_level_se']:.1f} ratio {r['mean_calibration_ratio']:.2f}" if "mean_sd_fitted" in r else ""))
    for pattern, r in report["supply"].items():
        print(f"supply {pattern:22s} fill decl {r['declared_fill_mean']:.2f}±{r['declared_fill_sd']:.2f} real {r['realized_fill_mean']:.2f}±{r['realized_fill_sd']:.2f} | late decl {r['declared_late_probability']:.2f} real {r['realized_late_share']:.2f} | lead decl {r['declared_lead']:.1f} real p50 {r['realized_lead_p50']:.1f} p90 {r['realized_lead_p90']:.1f}")
    print("intermittent", report["intermittent"])


if __name__ == "__main__":
    main()
