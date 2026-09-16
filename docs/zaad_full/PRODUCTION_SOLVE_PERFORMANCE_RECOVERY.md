# Production solve performance recovery (2026-09-15)

The Operating Product V2 was merged (`458fcaf`) and deployed (Fly `zaad-api` v26, `canonical-458fcaf`)
with every surface verified in production except the plan path: the default 10-product plan and a
5-product plan both reached TIMEOUT on the `shared-cpu-2x` machine, and reads took 40–80 s while solves
overlapped. This record is the investigation of *why*, the measurements behind the answer, and what was
changed. Nothing under `zaad/` that computes a decision was altered; the optimizer's economics, phase
semantics and solver settings are the released ones.

Companion scripts (both outside `zaad/`): `scripts/production_solve_benchmark.py` (the planner observed
from outside, by product count: every MILP's dimensions, budget and time, every candidate's build-and-
settle time, plan shape, serialisation and job-store write) and `scripts/production_plan_probe.py` (one
product-shaped plan against a deployed API with the operator's routine reads timed while it runs, and
an optional second plan to observe queueing).

## 0. Starting state — verified, not assumed

| item | expected | verified |
|---|---|---|
| remote `main` | `e961131` | `e96113103ca7a5feb6a79e52d8915e75eeddb5f8` (GitHub ref and fresh fetch agree) |
| V2 merge | `458fcaf` | parent of `b4dbdc0`; tree identical to tested head `b98bd0e` (recorded in the V2 audit) |
| Fly `zaad-api` | v26 `canonical-458fcaf` | v26, image `zaad-api:canonical-458fcaf`, digest `sha256:4ba1cd256bcbf732339b9d273a03c93541c7d90f46c18d08aab93dc14b2e661d`, one machine `0804e0dfd1e948` (fra), health check passing |
| machine | `shared-cpu-2x` | guest `cpu_kind=shared, cpus=2, memory_mb=2048`; `nproc` 2; `MemTotal` 2,015,640 kB |
| Vercel production | from the V2 merge | GitHub deployment records: production `zaad` and `harvestmind` from `e961131` (12:25 UTC), before that `b4dbdc0`; both are docs / workflow commits on top of `458fcaf`, so the web bytes are the V2 merge |
| production API | healthy | `GET /health` 200 in 0.5 s: `{"status":"ok","service":"zaad-api","env":"pilot","auth_enforced":true,"rate_limit_per_min":60}` |
| runtime tags | no V2 runtime tag | last runtime tag `zaad-post-p4b-cleanup-runtime` (`9012770`), `frontend-rebuild-runtime`; nothing for the operating product |
| working tree | clean | Desktop clone on `main` = `e961131`, `git status` clean (the earlier iCloud object stall did not recur; `ls-tree -r` and `diff` complete) |
| GitHub Actions | blocked for billing | see §1 |

The V2 records had one contradiction: the first status line of `docs/zaad_full/CURRENT_SYSTEM.md` still
described the v24 runtime while its table and the ledger described v26. Corrected in this pass.

## 1. GitHub Actions gate

At 10:35 UTC every job on this private repository was refused with *"The job was not started because
recent account payments have failed or your spending limit needs to be increased"* (CI run 34958788944
on `b4dbdc0`, deploy-api run 34958812308). Re-running that CI run at 14:22 UTC started all 13 jobs
immediately; it completed **success, 13 / 13** at 14:31 UTC. The account block is resolved and the
exact-head CI gate is available again. No release control was bypassed.

## 2. Configuration as deployed

