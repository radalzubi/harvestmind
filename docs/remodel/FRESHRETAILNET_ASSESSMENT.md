# FreshRetailNet-50K as a validation dataset for ZAAD: audit and integration proposal

Status: assessment only (2026-10-19). No production code, optimizer mathematics, source tables or benchmarks were
changed or run. Every dataset figure below was computed from the two supplied Parquet files with DuckDB and
PyArrow; every ZAAD fact was read from `origin/main` at `91b9b7d` (the H3b merge). Third-party repositories were
used as references, not as ground truth. Nothing here is a measured customer saving.

## 1. Dataset audit

### 1.1 Files

| file | path found | bytes | SHA-256 | rows | columns | row groups | writer |
|---|---|---|---|---|---|---|---|
| train.parquet | `/Users/radalzubi/Downloads/train.parquet` | 106,436,287 | `6706832db892bbae4969c19d87e07975d2543d2ba7d7d4756360654785de5a3d` | 4,500,000 | 19 | 4,500 | parquet-cpp-arrow 17.0.0 |
| eval.parquet | `/Users/radalzubi/Downloads/eval.parquet` | 8,440,124 | `1b118840664280c6b88bffc84c80ee1f54c05d911e354b7599e5da10995e960e` | 350,000 | 19 | 350 | parquet-cpp-arrow 17.0.0 |

The expected repository location `data/external/freshretailnet/raw/` does not exist; the files were read from
`Downloads` and were not copied into the repository. Both carry a Hugging Face `features` schema in the Parquet
key-value metadata and no other provenance. The checksums above should be the fixed manifest for any later run.

### 1.2 Field inventory (identical schema in both files)

