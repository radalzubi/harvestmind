# Diagnostic V3.1 — scale the rolling optimizer replay without changing optimization semantics

**Status: DONE — RELEASED (2026-09-21).** Branch `feat/diagnostic-v3.1-replay-scale` from `main` `9c5519c` (= the Diagnostic V3 runtime `d0edf15` plus its docs commit) → PR #93 (tested head `9c46fc2`, CI 35665692963 13 / 13) merged as `0cad5de`; Fly `zaad-api` **v35** `canonical-0cad5de` (digest `sha256:117dc421258aa763720372ecb962723141fbe284dc9b6d6243cc01a2cab00439`, deploy-api run 35667130197); Vercel production `dpl_G6PQvzhHghC9zxnQtXY9JUnnyWNn` from `0cad5de`; machine `0804e0dfd1e948` unchanged; runtime tag `zaad-diagnostic-v3.1-runtime` = `0cad5de`. Tracker written before any code change; release record in §8.

Primary principle of the brief: **optimization quality over speed.** No acceleration is acceptable if it can
change a recommendation the production optimizer would make on the same request. Every candidate change
below is classified before it is measured: *mathematically equivalent*, *decision-equivalent under the
existing tie-break*, or *a preliminary step with exact certification and fallback*. Anything else is not
enabled.

## 0. The problem, stated exactly

Diagnostic V3 replays the real production planner (`zaad.full.planner.plan`) at each weekly decision date.
On the production machine (Fly `shared-cpu-2x`) the two V3 QA runs completed 8 and 9 of 26 planned dates
inside the 1200 s budget, at 5 of 36 products, with per-date solves of 3–382 s (mean ≈ 158 s). Every one
of those dates returned `RETAIN_INCUMBENT`. The customer-facing evidence is therefore thin on two axes:
coverage (dates × products) and depth (a planner that, on this machine and budget, mostly cannot finish
its candidate solves inside the per-MILP cap and so retains the rule for lack of a comparable candidate).

What the prior performance pass established (`ZAAD_FULL_PERFORMANCE_PASS.md`, 2026-09-16), all of which
still holds on the V3 runtime because nothing under the optimizer changed since:

| fact | evidence |
|---|---|
| the solver is 94–100 % of a plan; model build, forecasting, worlds, settlement, serialisation are < 1 s per plan | pass §1.1 |
| 5-product plan: 135 s on the released formulation, both joint phase-one MILPs time-limited at gap 0.6; **7.1 s** with the FEFO symmetry removed (`fefo_symmetry_scope="all"`), zero time-limited MILPs | pass §4 #1, §9 |
| 91 % of the integer columns at 5 products are `fefo` indicators between cohorts that all outlive the horizon (interchangeable): a pure symmetry, big-M 1e9 | pass §3 |
| the symmetry removal is an exact projection (same feasible decisions, same objective) but changes the solver's search path and therefore **flipped one objective-flat tie** on frozen P1 fixture T (reviews 0 and 5: 1,368 / 552 vs 1,248 / 672 between two SKUs of one shared supplier order, equal cost) → canonical regression FAIL → merged default-off | pass §5 E5, §7 |
| second bottleneck from 8 products up: the joint phase-two cost proofs at the 1e-6 relative gap, each at its cap (gap 1.3e-6 / 1.9e-6); the MIP gap is an owner decision and is not changed here | pass §4 #2, E7 |
| the frontier oracle's discarded phase two was removed (exact, identical reports) | pass E6, merged |
| warm start: superseded by the symmetry fix; thread count: no effect; SQL scoping: not the cost; decomposition: changes phase two (pooled unmet) → deferred | pass §4.3, E4, E8, E9 |
| production solve times are the shared machine's burst budget draining during a long solve (`user` CPU 0.125 s/s refill) on top of the arm64-vs-x86 search-path difference | recovery record, environment memory |

So the replay's cost is the planner's cost, the planner's cost is one known symmetry plus one known
proof, and the symmetry fix is blocked only by tie preservation. That is the problem this pass works on.

## 1. Repo review (what was read before coding)

