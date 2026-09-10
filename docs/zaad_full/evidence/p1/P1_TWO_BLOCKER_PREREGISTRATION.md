# P1 two-blocker closure: pre-registration (T, then B)

Written at `4f49322` before any T or B regression run. Corrections are appended, dated, never edited in
place. Benchmark: the declared rolling 52-review landed-cost evaluation of `P1_BENCHMARK_PREREGISTRATION.md`,
unchanged. Legacy record kept beside it.

## Part I, T: protection provenance and the stress gate on purchasing reviews

### T1. Where FALSE_PROTECTION_RISK comes from (traced, `scripts/p1_flag_trace.py`, `closure/flag_trace_*.json`)

`zaad/full/protection.py`, inside `protection_profile`, per SKU / location:

```
protection     = max(0, z * sqrt(var_demand + var_level + var_supply) + inbound_at_risk - substitute_cover)
lean_baseline  = max(0, z * sqrt(window * sd_fitted^2 + var_supply_declared) - substitute_cover)
FALSE_PROTECTION_RISK  iff  activity <= .05  and  protection > 1.25 * lean_baseline + 1
```

* Source fields: the fitted demand spread with calibration widening (`sd`), the level standard error
  (`var_level`), the observed source lead / fill spread (`var_supply`, from `supply_profiles`), open
  orders at late risk (`inbound_at_risk`), against the fitted spread and the source's declared spread.
* Threshold: 1.25 of the lean baseline plus one unit; activity at or below .05 (no active driver).
* Relation to inventory: none. On-hand, pipeline, inherited stock and previous actions do not enter the
  flag. Traced on T: every flagged review has zero units in the pipeline and on-hand between 116 and
  1,036 units; the ratio is 1.32-1.94 on T and G, 8.1 on P0 cell 21 (a real supply driver there, and
  the cell is P0-owned by its declared mandate regardless).
