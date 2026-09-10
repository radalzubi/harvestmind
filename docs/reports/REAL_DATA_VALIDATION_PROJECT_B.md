# Project B validated on real public data

**Branch** `feat/commercial-real-data-validation`
**Reproduce** `scripts/fetch_real_data.py`, then `scripts/run_real_validation_suite.sh`
**Raw output** `outputs/real_validation/`

---

## 1. The short version

The commercial optimizer was tested against 414 months of real US wholesale
demand and eight years of satellite-measured port arrivals, across normal
years, two recessions, COVID, the 2021-23 inflation and the Red Sea war.

**It beats every baseline it was tested against, but by very different
margins, and the margin against the honest baseline is conditional.**

| comparison | median edge | 95% CI (block) | folds won |
|---|---|---|---|
| vs naive order-up-to with safety stock | **+13.2%** | — | 288/342 |
| vs cautious p90 lead-time buffering | **+34.3%** | — | 341/342 |
| vs the same optimizer given a point forecast | **+10.5%** | [+7.9, +13.1] | 283/336 |

The third row is the one that matters. The first two beat policies that are
worse by construction. The third asks whether *modelling uncertainty* pays,
against an optimizer identical in every respect except that it sees a mean
instead of a distribution. Over the full 1994-2026 history that edge is
**+1.8%**. Over the window where supply shocks are actually measured it is
**+10.5%**.

**Four harness defects were found and fixed during this work.** One of them
was a filter that was quietly selecting the folds where the model wins. Had
it survived, it would have produced this repository's sixth retracted
headline. That defect, and the fact that it was caught by checking rather
than assumed away, is the most important result here.

---

## 2. What is real, and what is not

This boundary decides what any number below is worth.

### Real, downloaded, committed under `data/external/`

| what | source | span |
|---|---|---|
| Demand path | US Census Monthly Wholesale Trade Survey, grocery and related products (NAICS 4244), **not** seasonally adjusted, via FRED `S4244SM144NCEN` | 414 months, 1992-01 to 2026-06 |
| Inventory norms | US Census merchant wholesaler inventory/sales ratios | 414 months |
| Supply shocks | IMF PortWatch satellite AIS, daily port calls and import tonnage for the ports serving each Jordanian import route | 2,797 days each, 2019-01 to 2026-08 |
| Chokepoint transits | IMF PortWatch, 28 chokepoints including Suez, Bab el-Mandeb, Hormuz | 78,372 daily records |

PortWatch records **Aqaba as carrying 100% of Jordan's maritime imports**.
Jordan's single-seaport exposure is measured, not assumed.

### Synthetic, and never claimed as validated

The **cross-section**: which SKU, which supplier, which margin. No public
source publishes SKU-level or supplier-level order and fill records for any
distributor. The ABC curve and supplier tagging remain calibrated guesses.

The **map from arrival shortfall to fill rate**. Tonnage landed is
observable; tonnage *ordered* is not. Every supply number here is a
documented proxy, built by dividing each port's arrivals by its own
trailing 12-month median and then by a benchmark port's same-month
deviation, so that shocks moving the whole region cancel and what remains
is specific to that route. It cannot remove a shock that hit one route
through demand alone. That residual confound is real.

**No public dataset permits a true end-to-end backtest of this optimizer**,
because the decision it makes — how much to commit to which supplier before
supply resolves — leaves no public trace. What is validated is the demand
process, the supply-shock process, the inventory constraint, and the
decision rule's behaviour when driven by all three.

---

## 3. Four harness defects, each of which moved a headline

### 3.1 The warehouse had no walls

The optimizer finished a 12-month horizon holding **16.6 months of stock**:
399,119 units against 24,046 units of monthly demand. Holding was 97% of
total cost. Nothing in the model priced or bounded inventory, so buying
many months of cover to avoid one month of lost margin was rational.

