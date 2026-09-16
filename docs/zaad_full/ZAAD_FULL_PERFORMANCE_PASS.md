# ZAAD full performance pass (2026-09-16) — live evidence record

Performance-engineering pass over the whole application and the planner, on the existing Fly
machine (no upgrade), after the V2.1A Insights release. The objective: find and remove avoidable
bottlenecks before spending on infrastructure. Nothing that computes a decision is changed unless
the change is proven decision-equivalent through the frozen gates; the default scope, the job cap,
the MIP gap, the objective, the phase and service semantics are not changed here.

Four problems are kept apart: FRONTEND, DATA / API, ORCHESTRATION, OPTIMIZER / MILP. Every finding
is classified as one of FRONTEND, API, DATABASE, SERIALIZATION, JOB SYSTEM, MODEL BUILD, SOLVER,
FORMULATION, INFRASTRUCTURE, UNKNOWN. Every number below has the measurement behind it; local
numbers are **STRUCTURAL / RELATIVE BENCHMARK**, production numbers are **PRODUCTION PERFORMANCE**.

## 0. Starting state — verified

| item | value |
|---|---|
| branch | `perf/zaad-full-performance-pass` from `main` `b818fd3801fa468144b0cba1906e9142b0c2108e` |
| production runtime | `13dde49` (Merge PR #84), Fly app `zaad-api` v28, image tag `canonical-13dde49`, digest `sha256:374b4e91…` (full digest in the ledger's V2.1A entry) |
| Fly machine | `0804e0dfd1e948` (fra), `shared-cpu-2x`, 2,048 MB, one machine, volume `vol_4m3pel5k9mdm95gv`; `MemTotal` 2,015,640 kB |
| production stack | Python 3.12.14, highspy 1.15.1, scipy 1.18.1, numpy 2.5.3, duckdb 1.5.5, x86-64 (measured on the machine in the recovery pass; the image is unchanged) |
| local stack (structural benchmarks) | `venv312`: Python 3.12.14, highspy 1.15.1, scipy 1.18.1, numpy 2.5.3, duckdb 1.5.5, **arm64** (Apple M4 Pro, 12 cores, 24 GB) — same versions, different architecture: search paths differ, timings are relative only |
| CI runners | GitHub `ubuntu-latest` x86-64 (the frozen gates run there) |
| Vercel | production from `main`, same tree as the runtime |
| production machine at the start of the pass | idle since the demo loads of 03:5x UTC; `/proc/stat` 12:16 UTC: user 385 s, steal 2,130 s since boot (uptime 8.6 h), load 0.00, `MemAvailable` 1.35 GB → rested |
| planner state | BLOCKED at the default scope (10 products > 450 s cap unthrottled); recovery record `PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md` |

Tools (all outside `zaad/`): `scripts/production_solve_benchmark.py` (extended in this pass: stage
attribution per MILP from the planner call site, lexicographic phase, per-stage time, `--dump-mps`),
`scripts/production_plan_probe.py` (+ Insights summary read), `scripts/production_machine_sampler.py`
(new: `/proc` on the Fly machine every N s — CPU / steal / load / memory / per-process RSS and
threads), `scripts/milp_replay.py` (new: one dumped MILP through highspy in isolation with the log
on, options one at a time), `scripts/insights_scale_qa.py`.

## 1. Phase A — baseline reproduced (unchanged runtime `13dde49`, no code change)

### 1.1 Local STRUCTURAL / RELATIVE BENCHMARK (`production_solve_benchmark --products 1,2,3,4,5,8,10`, sample vault, seed 7, arm64 venv312)

The product's plan request over the ranked top-N products of the 150-product sample (every phase
asked for; no phase block declared by the data, so no P3 / P4 / P5 / P4B model enters), horizon 12,
3 scenario worlds (+1 stress), one location, one source and one service per product. Job cap =
`min(1800, 15 × (10 + N) × 1.5)`; per-MILP budget = `solve_budget(req)` (66.3 s at 5, 90 s cap ≥ 8).

| products | plan wall | solver core (share) | MILPs | largest MILP cols / rows / integer / binary / nnz | time-limited MILPs | per-MILP budget | peak RSS | status | job cap |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.5 s | 0.4 s (80 %) | 14 | 2,361 / 2,446 / 735 / 723 / 12,977 | 0 | 19.5 s | 524 MB | RETAIN_INCUMBENT | 248 s |
| 2 | 3.0 s | 2.8 s (93 %) | 16 | 4,624 / 4,701 / 1,469 / 1,445 / 25,708 | 0 | 31.2 s | 658 MB | RETAIN_INCUMBENT | 270 s |
| 3 | 6.5 s | 6.2 s (96 %) | 18 | 6,887 / 6,956 / 2,203 / 2,167 / 38,463 | 0 | 42.9 s | 658 MB | RETAIN_INCUMBENT | 292 s |
| 4 | 85.1 s | 84.7 s (99 %) | 20 | 9,582 / 9,631 / 3,081 / 3,033 / 54,717 | 1 | 54.6 s | 689 MB | RETAIN_INCUMBENT | 315 s |
| 5 | 135.1 s | 134.6 s (100 %) | 20 | 11,125 / 11,166 / 3,575 / 3,515 / 61,545 | 2 | 66.3 s | 1112 MB | RETAIN_INCUMBENT | 338 s |
| 8 | 429.2 s | 428.2 s (100 %) | 28 | 17,621 / 17,626 / 5,681 / 5,585 / 97,332 | 2 | 90.0 s | 1219 MB | RETAIN_INCUMBENT | 405 s |
| 10 | **> 2 h 12 min, stopped** (never reached the report; the cap is 450 s) | — | — | 22,132 / 22,094 / 7,134 / 7,014 / 122,606 (structure-only build, §3) | — | 90.0 s (cap) | — | — | 450 s |

Everything outside the solver is under one second at every size (settlement / evaluate 0.01–0.1 s,
forecast fits, world draws, screen, plan shape, `report_json`, job-store write: all ≤ 0.02 s; the
workspace read 0.4–0.7 s once per plan). **This confirms the recovery record: the solver is
94–100 % of a plan, and nothing in SQL, JSON, request conversion or serialisation is worth a line
of optimizer work.** The 10-product structural run on the released formulation was stopped after 2 h 12 min without
reaching the report (every joint phase at its 90 s cap and 20 frontier solves of up to 90 s each,
repeated over the ladder); its cap is 450 s.

### 1.2 Where the time goes, by planner stage and lexicographic phase (baseline, local)

Stage = the planner call that owns the MILP (read from the call site; nothing in `zaad/`
instrumented); phase = `lex1` (minimum priority-weighted unmet), `lex2` (cost under that optimum),
or `single` (one objective).

