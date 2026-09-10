# P2 performance pass: bottleneck diagnosis (written before any modification)

Date 2026-09-10. Branch `claude/zaad-meio-p2`, starting HEAD `6261d12` (clean). Solver stack: scipy
1.17.1 with bundled HiGHS 1.12.0 on the unseeded path (`scipy.optimize.milp`), highspy 1.14.0 on the
seeded / completion path. Machine: 12-core Apple silicon, 24 GB, macOS 26.3.1, Python 3.14.3, nothing
else of ours running (load average 2.3-3.5 is the OS background).

## Original failure (unchanged record)

`ORIGINAL P2 RUNTIME GATE - FAILED`: final set `p2_final` (`P2_RESULTS.md`), 344 ZAAD reviews, p50
9.7 s, p95 86.9 s, **max 314.6 s** against the pre-registered 180 s: M seed 41002 review 7 (257 s,
NETWORK_ALLOCATION, eight worlds) and O seed 41001 review 6 (315 s, CAPITAL_OPTIMIZATION, six worlds).
Every M and O review, whatever its state, sits at 86-91 s (one capped solve); the two failing
reviews are three capped solves. That record is not edited.

## Reproduction

The exact planning snapshots were materialised by replaying each fixture to the review with
`keep_requests` (`scripts/p2_snapshots.py`), then planned through the unchanged
`zaad.full.planner.plan` with in-process instrumentation only (`scripts/p2_profile_review.py`,
wrappers around `Linear.matrix / solve / complete`, `model.solve`, `planner.evaluate`, `settle`,
`draw`; source untouched). `--deep` re-solves every captured model through highspy with a log file to
read HiGHS's own presolve reductions, LP iterations and incumbent timeline (time to first incumbent,
time to the final incumbent, time to proof).

| review | state / owner | worlds | recorded wall | reproduced wall | note |
|---|---|---|---|---|---|
| G 41001 r2 (easy) | NORMAL_REPLENISHMENT / P0 | 3 | 0.9 s | 0.8 s | |
| A 41001 r7 (p50) | NO_ACTION / P1 | 3 | 9.7 s | 7.9 s | |
| H 41001 r4 (p95 class) | PROTECT / P0 | 3 | 93.3 s | 77.5 s | |
| M 41002 r7 (max) | NETWORK_ALLOCATION / P0 | 8 | 256.7 s | **250.4 s** | identical state, three-class review reproduced |
| O 41001 r6 (max) | NO_ACTION / P1 in this replay | 6 | 314.6 s (CAPITAL_OPTIMIZATION) | 88.0 s | this replay's earlier time-limited reviews landed differently (documented run-to-run variability of FEASIBLE_TIME_LIMIT plans, `p2_authoritative_c1` vs `_c2`: 15 / 64 D-M-O-Q reviews differ); the profiled review is the single capped stochastic solve every O review pays, and the recorded CAPITAL_OPTIMIZATION review is three of them |

Raw profiles: `perf/profiles/<fixture>_<seed>_r<k>.json`, HiGHS logs under `perf/profiles/*.highs/`,
console summary `perf/profiles/baseline_profiles.log`.

## Where the time goes (M 41002 r7, 250.4 s)

| phase | seconds | share |
|---|---|---|
| warm-start completion (`Linear.complete`, floor mode, highspy, first-feasible) | **172.4** | 69% |
| MILP solves proper (`Linear.solve`) | 76.9 | 31% |
| model construction (Python build of rows / columns, incl. matrix) | 1.0 | 0.4% |
| candidate evaluation (`evaluate` -> `settle`, 8 worlds x 9 candidates) | 0.1 | 0.05% |
| everything else (forecasts, screen, protection, economics, explain) | 0.0 | - |

Per candidate (eight fitted worlds, H 12, budget 40 x 2.2 x 1.3 = 114 s -> declared 90 s ceiling):

| candidate | vars / rows / nnz (raw) | binaries | completion | main solve | status | nodes |
|---|---|---|---|---|---|---|
| stochastic_network | 13,631 / 13,761 / 89,842 | 3,648 | 30.0 s **rejected (time limit)** | 13.3 s | OPTIMAL | 315 |
| cvar_network | 13,640 / 13,769 / 99,354 | 3,648 | 30.0 s rejected | 22.2 s | OPTIMAL | 556 |
| protected_network | 13,631 / 13,761 / 89,842 | 3,648 | 30.0 s rejected | 13.1 s | OPTIMAL | 315 |
| stress_network (9 worlds) | 15,275 / 15,492 / 101,225 | 4,104 | 30.0 s rejected | 17.6 s | OPTIMAL | 375 |
| joint_recovery (9 worlds) | 15,275 / 15,473 | 4,104 | 23.2 s accepted | 0.4 + 5.1 s | OPTIMAL | 94 |
| joint_fitted | 13,631 / 13,760 | 3,648 | 29.1 s accepted | 0.3 + 4.6 s | OPTIMAL | 63 |
| base_stock, incumbent, deterministic, 2 oracles, alternatives probe | ~2,100 / ~1,800 | 456 | - | < 0.2 s each | OPTIMAL / INFEASIBLE | 1 |

