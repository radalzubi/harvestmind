# ZAAD P4 — Adaptive Recourse: release closeout (authoritative)

| item | value |
|---|---|
| P4 base | `ebcd1d0` (P3 performance-closure docs main) |
| P4 local engineering freeze (semantics) | `d8cdad5` = tag `p4-frozen-product` (published to origin at this release, unmoved) |
| P4 local evidence freeze | `7059379` = tag `p4-frozen` (published, unmoved) |
| release base | `main` `b24fd02` (seven documentation files since `ebcd1d0`; no runtime file) |
| release branch | `release/zaad-p4-adaptive-recourse` = `b24fd02` + merge of `7059379` (`0dcab9c`, runtime tree byte-identical to `d8cdad5`) + release-audit corrections `8b42aed` + evidence `0305e6a` |
| tested head (CI once) | `0305e6a`, PR #67, run 34675377987: green on every gate (ruff, gitleaks, security bandit / pip-audit, mypy, docker build, frontend, zaad frozen regression, pytest 4 shards: 362 + 170 + 1,139 + 275 = 1,946 passed, 2 skipped); the two CodeQL analyses fail as on every prior release because code scanning is not enabled on the private repository (environment defect, not a gate) |
| merge | `8c813ac` (merge commit; runtime tree identical to the tested head) |
| production | Fly `zaad-api` release v20 (v19 was built minutes earlier from the long-lived `harvestmind-main` worktree, which carried 207 untracked macOS Finder duplicate files (`* 2.py`, dated 2026-09-11 05:59, not importable) inside the Docker build context; superseded by v20 built from a fresh detached checkout of `8c813ac` with a clean status, same image label; v20 is the release), image `registry.fly.io/zaad-api:canonical-8c813ac (digest sha256:1f9ee687cf6edd6fec14782dcddbd9022185e32faf66f87d720d84aded58f3a5)`, machine `0804e0dfd1e948` (shared-cpu-2x, 2 GB, volume `harvestmind_data`, secrets and env unchanged) |
| release tag | `p4-release-runtime` -> `8c813ac` |
| previous production runtime | `61a3e75` (`p3-performance-closure-runtime`, Fly v18) |

**P4 local engineering freeze vs. P4 release runtime.** The freeze `d8cdad5` is the semantics
built and validated locally. The release runtime differs from it only by the release-audit
corrections recorded in `P4_RELEASE_AUDIT.md`: certified perfect-information semantics (blocker A),
exact information-set lookup with the declared static fallback instead of nearest routing (blocker
B), verdict wording for non-comparable / time-limited cases, evidence-script semantics, a PRODUCE
class in the performance matrix, P0 release arms, lint fixes and the release tests. The frozen model
builder (`zaad/full/model.py`), contracts, API router, migration 019 and workspace adapters are
byte-identical to `d8cdad5`.

## Blocker outcomes

| blocker | finding | correction | evidence | result |
|---|---|---|---|---|
| A PI semantics | the PI primal incumbent was used in the ordering check and labelled "lower bound" regardless of solver status; a time-limited PI (S1) and a time-limited adaptive solve (shared-order class, 2 epochs) produced "ordering check failed" | `policy.assess`: PI CERTIFIED only when OPTIMAL, else `perfect_information_feasible_cost` + NON_CERTIFIED, excluded from ordering, never a bound; solver dual bound reported apart in solver-objective units; verdicts distinguish no-comparator and time-limited-adaptive from a certified ordering failure | `P4_RELEASE_AUDIT.md` A; tests A1-A5, A7; invariant 23 on certified solves; fixture table marks non-certified PI | PASS (corrected) |
| B unseen info-set fallback | `information.lookup` routed a world with no exact signature to the nearest set; used by planner settlement of confirmation worlds (and second-epoch selection worlds) | nearest routing removed (`_distance` deleted); exact match or REPLAN_REQUIRED; the static commitments attached to the adaptive solution are the declared fallback; report exposes `replan_required` and `unseen_observation_rule` | `P4_RELEASE_AUDIT.md` B; tests B1-B7; adversarial lookup case | PASS (corrected) |
| C jobs safety | audited auth, tenant binding, validation, 16-world cap, spawned-process isolation (same machine), hard wall clock, cancel / timeout cleanup, duplicate submission, persistence, approval | none required; scope unchanged (shared-order recourse batch-only, cap 16) | `P4_RELEASE_AUDIT.md` C table; integration jobs tests; release test C8; production smokes N, R | PASS |
| D P3 historical wording | P4 docs stated only "2,304 / 2,304" for the P3 review identity | both comparisons stated: historical performance-closure record 2,273 / 2,304 + 31 proven objective-flat C6 ties (unchanged) vs the P4-disabled regression against the current baseline 2,304 / 2,304 | `P4_FROZEN_REGRESSION.md`, `P4_CLOSEOUT.md`, this document | PASS (wording corrected) |

## Release gates on the tested head

