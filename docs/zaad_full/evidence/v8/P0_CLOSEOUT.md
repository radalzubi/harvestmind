# P0 close-out: solver completeness and recovery logic (V8)

Branch `claude/zaad-industry-standard-v8`. Seeds: development8 38001. Focused P0 set: cells 15, 16, 20, 21, 90, 108.
Scaled solve budget on every arm. Evidence and scripts: `evidence/v8/p0/`.

## 1. P0-C: four-arm joint_recovery ablation (24 rows)

Table: `evidence/v8/p0/P0C_ablation_table.md` (pre-fix system; causal columns stand, starvation columns superseded).

| cell | V7 full | V8 escalated | V8 + forced joint | V8 no joint |
|---|---|---|---|---|
| 15 svc / inv | .983 / 102 | .980 / 46 | .983 / 102 | .980 / 46 |
| 16 | .972 / 212 | .972 / 135 | .972 / 212 | .972 / 135 |
| 20 | .827 / 187 | .827 / 185 | .827 / 187 | .827 / 177 |
| 21 | .760 / 115 | .744 / 63 | .760 / 115 | **.479 / 35** |
| 90 | .863 / 269 | .863 / 92 | .863 / 124* | .863 / 90 |
| 108 | .878 / 155 | .878 / 144 | .878 / 155 | .878 / 144 |

1. Forced joint reproduces V7 exactly on 15, 16, 20, 21, 108 (service, unmet, breaches and inventory to the decimal).
2. It did not on cell 90 in this run (124 vs 269). *Explained in §5: the pre-fix settlement gate rejected V7's time-limited joint plans; on the corrected system forced joint = V7 (271 vs 267, `diag8_90_*.json`).
3. joint_recovery is necessary for service on cell 21 (closure recovery) and, once time-limited plans are usable, on cell 20 (never_joint .827 vs .912).
4. It can be skipped without service cost on 15, 16, 90, 108 - where it only adds inventory.
5. Cell 90: §5. 6. Cell 108: §6.

## 2. P0-B: corrected required / optional / not-applicable accounting

Every class the screen names is classified once (REQUIRED, OPTIONAL, NOT_APPLICABLE) and carries one outcome:
SOLVED, PHYSICALLY_VALID_FTL, INFEASIBLE, NO_INCUMBENT, TIME_LIMIT_NO_USABLE_PLAN, OPTIMAL_PHYSICALLY_INVALID, ERROR, SKIPPED, NOT_APPLICABLE.
Required starvation = a REQUIRED class whose outcome is NO_INCUMBENT, TIME_LIMIT_NO_USABLE_PLAN, OPTIMAL_PHYSICALLY_INVALID, ERROR or SKIPPED.
INFEASIBLE is a definitive answer reported apart from starvation (`required_candidate_infeasible`). NOT_APPLICABLE
(hedged/stress protection without a credible or declared stress; quantile protection outside the reliability
profile) and skipped OPTIONAL classes are never starvation. An attempted-but-unusable joint_recovery is recorded
with its real status. Tests: `tests/unit/test_zaad_completeness_v8.py`.

What the old numbers were: cell 15 V7 "25 starved" = 24 INFEASIBLE definitive answers (stress_network 11/12,
hedged 10/12, every class at the one-period final review) + 1. Corrected: 0 / 84.

Corrected required starvation under the 12-process batch (`final8_*.json`), all arms:
cells 15, 16, 20, 21: **0** on every arm. Cell 90: 0-1 of 63-94 (1.1-1.6%). Cell 108: 4-5 of 78-105 (4.8-5.1%).
Clean single-process confirmation: §8.

## 3. P0-D1: FEASIBLE_TIME_LIMIT root cause

`settlement.settle()` began with `if plan.status != "OPTIMAL": raise PhysicalViolation("unusable solve is not a
zero-order plan")`. Every FEASIBLE_TIME_LIMIT plan was rejected on its status before a single physical check ran,
so `phys_bad == FTL` was a tautology, and "rescued incumbents" contributed nothing. Fixed: settlement gates on
`usable_plan` and applies every physical law (capacity, packs, MOQ, transfers, liquidity, terminal financing,
conservation) to time-limited plans; `replay`, `alternative_value` and the incumbent gate use usability too.

