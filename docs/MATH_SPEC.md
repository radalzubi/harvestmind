# HarvestMind — Mathematical Specification

For external review. Every computation the engine performs, with the exact
formula, a one-line description, and the source file/function so it can be
checked against the code.

**Honesty notes for the reviewer**
- The diagnostic layer (§2–§8) is descriptive arithmetic: sums, ratios,
  thresholds. It is auditable, not "AI".
- The two pieces with genuine mathematical content are the **hierarchical
  supplier model (§9)** and the **two-stage stochastic optimizer (§13)**.
- Nothing here has been validated against a real operator's data yet. Figures
  in demos come from a synthetic generator calibrated to public benchmarks.
- Constants (thresholds, cost coefficients) are configurable defaults, flagged
  where they appear.

---

## 1. Notation and data model

Five flat input tables (`stg_*`). Relevant fields:

| Symbol | Meaning | Source field |
|---|---|---|
| `ord`, `del`, `acc`, `rej` | ordered / delivered / accepted / rejected quantity (a delivery) | `stg_supplier_deliveries` |
| `req`, `ful`, `sub` | requested / fulfilled / substituted quantity (an order line) | `stg_buyer_orders` |
| `p_sell` | sales price per unit | `stg_buyer_orders.sales_price` |
| `c_unit` | supplier unit cost | `stg_supplier_deliveries.unit_cost` |
| `q`, `q_com` | quantity on hand / committed (a lot) | `stg_inventory_lots` |
| `t_exp`, `t_arr` | expiration / arrival date (a lot) | `stg_inventory_lots` |
| `v_lost`, `q_lost` | estimated value / quantity lost (a waste event) | `stg_waste_adjustments` |
| `t0` | "as-of" date (analysis date) | parameter |

Indices: `i` supplier, `j` product, `b` buyer, `ℓ` lot, `ω` scenario.

---

## 2. Waste loss
*One line: the dollar value of product written off, valued per row by best
available basis.* — `dashboard/lib/diagnostic_metrics.py :: waste_loss_usd`

For each waste row `r` of product `j`:
```
value(r) = v_lost(r)                       if v_lost(r) present and > 0
         = q_lost(r) · c̄_unit(j)           else if c̄_unit(j) known
         = 0  (counted in n_unvalued)       otherwise

c̄_unit(j) = mean of unit_cost over deliveries of product j (cost basis, not price)

WasteLoss = Σ_r value(r)
```

---

## 3. Shortage loss
*One line: revenue at risk from order quantities that were not fulfilled.* —
`diagnostic_metrics.py :: shortage_loss_usd`

For each order line `o` of product `j`:
```
missed(o) = max( req(o) − ful(o) − sub(o), 0 )      (substitutions count as filled)
price(o)  = p_sell(o)                 if present and > 0
          = p̄_sell(j)                 else            (avg sales price for product j)
          = 0  (counted in n_unvalued) otherwise
loss(o)   = missed(o) · price(o)

ShortageLoss = Σ_o loss(o)
```

---

## 4. Supplier reliability (deterministic scorecard)
*One line: each supplier's headline fill and rejection rates with risk tiers.*
— `diagnostic_metrics.py :: supplier_reliability_scores`

Per supplier `i`:
```
fill_rate(i)      = min( Σ acc(i) / Σ ord(i), 1 )      (acc falls back to del if acc all-null)
rejection_rate(i) = Σ rej(i) / Σ del(i)

risk(i) = High     if fill_rate < 0.80
        = Medium   if fill_rate < 0.90
        = Low       otherwise
        = Unknown  if Σ ord(i) = 0   (excluded from the risky count)
```
Thresholds 0.80 / 0.90 are configurable.

---

## 5. Buyer fulfillment
*One line: how reliably each buyer's orders get filled, split into filled /
substituted / missed.* — `diagnostic_metrics.py :: buyer_fulfillment_rates`

Per buyer `b`:
```
fulfillment_rate(b)  = Σ ful(b) / Σ req(b)
substitution_rate(b) = Σ sub(b) / Σ req(b)
missed_rate(b)       = Σ max(req−ful−sub, 0) / Σ req(b)
risk(b) = High if fulfillment_rate < 0.90
```
The three rates sum to ≈ 1 (identity check used in tests).

---

## 6. Traceability completeness (FSMA-204 readiness)
*One line: fraction of inventory lots carrying all required trace fields.* —
`diagnostic_metrics.py :: traceability_coverage`

A lot `ℓ` is **complete** iff all six fields are present and non-empty:
`{lot_id, product_id, supplier_id, arrival_date, quantity_on_hand, unit}`.
```
completeness = (# complete lots) / (# total lots)
```

---

## 7. Available-to-Promise (ATP)
*One line: how much of each product is genuinely safe to promise after
removing expired, committed, and near-expiry stock.* —
`diagnostic_metrics.py :: atp_by_product`

