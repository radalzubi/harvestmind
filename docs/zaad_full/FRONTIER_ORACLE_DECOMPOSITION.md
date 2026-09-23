# Optimizer performance pass — exact frontier oracle decomposition and reuse

**Status: DONE — RELEASED (2026-09-23).** PR #95 (tested head `14ba8f4`, CI 35882180173 13 / 13) merged as `328a294`; Fly `zaad-api` **v37** `canonical-328a294`; Vercel production `dpl_DoNrfbM7…`; machine unchanged; runtime tag `zaad-frontier-decomposition-runtime` (§20). Branch `perf/frontier-oracle-decomposition` from `main` `b9d28cc` (= the sentinel
cleanup runtime `6b8e38d` plus its docs commit). Tracker written before any code change. Brief: make the per-service frontier
oracle exactly cheaper — identical frontier values, gates, comparability and recommendation — then benchmark the identical
code on the shared Fly CPU against a temporary performance CPU. Optimization integrity over speed; nothing in §10 of the
brief (MIP gap, scenarios, floors, pooled unmet, tie-breaks, classes, thresholds, abstention, `fefo_symmetry_scope`) changes.

## 1. Repo review (§1 of the brief)

| question | answer (from the code, `zaad/full/planner.py` and `zaad/full/model.py` at `b9d28cc`) |
|---|---|
| where the frontier is built | `planner.plan`, after the recommendation is decided (`status`, `final`, `accepted`, `chosen` are fixed above it): `oracle = solve(req, deterministic, service_first=service.id, service_only=True)` once per `req.services` entry |
| what the planner consumes | exactly one number per service: `oracle.projected_service.get(service.id)` = `1 − Σ_t unmet_i,t / Σ_t demand_i,t` on the mean world → the report row `service_frontier[i].best_modeled_individual_unit_fill`, `unavoidable_gap_under_mean_world = max(0, target − best)`, and `frontier_best[i]` → `service_reliability.services[i].best_modeled_individual_service` and the `pre_existing` flag of `classify_service` (UNAVOIDABLE class only) |
| does it change the decision | no: `status`, `final`, the gates, comparability and materiality are all decided before the loop; nothing below reads the frontier except the report's classification text and fields. The replay's decision accounting compares executed orders (`_decision_changes`) — never the frontier |
| MILPs per plan for the frontier | one per service (N services on the workspace requests = N products, one service per SKU); each a full-scope model of the whole request |
| phase one only? | yes since the performance pass (E6, merged): `service_only=True` returns the phase-one solution; phase two was removed because its output was unread |
| one or several solves per service | one |
| the solve | `worlds = draw(req, seed, 1, deterministic=True)` (one world, weight 1); objective `priority_i × Σ_t unmet[i,t]`; no `service_floor`, no `targets`, no `fixed`, no v6 terms, no seed; budget `solve_budget(req)`; route `req.solver` (scipy HiGHS) or highspy with `ORDER_CLASS_SEARCH` on the shared-supplier-order class |
| service floors / budgets | none in the oracle model (the candidate solves carry them; the oracle is unconstrained in service) |
| pooled unmet | the joint solves pool `Σ_i priority_i × unmet_i`; the oracle pools nothing — one service's unmet only. This is why the decomposition question has a different answer here than for the joint solve (rejected for that solve in `PRODUCTION_SOLVE_PERFORMANCE_RECOVERY.md` §6 and deferred in `ZAAD_FULL_PERFORMANCE_PASS.md` §4.3: phase two can trade unmet between products; the oracle has no phase two and no cross-product objective) |
| coupling constraints in the model | inventory balance per (SKU, location, cohort), FEFO / depleted / priority / direct-first linkage rows, purchase caps and pack rows, MOQ / fee activation rows, quote groups, supplier-order rows (order binary, MOV, pallets, freight tiers, max pallets), sourcing shares and switching, transfers and lane rows, opening-stock rows, resource capacity rows, declared location volume rows, cash / debt / reserve / solvency rows (declared capital only), PO amendment rows |
| existing decomposition work | `scripts/v2_solve_profile.coupling` (products as nodes, declared shared constraints as edges): 25 products → 8 components (one per supplier, 2–6 products each), 50 → 8 (4–8); V3.1 §6.3 recorded the exact component argument for the frontier as "the next architecture step"; the sentinel record §12.3 measured the frontier at 70 % of a 50-product replay date |
| frozen regression | `scripts/zaad_canonical_regression.py` (P1 B / T / Q / A × 12 reviews, P0 cell 15); `tests/unit/test_zaad_perf_pass.py` (frontier phase-one identity); `scripts/plan_report_compare.py` (every report field incl. `service_frontier` and `service_reliability`, numbers at 1e-6) |

