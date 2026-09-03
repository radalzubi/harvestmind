"""Real public data behind the Project B commercial validation.

WHAT IS REAL HERE, AND WHAT IS NOT. This is the boundary the whole
validation rests on, so it is stated before anything else.

REAL, measured, downloaded, and committed under ``data/external/``:
  * The DEMAND PATH. US Census Monthly Wholesale Trade Survey, grocery and
    related products merchant wholesalers (NAICS 4244), monthly sales,
    1992-01 to 2026-06, via FRED ``S4244SM144NCEN`` (not seasonally
    adjusted, so the seasonality is the real thing and not an artifact of
    an adjustment filter). 414 observations spanning two recessions, COVID,
    and the 2021-23 inflation.
  * The SUPPLY SHOCK PATH. IMF PortWatch daily port calls and import
    tonnage from satellite AIS, 2019-01-01 to 2026-08-30, for the specific
    ports that serve each of Jordan's import routes. Aqaba is Jordan's only
    seaport and PortWatch records it as carrying 100% of Jordanian maritime
    imports, so route exposure is not a modelling choice here, it is the
    country's geography.
  * The CHOKEPOINT PATH. PortWatch daily transit calls for 28 chokepoints,
    including Suez, Bab el-Mandeb and Hormuz, over the same window.

SYNTHETIC, and therefore never claimed as validated:
  * The CROSS-SECTION. Which SKU, which supplier, which margin. No public
    source publishes SKU-level order and fill records for any distributor,
    so the ABC curve and the supplier tagging remain calibrated guesses.
  * The mapping from a port's ARRIVAL SHORTFALL to a supplier's FILL RATE.
    We observe tonnage, never orders, so a fill rate cannot be measured. We
    construct a documented PROXY below and label every result that uses it.

WHY THE PROXY IS DEFENSIBLE, AND WHERE IT BREAKS. Arrivals falling below
their trailing norm can mean supply failed OR that less was ordered because
demand fell. Those are not the same thing and COVID contains both. The
relative proxy strips the common component by dividing each port's own
deviation by a regional benchmark's deviation in the same month, which
removes any shock that moved every port together and leaves the part
specific to that route. It cannot remove a shock that hit one route through
demand alone. That residual confound is real and is reported, not hidden.
"""

from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FRED_DIR = ROOT / "data" / "external" / "fred"
PORT_DIR = ROOT / "data" / "external" / "portwatch"

# Demand spine. NSA on purpose: the seasonality is the signal, not noise.
DEMAND_SERIES = "S4244SM144NCEN"

# Each Jordanian import route mapped to the real port that serves it.
# ``None`` means domestically supplied and therefore unexposed to a port
# shock, which is the whole reason route substitution has any value.
ROUTE_TO_PORT: dict[str, str | None] = {
    "aqaba": "Aqaba",
    "saudi_land": "Jeddah",       # landed at a Saudi port, trucked north
    "syria_land": "Latakia",
    "iraq_land": "Umm Qasr",
    "local": None,
    "air": None,
}

# Benchmark for the relative (difference-in-differences) proxy. Jebel Ali is
# the largest regional container port and is not on any of Jordan's routes,
# so it carries the common regional component without carrying the shock
# specific to a Jordanian route.
BENCHMARK_PORT = "Jebel Ali"

# Named historical windows. Chosen BEFORE any result was computed, from
# dated events, so the regime split is not fitted to the outcome.
REGIMES: dict[str, tuple[str, str]] = {
    "normal_1990s":  ("1994-01", "2000-12"),
    "normal_2000s":  ("2003-01", "2007-06"),
    "gfc":           ("2007-07", "2010-12"),
    "normal_2010s":  ("2012-01", "2019-12"),
    "covid":         ("2020-01", "2021-06"),
    "inflation":     ("2021-07", "2023-06"),
    "red_sea_war":   ("2023-11", "2026-06"),
}

# Windows for which a REAL route-specific supply shock exists. PortWatch
# starts in 2019, so anything earlier can only use the real demand path.
PORT_DATA_START = "2019-01"


def load_fred_monthly(series_id: str) -> dict[str, float]:
    """FRED CSV to {YYYY-MM: value}, dropping the '.' missing marker."""
    path = FRED_DIR / f"{series_id}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run scripts/fetch_real_data.py first.")
    out: dict[str, float] = {}
    with path.open() as fh:
        for row in csv.DictReader(fh):
            raw = row.get(series_id, ".")
            if raw in (".", "", None):
                continue
            out[row["observation_date"][:7]] = float(raw)
    if not out:
        raise ValueError(f"{series_id} parsed to zero observations")
    return out