| item | file(s) | finding relevant to this pass |
|---|---|---|
| Diagnostic V3 implementation | `zaad/full/historical.py`, `api/routers/jobs.py`, `reports/diagnostic_v3.py` | replay = `build_request(as_of=origin)` once, then `zaad.full.replay.replay(rolling=True)` evolves the state in memory (no vault re-read per date); ZAAD leg = `choose(req, "gated")` = `plan(req)`; budget stop re-runs the completed prefix from recorded decisions (V3 PR #92) |
| replay loop | `zaad/full/replay.py` | per review: observe arrivals (model_dump / validate), inherited stock, incumbent rule projection (`baseline_plan`), `choose`, `settle(steps=1)`, next snapshot (`model_dump` + `Request.model_validate`). No solver call outside `choose` except `baseline_plan` (heuristic) |
| production planner path | `zaad/full/planner.py::plan` | per review: forecasts, supply profiles, protection, screen, ownership; solves = base-stock proxy (deterministic, `targets=`), incumbent (deterministic, `fixed=`), requested candidate classes (`deterministic_network`, `stochastic_network`, `protected_network`, …; `service_floor=True`), `joint_recovery` (`service_first="all"`, lexicographic), `joint_fitted` (state-dependent), per-service frontier oracle (phase one only), alternatives loop (reliability profile); selection by gates on settlement rows |
| model build | `zaad/full/model.py::solve` | one `Linear` per solve; integer columns: `packs`/`case`/`pallet`/`transport` multiples, `active` (MOQ / fixed fee), `po_option`, `depleted` (hoarding guard, big-M = location capacity / volume), `fefo` (one per younger cohort per service-period-world, big-M = capacity / volume; omitted between interchangeable cohorts on network requests, and on single-location requests only with `fefo_symmetry_scope="all"`), `priority`, `direct_first`, `order`/`pallets`/`freight_tier` (supplier terms), `switch` (P3), `line_full` (order metrics). Lexicographic: phase one (weighted unmet) then phase two (cost) on the same `Linear` with one added row and the phase-one point as seed |
| solve budget | `model.solve_budget` | `max(15, 15 × (H/12)² × breadth × 1.3)` capped at 90 s → **19.5 s per MILP** on the replay's requests (`max_solve_seconds=15`, H = 12, one location) |
| tolerances | `Request.solver_mip_gap` 1e-6, `comparable_gap` 0.02 (a time-limited candidate with gap ≤ 0.02 is still cost-comparable), phase-two row slack 1e-7, `service_tolerance`, `timing_tiebreak` 1e-4 of purchase value in the objective only | `zaad/full/contracts.py` |
| solver orchestration / leases | `zaad/full/jobs.py` (ordered solver lease), `api/routers/jobs.py` (`_Gate`, one diagnostic at a time) | the replay runs inside the diagnostic job's machine process, serially; nothing to parallelise without a second vCPU |
| FEFO symmetry | `model.py` lines 30–44, 1030–1045; `evidence/p2/perf/P2_PERF_DIAGNOSIS.md` | window rule: cohorts with expiry > max(H, latest transfer due) are interchangeable; indicator omitted exactly. The single-location default keeps every indicator |
| frontier / oracle | `planner.py` (`oracle = solve(..., service_first=service.id, service_only=True)`) | phase one only since the pass; consumed value = the phase-one optimum |
| caching / reuse | none in the planner; `forecast_all`, `supply_profiles`, `protection_profile` recomputed per review from the snapshot (all < 0.1 s per plan at 5–10 products) | pass §1.1 |
| replay scope selection | `historical.select_skus` | top-n by mean weekly history × unit cost at the first decision date; share reported. Audit in §6 |
| historical snapshot generation | `historical.build_truth`, `actual_orders_by_review`, `workspace.build_request` | once per replay; the per-review state is the replay loop's own |
| frozen regression | `scripts/zaad_canonical_regression.py` (CI job "zaad frozen regression"): P1 fixtures B, T, Q, A × 12 reviews order-for-order against the P1 freeze record; P0 cell 15 | fixture T is the recorded tie |
| decision-identity tooling | `scripts/plan_report_compare.py`, `scripts/production_solve_benchmark.py` (Recorder: per-MILP stage / phase / dims / time / gap / nodes), `scripts/milp_replay.py` | reused for this pass's profiler and equivalence runs |
| local vs production solver | local Python 3.14 carries highspy 1.17 (outside the project pin `>=1.14,<1.16`); a Python 3.12 environment with highspy 1.15.1 (the production and CI version) is used for every equivalence and timing run in this pass | `pyproject.toml` |

## 2. Plan of work (before code)

1. **Profile the replay end to end** (§3 of the brief) with a recorder around the real replay: per decision
   date, the time in snapshot construction, forecasting / statistics, world draws, request construction,
   each MILP (stage, lexicographic phase, columns / rows / integer / binary / non-zeros, nodes, gap, wall,
   CPU), settlement, and the leg's own bookkeeping; at 5 / 10 / 25 / 50 products on the synthetic
   demo company (36 products) and the synthetic FMCG sample (150 products). Record memory. Classify the
   cause of slow dates.
2. **Exact reuse / incremental features / model reuse** (§4–6): measured, not assumed. The pass's
   numbers say these are < 1 % of a plan; the profiler decides for the replay's own loop.
3. **Exact symmetry reduction with tie preservation** (§7 + §8): the reduced model (`fefo_symmetry_scope=
   "all"`, an exact projection) is a *fast candidate*; it is accepted only under an **exact certificate
   that no other solution of the same objective (within the solver's own gap tolerance) differs in any
   decision the planner reads** (purchases, transfers, amendments); otherwise the released formulation is
   solved exactly as today (the frozen search path, ties and all). Fixture T's tie must therefore fall
   back and reproduce the record; every non-tied solve must be identical. Certificate cost is measured.
4. **Repeated solves** (§9): audit per review with the profiler's stage attribution.
5. **Coupling graph** (§10–11): computed from the request (supplier capacity, terms, MOQ / MOV, shared
   service, capital); decomposition only if the pooled phase-one / phase-two objective is provably
   separable for the request — otherwise recorded and deferred with the reason.
6. **Replay scope selection** (§12): a deterministic, labelled STUDY SELECTION rule; no future
   information in any decision request; coverage reported exactly.
7. **Coverage benchmarks** (§13–14) at 5 / 10 / 25 / 50 × 8 / 13 / 26 / 52 where history permits, before
   and after, on the same machine; production runs after deploy.
8. **Evidence quality, decision-change rate, regime analysis** (§15–17): accounting in the replay result
   and the report; production materiality only.
9. **Tests** (§19–20), **release** (§22) only if a semantics-preserving change is justified by the
   measurements; otherwise findings and the next architecture.

## 3. Profile (measured; local Python 3.12 / highspy 1.15.1 arm64 = STRUCTURAL / RELATIVE; production numbers are the V3 QA runs on Fly)

Tool: `scripts/replay_profile.py` (the benchmark Recorder around the real replay: every MILP attributed to its
planner stage and lexicographic phase; every replay stage timed; nothing under `zaad/` runs differently).
Vaults: the synthetic DEMO company (36 products; the workspace V3 QA used) and the synthetic FMCG sample
(150 products). The replay's requests carry `max_solve_seconds=15`, so the per-MILP budget is
`solve_budget` = 15 × (1 + 0.6 × (products − 1)) × 1.3, capped at 90 s: **19.5 s at 1 product, 66 s at 5,
90 s from 8 products up** (every SKU/destination pair counts as a "location" in the breadth factor).

### 3.1 Where the replay's time goes (released formulation, 3 dates each)

| scope | total | MILP | non-solver | MILPs | time-limited | plan wall min / median / max | the solver time is | peak RSS |
|---|---|---|---|---|---|---|---|---|
| demo 5 products | 57.5 s | 55.7 s (97 %) | 1.8 s | 48 | 0 | 1.3 / 22.8 / 33.2 s | `joint_recovery` phase two 47.3 s (2 solves, 20–30 s each, proven), `joint_fitted` phase two 6.5 s; every candidate class (deterministic / stochastic / cvar / protected / hedged / stress) INFEASIBLE in 0.02 s; frontier 15 × 0.04 s | 421 MB |
| demo 10 products | 100.1 s | 96.2 s (96 %) | 3.8 s | 88 | 1 | 3.4 / 3.6 / 92.7 s | one `joint_recovery` phase two at the 90 s cap (gap 5.7e-5 after 13,049 nodes, seeded); the other two dates 3.4–3.6 s | 518 MB |
| demo 25 products | 148.3 s | 136.3 s (92 %) | 12.0 s | 159 | 1 | 19.8 / 20.3 / 107.3 s | frontier 75 × 0.5 s = 39.7 s; one `joint_recovery` phase two at the 90 s cap | 714 MB |
| sample 50 products (8 dates) | 108.6 s | 43.8 s (40 %) | 64.8 s | 480 | 0 | 12.4 / 13.1 / 13.4 s | every solve INFEASIBLE or trivial (§3.3); frontier 400 × 0.07 s = 28 s; **model construction ≈ 7 s per date** (60 models of up to 115,726 columns / 37,456 integers per date) | 1,017 MB |

Non-solver time by stage (5 products, 3 dates): truth reconstruction 0.03 s, request construction 0.11 s,
actual-orders leg 0.05 s, rule leg 0.04 s, per-review snapshot validation 0.03 s, world draws 0.13 s,
forecasts 0.05 s, settlement 0.05 s over 104 calls. **Everything the brief lists under §4–6 (snapshot
construction, feature statistics, scenario construction, request construction, settlement, result assembly)
is 1–4 s per replay against 56–136 s of solver at 5–25 products.** It is worth nothing until the planner
abstains quickly on a wide scope (50 products: model construction ≈ 55 % of a 13 s date).

### 3.2 The per-solve picture (5 products, released formulation, one date)

| stage | phase | worlds | columns | integer | binary | non-zeros | wall | outcome |
|---|---|---|---|---|---|---|---|---|
| base-stock proxy | single | 1 | 2,822 | 973 | 853 | 13,947 | 0.14 s | OPTIMAL |
| incumbent (fixed) | single | 1 | 2,702 | 973 | 853 | 13,828 | 0.01 s | OPTIMAL |
| 6 candidate classes | single | 1–4 | 2,702–10,236 | 973–3,397 | | 13,827–55,031 | 0.01–0.02 s each | INFEASIBLE (service floors unreachable from the opening position) |
| joint recovery | lex1 → lex2 | 4 | 10,226–10,970 | 3,397–3,644 | 3,277–3,524 | 54,551–60,712 | 0.02 s → **24–30 s** | proven at 1e-6 (760–10,327 nodes) |
| joint fitted | lex1 → lex2 | 3 | 7,730–8,068 | 2,593–2,708 | | 41,046 | 0.02 s → 3–8 s | proven |
| frontier oracle × 5 | lex1 only | 1 | 2,702 | 973 | 853 | 13,767 | 0.07–0.09 s each | OPTIMAL |

The objective of the joint solves is ≈ −5.0 × 10⁷ because the workspace adapter substitutes an unbounded
placeholder (10⁹) for an undeclared opening cash balance and the model charges the cost of capital on cash;
**the solver's relative gap of 1e-6 is therefore an absolute band of ≈ 50 cost units on these requests**
(≈ 0.03–0.05 on the P1 fixtures, whose cash is 10⁶). One case of one product held one week longer costs
≈ 1 unit here, so the released solver, and production with it, is indifferent among many plans that differ
by a case or a week. This is a property of the production planner's own request, recorded, not changed.

### 3.3 Why the planner abstains at 25–50 products on the sample vault (and would in production)

Every joint solve of the 50-product sample request is INFEASIBLE in 0.06–0.27 s, including the incumbent's
fixed solve, so every date is ABSTAIN. Bisection on the 25-product request: infeasible with the pipeline
removed, with supplier capacities unbounded, with promotions removed; **OPTIMAL with the opening stock
removed — and OPTIMAL in 1.0–1.7 s with the warehouse capacity set to 10⁸, 10⁷ or 10⁶ instead of the
adapter's unbounded placeholder 10⁹.** The location's `capacity_volume` is the big-M of the `depleted`,
`fefo`, `priority` and `direct_first` rows (capacity / volume = 10⁹); with thousands of such rows HiGHS
declares the model infeasible although no capacity row can bind. At 12 products the same request solves.
So a workspace that declares no warehouse capacity gets a request the released model cannot solve from
about 25 products up, on production as in the replay. Classified: **DATA / ADAPTER (numerical big-M), not
the optimizer's mathematics**; the fix (a finite, non-binding placeholder) changes every workspace model's
coefficients and is an owner decision recorded in §6. The demo company's request (36 products, mixed
expiry cohorts) does not hit it.

### 3.4 Why the reconstructed rule fails physically at 25+ products (fixed in this pass, replay side)

At 25 demo products the rule leg and the ZAAD leg ended on the second date with `shared supplier/route
capacity breach`: the reconstructed periodic rule orders every product of a supplier in the same week, which
the operator's own staggered orders never did, so its projection exceeds the declared supplier capacity
(60,000 / week) and the settlement refuses it; handed to the planner as the declared incumbent it made the
incumbent's fixed solve infeasible, so the planner abstained and fell back to the same unsettleable rule.
`historical._conform_shared` scales the rule's lines to the shared capacity (same factor, rounded down to
the declared cases, recorded per line) for the rule leg and for the declared incumbent the optimizer is
compared against. The planner's semantics are untouched (declared orders remain the incumbent); the
diagnostic supplies a physically admissible reconstruction, as it already did for the actual-orders leg.
After the change the 25-product replay completes (3 / 3 dates, RETAIN_INCUMBENT, PROTECT state).