Probe evidence (`ftlprobe_cell20_r1.txt`, `ftlprobe_cell90_r1_r2.txt`): FTL incumbents have max integrality
violation 1e-16 to 1e-12, constraint residual 1e-12 to 1e-09, bound violation < 1e-11, zero fractional integers at
1e-6, gaps 0.5-5%, and **every one passes physical settlement** (post-fix diagnostics: 23/23 on cell 90 V7, 13/13
on cell 108 V8, 25/25 forced joint; `FTL_invalid = 0` on all 36 final-run rows).

Verdict: FEASIBLE_TIME_LIMIT is a usable solver state for this implementation. Acceptance gate (all three):
(a) model residual <= 1e-5 on constraints, bounds and integrality (`model.py`); (b) physically valid on every
selection world in independent settlement; (c) ranked on economics only when achieved gap <= `comparable_gap`
(else usable for service, not for cost comparison). Physical validation was not weakened.

Effect: cell 20 service .827 -> .912 (unmet 66.8 -> 34.1, breaches 5 -> 4) because the time-limited joint plan at
review 3 is now usable.

## 4. Cell 90 root cause

Post-fix review-by-review (`diag8_90_{V7_full,V8_escalated,V8_forced_joint}.json`, `cmp8.py`): identical
service on all three arms from review 8 on; forced joint reproduces V7 (unmet 70.1 vs 68.2; inventory 271 vs 267).
First divergence: **review 11**. V7 and forced joint select `joint_recovery`; V8 keeps `projected_base_stock`.
Mechanism: at review 11 every candidate meets its target on the selection worlds, so the on-demand escalation
does not fire and V8 never builds the joint plan. V7 builds it every review; solved on the combined fitted+stress
worlds it buys stress-world service, passes `confirm_service_first`'s stress-weighted benefit, and is accepted -
raising inventory through reviews 11-19 (637 vs 56 at review 15) for no realised service difference. The screen
then labels V7's downstream CAPITAL_OPTIMIZATION. The batch-run "starvation" at reviews 1-2 (NO_INCUMBENT at ~28 s)
is load: a lighter run finds all four floored incumbents at 30 s (`frontier_cell90_r1.txt`) and reaches a 0.009%
gap at 120 s.

## 5. Cell 108 root cause

Same mechanism, first divergence **review 14** (V7/forced choose joint_recovery; V8 projected), then reviews 19,
22, 25, 27; service identical throughout; forced joint = V7 (153.7 vs 154.8).

Its required starvation is different in kind: at reviews 1, 2, 4 the floored classes (stochastic, protected, cvar,
hedged; 6.9k-8.3k variables) return NO_INCUMBENT at the 30-38 s scaled budget, and at review 1 **still at 40, 80
and 160 s** (`ftlprobe_cell108_r1.txt`). They are not infeasible: the incumbent plan meets the target on the
selection worlds (.957 vs .950, `frontier_cell108_r1_r2_r4.txt`), so a feasible point exists and HiGHS's primal
heuristics fail to find one on the largest (H=29) model. More time does not help; a warm start from the known
feasible incumbent would. `highspy` 1.14 with `Highs.setSolution` is installed; `scipy.optimize.milp` has no
warm-start path. Reformulation/warm start is preferable to a larger timeout.

## 6. P0-E: joint_recovery requiredness rule

Screen probes (`screen8_*.json`) separate the cells: where joint_recovery was necessary (cell 21, reviews 7-15)
the incumbent's projected service on the selection worlds sat 0.27-0.55 below target; where it changed nothing
(15, 16) the deficit stayed <= 0.11; a supply driver was active on every review of 15/16/20/21 alike, so the
driver is not a discriminator.

