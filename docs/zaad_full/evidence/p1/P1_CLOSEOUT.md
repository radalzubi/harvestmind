# P1 CYCLE-STOCK ECONOMICS — CLOSE-OUT

**Verdict: P1 CYCLE-STOCK ECONOMICS — FAIL ON FIXTURE PARITY (C, O, P); MECHANISMS COMPLETE AND RECONCILED; NOT FROZEN.**

The mechanisms the brief asked for are implemented, tested, reconciled and explained, and ZAAD P1
beats or ties the best competent baseline on 17 of 20 development fixtures. It does not on three
(MOQ four weeks, low opening stock, high opening stock), by 2.1% to 3.7% against a pre-registered
tolerance of 2%, and two pre-registered attribution expectations were wrongly written and fail.
The tolerance was not widened and the expectations were not edited, so the exact verdict "PASS AND
FROZEN" cannot be given. What is and is not established is set out below.

Branch `claude/zaad-cycle-stock-p1`, worktree `harvestmind-p1`, parent (frozen P0) `2e30721`.
Evidence in `docs/zaad_full/evidence/p1/`. Development fixtures only: every economic figure is a
CONFIGURED_ASSUMPTION; nothing here is customer validation, industry proof or a savings claim.

## 1. Result table (primary arm: nil declared stress, target-basis gate, order smoothing off)

Means over three seeds, eleven rolling reviews of a twelve-period weekly plan. The full table with
every required column (service, P10, breaches, unmet, worst shortfall, inventory units and value,
order count and size, purchase / freight / ordering / receiving / carrying / financing / shortage /
inventory value change / total, working capital, deltas, action recommended, why) is
`P1_RESULT_TABLE_none.md`; the per-cell records are `fixtures_none.jsonl`.

| fixture | incumbent | best baseline | ZAAD P1 | ZAAD vs incumbent | ZAAD vs best baseline | pre-registered checks |
|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 | 5,824 (incumbent) | 5,887 | +1.1% | +1.1% | PASS |
| B_fixed_order_cost_replace_sold | 8,528 | 6,995 (economic_lot) | 6,223 | -27.0% | -11.0% | PASS |
| C_moq_four_weeks | 9,595 | 5,898 (reorder_point) | 6,115 | -36.3% | +3.7% | FAIL: zaad_not_worse |
| D_case_multiple | 5,807 | 5,807 (incumbent) | 5,775 | -0.5% | -0.5% | PASS |
| E_pallet_multiple | 6,239 | 6,239 (incumbent) | 6,239 | +0.0% | +0.0% | PASS |
| F_mov_two_skus | 14,040 | 11,766 (periodic:2) | 11,669 | -16.9% | -0.8% | PASS |
| G_freight_tiers | 21,400 | 16,720 (economic_lot) | 14,970 | -30.0% | -10.5% | PASS |
| H_per_pallet_freight | 6,884 | 6,826 (periodic:2) | 6,671 | -3.1% | -2.3% | PASS |
| I_max_pallets_ftl_cap | 16,274 | 9,814 (economic_lot) | 9,967 | -38.8% | +1.6% | PASS |
| J_net60_cost_of_capital | 7,478 | 6,850 (periodic:2) | 6,079 | -18.7% | -11.3% | PASS |
| K_deposit_early_cash | 7,490 | 6,862 (periodic:2) | 6,079 | -18.8% | -11.4% | PASS |
| L_high_holding_rate | 7,434 | 6,856 (periodic:2) | 6,134 | -17.5% | -10.5% | PASS |
| M_order_calendar_wednesday | 6,256 | 6,256 (incumbent) | 6,272 | +0.3% | +0.3% | PASS |
| N_long_lead_21_days | 5,937 | 5,937 (incumbent) | 6,025 | +1.5% | +1.5% | FAIL: categories |
| O_low_opening_stock | 6,521 | 6,399 (reorder_point) | 6,576 | +0.8% | +2.8% | FAIL: zaad_not_worse |
| P_high_opening_stock | 6,282 | 5,786 (reorder_point) | 5,906 | -6.0% | +2.1% | FAIL: zaad_not_worse |
| Q_volatile_demand_high_target | 5,971 | 5,971 (incumbent) | 6,043 | +1.2% | +1.2% | PASS |
| R_asymmetric_prices_mov | 63,448 | 63,448 (incumbent) | 63,255 | -0.3% | -0.3% | FAIL: categories |
| S_cash_constrained | 6,924 | 6,234 (economic_lot) | 6,147 | -11.2% | -1.4% | PASS |
| T_combined_realistic | 24,255 | 17,593 (economic_lot) | 15,256 | -37.1% | -13.3% | PASS |