| products | stage | MILPs | wall | lex1 | lex2 | time-limited | share of plan |
|---|---|---|---|---|---|---|---|
| 2 | joint_recovery | 2 | 0.5 s | 0.3 s | 0.2 s | 0 | 18 % |
| 2 | joint_fitted | 2 | 1.8 s | 1.5 s | 0.3 s | 0 | 60 % |
| 2 | service_frontier | 4 | 0.2 s | 0.1 s | 0.1 s | 0 | 8 % |
| 5 | base_stock_proxy | 1 | 0.2 s | 0.0 s | 0.0 s | 0 | 0 % |
| 5 | joint_recovery | 1 | 66.3 s | 66.3 s | 0.0 s | 1 | 49 % |
| 5 | joint_fitted | 1 | 66.3 s | 66.3 s | 0.0 s | 1 | 49 % |
| 5 | service_frontier | 10 | 1.6 s | 0.9 s | 0.7 s | 0 | 1 % |
| 8 | base_stock_proxy | 1 | 2.2 s | 0.0 s | 0.0 s | 0 | 0 % |
| 8 | joint_recovery | 2 | 89.8 s | 1.2 s | 88.6 s | 1 | 21 % |
| 8 | joint_fitted | 2 | 89.9 s | 1.0 s | 88.9 s | 1 | 21 % |
| 8 | service_frontier | 16 | 246.0 s | 2.7 s | 243.2 s | 0 | 57 % |

Reading: at 2 and 3 products every joint phase one is optimal at the root node in 0.3–1.5 s; at
**5 products both joint phase ones stop at their 66 s budget with gap 0.59–0.62 after 30–41 k
nodes**, phase two never runs (it runs only after a proven phase one) and the candidates enter as
`FEASIBLE_TIME_LIMIT`; at **8 products the phase ones are cheap again (1.0–2.7 s) and the plan is
phase two: the two joint cost phases at the 90 s cap (gap 4.5e-3 and 1.2e-6) plus the per-service
frontier's cost phases, 243 s = 57 % of the plan, whose result the planner never reads (§4).**
The six network candidates are INFEASIBLE in ≤ 0.03 s each (the sample's service floors cannot be
met from the opening position), so every plan escalates to the joint solves; the base-stock proxy
and the incumbent solve cost 0.1–2 s.

### 1.3 PRODUCTION PERFORMANCE (`production_plan_probe --self-serve`, Fly `shared-cpu-2x`, rested, one plan at a time, machine sampled every 12 s)

Rested: idle since 04:00 UTC; `/proc/stat` 12:18 UTC user 385.7 s, steal 2,129.8 s since boot (the
demo loads of the night), load 0.00. Runs at 12:18 (1 product), 12:19 (2), 12:20:49 (5).

| products | job cap | queued | run | outcome | reads while solving (median / p95 / max s) | errors | machine CPU over the run | solver child RSS max | idle medians |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 248 s | 0.01 s | **4.3 s** | DONE, RETAIN_INCUMBENT | health 0.26 / 0.28 / 0.28 · summary 0.34 / 0.36 / 0.36 · inventory 0.35 / 0.39 / 0.39 · POs 0.33 / 0.33 / 0.33 · readiness 0.47 / 0.53 / 0.53 · insights 0.68 / 0.75 / 0.75 · job 0.35 / 0.47 / 0.47 | 0 | user +28 s, steal +0.9 s | 549 MB | idle: health 0.37 · summary 0.28 · inventory 0.32 · purchase_orders 0.39 · readiness 0.39 · insights_summary 0.59 |
| 2 | 270 s | 0.01 s | **29.7 s** | DONE, RETAIN_INCUMBENT | health 0.26 / 0.37 / 0.37 · summary 0.35 / 0.38 / 0.38 · inventory 0.39 / 0.48 / 0.48 · POs 0.43 / 0.47 / 0.47 · readiness 0.47 / 0.70 / 0.70 · insights 0.75 / 0.88 / 0.88 · job 0.27 / 0.51 / 0.51 | 0 | user +56 s, steal +1.1 s | 571 MB | idle: health 0.22 · summary 0.25 · inventory 0.32 · purchase_orders 0.27 · readiness 0.36 · insights_summary 0.55 |
| 5 | 338 s | 0.00 s | **139.0 s** | DONE, RETAIN_INCUMBENT | health 0.28 / 0.33 / 0.37 · summary 0.34 / 0.41 / 0.45 · inventory 0.38 / 0.45 / 0.50 · POs 0.38 / 0.45 / 0.47 · readiness 0.52 / 0.64 / 0.65 · insights 0.83 / 0.90 / 1.08 · job 0.23 / 0.35 / 0.54 | 0 | user +182 s, steal +3.4 s | 595 MB | idle: health 0.24 · summary 0.34 · inventory 0.35 · purchase_orders 0.31 · readiness 0.40 · insights_summary 0.67 |

The API process held 531 MB RSS / 12 threads throughout; the solver child (a `multiprocessing`
spawn) showed **16 threads** and at most 610 MB; `MemAvailable` never fell below 1,103 MB of
2,015 MB; load average peaked at 1.41. The three runs spent 270 s of user CPU of the 500 s burst
balance (user 38,573 → 65,637 cs), so the 8- and 10-product baselines are run only after the
balance has refilled (0.125 s / s → ≥ 36 min idle), one at a time — §1.4.

The reads stay in their idle band while the solver holds one vCPU, as in the recovery record; the
one read outside 0.5 s is the **Insights summary (0.55–0.67 s idle, 0.75–0.83 s median during a
solve, 1.08 s max)** — the largest server-side aggregation the workspace makes (§2).

### 1.4 Production 8 products (rested), and the 10-product baseline

**8 products, run at 12:56:04 UTC after 32 idle minutes** (`/proc/stat` before: user 664.3 s,
steal 2,138.1 s; load 0.00): job cap 405 s, queued 0.006 s, **TIMEOUT — "exceeded 405 s wall
clock", run 407.7 s, no report.** Machine CPU over the run: user +485 s, steal +10 s (the balance
ran out only in the last seconds: 32 minutes refill ≈ 240 s on top of the ~230 s left after the
morning's runs). Solver child RSS max 704 MB, 17 threads; `MemAvailable` min 995 MB; load 1.52.
Reads while solving (median / p95 / max s): health 0.24 / 0.30 / 0.62, summary 0.31 / 0.39 / 0.42,
inventory 0.40 / 0.48 / 0.85, purchase orders 0.36 / 0.44 / 0.58, readiness 0.49 / 0.62 / 0.64,
Insights summary 0.75 / 0.88 / 0.93, job 0.24 / 0.32; 0 errors in 259 reads. So the released
planner's cap holds on production up to 5 products and **fails from 8 products** on a rested
shared machine — the local 429 s structural number is in the same place.

**10 products** is not re-run on production for the baseline: the recovery record measured it on
the same planner code on a rested machine 2026-09-15 (TIMEOUT at 450 s, 509 s of CPU, 7.3 s steal;
its §3.1), the image since then changed nothing under `zaad/` that computes a plan, and the run
would spend the whole burst balance (≥ 1 h of idle to refill) that the post-deploy verification
needs. The local 10-product structural row (§1.1) is recorded when its run ends.

## 2. Phase B — site, API and data-scale profile

### 2.1 Server-side read latency by catalogue size (`scripts/workspace_scale_qa.py`, in process, arm64, median of 5, ms)