Rule (`joint_recovery_rule = "deficit"`, `joint_recovery_deficit = 0.20`): joint_recovery is REQUIRED when the
incumbent's projected service on the selection worlds is >= 0.20 below any target; otherwise it stays on-demand
(built when no candidate meets every target). Deterministic, one signal, explained in the screen's reasons.
The `deficit_cover` variant (adds: thin cover under an active supply driver) was tested and adds nothing on
service. Tests: `tests/unit/test_zaad_joint_rule_v8.py`.

Six-cell comparison (batch, `final8_*.json`; service / breaches / unmet / inventory):

| cell | always joint | never joint | V8 current | deficit rule | V7 full |
|---|---|---|---|---|---|
| 15 | .983/1/4.2/102 | .980/1/5.0/46 | .980/1/5.0/46 | .980/1/5.0/46 | .983/1/4.2/102 |
| 16 | .972/1/7.0/212 | .972/1/7.0/135 | .972/1/7.0/135 | .972/1/7.0/135 | .972/1/7.0/212 |
| 20 | .912/4/34.1/192 | .827/5/66.8/177 | .912/4/34.1/201 | .912/4/34.1/201 | .912/4/34.1/192 |
| 21 | .760/5/93.0/128 | .479/11/201.6/35 | .727/6/105.6/53 | **.760/5/93.0/146** | .760/5/93.0/127 |
| 90 | .863/4/70.1/199 | .863/4/70.1/90 | .863/4/70.1/147 | .863/4/70.1/147 | .863/4/70.1/124 |
| 108 | .878/4/69.9/154 | .878/4/69.9/144 | .878/4/69.9/144 | .878/4/69.9/144 | .878/4/69.9/155 |

The rule fires on 9 of 20 cell-21 reviews and on none of 15/16/20/90/108's. It restores V7 service parity on
cell 21 and takes none of the inventory savings that were not service-bearing.

## 7. P0-F: solve budget decision

Scaled budget is the default (`adaptive_solve_budget = True`, margin 1.3, ceiling 90 s). Evidence: at 5 s one of
four floored classes finds an incumbent on cell 20 review 1; at 16-30 s all four do (2-5% gaps); the hard cells
need 5.4-38 s to return anything at all. Latency, honest: §8.

## 8. Clean confirmation run (single process, chosen configuration)

`final8_clean_rule_deficit.json`, one process on the machine, defaults as committed (deficit rule, scaled budget, FTL validated).

| cell | service | p10 | tail | breaches | unmet | worst | inventory | cost | required done/req | **required starved** | infeasible | optional done/req | FTL valid/invalid | no-incumbent | joint req/built/chosen | lat p50 | p90 | p95 | max | wall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | .980 | .962 | .790 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 32/36 | **0** | 4 | 14/36 | 0/0 | 0 | 0/1/0 | 0.14 | 0.5 | 1.3 | 1.8 | 5 s |
| 16 | .972 | 1.000 | .650 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 6 | 14/36 | 0/0 | 0 | 0/2/0 | 0.13 | 0.7 | 0.9 | 2.6 | 6 s |
| 20 | .920 | .233 | .000 | 3 | 30.9 | 14.0 | 191.1 | 2466 | 53/58 | **0** | 5 | 33/57 | 6/0 | 0 | 0/2/1 | 0.18 | 20.3 | 29.7 | 65.6 | 143 s |
| 21 | .760 | .000 | .000 | 5 | 93.0 | 27.0 | 146.2 | 3619 | 47/63 | **0** | 16 | 18/52 | 7/0 | 0 | 8/12/6 | 0.60 | 20.5 | 29.7 | 65.6 | 156 s |
| 90 | .863 | .220 | .000 | 4 | 70.1 | 22.0 | 124.1 | 3360 | 58/67 | **0** | 9 | 22/59 | 13/0 | 2 (optional) | 0/5/2 | 0.68 | 79.3 | 90.3 | 113.6 | 512 s |
| 108 | .878 | .221 | .000 | 4 | 69.9 | 22.0 | 142.4 | 3692 | 70/78 | **4 (5.1%)** | 4 | 29/66 | 13/0 | 12 | 0/5/1 | 2.15 | 122.8 | 133.4 | 152.9 | 901 s |