Policies: INCUMBENT is the operator's declared rule projected from each review's snapshot
(`replace_sold`, `reorder_point` or `periodic:2` per fixture); REORDER_POINT+PROTECTION,
PERIODIC_REVIEW(2) and EOQ_LIKE are lot-, MOV-, load- and cash-aware projections
(`zaad/full/policies.py`); ZAAD P1 is the gated planner. All 300 cells of every arm completed;
no policy failed settlement.

Sensitivity and ablation arms (same fixtures, same seeds):

| arm | what changes | fixtures passing | where ZAAD moved |
|---|---|---|---|
| `none` (primary) | - | 15 / 20 | - |
| `late` | declared stress: one week late, full fill | 15 / 20 | protection is bought where the stress bites (I +2%, O +2%); P passes on cost and fails only the "mostly abstain" expectation |
| `gate` | `service_gate_basis="incumbent"` (V7 rule) | 15 / 20 | I: 9,967 -> 10,813 (+8.5%); the lean full-load plan is refused against the replace-sold incumbent's 100% service |
| `smooth` | `order_smoothing=.02` (P0 default) back on | 15 / 20 | C: 6,115 -> 6,201; F: 11,669 -> 12,114 (+3.8%): the smoothing proxy fights consolidation |

## 1a. Runtime

Per-review wall time of the gated planner, primary arm (660 reviews): p50 0.10 s, p90 0.65 s,
p95 1.00 s, max 19.8 s (one cadence-candidate MILP hitting the 15 s budget plus confirmation);
whole arm 90 s on three workers. No benchmark approached the eight-hour stop.

## 1b. Reconciliation and invariants

- Every cell of every arm: ledger components sum to the settlement's economic cost to 1e-9
  (`|ledger sum - total| = 0.0` across 1,200 cells).
- `scripts/p1_invariants.py`: 60 / 60 (20 fixtures x 3 seeds, first review): components
  reconcile; attribution partitions every order exactly; no negative category; every supplier
  order clears MOV and the maximum load; operating components non-negative; provenance labels from
  the closed set and no CUSTOMER_PROVIDED label on a fixture; no unmapped ledger key; materiality
  verdict from the closed set; recommendation matches status; abstention reason stated; timing
  audit and waterfall agree on arrival periods.
- Unit tests: 23 P1 tests in `tests/unit/test_zaad_p1_economics.py`; full suite green at the
  final SHA: 1431 passed, 2 skipped.

## 2. What P1 built (phases 1-8)

