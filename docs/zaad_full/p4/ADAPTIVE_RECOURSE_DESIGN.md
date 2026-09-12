# ZAAD P4 — Adaptive Recourse: design

Branch `claude/zaad-adaptive-recourse-p4` from `main` `ebcd1d0` (production runtime `61a3e75`).
Status: engineering design for the local freeze; not a release document.

## 1. Business question

P0-P3 answer "what is the best commitment now, under uncertainty". P4 answers "what should ZAAD do
later if the world develops differently from what we know today" - and, because of that, "what must
be committed now and what can wait". Principles: commit only what must be committed now and keep
flexibility where waiting has value; adapt to information, never to scenario labels; a recourse
decision is valid only when the operator would genuinely know its trigger before making it.

## 2. Ownership

| layer | owns | P4 relationship |
|---|---|---|
| P0 | protection / recovery economics, abstention, incumbent comparison | unchanged; adaptive purchases and transfers run under P0's service floors, so protection is re-sized after evidence without a new heuristic |
| P1 | purchase commitment economics (cadence, MOQ, MOV, packs, payment, carrying, continuation) | unchanged primitives; P4 indexes the uncommitted purchase columns by information set |
| P2 | network positioning, transfer physics, conservation | unchanged primitives; P4 indexes the uncommitted transfer columns by information set |
| P3 | source portfolio economics | unchanged; source decomposition of uncommitted quantities adapts because the per-source purchase columns adapt, under P3's share, switching, capacity and MOV rows |
| sector physics | physical feasibility | unchanged; every node's columns carry the same eligibility, receipt life and cohort rules |
| **P4** | **conditionality**: which decisions may depend on which observations, when | new layer `zaad/recourse`; one hook in the frozen model builder; one candidate and one report block in the planner |

## 3. What adapts, what does not

Adaptive (only when declared in `recourse.actions`, enforced per column kind by the node map):
`purchase` - every purchase line (all sources) in periods at or after a review epoch; `transfer` - every
lane / cohort transfer in those periods (a `transfer`-only declaration keeps purchases static). Source
decomposition and protection level are realised through those two under P3 and P0 rules; no new action
types. Irreversible: everything at periods before the first review epoch, pipeline PO options, opening
stock, every physical state. No cancellation in V1 (committed = committed); no retroactive switch,
transfer reversal or age reset. Recourse acts through the same lanes with the same lead times.

## 4. Review epochs and observables

`recourse.review_periods` are declared by the request (strictly increasing, inside `1 .. horizon-1`,
at most `MAX_REVIEW_EPOCHS`); zero epochs is the neutral case. At epoch `e` the observable history is
what has happened in periods `0 .. e-1`:

| observable | signature content | canonicalisation |
|---|---|---|
| `demand` | realised demand per service per period `< e` | quantised to `demand_grid` units (absolute grid, default 1.0): `round(d / grid)` as an integer |
| `receipts` | for every purchase line placed at `p < e` (and every pipeline PO): arrival period if it arrived by `e-1-confirmation_lag`, else `pending`; fill fraction when arrived, quantised to `fill_grid` (default 0.05) | integers / the literal `pending` |

Nothing else: no future demand, fills, lead times, failures, labels, seeds or world order. External
signals stay outside V1. Supplier confirmation is treated as exogenously observable for every line
placed before the epoch (the supplier's fill status for that period is confirmed whether or not ZAAD
drew the line) and this is declared, not hidden; `confirmation_lag` models late confirmation.

## 4b. Scenario tree (why shared histories are mandatory)

A first build grouped the planner's own selection worlds by signature. With continuous demand every
world is its own information set, so the branch decision is optimised against that world's own future
draw: the "adaptive" cost then sits next to the perfect-information cost (12,433 against 12,419 on
the P2 fixture, static 12,471) and the value of adaptation is an artefact of one-world sets. The
correct construction is a small scenario tree: `draw_tree` takes the selection draw as histories and,
at every review epoch, splices each branch with `continuations` independent futures that share the
branch's observable history exactly (demand from the epoch on, fills and arrivals of lines placed
from the epoch on). Worlds = scenarios x continuations ^ epochs (capped at 16); each information set
then holds a genuine conditional sample of the future. All three comparators (static, adaptive,
perfect information) are solved on the same tree.

## 5. Information sets

`information_sets(req, spec, worlds)` groups the worlds of a solve by identical signature at each
epoch, deterministic, order-independent and seed-reproducible: sets are sorted by signature, ids are
`e<epoch>.<rank>`, members are sorted world indices, probability is the sum of member weights.
Signatures at a later epoch extend the earlier one, so sets refine (a tree without a tree database).
A world outside the solve (a confirmation world, or a live observation) is mapped by exact
signature only. **Release rule (P4 release audit, blocker B):** there is no nearest-signature
routing. An observation that matches none of the modelled branches selects no branch action: for
that review window the world receives the declared fallback, the static commitments attached to the
adaptive solution (`policy.attach_fallback`), and the lookup is reported as `REPLAN_REQUIRED`
(`policy.lookup_exactness`, report field `replan_required`, rule text `unseen_observation_rule`).
Settlement therefore evaluates exactly the policy the operator may execute; nothing is credited to
adaptation on a world whose information is outside the modelled support. (The local engineering
freeze `d8cdad5` routed such worlds to the nearest signature; withdrawn at the release audit.)

