# Commercial Supply Uncertainty: Review and Decision Record

## Scope — read this first

**This implements COMMERCIAL SUPPLY uncertainty, not biological crop
yield.** The distinction is not pedantic:

| Layer | Status |
|---|---|
| Biological yield (kg/ha in the field) | **NOT implemented — research-only** |
| Harvestable fraction | Not separately modelled |
| Commercial packout / grade share | Not separately modelled |
| **Supplier delivery / commercially available supply** | **Implemented** |

What is deployed is a probabilistic model of *how much product a supplier
actually delivers against an order*, calibrated on delivery records. The
biological crop-yield mandate is **not complete**, for one deliberate
modelling reason (double counting, §1) and one data reason: no operator
currently supplies field, acreage or cultivar data.

Any claim that HarvestMind "forecasts crop yield" would be false. It
forecasts commercial supply — which is the quantity the optimizer needs.

---

Research basis for `forecasting/supply_uncertainty/` and
`risk/correlated_scenarios.py`. Claims graded **[V]** verified against the
primary source, **[P]** partial (abstract or reliable secondary only),
**[U]** unverified — recorded so it is not mistaken for evidence.

---

## 1. What is actually being forecast

The optimizer needs available supply, not crop yield. These are different
quantities and conflating them overstates what any model knows:

```
available_supply = harvested_area
                 × yield_per_area
                 × harvestable_fraction
                 × grade_share
                 × (1 − post_harvest_loss)
                 × supplier_execution_fraction
```

`QuantityKind` in the contract records which link a forecast describes.
**These must not be multiplied as independent point estimates** — a hot
week depresses yield, packout and delivery reliability together, so
multiplying independent draws understates the joint downside.

### The double-counting hazard, and how we avoid it

HarvestMind already models **supplier execution** as an Empirical-Bayes
Beta on observed fill rate (`risk/supplier_distribution.py`). Fill rate is
`accepted / ordered` — a ratio that has *already absorbed* every upstream
loss: if the crop failed, the fill rate was low.

So adding a separate biological-yield model on top of the existing fill-rate
model would count the same weather twice. Our design therefore keeps the
fill-rate model as the single supply-uncertainty channel for operators
whose data is delivery records (all of them today), and treats a
biological-yield model as a *future* tier for operators who supply field
and acreage data. This is a data-availability decision, not a preference.

---

## 2. Method review

### 2.1 Baselines — retained, and the benchmark

| Method | Verdict |
|---|---|
| Seasonal historical mean/median | Retained as `ClimatologyModel` |
| Empirical conditional quantiles | Core of `PooledEmpiricalModel` |
| Empirical-Bayes partial pooling | **Production Tier 0** |
| Residual bootstrap, analog years | Available; not needed given pooling |

Empirical-Bayes shrinkage: with n observations, within-group variance
sigma², between-group variance tau², weight on the group's own mean is
`w = n/(n + sigma²/tau²)`. The James-Stein result — shrunken estimators
dominate per-group sample means in total squared error — is textbook
[P]; the canonical anchor is Efron & Morris (1975) *JASA* 70(350):311-319,
whose full text I did not read.

**The failure mode this prevents** is not hypothetical, and it is the
single most important thing in this document. A supplier with three
deliveries within 1% of each other produces a near-zero sample variance. A
naive empirical quantile returns a ~1%-wide interval. The optimizer then
commits hard against a number that was never entitled to that confidence.

### 2.2 Classical probabilistic regression

| Method | Assessment |
|---|---|
| **Quantile regression forests** | **Challenger.** Meinshausen (2006) *JMLR* 7:983-999 [P]. Directly evidenced for crop yield: Gyamerah, Ngare & Ikpe (2020), *Agric. For. Meteorol.* 280:107808, doi:10.1016/j.agrformet.2019.107808 [V — exists; results [P], paywalled]. Note the evidence base is one country, two crops. |
| Linear/nonlinear quantile regression | **Implemented** as the dependency-free fallback |
| GAMLSS, Gamma/lognormal/Tweedie GLM | **Rejected for now** — commit to a shape we cannot justify; misfit lands in the lower tail |
| Censored / zero-inflated | **Future** — needed when total crop failure appears in the data |

**Why quantile regression over a fitted distribution:** supply outcomes are
skewed, bounded at zero, heteroscedastic and sometimes bimodal (the crop
makes it or it does not). Any single parametric family misfits somewhere,
usually in the lower tail — exactly where the optimizer is exposed.

