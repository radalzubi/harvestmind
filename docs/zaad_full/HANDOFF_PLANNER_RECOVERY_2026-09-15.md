# Handoff — ZAAD V2 production planner recovery (written 2026-09-15, 15:35 UTC)

Read this first if you are continuing the ZAAD release line in a new session. It says exactly where
things stand, what was proved, what is waiting on the owner, and how to pick up without repeating
the day's mistakes. The authoritative records it points at are
[`PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md`](PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md) (the
investigation), [`CURRENT_SYSTEM.md`](CURRENT_SYSTEM.md) (status line) and
[`../ZAAD_RELEASE_LEDGER.md`](../ZAAD_RELEASE_LEDGER.md) (current-state table, "Exact next action").

## 1. State, verified at the time of writing

| item | value |
|---|---|
| `main` | `75e97e7` = production `d2a3cb5` + one docs commit (this file adds another) |
| production runtime | `d2a3cb5` = `Merge PR #83: perf(zaad): production planner performance and availability recovery` (tested head `8ca59fb`, CI 34987486858 13 / 13, tree `9ce1c5d` identical) on the V2 merge `458fcaf` |
| Fly | app `zaad-api`, **v27**, image `zaad-api:canonical-d2a3cb5`, digest `sha256:2d5f2b5ac39a689a4554400437cb5699dd168a4d5d2dfbbbbe2e77b3dd75b13f`, machine `0804e0dfd1e948` (fra), `shared-cpu-2x` / 2 GB, volume `vol_4m3pel5k9mdm95gv`, secrets and env unchanged since v26 |
| Vercel | production from `main` (`e961131` at last check; the next production build picks up PR #83's web change — the queued state's wording — automatically) |
| production health | `GET /health` 200 in 0.5 s; release smoke on v27 **19 / 19** (throwaway workspace `op_0e51acef`); 1-product plan on v27 DONE in 4.0 s |
| plan path | **BLOCKED at the product's default scope (10 products)** — see §2 |
| runtime tag | **none** for the operating product (`zaad-operating-product-v2-runtime` must not be created until §2 passes); last runtime tags `zaad-post-p4b-cleanup-runtime`, `frontend-rebuild-runtime` |
| GitHub Actions | working again since 14:22 UTC (the billing refusal of 10:35 UTC cleared; re-running the refused run started all jobs). CI = `.github/workflows/ci.yml` (13 jobs); deploy = `.github/workflows/deploy-api.yml` (`workflow_dispatch`, inputs `sha` + `app`, secret `FLY_API_TOKEN`, 30-day deploy token created 2026-09-15) — **use it**, the laptop cannot push a build context to Fly |
| PR #83 | merged; nothing open |
| V2.1 (Insights) | **V2.1A released 2026-09-16** on the owner's instruction not to wait for the planner (PR #84 → `13dde49`, Fly v28, tag `zaad-operating-product-v2.1a-runtime`); the planner decisions below still stand |
| P4B V2, P6–P10 | not started; each needs its own authorization |

Verify before trusting any of it:

```bash
gh api repos/radalzubi/harvestmind/git/ref/heads/main --jq .object.sha
fly status -a zaad-api && fly image show -a zaad-api && fly releases -a zaad-api | head -3
curl -s https://zaad-api.fly.dev/health
gh run list -R radalzubi/harvestmind -L 3
```

## 2. What is proved, in one paragraph

Measured in production one plan at a time with the operator's reads timed beside the solve
(`scripts/production_plan_probe.py --self-serve --products N`): on a rested `shared-cpu-2x` machine
1 / 2 / 5 products complete in 4.6 / 29 / 138 s and every routine read stays in its idle band
(0.2–0.5 s median, worst 0.93 s, 0 errors in 902 samples); a second plan queues and then runs; the
**10-product default reaches TIMEOUT at 450 s with no throttling** (509 s of CPU, 7.3 s steal). Two
independent causes: (a) Fly shared vCPUs run at a 6.25 % baseline with a 500 s burst balance — one
plan spends it and everything after, reads included, runs throttled for up to an hour (that is what
timed the V2 closeout out: `/proc/stat` showed steal 1,888 s vs user 348 s); (b) the planner's own
scaling — on the sample every network candidate is infeasible against the service floors, so each
plan escalates to two joint lexicographic MILPs over every product (~22,000 columns at 10) plus a
per-service confirmation ladder, and the solver is 94–100 % of the wall clock. Classification B:
the machine helps, the planner's scaling at the default scope is primary. Component-wise
decomposition was **rejected** (the escalation objective pools unmet demand across products, so it
is a different optimisation, not a faster equivalent). Landed: one explicit solver lease, granted
in submission order, shared with the synchronous routes (`429 planner_busy`); atomic
`QUEUED → RUNNING`; `queue_position` / `running_now` on job reads; the web's queued state says how
many runs are ahead. Verdict recorded: **ZAAD V2 PRODUCTION PLANNER — BLOCKED**.

## 3. The two decisions that are the owner's, not engineering's

The next session cannot pass the planner without one answer to each. Do not decide them yourself;
do not work around them.

**Decision 1 — the machine (spend).** Removes throttling and makes the sizes that fit reliable; does
not shorten the 10-product plan (Fly's performance cores are the same cores without the quota).

```bash
fly scale vm performance-2x --memory 4096 -a zaad-api   # $64.39/month vs $11.83 today (+$52.56)
```

Apply only with explicit authorisation and when no job is RUNNING (`fly scale vm` restarts the
machine; a running job would be ABANDONED, honestly, by the V2 lease semantics). `performance-1x`
(2 GB, $32.19) is not enough: the solver and the API would share one core.

**Decision 2 — the default plan scope or its cap (product policy).** Both options are honest and
both are disclosed on the plan page; they differ in what "the default plan" covers versus how long
the operator waits.

* *Option A — default scope 5*, keep 10 / 25 / 50 as explicit choices that state their measured
  cost. Change `DEFAULT_SCOPE` in `web/src/lib/zaad/workspace-data.tsx` (currently 10;
  `SCOPE_CHOICES = [5, 10, 25, 50]`); the scope sentence (`web/src/lib/zaad/scope.ts`, tested)
  already discloses catalogue / evaluated / solved-together. Add the measured times to the choice
  labels. ~2 minutes for the default plan.
* *Option B — a cap that follows the planner's own budgets*: in `zaad/full/jobs.py`
  `JobRunner.timeout_for`, use `solve_budget(req)` (from `zaad/full/model.py`, up to 90 s) in place
  of `req.max_solve_seconds` — ≈ 900 s at 10 products, still bounded by `ZAAD_JOB_MAX_SECONDS`
  (1800). ~10-minute default plan; the UI's "you can leave the page" wording already fits. Touches
  `zaad/full/jobs.py` (orchestration): rerun the canonical regression and P1 invariants anyway.

Either option is a small PR of its own; keep it separate from Insights.

## 4. Exact sequence to finish V2 once the decisions are made

1. Apply Decision 1 (owner runs it, or authorises you to). Wait until the machine has been idle
   ≥ 30 min before measuring anything — burst balance, if still shared.
2. Land Decision 2 on a branch from `main`, PR, exact-head CI 13 / 13, merge with the convention
   `Merge PR #NN: …`, deploy the **merge SHA** with the workflow:
   `gh workflow run deploy-api.yml -R radalzubi/harvestmind -f sha=<merge sha> -f app=zaad-api`,
   then `fly image show -a zaad-api` must show `canonical-<sha7>`.
3. Prove the plan path **twice in a row** on the deployed runtime:
   `python3 -m scripts.production_plan_probe --api https://zaad-api.fly.dev --self-serve --products <default> --interval 3 --out probe.json`
   (needs `pip install certifi` or `SSL_CERT_FILE=$(python3 -m certifi)` on a python.org build).
   Pass = DONE inside the cap both times, reads in their idle band, 0 errors. Also run it once with
   `--second-plan-after 5` to see the second plan queue rather than overlap.
4. Run `scripts/operating_product_release_smoke.py --api https://zaad-api.fly.dev --self-serve`
   (expects 19 / 19) and review `fly logs -a zaad-api --no-tail`.
5. Only then: `git tag -a zaad-operating-product-v2-runtime <merge sha>` and push the tag; update
   `CURRENT_SYSTEM.md`'s status line and the ledger's current-state table to the new runtime, tag
   and machine; write "V2 PRODUCTION RELEASE PASS" in the ledger.
6. Then, and only then, start V2.1 (Insights) on a **new branch from the final V2 main**
   (`feat/zaad-insights-canonical-connectivity`); the V2.1 brief (§0–128) remains authoritative.

## 5. Things that cost hours today — do not repeat them

* **Never benchmark production with overlapping solves**, and never trust a timing taken within
  ~30 min of a previous solve on the shared machine: check `/proc/stat` steal first —
  `fly machine exec 0804e0dfd1e948 -a zaad-api 'sh -c "head -1 /proc/stat; cat /proc/loadavg"'`
  (the image has no `ps`/`free`; read `/proc`). The 8th field is steal, in centiseconds.
* **Local solver timings are not production-equivalent.** The image runs Python 3.12 / highspy
  1.15.1 / scipy 1.18.1 on x86-64; the laptop's default interpreter is 3.14 / highspy 1.14.0, and even
  a version-matched 3.12 venv on arm64 takes a different HiGHS search path. Use
  `scripts/production_solve_benchmark.py` locally for *structure* (dimensions, which solves
  dominate), production probes for *time*. `uv venv --python 3.12` + `uv pip install -e . highspy==1.15.1 scipy==1.18.1 numpy==2.5.3 duckdb==1.5.5 pydantic==2.13.5` rebuilds the matched venv in a minute.
* Running `scripts.p1_invariants` on the laptop rewrites
  `docs/zaad_full/evidence/p1/P1_INVARIANTS.json` with other objective-flat tie choices. The checks
  still pass; `git checkout` the file, never commit it from the laptop — CI regenerates it on x86.
* The Fly Prometheus metrics API (`api.fly.io/prometheus/<org>`) refused the organisation slug with
  both a session token and a read-only token; steal time from `/proc/stat` is the usable signal.
* `/private/tmp` scratch clones do not survive; the Desktop repo's git was healthy on 2026-09-15
  (fetch, `ls-tree -r`, diff all fine) — test before assuming the earlier iCloud stall.
* Do not build the Fly image from the laptop (Depot upload stalls, classic builder gRPC dies); the
  `deploy-api` workflow is the canonical path now that Actions works. The builder-side recipe in
  the ledger's V2 entry remains the fallback.
* `HARVESTMIND_SOLVER_THREADS` is a Fly secret (`2`) that overrides `fly.toml`'s `1`; nothing under
  `zaad/` reads it (only the legacy `optimization/solve_status.py`). Not a lever.
* Rate limit is 60/min **per client IP and path**; the probe's seven distinct reads every 3 s are
  fine, seven hits of one path every 3 s would not be.

## 6. What the next session must not do

* Start Insights / V2.1, P4B V2, or P6–P10 before §4 step 5 is done.
* Tag an unhealthy runtime, raise the cap "to make the benchmark pass", or lower the default scope
  without the owner's Decision 2 — the record explains why both are policy, not engineering.
* Change anything under `zaad/` that computes a decision (objective, settlement, phase semantics,
  solver options) for speed. Orchestration in `zaad/full/jobs.py` is allowed with the canonical
  regression and P1 invariants rerun.
* Touch Validation7 / Validation8 / holdout4; fake ERP integrations; send supplier orders.

## 7. Where the evidence files are

* Record: `docs/zaad_full/PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md` (§3 production runs, §3.1 the
  10-product timeout, §4 root cause, §5 shares and dimensions, §6 coupling and why decomposition is
  rejected, §7 the lease, §9 every decision, §10 the machine command and cost, §11 gates, §12
  acceptance matrix, §13 limits, §14 verdict).
* Scripts: `scripts/production_plan_probe.py`, `scripts/production_solve_benchmark.py` (both outside
  `zaad/`), `scripts/operating_product_release_smoke.py`.
* Tests pinning the lease: `tests/unit/test_zaad_solver_lease.py` (6),
  `tests/integration/test_zaad_jobs.py::test_a_synchronous_plan_is_refused_while_a_job_holds_the_solver_lease`,
  `web/src/lib/zaad/__tests__/queue.test.ts`.
* Raw probe JSON / logs from 2026-09-15 were in the session scratchpad only (not committed); the
  numbers they produced are in the record's tables. Re-measure rather than reconstruct.
* Throwaway production workspaces created today (sample data only, safe to leave or delete):
  `op_444e3293`, `op_9844a31c`, `op_954c232d`, `op_0e51acef`, plus the 10-product run's and the V2
  closeout's `op_ca598163`, `op_1ed2d08a`.