| field | type | documented meaning (dataset card / paper) | what the file shows |
|---|---|---|---|
| `city_id` | int64 | encoded city | 18 values; every store belongs to exactly one city; 290 of 898 stores are in city 0 |
| `store_id` | int64 | encoded store (paper: encrypted) | 898 values |
| `management_group_id` | int64 | top of the product hierarchy | 7 values; a store carries up to 7 groups (5,046 store×group pairs) |
| `first/second/third_category_id` | int64 | product hierarchy levels | 32 / 84 / 233 values; every product has exactly one category path |
| `product_id` | int64 | encoded SKU | 865 values (the paper's abstract says 863); median 10 stores per product, max 783 |
| `dt` | string | date | ISO date text, not a date type; train 2024-03-28 (Thu) to 2024-06-25 (Tue), 90 days; eval 2024-06-26 (Wed) to 2024-07-02 (Tue), 7 days |
| `sale_amount` | double | daily sales "after global normalization (multiplied by a specific coefficient)" | min 0, mean 0.9986, p50 0.7, p90 2.0, p99 5.8, max 44.9; 200,760 zero rows (4.5 %); 89.7 % of values are non-integer; equals the sum of `hours_sale` to 1.4e-14 on every row |
| `hours_sale` | list<double>[24] | hourly sales, same normalization | always 24 elements; night hours near zero, morning peak at indices 8 to 11 |
| `hours_stock_status` | list<int64>[24] | hourly out-of-stock status | always 24 elements, values {0,1}; **1 = out of stock** (only 2.5 % of all sales fall in hours flagged 1; the official baseline sets flagged hours to NaN) |
| `stock_hour6_22_cnt` | int32 | "number of out-of-stock hours between 6:00 and 22:00" | **equals the sum of flags at indices 6..21 (16 hours) on all 4,500,000 rows**; max is 16, never 17; mean 3.18 (train), 2.90 (eval) |
| `discount` | double | discount rate, 1.0 = none, 0.9 = 10 % off | 2,600 distinct values; 51.5 % of store-days < 1; 16,039 rows exactly 0; 34 rows > 1 (max 1.088) |
| `holiday_flag`, `activity_flag` | int32 | holiday / promotional activity indicators | holiday 34.4 % of rows, activity 37.8 %; all four combinations present |
| `precpt`, `avg_temperature`, `avg_humidity`, `avg_wind_level` | double | weather covariates, units undocumented | no nulls; temperature 12.1 to 30.9 (train), 26.4 to 32.3 (eval); precipitation 0 to 42.5 |

Not present in either file: price, cost, margin, inventory level, replenishment or delivery quantities, lead time,
supplier, shelf life, pack size, store location beyond the encoded city, or any unit of measure.

### 1.3 Structure and quality checks

- **Complete, duplicate-free panel.** 50,000 (store, product) series; every series has exactly 90 train days and 7
  eval days; zero duplicate (store, product, dt) keys; zero nulls in any key or list; no negative sales.
- **Split relationship.** The eval split is the 7 days immediately after the training window for the same 50,000
  series; zero series appear in only one split; zero (store, product, dt) rows overlap. The eval split carries full
  labels (`sale_amount`, hourly sales, stock flags) and is therefore a public 7-day forecasting horizon, not a
  hidden test set. The official SSA baseline confirms this (90-day encoder, 7-day horizon, split at 2024-06-26).
- **Internal consistency.** `sale_amount == sum(hours_sale)` everywhere; `stock_hour6_22_cnt == sum(status[6..21])`
  everywhere. The paper's text defines a status of 1 as "stock available"; the released files and the official
  code use 1 for out of stock. Treat the files and code as authoritative, and record this sign inversion.
- **Stockouts.** 44.3 % of training store-days have at least one out-of-stock hour in 06:00 to 21:59 (41.0 % in
  eval); the mean out-of-stock fraction of those 16 hours is 18.7 %, which matches the card's "approximately 20 %".
  The diurnal pattern is U-shaped: about 41 % of series are out of stock at midnight, under 6 % at 07:00 to 08:00
  (the paper's 06:00 restock), rising to 42 % by 22:00. Fully out-of-stock business days do not occur.
- **Censoring is material.** Mean observed daily sales are 0.98 on fully in-stock days, 1.35 on days with 1 to 4
  out-of-stock hours (popular items sell out), and 0.21 on days with 13 to 16 out-of-stock hours. A naive
  in-stock-hour-rate extrapolation adds 33.6 % to total observed sales; that figure is an upper bound because
  stockouts cluster in the evening after most demand has been served. Only 21,884 of 200,000 series-weeks in the
  last four full training weeks (10.9 %) are completely in stock, so an "uncensored" evaluation subset is small.
- **Scale and granularity.** Daily volumes are small and fractional (median series mean 0.66 per day; 13,143
  series average under 0.5 per day; 74 series have more than half their days at zero). Classified on daily
  series by the Syntetos-Boylan rule: 40,548 smooth, 7,888 erratic, 1,564 lumpy, 0 intermittent. Weekly
  aggregation gives 12 full Monday-to-Sunday weeks (2024-04-01 to 2024-06-23); weekly series means p10/p50/p90 are
  3.0 / 4.6 / 12.8 with a median coefficient of variation of 0.27 (p90 0.52).
- **Nonstationarity.** Weekly total sales rise from 290,886 (week of 1 April) to 411,008 (week of 17 June), a 41 %
  climb alongside mean temperature rising from 17.5 to 27.3 degrees; weekday effects are present (Sunday and
  Saturday highest). Twelve weeks of history contain a trend, not a seasonal cycle.
- **Continuity across the split.** Correlation of series mean sales between the last training week and the eval
  week is 0.977.
- **Data availability timestamps.** None. Rows carry a date only. For point-in-time use the knowledge rule must be
  declared: a day's sales and stock flags are knowable at the end of that day.
- **Anomalies to carry as flags.** 34 rows with discount above 1; 16,039 rows with discount exactly 0 (free or
  misrecorded); the 863 versus 865 product count; the undisclosed normalization coefficient.
- **License.** CC BY 4.0 (dataset card and paper), stated as fit for commercial and non-commercial use with
  attribution. Identifiers are pseudonymized and store identifiers encrypted. The operator is a 30-minute
  hyperlocal grocery delivery business whose "stores" are front warehouses restocked daily at 06:00.

### 1.4 What the official and independent references establish

- Official baseline (`frn-50k-baseline`): recovery models (TimesNet, SAITS, ImputeFormer, iTransformer, GPVAE,
  CSDI, DLinear) and forecasters (SSA, TFT, DLinear) with WAPE and WPE as daily averages, evaluated only on eval
  days with `stock_hour6_22_cnt == 0`. It uses hours 6..21 and treats flag 1 as out of stock.
- Paper (arXiv 2505.16319): recovery formula `d = y ⊙ s + d̂ ⊙ (1 − s)`; forecasting horizon 7 days; limitations
  named: the window misses seasonality, low-volume SKUs are hard to model.
- Independent repository (josephazar): Tobit and IMR demand recovery, LightGBM forecasts, Newsvendor policies with
  an invented cost structure; its own caveat is that its inventory result "is an observed-sales proxy under censored
  evaluation". It is a reference for method ideas only.

## 2. ZAAD architecture facts that govern integration

Read from `origin/main` (`91b9b7d`); the Desktop checkout is 34 commits behind and lacks the H2/H3 modules.

| constraint | where | value |
|---|---|---|
| Workspace adapter plans weekly only | `zaad/full/workspace.py:203` | `period_days != 7` is refused |
| Minimum demand history for the adapter | `workspace.py:52, 298` | `MIN_HISTORY_WEEKS = 16` (parameter `min_history_weeks`) |
| Minimum observations for the demand estimator | `zaad/full/forecast.py:76` | `estimate` raises below 16 consecutive zero-filled observations |
| Core contract periods | `zaad/full/contracts.py:482-484` | `period_days` 1..31, `horizon` 1..52, up to 5,000 SKUs, 100 locations |
| Opening inventory | `zaad/full/inventory_state.py` | a planned cell needs a count whose effective instant equals the origin and is knowable before it; otherwise NOT READY and the build refuses |
| Supplier fit | `workspace.py:131-165`, `uncertainty.py:24` | fitted only with 6 or more PO/receipt pairs; otherwise fill (0.95, 0.05), lead 14 days, sd 2 days, labelled CONFIGURED_ASSUMPTION |
| Economics defaults | `workspace.py:315-321, 437-451` | holding 8 % per year, cost of capital 10 %, salvage 0.8, margin 30 % when no price, shelf life 52 periods when absent, shortage rate = selling price + `sla_per_unmet` |
| Replay loop | `zaad/full/replay.py:108-392` | one truth World shared by all policies; each policy carries its own stock, pipeline, learned fill and liquidity; purchases become private POs with truth-drawn arrival and fill |
| Baseline policies | `zaad/full/replay.py:23-105`, `policies.py:149-159` | `incumbent`, `replace_sold`, `periodic:k`, `reorder_point`, `economic_lot`, `base_stock`, `order_up_to`, `deterministic`, `stochastic`, `robust`, `frozen_forecast`, production `gated_*` |
| Truth construction for an operator's own history | `zaad/full/historical.py:82-230` | demand MEASURED from orders, "recorded shortfalls do not reduce demand"; supply MEASURED / INFERRED / SIMULATED / ASSUMED |
| Historical replay scope | `historical.py:63-67, 596-620` | defaults 5 SKUs, 26 reviews, 1,200 s budget; needs 16 weeks before the first origin |
| Interactive plan caps | `api/routers/zaad_full.py:110-131` | 20 SKUs, horizon 12, scenarios 4; async jobs 200 SKUs, horizon 26, 1,800 s |
| Staging schema | migrations 013 to 030 | no stockout, availability or hourly column anywhere |
| Point-in-time tests | `tests/integration/test_historical_replay.py`, `test_workspace_temporal_contract.py`, `test_workspace_inventory_state.py`, `test_workspace_receipt_pit.py` | future rows leave requests byte-identical; knowledge time, not event time, decides inclusion |

Two consequences decide the design:

1. **Weekly periods are not viable.** Twelve full weeks of history is below both the adapter's 16-week floor and the
   estimator's 16-observation floor, and the floor cannot be met at any rolling origin inside the window. Relaxing
   either would change the modeling core, which is out of scope and would weaken a deliberate control.
2. **Daily periods are viable through the core contract.** `Request` accepts `period_days = 1`; 90 daily
   observations exceed the 16-observation floor with room for rolling origins (an origin on day 17 or later), and
   a daily period matches the data's operating tempo (06:00 restock, short shelf lives). The workspace adapter
   cannot be used for this, so a dataset-specific request builder is required.

## 3. Compatibility matrix

Provenance: OBSERVED (in the files), DERIVED (documented transformation of observed records), SYNTHETIC
(explicit modeling assumption), UNAVAILABLE.

| ZAAD input | contract field(s) | provenance | source and treatment |
|---|---|---|---|
| SKU and location identity | `SKU.id`, `Location.id`, `Service` per (store, product) | OBSERVED | `product_id` as SKU, `store_id` as location; one single-site instance per store (or per store×management group) |
| Demand history | `DemandObservation` per service, daily periods −N..−1 | OBSERVED (censored) | daily `sale_amount` knowable at end of day; zero-filled by construction (complete panel) |
| Uncensored demand | truth World demand / optional history variant | DERIVED | recovered demand from hourly sales and flags under a documented rule (for example in-stock-hour rate, or the paper's imputation); always labelled RECOVERED and run as a separate variant |
| Stockout annotation | none in `Request`; evaluation strata only | OBSERVED | `stock_hour6_22_cnt` and the hourly flags; no staging column exists, so they live in dataset-specific tables |
| Seasonality, calendar | `Calendar`, `Event` | OBSERVED (weekday, holiday flag); DERIVED (activity and discount as events with a multiplier estimated from history) | the planner's own estimator has no exogenous regressors; promotions enter only as `Event` multipliers, which must be fitted from the training window only |
| Weather | none | UNAVAILABLE to the planner | can be used in demand recovery and as an evaluation stratum |
| Opening inventory | `Stock` rows at review 0 | SYNTHETIC | declared cover of k days of mean demand at the first origin (as the public-data plan prescribes); later reviews carry settled stock |
| Supplier lead time and variability | `Source.lead_days`, `lead_sd_days`, `fill_mean`, `fill_sd` | SYNTHETIC | no deliveries exist; declare a small grid (lead 1 and 2 days, fill 1.0 and 0.9) held identical across policies and reported as a sensitivity axis |
| Purchase orders and receipts | `OpenPO`, shipment observations | UNAVAILABLE for the actual leg; SYNTHETIC inside the replay | no historical POs: the H3a comparator for the actual leg is `NONE`, claim class MODEL_COMPARISON; the replay's own purchases are simulated |
| MOQ, pack size, multiples | `Source.minimum`, `multiple`, `case_multiple` | UNAVAILABLE; set to 0 (continuous) | sales are fractional normalized units; any pack structure would be invented |
| Shelf life and waste | `SKU.shelf_life`, `terminal_value`, `disposal_fee`, `Stock.expires_in` | SYNTHETIC | the paper names short shelf lives but gives no numbers; declare by `first_category_id` class (for example 2, 4, 7, 14 days) and treat as a sensitivity axis; waste is then a modelled quantity, never an observed one |
| Unit economics | `Source.unit_price`, `SKU.asset_value`, `Service.selling_price`, holding rates | SYNTHETIC (relative) | no price or cost; the normalization coefficient is undisclosed, so costs can only be declared per normalized unit (for example cost 1, price 1.3, holding and shortage ratios); results are comparable across policies, not in currency |
| Shortage penalty and service target | `Service.target`, `sla_per_unmet` | SYNTHETIC | declared targets (0.90, 0.95, 0.98) as configured settings |
| Network replenishment and allocation | `Transfer`, multi-location `Request` | UNAVAILABLE | no lanes, no central warehouse quantities; cities could be modelled as a parent only by invention: out of scope |
| Risk preferences, stresses | `Stress` | SYNTHETIC | optional lead or fill stresses as declared scenarios |

What can be evaluated legitimately: the demand estimation and scenario machinery on real, censored, nonstationary
daily demand; the replenishment decision under declared supply at a daily tempo; the fill-versus-inventory frontier
across policies under identical information; stability of decisions; runtime. What requires explicitly synthetic
assumptions: everything on the supply side, opening stock, perishability and unit economics. What cannot be
established at all: supplier behaviour, actual purchasing cost, cash, multi-echelon value, customer outcomes, or
realized savings.

## 4. Integration architecture (smallest reliable method)

Reuse: `zaad.full.contracts.Request`, `zaad.full.planner.plan`, `zaad.full.replay.replay` and its baseline
policies, `zaad.full.settlement` and `zaad.full.evaluation` for the ledger, `zaad.full.worlds` for truth Worlds,
`comparator` for claim classes. Do not touch the workspace adapter, staging tables, intake routes or the optimizer.

1. **Dataset tables, outside the product's staging schema.** A loader reads both Parquet files into a dedicated
   DuckDB file (`data/external/freshretailnet/frn.duckdb`, git-ignored) as `frn_daily` (4.85 M rows, with a
   `split` column) and `frn_hourly` (108 M rows), plus a `frn_manifest` with the SHA-256 checksums above. Measured
   load: 0.6 s and 1.8 s respectively; 215 MB on disk; 1.7 GB peak memory. The source tables of operator vaults are
   never written.
2. **A request builder for daily periods.** `build_frn_request(conn, store_id, origin_day, *, horizon_days,
   history_days, supply_declaration, demand_variant)` returns a `Request` with `period_days = 1`, one `Location`
   per store, one `Service` and one synthetic `Source` per product, `DemandObservation` rows for the `history_days`
   before the origin (strictly before, by the end-of-day knowledge rule), `Stock` rows from the declared opening
   cover, and the declared economics. The builder is pure (no database writes) and deterministic; the supply and
   economics declaration is one checked-in JSON file with every assumption labelled SYNTHETIC.
3. **Truth Worlds from the panel.** For a window of W days after the origin, a `World` whose demand is the observed
   daily sales (variant OBSERVED) or the recovered demand (variant RECOVERED), and whose supply draws come from the
   declared source parameters with a fixed seed. Both variants are run; conclusions are reported for both.
4. **Replay per store.** `replay(initial, truth, reviews, method, rolling=True)` for each policy in a fixed list,
   with daily reviews (review every period) or weekly reviews (every seventh period), store by store. The planner
   runs as the `gated` method; baselines as named above. The H3b shadow comparison is not applicable (no operator
   plan exists) and the H3a comparator for the actual leg is `NONE`.
5. **Results store.** One JSONL row per (store, origin, policy, variant, seed) with the full per-review log, the
   ledger components, solver quality, wall time and any failure or abstention, written under
   `docs/remodel/evidence/frn/` (summaries) and a git-ignored raw directory; nothing is dropped.

Daily periods change the meaning of some defaults: horizon in days (7 to 14), lead times of 1 to 2 days, holding
and capital rates per day, shelf life in days. The builder must set these explicitly rather than inherit the
weekly defaults of the workspace adapter.

## 5. Proposed evaluation methodology

- **Rolling-origin design.** Origins every 7 days from day 31 (30 days of history, well above the 16-observation
  floor) to day 87 of the training window, plus day 91 (the eval boundary), giving 9 origins per store; each run
  settles W = 7 daily periods (or 14, as a horizon sensitivity). The public eval week is used only as the final
  settlement window; no parameter is tuned on it.
- **Policies under identical information.** `replace_sold`, `reorder_point`, `periodic:1` and `periodic:2`,
  `base_stock`, `order_up_to`, `deterministic`, `stochastic`, and the production `gated` planner; every policy sees
  the same history, the same declared supply and the same truth path, and keeps its own stock, open orders and
  learned fill through the replay loop (this is what `replay` already guarantees).
- **Measurements per run and aggregated across stores with block-bootstrap intervals** (the existing
  `_block_bootstrap_ci`): settled total cost and its components (purchase, carrying, shortage, disposal where
  shelf life is declared); average inventory and inventory per unit served; unmet units and unit fill against the
  configured target; periods with breaches; stockout exposure (periods at zero stock); purchase quantities and
  their period-to-period variability (decision stability); solver status, abstentions, fallbacks, wall time and
  memory; and the difference between the OBSERVED and RECOVERED demand variants for the same policy.
- **Stratification.** By observed stockout intensity of the series in the history window (the share of days with
  any out-of-stock hour), by volume class (smooth, erratic, lumpy), by category, by discount exposure, and by
  city. Report whether policy rankings hold within strata, not only in aggregate.
- **Sensitivity grid.** Lead 1 vs 2 days; fill 1.0 vs 0.9; opening cover 1, 2, 3 days; shelf life class; service
  target 0.90, 0.95, 0.98. Every cell is a declared assumption; a result that flips across cells is reported as
  such.
- **Temporal controls.** Knowledge rule: a day's sales and flags are known at 23:59:59 of that day; the request
  builder refuses any observation dated on or after the origin (the contract's `integrity` validator already
  rejects stamps after `as_of`); the truth World is built only from days after the origin; demand recovery models,
  event multipliers and any fitted parameter use training-window data strictly before each origin (rolling fit,
  not a global fit); the eval week never informs anything before day 91. Add the byte-identical perturbation test
  pattern from `test_historical_replay.py` to the builder: perturbing days on or after the origin must leave the
  request unchanged.
- **Censoring semantics.** OBSERVED demand understates true demand on stockout days; a policy that holds more
  stock will look worse on shortage than it is, and a policy that runs lean will look better than it is. The
  RECOVERED variant corrects direction, not magnitude, and its own error is unknown (the paper evaluates recovery
  only on artificially masked in-stock hours). Therefore: report both variants; report the fully in-stock subset
  (10.9 % of series-weeks) as the only censoring-free check; never state a single number as "the" service level;
  and never call a modelled cost difference a saving.

## 6. Scalability assessment

- **Ingestion and queries** are not a bottleneck (section 4, step 1). DuckDB answers a point-in-time read of one
  store in milliseconds; a weekly aggregation over 50,000 series takes 0.3 s.
- **Instance shape.** Stores carry a median of 50 products (p10 20, p90 98, max 164); 457 stores have 50 or more,
  83 have 100 or more. One `Request` per store (split by management group above about 100 products) stays within
  the contract's limits and the async job caps (200 SKUs). The core contract has no cap on `sources`.
- **Solver cost dominates.** No daily-period timing exists yet; the closest measurements on record are weekly
  plans of 50 products in about 158 s and 8 to 10 products in about 200 s on the production shared-CPU machine
  (these come from earlier release notes, not from this dataset). With 898 stores, 9 origins and one planner leg,
  about 8,100 planner solves are needed per demand variant and sensitivity cell; at 2 to 3 minutes each that is
  roughly 270 to 400 CPU-hours per cell, while the baselines cost seconds. Daily reviews instead of weekly multiply
  this by 7. The work is embarrassingly parallel across stores, so it is feasible on a multi-core machine or a
  small pool, and not on the Fly shared-CPU instance.
- **Staging.** Tier 1: 50 stores stratified by size and stockout intensity, one sensitivity cell, both variants
  (about 450 solves; a day of wall time on 8 cores). Tier 2: all 898 stores, weekly reviews, the central cell.
  Tier 3: the sensitivity grid and daily reviews only where Tier 2 shows the decision matters. Every tier keeps
  every instance's result, including abstentions and solver failures.
- **History sufficiency.** 90 days supports daily-period estimation (16-observation floor) with up to 59 days of
  rolling evaluation; it does not support the weekly adapter, the 52-week calibration the public-data plan assumed
  for M5, seasonal methods (the estimator enables `seasonal_naive` only at 68 observations), or any annual
  statement. Lead times beyond a few days leave too few settled periods to judge.
- **Reproducibility.** Fixed seeds per (store, origin, policy); the manifest checksums; the declaration file hash
  in every result row; the existing canonical-regression discipline (tie flips under solver changes are a known
  hazard) applies to any frozen result set.

## 7. Limitations and risks

- **Everything on the supply side is invented.** Lead time, fill, MOQ, costs, prices, holding rates, shelf life and
  opening stock are declarations. Any difference between policies is conditional on them. This dataset cannot
  validate supplier-reliability modelling, purchasing economics, cash or working-capital effects.
- **Normalized units.** The normalization coefficient is undisclosed; quantities are relative. Cost results are
  comparable only across policies within one declaration, never in currency and never as savings.
- **Censored demand truth.** The settlement's demand truth is itself censored or model-recovered. Fill rates
  against observed sales overstate service; recovered demand has unknown error. Only the fully in-stock subset is
  censoring-free, and it is small and biased toward slow sellers.
- **Operating model mismatch.** The data come from hyperlocal front warehouses restocked daily at 06:00 with
  30-minute delivery; ZAAD's product is built for weekly distributor replenishment. Daily periods fit the data but
  are an untested regime for the planner (period-dependent defaults, lead of one period, shelf lives of a few
  periods). Findings transfer to ZAAD's distributor customers only with that caveat stated.
- **Short, trending window.** Twelve weeks with a 41 % volume climb: no seasonality, no year-on-year, a trend that
  the estimator's change-point logic will be exercised by; the eval week is a single summer week.
- **Public ground truth.** The eval week is published; nothing can be tuned on it and the first run cannot claim
  blind validation.
- **No comparator from the operator.** There are no actual purchase orders, so H3a's ACTUAL_HISTORICAL_ACTION and
  H3b's shadow comparison are structurally absent; claim class is MODEL_COMPARISON for every leg.
- **Low volumes.** Median daily demand under one unit; the frontier is dominated by small-count effects, and pack
  constraints cannot be tested.

## 8. Implementation plan (for authorization; nothing below has been built)

1. `data/external/freshretailnet/` (git-ignored raw and DuckDB files) and `docs/remodel/evidence/frn/MANIFEST.json`
   with the two SHA-256 checksums, sizes and row counts above.
2. `zaad/public/__init__.py`, `zaad/public/freshretailnet/loader.py`: Parquet to `frn_daily`, `frn_hourly`,
   `frn_manifest`; verifies checksums; refuses a file that does not match the manifest.
3. `zaad/public/freshretailnet/declaration.py` and `docs/remodel/evidence/frn/SUPPLY_DECLARATION.json`: the
   synthetic supply, economics, shelf-life classes, opening cover, service targets and knowledge rule, each labelled
   SYNTHETIC or DECLARED, hashed into every result.
4. `zaad/public/freshretailnet/recovery.py`: the documented latent-demand recovery rule(s) fitted from data strictly
   before each origin, with a MASKED-hour self-test (the paper's protocol) reporting recovery error.
5. `zaad/public/freshretailnet/request_builder.py`: daily-period `Request` per store and origin (section 4, step
   2), pure and deterministic.
6. `zaad/public/freshretailnet/truth.py`: OBSERVED and RECOVERED truth Worlds with declared supply draws.
7. `scripts/frn_benchmark.py`: tiered, store-parallel rolling replay over the policy list, with per-instance JSONL,
   failure retention, seeds, and resumability; `scripts/frn_summarize.py`: strata, bootstrap intervals, sensitivity
   tables, no filtering of unfavourable cells.
8. Tests: `tests/unit/test_frn_loader.py` (checksums, schema, panel completeness, the two stockout invariants);
   `tests/unit/test_frn_request_builder.py` (16-observation floor, strict pre-origin history, byte-identical under
   future perturbation, declaration hash, no writes); `tests/unit/test_frn_recovery.py` (recovery never lowers
   demand below observed sales, masked-hour error reported); `tests/integration/test_frn_replay_small.py` (one
   store, three policies, two origins, both variants; state carried per policy; comparator NONE; claim class
   MODEL_COMPARISON; no realized-value permission).
9. Evidence: this file promoted to `docs/remodel/evidence/FRN_AUDIT.md` once the loader exists, and
   `docs/remodel/evidence/frn/RESULTS.md` written only from the retained JSONL.

No production module, migration, route or optimizer file is in that list. The workspace adapter and the
`stg_fmcg_*` tables remain untouched.

## 9. Recommendation

FreshRetailNet-50K is suitable as the first full-scale evaluation of ZAAD's demand-side and replenishment logic,
under three conditions: the integration runs on daily periods through the core contract (the weekly adapter
cannot accept 12 weeks of history, and that floor should not be relaxed); every supply-side and economic input is a
checked-in declaration treated as a sensitivity axis; and every result is reported for both the observed and the
recovered demand truth, with the fully in-stock subset as the only censoring-free check.

It genuinely challenges the optimizer where it is worth challenging: real, censored, trending, low-volume daily
demand across 50,000 series, with a 44 % stockout incidence that ZAAD's history pipeline currently treats as
unconstrained demand. It provides genuine evidence about forecast and scenario quality, about the fill-versus-
inventory trade-off across policies under identical information, and about runtime at scale. It provides no
evidence about suppliers, purchasing cost, cash, networks or realized savings, and it cannot, because none of that
is in the data. If the first run is framed as "model comparison on public demand under declared supply", with the
word "savings" absent, the dataset is the right first step. If the aim is to validate the supplier and cost side,
it is the wrong dataset and no public one will do.
