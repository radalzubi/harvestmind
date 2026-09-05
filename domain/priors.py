"""Public priors for what an operator has not yet measured.

Every prior here is a PUBLIC_BENCHMARK with an ASSUMED mapping, stated in
the docstring, and is overridden the moment the operator's own history
covers the same quantity. The point is not accuracy; it is that "pending
data intake" means a documented default with a provenance rather than a
silent constant.

  lead_time_cv_prior(iso3)      lead-time coefficient of variation by origin
                                country, from the World Bank Logistics
                                Performance Index (1..5).
  decay_rate_prior(commodity)   weekly shrink share for perishables, from
                                USDA ERS loss-adjusted availability when the
                                cache holds it, else a category table.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIORS = ROOT / "data" / "external" / "priors"


@dataclass(frozen=True)
class Prior:
    value: float
    provenance: str            # PUBLIC_BENCHMARK | ASSUMED
    source: str
    basis: str                 # what the number was derived from
    fetched_at: str | None = None

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _meta(name: str) -> str | None:
    p = PRIORS / f"{name}.meta.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text()).get("fetched_at")
    except ValueError:
        return None


def _lpi_table() -> dict:
    p = PRIORS / "lpi.csv"
    if not p.exists():
        return {}
    with p.open() as fh:
        return {r["iso3"]: (float(r["lpi"]), int(r["year"]), r["country"]) for r in csv.DictReader(fh)}


# ASSUMED mapping. A top-decile logistics country (LPI ~4.1, Germany) gets a
# lead-time CV of about 0.15; a bottom-decile one (LPI ~2.3) about 0.60.
# Quadratic in the score gap so that mid-table countries (3.0-3.5) land
# near 0.3, which is the range measured on the FMCG simulator's importer
# archetype. Clipped to [0.10, 0.80].
LPI_REF = 4.1
CV_REF = 0.15
CV_DEFAULT = 0.35


def lead_time_cv_prior(iso3: str | None) -> Prior:
    tab = _lpi_table()
    key = (iso3 or "").upper()
    if key in tab:
        lpi, year, name = tab[key]
        cv = min(0.80, max(0.10, CV_REF * (LPI_REF / max(lpi, 1.0)) ** 2 * (1.0 + 0.6 * max(0.0, LPI_REF - lpi))))
        return Prior(round(cv, 3), "PUBLIC_BENCHMARK", f"World Bank LPI {year} ({name}: {lpi:.2f})",
                     "CV = 0.15 * (4.1/LPI)^2 * (1 + 0.6*(4.1-LPI)), clipped [0.10, 0.80]; mapping ASSUMED",
                     _meta("lpi"))
    return Prior(CV_DEFAULT, "ASSUMED", "no origin country or LPI unavailable",
                 "flat default; provide supplier origin country to replace it", None)


# Category defaults (weekly shrink share at the distribution stage) used when
# no commodity-level public figure is cached. ASSUMED, conservative, and
# consistent with the buffers in risk/shelf_life.py.
CATEGORY_DECAY_PER_WEEK = {
    "leafy greens": 0.18, "herbs": 0.20, "berries": 0.22, "mushrooms": 0.18,
    "stone fruit": 0.12, "tomatoes": 0.10, "cucumbers": 0.10, "peppers": 0.08,
    "vegetables": 0.08, "fruit": 0.07, "citrus": 0.04, "apples": 0.03, "pears": 0.04,
    "bananas": 0.12, "avocados": 0.10, "grapes": 0.08, "melons": 0.09,
    "root vegetables": 0.02, "roots": 0.02, "onions": 0.02, "potatoes": 0.015,
    "dairy": 0.05, "eggs": 0.02, "fresh meat": 0.15, "poultry": 0.15, "seafood": 0.20,
    "shelf-stable": 0.0,
}


def _lafa_table() -> dict:
    p = PRIORS / "ers_lafa_loss.csv"
    if not p.exists():
        return {}
    out = {}
    with p.open() as fh:
        for r in csv.DictReader(fh):
            try:
                out[r["commodity"].strip().lower()] = {k: float(r[k]) for k in ("primary_to_retail", "retail_to_consumer", "consumer") if r.get(k)}
            except ValueError:
                continue
    return out


def decay_rate_prior(commodity: str | None, category: str | None = None,
                     distribution_weeks: float = 2.0) -> Prior:
    """Weekly decay share for a perishable at the distributor stage.

    With the ERS table cached: the primary-to-retail loss share for the
    commodity, spread over ``distribution_weeks`` (ASSUMED: two weeks from
    farm to shelf), i.e. rate = 1 - (1 - loss)^(1/weeks). Otherwise the
    category table above."""
    name = (commodity or "").strip().lower()
    tab = _lafa_table()
    if name and name in tab and "primary_to_retail" in tab[name]:
        loss = tab[name]["primary_to_retail"]
        rate = 1.0 - (1.0 - loss) ** (1.0 / max(distribution_weeks, 0.5))
        return Prior(round(rate, 4), "PUBLIC_BENCHMARK", f"USDA ERS LAFA primary-to-retail loss for {commodity}",
                     f"loss {loss:.1%} spread over {distribution_weeks} weeks (ASSUMED stage length)", _meta("ers_lafa_loss"))
    for key in (name, (category or "").strip().lower()):
        if key in CATEGORY_DECAY_PER_WEEK:
            return Prior(CATEGORY_DECAY_PER_WEEK[key], "ASSUMED", "category table (domain/priors.py)",
                         "conservative weekly shrink by category; replace with measured write-offs", None)
    return Prior(0.05, "ASSUMED", "no commodity or category match", "flat default 5%/week", None)


def priors_summary(products: dict, suppliers: dict) -> dict:
    """products: sku -> {commodity, category}; suppliers: id -> {origin_iso3}."""
    return {
        "decay": {j: decay_rate_prior(v.get("commodity"), v.get("category")).as_dict() for j, v in products.items()},
        "lead_time_cv": {s: lead_time_cv_prior(v.get("origin_iso3")).as_dict() for s, v in suppliers.items()},
    }