Same shape on O 41001 r6 (88.0 s): completion 30.0 s rejected, then the stochastic solve had only
the remaining 56 s of its 86 s budget and stopped at the time limit with a 1.13% gap
(FEASIBLE_TIME_LIMIT; first incumbent at 27 s, never improved, proof not reached). On H 41001 r4
(77.5 s): completions 39.7 s (all accepted, 2.8-17.1 s each), main solves 37.6 s (4.8-10.0 s each,
all OPTIMAL). On A 41001 r7 (7.9 s): completion 1.8 s, main solve 5.6 s.

Memory is not a factor: peak RSS 511 MB on M (113 MB baseline); the largest model holds ~100 k
nonzeros.

## Mechanism

1. **The warm-start completion is a duplicate of the hardest part of the solve.** The frozen v8
   warm start maps the incumbent's controls onto the candidate's columns and asks HiGHS for one
   feasible completion (`mip_max_improving_sols = 1`, budget `min(30 s, 0.6 x budget)`). The
   "equal" completion (controls pinned) is proved infeasible instantly on every stochastic candidate
   of A, H, M and O - the incumbent never meets the candidate's service floors - and the cascade
   falls to the "floor" completion (purchases as lower bounds), which is a first-feasibility search
   on the full candidate model. On the eight-world models that search does not finish inside 30 s
   (four of six candidates on M, the only candidate on O), the seed is rejected, the 30 s are
   forfeited, and the main solve starts from scratch with the remainder. Where the completion does
   finish (H, joint classes on M) it costs 3-29 s to save a main solve that then needs 5-10 s.
   Net effect on M r7: 172 s of 250 s; on O r6: 30 s taken from an 86 s budget the solve needed.
2. **First feasibility is hard because the relaxation is weak, and it is weak because of the FEFO
   binaries.** 3,456 of the 3,648 binaries of M's stochastic model are `fefo` indicators (one per
   younger cohort x service x period x world) and 192 are `depleted`; both are big-M rows with
   M = location capacity / unit volume = 1e6. HiGHS presolve removes 78% of the model (13,761 x
   13,631 -> 3,139 x 3,054; 3,648 -> 807 binaries), but the surviving 807 binaries with M = 1e6
   leave a relaxation in which every indicator sits at ~1e-6 and the heuristics need 10-31 s and
   ~100-200 k LP iterations to find a first integer point (deep re-solve, HiGHS 1.14: stochastic
   first incumbent 10.3 s, proof 23.4 s, 1,615 nodes, 192 k iterations; cvar 30.8 s / 45.9 s /
   369 k iterations). Every cohort in these snapshots expires 45-64 periods out against a 12-period
   horizon and a 1-4 period lane, so the consumption order between cohorts changes no cost and no
   constraint inside the plan: the FEFO binaries encode a pure symmetry.
3. **Scenario multiplicity multiplies 1 and 2.** Binaries, inventory and allocation columns are per
   world: 8 worlds -> 13.6 k columns, against 4.0 k at 3 worlds (H, A). Time to first incumbent
   grows from ~0 s (3 worlds) to 10-31 s (8 worlds); the completion cap (30 s) is exactly the
   region where that search fails.
4. **The review then multiplies by the requested classes.** NETWORK_ALLOCATION / CAPITAL_OPTIMIZATION
   request three to six full stochastic solves (plus joint recovery and joint fitted on M), each
   paying 1 + 2 sequentially.

What is NOT the bottleneck: model construction (1 s), settlement / evaluation (0.1 s), forecasting
and screening (< 0.1 s), memory, the deterministic and oracle solves (< 0.2 s), the alternatives
probe (instant INFEASIBLE), solver proof after the first incumbent (13-23 s of proof against 10-31 s
to first incumbent - the proof is not the long pole once an incumbent exists).

Time to decision against time to proof (M, deep re-solve): the final incumbent is found at the
moment of proof on every candidate (final_inc == proof) - there is no "good plan early, proof
later" region to exploit by a gap policy, which is consistent with the frozen `solve_budget`
finding and rules out gap loosening as a lever.

## Consequences for the plan (exact levers, in order)

1. Remove the FEFO symmetry where it is provably immaterial (older cohort outlives the horizon plus
   the longest lane lead plus receiving slack): objective and the set of reachable executable
   decisions are unchanged; only cohort labels within an interchangeable group can differ.
2. Re-measure the completion; if it still forfeits its budget on eight-world models, bound the
   completion by what it can pay back (record time to first incumbent seeded vs unseeded on the
   captured models; the warm start "changes the search only, never the problem", so any policy here
   is exact).
3. Bound tightening: the location-capacity M cannot be tightened from the request data on these
   fixtures (supplier and lane capacities are also 1e6); evaluated, not applied unless a valid
   tighter bound exists.
4. HiGHS parameter portfolio and parallel candidate execution only if 1-2 leave M / O above the gate.