Let `D = 3` days (near-expiry window, configurable). Per product `j`, summing
over its lots:
```
on_hand     = Σ q
expired     = Σ q   over lots with t_exp < t0
near_expiry = Σ q   over lots with t0 ≤ t_exp ≤ t0 + D
committed   = Σ q_com
usable      = max( on_hand − expired, 0 )
ATP         = max( usable − committed − near_expiry, 0 )
near_expiry_pct = near_expiry / on_hand

risk(j) = High   if ATP ≤ 0 or near_expiry_pct > 0.20
        = Medium if near_expiry_pct > 0.10
        = Low     otherwise
```
A lot is counted in at most one of {expired, near_expiry} (expired test first).

---

## 8. Annualized savings estimate
*One line: scales the period's losses to a year and applies a literature
recovery band.* — `diagnostic_metrics.py :: estimated_annual_savings`

```
period_days = max( span_of_data, 7 )      span = (max date − min date)+1 across
                                          orders, deliveries, waste; fallback 90
factor      = 365 / period_days
period_loss = WasteLoss + ShortageLoss
annual_loss = period_loss · factor
savings_low  = annual_loss · 0.15
savings_high = annual_loss · 0.30
```
The 15–30% band is an assumption sourced from USDA SR-77 benchmarks, **not**
measured. The clamp `≥ 7` prevents absurd extrapolation from tiny windows.

---

## 9. Hierarchical supplier fill-rate distribution  ★ (statistical core)
*One line: an empirical-Bayes Beta–Binomial model of the distribution of a
supplier's NEXT-delivery fill rate, capturing both estimation uncertainty and
delivery-to-delivery volatility.* — `risk/supplier_distribution.py`

**Per-delivery observation.** For delivery `k` of supplier `i`:
```
fr_k = clip( acc_k / ord_k , 0, 1 )     (deliveries with ord_k > 0 only)
```

**Population (empirical-Bayes hyperparameters), over all deliveries / suppliers:**
```
m0  = mean(fr)                          pooled mean, clipped to [ε, 1−ε]
v0  = max( var(fr; ddof=0), φ )          pooled variance, floored at φ = 4e-4
τ²  = var( {mean_i} ; ddof=1 )           between-supplier variance of supplier means
σ²  = max( mean_i[ var_i(fr; ddof=0) ], φ )   typical within-supplier variance
κ   = σ² / τ²                            shrinkage strength (pseudo-deliveries)
```
Fallback: if `< 2` suppliers or `τ² ≤ ε`, set `κ = 4.0` (`_FALLBACK_KAPPA`).

**Per-supplier predictive distribution.** Supplier `i` with `n` deliveries,
sample mean `m_i`, sample variance `v_i (ddof=0, defined for n ≥ 2)`:
```
Mean (James–Stein shrinkage toward population):
    μ_i = (κ · m0 + n · m_i) / (κ + n)

Variance (tiered by data sufficiency):
    v_eff = max(v_i, φ)     if n ≥ 3            (trust own volatility)
          = σ²              if 1 ≤ n < 3        (borrow typical within-variance)
          = v0  with μ_i = m0   if n = 0        (cold start = population prior)

Beta(α_i, β_i) by method of moments from (μ_i, v_eff):
    c   = μ_i(1 − μ_i) / v_eff − 1            (concentration; clamped ≥ ε)
    α_i = μ_i · c
    β_i = (1 − μ_i) · c

Downside quantile used by the optimizer / commitment logic:
    downside_i = F⁻¹_Beta(0.10 ; α_i, β_i)   (10th percentile, scipy.stats.beta.ppf)

Reported shrinkage weight:  κ / (κ + n)
Volatility spread:          μ_i − downside_i
risk(i) = High if μ_i < 0.80 ; Medium if μ_i < 0.90 or spread ≥ 0.15 ; else Low
```

**Reviewer note.** This is empirical Bayes (hyperparameters point-estimated by
method of moments), not full Bayesian inference. Chosen deliberately for thin
data (3–8 deliveries/supplier) and millisecond runtime. The model is two-level
(suppliers within one operator); a third level (operators within a global
prior) is the intended extension and the basis of the cross-operator data moat.
The central claim under review: at equal mean, a higher within-supplier
variance `v_i` yields a wider Beta and thus a lower `downside_i` — i.e. the
model holds back more from volatile suppliers. ε = 1e-6, φ = 4e-4.

---

## 10. Shelf-life usability weight
*One line: how much of a lot is committable for a delivery, given how close it
is to expiry relative to the delivery date.* — `risk/shelf_life.py`