## 2. The frontier, exactly (§2)

For every service *i* the oracle solves, on the single mean world *w₀* (weight 1):

```
F_i  =  min  p_i · Σ_{t<H} u_{i,t}
        s.t. (x, tr, a, inv, use, u, binaries, cash) ∈ 𝓕
```

* decision variables: the full model's — purchases `x[source,t]`, pack / case / pallet / transport integers, activation
  and order binaries, quote-group and switching binaries, transfers `tr`, PO amendments `a` and option flags, inventory
  `inv[sku,loc,expiry,t]`, allocations `use[sku,service,expiry,t]`, unmet `u[service,t] ∈ [0, d_{service,t}]`, the
  depleted / FEFO / priority / direct-first binaries, cash and debt columns when capital is declared;
* objective: `p_i` = the priority of service *i*'s customer times the world weight (1); every other column has cost 0;
* constraints: the whole released feasible set 𝓕 of `model.solve` on that request and world — every row listed in §1
  — with no service floor, no target, no fixed plan, no v6 term;
* the service being varied: *i* alone; global service requirements: none; shared resources: whatever the request declares;
* output read: `F̂_i = 1 − (Σ_t u*_{i,t}) / (Σ_t d_{i,t})` (1 when demand is zero), None when the solve returns no usable point.

So the frontier value is "the least unmet demand of service *i* that any physically and financially feasible plan can leave,
when nothing else is asked of the plan" — an individual, not simultaneous, bound (the report says so in `bound_scope`).
It is a MIP minimum: the released solver proves it to `solver_mip_gap` (1e-6 relative) or stops at the budget with an
incumbent (`FEASIBLE_TIME_LIMIT`, the incumbent's own unmet — an upper bound on the minimum, i.e. a *lower* bound on the
fill — reported as if it were the frontier) or with none (`NO_FEASIBLE_SOLUTION` → None).

## 3. Why it can be decomposed exactly (§4–5)

