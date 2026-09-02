# Indiana Validation: Settlement Correction

_2026-08-30. Supersedes the benchmark numbers in
`INDIANA_SYNTHETIC_VALIDATION.md`. That report's methodology disclosure was
correct and is what made this diagnosis possible; its conclusion was drawn
from a benchmark that could not express the mechanism under test._

## The defect

`score_commitment` computed `over = max(committed - demand, 0)`. Committed
kilograms were treated as delivered kilograms; no fill rate entered scoring
at any point. The module documented this ("realized supplier fills are not
replayed into the score") and judged it harmless because all policies were
scored identically.

Identical is not fair here. Only `two_sided_sp` receives `yield_scenarios`,
so only it inflates commitments to cover expected supplier shortfall. Under
commitment-equals-delivery scoring that inflation was charged as pure waste
at unit cost, and the shortfall it insured against never occurred. The
benchmark penalised hedging and never rewarded it.

## The correction

1. `{(supplier, product): kg}` allocations are preserved for SP and LP
   instead of being summed to product totals.
2. Supplier-blind policies (order-up-to, run-rate) are allocated pro rata
   by training-window delivered-volume share. **A stated modelling
   assumption**, applied identically to both so neither is advantaged.
3. Held-out supplier/week fills settle the decision. Suppliers absent that
   week fall back to their TRAINING-window mean, so the fallback carries no
   held-out information.
4. Every policy settles through one function, `settle()`.
5. `force_unit_fills=True` pins all fills to 1.0 for regression testing and
   **cannot open the commercial gate** — passing under assumed perfect
   delivery is not evidence.

## Regression check

With `force_unit_fills=True` the harness reproduces the pre-fix numbers
exactly (seed 11, 1.30x/0.30: vs LP -27.89%, vs naive -4.32%, vs
order-up-to +51.71%, service 100.0%). The refactor changed settlement and
nothing else.

The pre-fix grid below also reproduces the superseded report: median
-29.41% against its -29.21%, and an identical range of -41.70% to -5.83%.

## Results, all 30 regimes (5 seeds x 6 spot regimes, train_weeks=52)

| Metric | Pre-fix | Corrected |
|---|---:|---:|
| SP vs deterministic LP, median | **-29.41%** | **+13.46%** |
| SP vs LP, range | -41.70% to -5.83% | -11.95% to +18.28% |
| SP vs naive run-rate, median | n/a | +10.45% |
| Commercial gate passed | **0/30** | **25/30** |

### Where it still fails, and why that is coherent

All five failures occur in one regime: **spot at 1.15x with a 30% cap**,
meaning emergency coverage is both cheap and plentiful. When a shortfall
can be covered cheaply after the fact, paying upfront to hedge it is
wasted money. Insurance is worth least when the fallback is cheapest.

| Seed | vs LP @ 1.15x/0.30 |
|---|---:|
| 11 | -3.88% |
| 23 | +0.67% (fails on naive: -5.64%) |
| 42 | -1.03% |
| 67 | -11.95% |
| 101 | -3.33% |

Note this **reverses** the direction recorded in `PILOT_READINESS.md`,
where the SP won with cheap spot and lost with expensive spot. That earlier
result was produced under the same settlement defect. The corrected
direction is the economically sensible one: hedging supply risk pays when
the recourse channel is expensive or rationed, and does not pay when it is
cheap and abundant.

## Follow-up corrections (independent review)

Three issues found on independent review of PR #9, all fixed here:

1. **Zero-demand products escaped settlement.** `settle` iterated only
   products with positive realized demand, so a commitment to a product
   that sold nothing that week arrived, sold nothing, and was charged no
   waste. It does not move this grid, because the Indiana generator gives
   every product positive demand every week, but it would silently forgive
   overcommitment on intermittent real data. Settlement now iterates the
   union of demanded and delivered products.
2. **Even-sized median reported the upper middle value**, giving +13.53%
   where the conventional median is +13.46%. A reporting bug in
   `run_matrix`, not a model result. Now uses `statistics.median`.
3. **Language on correlation was wrong.** This harness draws each
   supplier's yields INDEPENDENTLY. It exercises marginal supplier-yield
   uncertainty; it does not exercise the correlated-shortfall model in
   `risk/correlated_scenarios.py`. Any claim that the Indiana result
   demonstrates value from modelling correlated supplier failure is
   unsupported by this benchmark.

## Standing limitations

- Synthetic data. Nothing here is validation on a real operator.
- The pro-rata supplier allocation for supplier-blind policies is an
  assumption, not an observation, and it affects their scores.
- 25/30, not 30/30. The gate requires beating both the LP and the naive
  baseline, and one spot regime defeats it consistently.
- Supplier yields are drawn independently here. The correlated-scenario
  layer is NOT under test in this benchmark.
- Absolute costs rose for every policy, as expected once free perfect
  delivery is no longer assumed.
