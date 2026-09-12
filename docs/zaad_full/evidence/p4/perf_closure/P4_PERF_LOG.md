# P4 performance closure — run log (TRACK A)

Every run in order; nothing tuned to a target. Machine: local Apple laptop, quiet (TRACK B work
on the same machine was limited to editing while these ran). Semantics frozen: P4 release
runtime `8c813ac`.

## Run 1 — baseline diagnosis matrix (`scripts/p4_perf_profile.py`, tag `P4_PERF_PROFILE`)

35 cells (5 classes x 7 grid points, 3-16 worlds, 1-2 epochs), 105 instrumented tree solves with
HiGHS logs + 35 planner runs. Summary in `P4_PERF_DIAGNOSIS.md` sections 2-4. Headline: the
heavy cost sits in three tree solves of the planner path - on the shared-order class the
UNSEEDED adaptive and perfect-information solves time-limit at the 78 s budget each (177 / 193 s
planner wall at 12 / 16 worlds); on the produce class the static comparator's warm-start
completion costs 19-26 s and the static / adaptive solves time-limit at 43 s (FEFO indicators).

## Run 2 — planner-path replay, shared-order class, 12 worlds (3 histories, epochs [3, 6], 2 continuations)

`tree_solves.py`: the planner's own three tree solves captured with their exact kwargs and
budget (78 s), replayed with logs, then two warm-start variants using the existing seed machinery
(`warm_start_vector` maps a plan's controls onto columns by (source, period) / (lane, expiry,
period) and ignores the node suffix, so a static plan seeds every node with the same value: the
static policy copied into all information-set nodes, feasible by construction).

| solve | seed | status | objective (projected cost) | wall | B&B nodes | LP iterations | first incumbent |
|---|---|---|---|---|---|---|---|
| static comparator | incumbent (as released) | OPTIMAL | 25,320.81 | 8.3 s | 5 | 43,533 | 0.2 s |
| adaptive (as released) | none | FEASIBLE_TIME_LIMIT (gap 0.26 %) | 25,346.17 | 78.3 s | 913 | 469,554 | 0.5 s |
| perfect information (as released) | none | FEASIBLE_TIME_LIMIT (gap 0.08 %) | 25,153.51 | 78.3 s | 2,410 | 322,569 | 0.3 s |
| **adaptive, seeded with the static comparator** | static -> every node | **OPTIMAL** | **25,318.43** | **40.3 s** | 69 | 194,259 | 0.2 s |
| perfect information, seeded with the adaptive plan | adaptive root columns only (node plans not mapped) | FEASIBLE_TIME_LIMIT (gap 0.11 %) | 25,155.38 | 78.3 s | 2,930 | 340,084 | 0.1 s |

Reading: (1) the released adaptive solve's time-limited incumbent (25,346.17) is DEARER than the
static optimum (25,320.81), which is why the release matrix records "time-limited adaptive solve
did not improve on the static plan" for this cell; the true adaptive optimum is 25,318.43 <=
static, proven in 40 s once the solve starts from the static policy. The warm start changes the
starting point only; the problem, its bounds and its tolerance are untouched (equivalence: the
optimal set is the same; a proven optimum replaces a non-certified incumbent). (2) The PI solve
does not benefit from the naive seed (the adaptive node plans are not mapped onto the per-world
PI columns); it remains a report-only cost of the full budget on this class.

## Run 3 — planner-path replay, produce class, 12 worlds (3 histories, epochs [3, 6], 2 continuations; budget 42.9 s per solve)