* Relation to protection_units: it IS the ratio of recommended protection to the lean baseline.
* Relation to the planner owner: `ownership.planner_owner` lists the flag as a P0 reason ("inherited
  protection under management"); on T it is the sole reason on 6 of 7 P0-owned sub-economic reviews.
* Purchase provenance: not known anywhere and not needed by the flag.
* Can the flag distinguish economic cycle stock, service protection stock and recovery stock? No: it
  says nothing about stock. It says "with no driver active, the protection recommendation is inflated
  by non-driver uncertainty terms". Occurrence: A, I, P never (single SKU); G once in 52 reviews; T on
  2 / 14 / 18 SKU-reviews per seed; P0 cells 15, 16, 20 never, 21 twice.

### T2. Provenance state: existing canonical state suffices

Protection or recovery stock can only exist as the consequence of an accepted PROTECT or RECOVER
decision, and every such situation is already canonical state the router reads: an active driver
(`activity > .05`), a decaying driver (`decaying`), a non-LEAN `regime` (PROTECT / RECOVER, whose RECOVER
definition is exactly "stock above the lean baseline while the driver has gone quiet"), the
RECOVERY_IN_PROGRESS flag, a confirmed demand decline, a non-calm screen state, a declared stress
mandate, or a recovery obligation. The replay additionally carries `inherited_on_hand` (stock the
optimizer did not buy). No new provenance account is needed to distinguish economic cycle stock from
protection stock: cycle stock is stock held while every one of those signals is absent. Nothing is
built (brief: "do NOT build new state unnecessarily").

### T3. Pre-registered ownership rule (rule T-A)

FALSE_PROTECTION_RISK alone is not a P0 ownership reason. P0 owns a review when canonical evidence of
protection or recovery being managed exists: declared mandate, adaptive escalation off, non-calm state,
active or decaying driver, non-LEAN regime, confirmed decline, or a recovery / service obligation (the
existing reasons, unchanged). The flag itself stays computed and reported exactly as before and P0's own
machinery uses it unchanged whenever P0 owns. Change is confined to `zaad/full/ownership.py` (P1 code).
No fixture, seed, order-size or inventory threshold; no reference to T.

Expected effect, stated before running: T's P0-owned reviews fall from 19 / 11 / 2 per seed to the
reviews with a real driver; the frozen-objective deferrals on those reviews disappear; the six P0 cells
are unaffected because each is P0-owned by its declared mandate on every review (owners 100% P0 in every
arm), so the six-cell arm must stay 120 / 120.

### T4. The stress gate on P1-owned reviews (mapped)

Call site: `planner.plan`, the loop `for i, stress in enumerate(req.stresses)`: adversary worlds
`draw(req_draw, seed + 30000 + i, scenarios, stress)`, `before` / `after` = incumbent and chosen candidate
evaluated on them (with the P1 terminal rule when P1-owned), `physically_ok`, `downside_ok` (per-world cost
cap AND per-service floor `_floor(req_gate, incumbent_service, s) - tolerance`), `service_under_stress`,
then `stress_gate` -> strict / not_worse / rejected. `req_gate` carries `service_gate_basis`: "incumbent"
(V7 / P0: the incumbent's own level is the bar) or "target" (a service at or above its target has not
worsened), chosen as "target" only when the request opts in AND the review is lean. The product default
is "incumbent" (kept after the unconditional target basis regressed P0 cells 20 / 21 / 90 / 108).

On a P1-owned review the declared stress is the identity by construction (a non-identity envelope is a
mandate and routes to P0), so the "stress" worlds are fitted worlds. At T 41003 review 9 (P1-owned): every
candidate proposed the 1,056 + 864 load; `physically_usable` True, `service_met` True (.964 / .969 against
.95), cost 14,790 against 23,423 on every world; `within_downside` False solely because the incumbent
(weekly replace-sold) serves 1.000 on those worlds and the floor is its level; gate mode "rejected";
materiality never reached; the incumbent's 192 + 120 executed. Review 47: the same.

### T5. Pre-registered gate rule (rule T-B)

On a review the P1 purchasing planner owns, the service floor of every gate that compares a candidate
with the incumbent uses the target basis (`min(incumbent level, target)`): a candidate that meets every
service target has not worsened service. On a review P0 owns, the basis is exactly what it is today
(the request's own setting, "incumbent" by default, or "target" on a lean review when the request opts
in). The gate itself still runs on P1-owned reviews: physical usability on every world, the per-world
cost cap against the incumbent, the service targets, priority consistency, and materiality. Effective
stress on a P1-owned review is the identity; if a request declares a non-identity stress the review is
P0-owned and nothing changes. No future truth enters: ownership and the basis are decided from the
review's snapshot before any candidate is evaluated.

Expected effect, stated before running: the P1-owned RETAIN_INCUMBENT outcomes on T (reviews 9, 47 of
seed 41003), G (37) and B (4, 41) become accepted lot plans where the candidate meets service; P0 cells
unchanged (P0-owned throughout).

### T6. Acceptance for T (stage 7): T <= +2.00% at the declared benchmark AND a sensible mechanism
(sub-economic orders gone or explained, service at or above the legacy level, P0 arm 120 / 120 apart from
recorded cell-21 variability). Controls (stage 8): A, G, I, P, Q, C, O plus the six-cell P0 arm.

## Part II, B: economic lot-cycle planning horizon (rule written before the B sweep; the sweep is
diagnostic and does not pick the rule)

### B1. Diagnostic sweep grid: P1 planning horizon 12, 16, 20, 24, 32 on B, everything else unchanged
(52-review evaluation, same truth). Read: first order quantity, cadence, cost, fixed order cost, carrying,
financing, service, order count, runtime, delta vs EOQ. Not used to choose the horizon.

### B2-B3. Horizon rule (rule B-A), derived from declared economics known at the review

```
reference lot L*         = min(load limit, max(EOQ on the supplier's fixed costs, MOQ, MOV units, one period of demand))   (lotsizing.reference_lots)
economic cycle periods   = ceil(L* / expected demand per period of the supplier's lines)
visibility horizon       = lead periods (order-to-arrival of the cheapest source) + economic cycle periods + 1 (the review after the lot lands)
P1 planning horizon      = max(request horizon, visibility horizon), capped at the request validator's maximum (52 periods)
```

Applies only when the P1 purchasing planner owns the review; a P0-owned review keeps the request horizon
and everything frozen. The planning request is extended the way the rolling replay extends it (declared
period data repeated, no fabricated demand: the forecast is the fitted level over the longer horizon,
which is what the twelve-period plan already assumes). If the visibility horizon would exceed the cap,
the cap is used and the case is reported (runtime guard); no silent truncation below the cap. Runtime is
reported per fixture (p50 / p95 / max) and the ceiling is the existing solve budget scaling
(`solve_budget`, quadratic in horizon / 12).

