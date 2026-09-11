# P3 development log

Every material experiment: hypothesis, implementation, fixture, result, decision. Failed experiments
stay.

## 1. Audit and baselines (2026-09-11)

* Branch `claude/zaad-sourcing-p3` from `main` `7bc4206` (docs-only over the released runtime `5ca3772`),
  worktree `harvestmind-p3`, clean.
* Audit (`P3_EXISTING_CAPABILITIES.md`): the frozen engine already carries a full source object and
  chooses among approved sources jointly (capacity, MOQ, packs, supplier orders across SKUs, payment
  terms, shared resources, per-source reliability, shared-domain supply shocks). P3 is therefore a
  declared sourcing contract (activation, risk groups with provenance, share constraints, switching
  cost, incumbent mix), three narrow default-off hooks (worlds, model, settlement), the incumbent mix in
  the rule projections, a sourcing report block, and the evidence machinery. No second optimizer.
* Baselines before any change: canonical regression PASS 48 s; sector tests pass 73 s; P2 / sector /
  P1 invariants: recorded below when complete.
* Fixture specification registered (`P3_FIXTURE_SPEC.md`, 30 fixtures) before any result.

## 2. Contract and hooks (2026-09-11)

* `zaad/sourcing/contracts.py`: `SourceRiskGroup`, `SourceShareConstraint`, `SourceSwitchingCost`,
  `IncumbentSourceShare`, `SourcingPortfolio`; `Request.sourcing` (None = frozen). Validation in
  `zaad/sourcing/validation.py` inside the frozen request validator.