### 2.3 Gradient-boosted probabilistic models — **Production Tier 1**

LightGBM quantile objective, one model per level. Optional at import; the
package falls back to a linear quantile regressor so tests need no heavy
dependency.

**Quantile crossing** is real and must be handled. Independently fitted
levels can cross, and a crossed interval passed to a scenario generator
produces negative-width distributions. We detect crossing, record it in the
forecast's warnings, then apply monotone **rearrangement**:
Chernozhukov, Fernández-Val & Galichon (2010), *Econometrica*
78(3):1093-1125 [V]. Their result matters: sorting is *not* an ad-hoc
tidy-up — the rearranged curve is provably weakly closer to the true
quantile function. We still surface it rather than sorting silently,
because crossing signals a model defect the operator should see.

### 2.4 Bayesian and hierarchical — **challenger, partly realised**

Full hierarchical Bayesian regression (Stan/PyMC) is **rejected for now**:
it would add a heavy sampler dependency to a small team's runtime, and the
partial pooling that gives it most of its advantage at our data scale is
already implemented analytically in Tier 0.

Bayesian neural networks for yield are **research-only** at our scale:
Ma, Zhang, Kang & Özdoğan (2021), *Remote Sensing of Environment*
259:112408, doi:10.1016/j.rse.2021.112408 [V — exists; R²≈0.77 figure [P]]
demonstrates the approach on US county corn with dense remote sensing.
That is thousands of county-years; a food hub has tens of supplier-seasons.

### 2.5 Process-based and hybrid crop models — **future tier**

Shahhosseini, Hu, Huber & Archontoulis (2021), *Scientific Reports* 11:1606,
doi:10.1038/s41598-020-80820-1 [V, PMC full text] show that adding
APSIM-derived variables to ML models cut RMSE ~7-20% for Corn Belt maize,
with the gain concentrated in the extreme 2012 drought year (5-43%) and
soil-water/drought-stress variables most valuable.

**Not adopted as a runtime dependency.** APSIM/DSSAT need cultivar,
planting date, soil profile and management inputs that HarvestMind's
CSV-intake operators do not have. The architecture accepts process-model
outputs as *optional features* if a customer supplies them.

### 2.6 Remote sensing — **blocked on geography, not on capability**

NDVI/EVI/LAI/SIF are well evidenced for yield. The blocker is that our
intake carries no field boundaries or acreage. Adding supplier location
(town/zip) — already flagged as an outreach ask — is the prerequisite.
Classified honestly: **future integration**, not "immediately usable."

### 2.7 Sequential in-season updating — **partly realised**

The architecture requirement is met: forecasts are indexed by issue date,
information cutoff, horizon and model version, so a newer forecast cannot
overwrite the one that was actually available during a backtest. Full data
assimilation (Kalman/particle filtering) is **research-only** for now.

### 2.8 Deep probabilistic forecasting — **rejected for current data**

DeepAR, TFT, mixture-density networks, deep ensembles. Minimum plausible
dataset is thousands of series with long histories; we have tens of
supplier-product series with a handful of seasons. No backtest could
distinguish such a model from noise here.

### 2.9 Conformal prediction — **production, and the key addition**

Romano, Patterson & Candès (2019), NeurIPS 32, arXiv:1905.03222 [V, full
text]. Exact algorithm as implemented:

1. Split data; fit `q_lo`, `q_hi` on the training part only.
2. On calibration data compute `E_i = max{q_lo(x_i) − y_i, y_i − q_hi(x_i)}`.
3. Take `Q` = the `⌈(n+1)(1−α)⌉/n` empirical quantile of `{E_i}`.
4. Return `[q_lo − Q, q_hi + Q]`.

Guarantee: `P(Y ∈ C(X)) ≥ 1 − α`, finite-sample and distribution-free,
requiring only **exchangeability** — and notably *not* requiring the
quantile model to be any good. A poor model gives wide intervals, not
wrong coverage. Coverage is also bounded above by `1 − α + 1/(n+1)`, so it
cannot be uselessly conservative.

`Q` may be **negative**, tightening an over-wide interval. That is correct
behaviour and is tested.