Expected per-fixture horizons, stated before running: B 1 + 19 + 1 = 21; J / K 1 + 11 + 1 = 13; L 1 + 11
+ 1 = 13; G / T (2,000 / 1,920-unit loads at 200 / week) 1 + 10 + 1 = 12 (base); I 1 + 5 + 1 = 7 (base
12); C / P / O / A / D / E / F / H / M / N / Q / R: base 12. So only B, J, K and L extend, and J / K / L
already pass; the rule is not tuned to B (B's horizon follows from its own $250 / 1,854-unit economics).

### B4. Acceptance: B <= 2% AND stability around the derived horizon (the sweep shows the decision does
not change between the derived horizon and the next grid point) AND controls G, I, T, J, K, L, C, P, O, A
unchanged or improved AND P0 horizon unchanged (six-cell arm 120 / 120).

### T1 addendum (recorded after the component trace, before the T run): what inflates the flag on T

`closure/flag_trace_T_combined_realistic_41003.json`, flagged reviews 16 / 20 / 24: protection 20.9-22.6
units against a lean baseline of 14.8-14.9 (ratio 1.41-1.53); demand forecast `calibration_ratio` 1.42-1.53
(realized one-step errors 8.8-9.5 against a fitted spread of 6.2), `regime_age` None, `level_se` 1.0-1.2,
pipeline 0, replenishment window 2. The ratio of protection to lean baseline equals the calibration
ratio to two decimals: the flag on T is the forecast's calibration widening (`sd` against `sd_fitted`),
below the 1.25-plus-driver threshold that would make it an active demand driver, and nothing else. It is
a forecast-calibration state, not an inventory state, and not a consequence of the lots.

### B, dated note (2026-09-09, after the T controls and the diagnostic sweep): rule B-A is NOT implemented

Under rules T-A / T-B alone B moves from +2.49% to +1.60% at the base twelve-period horizon (the two
100-unit RETAIN_INCUMBENT orders were the gate's per-service floor), inside tolerance at every endpoint
from 40 to 52 reviews. The brief's instruction for that case is "record limitation and move on", and the
pre-registered condition for a horizon redesign ("B is a valid freeze blocker and the failure is
economically material") no longer holds. The diagnostic sweep (`closure/horizon52_B_h{12,16,20,24,32}.jsonl`,
ZAAD at the sweep horizon, baselines at 12, 52-review evaluation) is recorded as the limitation evidence:
+1.60 / +0.15 / +0.59 / +1.57 / +2.21% (32: one seed, stopped after 2.5 hours for one cell) with first
lots 1,071 / 1,478 / 1,870 / 2,281 / 1,613 against the EOQ 1,854, and per-review solve time p50 .9 / 1.9 /
4.9 / 10.2 / 63.8 s, max 3.5 / 12.8 / 44 / 116 / 298 s. The derived horizon (21) sits in the passing region,
but the first lot changes by a fifth between 20 and 24 (overshoot past the EOQ beyond one cycle) and the
solve budget grows with the square of the horizon: not stable enough around the derived point to adopt in
this continuation. B's remaining property is the benchmark's: an 18.6-week lot cycle is 2.8 cycles in a
year, so the delta magnitude swings by up to 1.6 pp with the ZAAD / EOQ phase while the verdict does not.

### T, dated note (2026-09-09, after the full A-T under rules T-A + T-B): rule T-B REJECTED, rule T-A kept

The full run under both rules (`closure/horizon52_tA_full.jsonl.gz`, `fixtures_product_defaults_tA.jsonl`)
closes T (-0.57%), G (-1.02%), I (+0.24%), C (+0.13%) and moves B to +1.60%, but creates a valid failure:
A intervenes on 12 of 33 legacy reviews (36%) and 46 of 156 declared reviews (29%) against its
pre-registered "mostly abstain" expectation (at most a quarter), through three "capital tie-break"
acceptances and three more "next qualified candidate" acceptances that the incumbent-level floor had
vetoed: leaner plans that serve less than the incumbent (service .986 against .992, unmet 15.6 against
9.2) at a slightly higher cost (+0.80% against the incumbent). Q's legacy service falls from .980 to .965
against a .98 target (declared benchmark unchanged at .991, +0.17%). Per the brief ("if it creates another
valid failure: reject it; do not continue patching") T-B is rejected and the planner's gate basis is
restored to the request's own rule on every review; T-A (ownership) stands. The narrower rule the
evidence points to (target basis on the disruption stress-gate floor only, with the capital tie-break
retired where the terminal valuation already prices closing stock) is recorded as the next candidate
and NOT applied in this continuation.
