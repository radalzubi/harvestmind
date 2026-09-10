# P2 multi-echelon / network optimization: architecture decision record

Branch `claude/zaad-meio-p2`, worktree `harvestmind-p2`, parent `11f5459` (canonical `main`, tags
`p0-frozen` = `2e30721`, `p1-frozen-product` = `f7e1e62`, `p1-frozen` = `12db66c` unchanged).
Written after the read-only audit and before the P2 benchmark. P0 and P1 stay frozen.

## 1. What the audit found in the frozen core

The frozen optimizer (`zaad/full`) is already a **joint network MILP**, not a single-node engine:

| network requirement (brief) | where the frozen core already provides it |
|---|---|
| locations, lanes, supplier relationships, pipeline | `contracts.Location` (kind, capacity, holding rate, receiving calendar), `Transfer` (lane: lead, capacity, cost, loss, approval), `Source` (per destination), `OpenPO`, `InboundTransfer` |
| exact inventory conservation, no double counting | `model.solve`: one balance row per SKU / location / cohort / period / world (opening + arrivals - use - outbound = closing); transfers are scenario-invariant decision variables, so one unit leaves the origin's balance and enters the destination's in every world; period-0 outbound bounded by usable opening stock; `settlement.settle` recomputes conservation independently and refuses phantom stock |
| reachability, transfer physics | transfer variables exist only for cohorts that survive the lane; arrival = lead + receiving calendar; capacity per lane-period; loss fraction; cost per unit |
| shared upstream supply | shared `Resource` capacity rows across sources; one balance per origin cohort, so branches cannot both draw the same central unit |
| service per location, allocation | one service floor (expected or CVaR) per `Service` = per (SKU, location, customer); customer-priority rows; `joint_recovery` (service-first, priority-weighted) when targets are jointly impossible; `NETWORK_ALLOCATION` screen state |
| pooling accounting | `capital.pooling_split`, `capital.duplication`, `protection` placement (local vs pooled units), `echelon` base-stock comparator (v6), alternates valuation of lanes |
| terminal / continuation | per (SKU, location) continuation slabs (P1 cycle basis) and terminal value per cohort |

What the frozen core does **not** have, and P2 adds:

1. **Cross-branch demand correlation.** `worlds.draw` samples every service independently (own
   bootstrap path, own level shock). Risk pooling is worth exactly the diversification between
   branches, so a network needs the joint structure. Supply already carries shared failure domains.
2. **Transfer packs and per-dispatch cost.** Lanes were continuous with a per-unit cost only.
3. **A network incumbent.** The declared operator rules (`replace_sold`, `periodic`,
   `reorder_point`, `economic_lot`) are purchase-only and their projection never transfers; on a
   network the incumbent then starves the branches and ZAAD "intervenes" trivially.
4. **Per-location flow accounting, reachability and allocation explanations, stranded-stock
   reporting, per-branch service breach / starvation, node + lane + upstream reconciliation.**
5. **Network baselines and a network fixture matrix** (the P1 fixtures are single-branch; the v6/v7
   cells have a central + two branches but no independent-branch or pooled-rule comparator and no
   correlation in the planner's worlds, only in the truth).
6. **A multi-location workspace adapter** (the canonical adapter plans one location, `main`) and
   **network resource bounds on the API** (locations and lanes had no interactive bound).

## 2. Architectures considered

**A. Joint network MILP (all locations and transfers in one solve).** This is what the frozen core
already is. Correct by construction on conservation, shared resources and reachability; scales with
worlds x periods x cohorts x pairs; measured 5.4 s per stochastic solve on central + two branches at
H = 12 (frozen `solve_budget` note), 10-25 s per review with adaptive escalation.

**B. Decomposed echelon planner** (central allocation / purchasing layer + local planners +
coordination iterations). Rejected: it would re-implement node physics outside the frozen model,
lose exactness on shared central stock and supplier capacity (each local planner sees the same
central unit unless a master problem re-derives the same balance rows), and require a convergence
argument for the coordination loop. Its only advantage, runtime, is not needed at the canonical
topology (measured above) and is better obtained by candidate discipline.

**C. Hybrid candidate / joint settlement** (frozen node-level candidates + a network master problem
over them). Rejected as a second engine: the frozen candidates are already network-wide solves, so a
master problem over node candidates would either duplicate the joint MILP or reintroduce the double
counting of central stock that B suffers.

**D. Frozen joint MILP as the single decision engine + an additive P2 network layer (chosen).**
No second engine. P2 supplies what section 1 lists as missing: the joint scenario structure, the
transfer physics the contract lacked, a network incumbent the selector can compare against, and the
network view / accounting / explanations / baselines / fixtures / adapter / bounds around the frozen
decision. Ownership is unchanged: P1 owns ordinary purchasing economics, P0 owns protection and
recovery; the P2 **network router** names the contested shared resources and the affected locations
before the frozen planner runs and never overrides it.

Evaluation against the brief's criteria (A/B/C/D): mathematical correctness (D = A, exact; B/C
approximate), service guarantees (per-location floors inside the solve: A/D), conservation (A/D
exact by rows and by settlement), shared resources (A/D), uncertainty (A/D through worlds; P2 adds
correlation), scalability (A/D polynomial in pairs x cohorts; measured in the scalability
diagnostic), runtime (A/D as measured; B would be faster but wrong on shared stock), explainability
(D adds the layer), P0/P1 compatibility (D reuses them unchanged), more locations later (D: the
contract already allows 100 locations; the layer is topology-generic), failure modes (D inherits
the frozen fail-closed settlement and solve-quality gates).

