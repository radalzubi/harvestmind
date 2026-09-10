# P2 multi-echelon / network optimization: pre-registration

Written on branch `claude/zaad-meio-p2` BEFORE the authoritative benchmark run (`p2_authoritative`).
Nothing in this file is changed after that run; corrections, if any, are appended in a dated section
at the end and never edited in place. Development experiments (`P2_DEVELOPMENT.md`) preceded this
file and are the only place where fixtures, comparators and gates were iterated.

## 0. What is fixed

P0 and P1 optimizer semantics (untouched: no retuning, B, continuation economics, rule P1-S, T-A, the
service floor, P0 recovery and ownership). The frozen candidate classes and selector. The P2 layer as
committed at the SHA recorded in `P2_CLOSEOUT.md`. The fixture file `scripts/p2_fixtures.py` (the
matrix below is generated from it; the file is the authority), the seeds, the review counts, the
tolerances, the service modes, the validity rule, the runtime gate, the invariants, the adversarial
list and the scalability diagnostic. No threshold is set after seeing an authoritative result.

## 1. Fixtures (canonical topology: one central DC fed by one supplier, two branches fed by lanes)

Built by `zaad.meio.fixtures_p2.p2_request` with every economic and physical input a
CONFIGURED_ASSUMPTION: demand 100 / week per branch (K: 300 / 50), unit price 5, salvage 80%, holding
15% / year, supplier lead 7 days, fill .98, lane lead 1 review, lane cost .20 / unit (4% of price),
service target .95, priority 1, weekly periods, twelve-period horizon, `network:rop` as the declared
incumbent policy, correlated demand only where declared. Deviations per fixture:

| fixture | what deviates | expectation (service mode, action, principle) | tolerance |
|---|---|---|---|
| A independent demand | rho 0 | target, either, pooling_has_value | 2% |
| B correlated demand | rho .9 | target, either, pooling_benefit_shrinks | 2% |
| C short lane | lead 1 | target, either, long_lead_positions_more_locally (with D) | 2% |
| D long lane | lead 3, branches open at 350 | target, either, long_lead_positions_more_locally | 2% |
| E high transfer cost | lane cost 2.0 (40% of price) | target, either, no_churn | 2% |
| F low transfer cost | lane cost .01, central 600, branches 120 | target, either, rebalance_before_purchase | 2% |
| G central supply shortage | supplier 120 / week (60% of demand), central 100, branches 60 | feasible, either, principled_allocation | 3% |
| H one-branch demand shock | declared event south x1.8 in periods 1-3, central 400 | incumbent, either, healthy_branch_not_starved | 3% |
| I shared supplier disruption | declared severe stress (fill .6, +14 days, 6 periods), central 250 | incumbent, either, network_protection | 5% |
| J asymmetric targets | north .99 priority 2, south .90, central 200 | target, either, priority_branch_protected | 2% |
| K unequal scale | north 300 / south 50, stock 400 / 60, central 500, supplier 380 | target, either, small_branch_not_starved | 2% |
| L already efficient | central 400, branches 250 | target, **no** (abstain on at least half the reviews), abstain | 2% |
| M unreachable stock | lead 4, branches 50, central 800 | feasible, either, remote_stock_not_credited | 2% |
| N pipeline covers | branches 40, central 400, 260 in flight to each branch (due next period) | incumbent, either, no_over_transfer | 2% |
| O two lane options | slow lane lead 2 at .10, express lead 1 at 1.00, branches 220 | target, either, cheap_lane_when_time_allows | 2% |
| P lane capacity | 70 / week (70% of branch demand), branches 120 | feasible, either, capacity_respected | 3% |
| Q packs and dispatch fee | packs of 24, 15 per dispatch, capacity 360, solver gap 1e-4 | target, either, legal_packs | 2% |
| R order / transfer interaction | supplier fixed order cost 250; local sources at both branches at +15% | target, either, total_economic_sourcing; **20 reviews** | 2% |
| S recovery after imbalance | north 400, south 0, central 400 | incumbent, either, recovery_then_steady | 3% |
| T single node, network off | one branch, no lane, `reorder_point` incumbent | target, either, frozen_identity | 2% |