| setting | value | where |
|---|---|---|
| job workers (solver processes at once) | 1 | `ZAAD_JOB_WORKERS` unset → default 1 (`zaad/full/jobs.py`); one `BoundedSemaphore(workers)` |
| active jobs per workspace | 2 | `ZAAD_JOB_QUOTA_ACTIVE` default 2 (an evaluation needs both: baseline + overlay) |
| jobs per workspace per day | 24 | `ZAAD_JOB_QUOTA_DAILY` default |
| job wall clock | `min(1800, max(30, max_solve_seconds × (10 + services) × 1.5))` | `JobRunner.timeout_for`; 15 s × (10 + N) × 1.5 → 248 s (1 product), 270 s (2), 338 s (5), 383 s (8), 450 s (10) |
| per-MILP budget | `max_solve_seconds × (H/12)² × (1 + 0.6 × (lines − 1)) × 1.3`, ceiling 90 s | `zaad/full/model.py: solve_budget`; *lines* = distinct (SKU, destination) pairs, so it grows with the product count: 19.5 s (1), 31.2 s (2), 66.3 s (5), 90 s cap (≥ 8) |
| HiGHS options | `output_flag=False`, `time_limit=budget`, `mip_rel_gap=1e-6`; no `threads` option set (HiGHS default); the shared-supplier-order class adds the P3 search options; every other request keeps the frozen scipy `milp` route | `zaad/full/model.py` |
| solver process | one `multiprocessing` spawn child per job; the API process stays free | `zaad/full/jobs.py: _execute_guarded` |
| synchronous planning routes | `/api/zaad/network/plan`, `/plan/from-workspace`, legacy `/api/zaad/plan`: run the planner in the API process's thread pool behind a separate `BoundedSemaphore(1)`, so one synchronous plan **can** run beside one job | `api/routers/zaad_full.py`, `api/routers/zaad.py`; the product UI never calls them |
| `HARVESTMIND_SOLVER_THREADS` | secret `2` overrides `fly.toml`'s `1` | read only by the legacy `optimization/solve_status.py`; nothing under `zaad/` reads it |
| Python / solver stack in the image | Python 3.12.14, highspy 1.15.1, scipy 1.18.1, numpy 2.5.3 | measured on the machine; the laptop's default interpreter is 3.14 / highspy 1.14.0 / scipy 1.17.1 — HiGHS 1.14 explores a different tree on this class (a 2-product plan: 11.6 s on 1.14.0, 3.7 s on 1.15.1, 29 s on the production machine), so every local number below comes from a 3.12 virtualenv pinned to the image's versions — and even then the laptop's arm64 build takes a different search path from the image's x86-64 one, so local runs are used for *structure* (dimensions, which solves dominate, shares) and production runs for *time* |
| API server | one uvicorn process, 12 threads at rest | `python -m api.serve` |


## 3. The production measurements — one plan at a time, reads timed while it runs

Method: `scripts/production_plan_probe.py --self-serve --products N` against `https://zaad-api.fly.dev`.
Each run creates a throwaway workspace through the product's self-serve path, loads the sample FMCG
data (150 products, 427,995 rows — the same data the V2 smoke and browser walks used), builds the
request exactly as the plan button does (every product with a declared order change first, then the
most units still on order; every phase asked for), submits it to `POST /api/zaad/network/jobs`, and,
until the job ends, times seven reads every ~3 s: `/health`, `/me`, the workspace summary, the
inventory list, the purchase-order list, data readiness and the job itself. No two of these runs
overlapped; the machine had been idle for hours before the first one. CPU counters were read from
`/proc/stat` on the machine before and after each run.