150 = the sample (371 k customer-order rows); 10 k and 50 k = the QA scale fixtures (0.52 M / 2.6 M
order rows, 120 k / 600 k purchase-order rows). Every workspace read is bounded and server-side;
the last columns are the planner's workspace read (`/request/from-workspace`) scoped to 200 products.

| products | summary | inventory | inv. sort by value | inv. filter category | inv. search | inv. page 20 | inv. 200 by value | SKU detail | POs | PO search | PO detail | readiness | search | workspace read (200 SKUs) | its payload |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 150 | 10 | 19 | 18 | 19 | 19 | 18 | 18 | 22 | 12 | 14 | 1 | 41 | 13 | 660 | 3.6 MB |
| 10,000 | 21 | 34 | 34 | 58 | 58 | 33 | 33 | 40 | 29 | 62 | 2 | 86 | 24 | 3634 | 6.6 MB |
| 50,000 | 66 | 103 | 100 | 300 | 303 | 101 | 101 | 105 | 111 | 120 | 2 | 155 | 53 | 13960 | 6.6 MB |

Insights aggregations (V2.1A release, same fixtures): every tab under 800 ms median at 50 k
products (summary 437 ms worst) — `FABLE_V2_1_RELEASE_AUDIT.md` §7, not re-run.

**Findings (API / DATABASE / SERIALIZATION).**

* Every operating read (Home summary, Inventory with any sort / filter / search / page, PO list,
  detail drawers, readiness, search) is **≤ 60 ms at 10 k and ≤ 310 ms at 50 k products** with a
  payload ≤ 107 KB. The DuckDB queries are bounded (`LIMIT ? OFFSET ?`, one `count(*)`), no N+1,
  no full-table sort into Python. Nothing to change.
* **The planner's workspace read is the outlier: 655 ms and a 3.6 MB JSON body for the 150-product
  sample, 3.6 s / 6.6 MB at 10 k scoped to 200 products, 14 s at 50 k.** SQL is 60 ms of it; the
  rest is Python-side construction of the compact contract (per-row pandas access and pydantic
  validation of the history and shipment-history rows). Scoping the SQL reads to the requested SKUs
  is exact (request fingerprint identical) but saves nothing measurable at 10 k (3.74 → 3.67 s) —
  the cost is not in the scan. Of the 3.6 MB, `shipment_history` is 1.57 MB and `history` 0.77 MB:
  planner inputs the browser never reads but downloads on every workspace open and uploads again
  when it submits a plan. Classified API + SERIALIZATION; the accepted change is compression (§6);
  the read's Python cost at 10 k+ is DEFERRED with the measurement.

### 2.2 The web, measured on production (`zaadsupply.com`, Vercel production build, `api.zaadsupply.com`, the DEMO workspace `op_eaee6ee4`, 36 products, cold Home)

| phase | what | when (ms after navigation) |
|---|---|---|
| document | TTFB 40 ms, DOMContentLoaded 132 ms, load 421 ms; 14 scripts, 329 KB | 0–421 |
| session | `GET /me` | 424 → 573 (149 ms) |
| catalogue size | `GET /workspace/summary` | 577 → 802 (225 ms) |
| **workspace read** | `GET /network/request/from-workspace` (1.18 MB uncompressed for 36 products) | **803 → 2,508 (1,705 ms)** |
| after the read | directory, plan jobs, evaluation jobs (147–171 ms each, parallel) | 2,518 → 2,690 |
| Home content | Insights summary 687 ms, history 363 ms, summary(as_of) 414 ms, drafts 359 ms, readiness 564 ms (parallel) | 2,539 → 3,226 |
| page usable | | ≈ 3.2 s |

**Findings (FRONTEND / API).** The workspace read is both the largest transfer (1.2 MB here, 3.6
MB for a 150-product catalogue, uncompressed — the API sends no `Content-Encoding`) and the head
of a waterfall: three serial round trips precede it and every other read on Home waits for it,
although only the plan-dependent parts need it. In the local dev server (React StrictMode) every
request appears twice; that is a development artefact, absent in the production build above.
Pages read their own bounded endpoints (Inventory 3 facet reads + 1 page read; Purchase orders 1;
Insights 1–3 per tab, re-fetched on tab change with 4–25 KB payloads; History 1; Diagnostics 1),
lists are paginated server-side (50 rows), charts receive ≤ 400 points. No client-side aggregation
of raw rows, no non-virtualised large list. Accepted changes: gzip on the API (§6); starting the
directory / jobs reads and the Home reads that do not depend on the workspace request in parallel
with it (§6). DEFERRED: a compact workspace read for display and server-side plan submission by
scope (removes the 3.6 MB upload on plan submit) — an API-contract change, recorded for the owner.

## 3. Phase C — model growth (largest MILP of the plan, baseline formulation)

| products | columns | rows | integer | binary | non-zeros | worlds | coupling components (sizes) | supplier-capacity couplings | frontier solves | joint lexicographic solves | MILPs per plan |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2,361 | 2,446 | 735 | 723 | 12,977 | 4 | 1 [1] | 0 | 2 | 4 | 14 |
| 2 | 4,624 | 4,701 | 1,469 | 1,445 | 25,708 | 4 | 2 [1, 1] | 0 | 4 | 4 | 16 |
| 3 | 6,887 | 6,956 | 2,203 | 2,167 | 38,463 | 4 | 3 [1, 1, 1] | 0 | 6 | 4 | 18 |
| 4 | 9,582 | 9,631 | 3,081 | 3,033 | 54,717 | 4 | 3 [2, 1, 1] | 1 | 8 | 4 | 20 |
| 5 | 11,125 | 11,166 | 3,575 | 3,515 | 61,545 | 4 | 4 [2, 1, 1, 1] | 1 | 10 | 2 | 20 |
| 8 | 17,621 | 17,626 | 5,681 | 5,585 | 97,332 | 4 | 6 [3, 1, 1, 1, 1, 1] | 2 | 16 | 4 | 28 |

Dimensions grow linearly in the product count (≈ 2,200 columns, 2,200 rows and 700 integer columns
per product on the 4-world model); the solve count grows as 14 + 2 × N (two per-service frontier
phases per product). Built and not solved (`--structure-only`, every model the plan would solve): **10 products
22,132 columns / 22,094 rows / 7,134 integer (7,014 binary) / 122,606 non-zeros, 7 components, 3
supplier-capacity edges, 20 MILPs; 15 products 34,611 / 34,501 / 11,204 / 195,653 nnz, 8
components, 7 edges, 25 MILPs; 25 products 54,901 / 54,519 / 17,704 / 304,148 nnz, 8 components,
17 edges, 35 MILPs** — 0.7 / 1.2 / 2.5 s to build all of them. Linear in the product count.

