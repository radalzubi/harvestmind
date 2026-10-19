"""Deterministic stratified selection of store-product series from the TRAINING split only.

Every feature below is computed from the 90 training days; the evaluation week is never read. Strata are the
cross of volume tercile, stockout exposure, demand regularity and promotional exposure; 50 series are allocated
across the occupied strata proportionally with a floor of one, then drawn inside each stratum by a seeded generator
with a preference for stores, cities and categories not yet chosen, so the sample spans the business as widely as
50 cells allow. Nothing about any policy's results enters the selection, and the selection is frozen in a manifest
(`selection_manifest`) that records every cell's features and the rule that placed it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

import duckdb
import numpy as np

SELECTION_VERSION = "frn-selection-1"
DEFAULT_SEED = 20261019
DEFAULT_COUNT = 50
#: stratum thresholds (training-period features; documented, not tuned)
STOCKOUT_FREQUENT = 0.50        # share of days with at least one out-of-stock business hour
STOCKOUT_RARE = 0.25
INTERMITTENT_ZERO_SHARE = 0.25  # share of zero-sales days
VOLATILE_CV = 0.60              # coefficient of variation of daily sales
PROMOTIONAL_SHARE = 0.60        # share of days with discount < 1
MIN_STRATUM_POPULATION = 100    # a stratum this small (0.2 % of the panel) gets no guaranteed seat

FEATURE_SQL = """
SELECT store_id, product_id, any_value(city_id) AS city_id, any_value(first_category_id) AS first_category_id,
       any_value(third_category_id) AS third_category_id,
       count(*) AS days, avg(sale_amount) AS mean_daily, stddev_samp(sale_amount) AS sd_daily,
       avg(CASE WHEN sale_amount = 0 THEN 1 ELSE 0 END) AS zero_share,
       avg(CASE WHEN stock_hours_out > 0 THEN 1 ELSE 0 END) AS stockout_day_share,
       avg(stock_hours_out) / 16.0 AS stockout_hour_share,
       avg(CASE WHEN discount < 1 THEN 1 ELSE 0 END) AS promo_share,
       avg(CASE WHEN activity_flag = 1 THEN 1 ELSE 0 END) AS activity_share