| products | job cap | queued | run | outcome | `joint_recovery` solve | reads while solving (median / p95 / max, s) | errors |
|---|---|---|---|---|---|---|---|
| 1 | 247.5 s | 0.0 s | **4.6 s** | DONE, RETAIN_INCUMBENT | 0.7 s OPTIMAL | health .24 / .28 / .28 · summary .26 / .28 / .28 · inventory .37 / .43 / .43 · POs .33 / .37 / .37 · readiness .43 / .51 / .51 | 0 |
| 2 | 270 s | 0.0 s | **29.1 s** | DONE | 19.1 s OPTIMAL | health .22 / .28 / .28 · summary .31 / .48 / .48 · inventory .38 / .44 / .44 · POs .33 / .37 / .37 · readiness .41 / .53 / .53 | 0 |
| 2, submitted 6 s after the first | 270 s | **19.2 s** (QUEUED until the first finished) | 29.0 s | DONE | 18.8 s OPTIMAL | same window as above | 0 |
| 5 | 337.5 s | 0.0 s | **137.8 s** | DONE | 58.9 s OPTIMAL | health .21 / .27 / .27 · summary .30 / .38 / .41 · inventory .39 / .45 / .46 · POs .33 / .38 / .41 · readiness .43 / .49 / .50 · job .21 / .27 / .50 | 0 |
| 10 (the product's default) | 450 s | 0.0 s | **TIMEOUT at 450 s** (run 452.5 s) | no report | — | health .22 / .34 / .48 · summary .30 / .55 / .70 · inventory .41 / .69 / .91 · POs .34 / .52 / .87 · readiness .46 / .72 / .93 · job .21 / .33 / .35 (85 samples) | 0 |

Idle medians for the same reads, taken before each run: health 0.22–0.25 s, summary 0.29–0.33 s,
inventory 0.30–0.39 s, purchase orders 0.27–0.30 s, readiness 0.40–0.47 s. **While a solve runs the
reads are indistinguishable from idle** — the solver child owns one vCPU, the API process the other.

CPU accounting of the 5-product run (from `/proc/stat`, 14:32:13 → 14:36:37 UTC): user 171.8 s,
system 2.5 s, idle 350.4 s, **steal 3.7 s**. The solver process (`multiprocessing` spawn child) had 3
threads and 211 MB RSS; the API process 12 threads and 537 MB; load average peaked at 0.81. Two
solver processes were never alive at once (the second 2-product plan was QUEUED for 19.2 s — the job
runner's single worker — then ran alone).

### 3.1 The default 10-product plan, on a rested machine

Run at 15:05 UTC after 28 idle minutes (the balance spent by the runs above had refilled: the
counters show idle CPU only in between). `/proc/stat` over the run (15:05:15 → 15:13:18): **user
509.0 s**, system 7.6 s, idle 441.4 s, **steal 7.3 s** — no throttling; the solver child held one
vCPU flat out for the whole 450 s (load average 1.32) and the API process answered every read from
the other: 595 reads, 0 errors, worst 0.93 s. The job ended **TIMEOUT, "exceeded 450s wall clock"**,
with no report: the ladder had not reached the end of its confirmation solves.

So on a rested machine the plan path works up to 5 products with every routine read under half a
second, and **the product's default of 10 products does not fit its cap at full CPU speed**. That is
the two-part answer the V2 closeout could not separate: the day before, everything timed out and
reads took 40–80 s because the machine was throttled (§4); today, unthrottled, the 1-, 2- and
5-product plans complete comfortably and the 10-product default still needs more than 450 s of one
core (§5 says where). A dedicated CPU fixes the first part; it does not shorten the second, because
Fly's performance vCPUs are the same cores without the quota, not faster ones.

## 4. Root cause: the shared CPU's burst budget, exhausted by consecutive solves

Fly's shared-cpu machines are quota'd, not clocked: each shared vCPU is entitled to **5 ms of every
80 ms period (6.25 %)** and accrues unused time into a burst balance of at most **500 s**; while the
balance lasts the vCPU runs at 100 %, and when it is spent the scheduler throttles the whole VM back
to the 6.25 % baseline for the rest of each period (Fly docs, *CPU performance*). Performance
vCPUs get the full 80 ms and have no balance. Steal time in the guest is the time the vCPU wanted to
run and was not scheduled.

Evidence that this, and not the model, is what timed the V2 closeout out:

* `/proc/stat` on the machine at 14:22 UTC, after 2 h 35 min of uptime: **user 347.9 s, steal 1,887.6 s**.
  Since boot the VM had been denied the CPU it asked for 84 % of the time it was busy. Nothing else
  runs on it.
* The V2 closeout ran, in a row: the 10-product plan (TIMEOUT at 450 s), the 5-product plan (TIMEOUT
  at 337 s) and the profiler on the machine (306 s of solver time). The first of those alone spends
  the 500 s balance; everything after it ran at 6.25 % of a vCPU. A 5-product plan that takes 138 s at
  full speed takes about 37 min at the baseline — hence "TIMEOUT" everywhere and reads of 40–80 s
  (the API process shares the throttled quota).
* Today, after hours of idle, the same 5-product plan completed in 137.8 s with 3.7 s of steal, and
  reads never left their idle band.
* The balance refills at the baseline rate: 2 vCPUs × 6.25 % = 0.125 s of CPU per second, so a
  138 s plan is "paid back" in ~18 min and a 450 s one in an hour. One default plan per hour, at
  best, is the honest capacity of `shared-cpu-2x` for this workload.

Classification (§20 of the brief): **B — the machine helps, but the planner's scaling at the default
scope is the primary problem.** With the balance intact the released planner completes 1, 2 and 5
products inside their caps with the API responsive, and with the balance spent nothing completes —
that part is the machine, and a dedicated CPU removes it. But the 10-product default needs more than
450 s of one unthrottled core (§3.1), and no Fly machine has a faster core; that part is the joint
escalation solve and the per-service confirmation ladder (§5), which grow superlinearly with the
products solved together.

## 5. Where the time goes inside a plan

Method: `scripts/production_solve_benchmark.py --vault sample --products 1,2,5,8,10` in the
version-matched virtualenv: the planner observed from outside (nothing in `zaad/` instrumented),
every `Linear.solve` call recorded with its dimensions, budget, wall and CPU time, every candidate's
build-and-settle time around its MILPs, then the plan shape, `report_json` and a job-store write.

### 5.1 Shares

| products | plan wall (laptop) | solver core | candidate build + settlement | plan shape | serialise | job-store write | peak RSS | report |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.56 s | 0.46 s (81 %) | 0.05 s | 0.000 s | 0.000 s | 0.001 s | 553 MB | 51 KB |
| 2 | 3.7 s | 3.5 s (94 %) | 0.7 s | 0.000 s | 0.001 s | 0.001 s | 625 MB | 84 KB |
| 5 | 135.2 s | 134.7 s (100 %) | 0.5 s | 0.000 s | 0.001 s | 0.002 s | 1,204 MB | 167 KB |
| 8 | 413.9 s | 413.0 s (100 %) | 0.9 s | 0.000 s | 0.001 s | 0.002 s | 1,301 MB | 247 KB |

Request construction (the full 150-product workspace read) 0.40 s; the scoped request build
0.06 s; the vault load 3.1 s (a one-time upload, not part of a plan). Settlement is 0.01–0.05 s for
39–81 calls. **Everything outside the solver is under one second at every size**; the previous
profiler's "~96 % solver" is confirmed at 94–100 %. Nothing in JSON, SQL, request conversion or
serialisation is worth a line of work.

### 5.2 Model dimensions (largest MILP of the plan)

| products | MILPs per plan | columns | rows | integer | binary | non-zeros | per-MILP budget | scenarios (worlds) | screen state |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 14 | 2,361 | 2,446 | 735 | 723 | 12,977 | 19.5 s | 3 (+1 stress) | PROTECT |
| 2 | 16 | 4,624 | 4,701 | 1,469 | 1,445 | 25,708 | 31.2 s | 3 | PROTECT |
| 5 | 20 | 11,125 | 11,166 | 3,575 | 3,515 | 61,545 | 66.3 s | 3 | PROTECT |
| 8 | 28 | 17,621 | 17,626 | 5,681 | 5,585 | 97,332 | 90 s (cap) | 3 | PROTECT |
| 10 | 30 (by ladder shape) | ~22,000 (linear in products) | | | | | 90 s (cap) | 3 | PROTECT (production: TIMEOUT at 450 s, §3.1) |

Horizon 12 weeks; one location (the sample declares none, so the frozen single-location request);
one source and one service per product; 3, 5, 11, 17 and 21 open POs for 1, 2, 5, 8 and 10 products.
No phase block is declared by the sample (`sourcing`, `recourse`, `atp`, `commitments` all absent
from the request even though the product asks for all of them), so no P3 order class, no P4 tree,
no P5 allocation, no P4B options enter the model. The request is not in the shared-supplier-order
class, so the frozen scipy route and the frozen search settings apply. The HiGHS default thread
count is in force (no `threads` option is set): the solver child showed 3 threads on the machine and
80 % of one vCPU; on the laptop the CPU share of the plan was 0.97–1.36×, i.e. one core.

### 5.3 Which solves dominate, and why

Every plan on this data takes the same path. The six network candidates (`deterministic_network`,
`stochastic_network`, `cvar_network`, `protected_network`, `hedged_network`, `stress_network`) are
**INFEASIBLE in well under a second each** — the sample's service floors cannot be met inside the
lead time from the opening position — so no candidate meets every service target and the planner's
escalation rule (`adaptive_escalation`) builds the joint feasibility frontier: two `service_first=
"all"` solves over *every* product at once (`joint_recovery` on the fitted-plus-stress worlds, the
joint fitted frontier on the selection worlds), each a two-phase lexicographic MILP (minimum unmet
demand first, then cost under that optimum). Those two solves are the plan:

| products | `joint_recovery` | joint fitted | everything else |
|---|---|---|---|
| 1 (laptop) | 0.1 s | 0.1 s | 0.4 s |
| 2 (laptop) | 0.6 s | 1.9 s | 1.2 s |
| 5 (laptop) | 66.4 s, FEASIBLE_TIME_LIMIT (at budget) | 66.3 s, FEASIBLE_TIME_LIMIT | 2.5 s |
| 8 (laptop) | 90.0 s, FEASIBLE_TIME_LIMIT (at cap) | 90.0 s, FEASIBLE_TIME_LIMIT | 233.9 s (the per-service confirmation solves grow too: one took 67.9 s) |
| 2 (production) | 19.1 s OPTIMAL | — | 10 s |
| 5 (production) | 58.9 s OPTIMAL | — | 79 s |
| 10 (production) | not reached the end | | > 450 s in total: TIMEOUT |

After the two joint solves the ladder runs one **per-service confirmation solve** per product
(`alternative_value`: a two-phase solve of the deterministic model with that product's service
first), each over the whole scope's model (4,554 columns at 8 products) — at 8 products on the laptop
those ten solves took 2–68 s each, 234 s together. The count of these grows with the products, and
each one's size grows with the products: the second superlinear term.

The joint MILP couples every product through the lexicographic objective (one "unmet" total) even
when nothing in the data couples them. That is the superlinear term: at 5 products it is already at
its budget on the laptop, and at 8 both joint solves stop at the 90 s cap with a feasible incumbent
(a `FEASIBLE_TIME_LIMIT` candidate is admitted into selection under the released comparability
rules; the report says so in `solve_quality`).

## 6. Coupling: what actually ties these products together

From the request the product builds (`scripts/v2_solve_profile.coupling`, run over the ranked scope):

| scope | catalogue | components | component sizes | edges | why the edges exist |
|---|---|---|---|---|---|
| 1 | 150 | 1 | [1] | — | — |
| 2 | 150 | 2 | [1, 1] | none | different suppliers |
| 5 | 150 | 4 | [2, 1, 1, 1] | 1 | two products share supplier SUP-001's weekly capacity resource |
| 8 | 150 | 6 | [3, 1, 1, 1, 1, 1] | 2 | three products on SUP-001 |
| 10 | 150 | 7 | [3, 2, 1, 1, 1, 1, 1] | 3 | SUP-001 ×3, SUP-004 ×2 |
| 25 | 150 | 8 | [6, 4, 4, 3, 3, 2, …] | 17 | one component per supplier |
| whole catalogue | 150 | 8 | [19 × 8] | 142 | eight suppliers, each a capacity resource shared by its 18–19 products |

No supplier terms (MOV / fixed order cost), no fixed order fees, no transfers, no customer
allocation, no opening-cash constraint: the only declared coupling is the supplier capacity
resource. The one *global* tie the released formulation carries is the location's storage
capacity, declared as 10⁹ units for the sample — present in the model, never binding. The "10
products" the product defaults to are therefore seven independent decision problems solved as one,
and the joint escalation solve is where the coupling that is not in the data is manufactured by the
objective.

What this does **not** license (§23–24 of the brief): solving the components separately and adding
the ledgers. The joint escalation solve is lexicographic: phase one minimises **one** priority-
weighted total of unmet demand across every product, phase two minimises cost subject to *that
total* not rising. Even with no shared constraint, phase two may trade unmet demand between two
independent products — more on one, less on another, the total unchanged — when that is cheaper;
solving each component alone pins each product's own unmet at its own minimum and cannot make that
trade. The two problems have different feasible sets in phase two, so **component-wise decomposition
is not equivalent to the released joint solve** in general; it would be a change to what the planner
optimises, not to how fast. It is therefore rejected for this pass (§9), not deferred: it would need
its own mathematical authorisation, with the frozen gates re-baselined. Nothing in this pass changes
what the planner solves.

## 7. Concurrency: what could run at once, and what does now

As deployed, the job runner ran one solver process at a time (`ZAAD_JOB_WORKERS` unset → 1), with
two active jobs per workspace so an evaluation's baseline and overlay could both be *submitted*; they
then ran one after the other through the single slot. Two solver processes could still coexist on
the machine through the synchronous planning routes (`/plan`, `/plan/from-workspace`), which held
their own semaphore; the product's UI never calls them, so the overlap the V2 closeout saw came
from running the profiler on the machine beside a job, not from the product. Two solves at once on
this machine is not "twice as slow": the API process is the third claimant on two vCPUs and, once
the burst balance is gone, on 12.5 % of one.

Changed in this pass (`zaad/full/jobs.py`, orchestration only; `api/routers/zaad_full.py`):

* **One explicit solver lease**, `workers` wide (1), granted in **submission order**: the earliest
  queued job runs first; an evaluation's baseline then its overlay; no workspace overtakes another's
  queue; queued work adopted after a restart keeps its creation order. Deterministic enough to
  explain: a job's place is the sequence number it received when it was submitted.
* The synchronous routes take the **same lease** and answer `429 planner_busy` — only when no job
  holds it and none is waiting, so they never overtake the queue.
* `QUEUED → RUNNING` is an **atomic claim** in the store: a job cancelled while it waited is never
  started and its "cancelled before start" is never overwritten; a job is RUNNING only once its
  process exists (the row is written a few milliseconds before the process starts, and a cancel in
  that gap is recorded as "not being executed by this service", which is the truth).
* A queued job's read says where it stands: `queue_position` (1 = next to start) and `running_now`
  (how many solves hold the lease); the web's queued state reads "Your run is next; the planner is
  finishing another run…" or "queued behind N other runs; the planner runs one at a time…" instead of
  a bare "queued". No ETA is promised.
* Cancellation: QUEUED cancels immediately and skips its turn; RUNNING terminates the solver process
  (`proc.terminate()`) and records "cancelled by the workspace"; a RUNNING job this service is not
  executing says so rather than "before start". A timed-out or failed solve releases the lease for
  the next job (test-pinned).

Evaluation (§14 of the brief) already runs baseline and overlay **sequentially** by construction;
they were never parallel. Measured on the sample, baseline and overlay each cost a full plan of the
proposal's scope (an evaluation over 5 products ≈ 2 × 138 s of solver CPU on a rested machine).
Nothing changed there: correctness first, and sequential is what keeps the API usable.

Fairness: strict submission order means one workspace cannot starve another except by submitting
first, and the per-workspace quotas (2 active, 24 per day) bound how much of the queue any tenant
can occupy. No distributed scheduler; one process, one lease, one deque.

Tenant safety: the lease is process-global and carries no tenant data; `queue_position` reveals
only a count. Job reads, cancels and lists stay scoped to the caller's operator; nothing cached.

## 8. API responsiveness during a solve — the acceptance measurement

Budget used: the idle band of the same reads on the same machine (§3), not an invented SLA.

| read | idle median | during the 5-product solve: median / p95 / max | verdict |
|---|---|---|---|
| `/health` | 0.25 s | 0.21 / 0.27 / 0.27 s | within idle |
| `/me` | 0.31 s | 0.22 / 0.28 / 0.29 s | within idle |
| workspace summary (Home) | 0.29 s | 0.30 / 0.38 / 0.41 s | within idle |
| inventory list | 0.39 s | 0.39 / 0.45 / 0.46 s | within idle |
| purchase-order list | 0.27 s | 0.33 / 0.38 / 0.41 s | within idle |
| data readiness | 0.40 s | 0.43 / 0.49 / 0.50 s | within idle |
| job status | — | 0.21 / 0.27 / 0.50 s | fine |
| HTTP 503 / 500 / transport errors | — | 0 in 196 reads across the four runs | — |

The same holds while two plans are in flight (one running, one queued): §3, the 2 + 2 run. The
40–80 s reads of the V2 closeout do not reproduce on a machine with burst balance; they were the
throttled baseline, and they will return on `shared-cpu-2x` whenever a plan spends the balance.

## 9. Decisions on every candidate change

| change | decision | why |
|---|---|---|
| explicit ordered solver lease shared by jobs and synchronous routes; queue position; atomic claim | **PURSUE — done** | the cap on concurrent solves was a default, not a policy; the sync routes could double it; queued work should say where it stands (§7) |
| dedicated CPU: `performance-2x`, 4 GB | **PURSUE — needs the owner's authorisation (spend)** | the shared vCPU's 6.25 % baseline and 500 s balance make one 5-product plan per ~20 min the ceiling and throttle the API with it; a performance vCPU has no balance (§10). It makes the plans that fit their caps *reliable*; it does not make the 10-product default fit (§3.1) |
| the default plan scope (10) and its cap (450 s) | **decision for the owner — two honest options, §13** | at full speed 10 products need more than 450 s of one core; 5 products need 138 s. Either the default scope becomes the size that completes (5, with 10 / 25 / 50 as explicit choices that say what they cost), or the cap follows the planner's own per-solve budgets (≈ 900 s for 10 products) and the operator waits ~10 min for the default plan. Neither is a hidden change; both are disclosed on the plan page. Not chosen here because it is a product policy, not an engineering fact |
| decomposition of the joint escalation solve by coupling component | **REJECT for this pass** | seven independent components are solved as one 22,000-column MILP at 10 products, but the lexicographic escalation objective pools unmet demand across products, so component-wise solving is a different optimisation, not a faster equivalent one (§6); a change of that kind needs its own authorisation and a re-baselined frozen gate |
| candidate prefilter (drop products with nothing to decide) | **DEFER** | the planner already screens states and skips classes; the products the UI scopes all carry open POs by construction; nothing to remove safely without the coupling proof |
| reuse of the workspace read / fits between baseline and overlay | **REJECT** | the repeated work is 0.4 s per run against 138 s of solving; a cache keyed on every correctness input would buy nothing measurable |
| raise the job wall clock (450 → 900 s) | **REJECT** | on a rested machine the caps hold; on a throttled one no cap helps; a longer cap only lengthens the throttled period for everyone |
| HiGHS options (threads, presolve, gap, cuts) | **REJECT** | not the bottleneck: one core is fully used, no time-limited solve is proof-bound at small sizes, and any search-path change flips the frozen tie-sensitive gates |
| adaptive per-MILP budget vs job cap (the sum of budgets can exceed the cap) | **DEFER, documented** | the cap is the honest wall clock; `FEASIBLE_TIME_LIMIT` candidates are admitted under the released comparability rules; the mismatch has not produced a wrong outcome, only a TIMEOUT when throttled |
| lower the default scope below 10 | **REJECT** | it would hide the machine's limit; the scope rule is disclosed on the plan page and the honest fix is the CPU (§29–31 of the brief) |
| expose the machine's steal time on Diagnostics | **DEFER** | useful signal, no measurement today depends on it |

## 10. Infrastructure: the exact change and its cost — not applied

Nothing about the machine was changed in this pass (no authorisation for spend). What the evidence
supports, and the command that would do it:

```bash
fly scale vm performance-2x --memory 4096 -a zaad-api
```

| option | vCPU | RAM | $/month (ams basis; fra prices the same tier) | Δ vs today | what it buys |
|---|---|---|---|---|---|
| `shared-cpu-2x` 2 GB (today) | 2 × 6.25 % baseline, 500 s burst | 2 GB | $11.83 | — | one rested default plan per hour, then throttling |
| `performance-1x` 2 GB | 1 × 100 % | 2 GB | $32.19 | +$20.36 | no throttling, but the solver and the API would share one core — reads would degrade during every solve |
| **`performance-2x` 4 GB** | 2 × 100 % | 4 GB | **$64.39** | **+$52.56** | one core for the solver, one for the API, no balance to spend; 4 GB covers the 10-product solver child (≈1.3 GB RSS at 8 products, rising) beside the 0.5 GB API process with room for a second queued request's memory |

Expected effect: plan times equal to today's rested measurements (§3) on every run, not only the
first of the hour; reads unchanged. The rolling deploy of a `fly scale vm` change restarts the
machine (the volume and secrets are unchanged); a queued job would be ABANDONED and reported as
such (V2 lease semantics), so apply it when no job is running.

## 11. Job lifecycle, orphan and lease regression

Re-run on this branch (Python 3.12 virtualenv pinned to the image's solver stack, and the laptop's
default interpreter for the API tests):

| suite | what it pins | result |
|---|---|---|
| `tests/unit/test_zaad_job_lifecycle.py` (8) | store upgrade from the pre-lease schema; a live lease is never reaped by a reader; heartbeat renews only the owner's jobs; a new runner ABANDONs lapsed RUNNING jobs and resumes lapsed QUEUED ones; cancelling an orphan says what happened; purposes and references; submit stamps the owner | 8 passed |
| `tests/unit/test_zaad_solver_lease.py` (6, new) | one solve at a time in submission order with `queue_position` and `leases()`; a queued cancel is immediate, is never overwritten and the next job takes the turn; a running cancel terminates the process; a synchronous solve takes the same lease and never overtakes the queue; a timed-out solve releases the lease; adopted queued work runs in creation order | 6 passed |
| `tests/integration/test_zaad_jobs.py` (4, +1 new) | submit / poll / isolation; cancel and active quota; timeout terminates the worker; **a synchronous plan is refused `planner_busy` while a job holds the lease and a second job reads `queue_position` 1 / `running_now` 1** | 4 passed |
| `tests/integration/test_evaluation_atomicity.py` (6) | record-first evaluation, quota refusal leaves no record, baseline cancel on overlay refusal, amendment counterfactual, staleness | 6 passed |
| `tests/integration/test_diagnostic_job.py`, `tests/unit/test_tenant_isolation.py` | diagnostic replay through the runner; tenant scoping of jobs | passed (40 passed across the six files together) |
| `scripts.zaad_canonical_regression` | frozen P0 / P1 / P2 / sector / P3 / P4 / P5 decisions | **CANONICAL REGRESSION PASS** |
| `scripts.p1_invariants` | 720 P1 economics checks | **invariants clean: 720** (the laptop's arm64 solver build lands on other objective-flat ties than the committed x86 evidence; the evidence file is left as committed — CI regenerates it) |
| `scripts.zaad_workspace_smoke 7 A_stable 3` | synthetic workspace → Request → frozen plan | exit 0 |
| web: `tsc --noEmit`, `eslint`, `tsx --test` | queue rule (`queueAheadOf`, 2 new tests) and the rest | typecheck clean, 0 lint errors, **140 passed** |
| ruff (CI scope), mypy (CI scope: `api zaad/full …`), bandit (`api zaad/full`) | | clean / `Success: no issues found in 151 source files` / no findings |

Crash matrix (§37 of the brief), by construction and test: the API stopping while a job is **queued**
→ the job keeps its row; the next runner adopts it (`resumed_at_start`, creation order) and runs it;
while a job is **running** → its daemon child dies with the parent, the lease lapses, the next
reader or runner marks it ABANDONED with the reason, and the workspace's active quota is released;
during an **evaluation's baseline** → the baseline is ABANDONED, the overlay (queued, owned by the
dead runner) is adopted and runs, and the evaluation read reports FAILED because one of its runs is
ABANDONED (`api/routers/zaad_orders.py`, evaluation status rule) — nothing is approved from a
half-evaluation; during an **evaluation's overlay** → the same rule from the other side. Cancellation
semantics are in §7.

Failure isolation (§38): a plan's TIMEOUT / FAILED / ABANDONED is one job row; Home, Inventory,
Purchase orders, Data, Diagnostics and History read the vault, not the job, and the V2 smoke and
the probes above exercised them beside running and finished jobs with zero errors.


## 12. Production acceptance matrix (this pass, `shared-cpu-2x`, rested unless stated)

| item | value |
|---|---|
| idle Home (workspace summary) latency | 0.29–0.43 s median |
| Home latency during a solve | 0.30 s median, 0.55 s p95, 0.70 s max (10-product run, 85 samples) |
| Inventory latency during a solve | 0.41 s median, 0.69 s p95, 0.91 s max |
| Purchase-order list latency during a solve | 0.34 s median, 0.52 s p95, 0.87 s max |
| Readiness latency during a solve | 0.46 s median, 0.72 s p95, 0.93 s max |
| job-status latency | 0.21 s median, 0.33 s p95 |
| 1-product solve | DONE in 4.6 s (cap 247.5 s) |
| 2-product solve | DONE in 29.1 s (cap 270 s); a second one queued 19.2 s then DONE in 29.0 s |
| 5-product solve | DONE in 137.8 s (cap 337.5 s); 172 s CPU, 3.7 s steal |
| 10-product solve (the default) | **TIMEOUT at 450 s** on a rested machine; 509 s CPU, 7.3 s steal |
| evaluation baseline + overlay | sequential by construction (one lease); each run costs a plan of the proposal's scope; the V2 closeout's production evaluation over one product completed in 40 s |
| timeouts | 1 (the 10-product default) |
| 503 / 500 / transport errors | 0 / 0 / 0 in 902 reads across five runs |
| throttling observed today | none (steal ≤ 7.3 s per run); the machine carried 1,887 s of steal from the V2 closeout's consecutive solves |

## 13. Remaining limits and the two decisions that are not engineering's

1. **The default plan does not fit its cap on any Fly CPU.** 10 products need more than 450 s of one
   core unthrottled; the cores are the same on every Fly size. The options, both honest and both
   disclosed on the plan page, are a smaller default scope (5 completes in 138 s; 10, 25 and 50 remain
   explicit choices whose measured cost the page can state) or a cap that follows the planner's own
   per-solve budgets (`solve_budget(req)` in place of `max_solve_seconds` in the job's wall-clock
   formula ≈ 900 s for 10 products, i.e. a ten-minute default plan). The first keeps the operator's
   wait at two minutes and changes what "the default plan" covers; the second keeps the coverage and
   changes the wait. This record does not choose: it is a product policy with a mathematical
   consequence (which products are compared jointly), and the brief reserves that.
2. **The machine.** On `shared-cpu-2x` any plan is one burst balance: after a 5-product plan the next
   one runs at 6.25 % for ~20 min; after a default plan, for an hour, and reads with it. Reliability
   for the sizes that fit needs a performance vCPU (§10, +$52.56 / month). Not applied: spend.
3. The per-MILP budget (up to 90 s) and the job cap are still two formulas; §9 defers reconciling
   them until decision 1 is made, because it is the same knob.
4. Local benchmarks are structural, not temporal: the laptop's arm64 HiGHS takes a different search
   path from the image's x86-64 build (and 1.14 from 1.15). Production numbers are the only timing
   evidence; a same-image, same-size benchmark machine would need spend and was not created.
5. The Fly metrics API (`api.fly.io/prometheus`) refused the organisation slug from both a session
   token and a fresh read-only token, so CPU balance was inferred from `/proc/stat` steal, which is
   the mechanism's own signature, not from Fly's balance metric.
6. Not started, unchanged: P4B V2, P6–P10, Insights (V2.1).

## 14. Verdict

The V2 operating surfaces are healthy in production and stay healthy while the planner runs. The
planner is production-healthy for 1–5 products on a rested machine and unreliable on the deployed
machine class because of its CPU budget; the default 10-product plan exceeds its cap at full speed.
By the success criteria of the brief (§42–43: the representative default plan completes reliably
inside its cap), **ZAAD V2 PRODUCTION PLANNER — BLOCKED**, on two owner decisions: the machine
(spend) and the default scope or cap (product policy). The orchestration fix in this pass (one
ordered solver lease, honest queue) stands on its own and is merged through the exact-head gate;
no runtime tag is created for an unhealthy plan path.

## 15. Addendum (2026-09-16) — the planner's scaling, root-caused by the full performance pass

Historical sections above are unchanged. The full performance pass
(`ZAAD_FULL_PERFORMANCE_PASS.md`) profiled the same plans by planner stage and lexicographic phase
and replayed the individual MILPs in isolation. Its findings correct §5.3's attribution:

* The "per-service confirmation ladder" is the service-frontier oracle (one lexicographic solve per
  service, §5.3's `alternative_value` attribution was wrong: `alternative_value` never runs on the
  sample). Only its phase-one optimum is read; its phase two (a full cost minimisation per product)
  was 57 % of an 8-product plan and is now skipped exactly (`service_only=True`, merged).
* The joint escalation solves are not intrinsically hard: 91 % of their integer columns are FEFO
  indicators between cohorts that all outlive the horizon — the pure symmetry the P2 pass removed
  on network requests and kept on the single-node formulation for the frozen record's sake. With
  the same rule applied to single-location requests (`fefo_symmetry_scope="all"`, a request field
  merged default-off) the 5-product plan takes 5 s instead of 135 s and the 8-product plan 181 s
  instead of 429 s; enabling it on the product path is the owner's call because it moves an
  equal-cost tie on the frozen fixture T.
* What remains at 8–10 products with the symmetry removed is the phase-two cost proof at the
  requested MIP gap of 1e-6 on a 4.5e7 objective — 90 s per joint solve for the last 46 units;
  at 1e-5 the 8-product plan completes in 4 s with tolerance-level differences. Not changed
  (default gap policy), evidence recorded for the owner.
* The machine (§4) is still the machine: the burst budget throttles consecutive solves exactly as
  measured; nothing in the pass changes that, and Fly was not upgraded.
