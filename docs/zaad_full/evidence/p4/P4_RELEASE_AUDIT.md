# ZAAD P4 — Adaptive Recourse: release audit

Scope: the four release blockers of the P4 release brief, audited on the exact local engineering
freeze (`p4-frozen-product` = `d8cdad5`, evidence `p4-frozen` = `7059379`), with the narrowest
corrections required, on the release branch `release/zaad-p4-adaptive-recourse` (base: current `main`
`b24fd02`, whose only changes since the P4 base `ebcd1d0` are seven documentation files under
`docs/cofounder/` and `docs/zaad_full/`; no runtime file). The frozen evidence of `d8cdad5` is kept
verbatim under `frozen_local/`; the top-level `P4_INVARIANTS`, `P4_ADVERSARIAL`, `P4_PERFORMANCE`
records and `benchmarks/p4_release.*` are the release-candidate runs.

## Blocker A — perfect-information semantics under time limits

**Before (d8cdad5).** `policy.compare` and the planner used `perfect.projected_cost` - the primal
incumbent - whenever the perfect-information (PI) solve returned a usable plan, including status
`FEASIBLE_TIME_LIMIT`; the ordering `PI <= adaptive <= static` was asserted on that value, a
violation rejected the adaptive candidate, and the operator block carried the fixed text
`perfect_information_scope = "lower bound only: ..."` regardless of status. On the frozen evidence the
sector fixture S1 (integer case packs) had time-limited adaptive and PI solves, and the frozen
performance matrix already shows one cell (`p3_multi_sku_shared_order`, 3 histories, epochs [3, 6])
verdict `ADAPTIVE PLAN REJECTED (ordering check failed)` - a rejection driven by non-certified
solves.

**Mathematical issue.** For a minimisation a time-limited primal objective is the cost of one
feasible policy, an upper bound on the optimum, never a lower bound. Asserting `PI_feasible <=
adaptive` can fail without any modelling error, and calling that value a bound or an optimum is
false. The value HiGHS returns as `mip_dual_bound` is a lower bound on the *solver objective*
(the ledger cost plus objective-only terms: the 1e-4 timing tie-break, shortage surrogate,
smoothing), which is not the projected (ledger) cost, so it is not comparable with the reported
expected costs either.

**Correction (narrow).** `zaad/recourse/policy.py` gains `assess()` (used by `compare` and the
planner alike):

* `perfect_status` = CERTIFIED (status OPTIMAL) / NON_CERTIFIED (FEASIBLE_TIME_LIMIT) / UNAVAILABLE.
* `perfect_cost` is set only when CERTIFIED; otherwise `perfect_feasible_cost` carries the incumbent.
* the ordering check is `adaptive <= static` (both usable) and additionally `PI <= adaptive` only
  when CERTIFIED; a NON_CERTIFIED PI never enters it and can never reject the adaptive plan.
* `perfect_solver_bound` = HiGHS `mip_dual_bound`, reported apart, in the engineering block only,
  with an explicit units note; never a policy cost, never compared with the projected costs.
* `value_certified` records whether static and adaptive were both proven optimal; the operator
  block says so when they were not.

`zaad/recourse/explain.py`: `perfect_information_status`, `perfect_information_cost` (certified
only), `perfect_information_feasible_cost`, status-dependent `perfect_information_scope` (the word
"bound" appears only when certified), `ordering_scope`, explanation sentences. Evidence scripts
(`p4_benchmark` principle `pi_ordering`, `p4_invariants` 23, `p4_adversarial` double-counting and
report-only cases) follow the same rule; the fixture table marks a non-certified PI value
"(feasible, not certified)". Design doc section 7 and the design review updated.

**Tests.** `tests/unit/test_zaad_recourse_release.py` A1 (certified ordering, and a certified
violation is still a failure), A2 (time-limited primal is not a bound), A3 (primal and solver bound
separate), A4 (report never says "bound" unless certified; feasible cost reported; approval
unchanged), A5 (a dearer non-certified PI never rejects the adaptive plan; unavailable PI handled),
A6 = the existing disabled-path identity test plus B7 (a static solution is untouched by the fallback
attachment).