## 3. What P2 changes in frozen files (all default-off or telemetry; identity evidence required)

| file | change | identity guard |
|---|---|---|
| `contracts.py` | `Transfer.multiple`, `Transfer.fixed_cost_per_dispatch` (default 0); `IncumbentTransfer`, `Request.incumbent_transfers` (default empty); `Request.demand_correlation` (default 0); `incumbent_rule` may be `network:rop` / `network:pool` | defaults reproduce the frozen contract; validation only adds rules for the new fields |
| `worlds.py` | when `demand_correlation > 0` and the request has two or more services, uniforms and level shocks come from `correlation.copula_draws`; otherwise the frozen stream is consumed exactly as before | bit-identical draws at 0 and on any single-service request (tested) |
| `correlation.py` (new) | Gaussian copula per SKU group with the declared correlation; marginals unchanged | not on the frozen path |
| `model.py` | per lane-period integer pack variable when `multiple > 0`; per lane-period dispatch binary when `fixed_cost_per_dispatch > 0` | no variable or row is added at the defaults |
| `settlement.py` | pack check on the executable period-zero transfer; dispatch cost in the transfer ledger; **flow telemetry** (`flows`, `transfer_events`) read from the settlement's own state | economics unchanged at the defaults; telemetry only adds keys |
| `planner.py` | the declared incumbent carries `incumbent_transfers`; the rule incumbent carries the rule's transfers (frozen rules return none); `recovery_guidance.weighted_service_shortfall` made JSON-safe (None instead of inf) | frozen rules and empty incumbent transfers reproduce `transfers={}` |
| `replay.py` | a `NETWORK_METHODS` registry consulted before the frozen method table; the rule incumbent's transfers become `incumbent_transfers` at every review | empty registry and transfer-free rules reproduce the frozen path |
| `policies.py` | `baseline_plan` dispatches `network:*` rules to `zaad.meio.baselines` | frozen rules untouched |

Identity evidence: `scripts/zaad_canonical_regression.py` (B, T, Q, A twelve-review identity; P0 cell
15) and the frozen unit suite; recorded in `P2_P0_P1_ISOLATION.md` at freeze.

## 4. The P2 layer (`zaad/meio`)

* `topology.py`: `network_state` (nodes with roles and echelons, lanes with the earliest landing
  period, positions, reachability = local-only periods per fed SKU / location, stranded stock,
  shared suppliers / resources / origins, structural issues, interactive bounds).
* `planner.py`: `network_router` (contested origins over the reachable window, contended shared
  capacity, unreachable stock; reasons only) and `plan_network` = frozen `plan` + network block.
* `accounting.py`: per-location flows with the conservation identity checked on every row, lane
  usage (capacity, packs, dispatches, reverse-pair movement), per-location service with breach and
  severe-starvation flags, demand- and priority-weighted network service, stranded stock, node /
  lane / upstream / network economic buckets reconciled to the settlement ledger.
* `explain.py`: operator-facing reasons for purchases, transfers, central holds, allocation under
  scarcity, do-nothing and rejection; diagnostics keep the numbers.
* `baselines.py`: `network:rop` (incumbent network policy, Baseline C), `network:pool` (simple
  central pool, Baseline B), `independent_branch_requests` (Baseline A: the frozen optimizer per
  isolated branch with a virtual supplier through the lane).
* `fixtures_p2.py`: the central + N branches builder with every input declared.

## 5. Decisions taken deliberately

* **First production topology: central -> branch lanes.** Branch -> branch and branch -> central
  lanes are accepted by the schema and the model; `validate_network` flags zero-cost reverse pairs
  because nothing then prices a loop out; the accounting reports `ping_pong_units` per lane; the
  fixture matrix includes a reverse-lane adversarial case. The workspace adapter builds central ->
  branch lanes only unless the operator declares others.
* **Correlation groups are SKUs.** Demand for one product across branches is what pools; a
  cross-product factor is not represented (declared limitation).
* **Correlated worlds replace the LHS strata.** The P1 stratified sampler is per-service; with a
  copula the strata are dropped for that request (recorded in the world label `:rho`).
* **No new decision candidates.** The frozen candidate classes are network-wide solves; the
  network decision (hold central vs pre-position, transfer vs buy, allocate) is endogenous to them.
  Anything that looked like a needed candidate in development is recorded in `P2_DEVELOPMENT.md`.
* **Continuation economics at a central without customers** (a P1-owned review values branch
  residual stock by the cycle continuation but central residual at salvage) is audited in the
  development experiments before pre-registration; the decision is recorded there, never silently.