For a lot with remaining shelf life `R = (t_exp − t0)` days, delivery lead time
`L`, and category buffer `B`:
```
w(R; L, B) = 0              if R ≤ L                 (expired before delivery)
           = (R − L) / B    if L < R < L + B          (inside the buffer; linear ramp)
           = 1              if R ≥ L + B              (safe)
           = 1              if B ≤ 0 and R > L         (no buffer requirement)

weighted_available(j) = Σ_ℓ  q_ℓ · w(R_ℓ; L, B_cat(ℓ))
```
`B_cat` is a per-category buffer (e.g. Leafy Greens 4, Berries 3, Roots 14,
default 5 days). The shipped binary ATP rule (§7) is the special case `L=0`,
hard step at 3 days.

---

## 11. Safe-commit recommendation
*One line: the quantity safe to promise = shelf-life-weighted stock minus
commitments, scaled down by a volatility-aware holdback.* —
`risk/safe_commit.py`

Per product `j`, using `weighted_available(j)` (§10) and `downside(i*)` (§9)
for its worst supplier `i*`, and the product's buyer fulfillment rate:
```
net_available = max( weighted_available − committed, 0 )

holdback_frac = 0.15        if downside(i*) < 0.80
              = 0.08        elif downside(i*) < 0.90
              + 0.05        if buyer_fulfillment < 0.90

safe_commit = net_available · (1 − holdback_frac)
holdback_kg = net_available − safe_commit
```
Holdback coefficients 0.15 / 0.08 / 0.05 are configurable. Note this uses the
distribution's **downside**, not the mean — the volatility linkage.

---

## 12. Scenario generation (optimizer inputs)
*One line: turns operator history into the demand scenarios and
confidence-discounted supply capacity the optimizer needs.* —
`risk/scenario_generation.py`

```
Demand scenarios:  one scenario ω per distinct buyer delivery date,
                   equal weight 1/N,  d_jω = Σ req on that date for product j.

Supply capacity:   Y_ij = ord̄_ij · downside_i
                   ord̄_ij = avg ordered for supplier i, product j
                   downside_i from §9 (the confidence-calibrated fill rate)
Price:             c_ij = avg unit_cost for supplier i, product j
```

---

## 13. Two-stage stochastic optimizer  ★ (optimization core)
*One line: choose how much to commit to each supplier now (before demand is
known) to minimize expected total cost of commitments + spot buys + waste +
unmet, across demand scenarios.* — `optimization/two_stage_sp.py`
(Sample Average Approximation, solved with HiGHS via Pyomo.)

**Decision variables**
```
x_ij ≥ 0        Stage 1 (here-and-now): commit volume, supplier i → product j
s_jω ≥ 0        Stage 2 recourse per scenario ω: spot purchase of product j
w_jω ≥ 0        Stage 2: waste (over-supply) of product j
u_jω ≥ 0        Stage 2: unmet demand of product j
```

**Objective (minimize)**
```
min   Σ_ij c_ij · x_ij
    + (1/N) Σ_ω [  Σ_j (m · p̄_j) · s_jω        (spot at premium)
                 + Σ_j  c_w     · w_jω          (waste penalty)
                 + Σ_j  c_u     · u_jω ]        (unmet-demand penalty)
```
with scenario weights (1/N); defaults `m = 1.30` (spot premium),
`c_w = 0.50` $/kg (waste), `c_u = 2.50` $/kg (lost sale); `p̄_j` = avg price.

**Constraints**
```
Σ_i x_ij + s_jω − w_jω + u_jω = d_jω      ∀ j, ω      (demand balance per scenario)
x_ij ≤ Y_ij                                ∀ i, j      (supply capacity, §12)
x_ij , s_jω , w_jω , u_jω ≥ 0
optional:  s_jω ≤ ρ · d_jω                              (spot rationing, if set)
```

**Reviewer notes / known limitations**
- Supply uncertainty currently enters **only** through the deterministic
  capacity `Y_ij = ord̄·downside` (a conservative point estimate). Yield is
  **not** yet a per-scenario random variable in Stage 2. Making realized fill
  rate a second stochastic dimension (so commitments are made before *both*
  demand and supply resolve) is the primary intended extension.
- Weather and routing/logistics are not modeled. Weather would shift the
  per-product yield distribution; routing would add transport cost + capacity.
- Horizon: this is in-season procurement. The pre-season planting version
  (decide grower plantings before inventory exists) uses the same two-stage
  framework over a seasonal horizon and is not yet implemented.

---

## 14. Backtest — policy comparison
*One line: estimates how much realized loss the new (distribution + shelf-life)
policy's extra conservatism would have avoided, bounded so it cannot
overclaim.* — `backtesting/policy_comparison.py`

Per product `j`:
```
Δ_j        = safe_commit_old(j) − safe_commit_new(j)    (extra conservatism, kg)
realized_j = waste_kg(j) + shortage_kg(j)               (what actually went wrong)
covered_j  = min( Δ_j / realized_j , 1 )   if Δ_j > 0 and realized_j > 0,  else 0
avoided$_j = realized$_j · covered_j

Total avoided  = Σ_j avoided$_j
Reduction %    = Total avoided / Total realized$
```
The cap `min(·, 1)` is the honesty guard: you cannot avoid more than the loss
that actually occurred. Single-window form; the time-validated version runs
each policy through `backtesting/rolling_origin_engine.py` (decision at `t`,
scored on `t+1` outcomes, with lookahead protection).

