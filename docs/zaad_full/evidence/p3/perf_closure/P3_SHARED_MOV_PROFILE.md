# P3 shared-supplier-MOV production case: end-to-end profile

Scope: the one unresolved P3 release issue. The production smoke `payload.shared_mov` (release
ledger, Fly v17, runtime `0de6850`) measured **218.4 s** against the declared 180 s interactive
bound. Everything below is measured, not inferred.

## The exact workload

`shared_mov_prod_snapshot.json` is the request the release smoke posted, byte-for-byte apart from
the `operator_id` the smoke substitutes with the authenticated workspace (a label; no effect on the
model). It is fixture `C6_shared_mov_multi_sku` at seed 41001, dumped with the smoke's interactive
settings.

| dimension | value |
|---|---|
| SKUs | A, B (shelf life 52 periods, terminal value 4.0) |
| locations | central (DC), north, south (branches); 4 approved lanes (A and B to each branch, 1 period, 0.2 / unit) |
| services | 4 (unit fill 0.95, selling price 10, SLA 2.5 per unmet); demand about 100 / period / branch |
| sources | `src_A`, `src_A_B` (supplier `supplier`, 5.00 / unit), `src_S2`, `src_S2_B` (supplier `supplier_s2`, 5.40 / unit); no freight, handling, MOQ, packs or fees; lead 7 days; declared capacity 1,000,000 / period; maximum 1,000,000 |
| supplier terms | `supplier`: minimum order value 5,000, fixed order cost 150 (CONFIGURED_ASSUMPTION); `supplier_s2`: none |
| resources | `supplier_cap`, `cap_supplier_s2`: 1,000,000 / period |
| sourcing | PORTFOLIO, incumbent shares A: `src_A` 1.0, B: `src_A_B` 1.0 (OPERATOR_DECLARED); no groups, share rows or switching costs; `prune_zero_capability` true |
| horizon / period | 12 periods of 7 days |
| worlds | 3 selection scenarios (stratified), 1 declared nil stress |
| incumbent | `network:rop` |
| solver | HiGHS, `max_solve_seconds` 5, adaptive budget (margin 1.3, ceiling 90 s) -> 26 s per solve; MIP gap 1e-6; warm start on above 3,000 variables; cadence candidates on |
| sector | none (`sector_mode` null) |
| route | `POST /api/zaad/network/plan` -> `zaad.meio.planner.plan_network` -> `zaad.full.planner.plan` |
| seed | 41001 |

## Local reproduction (runtime `1e712c9` == `0de6850` for every runtime file)

Apple laptop, Python 3.14, scipy 1.17.1 (bundled HiGHS on the frozen route), highspy 1.14.0 (warm-started
solves). Harness: `local_profile_shared_mov_before.json` (every HiGHS call attributed to its candidate).

| phase | seconds | share |
|---|---|---|
| request validation / normalisation | < 0.01 | - |
| forecast fit, supply profiles, protection profile, screen | 0.01 | - |
| world generation (`draw`, all sets) | 0.05 | 0.3% |
| model construction (Python rows + sparse matrix) | 0.35 | 2% |
| **HiGHS (18 calls)** | **17.06** | **96%** |
| settlement / evaluation of every candidate | 0.12 | 0.7% |
| network accounting and explanations (P2 layer) | 0.01 | - |
| report construction and sourcing block | < 0.05 | - |
| JSON serialisation (131 KB) | 0.003 | - |
| **end to end** | **17.55** | |

Solver calls, in order (budget 26 s each; every one proved optimal locally):

| # | candidate | worlds | variables | binaries | rows | nonzeros | nodes | seconds |
|---|---|---|---|---|---|---|---|---|
| 1 | base_stock (projected base-stock proxy, targets) | 1 | 2,476 | 60 | 1,363 | 9,462 | 1,214 | 4.68 |
| 2 | incumbent (network:rop plan, fixed) | 1 | 2,364 | 60 | 1,979 | 9,870 | 0 | 0.02 |
| 3 | deterministic_network (analytic shortage surrogate) | 1 | 2,472 | 60 | 1,969 | 18,228 | 260 | 2.57 |
| 4 | stochastic_network (warm-started from the incumbent: 2 completion solves 0.12 s) | 3 | 5,904 | 156 | 3,759 | 26,860 | 13 | 4.03 |
| 5 | cadence_2_network | 3 | 5,904 | 156 | 3,759 | 26,860 | 3 | 1.30 |
| 6 | cadence_4_network | 3 | 5,904 | 156 | 3,759 | 26,860 | 1 | 1.16 |
| 7-10 | service frontier oracle, one two-phase solve per service (report only) | 1 | 2,364 | 60 | 1,308 | 9,210 | 84 / 82 / 51 / 49 | 0.40 / 0.47 / 0.38 / 0.64 |
| 11 | value of alternates (report only, `alternates` disabled) | 3 | 5,724 | 156 | 3,657 | 26,122 | 5 | 1.65 |
| 12 | value of transfers (report only, infeasible without lanes) | 3 | 5,724 | 156 | 3,657 | 26,122 | - | 0.06 |

