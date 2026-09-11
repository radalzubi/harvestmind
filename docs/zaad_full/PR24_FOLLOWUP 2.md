# PR 24 follow-up: selector review and PR 23 release blockers

Branch `claude/zaad-pr24-release-blockers`, stacked on PR 24
(`chatgpt/zaad-pr23-service-selector-fix`, commit `c06a54b`), which is stacked
on PR 23 (`codex/zaad-full-commercial-optimizer`). Nothing here is merged.
Autonomous purchase-order execution stays disabled on every path, including
the new asynchronous job path: every report still carries
`approval_required: true` and `executable_purchase_order: false`.

The optimizer architecture (scipy `milp` model, work-conserving settlement,
causal rolling replay, incumbent-first gated planner, SQLite shadow ledger) is
unchanged. No causal-replay, settlement or service constraint was weakened.
No number in this document was tuned against the consumed PR 23 or PR 24
final evidence (seeds 16001-16005, 19001-19005, 22001-22005). Changed
numerical behaviour was measured on three new seed splits that did not exist
before this branch: `development2` (23001), `validation2` (24001, 24002) and
`holdout2` (25001, 25002). `holdout2` is still frozen and has not been run,
because no candidate behaviour earned promotion to it.

## 1. Selector review (PR 24)

PR 24 introduced joint recovery: when the SLA targets are jointly infeasible,
rank candidates by priority-weighted shortfall instead of refusing. The
review found four defects; all are corrected in `zaad/full/planner.py` and
covered by `tests/unit/test_zaad_selector.py` plus the new suites below.

| Finding | Effect before | Correction |
|---|---|---|
| Recovery mode switched on whenever the joint solve was not `feasible`, even when another `OPTIMAL` candidate already met every target. | Strict SLA gating could be bypassed on an achievable case. | `target_jointly_feasible = feasible or (joint rows and service_ok(joint rows))`. Recovery is only entered when no candidate meets the targets. |
| "Materially better" meant `weighted_shortfall` lower by `1e-6`. | Solver noise could promote a candidate. | `material_shortfall_gap = max(1e-6, service_tolerance x sum of priorities)`, the configured service tolerance spread over every weighted service. |
| Only the `joint_recovery` candidate was considered in recovery. | A cheaper or better-recovering existing candidate was ignored. | Every `OPTIMAL` candidate is ranked (`recovery_ranking` in the report); the best materially-better one is chosen, otherwise the incumbent is retained. |
| The out-of-model stress gate required every service to be no worse than the incumbent, which contradicts priority-weighted recovery. | Every recovery was rejected at stress time. | In recovery mode the gate is physical feasibility, economic downside bound, material weighted-shortfall improvement, and priority consistency (no higher-priority service loses so a lower-priority one gains). |

Behaviour as now implemented:

- Targets achievable: strict gating. A candidate is accepted only if it meets
  every service target, passes physical settlement, stays within the economic
  downside bound, and passes stress confirmation.
- Targets not jointly achievable: recovery. Candidates are ranked by
  priority-weighted shortfall; the winner must improve by the material gap,
  be physically feasible, be within the downside bound, be priority consistent
  and pass stress confirmation, or the incumbent is retained.
- Every accepted plan is `PENDING_REVIEW` for a human. Nothing executes.

## 2. Blocker 1: numerical PO dust

One unit-aware zero policy now lives in `zaad/full/tolerance.py` and is used by
extraction (`model.py`), replay (`replay.py`) and settlement (`settlement.py`):

- `dust_threshold(pack) = max(1e-9, 1e-6 x smallest declared pack unit)` where
  the pack unit is the smallest of the source's minimum, multiple, case, pallet
  and transport multiples; a continuous source counts as one unit.
- `po_closed(po, source)`: an open PO whose remaining quantity is dust is
  closed and skipped by the amendment logic in all three layers.
- Purchases, transfers and amendments below their own threshold are dropped
  at extraction, not carried into replay, and not judged by settlement.

Material orders are never erased: the threshold is one millionth of the
smallest declared pack, and `tests/unit/test_zaad_tolerance_and_tail.py`
checks that a whole case is kept, that a `4e-7`-unit residual (the exact
PR 23 failure size) is closed, and that closing does not change the material
plan.

## 3. Blocker 2: post-horizon financial tail