---

## 15. Parameter reference (all configurable defaults)

| Symbol | Value | Where | Meaning |
|---|---|---|---|
| Near-expiry window `D` | 3 days | §7 | flag stock expiring within D |
| Supplier risk tiers | 0.80 / 0.90 | §4, §9 | High / Medium fill-rate cutoffs |
| Buyer risk tier | 0.90 | §5 | High fulfilment cutoff |
| ATP near-expiry risk | 0.20 / 0.10 | §7 | High / Medium near-expiry share |
| Savings band | 0.15 / 0.30 | §8 | USDA SR-77 recovery range |
| Period clamp | 7 days | §8 | min window for annualization |
| Downside quantile | 0.10 | §9 | lower-tail fill rate for safe commit |
| Variance floor `φ` | 4e-4 | §9 | Beta variance floor |
| Fallback `κ` | 4.0 | §9 | shrinkage when between-variance unknown |
| Own-variance threshold | 3 deliveries | §9 | trust own volatility above this |
| Category buffers `B` | 3–14 days | §10 | per-category shelf-life safety buffer |
| Holdback coeffs | 0.15 / 0.08 / 0.05 | §11 | supplier / supplier / buyer holdback |
| Spot premium `m` | 1.30 | §13 | spot price multiplier |
| Waste penalty `c_w` | 0.50 $/kg | §13 | Stage-2 waste cost |
| Unmet penalty `c_u` | 2.50 $/kg | §13 | Stage-2 lost-sale cost |

---

## 16. What a reviewer should scrutinize

1. **§9** — is empirical-Bayes method-of-moments the right estimator at
   n = 3–8 deliveries, versus a distribution-free robust set or a fully Bayesian
   posterior? Is the tiered-variance rule (own vs. borrowed) defensible?
2. **§13** — is the deterministic-capacity treatment of supply acceptable, or
   does the conclusion require yield as a Stage-2 recourse? What changes if it
   is added?
3. **§8 and §14** — the 15–30% band (assumed) vs. the backtest (measured but
   weak on synthetic data). Which should anchor a value claim, and under what
   conditions does the backtest become trustworthy?
4. **Cost coefficients (§13)** — `m`, `c_w`, `c_u` drive the optimizer's
   answer; how should they be elicited from a real operator rather than set as
   defaults?

---
## 17. Probabilistic demand forecast  ★
*One line: quantile forecasts with distribution-free calibrated coverage.*
— `forecasting/supply_uncertainty/quantile_model.py`, `conformal.py`

**Base model.** Gradient-boosted quantile regression (LightGBM) fitted
globally across SKUs at several levels, with **Croston's method** routing
intermittent series where boosting on mostly-zero data degrades. Predicted
quantiles are not guaranteed monotone, so crossing is repaired by **monotone
rearrangement** (Chernozhukov, Fernandez-Val & Galichon 2010): sort the
predicted quantile vector. Sorting is a projection that weakly improves any
proper loss, so it never hurts.

**Calibration (Conformalized Quantile Regression, Romano, Patterson &
Candes 2019).** Given a calibration set held out CHRONOLOGICALLY, define the
conformity score of observation `i` against its predicted interval:
```
E_i = max( q_lo(x_i) - y_i ,  y_i - q_hi(x_i) )
```
`E_i > 0` when `y_i` falls outside, `E_i < 0` when strictly inside (so a
negative correction TIGHTENS). The calibrated interval is
```
k  = ceil( (n + 1)(1 - alpha) )
Q  = k-th order statistic of {E_1..E_n}     (+inf if k > n)
C(x) = [ q_lo(x) - Q ,  q_hi(x) + Q ]
```
Under exchangeability this gives **finite-sample marginal coverage**
`P(y in C(x)) >= 1 - alpha`, with no assumption on the model or the
data-generating process.

**Refusal.** Coverage `1 - alpha` is unattainable when `k > n`, i.e. when
```
n < ceil(1 / alpha) - 1        (min_calibration_size)
```
The calibrator then returns `+inf` rather than a finite interval. Reporting
a narrow interval it cannot justify would be the worse failure.

**Mondrian variant.** Group-conditional calibration computes a separate `Q`
per group (e.g. product family), giving coverage WITHIN groups rather than
only on average across them — marginal coverage can hide a group that is
badly under-covered.

---

## 18. Supplier dependence: copulas  ★ (why VSS was ~0 without it)
*One line: suppliers sharing a weather region fail together, and pricing that
dependence is what makes stochastic modelling worth doing.*
— `risk/correlated_scenarios.py`

