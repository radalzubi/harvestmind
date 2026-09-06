# Service reliability: LEAN, PROTECT, ALLOCATE, RECOVER

Branch `claude/zaad-service-reliability`, stacked on `claude/zaad-pr24-release-blockers`
(PR 25), which sits on PR 24 and PR 23. Nothing is merged. Autonomous PO execution stays
off. The frozen PR 23/PR 24 engine is preserved as `engine_profile: "pr24"` on every
request and runs unchanged in the paired benchmark; the new behaviour is
`engine_profile: "reliability"`, the default. No frozen evidence was retuned. All changed
numerical behaviour was measured on new seed splits `development3` (26001),
`validation3` (27001, 27002) and `holdout3` (28001, 28002, frozen).

The objective: remain lean when it is safe, buy protection early enough when uncertainty
becomes economically dangerous, allocate by customer priority when targets are impossible,
recover, and return to lean. Not: hold more stock everywhere.

## 1. Protection that responds to uncertainty (`zaad/full/protection.py`, `uncertainty.py`)

Protection per SKU and location is assembled from named drivers, each in units, with the
quantile set by the priority- and demand-weighted service target of the customers served:

| Driver | Source |
|---|---|
| Demand spread | calibrated one-step residual spread of the chosen forecast since the last change, over the replenishment window |
| Forecast level | standard error of the level, widened while a detected regime change is younger than eight observations |
| Lead-time spread | the cheapest usable source's own censored lead-time tail (Kaplan-Meier from shipment history) or its declared spread, labelled `observed` or `declared` |
| Fill spread | that source's accepted-ratio spread and partial-delivery probability, observed or declared |
| Inbound ETA risk | open POs weighted by their late probability |
| Correlation | capacity-weighted effective number of independent sources; sources sharing a supplier or any failure domain count as one, and route nodes (ports, borders, terminals) are failure domains automatically |
| Substitution credit | approved substitute stock already at the location, at the conversion ratio |
| Replenishment | periods until the next feasible receipt |

There is no universal buffer factor. The projected base-stock proxy (the incumbent when no
operator policy is declared) uses this quantile and spread instead of the frozen 1.645.
Each row carries an explanation, for example "A at branch needs more protection: the
supplier lead-time tail contributes 12 of 23 units; sources share port so they count as 1.0
independent source" or "A at branch does not need extra inventory: replenishment lands
within 2 periods and approved substitute stock covers 100 units."

Inside the optimizer, protection is scenario-derived: the reliability profile adds a
quantile (CVaR) service constraint (`service_risk="cvar"`, Rockafellar-Uryasev form) so the
mean service over the worst half of scenarios must also meet each target, and it adds a
`hedged_network` candidate in which the declared stress envelopes enter the solve at an
evidence-weighted probability (section 10).

## 2. Customer-specific service levels

Targets were already per SKU x location x customer on `Service`; allocation already served
by priority then contribution. Added: `Customer.service_class` for reporting by contract
class; protection quantile weighted by each customer's priority and demand; reliability
metrics reported per service and aggregated per class; and priority-consistency checks so
a recovery may lower a service only to raise a strictly higher-priority one. Unit fill,
line fill, order fill, OTIF and order OTIF remain distinct metrics.

## 3. Demand-surge response (`zaad/full/surge.py`, `forecast.py`, `scripts/study_zaad_surge.py`)

Two detectors were added beside the frozen two-sided CUSUM and the asymmetric variant:
Page-Hinkley (origin dated from the start of the evidence run) and Bayesian online
change-point detection (Adams-MacKay, Gaussian mean, variance floored at the mean for
count-like demand, a material-change filter so an outlier's aftermath does not reset the
level). All four were replayed observation by observation through the forecast on nine
patterns (stable, one-week spike, two-week spike, level shift, gradual growth, known
promotion, unknown promotion, launch, seasonal) over 40 development and 40 validation
seeds. Metric: the same shortage/holding decision loss the forecast tournament uses.

