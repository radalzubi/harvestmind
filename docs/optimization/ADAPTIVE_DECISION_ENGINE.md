# HarvestMind Adaptive Decision Engine

*How the optimizer knows what kind of week it is, and what it is allowed to do about it.*

This document describes the state layer that sits between the operator's data and the
stochastic optimizer, the mathematics of each stage, and the guarantees the design gives.
Validation lives in [ADAPTIVE_ENGINE_VALIDATION.md](../validation/ADAPTIVE_ENGINE_VALIDATION.md).
The safe-selection machinery it builds on is in [SAFE_ADAPTIVE_OPTIMIZER.md](SAFE_ADAPTIVE_OPTIMIZER.md).

## 1. Problem

A stochastic optimizer that is always "on" wins in disrupted periods and loses in calm ones:
the frozen validation in `docs/validation/SAFE_POLICY_VALIDATION.md` measured the standalone
stochastic optimizer at −53% to +59% against a competent incumbent depending on the regime.
A hard regime switch (CALM / DISRUPTION labels) does not fix this. It flips on one bad
delivery, it cannot express "we are 40% sure something is starting", it treats a missing
logistics feed as good news, and it gives the optimizer the same freedom in every state.

The engine below replaces the switch with an estimated **operating state** and a
state-dependent **posture**. The optimizer's *formulation* does not change; what changes is
the scenario set it is handed, the risk weights in its objective, how far it may move from
the incumbent, how much it is charged for changing last week's plan, and how long the
resulting orders stay executable.

## 2. Pipeline

```
history + signals ──► state estimator ──► posture ──► conditioned scenarios ──► MILP ──► safe gate ──► plan
   (dated ≤ origin)   (probabilities,      (λ, α, ρ,     (widen / disrupt /        (trust    (state-       (EXECUTABLE
                       stress, change       trust,        recover paths)            region,   dependent      window,
                       points, hysteresis)  commit, …)                              change    thresholds)    ADVISORY
                                                                                     cost)                    tail)
```

Modules: `adaptive/signals.py`, `adaptive/change_point.py`, `adaptive/state_estimator.py`,
`adaptive/controller.py`, `adaptive/conditional_scenarios.py`, `adaptive/engine.py`;
optimizer additions in `optimization/multi_period_sp.py`; harness and API integration in
`backtesting/counterfactual.py` (`policy_adaptive_sp`, posture-aware `_scenarios`),
`backtesting/safe_selector.py` (`safe_select(..., posture=)`), `api/routers/fmcg.py`
(`GET /fmcg/state`, `POST /fmcg/plan`).

## 3. Signals: provenance, freshness, absence

Every observation that reaches the estimator is a `Signal(timestamp, entity_type, entity_id,
metric, value, provenance, quality, refreshed_at, transform)`. Provenance is one of
`REAL_OPERATOR, REAL_PUBLIC, INFERRED, ASSUMED, SYNTHETIC_CALIBRATED`. The `SignalStore`
answers three questions for every (entity, metric): *is it available, how old is the latest
observation, is it stale* (older than `max_age_days`). Queries are dated: `series(..., as_of)`
returns only observations at or before `as_of`, so the fold tests cannot leak.

Two rules that matter commercially:

* **Missing ≠ normal.** A route with no port signal makes the supplier's `port` stress
  component 0.35, adds a WATCH score, lowers `data_quality`, and says so in the reasons.
  It never contributes a "conditions normal" reading.
* **Stale ≠ current.** A stale observation keeps half its evidence weight.

The one public adapter shipped is IMF PortWatch (`load_portwatch_signals`): monthly import
tonnage for a port divided by its trailing twelve-month median, stamped with the month it
describes, `refreshed_at` the file's modification time. Operator flags (`operator_disruption_flag`)
are `REAL_OPERATOR` signals with a severity in [0, 1].

## 4. Change points: one bad delivery is not a regime

`adaptive/change_point.py` has three detectors, all one-pass over the prefix they are given:

