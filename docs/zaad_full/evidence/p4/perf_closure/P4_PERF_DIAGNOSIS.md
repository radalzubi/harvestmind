# P4 production performance closure — diagnosis (before any formulation change)

Branch `perf/p4-recourse-performance-closure` from `main` `adf45e4` (runtime `8c813ac`, Fly v20).
Harness `scripts/p4_perf_profile.py` (observes only: build time from `Linear` creation to solve
entry, matrix assembly, warm-start completions as their own calls, HiGHS log per solve with
presolve reductions, coefficient ranges, first incumbent, B&B nodes, LP iterations; dimensions by
column class and per node; peak RSS). Raw record `P4_PERF_PROFILE.json`, HiGHS logs under
`highs_logs/`, planner-path replays under `highs_logs/replay_*`. Machine: local Apple laptop, quiet.
Every number below is measured on this candidate, not carried over from the release evidence.

## 1. Matrix

Classes A single SKU (P1 request), B P2 network, C two-source P3, D shared-supplier-order P3
(`C6_shared_mov_multi_sku`), E PRODUCE sector request (`P2_near_expiry_inventory`); worlds 3 / 6 /
8 / 12 / 16 as histories x continuations ^ epochs with one and two epochs (16 = 4 x 2 x 2). For
every cell: the three tree solves of `policy.compare` (static / adaptive / perfect information,
`service_floor=True`, no planner terms) with logs, then the whole `plan()` (the production path)
with every candidate solve timed.

## 2. What the numbers say (tree solves, compare path)

| class | worlds (h, epochs) | rows / cols / binaries (adaptive) | binaries by class | node columns (purchase / transfer) | static s / nodes | adaptive s / nodes | PI s / nodes |
|---|---|---|---|---|---|---|---|
| A single SKU | 12 (3, [3,6]) | 6,373 / 6,096 / 1,872 | fefo 1,728, depleted 144 | 45 / 0 | 12.4 / 1,777 | 0.44 / 1 | 0.11 / 1 |
| A single SKU | 16 (4, [3,6]) | 8,496 / 8,127 / 2,496 | fefo 2,304, depleted 192 | 60 / 0 | 17.1 / 1,362 | 2.1 / 1 | 0.12 / 1 |
| B P2 network | 16 | 10,332 / 15,333 / 384 | depleted 384 | 60 / 1,560 | 0.73 / 1 | 0.29 / 1 | 0.20 / 1 |
| C two-source P3 | 16 | 10,395 / 15,396 / 384 | depleted 384 | 60 / 1,560 | 0.8 / 1 | 0.47 / 1 | 0.4 / 1 |
| D shared order | 6 (3, [3]) | 7,338 / 11,790 / 318 | order 30, depleted 288 | 108 / 1,404 | 4.4 / 1 | 2.0 / 2 | 2.3 / 17 |
| D shared order | 8 (4, [3]) | 9,765 / 15,663 / 423 | order 39, depleted 384 | 144 / 1,872 | 8.4 / 7 | 6.8 / 3 | 10.7 / 24 |
| D shared order | 12 (3, [3,6]) | 14,538 / 22,896 / 624 | order 48, depleted 576 | 180 / 2,340 | 7.8 / 1 | 8.0 / 4 | 11.7 / 146 |
| D shared order | 16 (4, [3,6]) | 19,365 / 30,471 / 831 | order 63, depleted 768 | 240 / 3,120 | 12.0 / 11 | 20.6 / 27 | 33.5 / 612 |
| E produce | 8 (4, [3]) | 8,325 / 8,551 / 1,984 | fefo 1,792, depleted 192 | 36 / 712 | 21.1 / 2,128 | 10.3 / 444 | 0.2 / 1 |
| E produce | 12 (3, [3,6]) | 12,448 / 12,548 / 2,976 | fefo 2,688, depleted 288 | 45 / 840 | 37.1 / 2,266 | 42.9 (time limit, gap 0.66 %) / 2,773 | 0.55 / 1 |
| E produce | 16 (4, [3,6]) | 16,589 / 16,703 / 3,968 | fefo 3,584, depleted 384 | 60 / 1,120 | 43.0 (no incumbent) / 2,153 | 42.9 (time limit, gap 1.6 %) / 1,201 | 0.57 / 1 |

Matrix coefficient range on every cell: `[6e-02 .. 1e+06]`; the 1e6 is the location capacity
(`capacity_volume` 1e6, volume 1) used as the big-M of the `depleted` and `fefo` indicator rows and
as the upper bound of every inventory column. Presolve removes 45-55 % of rows and columns but
none of the binaries of the dominant class. Build time is 0.003-0.44 s per solve (matrix assembly
included); construction is not the cost anywhere.

## 3. What the numbers say (planner path)