**What the integer columns are** (5 products, joint recovery model, 3,575 integers): `fefo` 3,264
(91 %), `depleted` 240, `case` (pack multiples) 60, `po_option` 11. Every `fefo` indicator here sits
between two cohorts that both expire at periods 52–66 against a 12-period horizon: the released P2
rule already omits exactly these indicators on network requests as a pure symmetry
(`FEFO_SYMMETRY_ELIMINATION`, `evidence/p2/perf/P2_PERF_DIAGNOSIS.md`), and keeps the single-location
formulation verbatim so the frozen P1 decision path reproduces bit for bit. No formal complexity
claim is made from six points; the descriptive fit is linear dimensions, superlinear solve time
driven by the indicator symmetry (§4).

## 4. Phase D — the three bottlenecks, with the evidence

**#1 — FORMULATION: the FEFO indicator symmetry on single-location requests.** 3,264 of the 3,575
integer columns of the 5-product joint model are `fefo` indicators between cohorts that all expire
at periods 52–66 against a 12-period horizon (§3). Replaying the 5-product joint phase-one MILPs
from their MPS dumps (`scripts/milp_replay.py`, the exact arrays HiGHS saw): with the `fefo` family
deleted, `joint_recovery` solves at the root in **0.08 s** and `joint_fitted` in **0.06 s**, both
proven optimal at the same objective values (3,464.54 and 3,331.79) the full models reach only when
they reach them at all (66 s, time-limited, gap 0.59–0.62). Through the planner, the released P2
window rule extended to single-location requests without sector physics (`fefo_symmetry_scope=
"all"`) takes the 5-product plan from **135.1 s to 5.1 s** (integer columns 3,575 → 311, zero
time-limited MILPs, status unchanged) and the 8-product plan from 429 s to 226 s. Root cause of the
10-product case, first part: the planner branches on a symmetric labelling of interchangeable
cohorts, which the LP relaxation cannot resolve (weak big-M rows, M = capacity / volume ≈ 10⁹).

**#2 — SOLVER: the lexicographic cost phase proving the last 10⁻⁶.** With the symmetry gone, the
8-product plan's remaining 180 s is the two joint **phase-two** solves (cost under the fixed service
optimum), each stopping at the 90 s cap with a gap of 1.28e-6 and 1.92e-6 against the requested
1e-6 — i.e. ~90 s each proving the last 46 units of a 45,000,000 objective. At `solver_mip_gap`
1e-5 the same plan completes in **4.0 s** with the joint objectives within 2 and 15 units of the
1e-6 run and the recovery-guidance quantities differing by one pack on four lines (§5, E7); at 1e-4
and 1e-3 the objectives and the gates move (economically visible) — rejected. This is the second
part of the 10-product root cause: proof at 1e-6 relative on a 4.5e7 objective, four times per plan.
Not changed (default MIP gap: owner authorisation, §19 of the brief); the evidence is here.

**#3 — MODEL BUILD / SOLVER: the per-service frontier's discarded cost phase.** The frontier
oracle (`solve(req, deterministic, service_first=service.id)`) answers one question — the best
modeled unit fill of that service alone — and reads only `projected_service[service]`, which is the
phase-one optimum by construction (phase two is constrained to it within 1e-7). Its phase two, a
full cost minimisation of the whole scope's model per product, was **243 s of the 429 s 8-product
plan (57 %)** and 45 s of the 226 s FEFO-reduced one. Skipping it (`service_only=True`) is an
exact removal of redundant computation: 8 products **429 s → 186 s** on the released formulation,
decisions IDENTICAL at 1–5 products against the unchanged-model reports (every compared field,
tolerance 1e-6; §7), canonical regression PASS, P1 invariants 720 clean.

What was **not** the bottleneck: model construction, settlement, forecasting, worlds, report
serialisation, the job store, the API's reads, the database (§1.1, §2). Warm start: the incumbent
seed *does* poison the 5-product joint phase one on the released formulation (seeded replay 66 s
time-limited at gap 0.62 vs 5.0 s optimal unseeded, §5 E2; with `warm_start=false` the 5-product
plan takes 54 s instead of 135 s), but with the FEFO symmetry removed the seed costs ≤ 0.1 s to
complete and the seeded solves are optimal at the root — the FEFO fix supersedes a warm-start
policy change, which would itself be a search-path change with its own tie exposure. Not changed.

### 4.1 The 10-product case answered (§13 of the brief)

Why 10 products cost dramatically more than 5: (a) the joint escalation models carry ~650 symmetric
FEFO indicators per product (3,264 at 5, ~6,500 at 10) whose LP relaxation is loose (big-M 10⁹), so
the branch-and-bound over the phase-one service objective explodes (gap 0.6 after 30–41 k nodes at
5 products — already at the budget) and every phase two then starts from an unproved phase one or
not at all; (b) the two phase-two cost proofs at 1e-6 on a 4.5e7 objective each take their 90 s
cap from 8 products up; (c) the frontier adds two full-scope solves per product, 12.8–73 s each at
8, whose second half is never read. Not the cause: model dimensions themselves (linear, §3),
scenario replication (4 worlds, unchanged 1→10), shared supplier constraints (3 edges at 10
products; the joint models solve at the root once the symmetry is removed), the confirmation
ladder (settlement only, no MILP, < 0.2 s), service-floor infeasibility (the six candidate solves
are INFEASIBLE in ≤ 0.03 s each), numerical tolerances (residuals ≤ 1e-9), the time-budget
interaction (a symptom: the caps are hit because of (a)–(c)).

### 4.2 Confirmation ladder (§14) and lexicographic implementation (§15)

