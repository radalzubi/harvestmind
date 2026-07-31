"""Temperature and shelf life: Q10 and Arrhenius kinetics.

Weather does not stop mattering at the farm gate. Deterioration rate in
fresh produce is governed by temperature, so a hot week shortens the usable
window of inventory already in the building. That is a second, independent
channel from weather to commitment risk, and it is the one an operator can
actually feel within days rather than seasons.

Q10 MODEL
---------
Q10 is the factor by which reaction rate multiplies per 10 C rise:

    Q10 = (R2 / R1) ^ (10 / (T2 - T1))
    rate(T) = rate(T_ref) * Q10 ^ ((T - T_ref) / 10)
    shelf_life(T) = shelf_life(T_ref) / Q10 ^ ((T - T_ref) / 10)

UF/IFAS EDIS HS1270 (doi:10.32473/edis-hs1270-2015) states it plainly: at
Q10 of 2.0-2.5, every 10 C rise shortens shelf life by 50-60%.

Q10 values below were computed from the respiration rates tabulated in
USDA Agriculture Handbook 66 (Gross, Wang & Saltveit, eds., "The Commercial
Storage of Fruits, Vegetables, and Florist and Nursery Stocks"), which
reports mg CO2/kg/h at 0, 10 and 20 C. Q10 is NOT constant across the
range — it is consistently higher near 0 C than near 20 C, so a single
value applied over a wide range will misestimate. Both sub-ranges are kept.

ARRHENIUS MODEL
---------------
    k = k0 * exp(-Ea / (R T))          T in kelvin
    t2 / t1 = exp[ (Ea/R) (1/T1 - 1/T2) ]

Labuza, T.P. (1984). "Application of chemical kinetics to deterioration of
foods." J. Chem. Educ. 61(4):348-358. doi:10.1021/ed061p348

CAVEAT, stated because misapplying it is easy: most published activation
energies for food quality loss come from THERMAL PROCESSING studies at
60-100 C, not 0-25 C cold-chain conditions. Q10 fitted to actual
refrigerated respiration data is the more defensible choice in this
temperature range, and is what the shelf-life functions here default to.

COLD-CHAIN EVIDENCE
-------------------
Thole, V., Vain, P. & Martin, C. (2021). "Effect of Elevated Temperature on
    Tomato Post-Harvest Properties." Plants 10(11):2359.
    doi:10.3390/plants10112359 — a rise from 18-20 C to 26 C cost about 11%
    of shelf life (~4 days), doubled weight loss (2.5% to 5.1%) and
    increased fungal lesion size ~11%.
Managa, M.G. et al. (2018). "Impact of transportation, storage, and retail
    shelf conditions on lettuce quality and phytonutrients losses in the
    supply chain." Food Science & Nutrition 6(6):1527-1536.
    doi:10.1002/fsn3.685 — retail abuse at 21-24 C drove vitamin C losses up
    to 81% and chlorophyll loss of 67%.
"""

from __future__ import annotations

import numpy as np

GAS_CONSTANT_J = 8.314462618          # J / (mol K)

# Q10 by commodity and temperature range, computed from the respiration
# rates in USDA Handbook 66. `shelf_life_days_ref` is at `t_ref_c`.
COMMODITY_KINETICS: dict[str, dict] = {
    "lettuce": {
        "q10_0_10c": 2.65, "q10_10_20c": 1.82,
        "t_ref_c": 0.0, "shelf_life_days_ref": 21.0,
        "optimal_storage_c": 0.0,
        "ref": "USDA Handbook 66; 2-4 weeks at 0 C",
    },
    "strawberry": {
        "q10_0_10c": 4.70, "q10_10_20c": 2.00,
        "t_ref_c": 0.0, "shelf_life_days_ref": 7.0,
        "optimal_storage_c": 0.0,
        "ref": "USDA Handbook 66; 5-7 days at 0 C",
    },
    "tomato": {
        # Handbook 66 reports tomato respiration at 10 and 20 C only.
        "q10_0_10c": 2.40, "q10_10_20c": 2.40,
        "t_ref_c": 13.0, "shelf_life_days_ref": 10.0,
        # Chilling-sensitive: do NOT store near 0 C.
        "optimal_storage_c": 13.0, "chilling_sensitive": True,
        "ref": "USDA Handbook 66; 7-21 C by ripeness stage",
    },
}