US Census reports merchant wholesalers at a mean inventory/sales ratio of
**1.264 across 414 months, about 38 days, with a p90 of 1.35**. That is the
constraint the model was missing. `MultiPeriodStochasticLP` gains an
optional inventory capacity — defaulting to `None`, so Project A is
untouched — and the replay writes off stock above the cap. The cap used is
2.0 months, deliberately slack against the measured 1.26.

### 3.2 The model and the scorer disagreed about disposal

Waste was priced at zero in the optimizer while the replay charged full
unit cost for the same units. The optimizer was solving a cheaper world
than the one it was graded in, and it exploited the gap: over-order, dump
the excess for free, get charged for it at settlement. Overflow was 97% of
scored cost. Disposal is now priced identically on both sides.

### 3.3 The guard was selecting the answer

The original design rejected any fold where service fell outside a band or
one cost component exceeded 90% of the total, on the reasoning that every
previously retracted headline showed one of those symptoms.

Applied to whole folds it did something worse than the defects it targeted.
It rejected **136 of 258 folds. The rejected folds had a median edge of
−4.21%; the kept folds, +7.33%.** It was discarding the folds where the
stochastic policy loses.

The cause is that a fold where holding is 96% of cost is not degenerate. It
is an *easy month*: everyone met demand, and the only thing separating the
policies is who tied up less capital. Those are exactly the months where
buying extra service loses, and dropping them flatters any policy that buys
service.

Rejection is now limited to genuine harness failures — a fill rate outside
[0,1], a non-positive cost, or overflow dominating. **One fold in 342 is
now rejected.** Lopsided folds are *stratified* in the output instead,
which turned out to be the most informative view in the whole study.

### 3.4 The naive baseline was a straw man

It ordered the trailing mean with no allowance for supplier shortfall and
no safety stock, reaching 78% service and losing by 347%. Beating that
proves nothing. It is now a textbook periodic order-up-to policy with a
normal-approximation safety stock, grossed up by the observed fill rate: it
knows demand varies and that suppliers under-deliver. It reaches 95-98%
service, the best of any policy tested, and the optimizer's edge over it
fell from 347% to 13%.

---

## 4. Results

### 4.1 Across the full history

1,028 folds, 1994-2026, rolling monthly origins, 12-month horizons.

| regime | vs naive | vs point-forecast optimizer | vs p90 | n |
|---|---|---|---|---|
| normal 1990s | +18.9% | +3.10% | +31.2% | 126 |
| normal 2000s | +22.3% | +1.53% | +28.9% | 162 |
| GFC 2007-10 | +20.1% | +1.00% | +27.0% | 126 |
| normal 2010s | +17.9% | +0.87% | +28.7% | 288 |
| COVID | +23.9% | **−0.76%** | +19.0% | 53 |
| inflation 2021-23 | +3.7% | **+11.83%** | +37.9% | 72 |
| Red Sea war | +14.1% | +2.97% | +29.3% | 81 |
| **pooled** | **+18.97%** | **+1.78%** | **+29.44%** | **1028** |

### 4.2 The finding that explains the rest

Splitting folds by how hard the month was — using the *baseline's* cost
split, never the stochastic policy's own, so the split cannot be drawn to
favour what is being tested:

| stratum | pooled full history | with real supply shocks |
|---|---|---|
| **binding** (shortage > 20% of baseline cost) | **+4.17%**, 528/769 | **+10.64%**, 272/323 |
| **slack** (easy month, holding dominates) | **−4.75%**, 69/259 | **+5.66%**, 14/19 |

**The stochastic model earns its keep when supply or demand actually bind,
and destroys value when they do not.** In an easy month it buys service
nobody needed and pays for the inventory. This is not a defect; it is what
the theory predicts, and it is the single most useful thing to tell an
operator: the model is worth running when conditions are tight, and an
operator in calm conditions with deep stock should not expect much.

### 4.3 Controlled experiment: do measured supply shocks change the value?

Identical window, seeds, training length, operator draws and demand path.
The only difference is whether the measured PortWatch route shocks are
applied. 336 matched folds.

| arm | edge over point-forecast optimizer | 95% CI (block) | wins |
|---|---|---|---|
| supply shocks disabled | +6.38% | [+3.31, +11.44] | 244/336 |
| real PortWatch shocks | **+10.46%** | [+7.91, +13.09] | 283/336 |