### 3.5 Production (Fly `shared-cpu-2x`, V3 QA runs, 5 products, released formulation)

| run | dates in 1200 s | per-date plan wall | note |
|---|---|---|---|
| v33 `job_ced0eadcc3` | 8 of 26 | 4.7 / 70 / 41 / 137 / 106 / 382 / 338 / 180 s (mean 157 s) | the same requests take 1.3–33 s locally (§3.1): the shared machine's burst budget drains during the phase-two proofs and the x86 search path differs |
| v34 `job_6a7e84a32d` | 9 of 26 | 3.3 / 69 / 28 / 121 / 74 / 346 / 336 / 159 s + one | after PR #92 (no re-solve of the prefix) |

Reading: production is 5–10× the local structural time on the same requests; the cause is the machine
(burst-credit throttling on a sustained solve, one vCPU) on top of the planner's inherent cost (§3.1).

## 4. Changes made and their equivalence class

| change | where | class | evidence |
|---|---|---|---|
| **Certified symmetry reduction** `fefo_symmetry_scope="certified"` (+ `tie_certificate_cutoff`): the symmetry-reduced formulation (the released P2 window rule on a single-location request) is solved first; its solution is kept only under an exact tie certificate; otherwise the released formulation is solved exactly as today; fixed, service-only and recourse solves never take the reduced path; a reduction below 25 % of the integer columns is not attempted | `zaad/full/model.py` (`tie_certificate`, `CERTIFY_MIN_REDUCTION`, `CERTIFICATE_LOG`), `zaad/full/contracts.py` | **PROVEN DECISION-EQUIVALENT (certificate or fallback)**; default `"network"` untouched | §5; `tests/unit/test_zaad_tie_certificate.py` |
| Shared-capacity conformance of the reconstructed rule (rule leg and declared incumbent) | `zaad/full/historical.py` (`_conform_shared`, `_LegMethods.rule`, `_conformed_incumbent`) | replay side; the planner's semantics unchanged (declared orders are the incumbent) | §3.4; `tests/integration/test_replay_scale.py` |
| Study selection of the replayed products (`select_scope`, rule `window_value`, labelled STUDY SELECTION; `d0_value` kept) | `zaad/full/historical.py` | replay side; no request reads window information (attested) | §6 |
| Engine choice on the replay (`fefo` = network / certified / all; env `HARVESTMIND_REPLAY_FEFO`, default network) and scope rule (`HARVESTMIND_REPLAY_SCOPE_RULE`) | `zaad/full/historical.py`, `api/routers/jobs.py` | configuration; default = the released engine | |
| Decision-change accounting (§16), settlement basis by leg and metric (§15), operating regimes (§17), certificate summary in the engine block | `zaad/full/historical.py`, `reports/diagnostic_v3.py`, PDF, UI, `api.ts` | reporting only | |
| Replay profiler | `scripts/replay_profile.py` | tooling | |