| solve | seed | calls | status | objective | wall | nodes | first incumbent |
|---|---|---|---|---|---|---|---|
| static comparator (as released) | incumbent | warm_complete(equal) 0.02 s infeasible -> warm_complete(floor) **25.8 s, rejected** (no feasible point inside the completion cap) -> solve with the remaining 17.2 s | **NO_FEASIBLE_SOLUTION** | - | 43.1 s | 659 | none |
| adaptive (as released) | none | solve | FEASIBLE_TIME_LIMIT (gap 0.66 %) | 13,398.06 | 43.1 s | 2,882 | **37.6 s** |
| perfect information (as released) | none | solve | OPTIMAL | 13,186.00 | 0.7 s | 1 | 0.1 s |
| adaptive seeded with the static comparator | (no usable static plan -> no seed) | solve | FEASIBLE_TIME_LIMIT | 13,398.06 | 43.1 s | 2,903 | 37.5 s |
| perfect information seeded with the adaptive plan | adaptive root columns | completions 0.15 s accepted, solve | OPTIMAL | 13,186.00 | 0.8 s | 1 | 0.1 s |

Reading: on produce the difficulty is the FEFO indicator structure inside the tree worlds (2,688
`fefo` binaries at 12 worlds): the seeded static comparator spends 60 % of its budget in a
rejected warm-start completion (the P2 performance pass saw the same mechanism on long lanes) and
then finds no incumbent; the unseeded adaptive solve finds its first incumbent only at 37.6 s of
42.9 s. The perfect-information solve is trivial (per-world decisions make FEFO an LP). A warm
start cannot help where no feasible static plan is found; the candidate exact change here is the
strength of the FEFO / no-hoarding indicator rows (run 4).

## Run 4 — indicator big-M experiment, shared-order class, 12 worlds

Hypothesis B: the `depleted` / `fefo` / `priority` / `direct_first` indicator rows use the
location capacity (1e6 / volume) as M. A valid, much smaller M is the system-wide undominated
stock bound: opening stock + inbound + the sum over sources and periods of the P3 closure's exact
activation bounds (the largest quantity any undominated plan carries on a line). Experiment
rewrites those rows after the build (harness only) and measures the same five solves.

Shared-order class, 12 worlds: M = 63,739.5 (opening 1,200 + inbound 0 + Σ activation bounds; the
declared capacities of the fixture are 1e6 so the activation bounds carry the sum), 576 rows
rewritten per solve.

| solve | as released | with tightened M | with tightened M + static seed |
|---|---|---|---|
| static comparator | OPTIMAL 25,320.81, 8.3 s, 5 nodes | OPTIMAL 25,320.81, 8.7 s, 5 nodes | - |
| adaptive | time-limited 25,346.17, 78.3 s, 913 nodes | OPTIMAL 25,318.43, 75.0 s, 1,036 nodes | OPTIMAL 25,318.43, 42.4 s, 95 nodes (seed alone: 40.3 s, 69 nodes) |
| perfect information | time-limited 25,153.51, 78.3 s, 2,410 nodes | time-limited 25,151.56, 78.3 s, 2,716 nodes | time-limited 25,151.56, 78.3 s, 3,296 nodes |

Reading: the objectives are identical (the rewrite is exact), but the indicator M is not what
drives the shared-order class - the tightened rows save nothing beyond the warm start and do not
close the perfect-information proof. **Rejected for this class.** The produce class is measured
next (its binaries are FEFO indicators, where the M enters the relaxation directly).