Paired difference: **+2.26 percentage points, 95% CI [−0.70, +4.62], sign
test p = 0.025, 189 of 336 folds improved.**

**Stated precisely: the direction is supported and marginally significant
by sign test, but the block-bootstrap interval on the paired median
includes zero. Real supply disruption raising the value of stochastic
optimization is consistent with the evidence and not established at 95%
once the overlap between folds is accounted for.**

The cleaner signal is in the strata. With shocks disabled, easy months run
at **−11.16%** (7/48 wins). With real shocks applied they run at
**+5.66%** (14/19), and the number of easy months falls from 48 to 19 —
measured disruption converts slack months into binding ones, which is the
mechanism working as designed.

### 4.4 The parameter that decides the answer

| opening stock | edge vs point-forecast optimizer | binding | slack |
|---|---|---|---|
| 0.0 months | +8.01% | +8.01% | — |
| 0.5 | +5.73% | +5.90% | −20.82% |
| 1.0 | +1.31% | +4.89% | −10.25% |
| 1.5 | −0.04% | +5.04% | −7.85% |
| 2.0 | −0.23% | +5.75% | −5.42% |

The pooled edge decays to nothing as the operator starts better stocked,
while the **binding-month edge stays flat at +5 to +8% throughout**. The
pooled number moves only because deep stock converts binding months into
slack ones. A lean operator benefits; a well-stocked one does not, and
should be told so.

Warehouse capacity behaves the same way: +1.33% at 1.5 months of capacity,
+1.31% at 2.0, +0.06% at 3.0. At a 1.0-month cap — tighter than the
measured 1.26-month industry mean — most folds become infeasible and the
edge inverts to −2.88%. That is a real limit and it is quoted as one.

---

## 5. Disruption presets confronted with satellite data

`risk/disruption_scenarios.py` carried seven presets, every one flagged
`assumed=True`. PortWatch measures the 2019-2026 window directly.

### 5.1 Measured chokepoint transits, ratio to each chokepoint's own 2019 baseline

| chokepoint | COVID | Ever Given | calm 2022 | Red Sea 2024 | 2025-26 |
|---|---|---|---|---|---|
| Suez Canal | 0.98 | 1.05 | 1.27 | 0.80 | 0.75 |
| Bab el-Mandeb | 1.00 | 1.05 | 1.25 | **0.66** | **0.64** |
| Cape of Good Hope | 1.11 | 1.04 | 0.92 | **1.75** | **1.87** |
| Strait of Hormuz | 1.11 | 1.18 | 1.37 | 1.30 | 0.96 |

Bab el-Mandeb fell by a third and **stayed there for over two years**. This
is a regime shift, not an episode. Cape of Good Hope nearly doubled: the
reroute is measured, not inferred, which validates the route-substitution
structure the model is built around.

### 5.2 Verdicts

| preset | assumed | measured | verdict |
|---|---|---|---|
| `red_sea_houthi` | 0.85 | 0.743 | **OPTIMISTIC → revised to 0.75** |
| `aqaba_congestion` | 0.80 | 0.743 | consistent |
| `northern_land_disruption` | 0.65 | 0.736 | consistent |
| `saudi_land_disruption` | 0.60 | — | **UNTESTED**, no such closure occurred |
| `all_land_disruption` | 0.50 | — | **UNTESTED**, never occurred |
| `regional_escalation` | 0.45 | — | **UNTESTED**, never occurred |

A tail scenario that did not happen in the measured window is untested, not
refuted. Three of six presets remain hypotheticals and are labelled so.

### 5.3 A preset that silently did nothing

`red_sea_houthi` listed `affected_routes = ("red_sea", "suez")`. **No
simulator ever tags a supplier with either name.** The scenario applied to
zero suppliers: running it returned the baseline while presenting as a
stress test. This is the most dangerous failure mode available here,
because it is invisible in the output.