| gate | result |
|---|---|
| P4 fixtures / invariants / adversarial | 28 / 28, 27 / 27, 25 / 25 (`benchmarks/p4_release.*`, `P4_INVARIANTS.md`, `P4_ADVERSARIAL.md`) |
| P4 tests | 15 release-audit tests + 12 P4 tests + P3 structural tests green |
| performance matrix | 30 cells, 5 classes (`P4_PERFORMANCE.md`); interactive rule tree worlds <= 8 and not the shared-supplier-order class; batch cap 16 |
| P3 shared-MOV snapshot (P4 disabled) | 12.19 s local, decision identical, no recourse block |
| P0 | six-cell arm `p4_release` 120 / 120 decision-identical in one pass |
| P1 | canonical B / T / Q / A identity PASS; 60 invariants, 0 failures |
| P2 | 20 / 20, 18 / 18, 1,720 / 1,720 identical |
| sector | 26 / 26, 19 / 19, 416 / 416 identical |
| P3 (current baseline, P4 disabled) | 30 / 30, 34 / 34, 23 / 23, 2,304 / 2,304 identical (historical record 2,273 / 2,304 + 31 ties preserved) |
| full suite (once, final candidate) | 1,946 passed, 2 skipped, 0 failed (5 m 33 s local; `release_gates/pytest_full.summary.log`) |
| ruff / mypy / bandit / pip-audit / gitleaks / Docker build / frontend | local ruff (CI scope), mypy (136 files), bandit clean; the rest on CI run 34675377987 |
| migration 019 | fresh schema idempotent; populated pre-019 vault: 17 staging tables, 474,830 rows preserved, nothing attached without a declaration |

## Production smokes (Fly v20 (v19 was built minutes earlier from the long-lived `harvestmind-main` worktree, which carried 207 untracked macOS Finder duplicate files (`* 2.py`, dated 2026-09-11 05:59, not importable) inside the Docker build context; superseded by v20 built from a fresh detached checkout of `8c813ac` with a clean status, same image label; v20 is the release), `registry.fly.io/zaad-api:canonical-8c813ac (digest sha256:1f9ee687cf6edd6fec14782dcddbd9022185e32faf66f87d720d84aded58f3a5)`)

All against Fly `zaad-api` v20 (`registry.fly.io/zaad-api:canonical-8c813ac`, digest `sha256:1f9ee687...58f3a5`) on synthetic self-serve workspaces; payloads and raw results under `release/` (`smoke_results.json`, `smoke_mn_results.json`, `smoke_q_results.json`).

| case | request | expected | result |
|---|---|---|---|
| A legacy / P4 absent | D1 base without a `recourse` key | 200, no recourse block | 200 in 1.8 s, `RETAIN_INCUMBENT`, no `recourse` block, approval true, no executable PO |
| B `enabled: false` | same with a disabled block | 200, no recourse block | 200 in 1.8 s, identical decision to A, no `recourse` block |
| C simple COMMERCIAL adaptive | D1 (tree 6, epoch 3) | 200 | 200 in 3.2 s; PI CERTIFIED; ordering true; NA pass; value 5.0 -> NO MATERIAL ADAPTIVE BENEFIT; replan 3 / 6 evaluation worlds (confirmation worlds) under the static commitments |
| D PRODUCE adaptive | S2 (FEFO / sellable life) | 200 | 200 in 75.8 s (host steal, see performance); PI CERTIFIED; ordering true; NA pass; adaptive material but NOT SELECTED (a static candidate passed the gates at lower settled cost); approval true |
| E MEAT_SEAFOOD adaptive | S3 (chilled) | 200 | 200 in 2.8 s; PI CERTIFIED; NO MATERIAL ADAPTIVE BENEFIT |
| F P2 + P4 network | I2 with 4 scenarios (tree 8), transfer-only actions | 200 | 200 in 3.7 s; sets 4; PI CERTIFIED; NO MATERIAL ADAPTIVE BENEFIT |
| G P3 + P4 source mix | I3 | 200 | 200 in 3.2 s; PI CERTIFIED; NO MATERIAL ADAPTIVE BENEFIT |
| H correlated risk + P4 | I7 plant group | 200 | 200 in 77.4 s (host steal); sets 2 (plant observed once); PI CERTIFIED; NO MATERIAL ADAPTIVE BENEFIT |
| I waiting-value example | W1 | 200 | 200 in 15.4 s; PI CERTIFIED; ordering true; on the production draw value 6.9 -> NO MATERIAL ADAPTIVE BENEFIT (the fixture's 8.7 % is on its pre-registered branches; production plans on the request's own draw) |
| J malformed epoch | review period = horizon | 422 | 422 "every review period must lie inside the horizon" |
| K unsupported observable | `weather` | 422 | 422 "Input should be 'demand' or 'receipts'" |
| L interactive world count too high | 4 scenarios x 3 continuations = 12 | 413 | 413 "Interactive recourse bounds exceeded ... (scenario-tree worlds 12); submit the request to /api/zaad/network/jobs" |
| M shared-supplier-order interactive | C6 with recourse, budget 12 s | 413 | 413 "Adaptive recourse on a supplier order shared across SKUs is batch-only in this version" (with a 15 s budget the aggregate-solver-time 422 fires first; both fail before any model) |
| N same request through `/jobs` | C6 with recourse, 6 tree worlds | correct safe behaviour | 202 (`timeout_s` 252, approval true, no executable PO); another tenant reads it as 404; job finished **TIMEOUT** after the 252 s wall clock, no partial report persisted, error recorded; the API answered every `/health` probe during the job (18 probes, max 0.4 s). Cause: host steal 6.05x (steal 27,821 vs user 4,506 + system 92 jiffies over 269 s; locally this planner run is 33 s). See performance and the release decision below |
| O PI diagnostic | every adaptive case | never a recommendation | `perfect_information_scope` "... never a recommendation" on every block; PI never a candidate |
| P approval | every 200 | approval true, no executable PO | true / false on every report and every recourse block |
| Q old workspace / no declaration | workspace loaded with the FMCG sample (427,995 rows), no `stg_recourse_spec` row; `plan/from-workspace` with `recourse=false` and `recourse=true` | unchanged | both 200 (97 s / 88 s); `recourse=true` attaches nothing (request `recourse: null`); reports identical with timing / hash stripped; no recourse block |
| R auth / tenant isolation | payload `operator_id` of another tenant; unauthenticated `/jobs`; other tenant's job | 403 / 401 / 404 | 403 / 401 / 404 |
| S CORS / frontend health | preflight from the app origin; `/health` | 200 | 200 / 200 |

