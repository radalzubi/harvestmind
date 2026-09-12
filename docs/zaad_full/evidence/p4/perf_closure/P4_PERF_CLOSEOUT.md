# ZAAD P4 — production performance closure (TRACK A): closeout

| item | value |
|---|---|
| original P4 release runtime | `8c813ac` (tag `p4-release-runtime`, Fly v20 `canonical-8c813ac`) - unchanged, historical |
| branch | `perf/p4-recourse-performance-closure` from `main` `adf45e4` (docs-only above `8c813ac`) |
| product commit | `5b3be50` |
| tested head (CI once) | `a9b2b92` (PR [#69](https://github.com/radalzubi/harvestmind/pull/69), run 34696879480: green on every gate - ruff, gitleaks, security (bandit, pip-audit), mypy, docker build, frontend, zaad frozen regression, pytest 4 shards 362 + 275 + 170 + 1,139 = 1,946 passed, 2 skipped; the two CodeQL analyses fail as on every prior release (code scanning not enabled on the private repository, environment defect, not a gate). A first run on the pre-lint head a9a4b42 was cancelled after its supersession) |
| merge | `6b58764` (runtime tree identical to the tested head) |
| new performance-closed runtime | `6b58764` -> Fly `zaad-api` v21 `registry.fly.io/zaad-api:canonical-6b58764 (digest sha256:38896b8dd0fc...), built from a clean detached checkout (tree 5e88df3, identical to the tested head), same machine 0804e0dfd1e948 / volume / secrets / env` |
| tag | `p4-performance-closure-runtime` -> `6b58764` |

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
1,946 passed, 2 skipped, 0 failed locally (5 m 36 s) and on CI.

## CI, merge, deployment, production benchmark

* CI once on the tested head `a9b2b92` (run 34696879480): green on every gate; merged as `6b58764` (merge commit; whole-tree hash `5e88df3` identical to the tested head; no post-merge rerun).
* Deployed from a clean detached checkout of `6b58764`: Fly `zaad-api` v21, `registry.fly.io/zaad-api:canonical-6b58764`; machine `0804e0dfd1e948` (shared-cpu-2x, 2 GB), volume `harvestmind_data`, 11 secrets and env unchanged.
* Bounded production benchmark (`production/prod_bench.json`, synthetic self-serve workspace, host steal measured across each request from `/proc/stat`):

| case | v20 (release, 2026-09-12 morning, steal 2.5-6x) | v21 (this closure, steal <= 0.04 on the interactive cases) | tree solves on v21 |
|---|---|---|---|
| simple P4 (C, tree 6) | 3.2 s | 3.1 s | static 0.74 s, adaptive 0.45 s OPTIMAL (1 node), PI CERTIFIED |
| P2 + P4 (F, tree 8) | 3.7 s | 3.7 s | static 0.94 s, adaptive 0.66 s OPTIMAL, PI CERTIFIED |
| P3 + P4 (G, tree 6) | 3.2 s | 3.4 s | static 0.72 s, adaptive 0.49 s OPTIMAL, PI CERTIFIED |
| PRODUCE + P4 (D, tree 6) | 75.8 s (steal 2.5x) | 67.1 s (steal 0.02) | static comparator FEASIBLE_TIME_LIMIT at its 43.1 s budget, adaptive OPTIMAL 7.9 s (89 nodes), PI CERTIFIED; the produce cost is formulation (FEFO indicators), not steal |
| shared-order job (N, tree 6, budget 12 s, `/jobs`) | TIMEOUT at 252 s, steal 6.05x | TIMEOUT at 252 s, **steal 3.21x** (steal 23,919 vs user 7,299 + system 146 jiffies over 269 s: 74 s of CPU delivered); API answered all 18 health probes (max 0.3 s) | no report (safe timeout); locally this cell is 36 s; the closure changes its 6-world local wall by +3 s (noise) and does not close the host-throttling residual recorded at the P4 release |

* Logs after the benchmark: no 5xx, no traceback, no OOM; 56 x 200, 1 x 202.
* Tag `p4-performance-closure-runtime` = `6b58764` pushed; `p4-release-runtime` (`8c813ac`), `p4-frozen-product`, `p4-frozen` and every older tag unmoved (verified peeled on origin).
* Residuals: (1) the shared-supplier-order recourse class through `/jobs` still times out on the shared-cpu-2x machine under 3-6x steal - a machine-class decision, unchanged; (2) the produce class at 12 / 16 tree worlds remains bounded by its FEFO indicators (identified exact candidate: a proven per-line undominated stock bound for the indicator rows); (3) the perfect-information diagnostic on the shared-order class stays NON_CERTIFIED at its budget (report-only).

## Verdict

One exact change adopted with its equivalence argument, measured before and after on the same
machine, every frozen regression green in one pass, CI green once on the exact candidate, tree
identity proven, deployed and benchmarked in production, historical tags immutable.

**ZAAD P4 PRODUCTION PERFORMANCE CLOSURE — PASS.** Original P4 release runtime `8c813ac`; new
performance-closed runtime `6b58764` (Fly v21, `canonical-6b58764`, tag
`p4-performance-closure-runtime`). Validation status unchanged: ENGINEERING VALIDATED, NOT
REAL-DATA VALIDATED.