Not changed, with the evidence for the owner (§6): the FEFO reduction without a certificate (`"all"`) on the
replay or the product path; the unbounded warehouse-capacity placeholder; the MIP gap; the phase-two proof.

## 5. Equivalence proof

**The reduced formulation is an exact projection.** For a single-location request without sector physics
the omitted `fefo` indicators sit between two cohorts that both outlive the horizon (expiry > H): neither is
disposed of, moved, or valued differently inside the window, so the FEFO rule between them constrains only
which label is consumed, never a quantity, a cost or a service value; the settlement applies FEFO itself.
Purchases, amendments, transfers, unmet demand and the objective of every feasible point are unchanged
(pass §4 #1: phase-one optima identical to 1e-13, cost optima within the solver gap).

**The certificate.** After a reduced solve proven optimal (objective z on the phase's cost vector), a second
MILP on the same reduced model maximises Σᵢ dᵢ / dustᵢ over every decision column the planner reads
(purchases in every period, amendments, transfers) subject to cost ≤ z + band, with dᵢ ≤ |vᵢ − vᵢ*|
linearised by one direction binary per control and big-M equal to the control's own bound width (valid for
every feasible point). A proven maximum below one dust unit means: no feasible point within the band differs
in any decision by a dust unit, so the released solver, whose stopping rule ends anywhere inside the band
(`"tolerance"`: band = `solver_mip_gap` × |z|; `"strict"`: 1e-7 × |z|, objective-flat ties), can only return
the same decisions. Anything else — a differing point found (the probe stops at the first, `objective_target`),
a time limit, a solver error, a reduced solve that is not proven — is not certified and the released
formulation is solved with the frozen search path, ties included.

**Frozen gates with the certified path forced on every request** (`Request` default patched; local 3.12 /
highspy 1.15.1): canonical regression **P1 fixtures B, T, Q, A × 12 reviews identical order for order and
status for status to the P1 freeze record; P0 cell 15 identical, no label variance.** 353 certificates
attempted: 126 certified, 201 refused because a differing point exists within the band, 26 not attempted on
an unproven reduced solve; the tie the pass recorded on fixture T (reviews 0 and 5) is refused and falls back,
which is the point. Unit tests pin the mechanism: identical decisions on the demo requests, an exact tie
(two identical sources) detected and refused, no reduced path for fixed / service-only / recourse solves,
default scope untouched.

**Cost of the certificate, measured on the replay's own requests.** This is where the mechanism fails the
brief's purpose, and the reason it is not the engine by default:

| run | released | certified (tolerance) | certified (strict) | why |
|---|---|---|---|---|
| demo 5 × 3 dates | 57.5 s | 187.7 s | 161.7 s | the `joint_recovery` phase-two certificate takes 30–54 s on a 7–11 k-column model with a weak relaxation, then (tolerance) finds a one-case alternative inside the 50-unit band and falls back to a 20–30 s released solve, or (strict) proves uniqueness in 53 s for a solve the reduced model finished in 1–11 s |
| demo 10 × 3 dates | 100.1 s | 257.8 s | — | one date 246 s: reduced phase two 90 s (time-limited) + certificate 90 s (not proven) + released phase two 90 s (time-limited) |
| P1 fixture T × 12 reviews | 11.1 s | 34.8 s | 37.2 s | small models: the certificate is pure overhead (0.2–0.9 s each, 93 of them) |

The certificate is as hard as the proof it replaces: proving that no alternative exists inside the band is
a branch-and-bound over the same weak relaxation. On the workspace requests the band is ≈ 50 cost units
(§3.2), one case-week of holding is ≈ 1 unit, so at the rigorous cutoff a differing point nearly always
exists and the released solve runs anyway. **Exact tie preservation is therefore achievable and proven, but
not cheap; the fast path pays for itself only where the reduced solve is orders of magnitude cheaper than
the certificate, which is not the case for the phase-two cost proofs that dominate the replay.**

## 6. Replay scope design (§12) and the owner decisions this pass surfaces

### 6.1 Study selection

The V3 rule (top products by demand value at the first decision date) has a survivorship exposure: a product
that becomes important during the window is never studied, one that fades stays. The V3.1 rule
(`historical.select_scope`, `"window_value"`, the default; `"d0_value"` kept as an option) ranks by demand
value over the whole replay window, takes the top n, and makes the set stratified (one intermittent-demand
product — zero demand in ≥ 35 % of the window's weeks, the diagnostic's own threshold — where any exists).
It is labelled **STUDY SELECTION** in the result and the report because it reads the window's demand; it
reads demand and unit cost only — never purchase orders' outcomes, receipts, stock counts or any policy's
result (test: rows after the origin in receipts and stock change nothing) — and it is used in one place: to
choose which products are replayed. Every decision request is then built from data strictly before its own
date (the per-snapshot attestation of V3 stands). Reported: window demand-value share, first-date demand-value
share, share of the window's purchase-order lines, strata, any stratification swap. Deterministic; ties by id.

### 6.2 What only the owner can decide (evidence in this record)

| decision | what it changes | evidence | recommendation |
|---|---|---|---|
| A. The replay engine: `HARVESTMIND_REPLAY_FEFO=all` (symmetry-reduced formulation without a certificate) | on an objective-flat tie the solver may return another optimal plan; executed decisions otherwise identical (exact projection). Production's own plans on x86 differ from the arm64 record on 46 of 1,720 P2 reviews for the same reason (pass §7) | §7 benchmark table: the same dates 3–4× faster at 5 products; decision agreement with the released engine measured over 13 + 8 dates (§7) | run the *replay* with `all` and state it in the report (the engine block already does); keep the product path at `network` |
| B. The unbounded warehouse-capacity placeholder (10⁹) in `workspace.build_request` | the big-M of thousands of rows; makes 25–50-product requests numerically infeasible → ABSTAIN on every date, on production too (§3.3) | §3.3: OPTIMAL at 10⁸ / 10⁷ / 10⁶ in 1–1.7 s | replace with a finite non-binding bound (e.g. 100 × the opening stock volume plus horizon capacity) in the adapter; frozen fixtures declare their own capacity and are untouched; production plans on undeclared-capacity workspaces move within tolerance |
| C. The unbounded opening-cash placeholder (10⁹) | the objective's scale (≈ 5 × 10⁷) and hence the 1e-6 gap's absolute band (≈ 50 units) and the cost-of-capital term's dominance | §3.2 | declare or bound opening cash in the adapter, or state the band in the report (done); no change here |
| D. `solver_mip_gap` 1e-5 (pass E7) | the phase-two proof time from 8 products up | pass §5 E7: 8 products 226 s → 4 s, one-pack differences on recovery guidance | unchanged (the brief forbids it) |
| E. Fly machine | the 5–10× production-over-local factor (§3.5) | §3.5 | after A: measure a performance CPU against the shared one on the same replay before deciding (§18 of the brief) |

### 6.3 Repeated solves (§9), coupling (§10) and exact decomposition (§11)

**Repeated solves.** Per decision date the planner solves: the base-stock proxy and the incumbent's fixed
projection (0.01–0.14 s each), six candidate classes (all INFEASIBLE in 0.02 s on these requests: the service
floors are unreachable from the opening position), `joint_recovery` (phase one + phase two), `joint_fitted`
(phase one + phase two; a different world set — the selection worlds without the declared stress — so not a
duplicate of the recovery solve; it would be one only on a request that declares no stress, and every
workspace request declares one), and one phase-one frontier solve per service. No solve's output is unread
since the pass removed the frontier's phase two. Nothing to remove.

**Coupling graph of the replay's requests** (`scripts.v2_solve_profile.coupling`, products as nodes, an edge
for every declared shared constraint): the only real coupling is the shared supplier-capacity resource — no
supplier terms, no MOQ / MOV, no transfers, no substitutions, no allocation, no shared service.