`model.py` now collects every committed payment that falls after the horizon
(the `tail`) and adds a terminal solvency row at the last period:
`cash - minimum_cash + credit_headroom >= post-horizon payments`. Settlement
performs the same check on the realised plan and raises
`PhysicalViolation("post-horizon obligations ... exceed terminal financing
headroom")` when it fails. Reports carry `terminal_liability_reserve` and
`terminal_financing_headroom`. Demo candidate statuses were compared before and
after the row on the shipped fixtures: unchanged, so the constraint is not
silently binding on the reference cases. An in-horizon cash result is still
not full affordability certification; it is now affordability up to the
declared credit line for known committed obligations.

## 4. Blocker 3: downward demand shift

Four adaptation modes are selectable on `Request.demand_adaptation`:

| Mode | Rule |
|---|---|
| `symmetric` (default, frozen PR 23 rule) | Two-sided clipped CUSUM, threshold 4.5 both ways. |
| `asymmetric` | Downward threshold 6.5 and a two-observation confirmation; upward unchanged. |
| `soft` | Blend pre- and post-change fits; weight `post/12` downward, `post/6` upward. |
| `ensemble` | Decision-loss-weighted blend of the frozen and changepoint fits. |

Study design: `scripts/run_zaad_full_benchmark.py --split development2
--adaptation <mode>` on the decrease, increase and stable demand cells at
target 0.95 for `frozen_forecast`, `stochastic` and `gated`; paired cost and
service comparison by `scripts/summarize_zaad_adaptation.py`. Every run,
including every loss, is in `docs/zaad_full/evidence/adaptation/`.

Development2 (seed 23001, 4 decrease pairs per method), modeled cost versus
symmetric, `gated` method:

| Mode | Losses | Median | Worst | Service breaches |
|---|---|---|---|---|
| asymmetric | 3 / 4 | +0.94% | +3.96% | 2 -> 2 |
| soft | 3 / 4 | +0.49% | +15.17% | 2 -> 2 |
| ensemble | 3 / 4 | +1.72% | +18.48% | 2 -> 2 |

`stochastic` shows the same direction (soft and ensemble lose 4 / 4). Increase
cells: asymmetric identical, soft and ensemble worse. Stable cells: identical.

Validation2 (seeds 24001, 24002; only asymmetric was carried forward because
soft and ensemble already lost on development2):

| Method, demand | Pairs | Losses | Median | Worst | Best | Breaches |
|---|---|---|---|---|---|---|
| gated, decrease | 8 | 2 | 0.00% | +4.71% | -3.81% | 1 -> 3 |
| stochastic, decrease | 8 | 2 | 0.00% | +12.24% | -6.09% | 3 -> 2 |
| gated, stable | 18 | 3 | -1.82% | +0.72% | -12.16% | 5 -> 5 |
| stochastic, stable | 18 | 6 | -1.35% | +1.26% | -7.98% | 6 -> 8 |
| any, increase | 8 | 0 | 0.00% | 0.00% | 0.00% | unchanged |

Reading: the asymmetric rule mostly reduces false downward alarms on stable
demand (a modest median cost gain for `gated`) but does not improve the
decrease cells it was built for, and it adds service breaches for `gated`
there (1 to 3). Two seeds and eight pairs are not enough to promote a change
that is neutral in median and adverse in breaches. No mode is adopted.
`symmetric` remains the default; the other modes stay opt-in with their
adverse evidence retained. `holdout2` was not consumed.

