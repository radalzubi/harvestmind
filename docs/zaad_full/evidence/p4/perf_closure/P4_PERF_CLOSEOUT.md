# ZAAD P4 — production performance closure (TRACK A): closeout

| item | value |
|---|---|
| original P4 release runtime | `8c813ac` (tag `p4-release-runtime`, Fly v20 `canonical-8c813ac`) - unchanged, historical |
| branch | `perf/p4-recourse-performance-closure` from `main` `adf45e4` (docs-only above `8c813ac`) |
| product commit | `5b3be50` |
| tested head (CI once) | {{TESTED_HEAD}} (PR {{PR}}, run {{CI_RUN}}: {{CI_RESULT}}) |
| merge | {{MERGE_SHA}} (runtime tree identical to the tested head) |
| new performance-closed runtime | {{MERGE_SHA}} -> Fly `zaad-api` {{FLY_RELEASE}} `{{IMAGE}}` |
| tag | `p4-performance-closure-runtime` -> {{MERGE_SHA}} |

## Scope

Production-performance closure of P4 adaptive recourse: semantics frozen (no new observable, action,
tree size, economics, gate or heuristic path). Diagnosis before any change (`P4_PERF_DIAGNOSIS.md`),
every run logged (`P4_PERF_LOG.md`), before / after (`P4_PERF_RESULTS.md`).

## Root cause

The cost of P4 on the heavy class is not model size, construction or the P3 shared-order rows per
node: the adaptive tree solve started from nothing while a feasible policy (the static comparator's
plan) was at hand, and on the shared-supplier-order class HiGHS spent the whole budget in a
branch-and-bound that ended with a non-certified incumbent dearer than the static optimum. On the
produce class the FEFO indicator structure inside the tree worlds bounds both the static and the
adaptive solves (and defeats the static comparator's warm-start completion); a valid stock bound for
those rows is identified but unproven, and left out.

## Accepted exact change (one)

Warm-start the adaptive tree solve from the static comparator's plan (`zaad/full/planner.py`,
`zaad/recourse/policy.compare`). Equivalence: a warm start supplies HiGHS a starting incumbent; the
model, bounds, integrality and tolerance are unchanged, so the optimal set is unchanged; the seed is
verified by the formulation's own completion and rejected when infeasible. The frozen builder
`zaad/full/model.py` and every P0-P3 path are untouched (the seed lives inside the recourse block).

| cell | before | after |
|---|---|---|
| shared order, 12 tree worlds, planner wall | 177.3 s; adaptive 78 s time-limited, incumbent 25,346.17 (dearer than static 25,320.81); verdict "NOT SELECTED (time-limited adaptive did not improve on the static plan)" | 138.1 s; adaptive **39.4 s OPTIMAL 25,318.43** (69-95 nodes); verdict NO MATERIAL ADAPTIVE BENEFIT |
| shared order, 8 worlds | 59.8 s (adaptive 20.8 s) | 54.5 s (adaptive 15.8 s) |
| shared order, 16 worlds | 193.5 s (adaptive and PI time-limited) | 193.2 s (unchanged: still time-limited) |
| produce, 6 / 8 worlds | 41.1 / 60.2 s | 35.7 / 54.2 s |
| commercial case packs (fixture S1, evidence path) | adaptive FEASIBLE_TIME_LIMIT at 42.9 s | adaptive OPTIMAL in 10.3 s, identical objective |
| interactive classes (<= 8 worlds, not shared-order) | 0.4-3.1 s | unchanged within 0.5-3 s |
| dimensions | unchanged (rows / columns / binaries identical; the change is a starting point) | |

Rejected: indicator big-M tightening (no gain on the shared-order class; the produce experiment's
bound was invalid - deferred until a per-line undominated stock bound is proven); PI seeding
(proof-bound); decomposition (one connected component: cash, shared order, lanes). Gate change:
none, and none recommended (the 16-world shared-order cell still time-limits).

## Frozen regressions on the candidate (one pass)

P3 shared-MOV snapshot identical (12.29 s, P4 disabled); P1 canonical identity + 60 invariants; P2
20 / 20, 18 / 18, 1,720 / 1,720; sector 26 / 26, 19 / 19, 416 / 416; P3 30 / 30, 34 / 34, 23 / 23,
2,304 / 2,304 (historical 2,273 / 2,304 + 31 proven ties unchanged); P0 six-cell 120 / 120; P4
28 / 28 (objectives identical to the release record), 27 / 27, 25 / 25, release-audit tests; PI
certification, exact-or-REPLAN_REQUIRED and approval semantics unchanged (same tests). Full suite:
{{SUITE}}.

## CI, merge, deployment, production benchmark

{{RELEASE}}

## Verdict

{{VERDICT}}