| request | products | real components (one per supplier) | products per supplier | artificial couplings in the formulation |
|---|---|---|---|---|
| demo 5 | 5 | 4 | 2 / 1 / 1 / 1 | the cash balance rows (one balance across every product; opening cash 10⁹, never binding), the warehouse-volume rows (10⁹, never binding), the pooled lexicographic objective |
| demo 10 | 10 | 4 | 4 / 2 / 2 / 2 | same |
| demo 25 | 25 | 5 | 7 / 6 / 5 / 4 / 3 | same |
| sample 50 | 50 | 8 | 8 / 7 / 7 / 7 / 7 / 5 / 5 / 4 | same |

**Exact decomposition.** With the artificial couplings never binding, the joint phase-one objective (priority-
weighted unmet demand summed over products) is a sum of component objectives, so its minimum is the sum
of the component minima, and phase two (cost at that service optimum, with a 1e-7 slack) then forces every
component to its own service minimum: component-wise solving is exact **when no shared row binds**, a
condition that can be certified after the fact (every shared row slack at the assembled solution, and the sum
of the component optima equal to the joint dual bound). It is not implemented here: (i) it is a search-path
change of the same class as the FEFO reduction — every component solve has its own tie exposure, so the same
certificate question returns; (ii) the measured cost is one supplier's joint solve, and the demo's largest
component (7 products) is above the size at which the phase-two proof hits its cap. Recorded as the next
architecture step after the owner's decision on A (§6.2): CATALOG → STUDY SET → COUPLING GRAPH → COMPONENT
SOLVES → SHARED-ROW CERTIFICATE → the joint solve only where the certificate fails.

