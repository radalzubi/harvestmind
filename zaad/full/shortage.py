"""Analytic expected shortage from the fitted predictive demand distribution (P1 final closure).

ZAAD samples demand from a bootstrap mixture: a zero with probability z0, otherwise one of the
historical sizes scaled so the unconditional mean is the fitted mean, deviations widened by the
calibration ratio and capped at the outlier bound exactly as `worlds.draw` does. That mixture is
discrete, so its loss function L(a) = E[(D - a)^+] is piecewise linear with breakpoints at the
atoms and can be represented exactly by one tangent cut per distinct atom. Nothing here is
sampled, tuned or scaled: the atoms are the fitted history, the probabilities are the fitted
zero probability, and the penalty that prices the loss is the declared shortage economics.

The level uncertainty of the fit (the multiplicative level shock draw() applies per world) and
firm order lines are not folded into the atoms; that omission understates the tail slightly and
is stated in the close-out rather than compensated for."""
from __future__ import annotations

import numpy as np

from zaad.full.uncertainty import OUTLIER_Z


def demand_atoms(fit: dict, multiplier: float = 1.) -> tuple[np.ndarray, float]:
    """(sorted atoms of the positive-demand branch, zero probability) for one period, after the
    same calibration widening and outlier cap the sampler applies, times the period multiplier."""
    sizes = np.asarray(fit.get("sizes", ()), dtype=float)
    if not len(sizes) or fit["mean"] <= 0:
        return np.zeros(0), 1.
    zero = float(fit["zero_probability"])
    occurrence = 1. - zero
    atoms = sizes * fit["mean"] / (occurrence * sizes.mean())
    u = fit.get("uncertainty") or {}
    ratio = max(1., float(u.get("calibration_ratio", 1.)))
    if ratio > 1.:
        atoms = np.maximum(0., fit["mean"] + (atoms - fit["mean"]) * ratio)
    if u.get("outliers", 0) and not u.get("intermittent"):
        atoms = np.minimum(atoms, fit["mean"] + OUTLIER_Z * max(float(u.get("residual_sd", 1.)), 1.) * ratio)
    return np.sort(atoms * multiplier), zero


def expected_shortage(atoms: np.ndarray, zero: float, available: float) -> float:
    """E[(D - available)^+] under the mixture; exact."""
    if not len(atoms):
        return 0.
    available = max(0., float(available))
    return float((1. - zero) * np.mean(np.maximum(atoms - available, 0.)))


def tail_probability(atoms: np.ndarray, zero: float, available: float) -> float:
    """P(D > available) under the mixture; exact. The negative slope of the loss function."""
    if not len(atoms):
        return 0.
    return float((1. - zero) * np.mean(atoms > max(0., float(available))))


def loss_cuts(atoms: np.ndarray, zero: float) -> list[tuple[float, float, float]]:
    """Tangent cuts (a_k, L(a_k), -P(D > a_k)) at 0 and at every distinct atom. Because the loss
    is piecewise linear with breakpoints exactly at the atoms, max over these cuts equals L(a)
    for every a >= 0: the representation is exact, not an approximation."""
    if not len(atoms):
        return []
    points = [0.] + sorted({float(x) for x in atoms})
    return [(a, expected_shortage(atoms, zero, a), -tail_probability(atoms, zero, a)) for a in points]


def loss_envelope(cuts: list[tuple[float, float, float]], available: float) -> float:
    """max over the cuts, the value the model's epigraph variable takes."""
    if not cuts:
        return 0.
    return max(0., max(intercept + slope * (available - a) for a, intercept, slope in cuts))