## 6. Non-anticipativity

Represented structurally: one column per information-set node, never one per world with equality
rows. `purchase[s, t]` for `t >= first epoch` becomes `purchase[s, t, node]` with `node =
set(e(t))` where `e(t)` is the latest epoch `<= t`; world `w` reads `purchase[s, t, node(w, e(t))]`
in its arrivals, costs, payments and cash rows. Same for transfers. Worlds sharing a node share the
column: leakage is impossible by construction, and the invariant re-checks it on the solved values.

## 7. Formulation

Minimise first-stage cost + Σ_w weight_w · (world cost with world `w` reading its nodes' columns)
subject to the frozen rows (conservation per world, MOQ / MOV / packs per node, share rows and
switching per world path, capacity per node, network rows per world, sector physics, service floors,
cash) - the same builder, the same ledger, the same tie-break. Static comparator: the same builder
with a single node (the frozen `stochastic_network` solve). Perfect-information comparator: one node
per world at every period (report-only; never executable). Ordering `adaptive <= static` must hold
within the solver tolerance because the feasible sets nest; `PI <= adaptive` is asserted only when
the perfect-information solve is **certified** (status OPTIMAL). **Release rule (P4 release audit,
blocker A):** a feasible time-limited perfect-information incumbent is the cost of a feasible policy,
not a lower bound of the minimisation: it is reported as `perfect_information_feasible_cost` with
`perfect_information_status = NON_CERTIFIED`, excluded from the ordering check, and never labelled a
bound, an optimum or a value of perfect information. HiGHS's dual bound, when returned, is reported
apart (`engineering.perfect_solve.solver_objective_bound`) in solver-objective units (the ledger cost
plus objective-only terms), never as a policy cost and never compared with the projected costs. A
certified ordering violation still rejects the adaptive candidate (`policy.assess`).

## 8. Value of adaptation, materiality, abstention

`value_of_adaptation = static_expected_cost - adaptive_expected_cost` on the same worlds, weights,
physics and ledger (solver objective, projected cost). Material only when it exceeds the request's
own `materiality_cost_fraction` of the static cost (the existing materiality standard; no P4
threshold). When not material the adaptive candidate is reported as NO MATERIAL ADAPTIVE BENEFIT and
does not enter selection; the static plan stands. Never called savings, never annualised.

## 9. Planner integration

`plan()`: when `resolve(req)` is not None, build the information sets on the selection worlds, solve
`adaptive_network` (the stochastic candidate's kwargs plus the node map) and, when declared, the
perfect-information diagnostic; `evaluate()` settles an adaptive solution world by world with that
world's own plan (its node columns; exact policy lookup for fresh worlds, the static commitments for
a window whose observation matches no branch); the report gains `recourse`
(comparators, value, sets per epoch in operator language, the policy per set, explanations). The
selected plan's period-0 actions are here-and-now by construction (epochs start at 1).

## 10. Reporting

Operator language only: what is committed now, what remains flexible, at which review period, under
which observable condition (quantised demand band, confirmed receipt status), what ZAAD would do and
why. No world names, node ids or column names in the operator block (they stay in the engineering
block).

## 11. Performance strategy and bounds

Few epochs, few worlds, node columns instead of equality rows, the frozen builder reused. V1 caps
(`INTERACTIVE_LIMITS`): review epochs <= 2, observables <= 2, actions <= 2, worlds as today (4
interactive), information sets <= worlds by construction; a request over the caps fails at
validation, before any model. Instrumented per solve: worlds, epochs, sets, columns, binaries, rows,
build time, HiGHS time, nodes, status; recorded in `evidence/p4/P4_PERFORMANCE.md`.

## 11b. Measured V1 bounds (after the performance matrix)

Interactive (`/plan`): tree worlds `scenarios x continuations ^ epochs <= 8`, epochs <= 2,
observables <= 2, actions <= 2, and never the P3 shared-supplier-order class (`shared_supplier_orders`),
which measured 33 - 192 s locally with recourse and is batch-only in V1. Batch (`/jobs`): tree worlds
<= 16, epochs <= 2. Both rules are evaluated on the request before any model is built.

## 12. Failure modes guarded

Leakage (structural + invariant), anticipatory branching under identical histories (zero-information
neutrality), free cancellation (no cancellation), teleportation (same lanes and leads), age reset
(same cohorts), capacity / MOV / share breaches after adaptation (same rows per node and path),
double counting (same ledger; PI <= adaptive <= static), perfect information surfaced as a policy
(report-only, flagged), default-on (absent or disabled = frozen), unbounded growth (caps).

## 13. Test matrix

`evidence/p4/P4_FIXTURE_MATRIX.md`: neutrality, non-anticipativity, demand / receipt / delay
observation, recovery, waiting value, no-benefit, P1 / P2 / P3 interactions, three sectors, mixed,
correlated risk, multi-SKU, two epochs, perfect-information ordering; invariants and adversarial
cases as separate scripts.

## 14. Deferred

Cancellation with declared penalty; external signals as observables; adaptive protection quantiles
as a distinct action; larger world counts and epoch counts (async path); persistence of solver nodes.