| phase | delivered | where |
|---|---|---|
| 1 audit + data model + cost accounting | gap analysis; `SupplierTerms` (MOV, fixed order cost, receiving per receipt / per pallet, units per pallet, stepped freight tiers, per-pallet freight, max load), `Liquidity.cost_of_capital_per_period`, materiality thresholds, provenance labels, `cadence_candidates`; model rows and settlement mirror for every term; `working_capital` ledger component | `contracts.py`, `model.py`, `settlement.py`, `P1_GAP_ANALYSIS.md` |
| 2 order timing + calendars | `next_replenishment` (arrival and next realistic replenishment under order / production / shipping / receiving calendars); `SUPPLIER_CALENDAR` attribution; timing audit reused from `procurement_timing` | `economics.py` |
| 3 MOQ + case + pallet | integer lot rules already in the model (P0); attributed as `MOQ`, `CASE_ROUNDING`, `PALLET_ROUNDING` in the order a buyer applies them | `economics.py` |
| 4 MOV + multi-SKU coordination | supplier-order binary per period, `sum(q * price) >= MOV * order`; settlement raises on a below-MOV order; `MOV` attribution shares the top-up across lines | `model.py`, `settlement.py`, `economics.py` |
| 5 freight LTL / FTL / container | integer pallets per supplier order, tier binaries, per-pallet freight, maximum load; settlement prices the same tariff; `FREIGHT_ECONOMICS` attribution (pallet completion, tier landing) | same |
| 6 payment terms + financing + carrying | deposit / trigger / net days (P0); cost of capital on own cash deployed, charged after borrowing so debt interest and capital charge never overlap; carrying on asset value only | `settlement.py`, `model.py` |
| 7 joint economic optimisation | the one MILP prices all of the above jointly; `cadence_2_network` / `cadence_4_network` optional candidates when a supplier carries order-level economics; `timing_tiebreak` for indifferent timings | `planner.py`, `model.py` |
| 8 attribution + explanations + abstention | `cost_breakdown` (PURCHASE / FREIGHT / ORDERING / RECEIVING / CARRYING / FINANCING / SHORTAGE / OTHER / INVENTORY_VALUE_CHANGE, reconciling to the settlement's economic cost), `order_waterfall`, `explain_order`, `materiality` with NO MATERIAL IMPROVEMENT AVAILABLE, `provenance`, `missing_data_fallbacks`; `report["economics"]` block | `economics.py`, `planner.py` |

Every order in a report is explained as: demand until the next realistic replenishment + justified protection + lot requirements - usable on hand - usable inbound = economic need, then MOQ, case, pallet, MOV, freight tier and order-cost steps, then calendars. The attribution categories partition the ordered quantity exactly (invariant 2), and anything the arithmetic cannot explain is labelled OTHER_EXPLAINED and said so in the sentence.

## 3. Changes to selector behaviour, each with its reason and its ablation

| change | default | reason | evidence |
|---|---|---|---|
| `service_gate_basis="target"` | new field, default `target` | the V7 rule counted any fall against the incumbent's service as a worsening. Against an over-buying incumbent (replace-sold under a 400-unit MOQ runs at 100% service) every lean candidate failed `_priority_consistent` and the alternatives loop admitted a bloated service-first plan instead (fixture C review 2: 676 units bought with 357 on hand). Under the target basis a service that stays at or above its target has not worsened; below target, and in recovery mode, the strict rule stands unchanged. | arm `gate` (basis `incumbent`) in `P1_RESULT_TABLE_none_gate_incumbent.md` |
| materiality gate: NO MATERIAL IMPROVEMENT AVAILABLE | new fields `materiality_cost_fraction=.01`, `materiality_inventory_fraction=.05`, `materiality_service=.005` | a candidate that passes every gate but moves cost, carried inventory and worst service by less than the declared materiality is not worth an intervention; service counts only up to the target | fixture A (near-optimal incumbent): abstention share in the table |
| `timing_tiebreak=1e-4` | new field, objective only | with no cost of capital and a small holding rate the model was indifferent between committing cash now or later; HiGHS returned whichever it found first. The tie-break is not a cost and never enters the ledger. | `test_timing_tiebreak_prefers_later_commitment_when_the_economics_are_indifferent` |
| settlement financial tail counts dated known receivables | settlement | the model's liquidity rows already used them; the settlement's tail rule did not, so a plan the model financed on declared receivables was `OPTIMAL_PHYSICALLY_INVALID` (fixture S, every policy) | `test_terminal_financing_tail_counts_declared_receivables_like_the_model_does` |
| cost of capital charged after borrowing, own cash only | settlement (P1 code) | first draft charged it before borrowing, so credit-financed dollars carried both interest and the capital charge | `test_phase6_carrying_financing_and_capital_are_separate_and_not_double_counted` |

Untouched: P0 solve states, residual gate, settlement gate on `usable_plan`, comparable-gap ranking, REQUIRED / OPTIONAL / NOT_APPLICABLE accounting, the deficit rule (.20), the adaptive solve budget, the warm-start cascade, and every recovery-mode rule. `order_smoothing` default (.02) is untouched (see section 5).

## 4. Deviations from the pre-registration, recorded rather than hidden

1. **Review window 8 -> 11.** With an eight-review window on a twelve-period plan, a policy that defers its purchases past review 8 is never charged for the stock periods 8-11 need, while the optimizer, which plans to the end of its horizon, is charged for that stock at terminal value inside the window. Measured before the change on fixtures C / I / F / T at 8 versus 11 reviews the ranking flipped on I and T (ZAAD from 16% / 13% worse than EOQ to 6% / 7% better). The window now equals the replay's own horizon - 1 convention for every policy alike.
2. **Fixture S revised.** The first draft (opening cash 1,500, credit 1,500, no dated receivables) left every policy, the incumbent included, unable to finance week 6, because the model counts only dated known receivables as cash in. Dated receivables of 450 per week make financing binding rather than impossible.
3. **Declared stress.** A declared stress is mandatory on every request. The first draft declared the P0-style envelope (10% short fill, one week late, +5% demand). Under it the P0 stress gate, correctly, refused lean plans that stock out under the disruption, and the fixtures measured protection economics rather than cycle-stock economics. The primary arm declares a nil stress (the fitted world itself) so the gate runs but cannot dominate; the `late` arm (one week late, full fill) is kept as the sensitivity result.
4. **`order_smoothing=0` on the fixtures.** See section 5. The product default is untouched.
5. **Fixture N's `LEAD_TIME_EXPOSURE` expectation** was written on the gross requirement; with 350 units on hand the three weeks of lead-time demand are covered by on-hand and the netted attribution is correctly zero. The expectation is left failing and is explained here rather than edited.

## 5. Discontinuities and hidden terms found

| item | what it does | status |
|---|---|---|
| `order_smoothing` (.02, reliability profile) | 2% of landed unit cost per unit of period-to-period change in each source's order quantity, in the model objective only, never settled | material: about $200 of phantom cost on a 1,000-unit consolidated $5 order, the size of an undeclared fixed order cost; it spreads purchases evenly and buys early. Off on the P1 fixtures; ablation arm `smooth` shows the effect; default left for the owner to decide |
| freight tiers | one unit over a tier boundary costs the next tier (settlement test: 400 units = $800, 401 units = $1,100) | modelled exactly by tier binaries; attributed as FREIGHT_ECONOMICS when an order lands on a boundary |
| MOQ / MOV | a need of 65 units becomes an order of 400 (MOQ) or is lifted by another SKU (MOV) | modelled; attributed; the baselines are lot- and MOV-aware so no policy fails settlement on a lot rule |
| maximum load | a 9-pallet cap splits or defers demand | modelled; the EOQ baseline caps its lot at a full load |
| terminal value (.8 of price on the fixtures) | stock left at the end of a window is credited at 80% | applied identically to every policy; it is the reason the window had to equal the plan horizon |
| the confirmation draw | a candidate optimised to exactly the service floor meets it on the selection worlds and fails it on an independent draw about half the time | P0 behaviour, unchanged; it is why `base_stock` (which over-serves) is sometimes the accepted candidate at review 0 on lean fixtures |

## 6. Provenance and missing-data fallbacks

Every economic input in a report carries one of CUSTOMER_PROVIDED / INFERRED_FROM_HISTORY / CONFIGURED_ASSUMPTION / NOT_AVAILABLE (`economics.provenance`). An undeclared non-zero figure is CONFIGURED_ASSUMPTION; an undeclared zero is NOT_AVAILABLE. On the fixtures every figure is CONFIGURED_ASSUMPTION or NOT_AVAILABLE (invariant 6: no CUSTOMER_PROVIDED label appears). Fallbacks are stated in the report (`missing_data_fallbacks`):

- cost of capital NOT_AVAILABLE: payment timing is valued only through interest on drawn credit, and the timing tie-break prefers later commitment;
- holding rate NOT_AVAILABLE: carrying is zero and inventory is compared on value only;
- a freight tariff without pallet sizes, or with a pallet size missing for one SKU: pallet economics disabled for that supplier, said so;
- no supplier terms: MOV, fixed order cost, receiving and tariffs NOT_AVAILABLE, per-unit source costs only.

No generic industry rate is hard-coded anywhere; the holding, capital and interest rates on the fixtures are declared per fixture and converted from annual to per-period by `annual_to_period`.

## 8. Commercial sanity questions

| | question | answer from the evidence |
|---|---|---|
| A | Can ZAAD tell a buyer to order nothing? | Yes. Fixture P (six weeks on hand) - ZAAD buys nothing for the first reviews while the replace-sold incumbent keeps buying; cost and inventory in the table. |
| B | Does it ever recommend less than the incumbent? | Yes - every fixture with a replace-sold incumbent under a lot rule (B, C, F, G, L, T). |
| C | Does it ever recommend more / earlier? | Yes - consolidation into a full load (I: 450 units at once; G / T: the whole horizon's demand in one tiered load) and the low-stock fixture O. |
| D | Can it say "no material improvement"? | Yes - the NO MATERIAL IMPROVEMENT AVAILABLE verdict on fixture A and on individual reviews elsewhere (review outcomes in the jsonl). |
| E | Does every order come with a reason a buyer would accept? | Each period-0 order carries a one-sentence explanation built from the waterfall (examples in section 9); the unexplained remainder is named as such. |
| F | Are MOQ, case, pallet, MOV and freight shown as costs, not hidden in "safety stock"? | Yes - they are separate attribution categories and, for freight, ordering and receiving, separate cost components that reconcile to the settlement. |
| G | Is cash timing valued? | Only when a cost of capital is declared (J vs K: net-60 versus 30% deposit at order differ in FINANCING alone, PURCHASE identical). Without it the report says NOT_AVAILABLE. |
| H | Does a cheaper plan that stocks out get through? | No - the service floor, the independent confirmation and the stress gate are unchanged from P0; the target-basis change only stops an above-target fall from counting as a worsening. |
| I | Is the comparison fair to the incumbent? | The incumbent is the operator's declared rule projected from the same snapshot every review, and the baselines are lot-, MOV-, load- and cash-aware. Deliberately weak baselines were not used; where a baseline fails a fixture it is because the fixture forbids its behaviour (unfinanceable lot), and that is shown as FAILED, not hidden. |
| J | What is the number a CFO should not believe? | Any TOTAL COST DELTA on these fixtures. They are development fixtures with configured economics; the deltas show the mechanisms work and reconcile, not what a customer will save. |

## 9. Persona review

- **Buyer / planner:** the explanation names the cadence, the lot rule and the tariff step that shaped the quantity, and nets off what is on hand and inbound. What is missing: a "what if I order half" counterfactual; that is P2 material.
- **Finance:** components reconcile to the cent; working capital and financing are separate from carrying; the capital charge is only on own cash. What finance will ask for and does not get here: a customer-provided cost of capital and holding rate (both CONFIGURED_ASSUMPTION on every fixture).
- **Supply-chain director:** cadence and consolidation are explicit candidates, not side effects; the freight tier and the FTL cap are respected by every plan. The `order_smoothing` finding is the item to decide on.
- **Sceptical engineer:** the target-basis gate is a real change to selector semantics and is the one item that could be argued; the ablation arm quantifies it. Fixture expectations were changed in three recorded places (window, S, N) and nowhere else.

## 7. Where ZAAD P1 loses, and why (no fix applied)

| fixture | ZAAD vs best baseline | cause from the review logs |
|---|---|---|
| C MOQ four weeks | +3.7% (seed 41001 alone: -2.3%) | under a 400-unit MOQ with no order cost and no cost of capital the model places its second lot as soon as it is cheaper than a stock-out on the scenario worlds, one to two reviews before the reorder-point rule does; the extra units end the window at terminal value. The timing tie-break is deliberately too small to move a lot-sized decision. |
| O low opening stock | +2.8% | an early stockout is unavoidable for every policy (review 0: "requested service targets are not jointly achievable"); ZAAD then runs on the 95% floor and pays shortage in the weeks realised demand exceeds the forecast, where the reorder-point rule's z-protection happens to cover it. |
| P high opening stock | +2.1% | same mechanism from review 5 on; on the `late` arm ZAAD is the cheapest policy. |

The common thread is that with a nil stress and an expected-service floor ZAAD's chosen plan sits
on the floor, and the independent truth draw lands above or below it. That is P0 behaviour and it
was not changed to make these pass. On the fixtures where order-level economics exist (B, F, G, H,
I, J, K, L, S, T) ZAAD P1 is the cheapest policy or within 1.6% of it.

Attribution expectations that fail: N expected LEAD_TIME_EXPOSURE but the three weeks of lead-time
demand are covered by the 350 units on hand, so the netted category is correctly zero; R expected
MOV but a $3,000 MOV against $5,500 of weekly demand at those prices never binds. Both are fixture-
design errors, left failing and explained.

## 10. Pass gate (reconstructed from the brief's requirements; 24 items)

| # | item | result |
|---|---|---|
| 1 | data model explicit (SupplierTerms, cost of capital, materiality, provenance, cadence) | PASS |
| 2 | units correct and stated (units, cases, pallets, currency per period, annual->period conversion explicit) | PASS |
| 3 | provenance on every economic input; missing data named, never invented | PASS |
| 4 | no duplicated economics (per-line fee vs supplier order cost; holding vs interest vs capital) | PASS |
| 5 | model and settlement carry the same rows (MOV, tiers, pallets, receiving, capital) | PASS |
| 6 | cost components reconcile to the settlement's economic cost | PASS (1,200 / 1,200 cells) |
| 7 | attribution partitions every order exactly | PASS |
| 8 | invariants script green | PASS (60 / 60) |
| 9 | timing under supplier calendars; next realistic replenishment | PASS |
| 10 | MOQ / case / pallet respected and attributed | PASS |
| 11 | MOV coordinated across SKUs | PASS |
| 12 | freight tiers, per-pallet freight, maximum load | PASS |
| 13 | payment terms, financing, carrying, capital with no double count | PASS |
| 14 | joint optimisation with cadence candidates | PASS |
| 15 | plain-language explanation per order | PASS |
| 16 | NO MATERIAL IMPROVEMENT AVAILABLE with configurable materiality | PASS |
| 17 | competent baselines, none deliberately weak | PASS |
| 18 | fixtures A-T pre-registered; deviations recorded | PASS with 5 recorded deviations |
| 19 | ZAAD not worse than the best baseline within tolerance on every fixture | **FAIL** (C, O, P) |
| 20 | pre-registered attribution expectations | **FAIL** (N, R: expectations wrongly written) |
| 21 | service floors respected; no physical failure of an accepted plan | PASS |
| 22 | runtime inside budget | PASS |
| 23 | Network Twin, frontend, Vercel, other worktrees, P0 evidence untouched; no Validation7 / 8 / holdout4; nothing merged; P2 and sector physics not started | PASS |
| 24 | verdict not softened | PASS (this document) |


## 9a. Explanation examples (period-0 orders of the first review, seed 41001, verbatim from the report)

- **B_fixed_order_cost_replace_sold**: Order 1058 units of A from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 996 extends cover by about 10.1 periods, avoiding about 10.1 orders ($2,516 in order-level costs) against about $72 of extra carrying and capital. Usable on hand 150 and inbound 0 were netted off.
- **I_max_pallets_ftl_cap**: Order 408 units of A from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 346 completes the pallet load or the freight tier the order lands on. Usable on hand 150 and inbound 0 were netted off.
- **T_combined_realistic**: Order 168 units of A from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 9 is case rounding; 60 lifts the supplier order to its minimum order value; 36 completes the pallet load or the freight tier the order lands on. Usable on hand 150 and inbound 0 were netted off. Order 168 units of B from supplier at review 0 (arrives period 1): 48 covers demand from arrival until the next realistic replenishment (period 2); 15 is service protection (LEAN); 9 is case rounding; 60 lifts the supplier order to its minimum order value; 36 completes the pallet load or the freight tier the order lands on. Usable on hand 150 and inbound 0 were netted off.
- **P_high_opening_stock**: (no period-0 order: the plan buys nothing this review)
- **M_order_calendar_wednesday**: Order 168 units of A from supplier at review 0 (arrives period 2): 48 covers demand before it lands in period 2; 99 covers demand from arrival until the next realistic replenishment (period 3); 19 is service protection (LEAN); 3 is not explained by the waterfall arithmetic (the joint solve found it cheaper; see the cost comparison). Usable on hand 150 and inbound 0 were netted off.

## 11. Final state

- Code and evidence at the SHA recorded in the last commit of `claude/zaad-cycle-stock-p1` (parent `2e30721`).
- Unit tests: 1431 passed, 2 skipped (full suite, final SHA). P1 tests: 23.
- Evidence files: `P1_GAP_ANALYSIS.md` (with amendment), `P1_RESULT_TABLE_{none,none_gate_incumbent,late,none_smoothing_0.02}.md`,
  `P1_EXPECTATIONS_*.json`, `P1_RUNTIME_*.json`, `fixtures_{none,gate,late,smooth}.jsonl`, `P1_INVARIANTS.json`, this file.
- Not started: P2 (network pooling, central versus local protection, transfer service windows, echelon accounting) and
  full sector physics (expiry / FEFO / cold chain / promotions).
- Untouched: Validation7, Validation8, holdout4 (unrun); Network Twin / PR #39; frontend; Vercel; production; other worktrees;
  P0 evidence (referenced only). Nothing merged. PR #38 and PR #39 remain as they were.
- Not claimed: production ready, industry proven, customer validated, guaranteed savings, optimizer complete.

**Recommended next step (not executed):** decide the two selector defaults this pass surfaced, with the P0
six-cell confirmation as the check: (1) whether `order_smoothing` should default to 0 whenever a supplier
declares order-level economics, and (2) whether `service_gate_basis="target"` should stand as the product
default. Then close the three fixture-parity exceptions by measuring the confirmation knife-edge (a
candidate optimised to exactly the service floor failing an independent draw) rather than by widening
any tolerance.
