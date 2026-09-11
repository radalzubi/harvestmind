# P3 production performance closure: AFTER

Candidate runtime: branch `perf/p3-shared-mov-closure` (parent `main` `1e712c9`, runtime-identical to
the released `0de6850`). Local machine and solver builds as in the BEFORE record. Every local figure
comes from `local_profile_<case>_after.json`; gate logs and review-level compares are under `gates/`.

## What changed (runtime)

`zaad/full/model.py` only:

* `shared_supplier_orders(req)`: the class - a P3 sourcing review in which a supplier carrying
  order-level economics serves more than one SKU. Everything below applies inside it and nowhere else.
* `activation_bounds(...)`: the exact undominated-quantity bound per (line, period), used as the
  coefficient of the `order` and `active` linking rows (the purchase column keeps its declared capacity).
* `search_options(req)` -> `{"mip_allow_restart": False}` through highspy for the class; the frozen
  scipy route everywhere else.
* A warm-start seed that exceeds a line's bound is rejected with the reason instead of after two
  completion solves (it is a dominated plan and could not be pinned anyway).

`scripts/p1_p0_arms.py`: arm registrations `p3_perf_closure` / `p3_perf_closure_rerun` (evidence
only). `tests/unit/test_zaad_activation_bounds.py`: the structural regression (bound value and
monotonicity, linking coefficient equals the bound while the column keeps its capacity, one order
binary per supplier and period and none per world, scope, seed rejection, dominance: the optimum
with the bound equals the optimum with the capacity as M). No wall-clock assertion.

## A. exact shared-MOV production snapshot

| | before | after |
|---|---|---|
| wall, local | 17.55 s | **12.8 s** (three runs 11.98 / 12.85 / 12.83) |
| solver wall, local | 17.06 s | 12.3 s |
| solver calls | 18 | 18 |
| base_stock | 4.68 s, 1,214 nodes | 0.15 s, 1 node |
| deterministic_network | 2.57 s, 260 nodes | 2.9 s, 29 nodes |
| stochastic_network | 4.03 s, 13 nodes | 3.4 s, 9 nodes |
| cadence_2 / cadence_4 | 1.30 / 1.16 s | 2.4 / 0.9 s |
| service frontier oracles (4) | 0.40 / 0.47 / 0.38 / 0.64 s, 84 / 82 / 51 / 49 nodes | 0.52 / 0.43 / 0.55 / 0.45 s, 1 node each |
| value of alternates | 1.65 s, 5 nodes | 0.87 s, 3 nodes |
| variables / binaries / rows | unchanged (1-world 2,476 / 60 / 1,363; 3-world 5,904 / 156 / 3,759) | unchanged: no variable added or removed |
| linking big-M on `src_A` at period 0 | 1,000,000 | 2,422 (3-world), 2,543 (surrogate), 2,205 (base) |
| status | every solve OPTIMAL | every solve OPTIMAL |
| selected action | stochastic_network, NO_ACTION, PURCHASING_ECONOMICS, MATERIAL_IMPROVEMENT | **identical** |
| objective (every candidate) | 51,267.0518 / 30,899.0274 / 25,656.5736 / 25,408.1631 / 25,458.3590 / 25,458.3590 / 25,633.3991 / 25,703.1968 | **identical to the fourth decimal** |
| purchases (plan) | src_A 621.3 @1, 2,187.4 @4; src_A_B 621.7 @1, 2,209.4 @4; src_S2 24.6 @0; src_S2_B 29.0 @0 | **identical** |
| source shares | A 0.991 / 0.009; B 0.990 / 0.010 | **identical** |
| MOV satisfaction | orders at periods 1 and 4 above 5,000 | **identical** |
| period-0 transfers | 334.4 units | 238.6 units - the other representative of an equal-cost lane tie (same objective) |
| settled selected TOTAL / incumbent TOTAL | 25,960.31 / 26,045.65 | 25,974.55 / 26,045.27 (settlement of the tie-equivalent transfer plan on the confirmation worlds; materiality verdict unchanged) |
| approval / execution | required / false | required / false |
| wall, Fly | 218.4 s (release smoke, throttled); 76.2 s (unthrottled rerun) | filled in the production re-run section of the closeout |

## B. multi-SKU shared capacity (no supplier terms: out of the class)

| | before | after |
|---|---|---|
| wall, local | 2.47 s | 2.81 s (run noise; identical call count 23, identical models) |
| decision | stochastic_network, CHANGE_SOURCE_MIX, settled TOTAL 39,850.471 | **bit-identical** |