**Motivation.** §9 gives each supplier a marginal fill-rate distribution.
Marginals do not determine a joint distribution. Sampling suppliers
INDEPENDENTLY understated aggregate supply variance so severely that the
value of the stochastic solution (§20) fell to approximately zero: the model
concluded uncertainty was not worth modelling. Aggregate supply SD roughly
DOUBLED once dependence was included.

**Sklar's theorem.** Any joint `F` decomposes as
`F(y_1..y_d) = C(F_1(y_1), .., F_d(y_d))` for a copula `C`. So dependence can
be fitted separately from the marginals, and the Beta marginals of §9 are
preserved exactly by the probability integral transform.

**Rank correlation to latent parameter.** Estimate **Kendall's tau** on
overlapping delivery history, then map to the latent elliptical correlation:
```
rho = sin( pi * tau / 2 )          exact for the WHOLE elliptical family
                                   (Gaussian and t at any df)
tau = (2 / pi) * arcsin(rho)       inverse
```
Kendall is used rather than Spearman deliberately. The Spearman identity
`rho = 2 sin(pi * rho_s / 6)` is **Gaussian-only**; it is implemented and
documented as such, but is not on the production path. Passing a rank
correlation directly in as a latent parameter is a scale error this module
made once and now guards against.

**Regularization.** Short, unequal, partly-overlapping histories give noisy
and frequently indefinite matrices. Applied in order, each recorded in
diagnostics:
1. Ledoit-Wolf style shrinkage toward an equicorrelated target, weight
   `w = clip(params / (params + n_periods), 0.1, 0.9)`
2. `validate_correlation_matrix` — square, finite, unit diagonal, symmetric,
   entries in [-1, 1], min eigenvalue >= -tol. It REPORTS, never repairs.
3. `nearest_positive_semidefinite` — eigenvalue clipping, then rescale to
   unit diagonal. Repair is always a recorded decision, never silent.
4. Cholesky factorization for sampling.

**Choice of copula.** Gaussian and Student-t are both offered. A Gaussian
copula has **zero tail dependence** (Demarta & McNeil 2005): it assumes
suppliers never fail together in the extreme, which is the exact scenario the
model exists to price. `t` with low `df` is the tail-aware option. `df` is a
JUDGEMENT parameter (default 5.0), not estimated.

**Fail-closed sufficiency gate.** `_estimation_refusal` refuses to call a
matrix "estimated" unless genuine PAIRWISE overlap supports it: enough joint
periods, enough share of pairs clearing `min_overlap`, and a connected
overlap graph. Two suppliers with 30 observations each but no shared weeks
carry no information about their dependence. On refusal the default is to
RAISE; independent fallback happens only when the policy sets
`on_failure="independent"`, and is then recorded as `fallback_applied`.
Infrastructure faults (`ScenarioDataError`) are never governed by
`on_failure`.

---

## 19. Forecast scoring (proper scoring rules)
*One line: score distributions honestly, so a confident wrong model cannot win.*
— `forecasting/supply_uncertainty/evaluation.py`

```
pinball_tau(y, q) = tau * (y - q)      if y >= q
                  = (1 - tau) * (q - y) otherwise

WIS  = 1/(K + 1/2) * [ 1/2 |y - median| + sum_k (alpha_k / 2) * IS_k ]
                                          (Bracher et al. 2021)

CRPS (fair, ensemble of size M):
     = (1/M) sum_i |x_i - y|  -  (1 / (2 M (M - 1))) sum_i sum_j |x_i - x_j|
```
The `2M(M-1)` normalization is the **unbiased** form: the naive `2M^2`
denominator is biased in ensemble size and rewards larger ensembles
artificially. PIT values `F(y)` are uniform under perfect calibration; a
U-shaped histogram means intervals are too narrow, a dome means too wide.

---

## 20. Value of the Stochastic Solution (out of sample)  ★
*One line: prove the stochastic layer earned its complexity, or report that
it did not.* — `optimization/vss_evaluation.py`

```
VSS = EEV - RP          (Birge & Louveaux, Ch. 4)
      WS <= RP <= EEV   in expectation, so VSS >= 0 IN SAMPLE
```
`RP` is the recourse-problem cost; `EEV` fixes the first stage at the
mean-value solution and evaluates it under the true scenario distribution.

**Out-of-sample protocol.** Scenarios are split. RP and the mean-value
problem are trained on TRAIN ONLY, then both first stages are evaluated on
the SAME held-out scenarios via `solve_with_fixed_first_stage`. Bootstrap
over the evaluation set gives a confidence interval, and the verdict is one
of three MUTUALLY EXCLUSIVE states:
```
beneficial    ci_low  > 0
harmful       ci_high < 0
inconclusive  ci_low <= 0 <= ci_high
```
`VSS >= 0` is an IN-SAMPLE property. Out of sample it can be genuinely
negative, and it has been observed negative at symmetric costs. A two-state
classification would hide that, so it is not used. Non-uniform scenario
weights are REFUSED (`NonUniformWeightsUnsupported`) rather than silently
averaged over the wrong measure.