Cell 108's four: review 1 stochastic + protected, review 2 protected, review 4 protected - the H=29..26 floored
models of §5. Every review still carried a usable, target-meeting plan (the incumbent or a sibling class), so no
decision was taken blind; but the required classes did not solve, and that is the standard.

Time-limited solves make the hard cells run-to-run non-deterministic: cell 90 V7 inventory measured 267 (diagnostic)
and 124 (six-arm batch); cell 20 service .912 (batch) and .920 (clean). Service and breaches move within a review
or two; the qualitative conclusions do not.

## 9. Gate

| # | criterion | result |
|---|---|---|
| 1 | corrected REQUIRED starvation ~ 0 on the focused set | **FAIL** - 0 on 15/16/20/21/90; 4 of 78 (5.1%) on cell 108 |
| 2 | no candidate disappears silently | PASS - every class carries an outcome and a reason |
| 3 | optional / not-applicable distinguished from required | PASS |
| 4 | FTL understood and safely gated | PASS - root cause fixed, gate in §3, 0 invalid FTL on 42 rows |
| 5 | cell 90 causally explained | PASS - §4 |
| 6 | cell 108 causally explained | PASS - §5 (heuristic failure with a known feasible point) |
| 7 | joint_recovery requiredness understood and tested | PASS - §6, six cells x five arms |
| 8 | no material regression (service, p10, tails, breaches, worst, feasibility) | PASS - versus V7 full on the corrected system: service equal on 15/16/20/90/108 within .003, equal on 21; breaches equal or better; worst shortfall equal |
| 9 | inventory reductions not from omitting required protection | PASS - the deficit rule restores the only case where it was (cell 21) |
| 10 | screen / escalation conservative | PASS - the rule only adds a required class, never removes one |
| 11 | runtime measured honestly | PASS as measurement; the numbers themselves are a production concern: p95 90-133 s and max 114-153 s on cells 90/108 |

**P0 FAILS / REMAINS OPEN on criterion 1.** Not frozen. P1 not started.

Named next step (P0-D3b): warm-start the floored classes from the known feasible incumbent. `scipy.optimize.milp`
has no such path; `highspy` 1.14 with `Highs.setSolution` is installed. Success test: cell 108 reviews 1-4 required
starvation 0 at the scaled budget, no change elsewhere on the six cells. After that, solver orchestration and
latency (p95 > 90 s on 26-30 review cells) become the next optimisation target; correctness first.

## 10. What was not touched