| class | worlds | planner wall | candidate solves | of which tree solves (static comparator / adaptive / PI) | verdict |
|---|---|---|---|---|---|
| A | 8 | 2.4 s | 8 | 0.6 / 0.5 / 0.1 | NO MATERIAL ADAPTIVE BENEFIT |
| B | 8 | 1.0 s | 12 | 0.6 / 0.1 / 0.1 | same |
| C | 8 | 1.1 s | 13 | 0.4 / 0.2 / 0.2 | same |
| D | 8 (4, [3]) | 59.8 s | 19 | 8.4 / 6.8 / 10.7 | same |
| D | 12 (3, [3,6]) | 177 s | 19 | 7.8 (seeded, 5 nodes) / **78.0 time limit, 923 nodes** / **78.1 time limit, 2,389 nodes** | NOT SELECTED (time-limited adaptive did not beat static) |
| D | 16 (4, [3,6]) | 193 s | 19 | 20.9 (seeded, 5 nodes) / **78.1 time limit, 101 nodes** / 78.1 time limit | NO MATERIAL ADAPTIVE BENEFIT |
| E | 8 (4, [3]) | 60.2 s | 13 | 21.7 (of which **18.9 s warm-start completion**) / 10.7 / 0.2 | same |
| E | 12 (3, [3,6]) | 93.0 s | 13 | 17.2 time limit (after **25.9 s completion**) / 43.0 time limit / 0.6 | NOT SELECTED |
| E | 16 (4, [3,6]) | 95.6 s | 13 | 43.0 (no incumbent, after completion) / 43.0 time limit / 0.6 | NOT COMPARABLE |

The planner budget per tree solve is `solve_budget(req)` = 78 s for D (breadth 5.2 x margin) and
42.9 s for E. The tree solves are 156 of 177 s on the heaviest D cell and 61 of 93 s on E; the
other 16 candidate solves cost 5-20 s in total.

## 4. Root-cause questions (section 7 of the brief), answered by measurement

| question | finding |
|---|---|
| A repeated supplier-order activation binaries per information set | real but small: `order` binaries 12 -> 30 / 39 / 48 / 63 per node set; the dominant binary class on D is `depleted` (576-768), one per (SKU, service, period, world), which scales with worlds, not nodes |
| B loose big-M multiplied across nodes | the `depleted` / `fefo` rows use M = location capacity / volume = 1e6 on every class; the supplier-order rows on D already carry the exact activation bounds of the P3 closure. The 1e6 is data (declared unlimited capacity), replicated per world and per node |
| C weak MOQ / MOV activation relaxations | not the driver on D: the compare-path adaptive solve of the 16-world cell needs 27 nodes; the planner-path solve of the same model needs hundreds and hits the limit - the difference is the planner's terms, not the MOV rows |
| D shared-capacity linking | none on D (no shared resource) |
| E source switching binaries | none in these requests |
| F symmetry between equivalent information-set policies | not observed: node columns are distinct decisions with distinct world sets; no symmetric block |
| G duplicated world-path rows | share / switching / smoothing rows are per path only when declared (not here); cash / payment rows are per world by the frozen design |
| H redundant cash / payment / resource rows | presolve removes ~50 % of rows; none of the remaining binaries |
| I static / adaptive / PI repeated construction | three builds of 0.1-0.4 s: negligible |
| J warm start | the adaptive tree solve has NO seed (the static comparator is seeded with the incumbent); the PI solve has no seed. `warm_start_vector` maps a static plan onto node columns by (source, period) ignoring the node, so a static seed IS the static policy copied into every node (feasible by construction). Measured in section 5 |
| K unnecessary candidate solves | the PI solve is report-only and costs as much as the adaptive solve on D (33 s at 16 worlds compare path, 78 s time-limited planner path) |
| L construction overhead | build 0.003-0.44 s; the E "build" of 19-26 s is the static comparator's warm-start completion (two `complete()` MIPs), recorded separately once instrumented |
| M proof time after a good incumbent | E: first incumbent at 20-38 s of a 43 s budget (compare path), the rest is proof; D planner path: first incumbent early, hundreds of nodes without proof |
| N P3 shared-order x P4 node multiplication | node columns 108 -> 240 purchases and 1,404 -> 3,120 transfers, order binaries 30 -> 63: growth is linear in nodes; the time growth (2 s -> 21 s compare, 8 -> 78+ s planner) is the B&B, not the size |

## 5. Experiments (planner-path replays of the heavy cells, `tree_solves.py`)

See `P4_PERF_LOG.md` for every run and `P4_PERF_RESULTS.md` for the before / after table.

