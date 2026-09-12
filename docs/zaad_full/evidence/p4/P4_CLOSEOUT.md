# ZAAD P4 — Adaptive Recourse: local closeout

Branch `claude/zaad-adaptive-recourse-p4` (worktree `harvestmind-p4`) from `main` `ebcd1d0`; production
runtime `61a3e75` (`p3-performance-closure-runtime`) is an ancestor. Status: **local freeze candidate**.
Not released: no push, no merge, no deploy, no migration applied anywhere but local test vaults.

## Business question

P0-P3 choose the best commitment under uncertainty. P4 lets declared future decisions depend on
information that is genuinely observable by a declared review epoch, and therefore separates what
must be committed now from what may wait. Design: `docs/zaad_full/p4/ADAPTIVE_RECOURSE_DESIGN.md`;
design against implementation: `P4_DESIGN_REVIEW.md`.

## What was built

* `zaad/recourse/contracts.py` - `RecourseSpec` (enabled, review_periods <= 2 inside 1..H-1,
  observables `demand` / `receipts`, actions `purchase` / `transfer`, `demand_grid`, `fill_grid`,
  `confirmation_lag`, `continuations` <= 3, `perfect_information`, provenance), `InformationSet`,
  `resolve()` (None when absent or disabled), request-level validation, `INTERACTIVE_LIMITS`.
* `zaad/recourse/information.py` - canonical observable signatures, deterministic order-independent
  information sets, the `NodeMap` the builder indexes by (per column kind), signature lookup for worlds
  outside the solve.
* `zaad/recourse/worlds.py` - `draw_tree`: histories spliced with independent continuations that share
  the observable history exactly (worlds = scenarios x continuations ^ epochs, capped at 16).
* `zaad/full/model.py` - one hook: `solve(..., nodes=NodeMap)`. Purchase and transfer columns of periods
  at or after a review epoch exist once per information-set node; every world reads its node's column in
  arrivals, costs, payments and cash rows; MOQ / MOV / pack / capacity / resource rows per node; share,
  switching and smoothing rows per world path; here-and-now columns keep the frozen names, so a solve
  without a node map is bit-identical to the released builder. `Solution.recourse` carries the per-node
  policy; `Solution.binaries` the integer count.
* `zaad/recourse/policy.py` - `world_plan` (the plan a world receives), `compare` (static / adaptive /
  perfect-information on the same worlds, ordering check), `non_anticipativity` (structural check on
  solved values).
* `zaad/full/planner.py` - the `adaptive_network` candidate on the tree worlds, the static comparator
  and the perfect-information bound on the same tree, the materiality gate (request's own
  `materiality_cost_fraction` of the static cost), world-by-world settlement of an adaptive solution in
  `evaluate`, `report["recourse"]`.
* `zaad/recourse/explain.py` - the operator block: committed now, flexible window, per-branch observable
  condition in words, action, difference from the static plan, explanations; engineering block apart.
* API: `recourse` query parameter on the from-workspace endpoints, 413 above `INTERACTIVE_LIMITS`
  (tree worlds > 16, epochs / observables / actions over the caps), 422 code `recourse_invalid`.
* Migration `019_adaptive_recourse.sql` (`stg_recourse_spec`, additive, idempotent, declaration only);
  adapter `zaad/recourse/workspace.py`.
* Evidence scripts: `scripts/p4_benchmark.py`, `scripts/p4_invariants.py`, `scripts/p4_adversarial.py`,
  `scripts/p4_profile.py`; tests `tests/unit/test_zaad_recourse.py`, `tests/unit/test_zaad_recourse_workspace.py`.

## Mathematics (short)

min first-stage cost + Σ_w weight_w · world cost, the frozen objective, where world w reads
`x[line, t, node(w, e(t))]` for `t >= first epoch` and the shared `x[line, t]` before it; the same
rows as the frozen model, replicated per node or per path where they couple periods. Static = one
node. Perfect information = one node per world at every period (report-only). Feasible sets nest, so
`PI <= adaptive <= static` within the solver tolerance; the check is enforced and a failure rejects
the adaptive candidate. Value of adaptation = static - adaptive on the same tree; material only above
the request's materiality fraction of the static cost.

## Fixture matrix (`benchmarks/p4_authoritative`)

**28 / 28 PASS.** Gate per fixture: every solve usable, ordering wherever a static plan exists,
non-anticipativity on solved values, every represented world settles under its own policy plan with no
guidance truncation, and the pre-registered principle (`P4_FIXTURE_MATRIX.md`).