## 7. Benchmarks before / after (§13–14)

Local = STRUCTURAL / RELATIVE (Python 3.12, highspy 1.15.1, arm64 M4 Pro; two or three benchmark
processes shared the machine, so wall times carry contention of up to ≈ 2×); production = the Fly
`shared-cpu-2x` machine. Released formulation unless stated. Coverage = decision dates completed of
planned. "Time-limited" = MILPs that reached their cap (66 s at 5 products, 90 s from 8).

### 7.1 Coverage and runtime by scope (released formulation, the engine production runs)

| scope | dates | coverage | total | median / p90 / max plan wall | MILPs (time-limited) | outcome | peak RSS |
|---|---|---|---|---|---|---|---|
| demo 5 | 3 (window from 2026-06-08) | 3 / 3 | 57 s | 22.8 / 33.2 / 33.2 s | 48 (0) | RETAIN × 2, PENDING_REVIEW × 1 (base stock) | 421 MB |
| demo 5 | 13 (window from 2026-03-30) | 13 / 13 | 1,295 s | 67 / 261 / 267 s | 198 (19) | RETAIN × 13 | 759 MB |
| demo 5 | **26** (window from 2026-01-05) | **26 / 26** | **4,770 s (79 min)** | 197 / 328 / 358 s | 377 (57) | RETAIN × 25, PENDING_REVIEW × 1 (`cvar_network`) | 753 MB |
| demo 10 | 3 | 3 / 3 | 100 s | 3.6 / 92.7 / 92.7 s | 88 (1) | RETAIN × 3 | 518 MB |
| demo 25 | 3 | 3 / 3 (after the rule conformance; 1 / 3 before, PHYSICAL_FAILURE) | 148 s | 20.3 / 107 / 107 s | 159 (1) | RETAIN × 3 (PROTECT) | 714 MB |
| sample 50 | 8 | 8 / 8 | 109 s | 13.1 / 13.4 / 13.4 s | 480 (0) | ABSTAIN × 8 — every joint solve numerically infeasible (§3.3) | 1,017 MB |
| **production** demo 5 (v33 / v34 / **v35**) | 26 planned | **8 / 9 / 7 of 26** in the 1200 s budget | 2,567 / 1,457 / 1,369 s | per-date solves 3–401 s (v35: 4.8 / 70 / 113 / 72 / 271 / 401 s + one) | — | v35: RETAIN × 6, own plan × 1 | 413 MB |

