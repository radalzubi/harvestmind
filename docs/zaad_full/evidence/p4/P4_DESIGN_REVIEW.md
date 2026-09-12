# P4 design review: design against implementation

| design item | implementation | verified by |
|---|---|---|
| default off | `Request.recourse: RecourseSpec | None = None`; `resolve()` None when absent or `enabled` false; no hook reached (`zaad/recourse/contracts.py`) | N1, invariant 25, adversarial "disabled block reaches a hook", unit test |
| review epochs from the request | `RecourseSpec.review_periods` (1..H-1, strictly increasing, <= 2), validated at the contract | adversarial cases 1-3, 7 |
| observables | `demand` (realised demand per service per period, quantised to `demand_grid`) and `receipts` (arrival period and quantised fill of lines placed before the epoch and of pipeline orders, `pending` when not landed by `epoch-1-confirmation_lag`) | A1, A2, R1, R2, I7; invariant 27; adversarial "future-information leak", "supplier failure known too early" |
| information sets deterministic / order-independent / seed-reproducible | `information_sets`: grouped by signature, sorted by signature, ids `e<epoch>.<rank>`, members sorted, probability = sum of weights | invariants 3, 26; adversarial "scenario reorder", "duplicate scenario" |
| non-anticipativity by construction | one column per (line, period, node); worlds read their node's column in arrivals, costs, payments, cash rows; MOQ / MOV / packs / capacity / resource rows per node; share, switching and smoothing rows per world path | invariant 1, unit test, `policy.non_anticipativity` on every fixture |
| here-and-now irreversibility | columns before the first epoch are shared (frozen names); no cancellation action exists | invariant 7; adversarial "committed purchase cancelled by a branch" |
| allowed actions | `purchase`, `transfer`; gated per column kind by `NodeMap.adapts`; source decomposition and protection timing realised through them under P3 / P0 rows | I2 (transfer-only), I3-I6, V1 |
| same ledger | the frozen builder and settlement; no P4 cost term; the adaptive objective is the frozen objective on the tree worlds | invariants 23-24; adversarial "double counting" |
| static comparator | the same builder on the same tree worlds with `nodes=None` | every fixture |
| perfect-information comparator | one node per world at every period; report-only, flagged `never a recommendation`, never a candidate. **Release audit (blocker A):** a bound only when CERTIFIED (status OPTIMAL); a feasible time-limited incumbent is `perfect_information_feasible_cost` with status NON_CERTIFIED, excluded from the ordering check, never labelled a bound; the HiGHS dual bound is reported apart in solver-objective units (`policy.assess`) | T3, invariant 23 (certified solves only); adversarial "perfect-information plan surfaced" (no bound claim unless certified); release tests A1-A5 |
| value of adaptation and materiality | `static - adaptive` on the same worlds; material only above the request's `materiality_cost_fraction` x static cost; otherwise NO MATERIAL ADAPTIVE BENEFIT and the adaptive candidate is not selectable | W2, planner tests |
| sector physics | same eligibility, receipt life, cohorts and lane rules per node; settlement of every world plan | S1-S5; invariants 18-20 |
| P2 physics | transfer columns per node from the epoch on, arriving lead periods later; conservation per world | I2; invariants 9, 10, 17 |
| P3 economics | capacity / MOQ / MOV / packs per node; shares and switching per path; plant groups observed through receipts of both members | I3-I7; invariants 11-16 |
| operator reporting | `report["recourse"]`: committed now, flexible window, per-branch observable condition in words, action and difference from the static plan, explanations; engineering block separate | planner tests (no node ids in operator text) |
| approval | `approval_required` true, `executable_purchase_order` false on the report and inside the block | invariants 21-22 |
| bounds | contract: epochs <= 2, continuations <= 3; interactive `/plan` 413 when tree worlds > 8, observables / actions / epochs over `INTERACTIVE_LIMITS`, or the P3 shared-supplier-order class; asynchronous `/jobs` 413 when tree worlds > 16 (`BATCH_LIMITS`); all before any model is built | workspace / API tests |
| policy lookup for a world outside the solve | **Release audit (blocker B):** exact canonical-signature match only (`information.lookup`); no nearest-signature routing anywhere. A window whose observation matches no modelled branch receives the declared fallback (the static commitments attached by `policy.attach_fallback`) and is reported REPLAN_REQUIRED (`replan_required`, `unseen_observation_rule`); settlement evaluates exactly that policy | release tests B1-B7; adversarial "policy lookup leaking the future" (outside-support history selects no branch) |
| persistence | migration 019 `stg_recourse_spec` (declaration only; no solver node persisted); adapter attaches the block only with `recourse=true` and a row | workspace tests |

Deviations from the first design draft: the scenario tree (design section 4b) replaced grouping of the
raw selection draw; the seed term and cancellation were never built; `actions` gating was added after
the transfer-only fixture exposed that the first builder indexed every column by node. At the release audit
the nearest-signature lookup of the local freeze (`d8cdad5`) was withdrawn in favour of exact match with a
declared fallback, and the perfect-information diagnostic became a bound only when certified.