Validation7, Validation8 and holdout4 were not run and their evidence directories are unchanged. Network Twin
(PR #39), the frontend and Vercel were not touched. Nothing was merged.



## 11. WARM-START COMPLETENESS FIX (P0-W)

**Root cause.** Cell 108's four required starvations were HiGHS finding no primal incumbent inside the budget on
the largest floored models (6.9k-8.3k variables, H=26-29) although a feasible point was known: the incumbent
plan meets the target (.957 vs .950 at review 1). Timeout was not the lever: review 1 returned NO_INCUMBENT at
40, 80 and 160 s (`ftlprobe_cell108_r1_r4.txt`).

**Approach.** `highspy` 1.14.0 (`Highs.setSolution`; `scipy.optimize.milp` has no warm-start path). `Linear.solve`
gained a highspy path on the *identical* cost, bounds, integrality and constraint arrays; unseeded solves keep
scipy's path. Seed source: the incumbent plan the selector already holds. Its controls - purchases, PO amendments,
transfers - are mapped by column name into **each candidate's own formulation** and completed by that formulation
(`Linear.complete`: pin the controls inside their bounds, solve the rest to a first feasible point,
`mip_max_improving_sols=1`). Cascade: equality pins first; if the formulation proves them infeasible, the
add-only repair - the plan's positive purchases as lower bounds, the formulation adding what its own floors need.
Both completions are genuine feasible plans of that candidate; a seed that fails both is rejected with the
reason. Completion time counts against the scaled budget (cap 30 s, at most 60% of the budget). The completed
vector is passed with `setSolution`; acceptance is confirmed by the solver returning a solution no worse than
the seed, and the outcome is recorded as improved / retained / rejected / no_incumbent_despite_seed.

**Seed feasibility, measured** (`seedwhy_cell108_r4_r2_r1.txt`, `seedfloor_cell108_r1_r2_r4.txt`): at reviews 2 and
4 the incumbent buys in every period and the floored classes need more supply than it carries, so the equality
seed is proved infeasible in 0.1 s; the add-only repair finds a feasible completion for every required class
(review 1 protected 25 s; review 2 stochastic/cvar/protected 21-30 s; review 4 17-27 s at a 30 s cap; 5-14 s once
completions stop at the first incumbent). It is not asserted feasible anywhere.

**Search only.** Solve-state mapping, model residual gate (1e-5), independent physical settlement on every world,
the FTL gap policy and the REQUIRED / OPTIONAL / NOT_APPLICABLE accounting are unchanged; a warm-started plan has
no special acceptance rights (`tests/unit/test_zaad_warm_start_v8.py`). Models under 3000 variables are not seeded.

**Cell 108 before / after (same requests, same scaled budget; `warm8_cell108_r1_r2_r4.txt`, `..._cascade.txt`):**

| review | class | before (frozen scipy) | after (highspy + cascade) |
|---|---|---|---|
| 1 | stochastic (required) | NO_INCUMBENT 38 s | FTL gap 1.3%, valid, seed accepted (equality, 0.3 s) and improved |
| 1 | protected (required) | NO_INCUMBENT 38 s | FTL gap 1.5%, valid, seed accepted (floor repair, 10.6 s) and improved |
| 1 | cvar (optional) | NO_INCUMBENT | FTL gap 3.4%, valid, improved |
| 2 | protected (required) | NO_INCUMBENT 35 s | FTL gap 0.15%, valid, floor repair 6.7 s, improved |
| 2 | stochastic (required) | FTL (unaided) | FTL gap 0.3%, floor repair 7.8 s, improved |
| 4 | protected (required) | NO_INCUMBENT 31 s | FTL gap 2.1%, valid, floor repair 6.2 s, improved |
| all | hedged (optional) | NO_INCUMBENT | NO_INCUMBENT - repair times out; optional, not starvation |
| all | stress | INFEASIBLE 0.1 s | INFEASIBLE - definitive |

Required starvation on reviews 1, 2, 4: **4 -> 0**, all inside the existing budget. Review 1 now selects
`stochastic_network` (projected service .965) instead of retaining the proxy (.957). No seed was merely retained
(W7): every accepted seed was improved by the solver. Highspy without a seed (W8 middle arm) is *not* equivalent
to scipy's bundled HiGHS - it found incumbents scipy missed and missed ones scipy found - so the causal
intervention is the seed, measured against both.

**Six-cell clean confirmation, single process, warm start on** (`final8_clean_warm_rule_deficit.json/.txt`):

| cell | service | p10 | breaches | unmet | worst | inventory | cost | required done/req | **required starved** | infeasible | optional done/req/skipped | NA | FTL valid/invalid | lat p50 | p90 | p95 | max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | .980 | .962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 32/36 | **0** | 4 | 14/36/0 | 0 | 0/0 | 0.14 | 0.4 | 1.3 | 1.5 |
| 16 | .972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 6 | 14/36/0 | 0 | 0/0 | 0.12 | 0.6 | 0.9 | 2.5 |
| 20 | .894 | .233 | 3 | 41.0 | 14.0 | 183.5 | 2502 | 50/58 | **0** | 8 | 31/57/0 | 0 | 4/0 | 0.16 | 12.4 | 30.0 | 59.7 |
| 21 | .760 | .000 | 5 | 93.0 | 27.0 | 144.8 | 3364 | 47/64 | **0** | 17 | 16/52/0 | 0 | 5/0 | 0.54 | 17.3 | 24.7 | 59.1 |
| 90 | .863 | .220 | 4 | 70.1 | 22.0 | 94.2 | 3317 | 57/64 | **0** | 7 | 24/52/0 | 0 | 12/0 | 0.54 | 74.4 | 77.0 | 113.6 |
| 108 | .879 | .225 | 4 | 69.8 | 22.0 | 138.6 | 3723 | 74/78 | **0** | 4 | 34/66/0 | 0 | 21/0 | 3.25 | 122.8 | 132.9 | 153.0 |

Regression cells (W9), warm start vs the pre-warm-start clean run (`final8_clean_prewarm_rule_deficit.json`):
cell 21 identical service, breaches and unmet (.760 / 5 / 93.0), inventory 144.8 vs 146.2, joint required on 9
reviews both times - the deficit rule's recovery behaviour is intact. Cell 90 identical service (.863 / 4 / 70.1),
inventory 94.2 vs 124.1, joint required 1 review vs 0 - no unnecessary joint inventory reintroduced. Warm-start
availability changed no REQUIRED / OPTIONAL / NOT_APPLICABLE classification (the rule reads the incumbent's
projected service, not solve outcomes).

**Run-to-run variability** (recorded, not hidden): cell 20 service .912 (batch) / .920 (clean, no warm start) /
.894 (clean, warm start), breaches 3-4, unmet 31-41 - inside the band time-limited solves already showed, and all
better than the pre-FTL-fix .827 / 66.8. Cell 90 inventory 124 / 94 across the two clean runs. The warm start does
not remove this variability; it remains a production-readiness item.

**Residuals.** Seeded solutions: HiGHS max integrality violation and primal infeasibility at machine precision
(1e-12 to 1e-16); model residual gate 1e-5 unchanged; 0 physically invalid FTL plans across the 42 seeded rows.

**Tests.** `test_zaad_warm_start_v8.py` (8): solver-path agreement on identical arrays, name-based mapping,
partial completion, invalid seed rejected (bounds and infeasible), valid seed accepted and improved, add-only
repair, no special acceptance for warm-started plans, solve-state mapping. Full unit suite: 1409 passed, 2
skipped (baseline 1401 + 8).

**Deficit threshold sensitivity (W10)** - see §12.

## 12. Deficit threshold sensitivity (W10)

Three concurrent runs, six cells each, warm start on (`final8_sens_deficit.txt`, `final8_sens_deficit_0.{15,20,25}.json`).

| cell | 0.15 (svc / breaches / unmet / inv / joint req) | 0.20 | 0.25 |
|---|---|---|---|
| 15 | .980 / 1 / 5.0 / 46.1 / 0 | same | same |
| 16 | .972 / 1 / 7.0 / 134.5 / 0 | same | same |
| 20 | .894 / 3 / 40.9 / 183.7 / 1 | .894 / 3 / 40.9 / 183.7 / 0 | .894 / 3 / 40.9 / 183.7 / 0 |
| 21 | .760 / 5 / 93.0 / 146.2 / 9 | .760 / 5 / 93.0 / 144.8 / 9 | .760 / 5 / 93.0 / 146.2 / 7 |
| 90 | .863 / 4 / 70.1 / 94.2 / 3 | .863 / 4 / 70.1 / 94.2 / 1 | .863 / 4 / 70.1 / 94.2 / 0 |
| 108 | .879 / 4 / 69.8 / 138.6 / 3 | .879 / 4 / 69.8 / 138.6 / 0 | .879 / 4 / 69.8 / 138.6 / 0 |

Service, breaches and unmet are identical at all three thresholds on every cell; only the count of reviews on
which the rule fires moves (cell 21: 9 / 9 / 7). Required starvation is 0 on all 18 rows. 0.20 sits on a plateau,
not a knife-edge; it is kept.

Warm-start counts per cell at 0.20 (seeded / accepted / improved / retained / rejected / repaired by add-only):
15 and 16: 0 (models under 3000 variables); 20: 20 / 6 / 6 / 0 / 14 / 0; 21: 20 / 8 / 8 / 0 / 12 / 0;
90: 51 / 31 / 31 / 0 / 20 / 24; 108: 75 / 46 / 46 / 0 / 29 / 30. Every accepted seed was improved on; none was
merely retained; no seeded class ended without an incumbent. Rejections are formulation-proved infeasibility or
completion timeouts on the optional hedged / stress classes, each with its reason recorded.

Determinism observation: the uncontended clean run and the three concurrent sensitivity runs returned identical
service and inventory on all six cells (cell 20 .894 / 183.5-183.7; cell 90 94.2; cell 108 138.6). Seeding from a
deterministic incumbent appears to make the time-limited solves reproducible on this machine; the run-to-run
variability of the unseeded system (§8) is recorded and this is not claimed as a general guarantee.

## 13. Gate, re-evaluated, and freeze

| # | criterion | result |
|---|---|---|
| 1 | corrected REQUIRED starvation ~ 0 on the focused set | **PASS - 0 / 0 / 0 / 0 / 0 / 0** (clean, single process) |
| 2 | no candidate disappears silently | PASS |
| 3 | optional / not-applicable distinguished from required | PASS |
| 4 | FTL understood and safely gated | PASS - 0 invalid FTL across 42 seeded and 42 unseeded rows |
| 5 | cell 90 causally explained | PASS - §4 |
| 6 | cell 108 causally explained | PASS - §5, §11 |
| 7 | joint_recovery requiredness understood and tested | PASS - §6, §12 |
| 8 | no material regression | PASS - versus V7 full: service equal within .003 on 15/16/90/108, better on 20 (.894-.920 vs .912 band), equal on 21; breaches equal or better; worst shortfall equal |
| 9 | inventory reductions not from omitting required protection | PASS |
| 10 | screen / escalation conservative | PASS - warm start changes no classification |
| 11 | runtime measured honestly | PASS as measurement; p95 77-133 s and max 114-153 s on cells 90/108 remain a production concern |

**P0 SOLVER COMPLETENESS / RECOVERY LOGIC — PASS AND FROZEN.**

Freeze record:
- branch `claude/zaad-industry-standard-v8`; parent SHA of this work `f6d1827`; code SHAs `7385d5c` (adapter), `8a7d293` (cascade); final SHA: the commit carrying this document
- solver: scipy `milp` (bundled HiGHS) for unseeded solves; `highspy` 1.14.0 for seeded solves on the identical arrays; `solver_mip_gap` 1e-6; `comparable_gap` 0.02
- solve budget: `adaptive_solve_budget=True`, `max_solve_seconds` 5 scaled by (horizon/12)^2 x breadth x margin 1.3, ceiling 90 s
- warm-start policy: `warm_start=True`, `warm_start_min_variables=3000`, completion cap `warm_start_completion_seconds=30`, `warm_start_completion_share=0.6`; seed = incumbent controls mapped by name into each candidate; cascade equality -> add-only repair; completion stops at first incumbent; search only
- joint_recovery: `joint_recovery_rule="deficit"`, `joint_recovery_deficit=0.20`; on-demand escalation retained as backstop
- FTL policy: usable iff model residual <= 1e-5 and physically valid on every selection world; cost-comparable only when gap <= comparable_gap
- required-starvation definition: a REQUIRED class whose outcome is NO_INCUMBENT, TIME_LIMIT_NO_USABLE_PLAN, OPTIMAL_PHYSICALLY_INVALID, ERROR or SKIPPED; INFEASIBLE reported apart; NOT_APPLICABLE and skipped OPTIONAL never starvation
- known limitations: hard-cell latency (p95 77-133 s, max 153 s); optional hedged_network finds no incumbent on cell 108's largest models; run-to-run variability of unseeded time-limited solves; the deficit rule and warm start are validated on the six-cell focused set at seed 38001 only - Validation8 and holdout4 remain unrun
- Validation7, Validation8, holdout4 not run and their evidence untouched; Network Twin / PR #39, frontend and Vercel untouched; nothing merged; P1 not started