Reading. At 5 products the 26-date local replay completes in 79 minutes on the released formulation: on
the earlier dates (January–March) every candidate class is *feasible and expensive* — 17 of 26
`deterministic_network` solves, 14 of 26 `hedged_network` and 9 of 26 `stochastic_network` /
`protected_network` reach the 66 s cap (the FEFO symmetry of pass §4 #1: candidates enter as
FEASIBLE_TIME_LIMIT with a wide gap, are not cost-comparable, and the rule is retained) — whereas on the
recent dates (June) the same classes are infeasible in 0.02 s and the time is the joint recovery's
phase-two proof. Production is 5–10× slower per date on the same requests (§3.5), so the budget of
1200 s covers 7–9 dates there. The 10- and 25-product 26-date runs on the released formulation were
started on the same machine and had not completed when this record was written (projected from the
3-date rows: ≈ 90–150 min each); they are not claimed.

### 7.2 Symmetry-reduced formulation (`fefo_symmetry_scope="all"`, the owner's option A) on the same dates

| scope | released | reduced | decision agreement (status, policy, executed period-0 orders) |
|---|---|---|---|
| demo 5 × 3 | 57.5 s | 14.5 s | 3 / 3 dates identical |
| demo 5 × 13 (window from 2026-03-30) | 1,295 s (22 CPU-min) | **not completed when this record was written: 73 CPU-minutes and still running** on the same 13 dates | not measurable yet |
| demo 10 × 8 | not started (queued behind the row above) | | |