# Generic fallback when the commodity is unknown. The 2.0-2.5 band is the
# broadly supported range for fresh produce over 5-25 C (UF/IFAS HS1270).
DEFAULT_Q10 = 2.2


def q10_for(
    commodity: str, temp_c: float, ref_temp_c: float | None = None,
) -> float:
    """Q10 appropriate to the temperature SPAN being crossed.

    Q10 is not constant with temperature — for produce it is consistently
    higher near 0 C than near 20 C (visible directly in the Handbook 66
    respiration tables). Selecting on the target temperature alone is
    therefore wrong when the span crosses ranges: going 0 C -> 10 C is a
    0-10 C transition and must use the cold-range Q10, not the warm one.
    When ref_temp_c is supplied the span MIDPOINT selects the value.
    """
    spec = COMMODITY_KINETICS.get(commodity)
    if spec is None:
        return DEFAULT_Q10
    probe = temp_c if ref_temp_c is None else (temp_c + ref_temp_c) / 2.0
    return spec["q10_0_10c"] if probe < 10.0 else spec["q10_10_20c"]


def rate_multiplier(temp_c: float, ref_temp_c: float, q10: float) -> float:
    """Deterioration-rate multiplier between two temperatures, single Q10."""
    return float(q10 ** ((temp_c - ref_temp_c) / 10.0))


# Boundary between the two tabulated Q10 ranges (Handbook 66 reports
# respiration at 0, 10 and 20 C).
_Q10_RANGE_BOUNDARY_C = 10.0


def rate_multiplier_piecewise(
    temp_c: float, ref_temp_c: float, commodity: str,
) -> float:
    """Rate multiplier composed across Q10 ranges.

    Q10 is not constant with temperature, so a span crossing 10 C must use
    BOTH tabulated values, not one of them. Rates compose multiplicatively
    along the path, so the span is split at the boundary and each segment
    contributes its own Q10:

        R(T) / R(Tref) = prod_segments Q10_seg ^ (dT_seg / 10)

    Selecting a single Q10 for a crossing span is not merely imprecise, it
    is non-monotonic: with lettuce's 2.65 (cold) and 1.82 (warm), picking
    the warm value for a 0 -> 20 C span yields a LONGER predicted shelf
    life than for 0 -> 15 C, which is physically impossible.
    """
    spec = COMMODITY_KINETICS.get(commodity)
    if spec is None:
        return rate_multiplier(temp_c, ref_temp_c, DEFAULT_Q10)

    lo, hi = sorted((float(ref_temp_c), float(temp_c)))
    b = _Q10_RANGE_BOUNDARY_C
    cold_span = max(0.0, min(hi, b) - min(lo, b))
    warm_span = max(0.0, max(hi, b) - max(lo, b))

    mult = (spec["q10_0_10c"] ** (cold_span / 10.0)
            * spec["q10_10_20c"] ** (warm_span / 10.0))
    # Direction: warming raises the rate, cooling lowers it.
    return float(mult if temp_c >= ref_temp_c else 1.0 / mult)


def shelf_life_at(
    temp_c: float,
    commodity: str = "lettuce",
    shelf_life_days_ref: float | None = None,
    ref_temp_c: float | None = None,
) -> dict[str, float | str | bool]:
    """Shelf life at a given holding temperature.

    Shelf life is inversely proportional to deterioration rate, so
        L(T) = L_ref / Q10 ^ ((T - T_ref) / 10).
    """
    spec = COMMODITY_KINETICS.get(commodity, {})
    t_ref = ref_temp_c if ref_temp_c is not None else spec.get("t_ref_c", 0.0)
    l_ref = (shelf_life_days_ref if shelf_life_days_ref is not None
             else spec.get("shelf_life_days_ref", 14.0))
    q10 = q10_for(commodity, temp_c, t_ref)

    mult = rate_multiplier_piecewise(temp_c, t_ref, commodity)
    life = l_ref / mult if mult > 0 else l_ref

    out: dict[str, float | str | bool] = {
        "commodity": commodity,
        "temp_c": float(temp_c),
        "q10_used": float(q10),
        "reference_temp_c": float(t_ref),
        "reference_shelf_life_days": float(l_ref),
        "rate_multiplier": round(float(mult), 4),
        "shelf_life_days": round(float(life), 2),
        "shelf_life_lost_days": round(float(l_ref - life), 2),
        "shelf_life_lost_pct": round(float((1.0 - life / l_ref) * 100.0), 1)
        if l_ref > 0 else 0.0,
    }
    if spec.get("chilling_sensitive") and temp_c < spec.get("optimal_storage_c", 0):
        out["warning"] = (
            "below optimal storage temperature for a chilling-sensitive "
            "commodity; the Q10 model does not capture chilling injury, so "
            "the shelf life above is optimistic"
        )
    return out