**Where the guarantee breaks.** Exchangeability fails under temporal drift,
and crop data drifts (climate trend, cultivar turnover). Mitigations
implemented: chronological calibration splits (never random), and Mondrian
per-group calibration so a single crop cannot be badly under-covered behind
healthy marginal coverage. Neither restores the theorem. **Coverage is
therefore always measured on held-out data and reported, never asserted.**
Adaptive conformal inference (Gibbs & Candès 2021, NeurIPS 34 [V]) and
EnbPI (Xu & Xie, ICML 2021 [V]) are the documented next step if drift
proves material.

### 2.10 Ensembles

Yin et al., *Earth's Future*, doi:10.1029/2024EF005900 [V] find the choice
of ensemble-averaging method is itself a major uncertainty source —
contributing over half of total projection uncertainty in some cases.
Taken as a caution against treating averaging as neutral. Not implemented
yet; would be premature with one production model and one challenger.

### 2.11 Lower tail — where the optimizer is exposed

The optimizer is asymmetrically exposed to supply arriving BELOW forecast.
Implemented: explicit p05 estimation, `tail_coverage()` reported separately
from central coverage, and t-copula tail dependence (below). **Extreme-value
/ generalised-Pareto tail fitting is deliberately rejected** at current
sample sizes — fitting a GPD to a handful of seasons produces unstable
shape parameters that look authoritative. Transparent stress scenarios are
the honest substitute.

### 2.12 Hierarchical reconciliation — audited, and the finding is negative

`forecasting/demand/hierarchical_reconciler.py` was imported only by tests.
The audit found the reason is **mathematical, not an oversight**: the demand
service forecasts at the bottom level only (product × buyer), and
bottom-level forecasts are already coherent, so MinT reduces to the identity.
Wiring it would add cost for no effect. Documented in place; added
`coherent_category_totals()` for the aggregation that *is* useful now. MinT
becomes live if category-level models are ever fitted directly.

### 2.13 Dependence — **the highest-value change in this work**

Independent sampling was the single most consequential modelling error in
the codebase.

`yield_scenarios_from_distributions` drew each supplier's fill rate
independently. Weather is regional: a heat wave hits every grower in a
supply shed at once. Independent draws cancel across a portfolio, the
aggregate tightens around its mean, and the stochastic optimizer finds
nothing to hedge — which is exactly the **VSS ≈ 0** result that took
extended investigation to explain. Independence was doing the work.

Implemented: Gaussian and **t** copulas preserving each supplier's
calibrated Beta marginal exactly while inducing rank correlation.

- Rank correlation is the target because it is invariant under the
  monotone marginal transforms the construction applies; Pearson is not.
  **Kendall's tau** is used rather than Spearman because the identity
  `rho_latent = sin(π·tau/2)` holds for the whole elliptical family —
  Gaussian and t at any degrees of freedom. The Spearman identity
  `rho = 2·sin(π·rho_s/6)` is Gaussian-specific and is retained only for
  that case.
- **A rank matrix is NOT a latent correlation parameter.** An earlier
  revision passed the estimated Spearman matrix straight into the Cholesky
  factor, silently targeting weaker dependence than requested (the error
  grows with |rho|; a 0.75 target realised ≈0.55). The conversion is now
  applied once, on the production path, and pinned by tests that check the
  realised Kendall's tau of the DRAWS to ±0.02 for both copulas.
- **t is the default copula *conditional on explicitly enabling correlated
  scenarios*** — correlated sampling itself defaults to OFF. Gaussian
  copulas have **zero tail dependence** for
  any rho < 1 — extreme events become asymptotically independent, so
  simultaneous severe shortfalls are systematically under-represented.
  That is the precise scenario a perishable buyer must plan for.
  Demarta & McNeil (2005), *Int. Statistical Review* 73(1):111-129 [V].

#### How correlation is estimated, pooled, and defaulted

Correlated sampling is **off by default** (`SupplyRiskPolicy.mode =
"independent"`). It changes the recommended commitment, so which
dependence model is in force is an operator-visible decision, not a
constant chosen in a module. Two parameters are genuinely unestimated
today — whether suppliers exhibit joint-tail clustering at all, and the
t-copula `df` that controls how much — so making the t copula an
unconditional default would be asserting an empirical claim we cannot
support.