| # | cell | experiment | result | decision |
|---|---|---|---|---|
| 2 | D shared order, 12 worlds | planner-path replay; adaptive seeded with the static comparator (static policy in every node via the existing `warm_start_vector`) | adaptive 78 s time-limited (incumbent 25,346.17, dearer than static 25,320.81) -> **40 s OPTIMAL 25,318.43** (69 nodes); PI unchanged (naive seed maps no node plan; proof-bound) | **ACCEPTED** (warm start only; problem unchanged) |
| 3 | E produce, 12 worlds | planner-path replay | static comparator loses 25.8 s to a rejected warm completion then finds nothing in 17 s; adaptive first incumbent at 37.6 s of 42.9; PI 0.7 s | no warm start possible without a static plan; FEFO indicators are the structure |
| 4 | D, E | indicator rows (`depleted`, `fefo`, `priority`, `direct_first`) with M = opening + inbound + Σ activation bounds instead of capacity / volume | D: objectives identical, no time saved beyond the warm start, PI still time-limited; E: large gains but the harness M (600) was NOT a valid bound (activation bounds exist only in the shared-order class) | D: rejected (not the driver); E: deferred - needs a per-line undominated bound proven for every line |
| 5 | E, 12 worlds | certification of the loose optima with a 900 s budget | static 13,424.64 in 74 s, adaptive 13,329.38 in 90 s: the 43 s budget is genuinely binding on produce at 12 worlds; the released incumbent is 0.52 % above the optimum | recorded; no gate change |

## 6. Root cause

The production-relevant cost of P4 is not model size, construction, or the P3 shared-order rows
per node; it is that the adaptive tree solve starts from nothing while a feasible policy (the
static comparator's plan, already solved and seeded from the incumbent) is at hand, and that on
the shared-order class HiGHS then spends the whole budget on a branch-and-bound that ends with a
non-certified incumbent dearer than the static optimum. Seeding the adaptive solve with the static
policy (exact: a warm start) halves the heavy-class tree solve and returns a proven optimum where
the released runtime returned a time-limited incumbent. The perfect-information solve on the
shared-order class is proof-bound (dual bound, not incumbent) and stays NON_CERTIFIED at its budget;
it is report-only and does not gate anything. The produce class is bounded by its FEFO indicator
structure; a valid stock bound for those rows is the identified but unproven next exact change.

## 7. Decomposition audit (section 10 of the brief)

Coupling graph of the frozen joint model on the profiled requests. Nodes: SKU, supplier, location,
information-set node, service, resource. Edges when entities share:

| coupling | present on | effect |
|---|---|---|
| supplier MOV / fixed order fee (a supplier order linking lines of several SKUs) | D (both SKUs, both suppliers) | one `order` binary per (supplier, period, node) joins every SKU of the supplier: no SKU-level component |
| cash / credit rows (per period, per world) | every request with a liquidity record (all profiled) | every purchase and every service of a world sits in the same cash row: no component below "the whole request" |
| lanes / network inventory (central -> branch transfers, conservation per world) | B, C, D, E | every location of a SKU joined per world |
| source shares / switching | none declared here | (per world path when declared) |
| common physical resource | none here | (per node when declared) |
| information-set nodes | all recourse solves | a node joins its member worlds' rows on the same column - the intended coupling of P4 |

Result: on every profiled class the coupling graph is one connected component (cash alone makes
it so, and on D the shared supplier order does as well). No exact decomposition is available, and
none was attempted: decomposing across cash, a shared order or a lane would change the feasible
economic set. The single-SKU class A is already one component by construction.

## 8. Warm-start audit (section 11 of the brief)

| seed | mechanism | feasible for the target? | measured |
|---|---|---|---|
| static comparator's plan -> adaptive tree solve | existing `warm_start_vector` (maps by (line, period); the node suffix is ignored, so every node receives the static value); completion `equal` accepted in 0.05-0.09 s on D | yes by construction (a static policy is an adaptive policy with identical nodes); the completion verifies it against every row | D 12 worlds: 78 s time-limited -> 40 s OPTIMAL; first incumbent 0.5 -> 0.2 s; proof 69 nodes; E: available only when the static comparator returns a usable plan |
| previous rolling-review solution mapped forward | not available in the planner (one review per request) | - | not measured; a replay-level seed is outside this closure |
| current incumbent (the rule / selected candidate on the selection draw) -> static tree comparator | already released (`seed=incumbent`) | its floors may not hold on the tree worlds: completion `equal` fails and `floor` runs to its cap on E (25.8 s of 42.9) | recorded; unchanged (a request setting) |
| adaptive plan -> perfect-information solve | naive (root columns only): accepted after a `floor` completion; the per-world node plans are not mapped | feasible but weak | proof-bound on D (2,400-3,300 nodes at 78 s either way); trivial on A / B / C / E; not adopted |

SciPy's `milp` has no warm-start interface; the seed path is the released highspy route
(`Linear.solve(seed=...)`), unchanged.

