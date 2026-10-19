# Walmart M5 dataset audit (second independent dataset)

Source. The archive `m5-forecasting-accuracy.zip` (48,009,163 bytes, sha256 `0349ba38a2efd30d0f5acc6394c1110e140e1a990c650d7b5ca44c5b25dd12f5`)
was downloaded by the repository owner from the Kaggle competition "M5 Forecasting - Accuracy" (data provider Walmart;
organiser the M Open Forecasting Center, University of Nicosia). Kaggle requires an account and acceptance of the
competition rules to download; the rules text could not be retrieved without a login from this environment, so the
use terms are not quoted here. The data are used only for internal research validation, the raw files are never
committed or redistributed, and any use beyond the competition's research terms needs the owner's confirmation
against the rules. No mirror and no synthetic substitute were used.

| file | bytes | sha256 |
|---|---|---|
| calendar.csv | 103,469 | `d12b5914ef03e66649adf5dd9e996e6602251c22b7a6af8f1f7e3aa12f8860f5` |
| sales_train_validation.csv | 120,007,726 | `f368e66ed1dbecb48b2cc8fc589bf68b3deddbbb36bf5c88b4d6d0a09b9b6724` |
| sales_train_evaluation.csv | 121,736,518 | `4b4a47c44c38380d2a9168216fea8c9ff2f31b1ddb772f8a0995952a038b8aa0` |
| sell_prices.csv | 203,395,785 | `9da3ad1f8b8ccacdbdc70612191dd375ec24a4ac6625c24b75b3bc60b0bed2ef` |
| sample_submission.csv | 5,228,786 | not used |

## Structure (computed from the files)

- **Series.** 30,490 store-item series = 3,049 items × 10 stores (CA_1..4, TX_1..3, WI_1..3; 3 states); 3 categories
  (FOODS 1,437 items, HOUSEHOLD 1,047, HOBBIES 565), 7 departments. Hierarchy: state > store; category > department >
  item. Identifiers are anonymised.
- **Observation period.** `sales_train_evaluation.csv` has 1,941 daily columns d_1..d_1941; d_1 = Saturday
  2011-01-29, d_1941 = 2016-05-22 (the calendar runs 28 days further, to 2016-06-19, for the competition's forecast
  horizon; the sales do not). `sales_train_validation.csv` has d_1..d_1913 and agrees with the evaluation file on
  every one of its 30,490 rows at d_1913; d_1914..d_1941 (2016-04-25..2016-05-22) are the competition's public
  evaluation labels. Daily resolution; Walmart weeks `wm_yr_wk` run Saturday to Friday (282 weeks in the calendar,
  277 full weeks inside the sales).
- **Quantities.** Unit sales (integers), 59,181,090 cells, min 0, max 763, no negatives, no nulls, no duplicate keys.
  Mean daily sales per series p10/p50/p90/p99 = 0.09 / 0.45 / 2.45 / 11.0 units. Zero-sale days p10/p50/p90 = 34 % /
  73 % / 93 % of a series' days. First sale day p10/p50/p90 = day 1 / 160 / 1,162 (many items enter later).
  784 series have no sale in the last 28 days of the data (candidate discontinuations). In the last 364 days,
  9,043 series average ≥ 1 unit a day with under 50 % zero days; 2,896 average ≥ 3; 7,810 are zero on ≥ 80 % of days.
- **Prices.** 6,841,121 weekly rows over 30,490 store-item pairs, weeks 11101..11621, price 0.01 to 107.32 (median
  3.47). No sale occurs on a day without a price row; 12,299,413 series-days (20.8 %) have no price row and are days
  before the item was listed, not zero demand.
- **Calendar.** 162 days carry a named event (30 names; 5 days carry two), and SNAP purchase days per state (650
  each). Weekday, month and year are present.

## Field classification for ZAAD

| ZAAD input | provenance | source |
|---|---|---|
| SKU, store identity | OBSERVED | `item_id`, `store_id` |
| Weekly demand history and settlement demand | OBSERVED unit sales (not demand) | daily `qty` summed per Walmart week |
| Selling price | OBSERVED | `sell_prices` for the origin's Walmart week |
| Unit cost | DERIVED | price × (1 − declared margin) |
| Calendar events, SNAP | OBSERVED | not supplied to the planner in Experiment A; strata only |
| Opening stock, lead time and spread, fill, holding, capital, salvage, shelf life, service target, order constraints | SYNTHETIC | `zaad/public/m5/declaration.py` |
| Purchase orders, receipts, supplier performance, inventory, costs, Walmart's replenishment | UNAVAILABLE | nothing of the kind is in the files |
| Stockout annotation | UNAVAILABLE | zeros cannot be told from stockouts or delistings |

## Limitations and leakage risks

- Sales are not demand and no stockout flag exists; every fill rate here is service against sales. A zero-sale
  week may be a stockout, a delisting or no demand; the selection excludes series with a run of 8 or more zero
  weeks and requires a price row every week, which removes delistings but not short stockouts.
- The public evaluation period d_1914..d_1941 is in the files. It was never used for selection or tuning; it enters
  only as settlement truth inside the horizons of the last reviews of the holdout window (origin 2016-01-02, 13 weekly
  reviews, 8-week horizon, truth through 2016-05-20). That is disclosed, not hidden.
- Prices change by week; using a later week's price at an earlier origin would be leakage. The builder uses the
  origin week's price (set at the week start) or the last earlier one, never a later one (tested).
- Selection features use only sales before the holdout origin; the price-row eligibility uses the catalogue through
  the truth end (listing is a fact about the product, not about sales); the test shows the holdout cannot move the
  selection.
- Items with intermittent sales are the majority of the dataset; the pilot restricts to series averaging ≥ 2 units a
  week so that weekly replenishment is a meaningful decision, and reports that restriction (16,624 eligible of 30,490).
- Walmart's own replenishment, promotions and supplier relationships are absent; the declared supply and economics
  are the pilot's assumptions and nothing here was observed at Walmart.

## Fitness for the intended test

M5 gives ZAAD what FreshRetailNet could not: five years of history (52-week fits with room for rolling origins),
weekly cadence matching the product's own planning period, dollar prices for cost and margin indices, and higher
volumes. It cannot give supplier evidence, cost evidence or demand under stockout, and its sales are a lower bound on
demand. Experiment A (single-SKU weekly replenishment) is supported on the dataset's own terms; Experiment B (coupled
purchasing under shared capacity, budget and lot rules) is supported only with explicitly synthetic coupling.