## C. correlated plant group (no supplier terms: out of the class)

| | before | after |
|---|---|---|
| wall, local | 3.77 s | 3.96 s (run noise; 10 calls, identical models) |
| decision | deterministic_network 9,747.326489, A / B split, TOTAL 12,986.559 | **bit-identical** |

## D. simple two-source economics (out of the class)

| | before | after |
|---|---|---|
| wall, local | 0.41 s | 0.44 s |
| decision | incumbent retained, TOTAL 12,889.393 | **bit-identical** |

## E. P2 representative network case (no P3 block)

| | before | after |
|---|---|---|
| wall, local | 0.34 s | 0.36 s |
| decision | incumbent retained, TOTAL 12,936.558 | **bit-identical** |

## F. P1 representative cases

Canonical regression on the final code: B / T / Q / A twelve-review identity True, P0 cell 15
identical (`gates/canonical_regression.log`). MOV, MOQ, packs, payment and continuation semantics
are untouched by construction (these requests carry no P3 block, so the class predicate is false).

## Regression gates on the final code

| gate | result |
|---|---|
| P3 fixtures | 30 / 30 PASS (`gates/p3_benchmark.log`; 480 ZAAD reviews p50 0.69 s / p95 18.7 s / max 43.6 s; 0 time-limited) |
| P3 invariants | 34 / 34 (`gates/p3_invariants.log`) |
| P3 adversarial | 23 / 23 (`gates/p3_adversarial.log`) |
| P3 review identity vs `p3_corrective` | 2,273 / 2,304 identical; the 31 others are all `C6_shared_mov_multi_sku` (gated 16, single:supplier 15): review-0 candidates identical on both seeds (`tie_evidence/c6_*`), the first differing key is `transfers` on an equal-cost lane tie, the later reviews are that tie's cascade (`gates/p3_perf_closure_compare.json`) |
| P2 | 20 / 20 fixtures, 18 / 18 principles, invariants PASS, 1,720 / 1,720 reviews identical (344 / 344 ZAAD) |
| sector | 26 / 26 fixtures, 19 / 19 invariants; ZAAD (gated) reviews 416 / 416 identical to `sector_corrective`; the age-at-receipt correction preserved. 19 differing reviews all in the `echelon_base_stock` comparator policy on X1 / X2 / P3_age_at_receipt, a policy this code cannot reach (no P3 block): the same comparator differs from the same baseline in 13 reviews when rerun on the unchanged released code (`gates/sector_variability_main_compare.json`), i.e. pre-existing run-to-run variability of that comparator, recorded and not fixed here |
| P1 | canonical B / T / Q / A identity; invariants 60 passing, 0 failures |
| P0 | six-cell arm `p3_perf_closure` vs `router_cycle`: cells 15 / 16 / 20 / 21 / 90 decision-identical, cell 108 28 / 30 under CPU contention (label-only differences, identical unmet and cost); quiet rerun of cells 21 and 108 (`p3_perf_closure_rerun`) 50 / 50 identical -> 120 / 120 under the established protocol |
| unit tests touching the model (12 files incl. sectors and the new test) | 144 passed |
| ruff / mypy (CI scope) | clean |

## Rejected experiments (measured, `local_profile_shared_mov_*`, `P3_SHARED_MOV_PROFILE.md`)

* heuristic effort 0 / 0.01 / 0.2, scaling strategy, dual pricing, LP age limit, cut pool limit,
  clique-table threshold: no change in time on any model.
* presolve off: 3x faster on the cadence model, neutral or slower on the others - not robust.
* a tighter big-M on the frozen `depleted` indicators (20,000 or 2,000 instead of the storage
  capacity): no gain (1.4 - 2.4 s either way) - the frozen P0 rows are not the driver and stay untouched.
* the seed term in the bound (keep every warm-start seed admissible): loosened the mean-world bound
  by the incumbent's over-buy and cost 1.6 s; replaced by explicit rejection of dominated seeds.
* moving the report-only oracle and alternate valuations off the synchronous path: 21 % of the
  before time, but they cost 3 s after the bound (1-node solves) and their asynchronous return would
  need a new report contract; not needed for the gate.
* broad scope (every request with activation binaries, then every shared-order request): exact on
  every candidate, but flipped tie representatives in E4 / R4 / T through the selector's confirmation
  gates; withdrawn (`tie_evidence/`).
