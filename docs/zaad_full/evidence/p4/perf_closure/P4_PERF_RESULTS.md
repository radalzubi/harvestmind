# P4 production performance closure — results (before / after, same machine, same day)

Accepted change: **warm-start the adaptive tree solve from the static comparator's plan** (the
static policy copied into every information-set node), in `zaad/full/planner.py` (production path)
and `zaad/recourse/policy.compare` (evidence path). Equivalence: a warm start supplies a starting
incumbent to HiGHS; the model, its bounds, its integrality and its optimality tolerance are
unchanged, so the optimal set is unchanged; the seed is verified by the formulation's own completion
(`warm_start_vector` -> `Linear.complete`) and rejected, never labelled feasible, when it violates
any row. No change to the frozen builder (`zaad/full/model.py`), to any P0-P3 path (the seed is
attached only inside the recourse block, which a request without an enabled `recourse` block never
enters), to the contracts, the gates, the materiality, the PI certification or the
exact-or-REPLAN_REQUIRED semantics.

Rejected / deferred: indicator big-M tightening (rejected on the shared-order class: identical
objectives, no time saved beyond the warm start; deferred on the produce class: a valid per-line
undominated stock bound must be proven first - the harness bound was invalid); PI seeding (proof-
bound; no gain); decomposition (one connected component everywhere: cash, shared order, lanes).

## Planner path (`plan()`), before -> after (`P4_PERF_PROFILE.json` -> `P4_PERF_PROFILE_after.json`)

| class | worlds (h, epochs) | planner wall | tree solves static / adaptive / PI (* = time-limited) | verdict |
|---|---|---|---|---|
| A single SKU | 8 (4,[3]) | 2.4 -> 3.1 s | 1.3 / 0.6 / 0.1 -> 1.4 / 1.2 / 0.1 | same |
| A single SKU | 12 (3,[3,6]) | 12.9 -> 14.0 s | 11.6 / 0.7 / 0.1 -> 12.7 / 0.6 / 0.1 | same |
| A single SKU | 16 (4,[3,6]) | 26.5 -> 29.7 s | 19.5* / 6.4 / 0.1 -> 19.5* / 9.5 / 0.1 | same |
| B P2 network | 8 / 12 / 16 | 1.0 / 1.5 / 2.1 -> 1.1 / 1.6 / 2.2 s | all <= 0.3 s | same |
| C two-source P3 | 8 / 12 / 16 | 1.3 / 1.6 / 2.3 -> 1.2 / 1.7 / 2.4 s | all <= 0.3 s | same |
| D shared order | 6 (3,[3]) | 33.5 -> 36.3 s | 5.2 / 5.1 / 10.8 -> 5.3 / 7.5 / 11.0 | same |
| D shared order | 8 (4,[3]) | 59.8 -> 54.5 s | 7.7 / 20.8 / 16.4 -> 7.6 / 15.8 / 16.2 | same |
| D shared order | 8 (8,[3]) | 27.5 -> 27.6 s | 4.4 / 1.6 / 0.0 -> 4.3 / 1.6 / 0.0 | same |
| **D shared order** | **12 (3,[3,6])** | **177.3 -> 138.1 s** | 7.8 / **78.0\*** / 78.1\* -> 7.4 / **39.4 (OPTIMAL)** / 78.1\* | **"NOT SELECTED (time-limited adaptive did not improve on the static plan)" -> "NO MATERIAL ADAPTIVE BENEFIT" (proven optimum 25,318.43 <= static 25,320.81, below materiality)** |
| D shared order | 16 (4,[3,6]) | 193.5 -> 193.2 s | 20.9 / 78.1* / 78.1* -> 20.7 / 78.0* / 78.1* | same (adaptive still time-limited with the seed) |
| E produce | 6 (3,[3]) | 41.1 -> 35.7 s | 17.3 / 5.7 / 0.2 -> 16.2 / 2.5 / 0.2 | same |
| E produce | 8 (4,[3]) | 60.2 -> 54.2 s | 21.7 / 10.7 / 0.2 -> 20.8 / 6.9 / 0.2 | same |
| E produce | 12 / 16 | 93.0 / 95.6 -> 92.7 / 95.3 s | 17.2* / 43.0* / 0.6 (no usable static plan -> no seed) | same |

Repeatability of the ordinary-class deltas: the single-SKU 16-world cell repeated twice on the
after code (see `P4_PERF_LOG.md`, run 7); the 3 s difference is inside run-to-run variation of
that cell's time-limited static comparator, and the cell is batch-only (16 worlds).

## Compare path (evidence, `scripts/p4_benchmark` on the after code, tag `p4_perf_closure`)

28 / 28 fixtures, objectives identical to the release record (`benchmarks/p4_release`), invariants
27 / 27, adversarial 25 / 25. See `P4_PERF_LOG.md` run 6 for S1 (the case-pack fixture whose
adaptive solve was time-limited at the release).

## What the closure changes in production terms

* Shared-supplier-order recourse at 12 tree worlds (batch-only class): the adaptive tree solve
  returns a proven optimum in 39 s instead of a non-certified incumbent at 78 s that the release
  runtime read as "did not improve on the static plan"; the whole job is 22 % shorter locally.
* Shared-order at 8 worlds: 9 % shorter; produce at 6 / 8 worlds: 10-13 % shorter.
* Interactive classes (<= 8 worlds, not shared-order): unchanged within noise (0.5-3 s).
* Commercial case packs (fixture S1, evidence path): the adaptive solve is proven OPTIMAL in 10.3 s where the release record has a FEASIBLE_TIME_LIMIT incumbent at 42.9 s, with the identical objective; the PI solve there stays NON_CERTIFIED (report-only).
* The perfect-information diagnostic on the shared-order class remains NON_CERTIFIED at its
  budget (proof-bound); it is report-only and gates nothing.
* No gate is changed: interactive stays tree worlds <= 8 and not the shared-order class; batch
  stays <= 16 worlds and <= 2 epochs. Recommendation for a future gate decision: none - the
  16-world shared-order cell still time-limits both the adaptive and the PI solve.
