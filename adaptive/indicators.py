"""Public leading indicators -> Signals.

Each loader turns a cached public series into dated ``Signal`` observations
with REAL_PUBLIC provenance, a quality score, the cache's ``fetched_at`` as
``refreshed_at``, and the transform written down. Indices are expressed
against the series' own trailing norm so the estimator reads "how unusual
is now" rather than a level it would have to interpret:

  chokepoint_transit_index   7-day mean transits / trailing 365-day median   (per chokepoint -> route)
  port_throughput_index      monthly imports / trailing 12-month median      (per port)
  gscpi                      level, in sd of the historical series            (global)
  freight_index_yoy          12-month change of the freight services index    (region "US")
  fuel_index                 30-day mean / trailing 365-day median            (global; Brent)
  conflict_index             7-day mean coverage / trailing 180-day median   (per topic -> route)
  demand_index_yoy           12-month change of retail sales                  (region "US")
  sentiment_z                consumer sentiment, sd from trailing 5-year mean (region "US")

Nothing here forecasts. ``adaptive.leading`` combines these into a risk
outlook, and the historical lead/lag check in
``scripts/validate_leading_indicators.py`` says how much (if any) lead they
actually carry against the port throughput they are supposed to anticipate.
"""

from __future__ import annotations

import bisect
import csv
import json
import statistics as st
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from adaptive.signals import Signal, SignalStore

ROOT = Path(__file__).resolve().parents[1]
IND = ROOT / "data" / "external" / "indicators"
PORTWATCH = ROOT / "data" / "external" / "portwatch"

# Which physical chokepoints a lane depends on, and which GDELT topic tracks it.
ROUTE_CHOKEPOINTS = {
    "red_sea": ("Bab el-Mandeb Strait", "Suez Canal"),
    "aqaba": ("Bab el-Mandeb Strait", "Suez Canal"),
    "sea": ("Bab el-Mandeb Strait", "Suez Canal"),
    "suez": ("Suez Canal",),
    "hormuz": ("Strait of Hormuz",),
    "gulf": ("Strait of Hormuz",),
    "cape": ("Cape of Good Hope",),
}
ROUTE_TOPIC = {"red_sea": "red_sea_shipping", "aqaba": "red_sea_shipping", "sea": "red_sea_shipping",
               "suez": "suez_shipping", "hormuz": "hormuz_shipping", "gulf": "hormuz_shipping"}
PORT_OF_ROUTE = {"red_sea": "AQABA", "aqaba": "AQABA", "sea": "AQABA"}


def _meta(name: str) -> datetime | None:
    p = IND / f"{name}.meta.json"
    if not p.exists():
        return None
    try:
        return datetime.fromisoformat(json.loads(p.read_text())["fetched_at"])
    except (KeyError, ValueError):
        return None


def _series(name: str) -> list[tuple[datetime, float]]:
    p = IND / f"{name}.csv"
    if not p.exists():
        return []
    out = []
    with p.open() as fh:
        for row in csv.DictReader(fh):
            try:
                out.append((datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc), float(row["value"])))
            except (KeyError, ValueError):
                continue
    return sorted(out)