| Mode | Development loss | Validation loss | Level-shift delay | Persistent detected | False-alarm share |
|---|---|---|---|---|---|
| symmetric (frozen) | 4431.8 | 4355.6 | 2 | 1.00 / 0.91 | 0.62 / 0.61 |
| asymmetric | 4415.7 | 4288.0 | 2 | 1.00 / 0.93 | 0.59 / 0.52 |
| page_hinkley | 4581.8 | 4414.2 | 2 | 0.80 / 0.74 | 0.57 / 0.56 |
| bocpd | 4731.9 | 4530.7 | 2 | 0.92 / 0.87 | 0.44 / 0.46 |

Reading: every detector reacts to a genuine shift within two observations and none resets
on a single spike; the frozen CUSUM family is the best on total decision loss, and the
asymmetric rule is marginally better on both splits (1.5% on validation). BOCPD panics
least but adapts worst; Page-Hinkley misses a share of persistent shifts. Because the
earlier validation2 study showed the asymmetric rule adding service breaches on decrease
cells under the gated planner, `symmetric` stays the default; `asymmetric`,
`page_hinkley` and `bocpd` are opt-in on `Request.demand_adaptation` with their evidence
retained in `docs/zaad_full/evidence/surge/` (first pass with a BOCPD variance bug is kept
as `dev_v1_first_pass.json`). The panic-buying guard is the level standard error: a young
regime widens uncertainty rather than committing the plan to the new level.

Regime uncertainty and calibration also feed the scenario draw: sampled deviations are
widened by the realized-error calibration ratio when the fitted spread has under-covered,
and each world carries a level multiplier drawn from the level standard error.

## 4. Supplier delay and fill-rate distributions

`supply_profile` builds, per source, the accepted-ratio distribution (mean, spread,
partial-delivery probability) and the unconditional Kaplan-Meier lead-time support from
its own shipment history, with open orders as right-censored records and an explicit
unresolved tail mass. Below six records the declared parameters are used and the profile
says `declared`. In the reliability profile the world generator draws fill and delay from
the observed profile through the shared factor (a copula-style mapping of the common shock
to the empirical quantiles), so a supplier whose observed tail has widened produces later,
shorter deliveries in the scenarios. "Late" means later than the declared lead by more
than half a planning period.

## 5. Correlated failures

`failure_domains_for` adds every intermediate itinerary node to a source's declared
resource failure domains, so two suppliers through one port share the common shock in the
scenario factor model and count as one source in `diversification`. The report shows the
shared domains and the effective number of independent sources. This is the transparent
common-factor approach; no copula fitting is attempted on synthetic data.

## 6. Alternatives, transfers and substitution valued from solves

`alternative_value` re-solves the reference candidate with approved alternates, transfers
or substitutions removed and compares on the selection worlds: extra cost of using the
option versus expected and worst-world shortage exposure avoided and the per-service
change. Verdicts are `necessary` (infeasible without it), `justified`, `cost_saving`,
`not_justified_on_modeled_evidence`, and for substitution `service`, `cost_only`,
`service_and_cost` or `no_modeled_benefit`, because a substitute that only saves cost is
not a service improvement. Transfers already compete with purchases in the network solve;
the value report makes the trade visible.

## 7. Selector changes (`planner.py`)

- Feasible candidates are ranked by hedged cost: fitted expected cost plus the declared
  stress at its evidence-weighted probability. Protection is bought when the stress
  downside is expensive enough at that weight, not otherwise.
- Service-first acceptance: when the incumbent misses a target under independent
  confirmation and the candidate meets every target, the candidate is accepted inside the
  economic downside cap; it does not have to be cheaper. When the incumbent already meets
  service, the frozen cost-first rule applies, with the benefit hedged by the same stress
  weight.
- Stress gate: when the per-world stress solve is infeasible (no plan can meet the SLA
  under the declared stress), the gate asks for "not worse than the incumbent" under
  stress (physically usable, within the cost cap, no larger weighted shortfall, priority
  consistent) instead of an impossible SLA, which under PR 24 rejected every candidate and
  retained an incumbent that failed the same stress. When the stress targets are feasible,
  the full SLA under stress is still required.
- Recovery (PR 24/25 logic) unchanged: ranked priority-weighted shortfall, material
  margin, priority consistency, downside cap.

## 8. Shortage classification and reliability metrics