Scenario count: `zaad.meio.topology.network_scenarios` (three worlds per two periods of the longest
lane window, minimum three, maximum eight): three for one-period lanes, six for D and O, eight for M.
Seeds 41001 and 41002 (truth seed + 10000). Eight rolling reviews (R: twenty), planning horizon
twelve, `max_solve_seconds` 15 with the frozen adaptive budget.

## 2. Comparators (`scripts/p2_benchmark.py`)

* `network_rop` — Baseline C, the INCUMBENT NETWORK POLICY: branch reorder points with local base
  stocks over lead + one review plus quantile protection, priority allocation (proportional among
  equals), central echelon reorder point with the frozen lot arithmetic, executed through the frozen
  common model.
* `central_pool` — Baseline B, the SIMPLE CENTRAL POOL: order-up-to at the branches every period,
  proportional allocation, central echelon replenishment.
* `independent` — Baseline A, INDEPENDENT BRANCH PLANNING: every branch as its own isolated chain
  (a private copy of the DC with its demand share of stock, supplier capacity and open orders, the
  same lane and order economics), planned by the frozen optimizer; no pooling.
* `echelon_base_stock` — the v6 MEIO comparator, unchanged.
* `gated` — ZAAD: the frozen joint decision on the network request (P1 purchasing owner on calm
  reviews, P0 protection / recovery otherwise), with correlated worlds, lane packs / dispatch fees
  and the incumbent network policy as declared.

None is weakened. A comparator that cannot complete a fixture (PHYSICAL_FAILURE, ERROR, an
unusable incumbent) is not a baseline for it.

## 3. Scoring