| Policy mode | Correlation source | When to use |
|---|---|---|
| `independent` (default) | none; rho = 0 | Always, until joint history exists. Provenance IS emitted on this path too (`correlation_source: independent_by_policy`, supplier count, seed) and states that aggregate risk is understated if suppliers share a region. |
| `equicorrelated` | one operator-supplied Kendall's tau | The operator knows their growers share a weather shed but history is too short to estimate |
| `estimated` | pairwise Spearman on shared weeks, then shrunk | Genuine joint history exists |

Under `estimated`, in order:

1. **Estimate.** Pairwise Spearman rank correlation of weekly fill rates
   on weeks both suppliers delivered. Rank, not Pearson, because it is
   invariant under the monotone marginal transforms the copula applies.
2. **Default thin pairs.** Any pair with fewer than `min_overlap` (4)
   shared weeks is set to **0** rather than reporting a correlation
   computed from two points.
3. **Pool by shrinkage.** k suppliers imply k(k−1)/2 correlations all
   estimated from the same n weeks, so the raw matrix is over-fitted. It is
   shrunk toward equicorrelation with weight
   `w = clip(params/(params + n_periods), 0.1, 0.9)`. With 6 suppliers
   (15 pairs) over 10 weeks, w = 0.6 — most of the estimate is discarded,
   correctly, because fifteen correlations cannot be learned from ten
   observations. **Both bounds are judgement and are labelled as such.**
4. **Validate and regularise.** Symmetry, unit diagonal, range and PSD are
   checked; a failure is repaired by projection to the nearest PSD
   correlation matrix and the repair is **recorded** in diagnostics
   (`regularized: true`, plus the pre-repair minimum eigenvalue).
5. **Refuse when too thin — measured on genuine PAIRWISE OVERLAP.** An
   earlier revision counted the longest single supplier series, which is
   not joint history at all: A observed Jan-Jun and B observed Jul-Dec
   would report 30 periods while sharing no week. Estimation is now refused
   when any of these fail, each with its own diagnostic code: fewer than 12
   periods with two or more suppliers observed together
   (`refused_insufficient_history`); under 60% of supplier PAIRS clearing
   `min_overlap` (`refused_sparse_pairs`, since most of the matrix would be
   defaults wearing the label "estimated"); or the adequately-overlapping
   pairs forming disjoint clusters (`refused_disconnected`). Diagnostics
   always report per-pair minimum, median and maximum overlap, the share of
   adequate pairs, the count of jointly-observed periods, and connectivity.
6. **Failures are never silent — including evidence-based refusals.**
   When the requested dependence model cannot be supported, the default
   behaviour is to **raise**. Independent fallback occurs only when the
   policy explicitly sets `on_failure="independent"`, and is then recorded
   as `fallback_applied`. This applies to the ordinary refusal path
   (insufficient history, sparse pairs, disconnected clusters) as well as
   to exceptions — an earlier revision honoured the policy only for
   exceptions, so the PRIMARY expected failure mode still degraded
   silently.
7. **Provenance is request-scoped, and emitted on EVERY path.**
   Diagnostics are returned with the draws (`generate_yield_scenarios` ->
   `ScenarioGenerationResult`, or the `diagnostics_out` sink), never stored
   in module-global state. A process global raced under concurrent planning
   calls, so operator A could read operator B's policy, supplier count and
   failure reason — corrupting audit provenance across a tenant boundary.
   The independent path emits provenance too; an earlier revision emitted
   only inside the correlated branch, leaving the most common production
   route — the default — entirely unaudited.
8. **Infrastructure faults are not modelling outcomes.** `on_failure`
   governs INSUFFICIENT STATISTICAL EVIDENCE only. A missing table or other
   database fault raises `ScenarioDataError` and propagates regardless of
   the policy. An earlier revision wrapped the query in
   `except Exception: return {}`, so a migration defect was reported as
   "no delivery history" — silently producing independent scenarios under
   `on_failure="independent"`, and a misleading *modelling* refusal that
   hid the root cause under `on_failure="raise"`.
9. **Seed precedence.** When correlation is enabled the policy's `seed` is
   authoritative, because the policy describes the whole dependence model
   and its reproducibility; the function argument governs the independent
   path. The seed actually used is always reported in diagnostics.

Every branch is reported in the returned diagnostics, so a plan can always
be traced back to the dependence assumption behind it.

**Measured effect** (6 suppliers, Beta(8,2) marginals, t-copula df=4) —
this is a SYNTHETIC illustration of mechanism, not a validated operator
result:

| rank correlation | aggregate supply SD | VSS |
|---|---|---|
| 0.0 | 0.0458 | 139.40 |
| 0.3 | 0.0707 | 194.31 |
| 0.7 | 0.0942 | 217.19 |

Correlation **doubles** aggregate supply risk and raises the absolute value
of stochastic optimization by 56%.

---

## 3. Decision matrix

| Method | Data need | Sparse behaviour | Tail | Calibration | Cost | Verdict |
|---|---|---|---|---|---|---|
| Pooled empirical + EB | Any | **Excellent** (designed for it) | Empirical | Uncalibrated by default | Trivial | **Production Tier 0** |
| Climatology | Any | Good | Empirical | Uncalibrated | Trivial | **Production fallback** |
| LightGBM quantile + CQR | 100+ rows | Poor alone; needs Tier-0 fallback | Direct p05 | **CQR** | Low | **Production Tier 1** |
| Linear quantile + CQR | 30+ rows | Moderate | Direct | CQR | Trivial | **Production fallback (no LightGBM)** |
| Quantile regression forest | 200+ rows | Good | Direct | CQR | Low | **Challenger** |
| Hierarchical Bayesian | Many groups, few obs | Excellent | Posterior | Native | High (sampler) | **Challenger, not adopted** |
| GAMLSS / parametric GLM | Moderate | Moderate | Shape-dependent | Parametric | Low | **Rejected** — unjustifiable shape |
| Process-based (APSIM) | Field/soil/cultivar | n/a | Physical | n/a | Very high | **Future tier** |
| Remote sensing features | Field geometry | n/a | Good | n/a | High | **Future — blocked on geography** |
| Deep probabilistic | 1000s of series | Very poor | Learned | Poor | High | **Rejected for current data** |
| EVT / GPD tails | 50+ extremes | Unstable | Native | n/a | Low | **Rejected** — too few seasons |
| Gaussian copula | Joint history | Fallback to equicorrelation | **Zero tail dep.** | n/a | Trivial | **Implemented, not default** |
| **t copula** | Joint history | Fallback to equicorrelation | **Nonzero tail dep.** | n/a | Trivial | **Opt-in via policy — NOT a default** |

---

## 4. Decision gate

The rule set before implementation was: do not displace the baseline unless
a candidate shows materially better WIS/CRPS, better lower-tail coverage,
better decision value, or comparable performance at lower complexity.

**Outcome: the baseline is retained as champion.** Tier 0 remains the
default for sparse and unseen groups — which is most groups at our
operators' data scale — and Tier 1 is integrated as the model for groups
with enough history. No candidate displaced Tier 0 on sparse data, and
none was tested on real operator data because none exists yet.

**The genuinely load-bearing change was not the model. It was the
dependence structure and the calibration layer** — both of which improve
every model, including the baseline.

---

## 5. Limitations, stated plainly

1. **No real operator data exists.** Every number here is from synthetic or
   controlled data. Calibration and decision value must be re-measured on
   the first pilot dataset before any of it is quoted to a customer.
2. **No biological-yield model is deployed**, deliberately — it would
   double-count weather already captured in fill rate. It becomes correct
   when field/acreage data arrives.
3. **Conformal coverage is not guaranteed under drift.** Mitigated, not
   solved. Measured coverage is the source of truth.
4. **Correlation is estimated from short histories.** Pairs with fewer than
   4 overlapping weeks fall back to a default rather than reporting a
   correlation computed from two points.
5. **The t-copula degrees-of-freedom parameter (5) is a judgement, not an
   estimate.** It controls how strongly joint tails cluster and should be
   fitted once real multi-supplier history exists. This is why correlated
   sampling is opt-in rather than default.
6. **VSS must be read from the out-of-sample bootstrap interval**
   (`optimization/vss_evaluation.py`), not the in-sample point estimate.
   At ~100 scenarios, sampling noise alone is worth roughly 7% of the
   objective (measured via `optimization/saa_bounds.py`), so a VSS smaller
   than that band is indistinguishable from noise. Where the interval
   contains zero, the honest conclusion is that stochastic optimization has
   not been shown to help on that instance.
7. **The correlation effect table above is synthetic.** It demonstrates
   that the mechanism works; it is not evidence about any real operator's
   suppliers.
6. **Specialty-crop thresholds remain thin** in the literature generally —
   see `docs/research/weather_agriculture_math.md` §3.