**Standing honest finding.** Against a deterministic LP the advantage is
contingent on spot economics: about +11% when emergency coverage is cheap and
capped at 30% of demand, about -4% when expensive and capped at 15%. Against
naive and order-up-to policies it wins everywhere tested. This is surfaced in
the product, not buried.

---

## 21. Multi-period stochastic program with random lead times  ★

Implemented in `optimization/multi_period_sp.py` (`MultiPeriodStochasticLP`).
The single-period model of §13 has no time index and therefore cannot
recommend ordering *earlier*; this model can.

**Sets.** suppliers $i \in I$, products $j \in J$, periods $t \in T=\{0,\dots,H-1\}$,
scenarios $\omega \in \Omega$ with weights $p_\omega \ge 0$, $\sum_\omega p_\omega = 1$
(completed and renormalised by `_normalized_weights`).

**Scenario data.** demand $d_{jt\omega}$; lead time $L_{i\omega} \in \mathbb{Z}_{\ge 0}$;
fill $f_{i\omega} \in [0,1]$; per-period supplier capacity $Y_{ij}$; opening
stock $I_{j,-1}$.

**First stage (here-and-now).** ordering schedule $x_{ijt} \ge 0$, committed
before any $\omega$ resolves. It carries no scenario index; this is the
information-timing constraint and is asserted by
`test_first_stage_is_scenario_invariant`.

**Second stage (per $\omega$).** inventory $I_{jt\omega}$, spot $s_{jt\omega}$,
unmet $u_{jt\omega}$, waste $w_{jt\omega}$, all $\ge 0$.

**Arrivals.** $A_{jt\omega} = \sum_i f_{i\omega}\, x_{ij,\,t-L_{i\omega}}$ for $0 \le t-L_{i\omega} < H$,
else 0. An order placed at $t$ lands at $t+L_{i\omega}$; the yield multiplier
enters here and nowhere else (`test_balance_holds_per_scenario_with_yield_applied_exactly_once`).

**Balance.** $I_{jt\omega} = I_{j,t-1,\omega} + A_{jt\omega} + s_{jt\omega} - (d_{jt\omega}-u_{jt\omega}) - w_{jt\omega}$.

**Decay.** $w_{jt\omega} \ge \delta_j\, I_{j,t-1,\omega}$: carried perishable stock
spoils; $\delta_j = 0$ for shelf-stable goods.

**Bounds.** $u_{jt\omega} \le d_{jt\omega}$; $x_{ijt} \le Y_{ij}$;
$s_{jt\omega} \le \rho\, d_{jt\omega}$ when a spot ration $\rho$ is set;
$\sum_j I_{jt\omega} \le \bar I$ when a warehouse capacity is set.

**Objective.**
$$\min \sum_\omega p_\omega \sum_{j,t}\Big[ \bar c_j(\mu-1)\, s_{jt\omega} + c^w_j w_{jt\omega} + c^u_j u_{jt\omega} + c^h_j I_{jt\omega} \Big]$$
with spot premium $\mu \ge 1$ on the average contract price $\bar c_j$, disposal
$c^w_j$, lost margin $c^u_j$, and holding $c^h_j$ per unit per period.
Procurement cost of committed-and-sold units is not charged (newsvendor
recourse economics, §13); consequently **disposal must be priced at unit
cost or the model buys freely and dumps** — this was a live defect and is
guarded by `test_free_disposal_exploit_is_closed`.

**Complete recourse.** Because $u$ and $w$ are unbounded slacks, every valid
input is feasible; an `infeasible` status can only come from a caller bug
(`test_complete_recourse_means_always_feasible`).

**Effective underage cost.** With spot available, the cost of being short is
$\min(c^u_j,\ \bar c_j(\mu-1))$, and the critical fractile falls accordingly.
This is correct economics, not a bug; a reviewer expecting the textbook
newsvendor quantity must set $\rho=0$.

## 22. Discrete ordering (FMCG)  ★

For a product with a `PackSpec` (lot size $q_j$ in base units, minimum
$m_j$, maximum $M_j$):

$$x_{ijt} = q_j\, n_{ijt},\quad n_{ijt} \in \mathbb{Z}_{\ge 0},\qquad
n_{ijt} \le \lceil Y_{ij}/q_j \rceil\, y_{ijt},\quad y_{ijt} \in \{0,1\},$$
$$x_{ijt} \ge m_j\, y_{ijt},\qquad x_{ijt} \le M_j .$$

The big-M is the lot count that fills capacity, so it is tight. Products
without a spec stay continuous, and a spec on one product leaves every
other product's schedule identical (`test_continuous_products_unaffected_by_other_products_specs`).
The model is then a MILP solved by HiGHS to `mip_rel_gap`; the returned
`gap` and `status` say whether optimality was proven.