Binaries: 12 first-stage supplier-order binaries (`order`, one per supplier and period; **not**
replicated per world) and 48 `depleted` no-hoarding indicators per world (frozen P0 semantics).
There are no pack, MOQ, activation, quote-group, switching, FEFO or priority binaries in this
request. HiGHS presolve on the base model: rows 1,363 -> 617, columns 2,476 -> 1,089; on the
stochastic model rows 3,657 -> 1,675, columns 5,724 -> 2,449 (`highs_logs_local_before.txt`).

Decision (local, before): `stochastic_network` selected, state NO_ACTION, owner PURCHASING_ECONOMICS,
COMMIT_AS_INCUMBENT_MIX on both pairs (A: `src_A` 2,808.7 / `src_S2` 24.6; B: `src_A_B` 2,831.1 /
`src_S2_B` 29.0), period-0 purchases `src_S2` 24.6 and `src_S2_B` 29.0, MATERIAL_IMPROVEMENT,
approval required, no executable order.

## Fly reproduction (runtime `0de6850`, v17, machine `0804e0dfd1e948`, shared-cpu-2x, 2 GB)

The exact snapshot through the production route on a synthetic self-serve workspace
(`fly_before_shared_mov_full.json`): **76.2 s**, every candidate OPTIMAL, the same decision as the
local run (stochastic_network, same purchases, same shares).

| candidate | local s | Fly s | ratio |
|---|---|---|---|
| base_stock | 4.68 | 19.3 | 4.1 |
| deterministic_network | 2.57 | 8.9 | 3.5 |
| stochastic_network | 4.03 | 19.7 | 4.9 |
| cadence_2_network | 1.30 | 5.8 | 4.5 |
| cadence_4_network | 1.16 | 3.0 | 2.6 |
| incumbent | 0.02 | 0.1 | - |

So the release-smoke figure of 218.4 s was not this request's steady-state cost on the machine: it
was the same request on a **throttled** shared CPU. The guest's own counters show it: at the time of
this profile `/proc/stat` on the machine read user 27,087, system 1,237, **steal 51,803** jiffies -
the hypervisor had withheld about two thirds of the machine's busy time since boot. The release
smoke posted 30 payloads back to back; `shared_mov` was the seventeenth plan call after several
long solves, and the other two slow smokes show the same signature (multi-SKU capacity 77.6 s on
Fly against 2.5 s locally, 31x; correlated plant group 45.6 s against 3.8 s, 12x). On the release
run the 26 s budget was reached on most candidate solves and the selector chose `cadence_4_network`
with a different, time-limited allocation (period-0 `src_A` 650 / `src_A_B` 654.7): the throttled
machine was not only slower, it produced weaker solves.

## Classification of the time

| class | before, local | note |
|---|---|---|
| A request / workspace construction | < 0.1% | |
| B world generation | 0.3% | |
| C model construction | 2% | |
| D primary optimisation (base_stock, deterministic, stochastic, 2 cadences) | 78% (13.7 s) | 6 candidate solves; base_stock alone 27% |
| E incumbent evaluation | 0.1% | fixed plan, no branching |
| F alternate-policy valuation (alternates / transfers) | 10% (1.7 s) | report only |
| G service frontier oracle | 11% (1.9 s) | report only, 4 two-phase solves |
| H settlement | 0.7% | |
| I reporting | < 0.3% | |
| J serialisation | < 0.1% | |
| K repeated candidate solves | 0 | every solve is a distinct candidate or valuation; nothing is rebuilt twice |
| L Python orchestration (everything else) | about 3% | |

## Root cause

Two things, both in the solver's work and both measured directly on the models above:

1. **Loose big-M on the supplier-order linking rows.** `purchase[s, t] <= M * order[supplier, t]`
   used the declared line capacity as M: here 1,000,000 units against a 5,000 minimum order value
   and about 2,400 units of demand a purchase can ever serve. The relaxation sets
   `order = purchase / 1,000,000`, so neither the 150 fixed cost nor the MOV is priced until the
   solver branches. Rebuilding the same three models with a 6,000-unit M gave identical objectives
   with base_stock 4.5 s / 1,214 nodes -> 0.06 s / 1 node, and the oracle solves 84 -> 1 node.