* Hooks, every one behind `sourcing is not None`: model (zero-capability pruning of binaries, declared
  share rows, one first-stage switching binary per declared non-incumbent source), worlds (group factor
  blended into the frozen shock from a separate generator), settlement (switching ledger line, mapped to
  the ORDERING component), rule projections (declared incumbent mix splits the rule's quantity),
  planner (`report["sourcing"]`).
* Canonical regression after the hooks: PASS, identical (46 s).

## 3. Decisions taken while the fixtures ran (2026-09-11)

| experiment | result | decision |
|---|---|---|
| a share constraint with an incumbent that violates it: the retained incumbent then breaks the operator's own contract and the "honoured" sentence was false | seen on the first smoke | REJECTED as behaviour: a declared limit now requires declared incumbent shares that meet it (validation); dated incumbent orders are reported against the limit instead |
| P2 window score (`cost_p2`) as the P3 economic gate: it credits residual stock at the policy's own realised freight premium, so a dear-freight single source (E2 `single:supplier_b`) scored below ZAAD while spending more | E2 smoke: single B `cost_p2` 8,701 < ZAAD 8,798 with procurement + freight 7,758 > 7,316 | REJECTED for sourcing; `cost_p3` (`scripts.p3_benchmark.p3_score`): the same continuation rule with the cheapest approved source's landed cost per received unit and no policy premium; `cost_p2` still recorded |
| cloned fixture sources inherited `src_A`'s per-source capacity | R2 baselines starved with an "unlimited" B capped at 500 | fixed: a cloned source is unlimited unless the spec sets its capacity (`_add_source`) |
| the network rule split a mix after capping the total by the primary source's capacity | R2 incumbent mix at 500 total | fixed: the mix's combined capacity caps the total; each line by its own source |
| R2 with a declared 60 / 40 mix: ZAAD retained the incumbent mix on small reviews (the 0.3 per unit on a 40 % line is below materiality) | principle "A at capacity" failed on abstained reviews | fixture changed: incumbent 100 % A (capacity-starved); the principle is judged on reviews where ZAAD acts (an abstention keeps the operator's mix by design) |
| C5 / N3 at the P2 default demand never reached the shared capacity | S2 unused | fixture changed: demand 250 per branch |
| C5: the network rule projects SKU by SKU and never sees a resource shared across SKUs; its projection breached the shared capacity, the fixed incumbent solve was INFEASIBLE and ZAAD abstained with nothing ("no verified feasible projection") | frozen behaviour surfaced by a multi-SKU shared cap | P3 request only: the projected line is capped by the room left on every shared resource inside the rule (`fit_resources`, first line booked first); legacy projections untouched |
| A1 at demand 400 with A capacity 480: opening stock too small for the lead, joint targets infeasible at review 0 | not an abstention test | fixture changed: default demand with A capacity 120 (60 %) |
| S1 as specified (B below the receipt minimum) is refused by the frozen sector contract (no source may arrive below the receipt minimum) | ValidationError | fixture changed: B arrives with 3 of 8 periods against a receipt minimum of 2 and a sale minimum of 2 (one sellable period); the block explains the short sellable life |
| S3 with B into a chilled-only branch that also holds frozen opening stock and demand | refused by the sector contract | fixture changed: B delivers to a chilled-only cross-dock feeding central |
| C2 with horizon-scope shares: a rolling plan can defer the minority source to later periods on every review | spec ambiguity | fixture changed to period scope; the horizon scope is proven on the plan by invariant 17 |
| `cheapest_landed` comparator built by stripping the incumbent shares: the cheapest source then became the incumbent and paid no switching cost | E6 comparator unfair | replaced by a replay method that projects the rule without a mix but settles on the fixture's own request |
| a declared switching cost charged on every review of a rolling replay with a static declared mix (8 x 2,000 on E6's comparator) | absurd 24,605 | replay adopts an executed switch into the incumbent mix for the next review (`replay.py`, P3 requests only): the cost is paid once, when the switch is executed |
| P2 invariant 18 baseline on this machine: one cell's late-transfer units differ from the committed record (380.6 against 395.6, seed 41002) before any P3 change | scipy 1.18.1 / highspy 1.15.1 against the record's 1.17.1 / 1.14.0; the invariant passes | recorded as an environment tie, not a regression (canonical regression identical) |
| C5 / N3 at demand 250 with a shared 600: a starvation regime at review 0; the frozen P0 recovery gate ("recovery candidate lowers a service without raising a higher-priority one") rejected the joint recovery that fed SKU B from S2 at the cost of a few points of A's service, so ZAAD retained the starving rule on two reviews and lost to the all-S2 single source (+4.5 %) | frozen P0 semantics, not a sourcing defect | fixtures changed: demand 150 per branch, shared capacity 450 (no starvation regime; S1 covers 450 of 600, S2 the rest) |
| A3: `gated` and `gated_noprune` executed identical purchases on every review; executed transfer units differed on reviews 0-2 | the P2 transfer degeneracy (equal holding rates, per-unit lane cost) | the principle now requires identical purchases and proves a transfer difference is an objective tie on the first differing snapshot (`_transfer_tie`) |
| `cheapest_landed` projected an expired-quote source (the frozen rule filters approval and compliance, not the quote date) and `single:<supplier>` ran for suppliers with no usable source | A3 comparators INFEASIBLE / ABSTAIN | comparators only consider usable sources (approved, cleared, quote valid, capacity in the horizon) |
| the `single:<supplier>` variants stripped the switching costs and the declared mix, so a full switch to B paid nothing (E6 best baseline 8,605) | unfair comparator | variants keep the declared mix and switching costs (a full switch pays the declared cost once); only share limits are dropped for an unapproved source |

## 4. First authoritative run (2026-09-11, 22 / 30) and the corrections it forced

| finding | evidence | decision |
|---|---|---|
| `cost_p3` read the cheapest approved source from the policy variant's own request, so `single:<supplier>` variants that unapprove the cheap source credited residual stock at the dearer source's landed cost (A6: identical realised cost, single B "cheaper" by 9 %) | A6, S2 | basis = the fixture's original request for every policy |
| E3 (demand 400) and R2 (demand 400) ran in a starvation regime (service .84 / .55) where the frozen P0 recovery rules own the reviews | ledgers dominated by lost sales | E3: demand 150, tiers 5.0 up to 200 / 4.4 from 250; R2: demand 150, A capacity 200 |
| E5: ZAAD abstained on 5.5 of 8 reviews keeping the declared 50 / 50 mix and bought A only when it acted; the whole-window A share (.65) failed a principle written for acted reviews | principle | `a_dominant_share` judged on acted reviews (whole-window share recorded) |
| S1: the rolling replay materialised every received PO with the SKU's full shelf life, ignoring the declared age at receipt, so the rule buying the "old" source got fresh goods and beat ZAAD by 8 %; the same replay served the sector phase's age-at-receipt fixture | end-stock cohorts with 8 periods of life from a source declared at 3 | `replay.py`: a materialised receipt carries `physics.receipt_life(sku, source)` on a physics request (legacy requests unchanged: full shelf life). Sector fixture P3 (age at receipt) is expected to differ from its release record for this reason; reported in the sector regression |
| S3: an empty chilled cross-dock feeding central by a lane put every review into NETWORK_ALLOCATION and ZAAD served less than the rule (frozen P2 topology behaviour on a dead upstream node) | -3.6 % / south .924 | the cross-dock stays (B's ineligible destination) without the lane |
| A2: the weak-evidence sentence was gated on a source being used | principle | a declared weak-provenance group is always stated |
| `single:<supplier>` variants ran for suppliers whose pairs have no other usable supplier (identical to ZAAD) | S3 | skipped |
| `cost_p3` chose the cheapest source by price and divided by that source's fill (the P2 rule), so a cheap low-yield source set the residual basis at its dearer received-unit cost | S2 | basis = the cheapest usable source per RECEIVED unit (landed / expected fill), the P1 steady-state convention |
| S2 (B at 4.5 with yield .80 sd .15 against A at 5.0 / .98): the two pre-registered truth draws gave B an 8-period mean yield of .88 and .91 (the sampler is unbiased: .808 over 20 seeds; these are the top decile), which makes B cheaper per received unit on those truths (4.95 against 5.10); the single-B policy then beat ZAAD by 3.09 % against a 3 % tolerance while ZAAD's ex-ante choice of A was right | truth draws inspected | fixture changed: B yield .70 (expected 6.43 per received unit; B still loses at a +2 sigma truth mean of .81: 5.56 > 5.10), so the window's yield luck cannot decide the gate; seeds and tolerance unchanged |
| the API mapped every vault ValueError containing "sourcing" to `sourcing_invalid`, including sector errors whose pydantic dump shows the `sourcing: None` field | sector workspace test | the code is chosen on the `sourcing:` message prefix |