* **CUSUM** on standardised deviations from a reference window (`k` = 0.5 sd allowance,
  `h` = 5 sd decision interval). Standardised deviations are clipped at ±4 sd and the
  reference sd is floored at 2% of the level, so a single wild point contributes at most 3.5
  and cannot fire the alarm alone; a second consecutive bad point can. *One bad delivery is
  an event, two in a row are evidence.*
* **Page–Hinkley** for a mean decrease, with `delta` and `lambda` scaled to the series' own
  standard deviation (0.5 sd and 4 sd), so a supplier that has always filled 85% ± 8 is not
  in a regime change.
* **Recent vs long-run** shift in sd units (the plainest drift measure, always reported).

A change-point alarm only counts as evidence when the estimated shift is *material*
(≥ 6 fill points). Alarms report the index at which evidence accumulated, so a report can say
*when* the shift started, not only that it did.

## 5. State estimator

### 5.1 Regimes and probabilities

Ten regimes: `CALM, NORMAL, WATCH, TIGHT, DEMAND_VOLATILE, SUPPLY_CONSTRAINED,
PORT_DISRUPTION, SEVERE_DISRUPTION, PROMOTION, RECOVERY`. Four are *disruptive*
(`TIGHT, SUPPLY_CONSTRAINED, PORT_DISRUPTION, SEVERE_DISRUPTION`); six are *supply regimes*
(the four plus `WATCH, RECOVERY`).

Each entity accumulates an evidence score per regime from named, interpretable features and
the probabilities are the softmax of the scores at temperature 0.6, over a prior that puts
mass on NORMAL (score 2) and CALM (score 1). With no evidence the disruptive mass is about
10%; evidence has to overcome the prior, which is the point.

