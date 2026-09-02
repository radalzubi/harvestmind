# Full Synthetic Simulation Sweep — Research

## Objective

Measure where HarvestMind's stochastic program (SP) adds value on synthetic
Indiana operator histories. This is a mechanism test, not customer validation
or a savings claim.

## Existing code paths reused

- `backtesting/benchmark_suite.py` is the single rolling-origin comparison and
  settlement path. PR #9 preserved supplier allocations and replays realized
  fills for every policy.
- `risk/correlated_scenarios.py` supplies Gaussian/t copula draws with exact
  Beta marginals and accepts Kendall's tau as the dependence target.
- `forecasting/demand/demand_forecast_service.py` routes a product to the
  Croston family when at least 60% of its weekly observations are zero.
- `forecasting/demand/intermittent_model.py` implements Croston, SBA and TSB.
- `synthetic/indiana_operator_sim.py` supplies the Indiana product, buyer and
  supplier operating frame.

## Defects and confounders identified before implementation

1. `scripts/validate_indiana_market.py` uses the upper middle observation for
   an even-sized sample. The sweep must use `statistics.median`, which averages
   the two middle values.
2. Settlement iterates only over products in realized demand. A commitment to
   a product with zero demand therefore escapes overage cost. The sweep must
   settle the union of realized and delivered products.
3. The benchmark's supplier yield draws are independent and local to the
   benchmark. Grid B.1 must call the existing copula implementation while
   deriving every marginal from the training window only.
4. The Indiana generator contains positive demand in every product-week and
   does not expose controlled mean fill. Both factors need explicit, recorded
   controls.
5. Supplier-blind policies require a constructed supplier allocation. The
   existing pro-rata training-volume rule is retained and disclosed.

## Method decisions

- Grid A is a 4 x 6 x 5 full factorial: controlled mean accepted fill,
  spot multiplier/capacity, and seed.
- Grid B changes one factor at a time from 0.85 fill, 1.30x spot cost and 30%
  spot capacity. Each level uses the same five seeds.
- Correlation means an explicit equicorrelated Gaussian-copula policy at
  Kendall tau 0.0, 0.3 or 0.6. Gaussian is deliberate here: at tau zero it
  gives true independence, isolating rank correlation without the t-copula's
  shared tail-mixing confounder. The target is applied to synthetic supplier-week
  outcomes and the SP scenario draws; diagnostics record the assumption.
- Intermittency inserts deterministic seeded zero-demand product-weeks and
  records Croston-route counts. Settlement still evaluates every committed
  product even when demand is zero.
- Cost asymmetry overrides underage cost as a multiple of overage cost for all
  optimization and settlement policies identically.
- `train_weeks=78` requires at least 90 weeks for 12 held-out folds; the runner
  automatically expands generated history to `train_weeks + folds`.
- A forced-unit-fill diagnostic cell is reported separately and is barred from
  opening the commercial gate.

## Primary references

- Python `statistics.median`: https://docs.python.org/3/library/statistics.html#statistics.median
- Demarta & McNeil (2005), *The t Copula and Related Copulas*:
  https://doi.org/10.1111/j.1751-5823.2005.tb00254.x
- Croston (1972), *Forecasting and Stock Control for Intermittent Demands*:
  https://doi.org/10.1057/jors.1972.50
- Lindskog, McNeil & Schmock, *Kendall's Tau for Elliptical Distributions*:
  https://urn.kb.se/resolve?urn=urn:nbn:se:kth:diva-130518