The 5 × 13 row is the finding: on the earlier window, where the expensive solves are the *candidate*
classes with feasible service floors (§7.1) rather than the joint phase one the pass measured, the
symmetry-reduced formulation is **slower**, not faster, at least 3× in CPU on the same dates before it
finished. The reduction removes the FEFO indicators; what remains at the cap on these dates is the
1e-6 cost proof (pass §4 #2, owner decision D), which the reduction does not touch. The 5 × 3 row (the
recent window, joint-solve-dominated) is where the 4× of the pass reappears. Owner decision A therefore
buys a 4× on one kind of date and nothing on the other; the honest expectation for a production replay
under `all` is "some dates fast, the rest unchanged", not a coverage jump. When the running comparison
completes its result lands in the session scratchpad (`prof/replay_demo_05x13_all_cmp13.json`); it is
not claimed here.

### 7.3 What the targets of §14 look like against these numbers

| target | achieved (released, local) | achieved (production) |
|---|---|---|
| 5 × 26 "comfortably complete" | complete in 79 min (57 time-limited candidate solves); not comfortable | 7–9 of 26 in 20 min |
| 10 × 26 "practical diagnostic runtime" | projected 1.5–2.5 h | not attempted |
| 25 × 26 "customer-usable" | projected > 2 h; the rule leg now settles | not attempted |
| 50 × 26 "serious evidence" | blocked by the adapter's capacity placeholder (§3.3), not by the solver: every date abstains in 13 s | not attempted |

No target is met by an exact change in this pass; the exact change that would meet the first two (the
FEFO reduction) is owner decision A because its tie exposure cannot be certified cheaply (§5), and the
third and fourth are blocked by adapter placeholders (owner decision B) before the solver is reached.

## 8. Release record (2026-09-21)

| step | value |
|---|---|
| PR #93 | `feat/diagnostic-v3.1-replay-scale`; tested head `9c46fc2`; CI run 35665692963 13 / 13 on the first run (ruff, mypy, bandit / pip-audit, gitleaks, docker, frontend typecheck / lint / test / build, six pytest shards, frozen regression) |
| merge | `0cad5dec1c5906d8a03c7671a245de5cc4efd6a0` (`Merge PR #93`, main was `9c5519c`) |
| deploy | Fly `zaad-api` **v35**, image `canonical-0cad5de`, digest `sha256:117dc421258aa763720372ecb962723141fbe284dc9b6d6243cc01a2cab00439`, deploy-api run 35667130197; Vercel production `dpl_G6PQvzhHghC9zxnQtXY9JUnnyWNn` from `0cad5de`; machine `0804e0dfd1e948` `shared-cpu-2x` unchanged; no Fly configuration change; replay engine env not set (the released formulation) |
| production QA (v35) | throwaway self-serve workspace **V3 QA DEMO (synthetic)** `op_9246979a` (the synthetic DEMO company, 36 products) and second tenant `op_ddbd8a22`; no customer workspace touched. `POST /jobs/diagnostic` 3.0 s, second press returned the same job; `queued` (30 s machine boot) → `preparing` → `testing` → `replaying` → `done`, run 1,369 s (`job_e41d633fe9`). Replay **partial**: 7 of 26 dates within the 1200 s budget, solves 4.8 / 70 / 113 / 72 / 271 / 401 s + one (mean 188 s, max 401 s), peak RSS 413 MB; engine `network` (released formulation, stated in the report); study selection `window_value`: 5 of 36 products, 31 % of window demand value, 31 % at the first date, 14 % of the window's purchase-order lines, no intermittent product in the top five; rule conformance 0 lines. Decision changes on the same snapshot: rule retained on 6 dates, own plan on 1, none abstained; 30 of 35 product-weeks identical to the incumbent, 5 new lines (all material by the planner's 1 % rule), no timing change; source and open-order changes not applicable (one source per product, keep-only options). Settlement basis: actual orders 100 % measured, rule and ZAAD 100 % inferred (their quantities differ from the recorded orders); attestation clean on all legs. Operating regimes: supplier-deterioration weeks (5) ZAAD better in 60 %, constrained-inventory weeks (3) better in 67 %. Result stated plainly: ZAAD 3.9 % less costly than the actual orders over the 7-date window, 4 of 7 periods better, worst period 2026-01-26 −187,263 JOD, too few periods for an interval; confidence **Low** (coverage). Six consistency checks pass; isolation 404 / 401 on job, report.json, report.pdf; PDF 41,509 bytes, 11 pages; payload 204 KB. Browser (zaadsupply.com, Chromium engine, the demo key): section 4 renders the decision-change paragraph, the operating-regime list, the settlement-basis and engine lines, and the 35-row decision detail. |
| runtime tag | `zaad-diagnostic-v3.1-runtime` = `0cad5de` (annotated; older tags untouched) |
| not done | the certified path is not the engine anywhere (§5); the two adapter placeholders (§6.2 B, C) are unchanged; no machine benchmark (§6.2 E); NTDCO: no customer key held |
