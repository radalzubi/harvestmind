# P2 performance pass: authoritative re-run results

Run `p2_authoritative_perf` (`docs/zaad_full/evidence/p2/p2_authoritative_perf.jsonl`, summary
`p2_final_perf.summary.json`, tables `p2_final_perf.tables.md`; console `perf/gates/
p2_authoritative_perf_run.log`), executed exactly as pre-registered in `P2_PERF_CORRECTIVE_PLAN.md`
at code SHA `cab3849` (evidence tree `a0b1573`): the unchanged fixture matrix A-T, seeds 41001 /
41002, five policies, eight rolling reviews (R twenty), the pre-registered world rule and budgets,
four workers. The pre-performance record it is compared with is `p2_final` (`P2_RESULTS.md`).

## Runtime gate (pre-registered p50 <= 60 s, p95 <= 120 s, max <= 180 s, no required-candidate starvation)

| set | ZAAD reviews | p50 s | p95 s | max s | starvation | solve statuses | verdict |
|---|---|---|---|---|---|---|---|
| pre-performance final record (`p2_final`) | 344 | 9.7 | 86.9 | 314.6 | 0 | 1,476 OPTIMAL, 143 INFEASIBLE, 19 FEASIBLE_TIME_LIMIT | FAIL (max) |
| performance re-run (`p2_authoritative_perf`) | 344 | **0.5** | **6.6** | **14.6** | 0 | **1,515 OPTIMAL, 143 INFEASIBLE, 0 FEASIBLE_TIME_LIMIT** | **PASS** |

Performance target (max < 180 s, p50 < 9.7 s, p95 < 86.9 s): met by 12x, 20x and 13x. The slowest
review of the whole set is Q 41002 (packs and dispatch fee, NETWORK_ALLOCATION) at 14.6 s; the
slowest fixtures by p95 are Q (14 s) and R (10 s). Every M and O review, 86-315 s before, is now
under 1.5 s. No candidate solve of any review ended at its time limit: every plan ZAAD chose was a
proven optimum of its candidate class at the requested 1e-6 gap (Q: its declared 1e-4).

## Economic and service gates (unchanged rules)

**20 / 20 valid fixtures PASS; 18 / 18 network principles PASS.** ZAAD gap against the best baseline
(P2 continuation basis; tolerance in brackets): A +0.98% (2), B +0.07%, C +0.98%, D +0.05%, E
+0.66%, F +0.53%, G +0.00% (3), H +1.05% (3), I +0.40% (5), J +1.22%, K +0.73%, L +0.46%, M -0.01%,
N +0.77%, O -1.38%, P +0.00% (3), Q -0.12%, R -3.02%, S +0.77% (3), T +0.86%. Minimum branch
service is never below the incumbent's where the incumbent meets target (H .970 against the
incumbent's .770, O .996, Q 1.000). Abstention, reverse-movement, conservation and starvation
gates pass on every cell as before.

The gaps moved within their tolerances relative to `p2_final` (A / C +0.12% -> +0.98%, H +2.06% ->
+1.05%, O -0.69% -> -1.38%, R -2.19% -> -3.02%, D -0.07% -> +0.05%). The two directions have one
cause, explained below: the executed transfer quantities on these fixtures are not unique at the
optimum, and a different but equally optimal choice settles differently on the truth.

## Decision comparison with the pre-performance record (`scripts/p2_decision_compare.py`, `p2_perf_decision_compare.json`)

1,720 reviews compared over five policies (state, owner, status, abstention, executed purchases
and transfers, settled cost, served units, candidate statuses); 1,283 identical.

| policy | cells | cells with a difference | identical reviews | first differing reviews |
|---|---|---|---|---|
| network_rop | 40 | 0 | 344 / 344 | - (rule projection) |
| central_pool | 40 | 0 | 344 / 344 | - (rule projection) |
| gated (ZAAD) | 40 | 27 | 196 / 344 | listed in `p2_perf_tie_check_gated.json` |
| independent (ZAAD on isolated chains) | 40 | 34 | 86 / 344 | `p2_perf_tie_check_independent.json` |
| echelon_base_stock | 40 | 18 | 313 / 344 | reviews 6-7 only, `p2_perf_tie_check_echelon.json` |

Once a review differs, every later review of the cell inherits a different state, so the count of
differing reviews overstates the number of distinct decisions: what has to be explained is the
FIRST differing review of each cell (its predecessors are identical, hence its snapshot is the
snapshot both runs planned on, up to the labels of interchangeable cohorts).

**Protocol** (`scripts/p2_perf_tie_check.py`): for each cell's first differing review, (i) confirm the
previous review's end stock per location is identical between the two records, (ii) materialise the
snapshot, (iii) plan it under the frozen formulation and under the new one through the same
instrumentation as the profiles, (iv) compare every candidate's status and objective (relative
1e-6) and the executed decision on that snapshot.

**Result** (`p2_perf_tie_check_gated.json`, `_gated_Q.json`, `_echelon.json`, `_independent.json`,
`_independent_Q.json`; logs under `perf/gates/tie_check_*.log`):

| policy | first differing reviews checked | predecessor end stock identical | every candidate objective identical (1e-6, or the request's declared gap) | of which: frozen candidate time-limited | unexplained |
|---|---|---|---|---|---|
| gated (ZAAD) | 27 | 27 / 27 | 26 / 27 (24 at 1e-6; the two Q cells at Q's declared 1e-4 gap: stochastic 12,623.124 -> 12,622.800 = 2.6e-5, 12,674.462 -> 12,673.625 = 6.6e-5, base stock +1.1e-5, deterministic 8.8e-6; both formulations are "optimal" at that gap) | 1 (M 41002 r4: the frozen stochastic plan was a FEASIBLE_TIME_LIMIT point at 12,482.81; the new solve proves 12,475.97, 0.05% better) | **0** |
| echelon_base_stock | 18 | 18 / 18 | 18 / 18 | 0 | **0** |
| independent (both isolated chains) | 34 | 34 / 34 | 34 / 34 (33 at 1e-6; Q 41002 r0 north chain 6,260.578 -> 6,260.448 = 2.1e-5 at Q's 1e-4 gap) | 0 | **0** |

On every checked snapshot the executed decision differs between the two formulations while every
candidate's objective is the same: the differences are ties (alternative optima) broken differently,
plus the one review where the frozen record held a time-limited plan. No difference is a change of
the decision problem.

**Why the executed transfer is a tie on these fixtures.** Central and branches carry the same holding
rate, the cost of capital is zero, a lane's cost is per unit moved whenever it moves, and every
cohort outlives the horizon; moving a unit the branch will need at period t now or one period
later therefore costs exactly the same, and the model's optimum is a face, not a vertex. The frozen
formulation and the new one land on different points of that face (they are different models
with different presolve paths), the settlement then realises them on the truth, and the settled
cost differs by the timing of the same moves. The frozen formulation itself already varied the
executed decisions of D, M, O and Q between `p2_authoritative_c1` and `_c2` on 15 of 64 reviews with
no code change (time-limited solves landing on different points).

## What the re-run establishes

* The runtime blocker is removed on the unchanged authoritative set by an exact model change: the
  same decision problem (same worlds, horizons, candidate classes, floors, gaps, economics), less
  computation.
* No candidate is time-limited anywhere on the set; the "usable plan without a proof" path of the
  frozen solve-quality gate is no longer exercised on it.
* Every difference from the pre-performance record is on a review whose snapshot the two
  formulations solve to the same candidate objectives; the differences are alternative optima
  realised differently by the settlement, in both directions, inside every tolerance.