| fixture | family | worlds | sets | static | adaptive | PI | value | principle | result |
|---|---|---|---|---|---|---|---|---|---|
| N1_disabled_is_frozen | neutrality | 3 | - | - | - | - | 0.0 | frozen_identity | PASS |
| N2_no_epochs_is_static | neutrality | 3 | - | 12,529.7 | 12,529.7 | - | 0.0 | equals_static | PASS |
| N3_zero_information | neutrality | 4 | 1 | 15,059.2 | 15,059.2 | 14,550.5 | 0.0 | one_set_equals_static | PASS |
| A1_demand_visible_at_epoch | non_anticipativity | 4 | 2 | 15,869.1 | 15,206.0 | 15,186.5 | 663.2 | same_before_diverge_after | PASS |
| A2_delayed_information | non_anticipativity | 4 | 1,2 | 12,682.0 | 12,682.0 | 12,657.9 | 0.0 | no_branch_until_observed | PASS |
| D1_demand_recourse | demand | 4 | 2 | 16,683.7 | 15,858.0 | 15,835.0 | 825.7 | high_branch_buys_more | PASS |
| D2_two_epochs | demand | 4 | 2,4 | 15,869.1 | 15,195.3 | 15,186.5 | 673.8 | high_branch_buys_more | PASS |
| R1_supplier_short_fill | receipts | 4 | 2 | -20,768.6 | -20,888.4 | -20,980.1 | 119.8 | short_branch_replaces_supply | PASS |
| R2_shipment_delay | receipts | 4 | 2 | 12,649.5 | 12,649.5 | 12,638.8 | 0.0 | late_branch_covers_gap | PASS |
| V1_recovery | recovery | 4 | 2 | -20,485.4 | -20,709.5 | -20,795.0 | 224.1 | recovered_branch_buys_less | PASS |
| W1_waiting_has_value | waiting | 4 | 2 | 15,268.4 | 13,945.7 | 13,924.7 | 1,322.7 | waiting_value | PASS |
| W2_no_benefit | waiting | 4 | 1 | 12,646.6 | 12,646.6 | 12,637.3 | 0.0 | no_benefit | PASS |
| W3_flexibility_costs_mov | waiting | 4 | 2 | 16,201.3 | 15,537.1 | 15,484.2 | 664.2 | ordering_only | PASS |
| I1_p1_fixed_cost_lots | p1 | 4 | 2 | 16,171.3 | 15,492.1 | 15,454.2 | 679.2 | moq_in_every_branch | PASS |
| I2_p2_transfer_recourse | p2 | 4 | 2 | 14,978.9 | 14,916.9 | 14,466.6 | 62.0 | transfers_adapt_conserved | PASS |
| I3_p3_source_mix | p3 | 4 | 2 | -17,919.3 | -18,588.8 | -18,615.6 | 669.6 | capacity_in_every_branch | PASS |
| I4_p3_shares_hold | p3 | 4 | 2 | 15,257.6 | 14,732.1 | 14,715.0 | 525.4 | shares_in_every_branch | PASS |
| I5_p3_switching_cost | p3 | 4 | 2 | 14,507.9 | 14,507.9 | 14,499.2 | -0.0 | ordering_only | PASS |
| I6_multi_sku_shared_capacity | p3 | 4 | 2 | 47,777.1 | 46,166.9 | 46,113.0 | 1,610.1 | capacity_in_every_branch | PASS |
| I7_correlated_plant | correlated | 4 | 2 | 18,236.1 | 17,178.0 | 17,161.6 | 1,058.1 | plant_observed_once | PASS |
| S1_commercial_packs | sector | 4 | 2 | 15,870.8 | 15,210.7 | 15,193.8 | 660.1 | packs_in_every_branch | PASS |
| S2_produce_sell_through | sector | 4 | 2 | 14,927.5 | 13,177.1 | 13,165.2 | 1,750.4 | feasible_every_world | PASS |
| S3_meat_cold_chain | sector | 4 | 2 | 16,479.6 | 15,669.2 | 14,911.1 | 810.4 | feasible_every_world | PASS |
| S4_mixed_sectors_static_infeasible | sector | 4 | 2 | - | 23,758.2 | 23,476.0 | 0.0 | feasible_every_world | PASS |
| S5_mixed_sectors | sector | 4 | 2 | 22,790.4 | 21,952.8 | 21,932.1 | 837.7 | feasible_every_world | PASS |
| T1_tree_three_histories | tree | 6 | 3 | 12,805.9 | 12,767.5 | 12,644.9 | 38.4 | ordering_only | PASS |
| T2_tree_two_epochs | tree | 12 | 3,6 | 12,841.5 | 12,794.8 | 12,648.2 | 46.7 | ordering_only | PASS |
| T3_perfect_information_bound | tree | 12 | 3,6 | 12,895.4 | 12,841.9 | 12,669.2 | 53.6 | pi_ordering | PASS |

