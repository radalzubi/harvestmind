"""Confront the ASSUMED disruption presets with measured satellite data.

Every preset in ``risk/disruption_scenarios.py`` carries ``assumed=True``
and a source string, because when they were written no measured series
paired a named event to a realized supply shortfall. IMF PortWatch closes
part of that gap: daily AIS port calls and import tonnage, 2019 to 2026,
for the exact ports that serve each of Jordan's import routes, spanning
COVID, the Ever Given, the Red Sea crisis and the Hormuz disruption.

WHAT THIS SCRIPT CAN AND CANNOT SETTLE. It can say whether a preset's
haircut is the right ORDER OF MAGNITUDE against measured arrival
shortfalls, and whether the simulator's disruption FREQUENCY and DURATION
match the real ones. It cannot convert any preset to ``assumed=False``,
because arrivals are not fills: we still never observe what was ordered.
A preset that survives this comparison is a better-founded assumption, not
a measurement, and the flag stays True.
"""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from risk.disruption_scenarios import PRESETS  # noqa: E402
from synthetic.commercial.jordan_distributor_v2 import (  # noqa: E402
    JordanV2Config,
)
from validation.commercial.real_data import (  # noqa: E402
    ROUTE_TO_PORT, load_chokepoint_monthly, port_shock_series,
)

# Dated windows, taken from the events themselves, not fitted to results.
EVENTS: dict[str, tuple[str, str]] = {
    "pre_crisis":   ("2019-01", "2019-12"),
    "covid_peak":   ("2020-03", "2020-08"),
    "ever_given":   ("2021-03", "2021-05"),
    "calm_2022":    ("2022-01", "2022-11"),
    "red_sea_2024": ("2023-12", "2024-12"),
    "red_sea_late": ("2025-01", "2026-06"),
}

DISRUPTED_THRESHOLD = 0.85   # a month arriving below 85% of its trailing norm


def _window(series: dict[str, float], lo: str, hi: str) -> list[float]:
    return [v for m, v in series.items() if lo <= m <= hi]


def _runs(flags: list[bool]) -> list[int]:
    out, cur = [], 0
    for f in flags:
        if f:
            cur += 1
        elif cur:
            out.append(cur); cur = 0
    if cur:
        out.append(cur)
    return out


def main() -> int:
    print("\n" + "=" * 78)
    print("DISRUPTION PRESETS vs MEASURED ARRIVALS (IMF PortWatch AIS)")
    print("=" * 78)

    print("\n1. CHOKEPOINT TRANSITS, daily calls averaged by month")
    print(f"   {'chokepoint':<22}" + "".join(f"{e:>14}" for e in EVENTS))
    for cp in ("Suez Canal", "Bab el-Mandeb Strait", "Cape of Good Hope",
               "Strait of Hormuz"):
        s = load_chokepoint_monthly(cp)
        base = st.mean(_window(s, *EVENTS["pre_crisis"])) or 1.0
        cells = ""
        for lo, hi in EVENTS.values():
            v = _window(s, lo, hi)
            cells += f"{(st.mean(v) / base):>14.2f}" if v else f"{'-':>14}"
        print(f"   {cp:<22}{cells}")
    print("   (ratios to each chokepoint's own 2019 baseline)")

    print("\n2. ROUTE ARRIVAL SHORTFALL, relative proxy, 1.00 = trailing norm")
    print(f"   {'route':<12}{'port':<12}" + "".join(f"{e:>14}" for e in EVENTS))
    measured: dict[str, dict[str, float]] = {}
    for route, port in ROUTE_TO_PORT.items():
        if port is None:
            continue
        s = port_shock_series(port)
        measured[route] = s
        cells = ""
        for lo, hi in EVENTS.values():
            v = _window(s, lo, hi)
            cells += f"{st.mean(v):>14.3f}" if v else f"{'-':>14}"
        print(f"   {route:<12}{port:<12}{cells}")

    print("\n3. PRESET ASSUMPTION vs MEASURED WORST SUSTAINED WINDOW")
    print("   A preset can only be judged against a window in which its event")
    print("   ACTUALLY HAPPENED. A tail scenario that did not occur in 2019-2026")
    print("   is untested, not refuted, and is marked so rather than scored.")
    # Which presets describe an event present in the measured window.
    OCCURRED = {
        "red_sea_houthi": "red Sea crisis, Dec 2023 onward",
        "aqaba_congestion": "Iraq transit surge through Aqaba",
        "northern_land_disruption": "chronic Syria/Iraq overland instability",
    }
    print()
    print(f"   {'preset':<26}{'assumed':>8}{'measured':>10}  {'verdict':<12}"
          f"{'basis'}")
    for name, sc in PRESETS.items():
        if name == "baseline":
            continue
        hit = [r for r in sc.affected_routes if r in measured] or list(measured)
        vals = []
        for r in hit:
            s_ = measured[r]
            for ev in ("covid_peak", "red_sea_2024", "red_sea_late"):
                w = _window(s_, *EVENTS[ev])
                if w:
                    vals.append(st.mean(w))
        worst = min(vals) if vals else float("nan")
        if name not in OCCURRED:
            verdict, basis = "UNTESTED", "event absent from 2019-2026"
        elif sc.fill_multiplier > worst + 0.08:
            verdict, basis = "OPTIMISTIC", OCCURRED[name]
        elif sc.fill_multiplier < worst - 0.15:
            verdict, basis = "pessimistic", OCCURRED[name]
        else:
            verdict, basis = "consistent", OCCURRED[name]
        w_txt = f"{worst:>10.3f}" if worst == worst else f"{'-':>10}"
        print(f"   {name:<26}{sc.fill_multiplier:>8.2f}{w_txt}  "
              f"{verdict:<12}{basis}")
    print()
    print("   'measured' is the worst event-window mean arrival ratio on any")
    print("   affected route. Arrivals are NOT fills; this bounds the order of")
    print("   magnitude, it does not measure the preset.")

    print("\n4. DISRUPTION FREQUENCY AND DURATION vs the simulator's regime")
    cfg = JordanV2Config()
    stationary = cfg.p_disruption_start / (
        cfg.p_disruption_start + cfg.p_disruption_end)
    exp_len = 1.0 / cfg.p_disruption_end
    print(f"   simulator assumes: {stationary:.1%} of weeks disrupted, "
          f"mean run {exp_len:.1f} weeks")
    print(f"   {'route':<12}{'months':>8}{'% disrupted':>13}"
          f"{'mean run (mo)':>15}{'max run':>9}")
    for route, s in measured.items():
        months = sorted(s)
        flags = [s[m] < DISRUPTED_THRESHOLD for m in months]
        runs = _runs(flags)
        share = sum(flags) / len(flags) if flags else 0.0
        print(f"   {route:<12}{len(months):>8}{share:>12.1%}"
              f"{(st.mean(runs) if runs else 0):>15.1f}"
              f"{(max(runs) if runs else 0):>9}")
    print(f"\n   A month below {DISRUPTED_THRESHOLD:.0%} of its trailing norm "
          "counts as disrupted.")
    print("   Monthly runs are not directly comparable to weekly ones: a run")
    print("   of 1 month spans 4.3 weeks, so the simulator's 3.6-week mean is")
    print("   SHORTER than anything this measurement can resolve.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