`PackSpec` rounds an MOQ that is not a whole lot up to one at construction,
so the optimizer never sees an unsatisfiable minimum. Heuristic policies
use `round_to_pack`, which rounds **up** (a short order is an unpriced
shortage) and applies the MOQ only when ordering at all.

## 23. Solver outcome vocabulary

`optimization/solve_status.py`. `optimal` (proven, or within gap),
`feasible` (time limit with an incumbent; carries a warning),
`infeasible`, `unbounded`, `timeout` (no incumbent), `error`. Only the
first two are `usable`; an unusable outcome returns **empty** decisions,
never zeros, because "commit nothing" is a real recommendation and must
not be confused with "could not solve".

## 24. Domain policy

`domain/model.py`. The engine is domain-blind; a `DomainPolicy` supplies
$\delta_j$, the pack specs, the `CostConfig` (which cost terms are live and
in what currency — one run, one currency), the `ServiceTarget` with its
metric named (`unit_fill` is the one the LP enforces in expectation),
whether supply uncertainty is a *yield* on a commitment (produce) or a
*fill* of an order (FMCG), and whether lots are FEFO (enforced in
settlement, since the LP tracks product totals).

| | agriculture (perishable) | FMCG |
|---|---|---|
| base unit | kg | each / case |
| $\delta_j$ | $> 0$ | 0 |
| ordering | continuous | whole cases / pallets, MOQ |
| supply uncertainty | yield, single harvest | fill and lead time |
| what over-buying costs | spoilage | capital |

## 25. Policy selection by backtest

`backtesting/counterfactual.py::policy_selected`. The stochastic model's
edge over its point-forecast twin is conditional: positive when supply or
demand bind, negative in an easy regime where insurance is never used.
The selected mode runs both on a fold built **inside the training window**
(the last $h$ training periods as truth) and deploys the winner. Nothing at
or after the origin is used.

## 26. Service floors, transfers, promotions (P1/P2 pass)

**Service floor (unit fill, expectation).** For products $j$ with a floor
$\beta_j$: $\sum_{\omega,t} p_\omega u_{jt\omega} \le (1-\beta_j)\sum_{\omega,t} p_\omega d_{jt\omega}$.
Same semantics as §13. A floor capacity cannot meet is reported
`infeasible` (`test_unattainable_floor_is_reported_infeasible`). The
counterfactual harness sets it from the domain policy's `ServiceTarget`
when the metric is `unit_fill` and the scope is global. Line fill and
order fill are **measured** in settlement and cannot be enforced by a
product-level LP; that is a stated limit, not a gap to close by
approximation.

**Transfers.** A location is a product key (`SKU@LOC`). For an arc
$a=(j_{\text{from}}, j_{\text{to}}, c_a, L_a)$ a recourse variable
$z_{at\omega}\ge 0$ enters the balance of $j_{\text{from}}$ at $t$ and of
$j_{\text{to}}$ at $t+L_a$, costs $c_a$ per unit, and is bounded by the
source's opening stock in the period
($\sum_{a:\,\text{from}=j} z_{at\omega} \le I_{j,t-1,\omega}$). Conservation
across locations is asserted in `test_conservation_across_locations`.

**Promotions.** A planned uplift $m_{jt}$ known at the origin multiplies
scenario demand and the deterministic twin's expectation alike, and the
heuristics' per-period mean. It is an input, not a surprise
(`test_planned_promotion_raises_orders_for_optimizer_and_heuristic`).

**Horizon rule.** In closed-loop evaluation the horizon is at least
$2\max_i L_i + R$ (two lead times plus a review cycle), so today's order
can see its own consequence.

**Money.** Solver arithmetic is float. Every cost that leaves the engine
passes through `domain/money.py::Money`, a Decimal quantised to the
currency's minor unit; a breakdown's total is the sum of its quantised
parts exactly (`money_breakdown`), and cross-currency addition is refused.


## 27. Adaptive state and posture  ★

**State.** For entity $e$ (supplier, SKU, portfolio) and regime $r \in \mathcal{R}$ (ten regimes, four disruptive), evidence scores $s_e(r)$ are sums of named feature terms (§5.1 of the engine document) over a prior $s(\text{NORMAL}) = 2,\ s(\text{CALM}) = 1$, and
$$p_e(r) = \frac{\exp(s_e(r)/\tau)}{\sum_{r'} \exp(s_e(r')/\tau)},\qquad \tau = 0.6 .$$
A SKU $j$ with supplier $i$ mixes the supplier's supply-regime mass in directly:
$p_j(r) \propto p_i(r)\,\mathbb{1}[r \in \mathcal{S}] + p_j^{\text{own}}(r)\,(1 - \sum_{r' \in \mathcal{S}} p_i(r'))$.
The portfolio is the value-weighted mixture, plus $v_{\text{dis}} = \sum_j w_j \mathbb{1}[p_j(\mathcal{D}) > 0.5] / \sum_j w_j$.