The constraint matrix *A* of the built model, with the column bounds and integrality, defines a graph *G* whose nodes are
the columns and whose edges join two columns that share a row. Let *C₁ … C_k* be its connected components and *R_j* the
rows whose columns lie in *C_j* (every row's columns lie in exactly one component by construction). Then, after a
permutation, *A* is block diagonal and

```
𝓕 = 𝓕₁ × 𝓕₂ × … × 𝓕_k,   𝓕_j = { y_j : A_{R_j, C_j} y_j ∈ [lo_{R_j}, hi_{R_j}],  y_j ∈ [l_{C_j}, u_{C_j}],  integrality on C_j }
```

because every row constrains columns of one component only and every bound is a single column's. For an objective
supported on one component (`u[i,·]` all lie in the component *C(i)* that holds service *i*'s balance rows):

```
min_{y ∈ 𝓕} p_i Σ_t u_{i,t} = min_{y_{C(i)} ∈ 𝓕_{C(i)}} p_i Σ_t u_{i,t}     provided 𝓕_j ≠ ∅ for every j ≠ C(i)
```

(if some other component is empty the whole 𝓕 is empty and the monolithic oracle returns INFEASIBLE — None for every
service; the decomposed oracle must reproduce that, §6). The component problem is the same MIP restricted to its own
columns and rows: the same objective coefficients, the same bounds, the same integrality, the same rows. Its optimum is
the frontier value; there is no relaxation, no aggregation, no dropped row.

The components are **computed from the matrix the builder produced**, never assumed from the data: any declared coupling —
a shared supplier order or capacity resource, a declared location volume, a declared cash balance, a substitution, a
transfer lane, a shared PO — appears as a row over both products' columns and merges their components. The "true global
constraints" of §6 of the brief (capital, network capacity, pooled allocation, shared supplier capacity) therefore need no
separate treatment: where one exists the components it touches are one component and that component is solved whole
(the monolithic solve, restricted to what is actually coupled). No master problem, Benders or coordination is attempted:
the frontier is a single-objective MIP and the exact answer for a coupled set is the coupled solve.

## 4. Reuse (§7)

The old loop rebuilds the full model N times (one `Linear` per service, ≈ the same 117 k-column arrays each time at 50
products). The new oracle builds it **once** per plan, partitions it once (union–find over the row structure, O(nnz)),
extracts each component's sub-model once and solves it with one objective vector per service in the component: build once →
change objective → re-solve, on the same solver route, budget, gap and options as the released oracle. The per-component
extraction is an index selection on the built arrays (`Linear.rows` dicts re-indexed, bounds and integrality sliced), so
the sub-model is the released rows and columns verbatim. Whether the build reuse matters by itself is measured separately
(§14: build time vs solve time).

## 5. Exact skips (§8)

Two certificates, both exact, no heuristics:

1. **Witness at the bound.** Every planner solve on the same request and the same deterministic world whose feasible set is
   a *restriction* of the oracle's (the incumbent's fixed projection, the base-stock proxy with its slack target rows and
   disabled options, `deterministic_network` with its floors and v6 terms whose extra columns project away) yields, when
   physically usable, a feasible point of the oracle model. If that point serves service *i* in full (`projected_service[i]
   == 1.0`: its unmet is zero in every period), it attains the trivial lower bound 0 of the minimisation, so `F̂_i = 1.0`
   exactly and no solve is needed. It also proves 𝓕 ≠ ∅, so every component is feasible and the infeasibility rule below
   is settled without a solve.
2. **Infeasibility.** Without a witness, a service-less component is solved once for feasibility (zero objective, same
   budget); any component proven INFEASIBLE makes every service's value None, exactly as the monolithic oracle would report.

Dominated / identical services (§8) are not skipped: two services in one component with identical feasible sets would
need a proof of identical objectives too, and none is available cheaply; the component solve already makes each of them
one small MIP.

## 6. Multi-service solves (§9) — evaluated, rejected

One solve yielding several exact frontier values would need either a per-service dual bound equal to the per-service
optimum (MIP duality gives no such bound) or a lexicographic / ε-constraint structure that changes what is minimised. A
joint solve's incumbent gives *upper* bounds on every service's unmet (feasible points) but the frontier needs the minimum;
only the witness rule above (bound attained) turns such a point into an exact value. Rejected for anything beyond that.

## 7. What stays identical (§10–11)

* The value `F̂_i` for every service with a proven monolithic optimum: identical up to the solver's own 1e-6 relative gap on
  the unmet objective (two different MIPs reach the same optimum by different search paths; on every measured request the
  values are compared exactly and at 1e-9, §15).
* Where the old oracle was time-limited its number was an incumbent, not the frontier; the component solve proves the
  optimum or reaches the same budget with its own incumbent. Such differences are reported per date and shown to leave the
  recommendation unchanged (the frontier is read after the decision, §1).
* The report rows of `service_frontier` keep their keys; telemetry of the decomposition goes to
  `orchestration.frontier` (components, solves, skips, build and solve seconds) — a new block, absent before.
* Statuses: the oracle Solution carries OPTIMAL when every solve proved its optimum, FEASIBLE_TIME_LIMIT when any solve
  stopped at its budget with an incumbent, INFEASIBLE when any component is infeasible, NO_FEASIBLE_SOLUTION otherwise.

The old path stays callable (`frontier_mode="monolithic"`) for the equivalence harness and the tests; production runs
`"component"`.

## 8. Harness, regression, fixtures (§11–13)

* `scripts/frontier_equivalence.py`: for every representative request builds both oracles and compares service ids, every
  value (exact and 1e-9), statuses; then runs `plan` under both modes and compares the reports with
  `scripts.plan_report_compare` (status, policy, actions, gates, frontier, reliability, economics …) and the executed plan.
* Frozen canonical regression (`scripts/zaad_canonical_regression.py`) — hard gate, unchanged.
* `tests/unit/test_zaad_frontier.py`: A independent components (component == monolithic, per service), B shared supplier
  (order rows keep the products in one component), C capital coupling (declared cash merges everything; monolithic answer),
  D MOQ / MOV, E location / network (declared volume; transfer lanes), F fully independent (maximum decomposition, N solves
  of N single-product components), G degenerate / tie (identical report and plan).

## 9. Measurement plan (§3, §14–16, §18)

`scripts/frontier_profile.py` (Recorder-based, outside `zaad/`): per scope 5 / 10 / 25 / 50 (/ 100 stress) — frontier solve
count, total / median / p90 / max solve, build time, solver time, dimensions (columns, integers, rows, non-zeros), status,
gap, nodes, peak RSS, components (count, sizes, largest), and the frontier's share of the whole plan; before (monolithic)
and after (component). Replay: `scripts/replay_profile.py` 5 × 26, 10 × 26, 25 × 26, 50 × 8 after the change, decision
equality against the sentinel-cleanup runs (§18 of the brief).

## 10. Supplier-capacity sentinel (§17) — audited, kept unchanged in this pass, removal plan recorded

`zaad/full/workspace.py:299–306`: a supplier with no declared capacity (master or per SKU) **and** no purchase order before
the origin gets `capacity = 1e9` with provenance `NOT_AVAILABLE`. Where that number reaches the model (`model.py`):

| site | with the placeholder | exact replacement available? |
|---|---|---|
| purchase column bound `cap = min(source.maximum, capacity_by_period[t])` (l. 805) | 10⁹ | "no constraint" is `+inf`; a finite *valid* bound exists only from dominance (`activation_bounds`: demand-to-go of every service the SKU may supply, plus continuation, MOV and MOQ floors, lattice-rounded), proven for the cost objective in P3 and — since over-buying never reduces unmet — for the service objective too; guarded (salvage below landed cost, lane loss below one, no share rows, integral lattice) |
| `packs` / case / pallet / transport integer bounds `floor(cap / multiple)` (l. 813–817) | 10⁹ / multiple | the same bound; `inf` would raise in `floor` |
| MOQ / fee activation row `purchase ≤ min(cap, tight) × active` (l. 821) | M = 10⁹ outside the shared-supplier-order class (`tight` is computed only inside it) | the dominance bound as M — the case the sentinel record deferred |
| supplier-order caps (l. 910) | `min(maximum, capacity, tight)` | same |
| resource row `Σ volume × purchase ≤ capacity[t]` (l. 1071) | rhs 10⁹, never binding | omit the row (no constraint). Note for this pass: the row also **merges the supplier's products into one coupling component** although nothing physical couples them — an artificial coupling the partition of §3 honours exactly (solving them together is still exact, only slower) |
| flow-derived stock bound `Σ_{s<t} min(maximum, capacity[s])` (l. 760) | 10⁹ × t as the depleted / FEFO / direct-first big-M and the inventory column bound | the dominance bound summed over the periods; this is the sentinel cleanup's own bound re-entered through a placeholder — latent, not on any tested workspace |
| settlement `q > min(maximum, capacity[t])` (settlement.py:172) and the replay's conformance (`historical.py:214, 239`) | pass everything | unchanged when the constraint is absent |

Where it occurs: on no frozen fixture, the demo (five suppliers, all declared) or the sample (eight, all inferred from PO
history). It enters no profiled failure and no replay date of this pass.

**Decision for this pass:** unchanged. The exact finite bound *is* derivable — `activation_bounds` supplies it under its
guards — but removing the sentinel is a formulation change of the sentinel-cleanup kind (the contract must admit an absent
supplier capacity; six model sites consume the dominance bound instead of the capacity; sources whose guards fail have no
finite bound and need their own rule; settlement and conformance follow), with its own audit and equivalence proof. Bundling
it into a pass whose claim is "identical frontier, identical decision" would muddy that claim for no measured benefit.
Recorded as the next sentinel item with the derivation above; the brief's instruction not to let it derail the frontier work
is followed.

## 11. Infrastructure benchmark (§19–20)

Only after the software work and its equivalence proof: the identical image on a temporary `shared-cpu-2x` and a temporary
`performance-2x` machine (one-shot `fly machine run` of the benchmark command, no service, destroyed afterwards; the
production machine untouched), 5 / 10 / 25 (/ 50) products, cold / rested / consecutive runs, wall, user CPU, peak RSS,
frontier and solver time. Recommendation from the measurements; no permanent change without the owner.

## 12. Rejected approaches (running list)

| approach | verdict | reason |
|---|---|---|
| master / Benders / column generation over shared resources | not needed | the oracle is a single-objective MIP per service; coupled products form one component and are solved whole — exact by construction |
| one multi-objective solve for several services | rejected | no exact per-service value from one solve except at the attained bound (§6) |
| skipping dominated / identical services | rejected | no cheap proof of equal optima |
| reusing HiGHS presolve / basis across objectives | not available | HiGHS re-presolves a MIP on every `run`; only the Python build is reusable |

## 13. Baseline and after — the oracle alone (§3, §14)

`scripts.frontier_profile --oracle` on the sample vault (STUDY-SELECTION scope, `max_solve_seconds` 15, seed 41001; local
Python 3.12 / highspy 1.15.1 / arm64, two to four benchmark processes sharing the machine). `monolithic` = the released loop;
`component` = one build, exact components, one solve per service (no witnesses: every service solved). Every solve on
both sides proved its optimum (`OPTIMAL`, gap 0); every value identical on both sides (§15).

| products | mode | solves | frontier total | median / p90 / max per solve | largest model (columns / integer / nnz) | B&B nodes | components (service-bearing) | build outside solves | peak RSS |
|---|---|---|---|---|---|---|---|---|---|
| 5 | monolithic | 5 | 1.3 s | 0.20 / 0.58 / 0.58 s | 2,824 / 907 / 12,654 | 725 | — | 0.04 s | 518 MB |
| 5 | component | 5 | **0.2 s** | 0.03 / 0.06 / 0.06 s | 566 / 182 / 2,534 | 52 | 5 (5) | 0.02 s | 514 MB |
| 10 | monolithic | 10 | 5.2 s | 0.39 / 0.82 / 1.60 s | 5,650 / 1,815 / 25,311 | 1,078 | — | 0.13 s | 561 MB |
| 10 | component | 10 | **0.3 s** | 0.03 / 0.05 / 0.06 s | 1,132 / 364 / 5,066 | 57 | 8 (8) | 0.03 s | 508 MB |
| 25 | monolithic | 25 | 46.4 s | 0.92 / 4.99 / 5.15 s | 14,096 / 4,529 / 63,044 | 6,956 | — | 0.82 s | 735 MB |
| 25 | component | 25 | **2.9 s** | 0.06 / 0.18 / 0.85 s | 2,832 / 911 / 12,670 | 1,269 | 8 (8) | 0.03 s | 543 MB |
| 50 | monolithic | 50 | 591.9 s | 3.71 / 30.8 / 90.3 s (**2 at the cap**) | 28,116 / 9,032 / 125,577 | 86,627 | — | 3.99 s | **1,875 MB** |
| 50 | component | 50 | **8.2 s** | 0.16 / 0.23 / 0.36 s | 4,526 / 1,455 / 20,267 | 50 | 8 (8) | 0.06 s | **531 MB** |

At 50 products the two monolithic solves that reached the 90 s cap returned their incumbent — `svc_SKU-0021` 0.447 and
`svc_SKU-0030` 0.833 — where the component solves prove the optimum in 0.2 s: 0.948 and 1.000. The released oracle was
reporting, on those services, a plan's unit fill as if it were the frontier (a lower bound on the fill, §2); the decomposed
oracle reports the frontier. Every other value (47 exact, one within 1e-9) is identical. Component sizes at 50 (columns):
4,526 / 3,964 / 3,964 / 3,952 / 3,914 / 2,790 / 2,788 / 2,218 — eight suppliers.

Component sizes at 25 products (columns): 2,832 / 2,822 / 1,698 / 1,692 / 1,656 / 1,134 / 1,134 / 1,128 — one component
per supplier whose inferred weekly capacity resource its products share; at 10: 1,132 / 1,128 / 566 × 6. Partition and
extraction cost 2–20 ms. Build reuse by itself (one build instead of N) saves the released build time N − 1 times (0.8 s at
25 products): real but secondary to the component solves, which are 16× faster in total at 25 products.

### 13.1 Demo vault (the replay's requests) and the genuinely coupled stress fixture

| request | mode | solves | frontier total | largest model | components (service-bearing) | values vs monolithic |
|---|---|---|---|---|---|---|
| demo 5 | monolithic → component | 5 → 5 | 0.3 → 0.1 s | 2,716 → 1,062 cols | 15 | 5 / 5 exact |
| demo 10 | monolithic → component | 10 → 10 | 1.4 → 0.2 s | 5,394 → 2,086 | 15 | 10 / 10 exact |
| demo 25 | monolithic → component | 25 → 25 | 11.2 → 2.1 s | 13,428 → 3,622 | 21 | 25 / 25 exact |
| sample 25 **stress** (declared cash 3.0 M / 300 k facility, MOV and fixed order cost per supplier) | monolithic → component | 25 → 25 | 17.5 → 17.5 s | 13,666 → **13,666** | **1** | 25 / 25 exact |
| sample 50 **stress** | monolithic → component | 50 → 50 | 101.1 → 100.9 s | 27,136 → **27,136** | **1** | 50 / 50 exact |
| sample 100 **stress** (206 k-column plan model; the oracle's mean-world model 53,896 columns / 17,966 integer / 255 k nnz) | monolithic → component | 100 → 100 | 619.4 → 611.3 s (5.9 s median per solve, every solve proven at the root) | 53,896 → **53,896** | **1** | 100 / 100 exact |

At 100 coupled products the frontier is inherently expensive — a hundred 54 k-column LP-dominated solves of one component —
and this pass says so rather than approximating it (§22 of the brief): the only exact savings available there are the witness
rule (services the incumbent's projection already serves in full) and the one-build reuse. The stress fixture is the §6 case
of the brief: a declared cash balance is one row per period over every product's payments,
so the partition finds **one** component and the "decomposed" oracle is the monolithic solve — same cost, same values, no
approximation. True global coupling is honoured by construction, never ignored.

## 14. The whole planner (§14): before / after, identical reports

`scripts.frontier_profile --plan` (the released `planner.plan` on the same sample requests; witnesses active in
`component` mode). Reports compared with `scripts.plan_report_compare` (status, policy, every action, gates, frontier,
reliability, economics, orchestration, solve-quality statuses): **no difference at 5, 10 or 25 products**; the recommendation
is RETAIN_INCUMBENT (operator rule `replace_sold`) on every one.

| products | mode | plan wall | frontier solves | frontier time | frontier share | witness-proven (no solve) | MILPs in the plan | where the rest goes | peak RSS |
|---|---|---|---|---|---|---|---|---|---|
| 5 | monolithic | 201.2 s | 5 | 1.4 s | 0.7 % | — | 13 (3 at cap) | three candidate classes at the 66 s cap | 720 MB |
| 5 | component | 199.8 s | 1 | 0.01 s | 0.0 % | 4 of 5 | 9 | same | 545 MB |
| 10 | monolithic | 98.2 s | 10 | 5.7 s | 5.8 % | — | 20 (1 at cap) | `joint_recovery` two phases 89.8 s | 534 MB |
| 10 | component | 92.6 s | 5 | 0.16 s | 0.2 % | 5 of 10 | 15 | same | 530 MB |
| 25 | monolithic | 169.4 s | 25 | 53.5 s | **31.6 %** | — | 35 (1 at cap) | `joint_recovery` 89.4 s, base-stock proxy 22.0 s | 766 MB |
| 25 | component | **116.6 s** | 13 | 1.1 s | 0.9 % | 12 of 25 | 23 | same | 676 MB |
| 50 | monolithic | 783.7 s | 50 | 626.6 s (2 at the cap) | **80.0 %** | — | 59 (3 at cap) | base-stock proxy 55.5 s, `joint_recovery` 89.5 s | **1,944 MB** |
| 50 | component | **157.7 s** | 30 | 4.6 s | 2.9 % | 20 of 50 | 39 (1 at cap) | same | **985 MB** |

**The one report difference, at 50 products.** The recommendation, the actions, every gate, the economics and 48 of 50
frontier rows are identical. On `svc_SKU-0021` and `svc_SKU-0030` the released oracle's solve reached its 90 s cap (gap 0.91
and 1.0) and the report carried the incumbent's fill — 0.447 and 0.833 — as `best_modeled_individual_unit_fill`; the
component solves prove 0.948 and 1.000 in 0.2 s. For `svc_SKU-0021` that turned the reliability classification from
UNAVOIDABLE `pre_existing: True` ("no feasible action meets the target even when this service alone is maximized") into
UNAVOIDABLE `pre_existing: False` ("not jointly achievable with the other services' targets") — the released text was
wrong, because its bound was a time-limited plan and not the frontier (§2). The class (UNAVOIDABLE) and the decision
(RETAIN_INCUMBENT) are the same; `classify_service` is untouched. Reported as the difference it is, not as a match.

At 5 and 10 products the frontier was never the cost: the plan is the joint recovery's two phases and the candidate classes
at their caps (the sentinel record §10 — the honest 1e-6 proof on real economics). At 25 it was a third of the plan and is
now under one percent. The witness rule fires on the services the incumbent's own projection already serves in full on the
mean world (4 / 5, 5 / 10, 12 / 25 here).

## 16. Memory (§16)

Measured as the process high-water RSS of the oracle alone (§13) and of the whole plan (§14). The released loop's peak is
the Python model (lists of row dicts, ≈ 28 k columns / 126 k non-zeros at 50 products) plus HiGHS's own copy of the whole
model — presolve, LP and branch-and-bound working sets of the full matrix — rebuilt for every service and released between
services (Python objects, no leak: the peak does not grow with the number of services solved). The decomposed oracle holds
the same Python model once and hands HiGHS one component at a time (≤ 4,526 columns at 50 products): 1,875 → 531 MB for
the oracle alone at 50 products, 766 → 676 MB for the 25-product plan. The full built model is kept for the duration of the
oracle (the sub-models are extracted lazily, one at a time, and dropped after their solves), which is the lower of the two
peaks (full + one component) against extracting everything first (2 × full). Nothing is cached across services; no log
is retained beyond the per-solve telemetry row.

## 15. Frontier values old vs new — the equivalence summary (§11)

`scripts.frontier_profile --compare` on every pair (service ids identical everywhere; values compared exactly, then at 1e-9;
statuses from each solve's HiGHS status):

| request | services | exact | within 1e-9 | differences | why |
|---|---|---|---|---|---|
| sample 5 / 10 / 25 (oracle) | 5 / 10 / 25 | all | 0 | 0 | — |
| sample 50 (oracle) | 50 | 47 | 1 | 2 | the released solves at their 90 s cap (incumbent 0.447 / 0.833; proven optimum 0.948 / 1.000) |
| demo 5 / 10 / 25 (oracle) | 5 / 10 / 25 | all | 0 | 0 | — |
| sample stress 25 / 50 / 100 (oracle; one component) | 25 / 50 / 100 | all | 0 | 0 | — |
| sample 5 / 10 / 25 (whole planner, reports compared field by field) | 5 / 10 / 25 | all | 0 | 0 report differences | — |
| sample 50 (whole planner) | 50 | 48 | 0 | 2 services, 8 report fields, all in `service_frontier` / `service_reliability` rows of those two services | the same two time-limited released solves (§14); decision, actions, gates, economics identical |
| unit fixtures A–G (`tests/unit/test_zaad_frontier.py`) | — | all at 1e-9 | | 0 | shared supplier, cash, MOQ / MOV, location volume, transfer network each one component; independent products one per SKU; whole-planner reports identical on `example("normal")`, `example("understock")` and three independent P1 products with an incumbent rule |

Planner decisions old vs new: identical on every request (status, selected policy, every action, incumbent actions,
candidate gates, economics, materiality, solve-quality statuses). Frozen canonical regression: PASS (P1 B / T / Q / A × 12
reviews order for order, P0 cell 15 identical) on the branch.

## 18. Replay after the frontier work (§18)

`scripts.replay_profile` with `HARVESTMIND_FRONTIER_MODE=component`, the same vaults, scopes, seeds, budgets and
`fefo_symmetry_scope="network"` as the sentinel-cleanup runs (`OPTIMIZER_SENTINEL_CLEANUP.md` §12.2); decisions compared
date by date against those runs (status, selected policy, executed orders, settled service).

| scope | before (sentinel record) | after | frontier before → after | plan wall median / p90 / max | MILPs (time-limited) | peak RSS | dates | decisions vs before |
|---|---|---|---|---|---|---|---|---|
| sample 50 × 8 | 6,231 s (104 min) | **1,911 s (32 min)** | 400 solves 4,331 s (15 at cap) → 201 solves **32 s** (0 at cap; 199 witness-proven) | 726 / 1,490 / 1,490 → **280 / 283 / 283 s** | 486 (34) → 287 (19) | 3,077 → **1,567 MB** | 8 / 8 | **identical orders, status and policy on 8 / 8**, identical service, identical window cost (1,679,933.69) |
| demo 25 × 26 | 6,574 s (110 min) | 6,248 s (104 min) | 650 solves 312 s → 137 solves **9 s** (513 witness-proven) | 199 / 467 / 470 → 185 / 454 / 455 s | 932 (68) → 419 (68) | 958 → 873 MB | 26 / 26 | identical orders, status and policy on 26 / 26, identical service and window cost |
| demo 10 × 26 | 8,337 s (139 min) | 8,303 s (138 min) | 260 solves 40 s → 47 solves **1.5 s** (213 witness-proven) | 274 / 543 / 544 → 272 / 542 / 542 s | 516 (87) → 303 (87) | 861 → 775 MB | 26 / 26 | identical orders, status and policy on 26 / 26, identical service and window cost |
| demo 5 × 26 | 5,158 s (86 min) | 5,140 s (86 min) | 130 solves 6 s → 24 solves 0.3 s (106 witness-proven) | 170 / 399 / 399 → 179 / 399 / 399 s | 382 (59) → 276 (58) | 653 → 656 MB | 26 / 26 | identical orders, status and policy on 26 / 26, identical service and window cost |

Every date of every replay completed; the decisions, settled service and window cost are identical to the sentinel-cleanup
runs on 86 / 86 dates. The demo replays (5 / 10 / 25 products) barely move because their frontier was already cheap (the
demo's products spread over more, smaller supplier components); the sample 50-product replay — the one the sentinel record
flagged at 70 % frontier — is 3.3× faster and fits 1.6 GB instead of 3.1. 50 × 26 was not run: at ≈ 240 s per date it would
be ≈ 1.7 h of a single process, practical now but not part of this pass's evidence; the 50 × 8 decision identity stands for it.
26 reviews at 5–25 products remain a 1.5–2.5 h run locally: the joint solves' 1e-6 proofs at their caps, not the frontier
(§21 of the brief: the replay is not yet "operationally usable" at 26 reviews, and this pass does not claim it).

What remains of a 50-product date is the joint recovery (710 s over 8 dates, 8 of 13 at the cap), the base-stock proxy
(556 s, 5 at cap) and the joint fitted solve (535 s): the honest 1e-6 proofs on real economics, not the frontier.

## 19. Infrastructure benchmark (§19) — set-up

Only after the software work: the **identical merged image** `registry.fly.io/zaad-api:canonical-328a294` (digest
`sha256:a8c9333c…`, the image production runs as v37) on two temporary one-shot machines in `fra`, started with
`fly machine run … -- bash -c '<benchmark>'` (no service, no traffic, destroyed after reading their logs; the production
machine `0804e0dfd1e948` untouched):

| machine | size | memory | why that memory |
|---|---|---|---|
| `bench-shared` `185e6dea5d74e8` | `shared-cpu-2x` (2 vCPU, AMD EPYC) | 2,048 MB | = production |
| `bench-performance` `d8939d0f119938` | `performance-2x` (2 dedicated vCPU, AMD EPYC) | 4,096 MB | Fly's minimum for the class (`invalid config.guest.memory_mb, minimum required 4096 MiB`); the 5 / 10 / 25-product plans peak below 1 GB, so memory does not enter the comparison; the 50-product plan (985 MB locally) is run on both |

Benchmark: `scripts.frontier_profile --vault sample --products 5,10,25 --plan` twice back to back (**cold** = the first plan
of each scope on a fresh machine, **consecutive** = the second pass immediately after), then 300 s idle, then a **rested**
pass with 50 products added; the same requests, scenarios, `solver_mip_gap`, threads and budgets as everywhere else in
this record. Wall, CPU, frontier and solver time, MILP statuses and peak RSS come from the script's own output.

*(results below when both machines report)*

## 20. Release record (2026-09-23)

| step | value |
|---|---|
| PR #95 | `perf/frontier-oracle-decomposition`; tested head `14ba8f49c876d793e5bfb0e8a5066c52e75beddc`; CI run 35882180173, 13 / 13 jobs (plus both Vercel previews; the first `Vercel – zaad` preview of an earlier head failed on a Google Fonts fetch inside `next/font` on Vercel's builder and passed on redeploy of the same commit) |
| merge | `328a294a00c7e5349685be0cc54a09e4cde9a4ff` (`Merge PR #95`, main was `b9d28cc`) |
| deploy | Fly `zaad-api` **v37**, image `canonical-328a294`, digest `sha256:a8c9333cce05bd3c2a2d342dc4ac39969ed620fa038c46047b4ef44c722e1da7`, deploy-api run 35885104825; machine `0804e0dfd1e948` `shared-cpu-2x` / 2 GB **unchanged**; no Fly configuration change; Vercel production `dpl_DoNrfbM7DpccU3FFGiUyGJ9HKRnW` (Ready, created at the merge push) |
| production smoke | `GET /health` 200 (0.46 s) on v37 |
| production planner QA | `production_plan_probe --self-serve --products 25` (throwaway sample workspace `op_8c12c21a`, the product's own request with every phase, job `job_ff24a607…`): **DONE in 306 s, RETAIN_INCUMBENT** (base-stock proxy 26 s OPTIMAL, incumbent OPTIMAL, `joint_recovery` FEASIBLE_TIME_LIMIT at 89.5 s, six candidate classes INFEASIBLE in 0.5–2 s) — on v36 the same request **timed out at the 788 s cap**. Reads during the solve: 176 reads, 0 errors; Insights summary 0.64 s idle → p95 12.5 s / max 15.0 s; inventory 0.41 → max 3.4 s; the shared vCPU still saturates while a plan runs |
| production replay QA (v37) | throwaway workspaces **FRONTIER QA DEMO (synthetic)** `op_171b96d3` (demo company loaded once, 1,800 s client timeout) and second tenant `op_db0f80db`; job `job_ede909f180`: `POST` 2.6 s, second press the same job; `queued` 9.5 s → `lanes` → `testing` → `replaying` → `done`, run 1,370 s. Replay **partial, 8 of 26 dates** in the 1,200 s budget (the same coverage as v36: the demo's 5-product date is the joint solves at their caps, solves mean 165 s / max 400 s, peak RSS 383 MB — the frontier was never its cost); study selection 5 of 36 products, 31 % of window demand value; every date RETAIN_INCUMBENT, 40 of 40 product-weeks identical to the incumbent; attestation clean on all legs; settlement basis actual 100 % measured, rule / ZAAD 3 % measured 97 % inferred; six consistency checks pass; report statements identical in substance to v36's (0.2 % less costly than the actual orders over the window, 3 of 8 periods better, worst period 2026-02-02 −110,615 JOD, confidence Low); PDF 41,140 bytes, 11 pages; payload 212 KB |
| tenant isolation | other tenant 404 / anonymous 401 on the job, `report.json` and `report.pdf` |
| runtime tag | `zaad-frontier-decomposition-runtime` = `328a294` (annotated; older tags untouched) |

## 21–23. *(filled as the pass proceeds)*