Root cause of the PR 23 "downshift harm" finding, traced on development2 and
confirmed on validation2 (where `gated` loses to `frozen_forecast` on modeled
cost in 7 of 8 decrease pairs even under the frozen symmetric rule): the harm
is not in the forecast. The gated controller alternates between the
`stress_network` candidate (accepted as `PENDING_REVIEW`) and the
`projected_base_stock_proxy` (`RETAIN_INCUMBENT` after "Out-of-model stress
confirmation rejected"), and the proxy front-loads large buys in the first
periods, immediately before an unforeseeable drop. Plain `stochastic` beats
`frozen_forecast` on the same cells. Fixing this means changing how the gated
planner treats proxy candidates under stress rejection, which is a selector
policy change outside this brief and outside "do not redesign the optimizer".
It is recorded as an open blocker, not resolved.

## 5. Blocker 4: order-level OTIF

- `OrderLine.revision` and `superseded_by`; a superseded or cancelled line is
  ignored for service and for allocation (`open_quantity` is what remains).
- `Service.metric` gains `order_otif`: a multi-line order counts only when
  every open line is complete and on time. `order_fill` and `order_otif` share
  one `order_full` variable per order and scenario across services, so two
  services cannot claim the same order under different definitions.
- Settlement reports an `orders` summary (`complete_order_rate`,
  `order_otif_rate`, partial and late line counts) and per service
  `order_otif`, `quantity_fill`, `lines`, `partial_lines`,
  `late_complete_lines`. Receipts after the horizon are "unobserved", not
  "on time".
- Late receipts against a line that was already due are late, never
  retroactively on time.

Covered by `tests/unit/test_zaad_otif_and_adaptation.py`. What is still
missing is adversarial operator-led testing with real revision, cancellation
and credit-note histories; the semantics are defined and enforced, not
field-validated.

## 6. Blocker 5: bounded asynchronous jobs

`zaad/full/jobs.py` adds `JobStore` (SQLite, per-operator rows with seed,
config hash, engine version, timeout, request and result JSON) and
`JobRunner` (one spawned process per job, bounded worker semaphore, active
and daily quotas, wall-clock timeout, cancellation by terminate,
`shutdown()`). API: `POST /api/zaad/network/jobs` (202 or 429 on quota, 403 on
operator mismatch, 413 above `LARGE_LIMITS` = 200 SKUs, 400 sources,
200 services, horizon 26, 32 scenarios, 12 stresses), `GET .../jobs`,
`GET .../jobs/{id}`, `DELETE .../jobs/{id}`. Configuration: `ZAAD_JOB_STORE`
(required, 503 otherwise), `ZAAD_JOB_WORKERS`, `ZAAD_JOB_QUOTA_ACTIVE`,
`ZAAD_JOB_QUOTA_DAILY`, `ZAAD_JOB_MAX_SECONDS`. Small requests keep using the
synchronous `/plan` endpoint unchanged. Tenant isolation: another operator's
token gets 404 on read and an empty list. Results are reproducible from the
stored seed and config hash. Covered by `tests/integration/test_zaad_jobs.py`
and a real-HTTP smoke against uvicorn (see VERIFICATION).

Not done: profiling of dense multi-scenario workloads at the limits above on
production-sized machines. The boundary exists; the capacity claim does not.

## 7. Blocker 6: inherited static-security findings

| Finding | Resolution |
|---|---|
| `api/serve.py` B104 all-interface bind | Bind scope is declared by `HARVESTMIND_BIND_HOST`; loopback binds loopback only, the wildcard is an explicit deployment opt-in (Dockerfile and fly.toml set it) and is refused by `api.dependencies` unless authentication is required. Annotated, not suppressed globally. |
| `api/worker.py` B310 urlopen | Target origin must be http(s) and the path must start with `/jobs/internal/`; annotated at the call. |
| `infrastructure/fly_machines.py` B310 urlopen | https only and a `/machines` path; annotated at the call. |

Bandit `-ll` on `api`, `infrastructure`, `zaad`: no medium or high findings.
Total `nosec` annotations on those paths went from 13 on the PR 24 base to 18;
the five additions are the three above, the second bind line, and the
column-literal `UPDATE` in `jobs.py`. Each states its reason inline.

## 8. Verdict

**NEEDS FURTHER ENGINEERING.**

Resolved on this branch: selector defects, PO dust policy, post-horizon
financing, order-level OTIF semantics, bounded asynchronous jobs, the three
static-security findings.

Still blocking a real shadow pilot:

1. Downward demand shift is not improved. The traced cause is gated-planner
   proxy chattering under stress rejection, which this brief did not permit
   changing. Symmetric stays default with adverse evidence on file.
2. No prospective real operator data has been through the pipeline; every
   number above is from synthetic worlds.
3. Order-level OTIF has not been exercised against real revision and
   cancellation histories.
4. The asynchronous path has not been load-profiled at its declared limits.
5. Inherited evidence gaps from PR 23 remain: uncalibrated ETA tails,
   duplicated disruption mappings, no independent MEIO comparator.