Observations: the commercial case-pack fixture S1 returns feasible time-limited adaptive and
perfect-information plans at the request's 42.9 s budget (the static solve already needs 4,385 nodes:
integer packs on four worlds), ordering and every check hold; S4 shows adaptation restoring feasibility
where no static plan meets the floors (ordering not applicable, recorded); I5 (switching cost) and R2
(a delay observed but not worth acting on) show value 0 without churn.

## Invariants, adversarial, performance, regression

* `P4_INVARIANTS.md`: **27 / 27** (no anticipation, same information -> same decision, probabilities,
  feasibility of every world plan, committed stays committed, conservation, no double allocation,
  capacity, shared capacity, MOQ, MOV, packs, shares, transfer lead, sector physics, FEFO, cold chain,
  approval, no executable PO, PI <= adaptive <= static, disabled = frozen, order independence, no future in
  a signature).
* `P4_ADVERSARIAL.md`: **25 / 25** fail safely (contract refusals, structural impossibilities, invariants).
* `P4_PERFORMANCE.md`: 24 matrix cells (single-SKU P1, P2 network, two-source P3, shared-order P3 x 3 / 4 / 8 histories x 1 / 2 epochs), every adaptive solve OPTIMAL. Interactive classes at 8 tree worlds: planner 0.6 - 2.6 s locally; the P3 shared-supplier-order class 33 - 192 s and therefore batch-only with recourse. Deterministic pre-solve rule enforced at the API: `/plan` accepts recourse only with `scenarios x continuations ^ epochs <= 8` and outside the shared-order class; `/jobs` accepts up to 16 tree worlds.
* `P4_FROZEN_REGRESSION.md`: P3 snapshot identical (12.0 s), canonical B / T / Q / A identity, P1
  invariants 60 / 0, P2 20 / 20 + 18 / 18 + 1,720 / 1,720, sector 26 / 26 + 19 / 19 + 416 / 416, P3 30 / 30
  + 34 / 34 + 23 / 23 + 2,304 / 2,304 (P4-disabled code against the CURRENT P3 baseline `p3_perf_closure` = runtime `61a3e75`; the historical P3
  performance-closure comparison stays 2,273 / 2,304 + 31 proven objective-flat C6 transfer ties and is not rewritten), P0 six-cell arm 119 / 120 under contention, cell 108 quiet rerun 30 / 30 -> 120 / 120 under the established protocol.
* Full suite: **1,930 passed, 2 skipped** locally on the final candidate (`gates/pytest_full.log`; the remote reference before P4 was 1,912 / 2), the two P4 test files and the P3 structural test re-run afterwards (25 passed); ruff (CI scope), mypy (CI scope), bandit clean locally; pip-audit and
  gitleaks run remotely at release.

## The commercial fixture (W1, `fixtures/W1_waiting_has_value_policy.json`)

Two demand branches (low 0.7x, high 1.5x) each with two futures, one review at period 2. Static
expected cost 15,268; adaptive 13,946; perfect information 13,925; value of adaptation 1,323 (8.7 %,
material). Policy: commit 320 units now and 302 in period 1 (the static plan's own commitments); at
period 2, if confirmed demand through period 1 is about 140 units per branch, buy 486 more over periods
2-11 (the static plan buys 2,450); if it is about 300 per branch, buy the 2,450. Reason: waiting keeps
the low branch from carrying 2,000 units it will not sell, while the high branch is served exactly as the
static plan would.

## Deferred

Cancellation with a declared penalty; external signals as observables; adaptive protection quantiles as
a distinct action; larger trees and the async path; persistence of policies beyond the declaration; an
operator-facing review trigger in the live system (the report states the policy; execution stays with
the operator, approval required).

## Untouched

Validation7, Validation8, holdout4 (unrun, unread); P5, P6; Network Twin #39; dashboard and website
uplift; global performance refactor; async architecture; Dependabot solver-stack bumps.

## Validation status

ENGINEERING VALIDATED. NOT REAL-DATA VALIDATED. The value of adaptation is a diagnostic on synthetic
fixtures, never a savings claim.

## Verdict

Every local freeze condition holds: core matrix 28 / 28, invariants 27 / 27, adversarial 25 / 25,
non-anticipativity proven structurally and on solved values, static neutrality proven (disabled and
absent blocks bit-identical, every frozen matrix identical), perfect-information ordering proven on
every fixture with a static plan, P1 / P2 / P3 / sector integrations proven, P0-P3 frozen regressions
green, performance inside the declared V1 bounds with the interactive rule enforced before any model,
full suite 1,930 passed / 2 skipped, ruff / mypy / bandit clean, no untouched validation data accessed.

**ZAAD P4 ADAPTIVE RECOURSE — PASS AND FROZEN LOCALLY.** Tags: `p4-frozen-product` on the product
commit, `p4-frozen` on this evidence commit; local only. P4 is not released; next required step: the
P4 release audit. P5 is not started.