**Final semantics.** PI diagnostic CERTIFIED only when OPTIMAL; otherwise reported as a feasible
cost with status NON_CERTIFIED and excluded from every correctness claim. On the release candidate:
S1 is NON_CERTIFIED (adaptive and PI time-limited at the request's budget) and passes on
`adaptive <= static`; every other fixture with a PI solve is CERTIFIED and ordered.

**Verdict wording (found while re-running the matrix).** The frozen block turned every falsy
`ordering_ok` into "ADAPTIVE PLAN REJECTED (ordering check failed)", including `None` (no static
comparator plan: infeasible, or none found within the budget - S4, and the produce class at 16
worlds where the static comparator returned NO_FEASIBLE_SOLUTION) and the case of a time-limited
adaptive incumbent dearer than the static plan (the shared-order class, 3 histories, epochs [3, 6]:
static OPTIMAL 25,320.8, adaptive FEASIBLE_TIME_LIMIT 25,346.2, PI NON_CERTIFIED). Neither is an
ordering violation. Now: `None` -> "ADAPTIVE PLAN NOT COMPARABLE (no static comparator plan ...)";
a false check with a certified (OPTIMAL) adaptive solve -> "REJECTED (ordering check failed)"; with a
time-limited adaptive solve -> "NOT SELECTED (time-limited adaptive solve did not improve on the
static plan)". In every case the adaptive candidate does not enter selection (unchanged gate).
Test A7.

**Result: PASS (corrected).**

## Blocker B — unseen information-set fallback

**Before (d8cdad5).** `information.lookup` returned the exact-signature set when one existed,
otherwise the nearest set under `_distance` (normalised absolute difference on quantised cells, one
per categorical mismatch, ties to the lower rank). Where used: (1) the planner's `evaluate()` settles
an adaptive candidate on the selection + confirmation worlds; those worlds are not the tree worlds,
so every one of them went through `lookup` (exact at the first epoch for the selection worlds, which
share the tree's histories; nearest for every confirmation world and, with two epochs, for the
second epoch of the selection worlds); (2) `explain.recourse_block` reported exactness per world;
(3) the adversarial case "policy lookup leaking the future" and one unit test. The optimisation
construction itself never used it (node membership is exact by construction).

**Risk.** Settlement was evaluating a policy the operator must never execute: for an observation
outside the modelled branches it executed the nearest branch's action, crediting (or debiting) the
adaptive candidate on states the model did not evaluate; a live evaluation reusing the same lookup
would have done the same silently.

**Correction (narrow).** Nearest routing removed entirely (`_distance` deleted). `lookup` returns
`(node, True)` on an exact canonical-signature match and `(None, False)` otherwise. The declared
fallback: `policy.attach_fallback` attaches the static comparator's commitments to the adaptive
solution (`recourse["fallback"]`); `world_plan` gives a window whose observation matches no branch
those static commitments (the plan the operator has without adaptation), never a branch action; the
lookup is reported REPLAN_REQUIRED. The planner's `evaluate` records `policy_lookup` per world; the
operator block carries `unseen_observation_rule`, `replan_required` (worlds outside the branches, of
how many, and which fallback), the per-world table in the engineering block, and a sentence when
any evaluation world was outside the branches. Generated tree worlds map exactly (membership and
signature agree; test B1).

**Live behaviour.** Canonicalise the observation (the same quantisation), exact match -> that
branch's committed action for the window; no match -> REPLAN_REQUIRED: no adaptive action, the
static commitments stand, a replan is required before any change. Categorical boundaries (receipt
pending vs. received, arrival period, plant-group receipts) can never be crossed because only
equality matches.

**Tests.** B1 every generated world maps exactly by membership and by signature (one- and
two-epoch trees); B2 world reordering leaves signatures, probabilities and memberships unchanged;
B3 a demand history outside every branch -> `(None, False)`, REPLAN_REQUIRED, the world receives
the static window; B4 a receipt-status mismatch is refused (no reinterpretation); B5 quantisation at
a grid boundary is deterministic and name-independent; B6 the report exposes the rule and counts
worlds outside the branches; B7 the disabled / static path is untouched. Adversarial "policy lookup
leaking the future" now also asserts that an outside-support history selects no branch.

**Observation recorded.** With two review epochs the planner's evaluation worlds (the selection
draw and the confirmation worlds) share the tree's histories only through the first epoch, so at the
second epoch every evaluation world is outside the modelled branches and is evaluated under the
static commitments (`replan_required` = all evaluation worlds); with one epoch the selection worlds
match exactly and only the confirmation worlds fall back. The adaptive candidate is therefore
credited with adaptation only where its information is in the modelled support - the conservative
reading the release requires. Extending the tree so that the evaluation worlds are leaves is P4
follow-up work, not a release change.