**Change points.** Two-sided CUSUM on $z_t = \text{clip}((x_t - \mu_0)/\sigma_0, \pm 4)$ with $S^+_t = \max(0, S^+_{t-1} + z_t - k)$, $S^-_t = \max(0, S^-_{t-1} - z_t - k)$, alarm when $\max(S^+, S^-) > h$, $k = 0.5$, $h = 5$, $\sigma_0 \ge 0.02|\mu_0|$. Page–Hinkley with $\delta = 0.5\sigma$, $\lambda = 4\sigma$. An alarm is evidence only if the estimated shift $\ge 6$ fill points.

**Hysteresis.** $\bar p_t = (1-\alpha)\bar p_{t-1} + \alpha p_t$, $\alpha = 0.5$; the disrupted flag enters when $\bar p_t(\mathcal{D}) > 0.60$ and leaves after two consecutive updates with $\bar p_t(\mathcal{D}) < 0.35$; one tracker per SKU and one for the portfolio.

**Stress.** $S = \sum_c w_c\, \phi_c \in [0,1]$ with the component weights listed in the engine document; components are reported with the score.

**Posture.** Severity $t = \max(p^{\text{eff}}(\mathcal{D}),\ S,\ v_{\text{dis}})$ with $p^{\text{eff}} = \max(p, 0.6)$ while the flag holds. Every knob is a monotone interpolation $\kappa(t) = \kappa_0 + (\kappa_1 - \kappa_0)\,t$ between its calm and disrupted values: scenario width, block length, $\lambda_{\text{CVaR}}$, $\alpha_{\text{CVaR}}$, regret budget share, anchoring scale, change-cost rate, commit window, gate threshold and confidence. Trust-region fraction is stepped by SKU severity (5 / 15 / 40 / 80%) and scaled by $(0.5 + 0.5\,a)$ where the autonomy $a = \text{clip}(0.15 + 0.45 S + 0.40\, \text{evidence})$ is capped by data quality, calibration confidence and economics provenance.

**Optimizer additions.** With baseline $b_{ijt}$ (clipped to supplier capacity) and width $w_{ijt} = \max(f_j b_{ijt},\ \ell_j)$ ($\ell_j$ one lot):
$$\max(b_{ijt} - w_{ijt}, 0) \le x_{ijt} \le b_{ijt} + w_{ijt},$$
and plan stability $x_{ijt} - x^{\text{prev}}_{ijt} = c^+_{ijt} - c^-_{ijt}$ with objective term $\sum \kappa_j (c^+_{ijt} + c^-_{ijt})$, $\kappa_j = $ unit cost $\times$ change-cost rate. These sit inside the MILP with the anchoring $\rho_j |x - b|$, the CVaR$_\alpha$ of baseline-relative regret (§21) and the optional hard regret budget.

**Conditional scenarios.** Per scenario $\omega$ and route $g$, a disruption indicator $D_{\omega g} \sim \text{Bernoulli}(p_g(\mathcal{D}))$ shared by all suppliers on the route; when it fires, fills are multiplied by a deterioration–trough–recovery path (depth and length learned from the supplier's own worst episode when one exists, else the default profile labelled ASSUMED) and lead times stretched in proportion to the fill loss. Demand deviations from the cross-scenario mean are scaled by the posture width.

**Leading outlook.** For lane $g$ with available feeds $k \in K_g$ and standardised excess $e_k \ge 0$ (transit shortfall $2(1-I)$, log coverage ratio, GSCPI level, fuel and freight excess), $\text{risk}_g = \sigma(b + \sum_{k} w_k\, e_k\, \phi_k)$ with $b = -2.2$, stale-feed weight $\phi_k = 0.5$, and quality $q_g = |K_g| / |K^{\text{all}}_g| \cdot (1 - 0.3\, n_{\text{stale}}/|K_g|)$. The supplier's WATCH score gains $3\,(\text{risk}_g - 0.12)^+ q_g$. Lead is tested by $r(\ell) = \text{corr}(x_t, y_{t+\ell})$, $\ell = 0..12$ weeks, declared only when $\ell^* > 0$, $r(\ell^*) > r(0) + 0.05$ and $r(\ell^*) > 2/\sqrt{n}$.

**Modes.** EFFICIENCY when $t < 0.25$ (trust region off, $\rho$ scale 0.25, all candidates, gate 2% at 0.80), PROTECTION when $t \ge 0.55$, BALANCED between; demand severity $d = \sum_j w_j d_j / \sum_j w_j$ with $d_j = \text{clip}(0.6\,(p_j(\text{DV}) + p_j(\text{PROMO})) + 0.4\,\phi^{\text{drift}}_j + 0.3\,\mathbb{1}[\text{shift} > 2\sigma])$ adds $0.6\, d_j$ to SKU $j$'s trust fraction and drives scenario width through $\max(t, d)$.