Continuation-valued cost over the window on the **P2 basis** (`p2_score`): the realised ledger plus
the value of residual stock and units in transit at the cost of the purchase one received unit
avoids (unit price over the cheapest source's fill plus the order-level premium the policy paid),
plus the lane cost a unit at a transfer-fed location avoids; origin residual reaches the branches
through the cheapest lane and pays it; no unit above the purchase it avoids, none below salvage.
This is the valuation the frozen P1 planner optimises on, applied to every policy alike. The
asset-basis `continuation` of the frozen `endpoint` is reported alongside and is not a gate
(Stage A showed it charges every policy that ends the window with stock the fill loss and the lane
cost of that stock, a window artefact of exactly the kind P1's continuation rule was built to remove).

## 4. Gates (all must hold for a VALID fixture to pass)

1. **zaad_not_worse**: ZAAD's P2-basis cost <= best qualifying baseline x (1 + tolerance).
2. **service**: mode `target` — every branch at or above its target less .01 under ZAAD; mode
   `incumbent` — every branch no worse than min(target, incumbent network policy) less .01; mode
   `feasible` — no severe starvation (below half the target) unless the incumbent starves the same
   branch and ZAAD is no worse, and ZAAD's worst branch no worse than the incumbent's less .01.
3. **action**: L abstains on at least half the reviews; every other fixture is `either`.
4. **no_reverse_movement**: zero units moved on a lane and its reverse inside the window.
5. **conservation**: settlement conservation residual <= 1e-4 on every review.
6. **no_starvation**: as in gate 2 (`feasible` clause), applied to every fixture.

Validity: a fixture is VALID when ZAAD completed every review and at least one comparator completed
every review and serves every branch no more than .05 below ZAAD (a comparator that is cheaper only
by starving a branch does not compare on cost). An INVALID fixture is reported, never counted.

**Network principles** (`network_principles`, read from the fixtures built for them): pooling_has_value
(A: ZAAD on the pooled network not worse than isolated chains by more than 2%), pooling_benefit_shrinks
(B's pooling benefit no larger than A's within 2%; the scenario-level fact is invariant 13/14),
correlated_demand_no_fabricated_diversification, long_lead_positions_more_locally (D's branch cover >=
C's), no_churn_at_high_transfer_cost, rebalance_before_purchase (F's first two reviews),
principled_allocation_under_shortage (G: no severe starvation), healthy_branch_not_starved (H: north no
worse than under the incumbent), priority_branch_protected (J: north >= .98), small_branch_not_starved
(K: south >= target - .01), already_efficient_abstains (L), remote_stock_not_credited (M: ZAAD no worse
than the incumbent; invariant 03 proves the plan credits nothing unreachable),
no_over_transfer_when_pipeline_covers (N: transfers <= 1.1 x demand), cheap_lane_when_time_allows (O
passes zaad_not_worse), capacity_respected (P completes), legal_packs (Q completes),
recovery_without_ping_pong (S), single_node_identity (T; proved by the canonical regression). Every
principle with a pass condition must pass.

**Runtime gate** (ZAAD, canonical topology, every authoritative cell): wall per review p50 <= 60 s,
p95 <= 120 s, max <= 180 s; no cell with a NO_FEASIBLE_SOLUTION on a required candidate; solve
statuses reported per fixture. Q carries a declared 1e-4 solver gap (general-integer packs).

**Invariants**: `scripts/p2_invariants.py` — 20 / 20 pass (18 reads fixture S from the authoritative
record). **Adversarial**: `scripts/p2_adversarial.py` — no findings (the free reverse pair is refused
by design). **Scalability**: reported, not gated (diagnostic).

**Frozen behaviour**: `scripts/zaad_canonical_regression.py` PASS (B, T, Q, A twelve-review identity;
P0 cell 15 identity) and, since frozen files were touched, the full P0 six-cell isolation arm
(`scripts/p1_p0_arms.py final` against the recorded arm) decision-identical.

**Engineering**: full Python suite, ruff, mypy, bandit on changed runtime code, `git diff --check`,
canonical workspace smoke, network workspace smoke, API tests; clean tree.

## 5. No-tuning statement

After this file is written no fixture argument, comparator rule, tolerance, service mode, scenario
rule or scoring basis changes. A coding defect found by the authoritative run is fixed, the affected
evidence invalidated and re-run, and the fix recorded in a dated section here and in `P2_CLOSEOUT.md`.

## 6. Untouched

Validation7, Validation8 (not present as directories), `docs/zaad_full/evidence/v4/holdout4`
(frozen, unrun), PR #39 / Network Twin, the dashboard and public website, sector physics
(fresh-produce shelf life, cold chain, manufacturing), `main`, the frozen tags.

## Correction 1 (dated 2026-09-10, after the authoritative run `p2_authoritative`)

The authoritative run passed every economic, service, action, conservation and principle gate (20 / 20
valid fixtures, 18 / 18 principles; `p2_authoritative.tables.md`). Two coding defects surfaced in the
runtime gate and are corrected here; the affected evidence is invalidated and re-run as
`p2_authoritative_c1` on the same seeds, reviews and rules:

1. **Solve budget did not follow the scenario rule.** `network_scenarios` raised the world count to
   six (D, O) and eight (M) but left the declared `max_solve_seconds` at 15, and the frozen adaptive
   budget scales with horizon and breadth only (it was fitted on three worlds). The stochastic
   candidate - a REQUIRED class on P1-owned reviews - then returned NO_FEASIBLE_SOLUTION inside the
   budget on 15 reviews of D, M and O (a required-candidate starvation the gate forbids). Fix:
   `zaad.meio.topology.network_solve_seconds` (the declared budget grows with S / 3, capped by the
   contract's 120 s), applied by the fixture builder and the workspace adapter. Invalidated: D, M, O.
2. **Transfer packs were enforced on guidance periods.** The model carried a general-integer pack
   variable on every lane-period while the settlement (and the frozen doctrine: only period-zero
   actions are executed, later actions are replanning guidance) judges packs on the executable period.
   The inconsistency made every candidate solve on Q general-integer over 24 lane-periods; under
   NETWORK_ALLOCATION (eight candidates at the adaptive budget) reviews took 217-282 s against the
   pre-registered 180 s maximum. Fix: the pack variable binds period zero only; the per-dispatch cost
   stays on every period. Invalidated: Q.

No fixture argument, comparator rule, tolerance, service mode, scenario rule or scoring basis changes.
The final table (`p2_final.tables.md`) is the authoritative record for the sixteen untouched fixtures
plus `p2_authoritative_c1` for D, M, O and Q; the runtime gate is read over the same set.