`service_reliability` in every report: requested, achieved, best modeled jointly feasible,
incumbent, ZAAD, avoidable service loss, unavoidable shortfall, service regret,
worst-case stress service, stockout period share, weighted shortfall, customer-priority
weighted service, by customer class. Each service miss is classified `UNAVOIDABLE` (with
`pre_existing` when even the single-service frontier misses, `under_stress` when only the
declared stress makes it infeasible), `AVOIDABLE`, `ECONOMIC_TRADEOFF` (blocked only by
the downside cap), or `DATA_INSUFFICIENCY`; `MODEL_FAILURE` is judged ex post in the
benchmark (realized demand or supply far outside the review-time model on two or more
reviews). The benchmark classifies every breach the same way against the other methods on
the same cell and seed.

## 9. Reliability benchmark (`--matrix reliability`)

56 cells: one-factor-at-a-time around a balanced centre plus 30 seeded random grid points
over inventory {low, balanced, high}, demand {stable, volatile, promotion, increase,
decrease, intermittent, spike, temporary spike, gradual, unknown promotion}, supply
{stable, variable fill, late, severe delay, partial delivery, correlated outage}, network
{single, two locations, central plus branches}, alternatives {none, supplier, route,
transfer, substitution} and service {90, 95, 97, 99}. Methods: frozen base stock,
stochastic, robust, the new `protected` (CVaR on fitted worlds), `gated_pr24` (frozen
gated planner) and `gated` (reliability profile). Measured per replay: service, breach,
ex-post breach class, weighted shortfall, inventory in periods of demand, working capital,
cost, emergency reviews, false protection on benign cells, recovery time.

<!-- EVIDENCE -->

## 10. What the evidence says

Development3 passes (all retained under `docs/zaad_full/evidence/reliability/`):

- `dev3_a`: first reliability profile (CVaR candidate, service-first acceptance, no stress
  weighting). Breaches 37 vs 38 for the frozen gated, median service .927 vs .872, but
  inventory 1.79 vs 1.26 periods and 17 cost losses. Not material.
- `dev3_b`: stress weight fixed at .2 (crashed on an unusable-row bug after 18 cells;
  partial rows kept): 3 breaches vs 12 on those cells, but benign inventory 2.9 periods,
  the "robust permanently overstocks" failure.
- `dev3_c`: evidence-weighted stress (credibility floor .25): breaches 34 vs 38,
  avoidable 8 vs 12, median service .932 vs .872, paired service wins 31 / losses 11, cost
  wins 24 / losses 26, saving vs base stock 2.27% vs 1.95%, inventory 1.68 vs 1.26
  periods, benign inventory 1.23 vs .57.
- `dev3_d` (stable-supply cells only, floor .10 vs .25): floor .10 holds 1.25 periods
  (vs 1.39 at .25 and .99 frozen) at the frozen breach count and a lower median cost;
  floor .25 trades three fewer breaches for that inventory. Floor .10 was adopted on the
  stated principle (less inventory when the supply record is clean).
- `dev3_e` and `validation3`: see the tables below.

VAL3_PLACEHOLDER

## 11. Remaining failure families

1. **Model failure on demand surprises.** One-week spikes, unknown promotions and volatile
   demand produce realized demand far outside the review-time model; every method breaches
   there, and protection sized from history cannot prevent it without holding for events
   that have not been declared. Known events (declared promotions) are handled; unknown
   ones are detected only after two observations.
2. **Correlated and severe supply outages.** With a single shared port and a 6-period
   outage at 50% fill, no method meets 95% on the horizon; the classification is
   unavoidable and the recovery plan allocates by priority. Alternatives help only when
   they are genuinely independent, which the correlated cell deliberately denies.
3. **Central-plus-branch networks with the source moved to the centre.** Transfer lead time
   plus supply lead time exceeds what a 95% target allows from a two-period cover; the
   miss is unavoidable in the benchmark's geometry but shows that protection has to be
   placed upstream earlier than the review loop currently does.
4. **False protection on benign cells** is reduced but not zero: the declared stress keeps
   a floor of a tenth of its weight, which costs about a quarter of a period of demand on
   clean single-source cells relative to the frozen planner.
5. **Data sufficiency.** Supply profiles need six arrived records before they are
   observed; until then the declared parameters govern and the profile says so.
6. **No real operator data.** Everything above is synthetic; the calibration ratio, level
   standard error and credibility floor were chosen on development seeds and confirmed on
   validation seeds, not on customer history.