Aqaba is *inside* Bab el-Mandeb, so the Cape reroute that protects
Europe-bound cargo cannot serve it — a ship calling at Aqaba must pass the
strait either way. `"aqaba"` is added, and a test now fails any preset that
reaches no live route.

Aqaba's **five worst months in seven years of record are all inside the Red
Sea crisis window**, bottoming at 0.406 in February 2024.

`assumed` stays `True` on every preset. PortWatch measures tonnage
*arrived*; a fill rate needs tonnage *ordered*. Measurement narrowed the
range. It did not turn an assumption into an observation.

---

## 6. A negative result worth more than a positive one

The scenario generator inside the optimizer bootstraps month-over-month
growth rates ignoring calendar month. On a not-seasonally-adjusted series
that discards the strongest signal present. Scored on 4,404 origin-horizon
pairs of real history:

| method | WIS | vs best | 80% coverage | below median |
|---|---|---|---|---|
| iid bootstrap *(the one in the loop)* | 0.0541 | 1.52 | **95.9%** | 47.9% |
| seasonal bootstrap | **0.0356** | 1.00 | **80.0%** | 51.0% |
| seasonal naive | 0.0396 | 1.11 | 54.5% | 20.2% |
| random walk | 0.0500 | 1.40 | 96.3% | 37.8% |

The generator in use was **52% worse than a seasonal variant, worse than
both trivial references, and badly over-dispersed**: 95.9% coverage from a
nominal 80% interval. The optimizer was hedging against a spread far wider
than history supports.

Fixing it changed the forecast score substantially. **It did not change the
decision.** Paired over 337 identical folds:

| | median | 95% CI (block) |
|---|---|---|
| SP cost, seasonal minus iid | +0.72% | [−0.96, +2.36], sign p = 0.19 |
| SP fill rate, seasonal minus iid | +0.45 pt | [+0.19, +0.66], p = 0.003 |
| deterministic cost (control) | 0.00% | [0.00, 0.00], p = 1.00 |

The control row is exact, which confirms the only thing that changed was
the scenario generator.

**A 52% improvement in forecast calibration produced no detectable
improvement in decision quality.** Forecast accuracy and decision value are
not the same currency, and improving the first is not a substitute for
demonstrating the second. The seasonal generator is now the default anyway
— it is better calibrated and costs nothing — but the honest claim is that
it buys 0.45 points of service, not a better decision.

---

## 7. What this licenses, and what it does not

### Supported

- The optimizer beats a competent order-up-to baseline by roughly 13%, and
  a lead-time-buffering baseline by roughly 34%, robustly across 1,028
  folds spanning three decades and five macro regimes.
- Against the honest baseline — the same optimizer with a point forecast —
  the edge is **conditional on conditions binding**: +4 to +11% in binding
  months, negative in easy ones.
- Jordan's single-port exposure and the Red Sea shock are measured facts,
  not modelling assumptions. Aqaba is 100% of Jordanian maritime imports
  and its worst months on record are the war months.
- Route substitution is real and measurable: Cape of Good Hope transits
  nearly doubled while Bab el-Mandeb fell by a third.

### Not supported

- **No end-to-end backtest on operator records exists.** Every result rests
  on a synthetic cross-section driven by real time paths. The first pilot
  with real order and fill data can overturn any of it.
- **The supply proxy is not a fill rate.** Arrivals below a trailing norm
  may reflect fewer orders rather than failed deliveries.
- The claim that measured disruption raises the value of stochastic
  optimization is directionally supported, **not established at 95%**.
- Three of six disruption presets describe events that have not occurred in
  the measurable record and remain priced hypotheticals.
- Results are monthly with 1-3 month lead times, which suits ocean import
  distribution. They say nothing about weekly perishable replenishment,
  which is Project A.

### The honest sentence for an operator

*If you run lean, and your supply is genuinely disrupted, this is worth
roughly 5 to 11% of the cost of getting the order wrong, and rather more
against how the decision is usually made today. If you carry deep stock in
calm conditions, it is worth close to nothing, and we would rather tell you
that now than after a pilot.*
