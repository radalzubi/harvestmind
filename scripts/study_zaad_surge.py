#!/usr/bin/env python3
"""Demand-surge response study: how fast each change rule adapts, and how often it panics.

Eight synthetic patterns are replayed observation by observation through zaad.full.forecast
.estimate with each demand_adaptation mode. A pattern is 52 periods of history followed by 12
online periods; the change (if any) starts at online period 0. Per pattern and mode:

    decision_loss     shortage- and holding-weighted one-step error over the online periods,
                      the same loss the forecast tournament uses
    detection_delay   online periods until the segment origin first lands inside the new regime
                      (None when never detected); only meaningful for genuine level changes
    false_alarms      share of runs where the origin moved on a pattern with no persistent change
                      (stable, one-week spike, seasonal, known promotion)
    overshoot         mean forecast excess over the truth in the two periods after a one-week
                      spike or a temporary spike ends: the panic-buying signature

Seeds are split development / validation; the choice of default is made on development and
confirmed on validation. Nothing here touches the frozen benchmark seeds.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zaad.full.forecast import estimate  # noqa: E402

MODES = ["symmetric", "asymmetric", "page_hinkley", "bocpd"]
PATTERNS = ["stable", "spike", "temporary_spike", "level_shift", "gradual", "known_promotion", "unknown_promotion", "launch", "seasonal"]
SEEDS = {"development": list(range(300, 340)), "validation": list(range(400, 440))}
HISTORY, ONLINE = 52, 12
SHORTAGE, HOLDING = 11., .05    # selling price plus SLA per unmet, holding per unit-period


def simulate(pattern: str, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, bool]:
    """Full series, the true mean per online period, and whether a persistent change exists."""
    base = 20.
    history = np.array([max(0., rng.normal(base * (1 + .3 * np.sin(2 * np.pi * t / 26)) if pattern == "seasonal" else base, 2.))
                        for t in range(-HISTORY, 0)])
    truth = np.full(ONLINE, base)
    if pattern == "spike":
        truth[2] = base * 3
    elif pattern == "temporary_spike":
        truth[2:4] = base * 2
    elif pattern == "level_shift":
        truth[:] = base * 1.8
    elif pattern == "gradual":
        truth = base * (1 + .05 * np.arange(1, ONLINE + 1))
    elif pattern in {"known_promotion", "unknown_promotion"}:
        truth[3:6] = base * 1.8
    elif pattern == "launch":
        truth[:] = base * 2.5
    elif pattern == "seasonal":
        truth = base * (1 + .3 * np.sin(2 * np.pi * np.arange(ONLINE) / 26))
    online = np.array([float(rng.poisson(m)) for m in truth])
    persistent = pattern in {"level_shift", "gradual", "launch"}
    return np.concatenate([history, online]), truth, persistent


def run(mode: str, series: np.ndarray, truth: np.ndarray, pattern: str) -> dict:
    losses, origins, forecasts = [], [], []
    for k in range(ONLINE):
        y = series[:HISTORY + k]
        fit = estimate(y, SHORTAGE, HOLDING, True, mode)
        forecast = fit["mean"]
        actual = series[HISTORY + k]
        if pattern == "known_promotion" and 3 <= k <= 5:
            forecast *= 1.8          # the declared event multiplier the planner applies in worlds
        losses.append(SHORTAGE * max(actual - forecast, 0.) + HOLDING * max(forecast - actual, 0.))
        origins.append(fit["segment_origin"])
        forecasts.append(forecast)
    delay = next((k for k, o in enumerate(origins) if o >= HISTORY), None)
    moved = any(o >= HISTORY for o in origins)
    overshoot = None
    if pattern == "spike":
        overshoot = float(np.mean([forecasts[k] - truth[k] for k in (3, 4)]))
    elif pattern == "temporary_spike":
        overshoot = float(np.mean([forecasts[k] - truth[k] for k in (4, 5)]))
    return {"decision_loss": float(np.sum(losses)), "detection_delay": delay, "moved": moved, "overshoot": overshoot,
            "final_forecast": forecasts[-1], "final_truth": float(truth[-1])}


def study(split: str) -> dict:
    report: dict = {"split": split, "seeds": SEEDS[split], "patterns": {}}
    for pattern in PATTERNS:
        cell: dict = {}
        for mode in MODES:
            results = []
            for seed in SEEDS[split]:
                rng = np.random.default_rng(seed)
                series, truth, persistent = simulate(pattern, rng)
                results.append(run(mode, series, truth, pattern))
            delays = [r["detection_delay"] for r in results if r["detection_delay"] is not None]
            cell[mode] = {"mean_decision_loss": float(np.mean([r["decision_loss"] for r in results])),
                          "median_decision_loss": float(np.median([r["decision_loss"] for r in results])),
                          "worst_decision_loss": float(np.max([r["decision_loss"] for r in results])),
                          "detected_share": float(np.mean([r["moved"] for r in results])),
                          "median_detection_delay": float(np.median(delays)) if delays else None,
                          "mean_overshoot": float(np.mean([r["overshoot"] for r in results])) if results[0]["overshoot"] is not None else None,
                          "mean_final_error": float(np.mean([r["final_forecast"] - r["final_truth"] for r in results]))}
        report["patterns"][pattern] = cell
    # Aggregate: total decision loss over all patterns (what the planner pays), plus panic and slowness.
    totals = {}
    for mode in MODES:
        totals[mode] = {"total_mean_decision_loss": float(sum(report["patterns"][p][mode]["mean_decision_loss"] for p in PATTERNS)),
                        "false_alarm_share": float(np.mean([report["patterns"][p][mode]["detected_share"] for p in ("stable", "spike", "seasonal", "known_promotion")])),
                        "persistent_detected_share": float(np.mean([report["patterns"][p][mode]["detected_share"] for p in ("level_shift", "gradual", "launch")])),
                        "median_delay_level_shift": report["patterns"]["level_shift"][mode]["median_detection_delay"],
                        "spike_overshoot": report["patterns"]["spike"][mode]["mean_overshoot"]}
    report["totals"] = totals
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=list(SEEDS), default="development")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evidence")
    report = study(args.split)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1, sort_keys=True))
    for mode, cell in report["totals"].items():
        print(f"{mode:13s} loss {cell['total_mean_decision_loss']:8.1f} false_alarm {cell['false_alarm_share']:.2f} "
              f"persistent_detected {cell['persistent_detected_share']:.2f} delay {cell['median_delay_level_shift']} spike_overshoot {cell['spike_overshoot']}")
    for pattern, cell in report["patterns"].items():
        print(pattern, {m: round(v["mean_decision_loss"], 1) for m, v in cell.items()})


if __name__ == "__main__":
    main()
