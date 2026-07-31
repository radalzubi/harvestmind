"""The probabilistic supply-forecast contract.

Every probabilistic forecast in the system is one of these. The contract
exists so a forecast can be audited after the fact: what was known when it
was issued, which model made it, how confident it was entitled to be, and
whether its intervals had been calibrated or merely asserted.

TWO TIMESTAMPS, NOT ONE
-----------------------
``issued_at`` is when the forecast was produced. ``information_cutoff`` is
the latest data it was allowed to see. They differ whenever a backtest
replays history, and conflating them is how leakage enters a backtest
unnoticed: a forecast "issued" at an old date but silently fitted on the
full dataset scores far too well. Keeping both, and validating that
cutoff <= issued_at, makes the distinction impossible to lose.

QUANTILES MUST NOT CROSS
------------------------
Independently fitted quantile models can cross (predicting a p10 above a
p90), which is not merely untidy: a crossed interval passed to a scenario
generator produces negative-width distributions and nonsense draws.
Validation rejects crossing rather than silently sorting, because sorting
hides a model defect that the operator should be told about. Use
``rearrange`` explicitly when monotonisation is the intended remedy — that
is the Chernozhukov-Fernández-Val-Galichon rearrangement, which is a
principled estimator, not a tidy-up.

WHAT THIS IS A FORECAST *OF*
----------------------------
Deliberately explicit, because these are different quantities and
conflating them overstates what the model knows:

    biological yield     kg per unit area in the field
    harvestable yield    what can actually be picked
    commercial packout   what meets grade after sorting
    supplier delivery    what the supplier actually ships
    available supply     what the optimizer may commit  <-- optimizer input

``quantity_kind`` records which one a given forecast represents.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Any

# The quantile grid the system standardises on.
QUANTILE_LEVELS: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95)


class QuantityKind(str, Enum):
    """Which link in the field-to-dock chain this forecast describes."""

    BIOLOGICAL_YIELD = "biological_yield"
    HARVESTABLE_YIELD = "harvestable_yield"
    COMMERCIAL_PACKOUT = "commercial_packout"
    SUPPLIER_DELIVERY = "supplier_delivery"
    AVAILABLE_SUPPLY = "available_supply"


class DataTier(str, Enum):
    """How much history stands behind a forecast.

    Drives model selection, interval width and the confidence label. A
    sparse group that happened to show low observed variance must NOT be
    given narrow intervals — that is the failure mode this exists to stop.
    """

    NONE = "none"                    # no history: climatology / prior only
    SINGLE_SEASON = "single_season"  # 1 season: pooled prior dominates
    SPARSE = "sparse"                # 2-3 seasons: heavy partial pooling
    ADEQUATE = "adequate"            # 4-7 seasons: group-level fit viable
    RICH = "rich"                    # 8+ seasons: full model justified


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ForecastValidationError(ValueError):
    """A forecast violated the contract. Never silently repaired."""


@dataclass
class ProbabilisticForecast:
    """One probabilistic forecast for one key at one target period."""

    # --- identity -------------------------------------------------------
    forecast_id: str
    issued_at: datetime
    information_cutoff: datetime
    target_start: date
    target_end: date

    # --- what is being forecast ----------------------------------------
    entity_key: dict[str, Any]           # supplier_id / product_id / region ...
    quantity_kind: QuantityKind
    unit: str

    # --- the distribution ----------------------------------------------
    quantiles: dict[float, float]        # level -> value
    mean: float | None = None

    # --- provenance -----------------------------------------------------
    model_family: str = "unknown"
    model_version: str = "0"
    feature_version: str = "0"
    training_cutoff: date | None = None
    random_seed: int | None = None

    # --- honesty --------------------------------------------------------
    data_tier: DataTier = DataTier.NONE
    confidence: Confidence = Confidence.LOW
    calibrated: bool = False
    calibration_method: str | None = None
    calibration_group: str | None = None
    n_observations: int = 0
    fallback_reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    drivers: list[str] = field(default_factory=list)

    # --- optional empirical sample (preferred by scenario generation) ---
    samples: list[float] | None = None

    # -- derived ---------------------------------------------------------
    @property
    def horizon_days(self) -> int:
        return (self.target_start - self.information_cutoff.date()).days

    @property
    def median(self) -> float:
        return self.quantiles[0.50]

    def interval(self, level: float = 0.80) -> tuple[float, float]:
        """Central interval at the requested level, e.g. 0.80 -> p10..p90."""
        tail = (1.0 - level) / 2.0
        lo = min(self.quantiles, key=lambda q: abs(q - tail))
        hi = min(self.quantiles, key=lambda q: abs(q - (1.0 - tail)))
        return self.quantiles[lo], self.quantiles[hi]

    @property
    def relative_width(self) -> float:
        """p10-p90 width as a fraction of the median — a sharpness proxy."""
        lo, hi = self.interval(0.80)
        med = self.median
        return float((hi - lo) / med) if med > 1e-9 else float("inf")

    # -- validation ------------------------------------------------------
    def validate(self) -> None:
        """Enforce every contract invariant. Raises, never repairs."""
        if self.information_cutoff > self.issued_at:
            raise ForecastValidationError(
                f"information_cutoff {self.information_cutoff} is after "
                f"issued_at {self.issued_at}: the forecast claims to have "
                "used data from after it was made")
        if self.target_end < self.target_start:
            raise ForecastValidationError(
                f"target_end {self.target_end} precedes target_start "
                f"{self.target_start}")
        if self.training_cutoff and self.training_cutoff > self.information_cutoff.date():
            raise ForecastValidationError(
                f"training_cutoff {self.training_cutoff} is after the "
                f"information cutoff {self.information_cutoff.date()}")
        if not self.quantiles:
            raise ForecastValidationError("no quantiles supplied")

        levels = sorted(self.quantiles)
        for q in levels:
            v = self.quantiles[q]
            if not math.isfinite(v):
                raise ForecastValidationError(
                    f"quantile q{q} is not finite: {v}")
            if v < 0:
                raise ForecastValidationError(
                    f"quantile q{q} is negative ({v}); supply quantities "
                    "cannot be negative")
        # Monotonicity: crossing is a model defect, surfaced not hidden.
        for lo, hi in zip(levels, levels[1:]):
            if self.quantiles[hi] < self.quantiles[lo] - 1e-9:
                raise ForecastValidationError(
                    f"quantile crossing: q{lo}={self.quantiles[lo]:.4f} > "
                    f"q{hi}={self.quantiles[hi]:.4f}. Fit a monotone model or "
                    "apply rearrange() deliberately — do not sort silently.")
        if self.mean is not None and not math.isfinite(self.mean):
            raise ForecastValidationError(f"mean is not finite: {self.mean}")
        if self.samples is not None:
            if not self.samples:
                raise ForecastValidationError("samples supplied but empty")
            if any((not math.isfinite(s)) or s < 0 for s in self.samples):
                raise ForecastValidationError(
                    "samples contain negative or non-finite values")
        if not self.calibrated and "uncalibrated" not in " ".join(self.warnings):
            self.warnings.append(
                "uncalibrated: intervals are model-asserted, not empirically "
                "validated for coverage")

    def to_dict(self) -> dict:
        """Deterministic serialisation — stable key order, JSON-safe."""
        d = asdict(self)
        d["issued_at"] = self.issued_at.isoformat()
        d["information_cutoff"] = self.information_cutoff.isoformat()
        d["target_start"] = self.target_start.isoformat()
        d["target_end"] = self.target_end.isoformat()
        d["training_cutoff"] = (self.training_cutoff.isoformat()
                                if self.training_cutoff else None)
        d["quantity_kind"] = self.quantity_kind.value
        d["data_tier"] = self.data_tier.value
        d["confidence"] = self.confidence.value
        # Quantile keys as strings, sorted, for stable JSON.
        d["quantiles"] = {f"q{int(round(k * 100)):02d}": round(v, 6)
                          for k, v in sorted(self.quantiles.items())}
        d["horizon_days"] = self.horizon_days
        return {k: d[k] for k in sorted(d)}


def rearrange(quantiles: dict[float, float]) -> dict[float, float]:
    """Monotone rearrangement of a crossed quantile function.

    Chernozhukov, V., Fernández-Val, I. & Galichon, A. (2010), "Quantile
    and probability curves without crossing," *Econometrica* 78(3):
    1093-1125. Sorting the estimated quantile values is not an ad-hoc
    tidy-up: the rearranged curve is a proper quantile function and is
    proven to be no further from the true curve than the original, so the
    operation weakly improves the estimate.

    It is exposed as an explicit, named step so that monotonisation is
    always a deliberate choice recorded in the code, never a silent repair
    inside a constructor.
    """
    levels = sorted(quantiles)
    values = sorted(quantiles[level] for level in levels)
    return dict(zip(levels, values))


def confidence_for_tier(tier: DataTier) -> Confidence:
    """Confidence label implied by data availability alone."""
    if tier in (DataTier.NONE, DataTier.SINGLE_SEASON):
        return Confidence.LOW
    if tier == DataTier.SPARSE:
        return Confidence.MEDIUM
    return Confidence.HIGH
