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

## Exact next action

None for the release line. The next brief is P2, branched from `main`; keep `ZAAD_LEGACY_PLANNERS`
explicit on every deployed environment and run `scripts/zaad_canonical_regression.py` before accepting
any Dependabot bump that touches the solver stack.