The "confirmation ladder" of the recovery record is two things: the per-service frontier oracle
(one lexicographic solve per service; the only consumer is `best_modeled_individual_unit_fill`,
§4 #3) and the independent / stress / alternatives confirmation, which is settlement on new world
draws — no MILP, 0.01–0.1 s per evaluation, nothing to remove. Lexicographic phases are two
sequential MILPs on the same `Linear` (phase one with the service objective; phase two adds one row
`service objective ≤ optimum + 1e-7` and re-solves on the cost objective, seeded with the phase-one
point on the highspy route). A single weighted objective is **not** an exact substitute (unmet
demand is continuous, no finite weight reproduces the lexicographic order); persistent model reuse
would save only the matrix build (< 0.1 s per phase). The phase-two seed is already in place. No
change to the priority hierarchy.

### 4.3 Decomposition (§18) — DEFER

The coupling map (§3) shows 7 components at 10 products with 3 supplier-capacity edges; the joint
lexicographic objective pools unmet demand across every product, so component-wise solving is a
different optimisation in phase two (recovery record §6). A coordinated exact decomposition would
have to reproduce the pooled phase-one optimum (a sum of independent minima only when no shared
constraint binds — a data-dependent condition the planner would have to certify per review) and
the pooled phase-two feasible set (the trade of unmet between products at equal total), which is
the global coupling itself. With the symmetry removed the joint phase-one solves at the root in
0.1 s at 8 products, so the decomposition would buy nothing on phase one and would change phase
two. Deferred: no equivalence, no benefit at the measured sizes.

## 5. Phase E / F — experiment register (one variable at a time)

| # | experiment | hypothesis | baseline | change | speed effect | decision effect | risk | verdict |
|---|---|---|---|---|---|---|---|---|
| E1 | replay 5-product `joint_recovery` phase one from its MPS, unseeded, default options | the model is not intrinsically hard | 66 s time-limited, gap 0.62, 30,737 nodes (in the planner, seeded) | isolate the MILP | **5.0 s OPTIMAL, 1,301 nodes**, root bound = optimum | same objective (3,464.54) | none (diagnostic) | evidence |
| E2 | E1 with the planner's incumbent seed (`setSolution`) | the seed changes the search | 5.0 s | seed the replay | **66 s time-limited, gap 0.62, 23,759 nodes**, incumbent stuck at 9,088 | n/a | — | evidence: the seed poisons this model class |
| E3 | E1 with the `fefo` family deleted (columns + their rows) | the FEFO indicators are the hard part | 5.0 s (008), 66 s TL (009) | drop 3,264 / 2,448 indicators | **0.08 s / 0.06 s at the root**, same objectives | same phase-one optimum | none (diagnostic) | evidence → E5 |
| E4 | 5-product plan with `warm_start=false` (request override) | remove the seed | 135.1 s, 2 TL | no seed | 53.9 s, 0 TL | not compared further (superseded) | search-path change, tie exposure | DEFER (superseded by E5) |
| E5 | `fefo_symmetry_scope="all"` through the planner (released P2 window rule on single-location, physics-free requests) | exact symmetry removal | 1 / 2 / 3 / 4 / 5 / 8 products: 0.6 / 3.4 / 7.4 / 85 / 135 / 429 s | integer columns 735 → 63, 1,469 → 125, 2,203 → 187, 3,081 → 249, 3,575 → 311, 5,681 → 497 | **0.2 / 0.5 / 1.0 / 1.2 / 5.1 / 226 s** | phase-one optima identical to 1e-13 in all 8 joint solves at 1–4; phase-two within the 1e-6 gap; reported settled numbers differ at tolerance level (0.03 % cost, one pack on some lines); at 4–5 products the baseline's decisions were made on time-limited solves; **frozen gate: P1 fixture T returns the other of two equal-cost source splits → CANONICAL REGRESSION FAIL**; P1 invariants 720 clean; P0 cell 15 identical | tie exposure on the frozen record | **SEMANTIC CHANGE — OWNER APPROVAL REQUIRED** (mechanism merged default-off) |
| E6 | frontier oracle phase one only (`service_only=True`) | phase two is unread | 8 products 429 s (frontier 246 s) | skip phase two | **186 s** (frontier 2.8 s); with E5 226 → 181 s | **IDENTICAL** reports and plan shapes at 1, 2, 3, 4, 5 products; canonical PASS; P1 invariants clean | none | **PURSUE — merged** |
| E7 | `solver_mip_gap` 1e-5 / 1e-4 / 1e-3 on the E5 8-product plan | the cost phases are proving the last 1e-6 | 225.7 s (both joint phase twos at the 90 s cap, gaps 1.3e-6 / 1.9e-6) | request override | **4.0 s / 2.3 s / 2.2 s** | 1e-5: joint objectives within 2 and 15 units, recovery quantities ± one pack on 4 lines, `recovery_guidance.status` OPTIMAL instead of FEASIBLE_TIME_LIMIT; 1e-4: objectives −1.7 k (0.004 %), gate reason changes, service at the 3rd decimal; 1e-3: objectives −23 k, `candidate_gates` flips base_stock ↔ joint_recovery, AVOIDABLE / UNAVOIDABLE classes change | default change | 1e-5: **DEFER to the owner** (evidence for §19); 1e-4 / 1e-3: **REJECT** |
| E8 | HiGHS `threads` 1 / 2 / 4 on E1's model | thread count changes the search or the time | default (auto): 5.0 s, 1,301 nodes | one option | 5.08 / 4.91 / 4.92 s, **1,301 nodes each, identical objective** | none | none | REJECT (no effect: the branch-and-bound is single-threaded and deterministic here; production keeps the default; §21) |
| E9 | SQL-side SKU scoping of the workspace read | the scan is the cost | 3.74 s at 10 k scoped to 200 | `WHERE sku IN (...)` | 3.67 s | request fingerprint identical | none | REJECT (not the cost); DEFER the Python-side read cost |
| E10 | gzip responses ≥ 1 KB | transfer size is the cost on the wire | workspace read 1.18 MB (36 products), 3.6 MB (150); plan report 326 KB | `GZipMiddleware` inside CORS | **57 KB / 42 KB** (20.8× / 7.7×); server time +50 ms on the 1.2 MB body | none (bytes identical after decoding) | none | **PURSUE — merged** |
| E11 | provider reads beside the workspace read | the directory / jobs / evaluations reads are serialised behind a 1.7 s read | Home usable ≈ 3.2 s on production (36 products); locally the three reads started at t = 2.5 s after the read | start them concurrently | locally they now start at t = 215 ms beside the summary read, i.e. they finish before the workspace read does; production measured after deploy (§9) | none (same reads, same order of attachment) | none | **PURSUE — merged** |

## 6. Phase G — accepted changes and their classification (§39 of the brief)

| change | where | class | evidence |
|---|---|---|---|
| Per-service frontier oracle runs phase one only (`solve(..., service_only=True)`) | `zaad/full/model.py`, `zaad/full/planner.py` | **PROVEN DECISION-EQUIVALENT** | the consumed value is the phase-one optimum by construction; reports and plan shapes IDENTICAL at 1 / 2 / 3 / 4 / 5 products vs the unchanged model (`scripts/plan_report_compare.py`, every decision, gate, economics, frontier, reliability and plan field, tolerance 1e-6); canonical regression PASS; P1 invariants 720 / 720; unit test `tests/unit/test_zaad_perf_pass.py` |
| `Request.fefo_symmetry_scope` (default `"network"` = released behaviour) | `zaad/full/contracts.py`, `zaad/full/model.py` | **NO SEMANTIC IMPACT** at the default (bit-identical formulation; canonical PASS, invariants clean, unit test pins default identity); enabling `"all"` is **SEMANTIC CHANGE — OWNER APPROVAL REQUIRED** (§5 E5: exact projection, tie exposure on frozen fixture T) | the product path does not set it in this release |
| gzip on API responses | `api/main.py` | NO SEMANTIC IMPACT (SERIALIZATION) | `tests/integration/test_api_gzip.py`; 1.18 MB → 57 KB workspace read, 326 KB → 42 KB plan report; CORS still outermost |
| provider starts the directory / plan-job / evaluation reads beside the workspace read | `web/src/lib/zaad/workspace-data.tsx` | NO SEMANTIC IMPACT (FRONTEND) | same reads, same attachment order; typecheck / lint clean; web unit tests 101 pass (the one local failure is the convention scan reading an untracked file from another session, `src/lib/network/adapters/workspace.ts`, not on this branch) |
| benchmark tooling: stage / phase attribution, report capture, MPS dump, request overrides, structure-only mode; `milp_replay.py`; `production_machine_sampler.py`; `workspace_scale_qa.py`; `plan_report_compare.py`; Insights read in the probe | `scripts/` | none (outside the runtime) | reproducible by another engineer |
| `CURRENT_SYSTEM.md` frontend sentence (four surfaces → the released groups) | docs | none | |

Not merged, recorded for the owner (§28 / §42 of the brief): `fefo_symmetry_scope="all"` on the
product path (E5; the 5-product plan 135 s → 5 s, 8 products 429 s → 181 s with E6); `solver_mip_gap`
1e-5 (E7; 8 products → 4 s with E5); the default scope and the job cap (unchanged, still the owner's
Decision 2 of the recovery record). Rejected: gap 1e-4 / 1e-3, HiGHS thread changes, a warm-start
policy change, SQL-side SKU scoping of the workspace read, component-wise decomposition.

## 7. Decision equivalence — what was compared and how

`scripts/plan_report_compare.py` compares two plan reports (and plan shapes) field by field:
status, selected policy, approval, the executable order, every recommended action (action, source /
SKU, period, quantity, first review), the incumbent actions, reasons, every candidate gate and its
stress rows, the service frontier, service reliability (per service: ZAAD service, best joint,
regret, avoidable / unavoidable), the network-service block, alternatives, joint feasibility,
protection value, recovery guidance, stress confirmation, confirmation benefit, procurement timing,
capital, the economics recommendation, orders, incumbent orders, materiality, selected / incumbent
costs and working capital, supplier orders and reconciliation, the orchestration classification and
candidate sets, the solve-quality statuses, and the plan shape's orders and purchase value; numbers
at relative tolerance 1e-6, everything else exactly; solve seconds, node counts, gaps and hashes are
excluded as volatile.

| comparison | products | verdict |
|---|---|---|
| unchanged model vs frontier phase-one-only (E6) | 1, 2, 3, 4, 5 | **IDENTICAL** (every field) |
| unchanged model vs `fefo_symmetry_scope="all"` (E5) | 1, 2, 3 | phase-one optima identical to 1e-13; phase-two objectives within the 1e-6 gap; settled numbers differ at tolerance level (recovery-guidance quantities by one pack on some lines, costs by ≤ 0.03 %, joint service by ≤ 3e-4); status, gates and orders identical |
| unchanged model vs E5 | 4, 5 | the baseline's joint solves were time-limited (phase two unproved at 4, phase one at 5) so its decisions rest on under-solved candidates; E5 proves them: at 4 products the gate moves from `base_stock` to `joint_recovery` — not a tie, a better-solved plan |
| E5 vs E5 + gap 1e-5 (E7) | 8 | one-pack differences on four recovery lines; `recovery_guidance.status` OPTIMAL vs FEASIBLE_TIME_LIMIT; statuses and gates identical |
| E5 vs gap 1e-4 / 1e-3 | 8 | economically visible: objectives −0.004 % / −0.05 %, gate reasons and AVOIDABLE / UNAVOIDABLE classes change → rejected |
| frozen gates on the merged tree (default scope + E6) | P0 cell 15, P1 fixtures B / T / Q / A | canonical regression **PASS**; P1 invariants **720 clean**; the label variance under time limits on cell 15 is the pre-existing recorded one |
| P2 evidence (`p2_benchmark`, 200 cells, 1,720 reviews) on the merged tree | P2 fixtures, all policies and seeds | against the frozen x86 record: 1,674 identical / 46 differing — **the unchanged `main` tree on the same arm64 machine differs from the record in exactly the same 46 reviews** (tie noise of the architecture, not the change); **unchanged `main` vs the merged tree on the same machine: 1,720 / 1,720 identical**, p2 invariants PASS; and faster (review p50 0.75 → 0.50 s, p95 8.9 → 5.5 s, max 24.1 → 16.6 s) |
| sector-physics evidence (`sector_benchmark`, 416 reviews) on the merged tree | commercial / produce / meat-seafood fixtures | invariants PASS 19 / 19; vs the frozen record 393 identical / 23 differing (architecture tie noise, as for P2); **unchanged `main` vs the merged tree on the same machine: 416 / 416 identical** |
| P3 sourcing evidence (`p3_benchmark`, 2,304 reviews) on the merged tree | P3 fixtures | invariants PASS 34 / 34; vs the frozen record 2,235 identical / 69 differing; **unchanged `main` vs the merged tree on the same machine: 2,304 / 2,304 identical** |
| P0 ownership arm (`p1_p0_arms`, the six P0 cells, 120 reviews) | cells 15 / 16 / 20 / 21 / 90 / 108 | vs the frozen x86 `router_cycle` record on arm64: 55 / 120 (architecture noise); unchanged `main` vs the merged tree **run concurrently with other benchmarks: 86 / 120** — the P0 cells hit their solver time limits, so their outcome depends on the CPU they get (the merged tree's own arm gave cell 21 cost 3,318 under load and 3,159 alone: same code, two answers); **both arms rerun alone, one after the other: 118 / 120** — cells 15, 16, 20, 90, 108 identical review for review, cell 21 differs on 2 of 20 reviews (r4 first-period purchase 22.35 vs 16.84 units at equal unmet), the cell the record itself lists as time-limited; not attributable to the change (`CURRENT_SYSTEM.md`: a time-limited review is rerun alone before it is judged) |
| frozen gates with `fefo_symmetry_scope="all"` forced (E5) | same | P0 cell 15 identical; P1 B / Q / A identical; **T differs**: reviews 0 and 5 split 1,920 units between src_A and src_B as 1,368 / 552 instead of 1,248 / 672 (equal cost) → the tie the P2 note predicted |

## 8. Memory (§24)

| run | API process | solver child | plan peak (local, RSS high-water of the benchmark process) |
|---|---|---|---|
| production, 1 / 2 / 5 / 8 products | 531 MB, 12 threads (constant) | 5 products **610 MB**, 16 threads, `MemAvailable` ≥ 1,103 MB of 2,015 MB; 8 products **704 MB**, 17 threads, `MemAvailable` ≥ 995 MB | — |
| local baseline (released formulation) 1 / 2 / 3 / 4 / 5 / 8 | — | — | 525 / 658 / 658 / 689 / 1,112 / 1,219 MB |
| local E5 (`fefo_symmetry_scope="all"`) 1–5 / 8 | — | — | 576 MB at 5, 889 MB at 8 |
| local E6 (frontier phase-one) 8 | — | — | (filled from the candidate run) |

Headroom on the 2 GB machine: the API process (0.53 GB) plus the solver child (0.6 GB at 5
products, ≈ 1.2 GB at 8–10 on the released formulation by the local high-water) leaves 0.3–0.9 GB;
no accepted change increases memory — E6 removes solves, E5 removes 91 % of the integer columns
(peak 1,112 → 576 MB at 5 products), gzip buffers one response at a time. The 10-product production
row is filled from the sampler when that run completes (§1.4).

## 9. Phase H — full benchmarks re-run on the candidate tree (local STRUCTURAL, same machine, same seed)

`candidate` = the merged tree (frontier phase one only; `fefo_symmetry_scope` at its default);
`candidate + all` = the same tree with `fefo_symmetry_scope="all"` (the owner's option, E5).
Baseline = the unchanged runtime. Time-limited MILPs in brackets.

| products | baseline | candidate (merged) | candidate + `fefo_symmetry_scope="all"` | what remains at the cap |
|---|---|---|---|---|
| 1 | 0.5 s | 0.6 s | 0.4 s | — |
| 2 | 3.0 s | 3.3 s | 0.6 s | — |
| 3 | 6.5 s | 3.1 s | 1.4 s | — |
| 5 | 135.1 s [2] | 134.6 s [2] | **7.1 s** [0] | joint phase ones (symmetry) |
| 8 | 429.2 s [2] | **186.9 s** [2] | **181.3 s** [2] | the two joint phase-two proofs at 1e-6 (90 s cap each) |
| 10 | > 2 h 12 min, stopped (cap 450 s; production TIMEOUT at 450 s in the recovery record) | **277.6 s** [3] | **182.6 s** [2] | merged: base-stock proxy and both joint phase ones at the 90 s cap (symmetry); with `all`: the two phase-two proofs |
| peak RSS (local) at 8 / 10 | 1,219 / — MB | 1,250 / 1,250 MB | 789 / 869 MB | |

The merged tree removes the frontier's discarded work everywhere (−243 s at 8, −224 s at 10 with
`all`) and, on the released formulation, brings the 8- and 10-product structural plans under their
caps (405 s, 450 s) on this machine; the production run after deploy decides whether the x86 search
path agrees (§10). The symmetry (E5) is what makes 5 products a 7 s plan and takes 8–10 products to
the residual 1e-6 proofs; both remain the owner's decisions (§6).

## 10. Phase I / J — gates, merge, deploy, production verification

| gate | result |
|---|---|
| exact-head CI | run 35104491427 on the tested head `e563800`: **13 / 13 green** (pytest 6 shards, ruff, mypy, security, gitleaks, frozen regression, docker, frontend). Earlier heads: `ee3ff86` failed gitleaks (a false positive on the image tag written as app:tag, and one flaky pass of `test_zaad_solver_lease::test_one_solve_at_a_time_in_submission_order` — the fake launch reads "the newest RUNNING row", a race under CI load; it passed on every later head and is not touched by this pass); `3ef3b01`, `712f44e`, `9c2525f`, `855df12` failed gitleaks only, on the same tag string in history — resolved with a `.gitleaksignore` of the exact fingerprints |
| canonical regression / P1 invariants | PASS / 720 clean on the merged tree (local); CI's frozen-regression job green on the tested head |
| P2 / sector / P3 evidence | unchanged `main` vs merged tree on the same machine: 1,720 / 1,720, 416 / 416, 2,304 / 2,304 identical; invariants PASS (20 / 19 / 34 checks) — §7 |
| P0 ownership arm | `perf_pass` vs the frozen `router_cycle` record: 55 / 120 decision-identical on arm64 (numerical noise of the architecture, e.g. 33.535749 vs 33.535747); the same-machine attribution against unchanged `main` is recorded below when it completes |
| security | bandit / pip-audit / gitleaks green in CI; mypy 153 files clean |
| merge | PR #86 → `914c5c33b8c9bc92a098b60ac2248613a31e788a` (`Merge PR #86: perf(zaad): full application and planner performance pass`), tree `99d43e2` identical to the tested head; `main` was `b818fd3` at merge time, unchanged since the branch point |
| deploy | `deploy-api.yml` run 35105475528 with `sha=914c5c3`: **success**; Fly `zaad-api` **v29**, image `canonical-914c5c3`, digest `sha256:bfe6177f…`; `GET /health` 200; the rolling deploy restarted the machine at 14:02 UTC (uptime and `/proc/stat` counters reset) |
| production smoke (v29) | `operating_product_release_smoke --self-serve`: **24 / 24 checks passed** (14:03 UTC) |
| Vercel | production deployments `zaad` and `harvestmind` from `914c5c3` (14:00–14:01 UTC) |

### 10.0 The web on the new build (Vercel from `914c5c3`, `api.zaadsupply.com` v29, DEMO workspace, cold Home, 15:21 UTC)

| what | before (§2.2) | after |
|---|---|---|
| directory / plan jobs / evaluation ids start | 2,518 ms, after the workspace read | **1,970 ms, beside the catalogue count**, finished before the read returns |
| workspace read | 1,705 ms, 1.18 MB on the wire | 1,685 ms, **57 KB on the wire** (`content-encoding: gzip`; curl: 1,183,178 B → 56,946 B) |
| Home content reads (Insights summary, history, summary(as_of), drafts, readiness) | 2,539 → 3,226 ms | 4,031 → 4,541 ms (this walk's `/me` took 808 ms on a cold connection, shifting everything by ~1 s; the relative order is unchanged) |

The workspace read's 1.7 s is server time, not transfer: curl's time-to-first-byte is 1.46 s with or
without compression, i.e. the shared vCPU takes ~1.4 s to build the 36-product request that the
laptop builds in 0.29 s. Compression removes the wire cost (material on a phone or a slow link;
the 150-product sample's 3.6 MB becomes ~170 KB) and the parallel start removes the 0.5 s of
serialised reads behind it; the server-side construction cost of the read remains the DEFERRED
item of §2.1.

### 10.1 Post-deploy verification, first attempt (14:04–14:16 UTC) — contaminated by throttling, not usable

Run 1 minute after the deploy restart: 1 product **DONE 4.4 s**, 2 products **DONE 30.4 s**, reads in
their idle band (health 0.21 / summary 0.28 / inventory 0.37 / POs 0.34 / readiness 0.46 / Insights
0.69–0.81 s median; 0 errors). Then the 5-product plan ran **315.9 s (DONE)** against 139 s in the
morning, with reads at 1.4–12 s, and the 8-product probe could not even load its sample data (60 s
read timeout). `/proc/stat` explains it: steal went from 3.0 s to **704.9 s during the 5-product run**
and kept climbing afterwards (875 s at 14:16) — the restarted machine came up with **no burst balance**
(a fresh machine accrues from zero), so the smoke, the 1- and 2-product plans and the first minute of
the 5-product plan spent the 90 s it had accrued and the rest ran at the 6.25 % baseline. This is the
recovery record's §4 mechanism, reproduced on a restart rather than on consecutive solves, and it is
exactly the case §50 of the brief names: **production data contaminated by throttling cannot be
separated, so nothing in this attempt is a performance measurement of the merged planner.** The
rested re-run is scheduled after ≥ 65 min of idle (8 products first, then 10 after a second rest,
then 5); results in §10.2.


### 10.2 Post-deploy verification, rested (v29 `canonical-914c5c3`, one plan at a time, machine sampled)

| products | idle before | job cap | queued | run | outcome | reads while solving (median / p95 / max s) | errors | CPU over the run | solver RSS max | `MemAvailable` min |
|---|---|---|---|---|---|---|---|---|---|---|
| 8 (15:23:35 UTC) | 67 min (steal flat at 883 s since 14:17) | 405 s | 0.00 s | **208.4 s** | **DONE, RETAIN_INCUMBENT** (`joint_recovery` FEASIBLE_TIME_LIMIT at 89.7 s — the phase-two proof at its cap, as §4 #2 predicts; `base_stock` OPTIMAL 1.8 s) | health 0.28 / 0.30 / 0.45 · summary 0.32 / 0.38 / 0.43 · inventory 0.40 / 0.58 / 0.71 · POs 0.34 / 0.41 / 0.42 · readiness 0.52 / 0.64 / 0.73 · Insights 0.81 / 0.93 / 1.10 · job 0.23 / 0.31 / 0.58 | 0 in 168 | user +263 s, **steal +5.0 s** (unthrottled) | 596 MB | 1,065 MB |
| 10 (16:13:10 UTC) | 45 min (steal +0.3 s over the rest) | 450 s | 0.01 s | **212.6 s** | **DONE, RETAIN_INCUMBENT** (`joint_recovery` FEASIBLE_TIME_LIMIT at 89.7 s; `base_stock` OPTIMAL 14.1 s; `hedged_network` INFEASIBLE 1.0 s) | health 0.28 / 0.30 / 0.36 · summary 0.31 / 0.43 / 0.44 · inventory 0.40 / 0.52 / 0.63 · POs 0.37 / 0.45 / 0.47 · readiness 0.49 / 0.62 / 0.68 · Insights 0.82 / 1.00 / 1.36 · job 0.24 / 0.32 / 0.65 | 0 in 168 | user +264 s, **steal +5.5 s** (unthrottled) | 648 MB | 935 MB |
| 5 (16:42:45 UTC) | 25 min (steal +0.1 s) | 338 s | 0.01 s | **133.7 s** | **DONE, RETAIN_INCUMBENT** | health 0.28 / 0.34 / 0.39 · summary 0.36 / 0.40 / 0.44 · inventory 0.40 / 0.51 / 0.57 · POs 0.36 / 0.45 / 0.53 · readiness 0.52 / 0.70 / 0.80 · Insights 0.82 / 0.94 / 0.96 · job 0.22 / 0.39 / 0.51 | 0 in 112 | user +168 s, **steal +2.9 s** | 682 MB | 1,029 MB |

**8 products: TIMEOUT at 405 s on v28 this morning (§1.4) → DONE in 208 s on v29; 10 products
(the product's default): TIMEOUT at 450 s on the released planner (recovery record §3.1) → DONE in
213 s on v29** — same machine, same data, rested in every case. The x86 search path lands where the
arm64 structural runs did (187 s and 278 s); the remaining time is the two joint phase-two proofs at
their 90 s cap (§4 #2), which is the owner's MIP-gap question. Each of these plans spends ~265 s of
the 500 s burst balance, so the honest sustained capacity of `shared-cpu-2x` is one default plan
per ~35 minutes of idle; a second plan inside that window runs throttled (§10.1 shows what that
looks like). 5 products: 139.0 s on v28 → 133.7 s on v29 (unchanged by construction; the 135 → 5 s lever is the owner's E5).

## 11. Final decision matrix (§48 of the brief)

| area | before | after | verdict |
|---|---|---|---|
| Home / API reads (production, idle) | summary 0.25–0.34 s, inventory 0.32–0.35, POs 0.27–0.33, readiness 0.36–0.49, Insights 0.55–0.67 s | unchanged bands (0.25–0.31 / 0.32–0.52 / 0.33–0.36 / 0.43–0.49 / 0.65–0.66 s); workspace read 1.18 MB → 57 KB on the wire; three reads no longer serialised behind it | improved transfer and waterfall; server time unchanged |
| Inventory (50 k products, server-side) | 101–303 ms | unchanged (no change needed) | fine |
| Insights (50 k products) | ≤ 437 ms (V2.1A record) | unchanged | fine |
| 10 k / 50 k data scale | every operating read ≤ 60 / ≤ 310 ms; planner workspace read 3.6 s / 14 s scoped to 200 | unchanged (SQL scoping exact but not the cost; DEFERRED) | documented |
| 1-product solve (production, rested) | 4.6 s | 4.4 s | unchanged |
| 2-product solve | 29.7 s | 30.4 s | unchanged |
| 5-product solve | 139.0 s | 133.7 s | unchanged by construction (frontier cost negligible at 5; the 135 → 5 s lever is the owner's E5) |
| 8-product solve | **TIMEOUT at 405 s** | **DONE 208 s** | fixed on a rested machine |
| 10-product solve (the default) | **TIMEOUT at 450 s** | **DONE 213 s** | fixed on a rested machine; sustained use still burst-limited |
| evaluation (baseline + overlay, sequential) | 2 × a plan of the proposal's scope | 2 × the new plan times (frontier removed from both) | improved proportionally; not re-measured separately |
| peak memory (solver child, production) | 610 MB at 5, 704 MB at 8 | 596 MB at 8, 648 MB at 10; API 531 MB; `MemAvailable` ≥ 935 MB | headroom kept |
| API responsiveness during a solve | idle band, worst 0.93 s | idle band, worst 1.36 s (Insights summary at 10 products) | unchanged |

## 12. Infrastructure recommendation (§49 of the brief)

**B — YES FOR RELIABILITY.** After the software pass, the released planner's default 10-product plan
completes in 213 s on a rested `shared-cpu-2x` (cap 450 s) and the 8-product plan in 208 s, with the
API in its idle band: the optimizer is no longer the reason a rested machine fails. What the machine
still does is throttle: a default plan spends ~265 s of the 500 s burst balance, a restart starts
from zero (§10.1: the first post-deploy 5-product plan took 316 s with 705 s of steal and reads at
1–12 s), and any second plan inside ~35 minutes runs at 6.25 % of a vCPU. A dedicated vCPU removes
that (the recovery record's §10: `performance-2x`, +$52.56 / month); it does not make the plans
faster. Not D: the formulation was the material problem *before* this pass (the frontier's discarded
phase and the FEFO symmetry), and the owner's two remaining software options (E5, E7) would take the
default plan from 213 s to well under a minute — those are cheaper than the machine and should be
decided first; but with the software as merged, repeated production use is a machine property.

## 13. Verdict

Every merged change is NO SEMANTIC IMPACT or PROVEN DECISION-EQUIVALENT (§6, §7); exact-head CI
13 / 13; canonical regression, P1 invariants, P2 / sector / P3 / P0 identity on the same machine;
Fly unchanged; deployed as v29 `canonical-914c5c3`; smoke 24 / 24; rested production verification
DONE at 8 and 10 products where the released runtime timed out. The V2 planner runtime tag stays
withheld: the handoff's own acceptance is the default plan **twice in a row** on the deployed runtime
plus the owner's machine decision, and this pass has one rested run at each size; the performance
release is tagged by the closure convention (`zaad-full-performance-pass-runtime` = `914c5c3`).

**ZAAD FULL PERFORMANCE PASS — RELEASE PASS**