**Result: PASS (corrected; nearest fallback removed from the optimiser path).**

## Blocker C — asynchronous jobs safety

Audited `zaad/full/jobs.py`, `api/routers/zaad_full.py` (`large_payload`, `/jobs` endpoints),
`api/dependencies.py`, `tests/integration/test_zaad_jobs.py`, the Fly configuration and secrets.

| item | finding |
|---|---|
| C1 authentication | `/jobs` (submit, list, read, cancel) depend on `authenticated` -> 401 without a bearer / API key; the same dependency as `/shadow` and `/plan/from-workspace` |
| C2 tenant binding | the job row stores the operator; `get`/`list`/`cancel` filter by operator, another tenant's job reads as 404; the payload `operator_id` must equal the authenticated operator (403); integration test `test_submit_poll_result_and_isolation` |
| C3 validation | `large_payload` parses with `Request.model_validate_json` (every contract validator incl. `recourse` and sector physics), then applies the batch envelope: recourse tree worlds <= 16 and epochs <= 2 (`BATCH_LIMITS`), `LARGE_LIMITS` on SKUs / sources / services / horizon / scenarios / stresses, 16 MiB body. Same 422 shape as `/plan` |
| C4 complexity bound | `tree_worlds(req) = scenarios x continuations ^ epochs` checked before any model; > 16 -> 413 (test `test_batch_path_accepts_what_plan_refuses_and_caps_the_tree`) |
| C5 worker isolation | one `multiprocessing` spawn process per job (`_run` -> `plan(req)`), a process-wide slot semaphore (`ZAAD_JOB_WORKERS`, default 1), per-operator quotas (2 active, 24 / day). The API request worker is not blocked; the job runs on the same Fly machine (process isolation, not a separate worker fleet - stated as such, not called distributed) |
| C6 timeout | hard wall clock `timeout_for` = min(`ZAAD_JOB_MAX_SECONDS` 1800, max(30, max_solve_seconds x (10 + services) x 1.5)); the child is terminated and the job recorded TIMEOUT (integration test `test_timeout_terminates_the_worker`) |
| C7 cancellation / cleanup | DELETE cancels (queued -> CANCELLED, running -> terminate + CANCELLED); the report is written only at completion, so a failed / cancelled / timed-out job persists no partial recommendation; the child pipe is closed and the process joined; runner faults are recorded FAILED, never hung |
| C8 duplicate submission | no idempotency key: a second identical submission creates a second job with the same `config_hash` and a distinct id; state is not corrupted and the active quota bounds it (release test C8) |
| C9 result persistence | SQLite row per job with request, seed, engine version, timeout, report JSON (the full planner report incl. every candidate's solver status and the recourse block), error; tenant-bound reads |
| C10 approval | the 202 response and the persisted report carry `approval_required: true`, `executable_purchase_order: false`; nothing executes |

Production: `ZAAD_JOB_STORE` is a deployed Fly secret (v18 and earlier), the job store lives on the
mounted volume; no configuration change needed for P4.

**Decision.** The existing jobs system satisfies C1-C10 for the P4 batch envelope; no new queue
platform, no cap increase. **Result: PASS (no correction).** The shared-supplier-order recourse
class remains batch-only (interactive 413) and the batch cap stays 16 tree worlds.

## Blocker D — P3 historical exactness wording

Two different comparisons exist and both are preserved:

* **P3 performance-closure comparison** (`61a3e75` against `p3_corrective`, historical record):
  **2,273 / 2,304 identical + 31 proven objective-flat C6 transfer ties**
  (`evidence/p3/perf_closure/P3_PRODUCTION_PERF_AFTER.md`). Not rewritten.
* **P4-disabled regression against the current P3 baseline** (`p3_perf_closure` = the production
  runtime `61a3e75`): 2,304 / 2,304 identical.

`P4_FROZEN_REGRESSION.md` and `P4_CLOSEOUT.md` now state the distinction explicitly; no P4 document
implies that P3 "has always been 2,304 / 2,304". **Result: PASS (wording corrected).**

## Lint debt found at the audit

The frozen closeout reported ruff (CI scope) clean; on `d8cdad5` the CI invocation
(`ruff check . --extend-exclude "docs,dashboard,scripts/p1_*.py"`, ruff 0.15.12) reports 13 findings
in `scripts/p4_benchmark.py`, `scripts/p4_invariants.py` and `tests/unit/test_zaad_recourse.py`
(E731 lambda assignments, E701 one-line conditionals). Fixed mechanically on the release branch
(no semantic change); recorded here because the frozen statement was inaccurate.

## Runtime differences between `d8cdad5` and the release candidate

Every runtime file difference is one of the two blocker corrections above or the lint fix:
`zaad/recourse/information.py` (exact lookup, `_distance` removed), `zaad/recourse/policy.py`
(`assess`, `attach_fallback`, `resolve_nodes`, fallback in `world_plan`, REPLAN_REQUIRED in
`lookup_exactness`), `zaad/recourse/explain.py` (status-dependent PI fields, replan fields),
`zaad/full/planner.py` (uses `assess` / `attach_fallback`; `policy_lookup` telemetry in
`evaluate`), scripts `p4_benchmark` / `p4_invariants` / `p4_adversarial` / `p4_profile` (semantics of
the evidence, a sector class in the matrix, lint), `scripts/p1_p0_arms.py` (release arms), tests.
The frozen model builder `zaad/full/model.py`, the contracts, the API router, the migration and the
workspace adapters are byte-identical to `d8cdad5`.

## Release-candidate results (local, before CI)

| gate | result |
|---|---|
| P4 fixtures (`benchmarks/p4_release.*`) | 28 / 28; costs identical to the frozen record; S1's PI recorded NON_CERTIFIED (feasible, not certified) and passing on adaptive <= static |
| P4 invariants (`P4_INVARIANTS.md`) | 27 / 27 (invariant 23 over 25 certified PI solves; S1 listed, not compared) |
| P4 adversarial (`P4_ADVERSARIAL.md`) | 25 / 25 (outside-support history selects no branch; no bound claim unless certified) |
| P4 release tests (`tests/unit/test_zaad_recourse_release.py`) | 15 (A1-A5, A7, B1-B7, C8, probability sums, delayed information) + 12 existing P4 tests |
| performance matrix (`P4_PERFORMANCE.md`) | 30 cells (5 classes); interactive classes at <= 8 worlds 0.6 - 2.4 s planner wall (single SKU, P2, two-source P3); PRODUCE 10 - 58 s at 8 worlds; shared-order class 24 - 192 s (batch-only with recourse) |
| P3 shared-MOV production snapshot, P4 disabled | 12.19 s local (frozen P4 run 12.02 s, P3 closure 12.8 s), 18 HiGHS calls, identical candidate objectives, decision view identical with timing fields stripped, no recourse block |
| P1 canonical B / T / Q / A + P0 cell 15 | identical True on every fixture, CANONICAL REGRESSION PASS; P1 invariants 60 passing / 0 failures |
| P2 | 20 / 20 fixtures, 18 / 18 principles, INVARIANTS PASS, 1,720 / 1,720 reviews identical vs `p2_perf_closure` |
| sector | 26 / 26 fixtures, 19 / 19 invariants, ZAAD reviews 416 / 416 identical vs `sector_perf_closure` |
| P3 (P4-disabled, current baseline) | 30 / 30 fixtures (480 reviews p50 0.63 s / p95 17.1 s / max 40.7 s, 0 time-limited), 34 / 34 invariants, 23 / 23 adversarial, 2,304 / 2,304 identical vs `p3_perf_closure`; historical closure record 2,273 / 2,304 + 31 ties preserved separately |
| P0 six-cell arm `p4_release` vs `router_cycle` | 120 / 120 decision-identical in one pass (15 / 16 / 20 / 21 / 90 / 108: 12, 12, 20, 20, 26, 30); no rerun needed |
| migration 019 | fresh schema: table present, migration re-applied idempotently; populated pre-019 vault (17 staging tables, 474,830 rows): rows preserved, `stg_recourse_spec` empty, nothing attached without a declaration |
| ruff (CI scope) / mypy (CI scope, 136 files) / bandit (CI scope + `zaad/recourse`) | clean |
| full suite | see `P4_RELEASE_CLOSEOUT.md` (run once on the final candidate) |

Logs: `release_gates/`.