**Supplier** (`supplier_state`): features are recent and long-run fill, fill shift, fill sd,
lead ratio, lead sd, port index. Evidence rules (all relative to the supplier's own history):

| evidence | regime score |
|---|---|
| fill shift < −6 pts, not yet sustained | WATCH +1.5 |
| sustained (material change point) and declining | SUPPLY_CONSTRAINED +2.5 + 4·depth/0.3, TIGHT +1 |
| recent fill < 70% and > 25 pts below own norm | SEVERE_DISRUPTION +2 + 4·(depth−0.25)/0.3 |
| trough behind, recent fill back within 6 pts of norm | RECOVERY +2.5 |
| chronically low fill, no recent change | SUPPLY_CONSTRAINED +0.5 (a known feature, priced by the incumbent) |
| lead ratio > 1.3 | TIGHT +1.5, PORT_DISRUPTION +1 |
| port index < 0.70 / < 0.85 | PORT_DISRUPTION +2.5 / WATCH +1 (×0.5 if stale) |
| port signal unavailable | WATCH +0.5, data quality ×0.85 |
| none of the above | NORMAL +1, CALM +1 if sd < 0.04 |

**SKU** (`sku_state`): demand CV, level shift (CUSUM), intermittency, spike ratio, cover in
periods, planned promotion. A SKU sourced from a disrupted supplier *is* supply-disrupted:
the supplier's supply-regime mass enters the SKU distribution as a mixture,
`p_sku(r) ∝ p_sup(r)·[r ∈ supply] + p_own(r)·(1 − Σ_supply p_sup)`, so nothing is diluted by
the number of regimes.

**Portfolio** (`aggregate`): value-weighted mixture of SKU probabilities and stress, plus
`value_share_disrupted`, the share of value in SKUs with p(disruptive) > 0.5. A third of the
portfolio at p = 0.8 is a disruption whatever the mean says; the posture uses
`max(p_disruptive, stress, value_share_disrupted)` as severity.

### 5.2 Stress score

`S ∈ [0, 1]` is a weighted sum of named components, each in [0, 1]:

* supplier: fill level (0.30), fill decline (0.25), fill variance (0.10), lead drift (0.15),
  lead variance (0.05), port (0.15);
* SKU: demand CV (0.25), demand drift (0.15), cover (0.25), supply = supplier stress (0.35).

Components are reported with the score, so "stress 0.62" always comes with "fill level 0.8,
lead drift 0.5, port unavailable".

### 5.3 Hysteresis and smoothing

`StateTracker` smooths probabilities across updates (EWMA, α = 0.5) and holds a
`posture_disrupted` flag that is **entered** when smoothed p(disruptive) > 0.60 and **left**
only after p(disruptive) < 0.35 for two consecutive updates. `TrackerBank` keeps one tracker
for the portfolio and one per SKU, so hysteresis is applied where the trust regions are.
A single wobble cannot flip the engine; the unit test `test_tracker_does_not_thrash_on_a_single_wobble`
pins the exact sequence.

### 5.4 Leakage

`estimate(fi, ...)` reads supply events keyed relative to the fold origin and uses only keys
< 0; the signal store is queried `as_of` the origin. `TestEngineLeakage` puts a catastrophe at
and after the origin and checks the state is identical to the clean history.

## 5.5 Leading indicators: forecasting trouble before receipts show it

Receipts lag: the validation measured four to ten weeks from the onset of a supply
episode to detection, because a fill shortfall is only observed when the delayed order
lands. `adaptive/indicators.py` and `adaptive/leading.py` add public, keyless feeds that
move earlier, each cached by `scripts/fetch_indicators.py` with a `fetched_at` stamp:

| feed | source | index | reaches the estimator as |
|---|---|---|---|
| chokepoint transits (Bab el-Mandeb, Suez, Hormuz, Cape) | IMF PortWatch, daily AIS | 7-day mean / trailing 365-day median | lane outlook |
| port throughput (Aqaba) | IMF PortWatch | monthly imports / trailing 12-month median | port evidence and lane outlook |
| shipping news coverage per lane | GDELT DOC 2.0 | 7-day coverage share / trailing 180-day median | lane outlook |
| Global Supply Chain Pressure Index | NY Fed | level (sd units) | lane outlook |
| Brent crude | FRED | 30-day mean / trailing 365-day median | lane outlook |
| Freight Transportation Services Index | FRED | 12-month change | lane outlook |
| retail sales, consumer sentiment | FRED | 12-month change; 5-year z-score | demand outlook |

`disruption_outlook(store, route, as_of)` combines whatever is available into a logistic
risk with a named contribution per feed and a **quality** that falls with every feed that
is missing or stale. Missing feeds contribute nothing and are listed; a lane with no feeds
gets quality zero and the words "outlook UNAVAILABLE". The weights are design constants,
labelled ASSUMED. The supplier state reads the outlook as WATCH evidence (and, when the
excess risk is large, PORT_DISRUPTION evidence) scaled by the outlook's quality, so it can
raise the posture before the first short delivery, but a one-feed outlook counts for little.

Whether these feeds actually lead is a question, not an assumption:
`scripts/validate_leading_indicators.py` cross-correlates each indicator with Aqaba's
import index at leads of zero to twelve weeks over the full span and over the Red Sea
crisis, with a noise floor of 2/√n, and writes the answer, positive or negative, to
`docs/validation/evidence/leading_indicators.md`.

## 5.6 The demand channel

Demand evidence has its own severity: `demand_severity` per SKU from the DEMAND_VOLATILE and
PROMOTION probabilities, the demand drift component and a detected level shift, value-weighted
to the portfolio. It widens the scenarios, opens the *upside* of the trust region
(`demand_trust_open × demand_severity`), shortens the commit window and admits the
stochastic candidate, without pretending a supply problem exists. This is the fix for the
negative result in the first transition validation, where a demand-only shock left the
optimizer pinned to the incumbent.

## 6. Posture: what the state changes

### 6.0 Three modes, one continuous mapping

Severity `t = max(p_eff, S, value_share_disrupted)` selects a mode, with the trackers'
hysteresis upstream so it cannot flicker:

| mode | when | what the optimizer is allowed |
|---|---|---|
| **EFFICIENCY** | t < 0.25 | optimise ordinary expected cost: trust region **off**, light anchor (ρ scale 0.25), every candidate admitted, the safe gate at its normal bar (lower bound must beat the incumbent by 2% at 80% confidence on the operator's own history), commit window 4 |
| **BALANCED** | 0.25 ≤ t < 0.55 | trust region by SKU severity, anchoring and CVaR rising with t, gate tightening |
| **PROTECTION** | t ≥ 0.55 | tight trust region, CVaR weight up to 1.0 at α 0.95, regret budget, commit window down to 1, robust candidate when the estimator itself is uncertain |

In every mode the engine keeps reading the state at each review and re-deriving the
posture; the mode is a label on a continuous mapping, not a switch that changes the code
path. The safe gate protects the incumbent in efficiency mode the way it always has: by
evidence on the operator's history, not by a bound.



`posture_from_state` maps severity `t = max(p_eff, S, value_share_disrupted)` (with `p_eff`
raised to 0.6 while the tracker holds the disrupted flag) through monotone interpolations:

| knob | calm (t = 0) | disrupted (t = 1) | where it acts |
|---|---|---|---|
| scenario width (demand spread scale) | 0.85 | 1.35 | `widen_demand` |
| persistence (block length) | 2 | 5 | `conditional_supply_paths` |
| CVaR weight λ on baseline-relative regret | 0.10 | 1.00 | objective |
| CVaR level α | 0.80 | 0.95 | objective |
| regret budget (share of baseline expected cost) | none | 0.15 + 0.35·(1−t) | hard constraint, relaxed and reported if infeasible |
| anchoring scale on ρ_j | 0.25 (efficiency) / 0.75 (calm) | 0.25 | L1 penalty, × (1.5 − autonomy) |
| trust region per SKU | off (efficiency) / 5% | 15% / 40% / 80% by SKU severity, + 0.6 × demand severity | MILP bounds |
| plan-stability cost (per unit changed, × unit cost) | 0.02 | 0.005 | objective |
| commit window (weeks) | 4 | 1 | EXECUTABLE / ADVISORY split |
| selection threshold (lower bound must beat) | 2% (efficiency) / 3% | 2% | safe gate |
| selection confidence | 0.80 (efficiency) / 0.85 | 0.75 | safe gate |
| candidates admitted | all (efficiency); order_up_to, deterministic_sp, anchored_sp, adaptive_sp (balanced) | + stochastic_sp when t > 0.45 or demand severity > 0.4; + dro when p > 0.5 and data quality or calibration is poor | safe gate |

In calm periods the optimizer is held close to the incumbent, charged for churn, allowed to
commit four weeks, and must clear a high bar to replace the incumbent. In disrupted periods it
is given room, risk aversion on the *downside relative to the incumbent* rises, scenarios
widen and persist, the commit window shrinks to one week, and the robust candidate is
admitted only when the estimator itself is uncertain.

### 6.1 Autonomy score

`autonomy = clip(0.15 + 0.45·S + 0.40·evidence_strength)`, then capped by data quality
(< 0.6), scenario-calibration confidence (< 0.5) and economics provenance (< 0.7). The
reasons for every cap are returned. Autonomy scales every SKU's trust region
(× (0.5 + 0.5·autonomy)) and the anchoring scale. *Less evidence = less autonomy, always.*

### 6.2 State-evidence selection

The safe gate evidences a candidate on backtest folds inside the training window. When a
large share of value has just had a demand level shift, every fold predates the shift, so
the gate cannot see the value of responding and would retain an incumbent that is now
under-ordering (the first validation measured exactly that). In that one situation the
state itself is the evidence: if `demand_severity ≥ 0.5` and the fresh-shift value share
is ≥ 0.3, the gate runs the state-conditioned candidate with a **hard** regret budget
(10% of the incumbent's expected cost under the conditioned scenarios) and accepts it only
if the budget held; otherwise it falls through to the backtest gate. The decision says
`selection_basis: state` and carries the reason. Supply-side departures are never selected
this way: for those the receipts and the leading indicators are the evidence, and the
protection posture bounds what the optimizer may do.

## 7. Conditional scenarios

`conditional_supply_paths` starts from the moving-block bootstrap of the supplier's own
history (block length = the posture's persistence) and, per scenario and per **route**,
draws a disruption path with the route's estimated p(disruptive). A path is deterioration →
trough → recovery (`DisruptionProfile`). Its depth and length are learned from the worst
observed below-norm episode in the supplier's own history when there is one (`MEASURED`),
otherwise the default profile is used and labelled `ASSUMED` in the scenario assumptions.
Every supplier on a route degrades together in the same scenarios. A route the estimator
reads as RECOVERY starts its path in the recovery leg. Lead times are stretched with fill
loss. Demand spread is scaled by the posture width without moving the mean.

Because `_scenarios` applies the posture to **every** optimizer candidate in a fold, the
safe gate compares policies, not scenario sets.

## 8. Optimizer additions

Inside `MultiPeriodStochasticLP` (so MOQ, pallet, capacity and service constraints still hold):

* **Trust region.** For each (supplier, product, period) with baseline `b`:
  `max(b − w, 0) ≤ x ≤ b + w`, `w = max(frac_j · b, one lot)`. The lot floor means pack
  rounding can never make the region empty.
* **Plan stability.** `x − x_prev = c⁺ − c⁻`, objective `+ Σ κ_j (c⁺ + c⁻)`, `κ_j` = unit cost ×
  the posture's change-cost rate. Zero rate reproduces the free problem exactly
  (`test_zero_change_cost_is_the_free_problem`).
* Existing: L1 anchoring `ρ_j |x − b|`, CVaR_α of baseline-relative regret with weight λ and
  optional hard budget, fixed-schedule evaluation, service floors scoped to the reachable window.

`policy_adaptive_sp` composes these: conditioned scenarios → anchored solve with the posture's
λ, α, ρ scale, trust region and change cost → if the regret budget is exceeded, re-solve with
the budget as a hard constraint → if the service floor is unattainable inside the trust
region, drop the floor and say so (`floor_relaxed`, counted as a fallback by the gate) → if
still infeasible, widen the region once and say so.

## 9. Rolling horizon and replanning

Only the first `commit_window` weeks of a plan are EXECUTABLE; the tail is ADVISORY. The
window is the smaller of what the operator asked for and what the posture allows. The API
reports the state-derived replanning triggers: a change-point alarm on any supplier, a
demand level shift, a port index below 0.85 or a signal going stale, the portfolio
p(disruptive) crossing the enter/exit threshold, an inventory discrepancy, a promotion change.
The closed-loop harness carries the previously published schedule so the plan-stability cost
is charged against what the operator actually saw last review.

## 10. What is measured, what is assumed

| element | status |
|---|---|
| supplier fill and lead series | REAL OPERATOR (from POs and receipts) |
| port throughput index | REAL PUBLIC (IMF PortWatch), monthly, stale after 75 days |
| chokepoint transits, GSCPI, freight, fuel, news coverage, retail sales, sentiment | REAL PUBLIC (IMF PortWatch, NY Fed, FRED, GDELT), cached with fetch stamps; whether they lead is tested, not assumed |
| outlook weights | ASSUMED design constants, reported per call with each feed's contribution |
| disruption path depth/length | MEASURED from the supplier's own history when an episode exists, else ASSUMED and labelled |
| posture constants (table in §6) | design constants, developed on calibration seeds, never fitted to evaluation seeds |
| regime evidence scores | design constants, transparent, listed in §5.1 |

The engine has not been run on a real operator's live data. Every number in the validation
document comes from the calibrated synthetic distributor with unseen evaluation seeds and
from the public series named above. See the validation document for negative results.
