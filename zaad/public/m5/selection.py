"""Deterministic, training-only selection of M5 store-item series for the weekly evaluation.

Chronology (declared before any policy ran). Walmart weeks run Saturday to Friday; d_1 = Saturday 2011-01-29. The
final holdout origin is Saturday 2016-01-02 (d_1800). Every selection feature is computed on days strictly before
that origin, over the 52 Walmart weeks ending 2016-01-01. The evaluation period (d_1914..d_1941, public Kaggle labels)
was never read for selection or tuning; it enters only as settlement truth for the last holdout reviews' horizons.

Eligibility (distributor relevance, not performance): listed for the whole history and holdout (a price row exists
for every Walmart week from the history start to the end of the truth window: a catalogue fact, not a sales outcome);
mean weekly sales of at least 2 units in the feature window (low-volume retail was FreshRetailNet's regime; this
dataset should exercise multiweek replenishment of moving items); no run of 8 or more zero-sales weeks in the feature
window (a proxy for a delisting or long stockout that the dataset cannot distinguish from no demand).

Strata: category (FOODS / HOBBIES / HOUSEHOLD) × weekly volume tercile × weekly volatility (CV > 0.5 volatile) ×
zero-week share (≥ 10 % intermittent). 50 series allocated proportionally with a guaranteed seat for strata of at
least 50 series, seeded draw inside each stratum preferring unseen stores and departments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
import hashlib
import json
from typing import Any

import duckdb
import numpy as np

SELECTION_VERSION = "m5-selection-1"
DEFAULT_SEED = 20261019
DEFAULT_COUNT = 50
HOLDOUT_ORIGIN = date(2016, 1, 2)           # Saturday, d_1800
FEATURE_WEEKS = 52
MIN_MEAN_WEEKLY = 2.0
MAX_ZERO_RUN_WEEKS = 8
VOLATILE_CV = 0.5
INTERMITTENT_ZERO_SHARE = 0.10
MIN_STRATUM_POPULATION = 50
TRUTH_END = date(2016, 5, 20)               # last full Walmart week in the SALES data ends Friday 2016-05-20 (d_1939; d_1941 = 2016-05-22)


def week_start(d: date) -> date:
    """The Saturday that starts the Walmart week containing `d`."""
    return d - timedelta(days=(d.weekday() - 5) % 7)


FEATURE_SQL = """
WITH w AS (
    SELECT id, item_id, dept_id, cat_id, store_id, state_id, c.wm_yr_wk, sum(qty) AS q
    FROM m5_daily m JOIN m5_calendar c USING (d)
    WHERE m.d >= ? AND m.d < ?
    GROUP BY 1, 2, 3, 4, 5, 6, 7
), s AS (
    SELECT id, any_value(item_id) AS item_id, any_value(dept_id) AS dept_id, any_value(cat_id) AS cat_id, any_value(store_id) AS store_id,
           any_value(state_id) AS state_id, count(*) AS weeks, avg(q) AS mean_weekly, stddev_samp(q) AS sd_weekly,
           avg(CASE WHEN q = 0 THEN 1 ELSE 0 END) AS zero_share, list(q ORDER BY wm_yr_wk) AS series
    FROM w GROUP BY id
)
SELECT * FROM s
"""


@dataclass(frozen=True)
class SeriesFeatures:
    id: str
    item_id: str
    dept_id: str
    cat_id: str
    store_id: str
    state_id: str
    weeks: int
    mean_weekly: float
    sd_weekly: float
    zero_share: float
    longest_zero_run: int
    listed_throughout: bool
    volume_class: str
    volatility_class: str
    intermittency_class: str

    @property
    def stratum(self) -> str:
        return f"{self.cat_id}|{self.volume_class}|{self.volatility_class}|{self.intermittency_class}"


def _longest_zero_run(values: list[float]) -> int:
    best = run = 0
    for v in values:
        run = run + 1 if v == 0 else 0
        best = max(best, run)
    return best


def _listed(conn: duckdb.DuckDBPyConnection) -> set[str]:
    """Series with a price row for every Walmart week from the history start to the truth end."""
    start = HOLDOUT_ORIGIN - timedelta(weeks=FEATURE_WEEKS)
    row = conn.execute("SELECT count(DISTINCT wm_yr_wk) FROM m5_calendar WHERE d >= ? AND d <= ?", [start, TRUTH_END]).fetchone()
    weeks = row[0] if row else 0
    rows = conn.execute("""SELECT p.store_id || '|' || p.item_id FROM m5_prices p
                           JOIN (SELECT DISTINCT wm_yr_wk FROM m5_calendar WHERE d >= ? AND d <= ?) k USING (wm_yr_wk)
                           GROUP BY 1 HAVING count(DISTINCT p.wm_yr_wk) = ?""", [start, TRUTH_END, weeks]).fetchall()
    return {r[0] for r in rows}


def features(conn: duckdb.DuckDBPyConnection) -> list[SeriesFeatures]:
    listed = _listed(conn)
    rows = conn.execute(FEATURE_SQL, [HOLDOUT_ORIGIN - timedelta(weeks=FEATURE_WEEKS), HOLDOUT_ORIGIN]).fetchall()
    means = np.asarray([r[7] for r in rows if r[7] >= MIN_MEAN_WEEKLY])
    lo, hi = np.quantile(means, [1 / 3, 2 / 3])
    out = []
    for r in rows:
        id_, item, dept, cat, store, state, weeks, mean, _sd_sql, zero, series = r
        # moments from the ordered weekly list in Python: DuckDB's parallel aggregates differ in the last bits between runs
        # (one series sits at a coefficient of variation of exactly 0.5, and 6.0 versus 5.999... flipped its stratum, the
        # allocation and the draw); a strict comparison on a rounded ratio keeps the frozen manifest reproducible
        values = np.asarray(list(series), dtype=float)
        mean = float(values.mean())
        sd = float(values.std(ddof=1)) if len(values) > 1 else 0.
        zero = float(np.mean(values == 0))
        cv = round(sd / mean, 9) if mean > 0 else float("inf")
        out.append(SeriesFeatures(id_, item, dept, cat, store, state, int(weeks), float(mean), sd, float(zero), _longest_zero_run(list(series)),
                                  f"{store}|{item}" in listed,
                                  volume_class="high" if mean > hi else "low" if mean <= lo else "medium",
                                  volatility_class="volatile" if cv > VOLATILE_CV else "steady",
                                  intermittency_class="intermittent" if zero >= INTERMITTENT_ZERO_SHARE else "continuous"))
    return out


def select(conn: duckdb.DuckDBPyConnection, *, count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED) -> dict[str, Any]:
    rows = features(conn)
    eligible = [f for f in rows if f.weeks == FEATURE_WEEKS and f.mean_weekly >= MIN_MEAN_WEEKLY and f.longest_zero_run < MAX_ZERO_RUN_WEEKS and f.listed_throughout]
    by: dict[str, list[SeriesFeatures]] = {}
    for f in eligible:
        by.setdefault(f.stratum, []).append(f)
    strata = sorted(by)
    sizes = {s: len(by[s]) for s in strata}
    total = sum(sizes.values())
    floors = {s: (1 if sizes[s] >= MIN_STRATUM_POPULATION else 0) for s in strata}
    if sum(floors.values()) > count:
        raise ValueError(f"{sum(floors.values())} non-negligible strata exceed the sample of {count}")
    remaining = count - sum(floors.values())
    shares = {s: sizes[s] / total * remaining for s in strata}
    alloc = {s: floors[s] + int(np.floor(shares[s])) for s in strata}
    leftover = count - sum(alloc.values())
    for s in sorted(strata, key=lambda k: (-(shares[k] - np.floor(shares[k])), k))[:leftover]:
        alloc[s] += 1
    rng = np.random.default_rng(seed)
    chosen: list[SeriesFeatures] = []
    used_stores: set[str] = set()
    used_depts: set[str] = set()
    for s in strata:
        if alloc[s] == 0:
            continue
        pool = sorted(by[s], key=lambda f: f.id)
        order = rng.permutation(len(pool))
        picked = 0
        for pass_ in range(3):
            for i in order:
                if picked >= alloc[s]:
                    break
                f = pool[i]
                if f in chosen:
                    continue
                ok = (pass_ == 0 and f.store_id not in used_stores and f.dept_id not in used_depts) or (pass_ == 1 and f.store_id not in used_stores) or pass_ == 2
                if not ok:
                    continue
                chosen.append(f)
                used_stores.add(f.store_id)
                used_depts.add(f.dept_id)
                picked += 1
    if len(chosen) != count:
        raise RuntimeError(f"selected {len(chosen)} series, {count} requested")
    series = sorted((asdict(f) | {"stratum": f.stratum} for f in chosen), key=lambda r: (r["stratum"], r["id"]))
    manifest = {
        "selection_version": SELECTION_VERSION, "seed": seed, "count": count, "evidence": "DERIVED from sales before the holdout origin and the price catalogue",
        "information_boundary": f"sales features: 52 Walmart weeks ending {(HOLDOUT_ORIGIN - timedelta(days=1)).isoformat()}; the public evaluation period d_1914..d_1941 was not read",
        "holdout_origin": HOLDOUT_ORIGIN.isoformat(), "eligibility": {"min_mean_weekly": MIN_MEAN_WEEKLY, "max_zero_run_weeks": MAX_ZERO_RUN_WEEKS,
                                                                    "listed_every_week_through": TRUTH_END.isoformat()},
        "thresholds": {"volume_terciles_mean_weekly": [float(lo) if (lo := np.quantile([f.mean_weekly for f in eligible], 1 / 3)) else 0.,
                                                       float(np.quantile([f.mean_weekly for f in eligible], 2 / 3))],
                       "volatile_cv": VOLATILE_CV, "intermittent_zero_share": INTERMITTENT_ZERO_SHARE, "min_stratum_population": MIN_STRATUM_POPULATION},
        "population": {"series": len(rows), "eligible": len(eligible), "strata": {s: {"population": sizes[s], "allocated": alloc[s]} for s in strata}},
        "diversity": {"stores": len({r['store_id'] for r in series}), "states": len({r['state_id'] for r in series}), "categories": len({r['cat_id'] for r in series}),
                      "departments": len({r['dept_id'] for r in series}), "items": len({r['item_id'] for r in series})},
        "series": series,
    }
    manifest["selection_hash"] = hashlib.sha256(json.dumps([r["id"] for r in series]).encode()).hexdigest()
    return manifest