def arrhenius_shelf_life_ratio(
    temp_c_1: float, temp_c_2: float, activation_energy_j_mol: float,
) -> float:
    """Shelf-life ratio t2/t1 between two temperatures (Arrhenius).

    Provided for completeness and cross-checking against Q10. Prefer the
    Q10 functions in the refrigerated range — see the module caveat about
    activation energies derived from thermal-processing studies.
    """
    t1 = temp_c_1 + 273.15
    t2 = temp_c_2 + 273.15
    return float(np.exp(
        (activation_energy_j_mol / GAS_CONSTANT_J) * (1.0 / t2 - 1.0 / t1)))


def q10_to_activation_energy(q10: float, temp_c: float = 10.0) -> float:
    """Convert a Q10 to the equivalent activation energy, J/mol.

    Ea = R * T * (T+10) * ln(Q10) / 10, with T in kelvin. The two models
    agree only locally; the equivalence is temperature-dependent, which is
    itself the reason a single Q10 cannot span 0-30 C.
    """
    t = temp_c + 273.15
    return float(GAS_CONSTANT_J * t * (t + 10.0) * np.log(q10) / 10.0)


def heat_exposure_shelf_life_penalty(
    daily_tmax_c: np.ndarray,
    commodity: str = "lettuce",
    controlled_temp_c: float = 4.0,
    exposure_hours_per_day: float = 2.0,
) -> dict[str, float]:
    """Shelf life lost to ambient heat during handling gaps.

    Models the part of the chain that is NOT refrigerated — loading docks,
    staging, last-mile — where product sits near ambient. Each day
    contributes exposure_hours at ambient and the remainder at the
    controlled temperature; the deterioration rates are time-weighted.

    The exposure assumption is a parameter, not a measured quantity: an
    operator with dock-temperature logs should replace it. Stated because
    the output is only as good as that input.
    """
    tmax = np.asarray(daily_tmax_c, dtype=float)
    if tmax.size == 0:
        return {"status": "no_data"}

    spec = COMMODITY_KINETICS.get(commodity, {})
    t_ref = spec.get("t_ref_c", 0.0)

    frac_amb = np.clip(exposure_hours_per_day / 24.0, 0.0, 1.0)
    rate_amb = np.array(
        [rate_multiplier_piecewise(float(t), t_ref, commodity) for t in tmax])
    rate_ctl = rate_multiplier_piecewise(controlled_temp_c, t_ref, commodity)

    effective = frac_amb * rate_amb + (1.0 - frac_amb) * rate_ctl
    baseline = rate_ctl

    return {
        "status": "ok",
        "commodity": commodity,
        "n_days": int(tmax.size),
        "mean_tmax_c": round(float(np.mean(tmax)), 2),
        "exposure_hours_per_day": float(exposure_hours_per_day),
        "mean_rate_multiplier": round(float(np.mean(effective)), 4),
        "baseline_rate_multiplier": round(float(baseline), 4),
        # >1 means product deteriorates faster than a fully cold chain.
        "relative_deterioration": round(
            float(np.mean(effective) / baseline), 4) if baseline > 0 else 1.0,
        "shelf_life_retained_pct": round(
            float(baseline / np.mean(effective) * 100.0), 1)
        if np.mean(effective) > 0 else 100.0,
        "assumption": (
            f"{exposure_hours_per_day:.1f} h/day at ambient, remainder at "
            f"{controlled_temp_c:.1f} C — replace with dock temperature logs "
            "where available"
        ),
    }