def _trailing_index(xs: list, window_days: int, recent_days: int) -> list[tuple[datetime, float]]:
    """value = mean(last recent_days) / median(prior window_days), per date.
    ``xs`` is sorted; the two windows slide with bisect so a long daily
    series costs O(n log n) rather than a rescan of the past per date."""
    if not xs:
        return []
    dates = [d for d, _ in xs]
    vals = [v for _, v in xs]
    min_prior = max(10, window_days // 30)
    out = []
    for k, d in enumerate(dates):
        r0 = bisect.bisect_right(dates, d - timedelta(days=recent_days), 0, k + 1)     # first dd > d - recent
        p0 = bisect.bisect_right(dates, d - timedelta(days=window_days + recent_days), 0, k + 1)
        recent = vals[r0:k + 1]
        prior = vals[p0:r0]
        if len(prior) >= min_prior and recent:
            med = st.median(prior)
            if med > 0:
                out.append((d, st.mean(recent) / med))
    return out


def _z(xs: list, window_days: int) -> list[tuple[datetime, float]]:
    if not xs:
        return []
    dates = [d for d, _ in xs]
    vals = [v for _, v in xs]
    out = []
    for k, (d, v) in enumerate(xs):
        p0 = bisect.bisect_right(dates, d - timedelta(days=window_days), 0, k)
        prior = vals[p0:k]
        if len(prior) >= 12:
            sd = st.pstdev(prior) or 1e-9
            out.append((d, (v - st.mean(prior)) / sd))
    return out


def _yoy(xs: list) -> list[tuple[datetime, float]]:
    by_month = {(d.year, d.month): v for d, v in xs}
    out = []
    for d, v in xs:
        prev = by_month.get((d.year - 1, d.month))
        if prev:
            out.append((d, v / prev - 1.0))
    return out


def load_chokepoints(store: SignalStore, csv_path: Path = PORTWATCH / "chokepoint_daily.csv",
                     names: tuple = ("Bab el-Mandeb Strait", "Suez Canal", "Strait of Hormuz", "Cape of Good Hope"),
                     step_days: int = 7) -> int:
    if not csv_path.exists():
        return 0
    refreshed = datetime.fromtimestamp(csv_path.stat().st_mtime, tz=timezone.utc)
    daily: dict = defaultdict(list)
    with csv_path.open() as fh:
        for row in csv.DictReader(fh):
            if row["portname"] in names:
                daily[row["portname"]].append((datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc),
                                               float(row["n_total"] or 0)))
    n = 0
    for name, xs in daily.items():
        xs.sort()
        idx = _trailing_index(xs, 365, 7)
        for k, (d, v) in enumerate(idx):
            if k % step_days:
                continue
            store.add(Signal(d, "chokepoint", name.upper(), "chokepoint_transit_index", min(v, 3.0), "REAL_PUBLIC",
                             0.85, refreshed, "7-day mean transits / trailing 365-day median (IMF PortWatch)"))
            n += 1
    return n


def load_fred_like(store: SignalStore, name: str, entity_type: str, entity_id: str, metric: str,
                   transform: str, quality: float = 0.7) -> int:
    xs = _series(name)
    if not xs:
        return 0
    if transform == "yoy":
        vals = _yoy(xs)
    elif transform == "z5y":
        vals = _z(xs, 5 * 365)
    elif transform == "index30_365":
        vals = _trailing_index(xs, 365, 30)
    elif transform == "level":
        vals = xs
    else:
        raise ValueError(transform)
    refreshed = _meta(name)
    for d, v in vals:
        store.add(Signal(d, entity_type, entity_id, metric, float(v), "REAL_PUBLIC", quality, refreshed,
                         f"{name}: {transform}"))
    return len(vals)


def load_gdelt(store: SignalStore, topic: str, step_days: int = 3) -> int:
    xs = _series(f"gdelt_{topic}")
    if not xs:
        return 0
    vals = _trailing_index(xs, 180, 7)
    refreshed = _meta(f"gdelt_{topic}")
    n = 0
    for k, (d, v) in enumerate(vals):
        if k % step_days:
            continue
        store.add(Signal(d, "topic", topic.upper(), "conflict_index", min(v, 5.0), "REAL_PUBLIC", 0.5, refreshed,
                         "7-day mean coverage share / trailing 180-day median (GDELT)"))
        n += 1
    return n


def load_all_indicators(store: SignalStore) -> dict:
    """Everything the cache holds; the return value says what loaded."""
    counts = {
        "chokepoints": load_chokepoints(store),
        "gscpi": load_fred_like(store, "gscpi", "region", "GLOBAL", "gscpi", "level", 0.8),
        "freight_index_yoy": load_fred_like(store, "freight_index", "region", "US", "freight_index_yoy", "yoy", 0.6),
        "fuel_index": load_fred_like(store, "brent_usd", "region", "GLOBAL", "fuel_index", "index30_365", 0.7),
        "demand_index_yoy": load_fred_like(store, "retail_sales_usd_m", "region", "US", "demand_index_yoy", "yoy", 0.6),
        "sentiment_z": load_fred_like(store, "consumer_sentiment", "region", "US", "sentiment_z", "z5y", 0.5),
    }
    for topic in ("red_sea_shipping", "hormuz_shipping", "suez_shipping", "jordan_economy"):
        counts[f"gdelt_{topic}"] = load_gdelt(store, topic)
    return counts