Produce class, 12 worlds: the harness computed M = 600 - the opening stock alone, because
`activation_bounds` returns nothing outside the P3 shared-supplier-order class (it exists for that
class's linking rows only), so the experimental M was NOT a valid
bound of the model's stock (the source may deliver up to its declared 1e6). The measurements are
therefore an upper estimate of what a VALID stock bound could give, not evidence of an exact change:

| solve | as released | with M = 600 (invalid, upper estimate only) |
|---|---|---|
| static comparator | rejected completion 25.8 s -> NO_FEASIBLE_SOLUTION at 43 s | completion still 25.8 s (rows rewritten after it) -> OPTIMAL 13,424.64 in 1.7 s at the root |
| adaptive | time-limited 13,398.06 at 43 s, first incumbent 37.6 s | OPTIMAL 13,329.38 in 35.2 s (2,347 nodes); seeded 20.4 s (779 nodes) |
| perfect information | OPTIMAL 13,186.00, 0.7 s | OPTIMAL 13,186.00, 0.5 s |

Run 5 certifies the loose optima with a 900 s budget to read these numbers correctly. Decision:
a valid stock bound for the FEFO / no-hoarding indicator rows needs the undominated purchase
quantity of EVERY line (opening + inbound + Σ over lines and periods), a dominance argument that
the P3 closure established per line only for lines with activation rows; extending it to every
line, with MOQ / pack rounding and continuation credits, is a formulation change whose exactness
must be proven line by line before any use. Not done in this closure (recorded as the deferred
candidate for the produce / FEFO class); the warm start is adopted alone.

## Run 5 — certification of the loose produce optima (900 s budget, planner kwargs, no rewrite)

| solve | status | objective | wall | nodes |
|---|---|---|---|---|
| static comparator, unseeded, loose rows | OPTIMAL | 13,424.644 | 73.7 s | 5,960 |
| adaptive, unseeded, loose rows | OPTIMAL | 13,329.380 | 89.6 s | 8,481 |

The objectives equal the run-4 values to 1e-9: on this instance no optimal plan holds more than
the opening stock at any period, so the invalid M happened not to bind - a coincidence of the
instance, not a proof; the run-4 timings stay an upper estimate. What run 5 does establish: the
produce class at 12 tree worlds needs 74-90 s of proof for its static and adaptive tree solves
against a 43 s budget, i.e. the released time limits are genuinely binding there, and the
released adaptive incumbent (13,398.06) sits 0.52 % above the optimum. With a usable static plan
the seeded adaptive solve reaches the same optimum in about half the unseeded time (run 3 / 4).

## Run 6 — P4 evidence chain on the warm-start candidate (`p4_benchmark --tag p4_perf_closure`, invariants, adversarial)

28 / 28 fixtures, 27 / 27 invariants, 25 / 25 adversarial. Objective differences against the
release record `benchmarks/p4_release`: none (every static / adaptive / PI cost identical
to 1e-6 relative). S1 (integer case packs, the fixture whose adaptive solve time-limited at the
release): statuses release {static, adaptive, PI} = ('OPTIMAL', 'FEASIBLE_TIME_LIMIT', 'FEASIBLE_TIME_LIMIT')
-> after = ('OPTIMAL', 'OPTIMAL', 'FEASIBLE_TIME_LIMIT'), solve seconds (9.1, 42.9, 42.9) -> (9.6, 10.3, 42.9).

## Run 7 — repeatability of the single-SKU 16-world cell on the after code

Two repeats: planner 29.50 s and 29.52 s; tree solves (19.47 s time-limited static comparator,
9.39 s adaptive OPTIMAL, 0.12 s PI) and (19.47, 9.40, 0.12). The before run's 26.5 s / 6.4 s is
one draw of the same cell; the cell is batch-only (16 worlds) and its planner verdict is unchanged.

## Run 8 — frozen regressions on the candidate (`gates/`, one pass, no rerun needed)

| gate | result |
|---|---|
| P3 shared-MOV production snapshot, P4 disabled | 12.29 s local, 18 HiGHS calls, decision view and candidates identical (timing stripped), no recourse block |
| P1 canonical B / T / Q / A + P0 cell 15 | CANONICAL REGRESSION PASS; P1 invariants 60 passing, 0 failures |
| P2 | 20 / 20, 18 / 18, INVARIANTS PASS, 1,720 / 1,720 identical vs `p2_perf_closure` |
| sector | 26 / 26, 19 / 19, 416 / 416 identical vs `sector_perf_closure` |
| P3 (current baseline, P4 disabled) | 30 / 30, 34 / 34, 23 / 23, 2,304 / 2,304 identical vs `p3_perf_closure` (historical record 2,273 / 2,304 + 31 proven ties unchanged) |
| P0 six-cell arm `p4_perf` vs `router_cycle` | 120 / 120 decision-identical in one pass |
| P4 | 28 / 28 (objectives identical to the release record), 27 / 27, 25 / 25, release-audit tests green |