2. **Root work the solver repeats after its own restart.** With the bound tight, the 3-world solves
   still spend 1.4 - 3.7 s at the root: separation, sub-MIP heuristics and then a HiGHS "restart"
   (2 % inactive integer columns -> re-presolve, redo the root). Disabling the restart halves every
   candidate solve for the same optimum (deterministic 1.9 -> 1.0 s, stochastic 3.7 -> 1.4 s,
   cadence_2 2.3 -> 1.4 s); heuristic effort, scaling, pricing, cut pool and LP-age settings change
   nothing (`sweep` records in `local_profile_*`). The `depleted` indicators' own big-M (the storage
   capacity) was tested and is **not** a driver: tightening it to 20,000 or 2,000 left the solve at
   1.4 - 2.4 s.

Everything else - request build, worlds, settlement, reporting, serialisation, Python overhead -
is under 4 % of the wall time and is not the problem. There is no duplicated first-stage binary
per world, no repeated solve of the same model, and nothing to cache: the 18 calls are 12 distinct
candidate / valuation models plus warm-start completions.

The factor between local and Fly (4-5x unthrottled, 12-31x throttled) is the machine class, not
the formulation. The closure therefore (a) removes the formulation pathology exactly, (b) takes the
one search setting that measurably halves the remaining root work, and (c) records the CPU steal on
the production machine so the residual environment risk is named rather than hidden.

## Scope of the correction, and why it is this narrow

The two changes are exact on every request they touch (identical candidate optima), but they change
HiGHS's search path, and the frozen benchmarks are sensitive to search path wherever the objective
is flat: transfer timing between two lanes of equal cost, or two sources with the identical landed
price, are ties the model does not break. A first, broader version of the closure (bounds and
search settings on every request with an activation binary) was run against the whole P3 matrix:
every candidate solve on every fixture returned the same objective as the released runtime, yet
192 of 2,304 replay reviews differed - all of them tie representatives - and two fixtures turned the
tie into a different gate outcome:

* `E4_moq_mov_small_order`: every candidate plan of review 0 is bit-identical to the released
  runtime (deterministic 8,892.0444, stochastic 8,742.2727, cadence 2 8,845.7112, cadence 4
  8,887.6139), but the cadence-4 candidate's transfers landed on the other representative of an
  equal-cost tie, its out-of-model stress confirmation then read a worse downside on the
  confirmation worlds (south service 0.9993 -> 0.9778), the selector moved to the next qualified
  candidate, and the replayed trajectory ended 2.14 % above the cheapest-landed comparator against
  the fixture's 2 % tolerance.
* `R4_shared_plant_no_fake_diversification`: `src_A` and `src_B` carry the identical 5.00 landed
  price and share the plant; the plan flipped from an A / B period split to all-B (the same
  representative production v17 returned), so the "share the same origin plant" sentence, which is
  written when both members are used, was absent and the `no_split` principle's sentence check
  failed.

Neither is a change in optimisation quality, and neither can be fixed without either retuning a
fixture or adding a tie-break term to the frozen objective - both out of scope. A second, still
broad version (every request with a shared supplier order, P3 or not) kept the whole P3 matrix
green but moved the P1 canonical fixture `T_combined_realistic` (a shared-order request with pack
lattices and no P3 block) and thirteen `echelon_base_stock` replay reviews of the mixed-sector
fixtures, again on ties. The closure is therefore scoped to the exact class of the blocker: **a P3
sourcing review (`sourcing` declared) in which a supplier order - MOV, fixed cost, receiving fee or
tariff - links purchase lines of more than one SKU** (`shared_supplier_orders`). Inside that class
the activation bounds and the order-class search apply; outside it nothing changes and the released
runtime's solver route, formulation and tie resolution are kept bit for bit, so every frozen P0, P1,
P2 and sector request is untouched by construction and the gates confirm it. Under the scoped code
`E4` and `R4` reproduce the released candidates, selection and explanations exactly; the only P3
fixture in the class is `C6_shared_mov_multi_sku`, whose review-0 candidates are identical on both
seeds (`tie_evidence/c6_*`) and whose 31 differing replay reviews are the cascade of one
equal-cost transfer tie at review 0.

The same loose big-M sits under the P1 shared-order class (fixture T) and the single-SKU MOV / MOQ
class (E4, S4); both would benefit from the same bound and search and are recorded for the global
performance phase, where their tie representatives can be re-baselined together.
