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
