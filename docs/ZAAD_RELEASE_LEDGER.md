# ZAAD release ledger

Source of truth for what is frozen, where it lives, and what may move next. First written 2026-09-10
after the P1 freeze; updated the same day at the end of the canonical integration pass. Update this
file whenever a freeze, a push, a merge or a Vercel change happens.

## Frozen milestones (immutable)

| layer | verdict | SHA | tag (local) |
|---|---|---|---|
| P0 solver completeness / recovery | SOLVER COMPLETENESS / RECOVERY LOGIC — PASS AND FROZEN | `2e30721` | `p0-frozen` |
| P1 product code | P1 CYCLE-STOCK / PURCHASING ECONOMICS — PASS AND FROZEN | `f7e1e62` | `p1-frozen-product` |
| P1 final freeze (evidence) | same verdict; the P1 freeze point | `12db66c` | `p1-frozen` |
| post-freeze consolidation / documentation state | not a freeze | `56e998f` | `pre-canonical-integration` |

`12db66c` is the P1 frozen milestone; `56e998f` is the post-freeze documentation state (it adds only the
three consolidation documents). Neither is relabelled by the integration.

## Canonical branch

`zaad/canonical`, created from `56e998f` (the frozen P1 lineage plus the consolidation documents) and
carrying the integration in logical commits:

| commit | content |
|---|---|
| `28d9839` | merge of the site lineage `origin/adaptive/decision-engine` (`c941c64`): the twelve web commits Vercel serves (#22, #29, #34); clean merge, no python change |
| `0fbd8ee` | merge of `origin/main` (`865b701`): Project B synthetic generator (identical to the lineage's own copy), the workspace / agent documents (#15), the #26 / #27 net-zero pair; the 21 web conflicts of #28 resolved to the site lineage |
| `073d702` | the customer-data path (`zaad/full/workspace.py`), the canonical workspace endpoints, the legacy-planner gate, the purchase-plan page on the canonical engine, tests and smoke |
| `3263aff` | typed debt of the decision core (no behaviour change) and JSON-safe shortfall fields |
| `d7f76cf` | canonical CI gates, the fast frozen regression, security and hygiene closure, ESLint |
| closeout commit (this file) | source-of-truth documents |

Frozen optimizer tree: `zaad/full` at `12db66c` has tree hash `7cd0f5ab`; the two merges left it
byte-identical; `073d702` adds `workspace.py` beside it; `3263aff` changes annotations, three local
names and the report's representation of an infinite shortfall (None), with the identity evidence
below. Optimizer behaviour is frozen and verified, not assumed.

## Integrity evidence after integration

* `scripts/zaad_canonical_regression.py`: B, T, Q, A twelve-review rolling replays (seed 41001)
  reproduce the first twelve reviews of the freeze record `closure/horizon52_cycle.jsonl.gz` order for
  order and status for status; P0 cell 15 reproduces the isolation arm `closure/p0_arm_router_cycle.json`
  review by review (state, candidate sets, selection, status, recovery mode, feasibility, chosen plan,
  final P0 purchases), every review protection-owned. PASS at `d7f76cf`.
* B alone on the freeze benchmark after the typing edits: costs and orders bit-identical to
  `closure/horizon52_cycle_B.jsonl.gz` (`closure/identity_typing.jsonl.gz`).
* P1 invariants: 720 / 720, byte-identical checks to the freeze record.
* Python suite on the canonical tree: 1,810 passed, 2 skipped (1,532 unit at the freeze plus the
  integration suites and 12 new tests); 71 P1 principle tests pass.

## Lineages (git ancestry, `origin` fetched 2026-09-10)

Common base `11f06e9` on `main`. Optimizer lineage: `main@11f06e9` -> #16 -> #17 -> #18 -> #19
(`adaptive/decision-engine@2820a69`) -> #20 -> #21 -> #23 -> #24 -> #25 -> #30 -> #31 -> #32 -> #33 ->
#35 -> #36 -> #37 -> #38 (`e8e2398`) -> P0 `2e30721` (+9 local) -> P1 `12db66c` (+26 local) -> `56e998f`;
every step contains its parent completely. Site lineage: `adaptive/decision-engine@c941c64` =
`2820a69` + 12 web commits (Vercel production per `81f141e` and the session record). `main`: five
commits (#14, #15, #26, #27, #28). Network Twin: `adaptive` + 3 web commits (PR #39). The canonical
branch now contains all three lineages; PR #39 is not merged.

## Integrated product surfaces

* API (`api/main.py`, title "Zaad Supply API", health service `zaad-api`): canonical planning engine
  = the frozen P1 optimizer under `/api/zaad/network` (`/plan`, `/shadow`, `/jobs`, and the workspace
  path `/request/from-workspace`, `/plan/from-workspace`); `/fmcg/plan` defaults to `mode=canonical`
  and serves the purchase-plan page from the same engine. Superseded engines (the first ZAAD engine
  under `/api/zaad`, the safe-selector modes of `/fmcg/plan`) are served only while legacy planners
  are enabled: dev by default, off in pilot / staging / prod unless `ZAAD_LEGACY_PLANNERS=1` (410 with
  the canonical pointer). No autonomous purchase order anywhere; approval stays with the operator.
* Customer-data path: operator files -> `api/routers/intake.py` (validated upload into the operator's
  own DuckDB vault, `stg_fmcg_*`) -> `zaad/full/workspace.py` (weekly normalisation, fitted supplier
  fill and lead with sample sizes and provenance, shipment observations, opening stock, open orders,
  promotions, pack structure and order-level economics) -> `zaad.full.contracts.Request` -> the frozen
  planner -> the purchase-plan rows. Verified on a synthetic, schema-realistic workspace: 192k raw rows
  become a 61 KB request for three SKUs (156 demand observations, 180 shipment observations, six open
  orders); 428k rows for the 150-SKU distributor. No raw table reaches the MILP.
* Web (`web/`): the site lineage (SEO, /how-it-works, homepage), the workspace (upload, data quality,
  purchase plan on the canonical engine, state, reports), the network workspace at `/zaad/network`;
  the first engine's page redirects and is kept at `/zaad/legacy`. Public surfaces say ZAAD.

## CI (workflow `.github/workflows/ci.yml` at `d7f76cf`; local run of every gate)

| gate | status on the canonical tree |
|---|---|
| pytest (unit + integration) | 1,810 passed, 2 skipped |
| ruff, canonical scope (all but `docs/`, `dashboard/`, `scripts/p1_*.py`) | clean |
| mypy (`optimization risk backtesting api ingestion domain adaptive zaad/full`) | clean, 135 files |
| bandit `-ll` on the canonical packages | 0 medium, 0 high |
| pip-audit | clean after refreshing urllib3, weasyprint (pin raised to 70.0 for CVE-2026-55073) and tornado locally; the ignore of PYSEC-2026-3412 remains documented |
| secret scan | gitleaks job added to CI; local bounded regex scan clean; `.env` untracked (`test_no_secrets_committed`) |
| zaad frozen regression + invariants + workspace smoke | PASS / 720 / OK |
| frontend typecheck, ESLint, production build, npm audit (prod) | clean / 0 errors, 21 warnings kept visible / builds / 0 vulnerabilities |
| Docker image build and smoke | defined in CI (health, fail-closed, no open legacy planner in prod); not run locally (no Docker on this machine) |

Remaining, documented debt: ruff in `docs/` evidence snippets, `dashboard/` (deprecated HarvestMind
Streamlit shell) and the frozen P1 diagnostic scripts; the 21 ESLint warnings (React 19
set-state-in-effect patterns in the site lineage, one `any`); the pip-audit ignore.

## Deprecated code paths (kept, not served by default)

`zaad/engine.py` and its bounded API `api/routers/zaad.py` (first engine), the safe-selector modes of
`api/routers/fmcg.py`, `optimization/` (HarvestMind-era LP / SP library still imported by the legacy
modes and `adaptive/`), `dashboard/` (Streamlit shell), `api/routers/planning.py` (`/run` deprecated).
Removal is a later step, after the legacy modes have no consumer (`docs/ZAAD_REPOSITORY_CONSOLIDATION_PLAN.md`).

## PR dispositions

| PR | disposition | safe to close after the canonical PR merges? |
|---|---|---|
| #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #33, #35, #36, #37 | SUPERSEDED (content contained in the canonical branch by ancestry) | yes |
| #32 holdout3 | HISTORICAL NEGATIVE RESULT / EVIDENCE ONLY (holdout failed; evidence contained) | yes, with a closing note pointing at the evidence |
| #38 V8 industry standard | SUPERSEDED (origin at `e8e2398`, nine commits behind the P0 freeze) | yes, after the push carries `2e30721` |
| #19 adaptive decision engine (site, Vercel production) | CANONICAL SITE SOURCE until Vercel is repointed; content merged | after Vercel tracks `main` or `zaad/canonical` |
| #39 Network Twin V1 | DEFERRED, untouched | no |

Dispositions executed 2026-09-10 after the merge of #40 (see "Release line closed"): the listed PRs are closed, no branch was deleted.

## Untouched

Validation7 and Validation8 (not present as directories), `docs/zaad_full/evidence/v4/holdout4` (frozen,
unrun), PR #39 / `claude/zaad-network-twin-v1`, Vercel, every other worktree. P2 NOT STARTED.


## Release gate status (2026-09-10, end of the release-engineering pass)

* Preflight at `3bbb07c`: branch `zaad/canonical`, clean tree, `12db66c` and `2e30721` ancestors;
  frozen regression re-run PASS (B, T, Q, A twelve-review identity; P0 cell 15 identity).
* Remote: `origin` has no `zaad/canonical`, no tags, and `claude/zaad-industry-standard-v8` at
  `e8e2398` (nine commits behind the P0 freeze); `main` at `865b701`, fully contained in the canonical
  branch (176 commits ahead, 0 behind). The token has push and workflow scope; branch protection is not
  available on the private plan.
* **Push authorization was not explicit in the session, so nothing was pushed, no PR was opened, no PR
  was closed, Vercel was not touched.** The exact commands are in
  `docs/ZAAD_POST_P1_INTEGRATION_CHECKLIST.md`; the PR body is `docs/ZAAD_CANONICAL_PR.md`.
* Every open PR head except #39 is an ancestor of `zaad/canonical` (re-verified).


## Remote release gate (2026-09-10, authorized pass)

Pushed and verified on origin: `claude/zaad-industry-standard-v8` -> `2e30721`, `claude/zaad-cycle-stock-p1`
-> `56e998f`, tags `p0-frozen`=`2e30721`, `p1-frozen-product`=`f7e1e62`, `p1-frozen`=`12db66c`,
`pre-canonical-integration`=`56e998f`, and `zaad/canonical`. Canonical PR: **#40**
(https://github.com/radalzubi/harvestmind/pull/40), `zaad/canonical` -> `main`, **merged 2026-09-10 11:57 UTC**
(merge commit `f7ff600`, no squash) from head `9a8d266` (= `7cf0431` + this ledger).

Remote CI on PR #40, job by job (the workflow of `.github/workflows/ci.yml`):

| run | head | pytest | ruff | mypy | security | secret scan | frozen regression | docker | frontend |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `653b86c` | cancelled by run 2 | pass | **fail** (highspy 1.15 alias) | pass | **fail** (403: pull-requests read) | **fail** (label variance on cell 15) | **fail** (compose needs the admin-key placeholder; image smoke itself passed) | pass |
| 2 | `1ca2eb9` | cancelled at the 30-min budget (an unbounded 60-SKU plan under coverage) | pass | pass | pass | **fail** (one historical presigned-URL key id) | pass | **pass** | pass |
| 3 | `4bc8c4a` | **fail**: 1,809 passed, 1 failed (`test_no_obvious_secrets_in_tracked_files` on the literal key id in `.gitleaks.toml`) | pass | pass | pass | pass | pass | pass | pass |
| 4 | `7cf0431`, `9a8d266` | not started (billing) | not started | not started | not started | not started | not started | not started | not started |
| 4 rerun ([34462761422](https://github.com/radalzubi/harvestmind/actions/runs/34462761422)) | `9a8d266` | **pass**: 1,810 passed, 2 skipped (36 min) | pass | pass | pass | pass | **pass** | **pass** | pass |

Run 4 (three attempts, and the push-triggered run on the same commit) did not schedule a single job:
GitHub annotated every job "The job was not started because recent account payments have failed or
your spending limit needs to be increased" (private repository; runs 1-3 consumed about 116
job-minutes). The owner restored Actions billing and raised the budget; the rerun of the latest PR
run (`gh run rerun 34462761422`, head `9a8d266`, identical code to `7cf0431`) scheduled every job and
every job passed. The stale "not started" check runs of the push-triggered run on the same commit were
left as they are (the pull-request run is the gate; the merge commit got its own run on `main`).

Docker on GitHub (runs 2 and 3, real evidence): the image builds from a clean checkout, the API imports
and starts, `/health` reports service `zaad-api` with `auth_enforced` true under `HARVESTMIND_ENV=prod`,
anonymous job listing is 401, the legacy demo endpoint is not open, and `compose.pilot.yml` validates.

Fixes made for CI (`1ca2eb9`, `4bc8c4a`, `7cf0431`; none touches optimizer behaviour): the deprecated
highspy status alias read defensively (`zaad/full/model.py`), `highspy>=1.14,<1.16` (decisions
reproduced on 1.14.0 locally and 1.15.1 on GitHub), the P0 anchor of the frozen regression applying the
recorded decision semantics (candidate-label variance under time limits reported, never accepted as a
decision change), `pull-requests: read` for gitleaks, the compose validation placeholder, a bounded
canonical purchase-plan test (`skus`, `max_solve_seconds` on `/fmcg/plan?mode=canonical`), a 45-minute
pytest budget, and the scoped gitleaks allowlist.

Frozen regression on GitHub (highspy 1.15.1, two-core runner): B, T, Q, A identical to the freeze record;
P0 cell 15 identical on state, candidate sets, status, recovery mode, feasible set and final purchases,
with three equal-plan label swaps reported as timeout variance.

CodeQL (`.github/workflows/codeql.yml`, added at `5895f18`, never run on `main`) fails on every run of
this repository at the analyze/upload step with "Resource not accessible by integration": code scanning
is not enabled for this private repository (the repository's security settings are empty and the
code-scanning API answers 403 "Code scanning is not enabled"). ENVIRONMENT DEFECT outside the
repository, not one of the release gates; no permission change can make the upload succeed on this
plan, so the workflow was left untouched. To use it: enable code scanning (GitHub Advanced Security)
or make the repository public, and add `actions: read` to its permissions as the action documents for
private repositories.

## Release line closed (2026-09-10)

* **Merge:** PR #40 merged with a merge commit, `main` = **`f7ff600`** (parents `865b701`, `9a8d266`).
  The tree of `main` is byte-identical to `9a8d266`; `2e30721`, `f7e1e62`, `12db66c`, `56e998f`,
  `3bbb07c` and `9a8d266` are ancestors of `main`; the four tags still point where they were pushed.
* **Post-merge verification:** the push-triggered run on `main`
  ([34474090176](https://github.com/radalzubi/harvestmind/actions/runs/34474090176)) passed every job
  (pytest 1,810 passed / 2 skipped in 36 min; ruff; mypy; bandit + pip-audit "No known vulnerabilities
  found"; gitleaks; frozen regression PASS on highspy 1.15.1 with the three equal-plan label swaps
  reported; Docker image smoke `{'status': 'ok', 'service': 'zaad-api', 'env': 'prod', 'auth_enforced':
  True}` with anonymous jobs 401 and the legacy demo closed, compose validated; frontend typecheck /
  lint 0 errors / build / npm audit 0 vulnerabilities). Locally on the `main` tree: the canonical API and
  workspace tests (12) pass; legacy planners are off outside dev; `/network` is absent (404 on the
  site); Network Twin's head `734fa49` is not an ancestor of `main`.
* **PR closures (executed, branches kept, nothing deleted, `delete_branch_on_merge` false):**
  #16, #17, #18, #20, #21, #23, #24, #25, #30, #31, #33, #35, #36, #37, #38 closed as superseded
  (each head re-verified as an ancestor of `main`); #32 closed with the historical-evidence note
  (holdout3 negative result, evidence only); #19 closed after the Vercel repoint. #39 (Network Twin)
  stays open and deferred. Dependabot opened #41-#51 (GitHub Actions, npm and pip bumps) on the merge;
  they are out of this release's scope and untouched (any solver-stack bump needs the frozen regression
  before acceptance; the ruff / TypeScript / ESLint majors need their own gate runs).
* **Vercel (authorized, done after the post-merge verification):** project `zaad` (team
  `rad-al-zubi-s-projects`, serves `zaadsupply.com`, root `web`) production branch changed from
  `adaptive/decision-engine` to **`main`** (the public project API does not expose the production
  branch, so the change was made in the dashboard: Settings -> Environments -> Production -> Branch
  Tracking); a production deployment of `main` at `f7ff600` was created through the deployments API
  (`dpl_AbNhZqenfZa51PC29C8dkenJja67`, READY, aliases `zaadsupply.com`, `www.zaadsupply.com`,
  `zaad-tau.vercel.app`). Live smoke: `/`, `/how-it-works`, `/overview`, `/upload` 200, `/network` 404.
  The project's only production variable is `NEXT_PUBLIC_API_URL` (unchanged). The API deployment is
  outside Vercel and outside this pass; its required posture is the handoff above (`HARVESTMIND_ENV=prod`,
  `HARVESTMIND_AUTH_REQUIRED=true`, `ZAAD_LEGACY_PLANNERS=0`, explicit CORS origins, admin key, persistent
  data root, positive rate limit). The second Vercel project `harvestmind` already tracked `main`.
* **Verdict:** ZAAD CANONICAL RELEASE LINE — PASS, P2 MAY BE BRANCHED. P2 has not been started; it
  branches from `main` (`f7ff600` or later). Nothing in this pass claims production-ready security.

## Production P0/P1 plumbing (2026-09-10, verified live)

The API deployment is separate from Vercel: Fly app `zaad-api` (`api.zaadsupply.com`, region fra, volume
`harvestmind_data`). After the canonical merge it was still running the 2026-09-05 image (service
`harvestmind-api`, no `/api/zaad/*` route), so the site on `main` could not reach the frozen optimizer.
The owner deployed `registry.fly.io/zaad-api:canonical-11f5459` (release v13) with the persistent
`ZAAD_JOB_STORE` / `ZAAD_SHADOW_LEDGER` paths and `ZAAD_LEGACY_PLANNERS=0` (volume snapshot taken first).

Live verification against `https://api.zaadsupply.com` (production `NEXT_PUBLIC_API_URL` of the Vercel
project `zaad`): `/health` = `zaad-api`, env `pilot`, `auth_enforced` true, rate limit 60; 91 OpenAPI paths
including every `/api/zaad/network/*` route; anonymous `/fmcg/status`, `/api/zaad/network/jobs`,
`request/from-workspace` = 401; `/api/zaad/demo`, `/fmcg/plan?mode=incumbent`, `/api/zaad/plan` = 410
with the canonical pointer; CORS preflight allows `https://zaadsupply.com` and `https://www.zaadsupply.com`
and refuses a foreign origin; the site sends `Authorization: Bearer`. Bounded synthetic smoke on a
self-serve workspace (`op_b9bbe700`, SYNTHETIC CALIBRATED sample, no customer data): `request/from-workspace`
for two SKUs builds `zaad.network.v2` with the leakage guard and fitted provenance (1 s);
`plan/from-workspace` with `max_solve_seconds=5` returns `engine = zaad.full frozen P1`,
`mode_run = canonical_p1`, `planner_owner = PROTECTION_RECOVERY`, `solver_status = RETAIN_INCUMBENT`,
`approval_required = true`, `executable_purchase_order = false` (25 s); `/fmcg/plan?mode=canonical` the
same (36 s). The only frontend callers of the old engine are the explicit `/zaad/legacy` page and the
`(legacy)`-labelled modes of the `/fmcg` selector, which answer 410 in production; no normal route falls
back silently. Fly logs after the deploy: one health-check miss inside the start-up grace, the old
process's cancellation traceback, then "Application startup complete"; no 5xx during the smoke.

**PRODUCTION P0/P1 PLUMBING — VERIFIED.**

## P2 multi-echelon / network optimization (2026-09-10, branch `claude/zaad-meio-p2`, worktree `harvestmind-p2`, parent `11f5459`)

Not merged, not pushed. Evidence in `docs/zaad_full/evidence/p2/` (architecture decision, development
record, pre-registration with its dated correction, authoritative results, invariants, adversarial review,
scalability, P0 / P1 isolation, closeout). The frozen core was found to be one joint network MILP already;
P2 adds the network layer `zaad/meio` (topology, reachability, router, accounting, explanations, network
policies and baselines, fixtures, benchmark, workspace adapter with migration 016, API `network=true`,
interactive bounds) and default-off / telemetry hooks in the frozen files (demand correlation, lane packs
and dispatch fees, incumbent transfers, replay registry, settlement flows, network continuation). Frozen
regression identical throughout; six-cell P0 isolation decision-identical (cell 108 on an idle machine; cell 21 identical to the frozen
code's own replay, its divergence from the record being documented run-to-run variability). Authoritative benchmark: 20 / 20
valid fixtures pass every economic, service and structural gate, 18 / 18 network principles, 20 / 20
invariants, adversarial review clean, full suite 1,838 passed. **Verdict: P2 CORE ARCHITECTURE BUILT —
FREEZE BLOCKED** on one pre-registered gate: the runtime maximum per review (180 s) is exceeded on two of
344 reviews (M 257 s, O 315 s: three candidate classes at the declared per-solve budget with six to eight
worlds); p50 9.7 s and p95 87 s pass. See `P2_CLOSEOUT.md` for the blocker and the decision it needs.

## P2 performance pass (2026-09-10, branch `claude/zaad-meio-p2`, code `cab3849`)

Not merged, not pushed. Evidence in `docs/zaad_full/evidence/p2/perf/` (diagnosis written before any
change, development log, dated corrective plan, re-run results, architecture note, profiles, gate
logs). The original runtime failure stands as recorded (`P2_RESULTS.md`: M 257 s, O 315 s). Profiling
the two failing reviews on their exact snapshots showed 69% of the wall in the warm-start completion
forfeiting its cap and the rest in solves whose first incumbent took 10-31 s, because 95% of the
binaries were FEFO indicators between cohorts that all outlive a 12-period horizon (big-M 1e6). One
exact model change (`zaad/full/model.py`, `FEFO_SYMMETRY_ELIMINATION`: no FEFO indicator between two
cohorts that both outlive the horizon and the latest schedulable transfer arrival; network requests
only, the single-node P1 formulation verbatim) removes 95% of the binaries; every candidate then solves
at the root node with identical objectives. Authoritative set re-run unchanged (`p2_authoritative_perf`):
**p50 0.5 s, p95 6.6 s, max 14.6 s** (gate 60 / 120 / 180), 0 time-limited solves, 20 / 20 fixtures,
18 / 18 principles, 20 / 20 invariants, adversarial clean; P1 B / T / Q / A and the P0 six-cell set
(120 / 120 reviews) decision-identical; full suite 1,843 passed. Every decision difference from the
pre-performance record is a tie broken differently (objective equality proved on the snapshot) or the
one review whose frozen plan was time-limited. **Verdict: P2 MULTI-ECHELON / NETWORK OPTIMIZATION —
PASS AND FROZEN** (see `perf/P2_PERF_RESULTS.md`, `P2_CLOSEOUT.md`; frozen SHA recorded there).

## P2 release line (2026-09-10 / 11, authorized)

* **Preflight**: `claude/zaad-meio-p2` at `fa615ff`, clean; `origin/main` at `11f5459` had not advanced
  except by PR #53 (docs only, the production-plumbing record), merged first as `6d2934e`; the P2
  branch then received one docs-only merge of `main` (`cef7a72`, ledger sections kept side by side).
* **Freeze tags** (published for the first time, verified on origin): `p2-frozen-product` = `cab3849`
  (the frozen P2 runtime / code), `p2-frozen` = `fa615ff` (the complete freeze record with evidence
  and closeout). The local pre-release tag already pointed at `fa615ff`; the product tag was created
  before publication. Ancestry: `2e30721`, `f7e1e62`, `12db66c`, `cab3849` are ancestors of `fa615ff`.
* **PR #54** (`claude/zaad-meio-p2` -> `main`, "ZAAD P2: multi-echelon network optimization, performance
  closure, and freeze"). First CI run 34532888450: every gate green except pytest, cancelled at the
  45-minute job budget at 85% (1,845 tests; a 20-minute stretch inside the integration tests that does
  not reproduce locally on the same scipy 1.18.1 / highspy 1.15.1 stack, where the same files run in
  8 s). Release-only fix `89211b1`: pytest budget 90 minutes and `--durations=30`; no test and no
  optimizer code changed. Second run 34537444878 green on every job: pytest 1,843 passed, 2 skipped
  (71:50 on the runner; slowest tests the two network workspace plans at 1,048 s and 523 s and the
  frozen economic-horizon test at 420 s), ruff, mypy, security, gitleaks, frozen regression, Docker
  build, frontend. CodeQL: the documented "code scanning is not enabled" environment failure, unchanged.
* **Merge**: merge commit `9c4ece7` at 2026-09-10T23:40:25Z (pre-merge `main` `6d2934e`, PR head
  `89211b1`). Every freeze SHA is an ancestor of `main`. Post-merge main CI 34543195400 green
  (pytest 1,843 passed, 2 skipped in 55:45; frozen regression green); local canonical regression on
  `9c4ece7` PASS (B / T / Q / A twelve-review identity, P0 cell 15).
* **Fly**: `zaad-api` release **v14**, image `registry.fly.io/zaad-api:canonical-9c4ece7`, rolling
  update of the existing machine `0804e0dfd1e948` (fra), volume `harvestmind_data` untouched, secrets
  untouched (`ZAAD_LEGACY_PLANNERS=0`, `ZAAD_JOB_STORE`, `ZAAD_SHADOW_LEDGER` persistent). Start-up:
  the old process's cancellation traceback, one health-check miss inside the grace period, then
  "Application startup complete"; no 5xx during the smoke.
* **Bounded production smoke** (`https://api.zaadsupply.com`): `/health` = `zaad-api`, env `pilot`,
  `auth_enforced` true; 11 `/api/zaad/network/*` routes present; `/api/zaad/demo` and `/api/zaad/plan`
  410 with the canonical pointer; anonymous `/fmcg/status`, `/api/zaad/network/jobs`,
  `request/from-workspace` and `/fmcg/plan?mode=incumbent` 401; CORS preflight allows
  `https://zaadsupply.com` and `https://www.zaadsupply.com`, refuses a foreign origin (400). P1 path on
  a fresh self-serve synthetic workspace (`op_47bdde74`, `load-sample-fmcg`, two SKUs):
  `plan/from-workspace` -> `engine = zaad.full frozen P1`, `mode_run = canonical_p1`,
  `planner_owner = PROTECTION_RECOVERY`, `solver_status = RETAIN_INCUMBENT`, `approval_required = true`,
  `executable_purchase_order = false` (23.5 s). P2 path (`op_be0813f3`, payload `/api/zaad/network/plan`,
  one SKU, one central and two branches, two lanes, horizon 12, three worlds, 5 s budget): HTTP 200 in
  1.8 s, `zaad.network.2.0`, state NO_ACTION, owner PURCHASING_ECONOMICS, selected
  `operator_rule:network:rop`, status RETAIN_INCUMBENT, period-zero purchase 39.2 and transfers 68.1 /
  76.5, branch service .990 / .982, economics block, network block with explanations ("no change to
  your current network policy this period"), provenance fingerprint, `approval_required = true`,
  `executable_purchase_order = false`. Oversized payload (15 locations) -> 413 with the interactive
  bounds. One observation outside P2's scope: a whole-workspace `/fmcg/plan?mode=canonical` call without a SKU subset (150 synthetic SKUs) did not return inside a 400 s client window and left no error, traceback or 5xx in the logs (health stayed 200); the interactive canonical route is meant to be called with a SKU subset, as the plumbing smoke did (36 s), and the whole-workspace case belongs to the asynchronous job path.
* **Frontend**: `/`, `/overview`, `/upload`, `/fmcg`, `/state`, `/access` on `https://zaadsupply.com`
  answer 200 before and after the API release (unchanged site; the P2 fields are available on the
  backend for the later dashboard / Network Twin phases).
* **Untouched**: Validation7, Validation8, holdout4 (unrun, unread); Network Twin PR #39 open and
  deferred; Dependabot #41-#51 untouched (no solver-stack bump); sector physics, P3, dashboard and
  website uplift not started.
* **Verdict: ZAAD P2 RELEASE LINE — PASS** (final `main` `9c4ece7`, Fly `zaad-api` v14
  `canonical-9c4ece7`). Next authorized build: Three-Sector Physics Engine (commercial goods,
  produce, meat & seafood) — not started.

## Three-sector physics engine (2026-09-11, branch `claude/zaad-sector-physics`, worktree `harvestmind-sectors`, parent `ea1ed3a`)

Not merged, not pushed, not deployed. Evidence in `docs/zaad_full/evidence/sectors/` (capability audit,
architecture, dated fixture specification, development log, authoritative results, performance record,
invariants, closeout, gate logs). One engine: `zaad/sectors` declares per-SKU operating physics
(COMMERCIAL / PRODUCE / MEAT_SEAFOOD; storage state, age at receipt, minimum remaining life at receipt
and at sale, shipment weight) with provenance, plus optional storage states on locations and lanes;
the frozen model, settlement, continuation, rule projection and report consult one resolved view
behind `physics is not None` (a legacy request resolves to None). Migration 017 (additive), both
workspace adapters, `sector_mode` API parameter, 422 on malformed physics. Authoritative synthetic
run: 26 / 26 pre-registered fixtures (C1-C7, P1-P8, M1-M8, X1-X3) pass; 19 / 19 invariants; runtime
p50 1.4 s / p95 8.4 s / max 59.5 s, 0 time-limited solves. Frozen behaviour: P0 six-cell 120 / 120,
P1 B / T / Q / A identity and 720 / 720 invariants, P2 matrix 20 / 20 with 344 / 344 reviews
decision-identical to the release record. Full suite 1,865 passed, 2 skipped. **Verdict: THREE-SECTOR
PHYSICS ENGINE — PASS AND FROZEN LOCALLY** (product `43d769f`, local tags `sector-physics-frozen-product`
and `sector-physics-frozen`; ENGINEERING VALIDATED, not real-data validated).

## Three-sector physics release line (2026-09-11, authorized)

* **Preflight**: `claude/zaad-sector-physics` at `4f358f7`, clean; `origin/main` still `ea1ed3a` (no
  advancement). Ancestry: `43d769f` in `4f358f7`; every P0 / P1 / P2 freeze SHA in the sector freeze.
* **Freeze tags published exactly** (verified on origin, never moved): `sector-physics-frozen-product`
  = `43d769f`, `sector-physics-frozen` = `4f358f7`.
* **PR #56** ("ZAAD: Three-Sector Physics Engine — commercial, produce, meat & seafood", base
  `ea1ed3a`). First exhaustive run 34573264612: every gate green except pytest, cancelled by the
  runner at the 90-minute job budget at 92% (the same suite is 4:42 locally; the P2 matrix is
  decision-identical under the sector code: runner overhead, not a model regression). CI-only fix
  `be12202`: the identical 1,867 collected tests run as three parallel shards (integration, unit
  without the zaad files, zaad unit files); no timeout widened, no test changed. Run 34580683633
  green on every job: pytest 275 + 1,139 + 451 = **1,865 passed, 2 skipped** (unit-zaad shard 72 min
  on the runner), ruff, mypy, security (bandit, pip-audit), gitleaks, frozen regression, Docker
  build, frontend. CodeQL: the documented "code scanning is not enabled" environment failure.
* **Merge**: `dca3d48` at 2026-09-11T09:59:16Z (pre-merge `main` `ea1ed3a`, head `be12202`). Merged
  tree identical to the tested candidate (`git diff be12202 dca3d48` empty); runtime directories
  identical to the product freeze `43d769f`. Bounded post-merge verification on the exact commit:
  ancestry, API import, migration 017 present, canonical regression PASS, sector and network API
  tests (the three 429s of one combined run were the per-minute recommendation rate limiter across
  files in one process; the file passes 4 / 4 alone). No second full CI (tree identity proven).
* **Fly v15** `canonical-dca3d48` (rolling, machine `0804e0dfd1e948`, volume and secrets untouched,
  `ZAAD_LEGACY_PLANNERS=0`). Production smoke: health, routes, legacy 410, anonymous 401, CORS,
  legacy P1 workspace path (two SKUs, 24 s), commercial / produce / meat & seafood payloads PASS;
  **the mixed-sector payload answered 500**: on the Fly machine a base-stock projection breached
  receiving capacity on a stress world, the candidate gate stored an infinite weighted service
  shortfall and the JSON encoder refused it (reproduced read-only on the machine; not reproducible
  on macOS: a solver tie broke differently). Release fix **PR #57** `3f57284` (`zaad/full/planner.py`:
  the report's weighted-service-shortfall fields carry None where the recovery ranking already did;
  gate decisions read the numeric value before serialisation and are unchanged; regression test).
  CI run 34588333043 green (1,866 passed, 2 skipped); merged as **`5ca3772`** at 11:15:36Z; merged
  tree identical to the tested head; runtime delta against `dca3d48` is that one file.
* **Fly v16** `registry.fly.io/zaad-api:canonical-5ca3772` (rolling, same machine, volume and secrets
  untouched). Smoke on v16: `/health` = `zaad-api`, env `pilot`, auth enforced; 11 network routes;
  `/api/zaad/demo` and `/api/zaad/plan` 410; anonymous protected calls 401; CORS allows zaadsupply.com
  and www, refuses a foreign origin; legacy workspace (`op_0a69199c`, no sector fields) builds
  (`sector_mode` null, no profiles) and plans on the frozen P1 path (`canonical_p1`,
  `approval_required` true, `executable_purchase_order` false, 24 s); the same workspace with
  `sector_mode=COMMERCIAL` carries a physics block with undeclared (neutral) profiles. Payload
  smokes, all HTTP 200, `approval_required` true, `executable_purchase_order` false: COMMERCIAL
  (case pack 12: purchase 48 = 4 x 12 with the operator-language explanation; 31 s), PRODUCE
  (age / sellable life: transfer cohort keeps expiry 4, "arrive with 3 periods of life, 2 of them
  sellable"; 2 s), MEAT_SEAFOOD (chilled, ambient south lane never used, reefer lane declared; 6 s),
  MIXED (commercial A with produce B: profiles isolated, A min life 0 / B min life 1, shared
  branches; 5 s). Malformed inputs 422 with clear messages: unknown sector mode, negative shelf
  life, minimum life above shelf life, invalid storage state, physics for an unknown SKU, declared
  value without provenance. Logs after the v16 start-up: 0 x 5xx, 0 tracebacks from the active
  process, no store / migration / auth errors (one health-check miss inside the grace period).
* **Migration 017**: additive, nullable, idempotent (`ADD COLUMN IF NOT EXISTS`, the pattern since 007);
  applied by the existing mechanism (`setup_db` at vault creation) to every vault created from v15 on;
  existing vaults keep their schema and load through the guarded adapters (legacy-neutral); no
  backfill. To declare physics on a pre-existing vault the operator runs the idempotent
  `scripts.setup_db.setup_db` on that vault's DuckDB file.
* **Frontend**: `/`, `/overview`, `/upload`, `/fmcg`, `/state`, `/access` answer 200 before and after.
* **Known observations (future performance work, not fixed here)**: C1 report-only service-frontier
  oracle up to ~59.5 s; two-SKU P1 workspace request ~24 s end to end on a 5 s solve budget; the
  synchronous 150-SKU whole-workspace canonical call exceeded 400 s (P2 release).
* **Untouched**: Validation7, Validation8, holdout4 (unrun, unread); Network Twin #39; P3-P6;
  dashboard and website uplift; Dependabot solver-stack bumps.
* **Verdict: ZAAD THREE-SECTOR PHYSICS RELEASE LINE — PASS** (final released runtime `5ca3772`, Fly
  `zaad-api` v16 `canonical-5ca3772`; ENGINEERING VALIDATED, not real-data validated). Next
  authorized build: P3 supplier / sourcing portfolio optimization — not started.

## Three-sector physics release bookkeeping (2026-09-11, lineage tags)

Three immutable markers describe the sector phase. They are distinct commits and are never moved.

| tag (on origin) | SHA | meaning |
|---|---|---|
| `sector-physics-frozen-product` | `43d769f` | original sector optimization / runtime semantics freeze, before release smoke |
| `sector-physics-frozen` | `4f358f7` | complete local engineering evidence freeze (fixtures, invariants, benchmark, closeout) |
| `sector-physics-release-runtime` | `5ca3772` | exact runtime deployed to Fly `zaad-api` v16 (`canonical-5ca3772`) after PR #57 |

`43d769f` freezes sector optimization semantics. `5ca3772` is the exact released runtime and contains
one post-freeze JSON-safe reporting correction (PR #57, `zaad/full/planner.py`) that does not alter
optimizer gate decisions: the report's weighted-service-shortfall fields carry None where a
stress-world settlement is physically unusable (the value the recovery ranking already used); the
gate reads the numeric value before serialisation. Evidence for that correction: canonical regression
PASS on the merged commit, the targeted regression test, exhaustive pre-merge CI green on the
identical tree (run 34588333043, 1,866 passed, 2 skipped), production mixed-sector smoke 200 on v16.
`43d769f` is therefore not byte-identical to production; v16 (`5ca3772`) is the authoritative released
runtime. Final `main` `4cc9f52` adds the docs-only release closeout after the released runtime.

Ancestry (verified): `43d769f` -> `4f358f7`; `43d769f` -> `5ca3772` (through `dca3d48`);
`5ca3772` -> `4cc9f52`; `2e30721`, `f7e1e62`, `12db66c`, `cab3849`, `fa615ff`, `9c4ece7` all in
`4cc9f52`. Original tags re-verified on origin at bookkeeping time: `43d769f` / `4f358f7`, unchanged.

GitHub Actions at bookkeeping time: the push runs on `main` for `5ca3772` (34593147827) and `4cc9f52`
(34593818699) and the docs PR #58 run did not start ("recent account payments have failed or your
spending limit needs to be increased"): REMOTE_CI_UNAVAILABLE — GITHUB ACTIONS BILLING. This is a
billing condition, not a code failure; the code line's evidence is the green pre-merge runs on
`be12202` and `3f57284`, whose trees equal the merged commits. Owner action: restore Actions billing
and rerun CI on `main`.

## P3 supplier / sourcing portfolio optimization (2026-09-11, branch `claude/zaad-sourcing-p3`, worktree `harvestmind-p3`, parent `main` `7bc4206`)

* **Audit first** (`evidence/p3/P3_EXISTING_CAPABILITIES.md`): the frozen engine already chooses among approved
  sources jointly (per-source purchase columns, capacity, MOQ, packs, supplier orders across SKUs, payment
  terms through the cash balance, shared resources, per-source fill / lead fitting, shared-domain supply
  shocks). No second optimizer, candidate class, supplier score or diversification rule was built.
* **P3 layer** (`zaad/sourcing`): a default-off `SourcingPortfolio` on the frozen request (risk groups with
  kind, correlation and provenance; declared share limits and committed units; declared switching /
  qualification costs; the operator's incumbent source mix). Hooks reached only when a portfolio is
  declared: model (exact zero-capability pruning, share rows, one first-stage switching binary), worlds
  (group factor from a salted generator, marginals preserved, frozen stream untouched), settlement
  (switching ledger line under ORDERING), rule projections (incumbent mix split, shared-resource fit),
  replay (an executed switch joins the mix), planner `report["sourcing"]` with operator-language reasons;
  approval required, no executable PO. Migration 018 (`stg_fmcg_sources`, four supplier risk columns);
  `sourcing` parameter on the workspace endpoints; interactive bounds (413) and 422 `sourcing_invalid`.
* **Evidence**: 30 / 30 pre-registered fixtures PASS (`p3_authoritative`; changes recorded in the spec and
  dev log), 34 / 34 invariants, 23 / 23 adversarial cases fail safely; runtime 480 reviews p50 0.66 s /
  p95 19.2 s / max 42.8 s, 0 time-limited; P0 six-cell arm `p3_sourcing` 120 / 120 decision-identical;
  canonical regression identical; P1 invariants no failures; P2 matrix under the P3 code 20 / 20, 18 / 18,
  344 / 344 decision-identical; sector matrix 26 / 26, 19 / 19 invariants, 402 / 416 identical with the 14
  differences confined to fixture P3_age_at_receipt: one documented correctness correction in
  physics-enabled historical replay (received perishable purchases keep their declared remaining life;
  live planner / settlement unchanged; legacy replays bit-identical), audited and causally proven in
  `evidence/sectors/corrections/` (2026-09-11 corrective pass); "sector physics remains frozen" is
  withdrawn in favour of that precise statement.
* **Frozen and local only**: product tag `p3-frozen-product`, evidence tag `p3-frozen` (see
  `evidence/p3/P3_CLOSEOUT.md` for the SHAs). Not pushed, not merged, not deployed. ENGINEERING
  VALIDATED, not real-data validated; no savings claimed.

## P3 supplier / sourcing portfolio release line (2026-09-11, authorized)

* **Remote CI prerequisite**: the last known state was REMOTE_CI_UNAVAILABLE (billing); one rerun of the
  main run on `7bc4206` (34605444241) started every job with steps and completed green, so the release
  proceeded.
* **Preflight**: `claude/zaad-sourcing-p3` at `fb91946`, clean; `origin/main` `7bc4206` (no advancement).
  Freeze integrity: `p3-frozen-product` = `9e496ed`, `p3-frozen` = `628d49f`, `p3-corrective-evidence` =
  `fb91946`; `9e496ed` in both; runtime directories identical between `9e496ed` and `fb91946` (the only
  file outside docs / tests is the P0 arm registration in `scripts/p1_p0_arms.py`). Branch and the three
  tags published exactly (verified on origin, never moved); `sector-physics-replay-correction` stays a
  local forensic marker.
* **PR #60** ("ZAAD P3: Supplier / Sourcing Portfolio Optimization", base `7bc4206`). First exhaustive run
  34626589387: every gate green except the unit-zaad pytest shard, cancelled by the runner at the 90-minute
  job budget while the docs-only main rerun competed for runners (the zaad unit files take 224 s locally).
  CI-only fix `326c010`: that shard split into two disjoint name ranges (`[a-r]` 323 tests, `[s-z]` 170
  tests; union = the 493 zaad unit tests exactly); no timeout widened, no test changed. Run 34635732278
  green on every job: pytest 275 + 1,139 + 322 + 170 = **1,906 passed, 2 skipped** (integration 14 min,
  unit-core 6 min, unit-zaad-a 48 min, unit-zaad-b 43 min), ruff, mypy, security (bandit, pip-audit),
  gitleaks, Docker build, frontend, frozen regression. CodeQL: the known "resource not accessible by
  integration" (code scanning not enabled) configuration failure.
* **Merge**: `0de6850` (pre-merge `main` `7bc4206`, head `326c010`, merge commit). Whole-tree diff against
  the tested head empty; runtime directories identical to the product freeze `9e496ed`. Bounded post-merge
  verification on the exact commit: ancestry, API and `zaad.sourcing` import, 33 sourcing / receipt-life
  tests, canonical regression PASS, migration 018 present. No second full CI (tree identity proven).
* **Migration 018**: additive, idempotent (`CREATE TABLE IF NOT EXISTS stg_fmcg_sources`, four
  `ADD COLUMN IF NOT EXISTS` supplier risk columns), no backfill, nothing inferred. Applied by the
  existing mechanism (`setup_db` at vault creation): the smoke vault created on v17 reports the source
  table present; a pre-P3 vault (`op_0a69199c`, inspected read-only on the machine) has no
  `stg_fmcg_sources` and keeps working through the legacy adapter (`sourcing=true` on such a vault warns
  and builds the frozen request). To declare P3 sourcing on a pre-existing vault the operator runs the
  idempotent `scripts.setup_db.setup_db` on that vault's DuckDB file (the API holds the vault lock while
  it serves the tenant; run it with the tenant idle).
* **Fly v17** image label `canonical-0de6850` on the `zaad-api` registry repository (rolling, machine `0804e0dfd1e948`, volume
  `harvestmind_data` untouched, the Fly configuration values left exactly as they were (names only verified), legacy planners still disabled, env `pilot`); health
  checks passing after the grace period, no restart loop.
* **Production smoke on v17** (`evidence/p3/release/production_smoke_v17.json`): `/health` = `zaad-api`,
  pilot, auth enforced; legacy `/api/zaad/demo` and `/api/zaad/plan` 410; anonymous protected calls 401;
  CORS allows zaadsupply.com and www, refuses a foreign origin. Self-serve workspace `op_38e4101e`
  (sample FMCG, 427,995 rows): legacy request has `sourcing` null (`requested` false); with `sourcing=true`
  and no declarations the block stays null and the request stays frozen; the P1 workspace plan runs on the
  canonical path with approval required. Payload smokes (all HTTP 200, `approval_required` true,
  `executable_purchase_order` false, economics reconciled, no unmapped ledger key): legacy no-P3 (no
  sourcing block); single source (allocation = the P1 commitment, share 1.0); two-source economics (B
  cheaper per unit, A cheaper landed after freight and terms: A retained, sentence present); capacity
  split (A at its 200 capacity, B 108, sum = commitment, sentence present); MOQ / MOV (B orders 1,333 >=
  MOQ 1,200 and MOV); packs (120 = 1 x 120-unit pallet); payment terms (declared 50 / 50 retained, not
  material); switching small (B unused: "starting to buy from it would cost 2,000"), switching large (B
  adopted, cost 300 charged once); shares (A at most 70 % and B at least 30 % honoured exactly);
  correlated risk (plant group listed with provenance on A and B, C independent; one source per period,
  no intra-period split); independent identical sources (period-level label ties, never a split within a
  period); PRODUCE (short-life B unused; age by source in the profile); MEAT_SEAFOOD (frozen source into a
  chilled-only destination rejected with the reason); network (P2 transfers 300 at period 0, source split
  P3, conservation exact); multi-SKU shared capacity (S1 lines 158 + 292 = 450 = the shared cap, S2 takes
  the overflow); shared MOV (combined S1 orders 650 + 655 units >= 5,000 MOV); age at receipt payload
  (profile `{src_A: 3}` on shelf life 6: "arrive with 3 of 6 periods of life"). Malformed inputs: unknown
  group member, unqualified source with a minimum share, negative capacity, minimum above maximum share,
  impossible aggregate shares, missing provenance, infinite price all 422; 11 sources on one pair 413
  before any model. Frontend `/`, `/overview`, `/upload`, `/fmcg`, `/state`, `/access` 200.
* **Age-at-receipt workspace check** (`evidence/p3/release/age_at_receipt_workspace_*`): a new produce
  workspace `op_a2b8b9d9` loaded through the intake upload with a SKU master declaring shelf life 42 days,
  age at receipt 21 days and sale minimum 7 days; the production adapter built `sku_physics`
  `age_at_receipt_periods` 3 on a 6-period shelf life (received life 3, not 6) and the plan's physics
  profile carried it; approval required, no executable order.
* **Logs after the smokes**: 0 x 5xx, 0 tracebacks, no store / migration / tenant / serialization error;
  one health-check miss inside the rolling-deploy grace; 59 x 200, 7 x 422, 3 x 401, 2 x 410, 1 x 413,
  1 x 400 (foreign CORS preflight).
* **Release-runtime tag**: `p3-release-runtime` = `0de6850` (on origin; identical runtime tree to
  `9e496ed`).
* **Known observations (future performance work, not fixed here)**: sector C1 frontier oracle ~60 s; the
  two-SKU P1 workspace call ~24 s on a 5 s budget; the synchronous 150-SKU whole-workspace call > 400 s;
  new: interactive P3 payloads with supplier-order MOV binaries across two SKUs run far slower on the Fly
  machine than locally (shared-MOV smoke 218 s, multi-SKU shared capacity 78 s, plant-group case 46 s,
  against 1-20 s locally); async jobs remain the path for such requests.
* **Untouched**: Validation7, Validation8, holdout4 (unrun, unread); Network Twin #39; P4-P6; dashboard
  and website uplift; Dependabot solver-stack bumps.
* **Verdict: ZAAD P3 SUPPLIER / SOURCING PORTFOLIO RELEASE LINE — PASS** (released runtime `0de6850`, Fly
  `zaad-api` v17 `canonical-0de6850`; ENGINEERING VALIDATED, not real-data validated; no savings claimed).
  Next authorized phase: P4 adaptive recourse — not started.

## P3 production performance closure (2026-09-11, branch `perf/p3-shared-mov-closure`, worktree `harvestmind-p3-perf`, parent `main` `1e712c9`)

* **Original release observation (kept, not erased)**: the P3 release smoke's shared-supplier-MOV case
  (`payload.shared_mov`: two SKUs, one supplier with a 5,000 MOV and a 150 fixed order cost, declared line
  capacity 1,000,000) measured **218.4 s** on Fly v17 (`0de6850`) against the declared 180 s interactive bound;
  functionally correct, performance blocked.
* **Exact workload**: snapshotted byte for byte (`evidence/p3/perf_closure/shared_mov_prod_snapshot.json`)
  with the multi-SKU capacity, plant-group, simple P3 and P2 network snapshots and the v17 reference results.
* **Root cause (measured, `P3_SHARED_MOV_PROFILE.md`)**: 96 % of the wall time inside HiGHS across 18 calls
  (12 distinct candidate / valuation models; no first-stage binary duplicated per world; nothing rebuilt
  twice). (1) The supplier-order linking rows used the declared capacity (1,000,000) as big-M, so the
  relaxation never priced the MOV or the fixed cost: base_stock 4.7 s / 1,214 nodes, oracles 84 nodes.
  (2) After the bound is tight, HiGHS's root restart doubles every remaining solve for the same optimum.
  (3) The 218 s itself was the request on a **throttled shared CPU** (guest counters: 518 s steal against
  271 s user time since boot); the exact request rerun on the unthrottled machine took 76.2 s with every
  candidate optimal and the same decision as locally. The frozen `depleted` indicators' big-M, heuristic
  effort, scaling, pricing, cut and LP-age settings were measured and are not drivers.
* **Correction** (`zaad/full/model.py`, PR #64 `5bbdefc` -> merge `61a3e75`): scoped to the P3
  shared-supplier-order class (`shared_supplier_orders`: a sourcing review whose supplier order links lines
  of more than one SKU). Inside it: `activation_bounds` (the exact undominated quantity per line and period
  as the coefficient of the `order` / `active` linking rows; purchase columns keep their capacity; guarded
  by salvage < landed cost, no bound under fixed plans or declared share rows, pack-lattice rounding),
  highspy with `mip_allow_restart` off, and explicit rejection of dominated warm-start seeds. Outside the
  class nothing changes. Two broader scopes were built, measured and withdrawn because they flipped
  tie representatives (equal-cost transfers, identical-price sources) through the selector's confirmation
  gates in E4 / R4 / T (`tie_evidence/`).
* **Exactness**: every candidate on the exact snapshot returns the identical objective, bound and purchase
  plan before and after; only equal-cost transfer allocations move (objective 25,408.1631 both).
* **Before / after**: local 17.55 s -> 12.8 s (solver 17.06 -> 12.3 s; base_stock 4.68 -> 0.15 s; every
  solve at or near one node). Fly: exact snapshot 218.4 s (v17 release smoke, throttled) / 76.2 s (v17 unthrottled rerun) -> **39.4 s** fresh and **37.8 s** after the sustained sequence on v18, every candidate optimal; multi-SKU capacity 77.6 -> 9.5 s; plant group 45.6 -> 14.5 s; simple P3 1.8 s; P2 network 1.6 s.
* **Regression on the final code**: P3 30 / 30, 34 / 34, 23 / 23, 2,273 / 2,304 replay reviews identical
  to `p3_corrective` (the 31 others all C6: one equal-cost transfer tie at review 0 and its cascade,
  review-0 candidates identical on both seeds); P2 20 / 20, 18 / 18, invariants PASS, 1,720 / 1,720
  identical; sector 26 / 26, 19 / 19, ZAAD reviews 416 / 416 identical (the `echelon_base_stock`
  comparator's 19 differing reviews reproduce on the unchanged released code: pre-existing comparator
  variability, recorded); P1 canonical B / T / Q / A identity, invariants 60 / 0; P0 six-cell arm
  `p3_perf_closure` 118 / 120 under contention, quiet rerun of cells 21 and 108 50 / 50 -> 120 / 120.
  New structural test `tests/unit/test_zaad_activation_bounds.py` (no wall clock).
* **Remote CI**: PR #64 run 34657879427 green on every executable job: pytest 275 + 1,139 + 328 + 170 = **1,912 passed, 2 skipped** (the six new structural tests included), ruff, mypy, security (bandit, pip-audit), gitleaks, Docker build, frontend, frozen regression; CodeQL: the known configuration failure only.
* **Merge / tree identity**: PR #64 head `5bbdefc`, pre-merge `main` `1e712c9`, merge commit `61a3e75`; whole-tree diff against the tested head empty, so no second full CI.
* **Deployment**: `fly deploy -a zaad-api --image-label canonical-61a3e75 --strategy rolling --yes` from `harvestmind-main` at `61a3e75`: release v18, machine `0804e0dfd1e948` (fra, shared-cpu-2x, 2 GB), volume `harvestmind_data`, secrets and configuration identical before and after (listed), health `ok`, auth enforced; the deploy log's only traceback is uvicorn's SIGINT shutdown of the previous VM.
* **Production re-run**: exact shared-MOV snapshot **39.4 s** (fresh) and **37.8 s** (after the four other snapshots), candidates incumbent 0.1 / base_stock 0.5 / deterministic 6.8 / stochastic 10.7 / cadence_2 5.5 / cadence_4 3.7 s, all OPTIMAL; same purchase commitment, source split (A 0.991 / 0.009, B 0.990 / 0.010), MOV satisfaction, objective and service as the local run and the v17 unthrottled rerun; `approval_required` true, `executable_purchase_order` false on every response; guest steal over the whole sequence 130 jiffies against 9,924 user (unthrottled numbers). Primary gate < 180 s met with a 4.6x margin; the residual host-throttling risk (12-31x observed at release) is recorded, not hidden.
* **Log review**: 0 x 5xx, 0 request tracebacks, 0 timeouts, 0 OOM, 0 store / serialization errors; 41 x 200 in the window including the six plan calls (`evidence/p3/perf_closure/fly_logs_after_rerun.txt`).
* **Performance-closure tag**: `p3-performance-closure-runtime` -> `61a3e75`; `p3-release-runtime` stays
  on `0de6850` (the original P3 released runtime), never moved.
* **Recorded, not fixed**: the same loose big-M under the P1 shared-order class (fixture T) and the
  single-SKU MOV / MOQ class (E4, S4); the `echelon_base_stock` comparator's run-to-run variability;
  the shared-CPU steal on the production machine (a performance-CPU machine or the async job path remain
  the defences when the host throttles); sector C1 ~60 s, P1 workspace ~24 s, 150-SKU > 400 s unchanged.
* **Untouched**: Validation7, Validation8, holdout4; Network Twin #39; P4-P6; dashboard and website
  uplift; Dependabot solver-stack bumps.
* **Verdict**: **ZAAD P3 PRODUCTION PERFORMANCE CLOSURE — PASS**; P3 release line fully closed (released runtime `0de6850`, performance-closure runtime `61a3e75`, Fly v18); ENGINEERING VALIDATED, not real-data validated; no savings claimed. Next authorized phase: P4 adaptive recourse — not started.

## P4 adaptive recourse release line (2026-09-12, authorized; branch `release/zaad-p4-adaptive-recourse`, worktree `harvestmind-p4rel`, base `main` `b24fd02`)

* Local engineering freeze `d8cdad5` (`p4-frozen-product`) / evidence `7059379` (`p4-frozen`), published unmoved. Main since the P4 base `ebcd1d0`: seven docs files, no runtime file.
* Release audit (`evidence/p4/P4_RELEASE_AUDIT.md`): A PI semantics corrected (bound only when OPTIMAL; time-limited PI = feasible cost, excluded from ordering; solver bound apart; verdicts distinguish no-comparator / time-limited-adaptive), B nearest-signature lookup removed (exact or REPLAN_REQUIRED with the static commitments as declared fallback, reported), C jobs safety verified (no change), D historical P3 wording (2,273 / 2,304 + 31 ties vs 2,304 / 2,304 P4-disabled current baseline) fixed. 13 pre-existing lint findings in the P4 scripts / tests fixed.
* Gates on the candidate: P4 28 / 28, 27 / 27, 25 / 25, 30-cell matrix; P3 snapshot identical 12.2 s; P1 identity + 60 invariants; P2 20 / 20, 18 / 18, 1,720 / 1,720; sector 26 / 26, 19 / 19, 416 / 416; P3 30 / 30, 34 / 34, 23 / 23, 2,304 / 2,304; P0 120 / 120 (one pass); migration 019 audited on fresh and populated pre-019 vaults; full suite 1,946 passed / 2 skipped.
* PR #67, tested head `0305e6a`, CI run 34675377987 green (1,946 passed on 4 shards; CodeQL environment defect unchanged); merged `8c813ac` (tree `e1e1f2d` identical to the tested head, no post-merge rerun).
* Fly `zaad-api` v20 `canonical-8c813ac` (v19 superseded: built from a worktree with stray untracked Finder duplicates; v20 from a clean detached checkout), machine / volume / secrets / env unchanged. Smokes A-S PASS as recorded in `evidence/p4/P4_RELEASE_CLOSEOUT.md`; N (shared-order recourse through `/jobs`) safe but TIMEOUT under 6x host steal (infrastructure residual, scope stated). Logs clean.
* Tag `p4-release-runtime` = `8c813ac`. Historical tags immutable (verified peeled on origin).
* VERDICT: ZAAD P4 ADAPTIVE RECOURSE — RELEASED AND CLOSED. ENGINEERING VALIDATED, NOT REAL-DATA VALIDATED. Next authorized phase: P5 — ATP / scarce-supply allocation (not started).

## P4 production performance closure (2026-09-12, branch `perf/p4-recourse-performance-closure`, worktree `harvestmind-p4-perf`, parent `main` `adf45e4`) — TRACK A of the parallel stage

* Diagnosis before any change (`evidence/p4/perf_closure/P4_PERF_DIAGNOSIS.md`, harness `scripts/p4_perf_profile.py`, 35 cells with HiGHS logs): the heavy cost is the unseeded adaptive tree solve (shared-order 12 worlds: 78 s time-limited incumbent dearer than the static optimum; produce: FEFO indicators, rejected warm completion). One exact change adopted: warm-start the adaptive tree solve from the static comparator (planner + `policy.compare`); rejected: indicator big-M tightening (invalid harness bound on produce; no gain on shared order), PI seeding, decomposition.
* Before / after: shared order 12 worlds 177 -> 138 s (adaptive 39 s OPTIMAL, verdict corrected), 8 worlds 60 -> 55 s, produce 6 / 8 worlds 41 / 60 -> 36 / 54 s, S1 adaptive time-limited -> OPTIMAL 10 s, interactive classes unchanged, 16-world shared order unchanged; no gate changed or recommended.
* Gates: P3 snapshot identical, P1 identity + 60, P2 20 / 20 + 18 / 18 + 1,720 / 1,720, sector 26 / 26 + 19 / 19 + 416 / 416, P3 30 / 30 + 34 / 34 + 23 / 23 + 2,304 / 2,304, P0 120 / 120 (one pass), P4 28 / 28 (objectives identical) + 27 / 27 + 25 / 25, full suite 1,946 / 2.
* PR #69 tested head `a9b2b92`, CI 34696879480 green; merged `6b58764` (tree identical); Fly v21 `canonical-6b58764` from a clean checkout; production benchmark: interactive 3.1 / 3.7 / 3.4 s, produce 67 s (steal 0.02), shared-order job TIMEOUT under 3.2x steal (infrastructure residual unchanged); logs clean; tag `p4-performance-closure-runtime` = `6b58764`, `p4-release-runtime` unmoved.
* VERDICT: ZAAD P4 PRODUCTION PERFORMANCE CLOSURE — PASS.

## P5 ATP / scarce-supply allocation — parallel-phase isolated engineering (2026-09-12, branch `claude/zaad-atp-p5`, worktree `harvestmind-p5`) — TRACK B

* Audit `docs/zaad_full/p5/P5_EXISTING_CAPABILITIES.md`, architecture `P5_ARCHITECTURE.md`, pre-registration `P5_PREREGISTRATION.md` (fixtures A-V, 20 invariants, 16 adversarial), dev log. Isolated package `zaad/atp` (contracts with provenance, ATP ladder, incumbent policies, exact MILP via scipy HiGHS, shared-ledger economics, validation, report, fixtures, adapter), migration 020, `Request.atp` default None (identity proven), endpoint `POST /api/zaad/atp/promise` behind `ZAAD_ATP_ENABLED=1`. Results: 24 / 24 fixtures, 16 / 16 adversarial, 9 tests, ruff / mypy / bandit clean. Commits `f9d0251` -> rebased `ae7001a` + `149fb5f` on the TRACK A main; no shared-core file touched; not pushed, not frozen, not released. Next: shared-core integration (separate authorization).

## P5 ATP / scarce-supply allocation — shared-core integration engineered (2026-09-12, branch `claude/zaad-atp-p5`), NOT released

* Isolated baseline tag `p5-isolated-baseline` = `660e5fc` (pushed; re-run from that SHA clean). Integration on top: `P5_INTEGRATION.md` (state contract: envelope, P0 overlay not a reservation, firm / non-firm inbound, direct vs alternative ship-from, PROPOSED reservations; ledger audit with owners, no double charge), planner hook after the frozen report (`zaad/full/planner.py`), workspace flag (`atp=True`, migration 020 adapter), API gate (`ZAAD_ATP_ENABLED`; 422 `atp_disabled` / 413 / 403). Evidence `docs/zaad_full/evidence/p5/integration/`: I01-I20 20 / 20 (I20 identical to the pre-P5 runtime `6b58764`), isolated 24 / 24, adversarial 17 / 17, invariants, profile, frozen regression gates, migration and API audits. `zaad/full/model.py`, P3 rows, P4 node indexing, scenario draws, tolerances, holdouts, historical tags: untouched. Next: P5 release audit under its own authorization; no deployment.

## P5 ATP / scarce-supply allocation — release audit (2026-09-12, branch `release/p5-atp-release-audit` from `17d2d74`)

* Economics: lost-sale basis corrected to the lost contribution (`selling_price - asset_value`, the frozen model's allocation-ranking basis; declared line / class margins override; gross selling price reported as information; ledger key `lost_contribution`) - a P5 semantic correction, no verdict changed on the 24 + 20 matrices, R01-R03 pre-registered and passing. SLA / class shortage penalty: distinct terms with a fail-closed `shortage_penalty_basis` (ADDITIONAL_TO_SERVICE_SLA with a reference and CONTRACT / OPERATOR_DECLARED provenance, or REPLACES_SERVICE_SLA), migration 021. P4 plumbing: `plan/from-workspace` forwards every phase flag by keyword. Evidence `docs/zaad_full/evidence/p5/release_audit/` (R01-R18 18 / 18 with runs 1-2 preserved, matrices, adversarial 18 / 18, profile, migration and API audits, frozen chain). Release: PR #72 merged as `main` `2fc7b50` (tested head `e33e027`, tree-identical; product freeze `p5-frozen-product` = `eacf3c3`, evidence freeze `p5-frozen` = `6919379`), Fly `zaad-api` v22 `canonical-2fc7b50` from a clean detached checkout, production smoke and logs clean, tag **`p5-release-runtime`** = `2fc7b50`. ZAAD P5 RELEASE AUDIT — PASS. Next authorized phase: none started (P6 not started).

## P4B V1 open PO / commitment intervention — IMPLEMENTED (2026-09-13, branch `claude/zaad-commitments-p4b` from `5dc87b4`), NOT released

* Design gate PR #74 (BUILD, V1). Implementation on the released P0 / P1 amendment columns: KEEP incumbent (base-stock proxy keeps when options are declared), bounded refund / credit (`credit_per_unit <= prepaid x deposit_refundable_fraction`; one guarded line in the model and in the settlement), fee keys and credit mapped to ORDERING, `zaad/commitments/` (windows, irreversibility ladder, operator block, `NO MATERIAL COMMITMENT IMPROVEMENT AVAILABLE`), migration 022, workspace `commitments=true`. Evidence `docs/zaad_full/evidence/p4b/`: fixtures 21 / 21 (runs 1-4 preserved), invariants, adversarial 16 / 16, profile, frozen chain green (P3 snapshot identical, P1 720, P2 1,720 / 1,720, sector 416 / 416, P3 2,304 / 2,304, P0 120 / 120), no-declaration identity against `2fc7b50`, suite 1,973. Untouched: P0-P5 semantics, P4 node map, P3 formulation, probabilities, tolerances, physics, holdouts, historical tags. Next: P4B release audit under its own authorization; no deployment; V2 not started.

## P4B V1 open PO / commitment intervention — RELEASE AUDIT (2026-09-13, branch `release/p4b-v1-release-audit` from PR #75 head `aacb7b9`)

* Authoritative record `docs/zaad_full/evidence/p4b/release_audit/P4B_RELEASE_AUDIT.md`. Six corrections, smallest scope each: R1 adapter normalisation boundary (`commitments:` refusals for stage / action / provenance / numbers / duplicates; case normalised, nothing mapped to a neighbour); R2 option-set bounds (`INTERACTIVE_LIMITS` 12 per order / 200 non-keep; 413 on `/plan`, four times on `/jobs`); R3 split floor as a sum of clipped cancel caps + settlement floor check (guarded by a positive floor); R4 credit on cancel options only; R5 block 1.1 with `commitment_action` / `commitment_verdict` / `commitment_value_vs_keep` (0 when every order is KEEP) / `overall_plan_status` / `plan_changes_outside_commitments` / `reading`; R6 a pre-existing production defect (numpy bool in `service_reliability`, `/plan` 500 on `2fc7b50`, request id `req-b379888a10da`) cast to `bool`.
* Frozen decisions of record: fixture re-registrations classified VALID FIXTURE REPAIR with causal evidence (`f06_boundary_scan.log`); the released multi-dimensional materiality standard (cost, carried inventory, service) governs commitment recommendations unchanged (E1a); refunds are cancel-only and bounded by `prepaid x deposit_refundable_fraction`; under split the cancel caps must sum inside the floor.
* Validation on the audit product: release-audit cases 35 / 35, fixtures 21 / 21 (F00 identical to `2fc7b50`), adversarial 16 / 16, invariants, profile structurally identical (850 / 300 / 122 nodes), suite 1,979 passed / 2 skipped, ruff / mypy / bandit clean, frozen chain P3 snapshot identical (18 HiGHS calls), P1 canonical PASS + invariants 0 failures, P2 1,720 / 1,720 (15 load-time-limit reviews rerun quiet: 280 / 280), sector 416 / 416, P3 2,304 / 2,304, P0 arm 120 / 120.
* Freeze: `p4b-v1-frozen-product` = `28c1fa7`, `p4b-v1-frozen` = tag `p4b-v1-frozen`. Release: CI run 34774980685 green (12 / 12), PR #76 merged as `main` `1851f40` (tree = tested head), Fly `zaad-api` v23 `canonical-1851f40` from a clean detached checkout, production smoke 12 / 12 (the pre-existing `/plan` 500 on the no-declaration state is gone), logs clean, tag `p4b-v1-release-runtime` = `1851f40`. PR #75 is marked merged by GitHub (its head `aacb7b9` is an ancestor of the merge commit through the release branch); it was never merged independently.

## Exact next action

P4B V1 is released (Fly v23, `1851f40`, tag `p4b-v1-release-runtime`) on top of P5 (v22, `2fc7b50`). P4B V2, P6, P7, P8, P9 are not started and each needs a separate authorization. Keep
`ZAAD_LEGACY_PLANNERS` explicit on every deployed environment and run
`scripts/zaad_canonical_regression.py` before accepting any Dependabot bump that touches the solver
stack. Keep `ZAAD_LEGACY_PLANNERS`
explicit on every deployed environment and run `scripts/zaad_canonical_regression.py` before accepting
any Dependabot bump that touches the solver stack.