FROM frn_daily WHERE split = 'train' GROUP BY store_id, product_id
"""


@dataclass(frozen=True)
class SeriesFeatures:
    store_id: int
    product_id: int
    city_id: int
    first_category_id: int
    third_category_id: int
    days: int
    mean_daily: float
    sd_daily: float
    zero_share: float
    stockout_day_share: float
    stockout_hour_share: float
    promo_share: float
    activity_share: float
    volume_class: str
    stockout_class: str
    regularity_class: str
    promo_class: str

    @property
    def stratum(self) -> str:
        return f"{self.volume_class}|{self.stockout_class}|{self.regularity_class}|{self.promo_class}"

    @property
    def cv(self) -> float:
        return self.sd_daily / self.mean_daily if self.mean_daily > 0 else float("inf")


def features(conn: duckdb.DuckDBPyConnection) -> list[SeriesFeatures]:
    rows = conn.execute(FEATURE_SQL).fetchall()
    means = np.asarray([r[6] for r in rows])
    lo, hi = np.quantile(means, [1 / 3, 2 / 3])
    out = []
    for r in rows:
        store, product, city, cat1, cat3, days, mean, sd, zero, so_day, so_hour, promo, activity = r
        sd = float(sd or 0.)
        cv = sd / mean if mean > 0 else float("inf")
        out.append(SeriesFeatures(
            int(store), int(product), int(city), int(cat1), int(cat3), int(days), float(mean), sd, float(zero), float(so_day), float(so_hour),
            float(promo), float(activity),
            volume_class="high" if mean > hi else "low" if mean <= lo else "medium",
            stockout_class="frequent" if so_day >= STOCKOUT_FREQUENT else "rare" if so_day < STOCKOUT_RARE else "occasional",
            regularity_class="intermittent" if zero >= INTERMITTENT_ZERO_SHARE else "volatile" if cv >= VOLATILE_CV else "smooth",
            promo_class="promotional" if promo >= PROMOTIONAL_SHARE else "non_promotional"))
    return out


def select(conn: duckdb.DuckDBPyConnection, *, count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    """The frozen selection and its manifest. Deterministic for (count, seed, data)."""
    rows = features(conn)
    complete = [f for f in rows if f.days == 90]
    if len(complete) != len(rows):
        raise ValueError(f"{len(rows) - len(complete)} training series do not have 90 days; the panel is not the audited one")
    by_stratum: dict[str, list[SeriesFeatures]] = {}
    for f in complete:
        by_stratum.setdefault(f.stratum, []).append(f)
    strata = sorted(by_stratum)                                    # deterministic order
    sizes = {s: len(by_stratum[s]) for s in strata}
    total = sum(sizes.values())
    # proportional allocation with a floor of one for every stratum that is not negligible (at least MIN_STRATUM_POPULATION
    # series); negligible strata take only what proportion gives them; largest remainders fill what is left
    floors = {s: (1 if sizes[s] >= MIN_STRATUM_POPULATION else 0) for s in strata}
    if sum(floors.values()) > count:
        raise ValueError(f"{sum(floors.values())} non-negligible strata exceed the sample of {count}")
    remaining = count - sum(floors.values())
    shares = {s: sizes[s] / total * remaining for s in strata}
    alloc = {s: floors[s] + int(np.floor(shares[s])) for s in strata}
    leftover = count - sum(alloc.values())
    for s in sorted(strata, key=lambda k: (-(shares[k] - np.floor(shares[k])), k))[:leftover]:
        alloc[s] += 1
    all_strata = list(strata)
    strata = [s for s in strata if alloc[s] > 0]
    rng = np.random.default_rng(seed)
    chosen: list[SeriesFeatures] = []
    used_stores: set[int] = set()
    used_cities: set[int] = set()
    used_categories: set[int] = set()
    for s in strata:
        pool = sorted(by_stratum[s], key=lambda f: (f.store_id, f.product_id))
        order = rng.permutation(len(pool))
        picked = 0
        # preference passes: unseen store+city+category, then unseen store, then anything
        for pass_ in range(3):
            for i in order:
                if picked >= alloc[s]:
                    break
                f = pool[i]
                if f in chosen:
                    continue
                fresh_store = f.store_id not in used_stores
                fresh_city = f.city_id not in used_cities
                fresh_cat = f.first_category_id not in used_categories
                ok = (pass_ == 0 and fresh_store and (fresh_city or fresh_cat)) or (pass_ == 1 and fresh_store) or pass_ == 2
                if not ok:
                    continue
                chosen.append(f)
                used_stores.add(f.store_id)
                used_cities.add(f.city_id)
                used_categories.add(f.first_category_id)
                picked += 1
    assert len(chosen) == count, (len(chosen), count)
    series = [{**asdict(f), "stratum": f.stratum, "cv": None if f.cv == float("inf") else round(f.cv, 4)} for f in chosen]
    series.sort(key=lambda r: (r["stratum"], r["store_id"], r["product_id"]))
    manifest = {
        "selection_version": SELECTION_VERSION, "seed": seed, "count": count, "evidence": "DERIVED from the training split only",
        "information_boundary": "training split (2024-03-28 .. 2024-06-25); the evaluation week was not read",
        "thresholds": {"volume_terciles_mean_daily": [float(np.quantile([f.mean_daily for f in complete], 1 / 3)),
                                                      float(np.quantile([f.mean_daily for f in complete], 2 / 3))],
                       "stockout_frequent_day_share": STOCKOUT_FREQUENT, "stockout_rare_day_share": STOCKOUT_RARE,
                       "intermittent_zero_share": INTERMITTENT_ZERO_SHARE, "volatile_cv": VOLATILE_CV, "promotional_share": PROMOTIONAL_SHARE},
        "population": {"series": total, "strata": {s: {"population": sizes[s], "allocated": alloc[s]} for s in all_strata}},
        "diversity": {"stores": len({r['store_id'] for r in series}), "cities": len({r['city_id'] for r in series}),
                      "first_categories": len({r['first_category_id'] for r in series}), "products": len({r['product_id'] for r in series})},
        "rule": f"proportional allocation across occupied strata with a floor of one for strata of at least {MIN_STRATUM_POPULATION} series, "
                "largest remainders; seeded permutation inside each stratum with preference for unseen stores, cities and categories; "
                "no policy result enters the selection",
        "series": series,
    }
    manifest["selection_hash"] = hashlib.sha256(json.dumps([(r["store_id"], r["product_id"]) for r in series]).encode()).hexdigest()
    return manifest