def load_port_monthly(portname: str, field: str = "import") -> dict[str, float]:
    """Daily PortWatch rows summed to calendar months for one port."""
    path = PORT_DIR / "regional_ports_daily.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run scripts/fetch_real_data.py first.")
    out: dict[str, float] = defaultdict(float)
    seen = False
    with path.open() as fh:
        for row in csv.DictReader(fh):
            if row["portname"] != portname:
                continue
            seen = True
            out[row["date"][:7]] += float(row[field] or 0.0)
    if not seen:
        raise ValueError(f"port {portname!r} not present in the panel")
    # The final month is usually partial and would read as a fake collapse.
    months = sorted(out)
    return {m: out[m] for m in months[:-1]}


def load_chokepoint_monthly(portname: str,
                            field: str = "n_total") -> dict[str, float]:
    """Daily chokepoint transits averaged per day within each month."""
    path = PORT_DIR / "chokepoint_daily.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. Run scripts/fetch_real_data.py first.")
    acc: dict[str, list[float]] = defaultdict(list)
    with path.open() as fh:
        for row in csv.DictReader(fh):
            if row["portname"] != portname:
                continue
            acc[row["date"][:7]].append(float(row[field] or 0.0))
    months = sorted(acc)
    return {m: st.mean(acc[m]) for m in months[:-1]}


def _trailing_expectation(series: dict[str, float], window: int = 12
                          ) -> dict[str, float]:
    """Trailing median over ``window`` months, strictly BEFORE each month.

    Median rather than mean so that one catastrophic month does not lower
    the bar that the following months are judged against, which would make
    a sustained disruption decay to 'normal' purely by arithmetic.
    """
    months = sorted(series)
    out: dict[str, float] = {}
    for k, m in enumerate(months):
        if k < window:
            continue
        prior = [series[months[j]] for j in range(k - window, k)]
        med = st.median(prior)
        if med > 0:
            out[m] = med
    return out


def port_shock_series(portname: str, field: str = "import",
                      relative: bool = True) -> dict[str, float]:
    """Monthly arrival-shortfall PROXY for one port, capped at 1.0.

    Returns {YYYY-MM: multiplier in (0, 1]}. A value of 1.0 means arrivals
    were at or above their trailing norm; 0.6 means arrivals came in at 60%
    of it. This is a PROXY FOR A FILL RATE, not a measured fill rate: we
    observe tonnage landed, never tonnage ordered.

    With ``relative=True`` the port's own deviation is divided by the
    benchmark port's deviation in the same month, so any shock that moved
    the whole region drops out and what remains is specific to this route.
    """
    series = load_port_monthly(portname, field)
    expect = _trailing_expectation(series)
    own = {m: series[m] / expect[m] for m in expect}
    if not relative:
        return {m: min(1.0, v) for m, v in own.items()}

    bench = load_port_monthly(BENCHMARK_PORT, field)
    bexp = _trailing_expectation(bench)
    bdev = {m: bench[m] / bexp[m] for m in bexp}
    out: dict[str, float] = {}
    for m, v in own.items():
        b = bdev.get(m)
        if not b or b <= 0:
            continue
        out[m] = min(1.0, v / b)
    return out


def route_shock_panel(relative: bool = True) -> dict[str, dict[str, float]]:
    """Arrival-shortfall proxy per Jordanian import route.

    Routes with no port (``local``, ``air``) get an all-ones series over the
    union of months, because domestic supply and air freight are not exposed
    to a seaport shock. Leaving them exposed would erase the substitution
    effect that the route structure exists to represent.
    """
    panel: dict[str, dict[str, float]] = {}
    for route, port in ROUTE_TO_PORT.items():
        if port is not None:
            panel[route] = port_shock_series(port, relative=relative)
    months = sorted({m for s in panel.values() for m in s})
    for route, port in ROUTE_TO_PORT.items():
        if port is None:
            panel[route] = {m: 1.0 for m in months}
    return panel


def demand_index(start: str | None = None, end: str | None = None
                 ) -> dict[str, float]:
    """Real monthly wholesale grocery sales, normalised to mean 1.0.

    Kept as an INDEX rather than dollars: the level of US wholesale trade is
    not the level of a Jordanian distributor, but the shape over time, the
    seasonality and the shock structure are what the optimizer is judged on.
    """
    raw = load_fred_monthly(DEMAND_SERIES)
    sel = {m: v for m, v in raw.items()
           if (start is None or m >= start) and (end is None or m <= end)}
    if not sel:
        raise ValueError(f"no demand observations in [{start}, {end}]")
    mean = st.mean(sel.values())
    return {m: v / mean for m, v in sorted(sel.items())}


def months_between(start: str, end: str) -> list[str]:
    y0, m0 = map(int, start.split("-"))
    y1, m1 = map(int, end.split("-"))
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def regime_of(month: str) -> str | None:
    for name, (lo, hi) in REGIMES.items():
        if lo <= month <= hi:
            return name
    return None


__all__ = [
    "REGIMES", "ROUTE_TO_PORT", "BENCHMARK_PORT", "DEMAND_SERIES",
    "PORT_DATA_START", "load_fred_monthly", "load_port_monthly",
    "load_chokepoint_monthly", "port_shock_series", "route_shock_panel",
    "demand_index", "months_between", "regime_of",
]