**Release decision on N.** The asynchronous path behaves safely (bounded wall clock, TIMEOUT recorded, no partial recommendation, tenant-bound, approval preserved, API responsive) but the shared-supplier-order recourse class did not complete on the shared-cpu-2x machine under the observed steal. Scope statement for this release: shared-supplier-order recourse above interactive complexity is accepted asynchronously and is not guaranteed to complete on the current machine class; that is an infrastructure (machine-class) residual, the same class as the P3 performance-closure residual, not a formulation problem (33 s locally, 45 s of user CPU on the host). No code change; the batch cap stays 16; the interactive rule already excludes the class.

## Production log review

`release/fly_logs_after_smoke.txt` and `release/fly_logs_final.txt` (06:56 - 07:20 UTC, the deploy and every smoke): no 5xx, no traceback, no OOM / kill, no serialization error, no timeout cascade; status histogram over the two overlapping captures 200 x 147, 202 x 2, 401 x 2, 403 x 2, 404 x 2, 413 x 2, 422 x 10 (the expected refusals; the overlap 07:05 - 07:06 counts a few lines twice). One health-check failure at 06:56:54, one second after machine start and before the application finished starting (06:57:15 startup complete, first `/health` 200 immediately after): boot grace, not a runtime fault. Every subsequent health check 200, including throughout the timed-out job.

## Production performance

| case | production wall | local reference | note |
|---|---|---|---|
| simple P4 (C, tree 6) | 3.2 s | 0.7 s planner | interactive |
| P2 + P4 (F, tree 8) | 3.7 s | 1.0 s | interactive |
| P3 + P4 (G, tree 6) | 3.2 s | 0.8 s | interactive |
| PRODUCE + P4 (D, tree 6) | 75.8 s | 39 s | interactive; under host steal; well inside the 180 s interactive stop condition |
| correlated + P4 (H, tree 6) | 77.4 s | 17 s | interactive; under host steal |
| shared-order job (N, tree 6) | TIMEOUT at 252 s | 33 s | asynchronous; steal ratio 6.05 measured from `/proc/stat` across the job; formulation cost unchanged |

Host steal on the machine since boot: 44,039 steal vs 17,452 user jiffies at the end of the first smoke window (2.5x), 6.05x during the job. Infrastructure contention is recorded separately from formulation cost; no interactive class declared supported exceeded 180 s.

## Deferred (unchanged from the local closeout)

Cancellation with a declared penalty; external signals as observables; adaptive protection
quantiles as a distinct action; trees beyond 16 worlds; a tree whose evaluation worlds are leaves
(two-epoch evaluation currently falls back to the static commitments at the second epoch);
persistence of policies beyond the declaration; live review triggers (approval stays with the
operator); idempotent job submission.

## Untouched

Validation7, Validation8, holdout4 (unrun, unread); P5-P10; Network Twin #39; dashboard and website
uplift; global performance refactor; real operator pilot; security-hardening phase; deletions.

## Validation status

ENGINEERING VALIDATED. NOT REAL-DATA VALIDATED. Value of adaptation is a diagnostic on synthetic
fixtures (W1: commit, observe, adapt; the 8.7 % is engineering evidence, not savings).

## Verdict

Blockers A-D PASS (A, B and D corrected narrowly; C verified), main reconciliation docs-only, runtime tree of the tested head identical to the merge, every frozen regression green, CI green once on the exact candidate, migration safe, production smokes A-S as recorded (N safe with an infrastructure residual), no unexplained 5xx, historical tags immutable, `p4-release-runtime` = `8c813ac`.

**ZAAD P4 ADAPTIVE RECOURSE — RELEASED AND CLOSED.** P4 release line fully closed. Validation status: ENGINEERING VALIDATED, NOT REAL-DATA VALIDATED. Next authorized phase: P5 — ATP / scarce-supply allocation (not started).
