# P1 CYCLE-STOCK ECONOMICS — CLOSE-OUT

> **Current verdict (candidate-comparability pass, 2026-09-09): P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.** See the CANDIDATE-COMPARABILITY PASS section; earlier passes are kept as the record they were.

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


# CLOSURE PASS (2026-09-08, second pass on this close-out)

**Verdict after the closure pass: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.**

Fixture parity now holds on 17 of 20 pre-registered fixtures at the original 2% tolerance, O and
P included; C remains outside at +2.3%. Two attribution expectations (N, R) are proven invalid by
the fixtures' own arithmetic and are left in the record as failing. No tolerance was widened, no
fixture, seed, window or baseline was changed, no expectation was edited.

## C1. Evidence lock

Recorded before any code change in `P1_CLOSURE_LOCK.md`: fixture definitions, seeds (41001-41003), window (11 reviews of a 12-period weekly plan), the 2% parity tolerance, the P1 defaults at SHA 3773944 and the five earlier deviations. None of C, O, P, their seeds, expectations, window or baselines was changed in this pass.

## C2. Root causes (decision-time versus truth-time trace, `closure/cop_trace.json`, `scripts/p1_cop_trace.py`)

| fixture | causal category | mechanism, with the numbers that establish it |
|---|---|---|
| O (low opening stock) and P (high opening stock), steady state | **1. SCENARIO COVERAGE** | Three iid scenario worlds let the plan protect only against the largest of three draws per period (median: the 79th percentile). The plan's projected service on those worlds sat 3-4 points above the 95% target (mean +0.031 / +0.036, never a knife-edge in projection), yet realised weekly service fell to .86-.94 whenever truth demand exceeded the best sampled draw, in 30-40% of weeks. The waterfall said "15 units of service protection" while the order was 12-17 units *below* the arithmetic need: the plan held no protection because its worlds never showed the tail. Same sign on every seed and both fixtures: systematic, not sampling noise. Economically the model was wrong on its own inputs: a stockout costs $7.5 net per unit, protection $0.014 per unit-period. |
| O, reviews 0-1 | **3. SELECTION (P0 recovery rule, left as is)** | With 20 units on hand and a one-week lead the review-0 stockout is unavoidable for every policy (78 units). The review is in recovery mode; P0's rule admits a candidate only if it *materially improves* the weighted shortfall, which nothing can, so the declared periodic incumbent's 294-unit order stands against the reorder-point baseline's 192. Reviews 0-1 are $185 of O's $152 total gap: over the other nine reviews ZAAD is net $33 better than the best baseline. This rule is P0 recovery logic and was not changed. |
| C (400-unit MOQ) | **5. HORIZON / TERMINAL EFFECT** | Under the MOQ the horizon-optimal plan buys the rest of the window in one lot (453, 608-618) rather than two 400s, and at the last reviews buys a 400 lot for a 38-56-unit expected deficit; the leftover is credited at the 80% terminal value inside the window. With the haircut removed (diagnostic only, plans unchanged) the gap is +1.58% before the fix and +1.58% after it, against +3.7% / +4.0% with it. The remainder is lot timing under an MOQ with near-zero holding and no cost of capital. |

The knife-edge hypothesis (step D) is rejected for all three: chosen-plan projected service minus target was +0.043 (C), +0.031 (O), +0.036 (P) on average and the per-world minimum was above the target on most reviews. The gap is between the sampled worlds and the truth's tail, not between the plan and the floor.

## C3. Calibration check (step E)

Demand quantiles: truth and scenario paths are drawn from the same bootstrap of the fixture history (sizes 89-111, sd 6); the fitted spread is right. Fill and lead distributions: deterministic on these fixtures (fill .98, lead 7 days). Correlation: none in truth. Sampling count: three. Scenario weighting: equal. Service floor: expected unit fill over the horizon and worlds. The under-representation is the sampling count combined with equal weights: the expectation is unbiased but the plan reacts to the realised sample, and with three draws the tail beyond the target is absent from most reviews. The fix therefore changes the representation, not the target and not a margin.

## C4. The fix (step H) and what it is not

1. **Target-stratified scenario worlds** (`worlds.draw`, `forecast.sample`, request field `stratified_scenarios=True`): S-1 body worlds drawn below the lowest service target (weight target/(S-1) each) and one tail world drawn above it (weight 1-target). Stratified sampling of the same fitted distribution: unbiased, no margin, the tail always present at its probability mass. The tail world varies per-period noise at the fitted level; the level shock and young-regime mixture stay in the body worlds (the unconditional form fabricated a path above an old demand regime and failed `test_young_regime_is_bounded_mixture_not_symmetric_widening`). Single-world and deterministic draws, which are every benchmark's truth path, are bit-identical to before (tested).
2. **Weight-aware selector statistics** (`planner._wmean`, `_service_value`, bootstrap, burden, materiality): every mean over evaluation rows respects scenario weights and reduces to the former plain mean under equal weights (tested), so equal-weight paths are unchanged.
3. **Leanness may not be bought with service** (`plan`, V7 ranking branch): inside the cost band the leanest plan wins only among plans whose expected shortage exposure on the selection worlds is no larger than the cheapest plan's. Before, a plan with no protection that paid the resulting shortage was "leanest" whenever that shortage cost less than the 5% band, which on a purchase-dominated cost is far more than protection costs to carry.
4. **Lean reviews only.** Items 1 and 3, and the target service-gate basis, apply when the review is lean: calm screen state (NO_ACTION, NORMAL_REPLENISHMENT, CAPITAL_OPTIMIZATION) and no active risk driver on any SKU/location. Under PROTECT, RECOVER, NETWORK_ALLOCATION, ESCALATE_UNKNOWN or any active driver, P0's own downside representation and rules stand unchanged. This split is the brief's NORMAL/LEAN versus RECOVERY/DISRUPTION line, and it was forced by evidence: the unconditional target gate and the unconditional stratified worlds each lost service on P0 cells 20 and 21 (section C5).

Not done: no safety-stock layer, no target + margin, no scenario-count change on the fixtures, no change to C/O/P definitions, seeds, window, tolerance or baselines, no change to any P0 recovery rule.

## C5. The two defaults against the frozen P0 six-cell set (step B)

Cells 15/16/20/21/90/108, seed 38001, the P0 close-out's own configuration (`scripts/p1_p0_arms.py`, `closure/p0_arm_*.json`).

ARM A (P1 code, P0 behaviour: incumbent gate, smoothing .02, no tie-break, no materiality gate) reproduces the P0 record: cells 15/16/20/90/108 identical to `final8_clean_warm_rule_deficit`; cell 21 within the recorded run-to-run band of time-limited solves (service .760 / breaches 5 / unmet 93 identical; inventory 130.5 vs 144.8).

ARM C (conditional smoothing) is identical to ARM A by construction: none of the six cells declares supplier terms or a fixed order fee, so `effective_smoothing` returns the declared .02 on every one (checked programmatically; recorded in the transcript of this pass).

**Timing tie-break (step G).** The coefficient is applied per unit-period of earliness scaled by 1/(H-1), so its total objective contribution is bounded by `timing_tiebreak` x purchase value: at the default that is 1e-4 of spend, two orders of magnitude below the 1% cost materiality and below the solver's own relative gap on any plan above $100. Proved by `test_timing_tiebreak_total_is_bounded_by_its_coefficient_times_purchase_value` at H=12 and H=30. It never enters projected cost or the ledger (`test_random_identical_world_reconciliation` reconciles model and settlement exactly). Decision: keep 1e-4, objective-only, horizon-scaled.

**Smoothing (step B2).** Decision: `order_smoothing` is applied only when the request declares no explicit order economics (no supplier terms, no per-line fixed order fee); with explicit economics it is switched off, because the proxy then double-counts lumpiness as an undeclared order cost (about 2% of landed cost per unit of change, roughly $200 on a 1,000-unit $5 order). The P0 default value .02 is unchanged and P0 cells are unaffected.

## C6. Default decisions (step B, concluded)

| default | decision | evidence |
|---|---|---|
| `service_gate_basis` | **"incumbent" (P0 rule) stays the default.** The target basis remains a request option, applied only on lean reviews when chosen. | Unconditional target gate on the P0 six-cell set: cell 20 service .894 -> .818 (6 breaches), cell 21 .760 -> .703 with one starved required class, cell 90 4 -> 5 breaches, cell 108 unmet 69.8 -> 76.0. Once the scenario representation was corrected, the fixtures the gate was introduced for pass without it (I +1.7%, O +1.7%, P -0.5% under the incumbent gate). |
| `stratified_scenarios` and the band guard | **default on, lean reviews only** (calm screen state, no active risk driver). | Unconditional: cell 20 .894 -> .792, cell 21 .760 -> .746. Lean-only with the incumbent gate: see the `final_incgate` row of the P0 table. |
| `order_smoothing` | **value .02 unchanged; applied only without explicit order economics.** | Identical to P0 on all six cells (none declares supplier terms or order fees; `effective_smoothing` returns .02 on each). On the fixtures the smoothing ablation moved C from +2.3% to +3.2% and F from +1.5% to +1.5% (categories), confirming the proxy fights consolidation where order economics exist. |
| `timing_tiebreak` | **1e-4, objective only, horizon-scaled.** | Bounded by 1e-4 x purchase value at any horizon (test at H=12 and H=30); never in projected cost or the ledger. |

## C7. Invalid expectations, proven (gate item 1)

Two pre-registered attribution expectations cannot hold by the fixture's own arithmetic. Neither fixture was edited; the checks stay in the record marked as proven invalid.

- **N (`LEAD_TIME_EXPOSURE` expected).** Lead-time demand is the fitted mean 98.9 x 3 periods = 297 units; usable on hand is 350; the netted category is max(0, 297 - 350) = 0 in every seed. The expectation was written on the gross requirement, which the waterfall (correctly) nets against on hand first.
- **R (`MOV` expected).** One period of mean demand at list prices is 100 x $5 + 100 x $50 = $5,441 per order against a $3,000 minimum order value: the MOV never binds on any order covering at least one period, so no MOV units can be attributed. The fixture was meant to make the MOV bind on the cheap line and was mis-sized.

## C8. Residual C, named

C fails parity at +2.3% (tolerance 2%). Cause 5, horizon/terminal: under a 400-unit MOQ the horizon-optimal plan buys the rest of the window in one lot and any last-review lot for a small expected deficit, and the leftover is credited at 80% of price inside the twelve-week window; with the haircut removed as a diagnostic (plans unchanged) C is +1.6%. Not sampling noise: the sign is the same on every seed. Not a systematic calibration problem: the demand representation is now correct on the fixtures where it mattered (O, P). Not changed: terminal value, window, MOQ, tolerance. The best next intervention is to value end-of-window stock at its continuation value in the benchmark rather than at salvage, which is a benchmark-design decision, not an optimizer change, and is not made here.


## C9. Targeted rerun (step I) and full A-T rerun (step J), final defaults

Targeted (C, O, P plus controls T, A, G, Q; `closure/targeted_fix3.json`): P +0.72%, O +2.37%, C
+4.03% under the target gate; the full run below is at the final defaults (incumbent gate).

Primary arm (nil declared stress, P1 defaults; `P1_RESULT_TABLE_none.md`, `fixtures_none.jsonl`):

17 / 20 fixtures pass

| fixture | incumbent | best baseline | ZAAD P1 | ZAAD vs incumbent | ZAAD vs best baseline | checks |
|---|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 | 5,824 (incumbent) | 5,825 | +0.0% | +0.0% | PASS |
| B_fixed_order_cost_replace_sold | 8,528 | 6,995 (economic_lot) | 6,262 | -26.6% | -10.5% | PASS |
| C_moq_four_weeks | 9,595 | 5,898 (reorder_point) | 6,034 | -37.1% | +2.3% | FAIL: zaad_not_worse |
| D_case_multiple | 5,807 | 5,807 (incumbent) | 5,771 | -0.6% | -0.6% | PASS |
| E_pallet_multiple | 6,239 | 6,239 (incumbent) | 6,239 | +0.0% | +0.0% | PASS |
| F_mov_two_skus | 14,040 | 11,766 (periodic:2) | 11,852 | -15.6% | +0.7% | PASS |
| G_freight_tiers | 21,400 | 16,720 (economic_lot) | 14,793 | -30.9% | -11.5% | PASS |
| H_per_pallet_freight | 6,884 | 6,826 (periodic:2) | 6,524 | -5.2% | -4.4% | PASS |
| I_max_pallets_ftl_cap | 16,274 | 9,814 (economic_lot) | 9,981 | -38.7% | +1.7% | PASS |
| J_net60_cost_of_capital | 7,478 | 6,850 (periodic:2) | 6,097 | -18.5% | -11.0% | PASS |
| K_deposit_early_cash | 7,490 | 6,862 (periodic:2) | 6,097 | -18.6% | -11.1% | PASS |
| L_high_holding_rate | 7,434 | 6,856 (periodic:2) | 6,165 | -17.1% | -10.1% | PASS |
| M_order_calendar_wednesday | 6,256 | 6,256 (incumbent) | 6,209 | -0.7% | -0.7% | PASS |
| N_long_lead_21_days | 5,937 | 5,937 (incumbent) | 6,043 | +1.8% | +1.8% | FAIL: categories |
| O_low_opening_stock | 6,521 | 6,399 (reorder_point) | 6,506 | -0.2% | +1.7% | PASS |
| P_high_opening_stock | 6,282 | 5,786 (reorder_point) | 5,758 | -8.3% | -0.5% | PASS |
| Q_volatile_demand_high_target | 5,971 | 5,971 (incumbent) | 5,971 | +0.0% | +0.0% | PASS |
| R_asymmetric_prices_mov | 63,448 | 63,448 (incumbent) | 63,941 | +0.8% | +0.8% | FAIL: categories |
| S_cash_constrained | 6,924 | 6,234 (economic_lot) | 6,176 | -10.8% | -0.9% | PASS |
| T_combined_realistic | 24,255 | 17,593 (economic_lot) | 15,598 | -35.7% | -11.3% | PASS |

ZAAD P1 mean service across the 60 gated cells 0.990; interventions 371 of 660 reviews,
NO MATERIAL IMPROVEMENT AVAILABLE on 6; attribution residual zero on every cell (partitions
exact); components reconcile to the settlement on every cell of every arm; invariants 60 / 60.

Arms (same fixtures and seeds):

| arm | passing | C | O | P |
|---|---|---|---|---|
| late | 16 / 20 | +2.38% | -0.07% | +0.66% |
| none | 17 / 20 | +2.31% | +1.67% | -0.48% |
| none_gate_target | 15 / 20 | +4.03% | +2.37% | +0.72% |
| none_smoothing_0.02 | 17 / 20 | +5.98% | +0.99% | -0.75% |

The target-gate arm is the ablation of the reverted default: with the representation fixed, the
target basis makes C, O and P worse. The smoothing arm shows the proxy's cost where order
economics exist (C +2.3% -> +6.0%).

Runtime, primary arm: p50 0.11 s, p90 0.92 s, p95 1.47 s, max
16.6 s per review; 87 s for the arm on three workers (the `late` arm took 913 s on
the same machine while a P0 cell ran alongside it; its per-review p95 is 1.9 s).

## C10. P0 six-cell arms (step B3)

| arm | cell | service | p10 | breaches | unmet | worst | inventory | cost | required done/req | starved | joint req/built/chosen | lat p50 | p95 | max |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| final | 15 | 0.983 | 1.000 | 1 | 4.2 | 4.2 | 50.0 | 1576 | 34/36 | **0** | 0/0/0 | 0.14 | 1.1 | 1.2 |
| final | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 1.0 | 3.9 |
| final | 20 | 0.916 | 0.000 | 3 | 32.3 | 17.0 | 203.2 | 2475 | 52/59 | **0** | 0/2/1 | 0.15 | 29.8 | 55.0 |
| final | 21 | 0.746 | 0.000 | 6 | 98.3 | 27.0 | 148.0 | 3590 | 47/65 | **0** | 9/14/6 | 0.78 | 29.4 | 54.7 |
| final | 90 | 0.863 | 0.220 | 4 | 70.1 | 22.0 | 121.0 | 3405 | 63/72 | **0** | 2/6/2 | 1.00 | 87.1 | 113.6 |
| final | 108 | 0.890 | 0.308 | 4 | 63.0 | 20.9 | 116.1 | 3677 | 74/78 | **0** | 2/6/1 | 7.19 | 133.1 | 153.1 |
| final_incgate | 15 | 0.983 | 1.000 | 1 | 4.2 | 4.2 | 50.0 | 1576 | 34/36 | **0** | 0/0/0 | 0.14 | 0.9 | 1.1 |
| final_incgate | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 1.0 | 4.0 |
| final_incgate | 20 | 0.916 | 0.000 | 3 | 32.3 | 17.0 | 203.2 | 2475 | 52/59 | **0** | 0/2/1 | 0.15 | 29.9 | 55.3 |
| final_incgate | 21 | 0.746 | 0.000 | 6 | 98.3 | 27.0 | 148.0 | 3580 | 47/65 | **0** | 9/14/5 | 0.69 | 29.9 | 55.2 |
| final_incgate | 90 | 0.863 | 0.220 | 4 | 70.1 | 22.0 | 121.0 | 3405 | 63/72 | **0** | 2/6/2 | 0.98 | 85.7 | 113.6 |
| final_incgate | 108 | 0.890 | 0.308 | 4 | 63.0 | 20.9 | 116.1 | 3677 | 74/78 | **0** | 2/6/1 | 6.84 | 133.1 | 153.1 |
| final_unconditional | 15 | 1.000 | 1.000 | 0 | 0.0 | 0.0 | 124.5 | 1620 | 36/36 | **0** | 0/0/0 | 0.11 | 1.2 | 5.1 |
| final_unconditional | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 160.2 | 1428 | 36/36 | **0** | 0/0/0 | 0.11 | 0.8 | 1.2 |
| final_unconditional | 20 | 0.792 | 0.000 | 7 | 80.6 | 18.9 | 176.5 | 2720 | 43/59 | **0** | 4/7/1 | 0.27 | 26.2 | 46.5 |
| final_unconditional | 21 | 0.746 | 0.000 | 6 | 98.3 | 27.0 | 121.6 | 3215 | 46/64 | **0** | 9/12/5 | 0.65 | 24.7 | 45.3 |
| final_unconditional | 90 | 0.859 | 0.223 | 5 | 72.3 | 22.0 | 271.8 | 3350 | 75/81 | **0** | 4/6/2 | 1.05 | 50.6 | 85.3 |
| final_unconditional | 108 | 0.906 | 0.308 | 4 | 54.0 | 21.0 | 275.0 | 3652 | 85/85 | **0** | 1/11/1 | 1.63 | 113.7 | 147.5 |
| gate | 15 | 1.000 | 1.000 | 0 | 0.0 | 0.0 | 63.2 | 1612 | 36/36 | **0** | 0/0/0 | 0.13 | 2.2 | 5.1 |
| gate | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 137.1 | 1425 | 36/36 | **0** | 0/0/0 | 0.09 | 1.1 | 1.1 |
| gate | 20 | 0.818 | 0.159 | 6 | 70.6 | 21.5 | 179.7 | 2678 | 53/67 | **0** | 8/9/3 | 0.21 | 26.5 | 57.8 |
| gate | 21 | 0.703 | 0.000 | 6 | 115.0 | 27.0 | 114.4 | 3362 | 47/65 | **1** | 11/11/5 | 0.46 | 26.0 | 58.5 |
| gate | 90 | 0.859 | 0.223 | 5 | 72.4 | 22.0 | 103.8 | 3360 | 63/72 | **0** | 4/8/0 | 0.36 | 63.2 | 100.2 |
| gate | 108 | 0.868 | 0.221 | 5 | 76.0 | 22.0 | 91.1 | 3696 | 64/76 | **0** | 2/8/2 | 1.49 | 122.9 | 153.1 |
| p0_defaults | 15 | 0.980 | 0.962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 32/36 | **0** | 0/1/0 | 0.13 | 1.3 | 1.6 |
| p0_defaults | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 0.8 | 2.5 |
| p0_defaults | 20 | 0.894 | 0.233 | 3 | 40.9 | 14.0 | 183.7 | 2502 | 50/58 | **0** | 0/3/2 | 0.17 | 25.6 | 59.8 |
| p0_defaults | 21 | 0.760 | 0.000 | 5 | 93.0 | 27.0 | 130.5 | 3257 | 45/61 | **0** | 7/10/5 | 0.74 | 30.0 | 60.2 |
| p0_defaults | 90 | 0.863 | 0.220 | 4 | 70.1 | 22.0 | 94.4 | 3315 | 57/64 | **0** | 1/3/1 | 0.81 | 81.1 | 113.7 |
| p0_defaults | 108 | 0.879 | 0.225 | 4 | 69.8 | 22.0 | 138.6 | 3723 | 74/78 | **0** | 0/5/1 | 3.20 | 133.0 | 153.1 |
| representation_only | 15 | 0.980 | 0.962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 32/36 | **0** | 0/1/0 | 0.12 | 1.3 | 2.3 |
| representation_only | 16 | 0.972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 30/36 | **0** | 0/2/0 | 0.13 | 0.9 | 3.9 |

Reading: `p0_defaults` (P1 code, P0 behaviour) reproduces the frozen record. `gate`
(unconditional target basis) regresses 20, 21, 90, 108. `final_unconditional` (stratified worlds
and guard everywhere) regresses 20 and 21. `final` and `final_incgate` (lean reviews only)
improve 15, 20 and 108, leave 16 identical, and move 21 (service -.014, cost +10%) and 90
(inventory +28% at identical service, joint recovery chosen on 2 reviews instead of 1). Required
starvation is zero in every arm and cell 21's recovery behaviour (joint recovery required and
chosen) is intact throughout. `representation_only` isolates the stratified worlds and guard from
the materiality gate and the tie-break: see C11.

## C11. Default decision after the isolating arm, and the final product defaults

`representation_only` (stratified worlds and band guard on lean reviews, P0 gate, no tie-break,
materiality gate off) against `p0_defaults`:

| cell | service | breaches | unmet | inventory | cost | starved | joint req/built/chosen |
|---|---|---|---|---|---|---|---|
| 15 | .980 -> .980 | 1 -> 1 | 5.0 -> 5.0 | 46.1 -> 46.1 | 1678 -> 1678 | 0 | 0/1/0 -> 0/1/0 |
| 16 | .972 -> .972 | 1 -> 1 | 7.0 -> 7.0 | 134.5 -> 134.5 | 1515 -> 1515 | 0 | 0/2/0 -> 0/2/0 |
| 20 | .894 -> .894 | 3 -> 3 | 40.9 -> 40.9 | 183.7 -> 183.7 | 2502 -> 2502 | 0 | 0/3/2 -> 0/3/2 |
| 21 | .760 -> .760 | 5 -> 5 | 93.0 -> 93.0 | 130.5 -> 147.5 (P0 record 144.8) | 3257 -> 3381 (record 3364) | 0 | 7/10/5 -> 9/14/5 (record 9/13/6) |
| 90 | .863 -> .858 | 4 -> 5 | 70.1 -> 72.6 | 94.4 -> 140.4 | 3315 -> 3388 | 0 | 1/3/1 -> 2/6/0 |
| 108 | .879 -> .885 | 4 -> 4 | 69.8 -> 65.9 | 138.6 -> 142.0 | 3723 -> 3673 | 0 | 0/5/1 -> 1/5/1 |

Cells 15, 16 and 20 are identical; cell 21 is identical on service, breaches and unmet and inside
the recorded run-to-run band on inventory and cost; cell 108 is better. Cell 90 is a genuine
regression: 49% more inventory, one more breach, service .863 -> .858, at the cell the P0 freeze
names for "no unnecessary joint protection". Required starvation is zero everywhere and cell 21's
recovery behaviour is intact. By the rule of this pass (a default that regresses P0 does not ship
as default), the representation is not the default.

The bundled arms (`final`, `final_incgate`) additionally moved cell 21 (service -.014, cost
+10%) and cell 15 (better); with the representation alone neutral on both, that movement belongs
to the materiality gate and the timing tie-break, which this pass did not separate.

**Final product defaults (all P0 behaviour, one provable no-op added):**

| field | default | P1 fixtures declare | why |
|---|---|---|---|
| `service_gate_basis` | `incumbent` (P0) | `incumbent` | unconditional target gate regressed 20/21/90/108; not needed once the representation is fixed |
| `stratified_scenarios` (with the band guard) | `False` | `True` | regresses cell 90 |
| `materiality_*` thresholds | 0 (gate off) | .01 / .05 / .005 | bundled movement on 21/90 not separated from the tie-break |
| `timing_tiebreak` | 0 | 1e-4 | same; bounded at 1e-4 of spend when on |
| `order_smoothing` | .02, applied only without explicit order economics | 0 | identical to P0 on every cell without order economics |

So the product's default behaviour on the P0 set is the frozen P0 behaviour (`p0_defaults` arm
reproduces the record), and the P1 result below is a result under declared request settings, not
under product defaults. That is stated as such and is one of the reasons P1 remains open.

## C12. Final state of the closure pass

- Unit tests at the final code state: 1436 passed, 2 skipped (final baseline was 1431 + 2; the 5 additions are the closure tests: stratified worlds, weighted statistics, conditional smoothing, tie-break bound, attributable protection).
- Invariants: 60 / 60. Attribution residual zero on every gated cell. Components reconcile to the settlement on every cell of every arm.
- Full A-T at the final code (declared fixture settings): 17 / 20. C +2.31% (parity), N and R attribution expectations proven invalid (C7). O +1.67%, P -0.48%, I +1.71%.
- P0 six-cell set under product defaults: identical to the frozen record (`p0_defaults`).
- Evidence files: `P1_CLOSURE_LOCK.md`, `closure/cop_trace.json`, `closure/p0_arm_{p0_defaults,gate,final_unconditional,final,final_incgate,representation_only}.json`, `closure/targeted_fix*.json`, `closure/TABLES.md`, `P1_RESULT_TABLE_*.md`, `P1_EXPECTATIONS_*.json`, `P1_RUNTIME_*.json`, `fixtures_*.jsonl`, `P1_INVARIANTS.json`.
- Not started: P2 and sector physics. Untouched: Validation7, Validation8, holdout4 (unrun, not inspected), Network Twin / PR #39, PR #38, frontend, Vercel, production, other worktrees. Nothing merged, pushed or opened.
- Not claimed: industry standard complete, production ready, customer validated, guaranteed savings.

**What was explicitly refused:** widening the 2% tolerance; editing C, O, P, their seeds, window, expectations or baselines; a generic safety margin; shipping any default that regressed a P0 cell; calling the C residual noise (it is the terminal haircut, same sign on every seed); calling the O/P finding noise (it was a systematic representation gap, now fixed under declared settings).

**Best next intervention (not executed):** (1) separate the materiality gate from the tie-break on the P0 six-cell set (two arms, about an hour) so each can be judged for default on its own; (2) understand cell 90 under the stratified representation - why the tail world raises inventory without service on that truth path - before proposing it as default; (3) decide, as a benchmark-design question, whether end-of-window stock should be valued at continuation value rather than salvage, which is what keeps C at +2.3%.


# DIAGNOSTIC PASS (2026-09-08, third pass on this close-out; from 673e3f8)

## D1. Cell 90: first divergence (arm A = frozen P0 behaviour, arm B = representation + guard, lean reviews only)

Traces: `closure/cell90_trace_p0_defaults.json`, `closure/cell90_trace_representation_only.json`
(`scripts/p1_cell90_trace.py`, `scripts/p1_cell90_diff.py`). Cell 90: one SKU, one location, one
source (no MOQ, no case pack, fill .97, lead 7 days), shared supplier and port capacity of 100 units
per period, target .95, 26 reviews, declared stress "operator_adverse" (fill x0.7, +28 days, demand
x1.1, recovery period 9, port), supply state "deterioration_recovery". Mechanisms 5 (MOQ / case
pack) and 7 (cross-SKU allocation) cannot apply: there is no lot rule and one SKU; the only shared
capacity is the 100-unit per-period cap, which matters below.

Reviews 0-15: decisions and settlements identical in A and B. Review 0's chosen label differs
(A deterministic_network, B cvar_network) but both execute the same 11-unit order and settle
identically; reviews 1-15 are PROTECT (active driver) so the representation is off by construction.

**Review 16 is the first material divergence** (first lean review after the disruption: profile
LEAN, activity 0, protection 52.7 units, on hand 32, no pipeline, demand about 20 per period):

| item | A (P0) | B (representation) |
|---|---|---|
| scenario demand paths, periods 0-5 | [32,12,12,23,23,14], [26,25,15,15,20,20], [28,15,20,20,22,12]; sums 203 / 194 / 185 | [17,24,13,9,23,16], [17,26,18,19,18,19], tail [29,29,29,29,29,29]; sums 171 / 195 / 292 |
| weights | 1/3 each | .475 / .475 / .050 |
| supply in the worlds (fill, arrival period of orders placed at 0,1,2) | fills .82/.97/.82, .82/.95/.83, .83/.82/.83; arrivals [3,2,5], [3,2,5], [3,4,5] | fills .98/.83/.82, .96/.96/.97, .97/.82/.96; arrivals [1,4,5], [1,2,3], [1,4,3] |
| candidate period-0 orders | incumbent 22, base_stock 22, deterministic 14, stochastic INFEASIBLE, cvar INFEASIBLE, joint_recovery 33 (then 100 at period 1) | incumbent 22, base_stock 22, deterministic 14, stochastic **100**, cvar **100** |
| service statistic (weighted unit fill over worlds) | incumbent .826, deterministic .768, joint .894 | incumbent .890, deterministic .812, stochastic .973, cvar .975 |
| per-world service of the chosen plan | joint .944 / .903 / .832 | cvar 1.0 / 1.0 / .677 (tail) |
| feasible set | empty -> recovery mode | stochastic, cvar |
| band guard | not reached (recovery mode) | cheapest = cvar (1124), exposure 51.9; stochastic 1125, exposure 55.9 -> band {cvar}; chosen cvar |
| selected / status | joint_recovery, PENDING_REVIEW | cvar_network, PENDING_REVIEW |
| executed order | 33 | 100 (= the per-period capacity cap) |
| attribution of the order | DEMAND_CYCLE 7, SERVICE_PROTECTION 26 | DEMAND_CYCLE 7, SERVICE_PROTECTION 53, OTHER_EXPLAINED 40 |
| review settlement | unmet 0, end stock 19.5 | unmet 0, end stock 19.5 (the order has not landed) |

Downstream (B): the 100 units land at review 17 (on hand 116 vs 51), the screen classifies
reviews 17-20 as CAPITAL_OPTIMIZATION and B buys nothing until review 22; inventory runs 96 / 79 /
62 / 54 against A's 31 / 16 / 20 / 36. At review 25 B arrives with 16 on hand (A: 23), every
candidate is infeasible on B's worlds (the tail world demands 27 against 16 on hand with a
3-period arrival), the incumbent's 36-unit order is retained and 2.4 units go unmet: the extra
breach. A at review 25 holds 23, its worlds ask 13-17, and it serves everything.

## D2. Why the 100-unit order: two mechanisms, separated

**(a) Random-stream coupling.** The stratified sampler draws demand through `rng.random(H)`
instead of `rng.choice(sizes, H)` + `rng.random(H)`, and the tail world skips the level-shock
draw, so every random number drawn *after* demand (the shared supply factors that set fill and
arrival) comes from a shifted stream. That is why B's worlds at review 16 see orders landing in
1 period with fill .96-.98 where A's see 3-5 periods with fill .82. The supply the plan believes
in is a different random sample, not a different representation. `STRATIFY_DECOUPLED_RNG` draws
the strata from a generator of their own and consumes the main stream exactly as an unstratified
draw would; with it on, fills, arrivals and PO due dates are bit-identical to the unstratified
draw on the fixture and on cell 90 (checked). Arm `c90_strat_decoupled` measures cell 90 with
only this changed.

**(b) The correlated tail path.** The tail world is [29, 29, 29, ...]: 45% above the fitted
level in every one of the remaining ten periods, at weight .05. Per period that is the 95th
percentile, which is what the stratum is meant to be; as a path it is a ten-period run of 95th
percentile weeks, which in the fitted world has probability of order 0.05^10, not 0.05. Where an
order can be placed and land next period (the P1 fixtures: lead one week, capacity unbounded) the
path costs nothing to follow, because each period's decision only has to cover the next week's
tail draw. Where supply is slow and capped (cell 90 after the disruption: arrivals 3-5 periods,
100 units per period) the only way to cover a ten-period run is to buy the cap now, and the CVaR
candidate does exactly that: 100 units, of which the attribution can explain 60 and calls 40
OTHER_EXPLAINED. This is mechanism 8 of the brief, dependence information lost by stratifying
per world rather than per period.

Mechanisms tested by arm (cell 90 only, one switch each on top of the representation):
`c90_guard_only` (4), `c90_strat_noguard` (1+2+3 without 4), `c90_strat_equal_weights` (2),
`c90_strat_unweighted_stats` (3), `c90_strat_body_iid` (1: body restriction), `c90_strat_decoupled`
(1: stream coupling). Results in D3.


## D3. Cell 90 mechanism arms (one switch each; `closure/p0_arm_c90_*.json`)

| arm (cell 90) | service | breaches | unmet | inventory | cost | starved | joint req/built/chosen |
|---|---|---|---|---|---|---|---|
| p0_defaults | 0.863 | 4 | 70.1 | 94.4 | 3315 | 0 | 1/3/1 |
| c90_guard_only | 0.863 | 4 | 70.1 | 95.8 | 3317 | 0 | 1/3/1 |
| representation_only | 0.858 | 5 | 72.6 | 140.4 | 3388 | 0 | 2/6/0 |
| c90_strat_noguard | 0.858 | 5 | 72.6 | 140.4 | 3388 | 0 | 2/6/0 |
| c90_strat_equal_weights | 0.863 | 4 | 70.1 | 150.1 | 3357 | 0 | 1/7/1 |
| c90_strat_unweighted_stats | 0.863 | 4 | 70.1 | 139.3 | 3354 | 0 | 1/9/3 |
| c90_strat_body_iid | 0.859 | 5 | 72.2 | 120.6 | 3397 | 0 | 2/6/2 |

Reading. The band guard is neutral (mechanism 4 cleared). The stratified worlds without the guard
reproduce the full regression, so the worlds are the whole effect. The **extra breach is the
selector's weighted statistic (mechanism 3)**: it appears exactly when the tail world enters the
selector's service and shortfall statistics at weight .05 (`representation_only`, `strat_noguard`,
`strat_body_iid`) and disappears when the selector treats worlds equally with the model's weights
untouched (`strat_equal_weights`, `strat_unweighted_stats`). At weight .05 a plan whose service in
the tail world is .677 still clears the weighted floor at .975 (review 16), so the selector admits
plans with a worse tail than P0's equal-weight floor would, and review 25 pays with 2.4 unmet
units. The **inventory rise is the world construction (mechanisms 1 and 8)**: present in every
stratified arm (121-150 units against 94) whatever the weights, statistic or guard, and traced at
review 16 to the CVaR candidate buying the 100-unit capacity cap against a ten-period run of
95th-percentile demand. Drawing the body worlds over the full range narrows it (121) but keeps it.
The decoupled-RNG arm (D3a, below) separates the random-stream shift from the tail path.

## D4. Materiality gate versus tie-break, isolated (`closure/p0_arm_{neither,materiality_only,tiebreak_only,both}.json`)

| arm | cell | service | breaches | unmet | inventory | cost | starved | joint req/built/chosen |
|---|---|---|---|---|---|---|---|---|
| p0_defaults | 15 | 0.980 | 1 | 5.0 | 46.1 | 1678 | 0 | 0/1/0 |
| neither | 15 | 0.980 | 1 | 5.0 | 46.1 | 1678 | 0 | 0/1/0 |
| materiality_only | 15 | 0.980 | 1 | 5.0 | 46.1 | 1678 | 0 | 0/1/0 |
| tiebreak_only | 15 | 0.983 | 1 | 4.2 | 50.0 | 1576 | 0 | 0/0/0 |
| both | 15 | 0.983 | 1 | 4.2 | 50.0 | 1576 | 0 | 0/0/0 |
| p0_defaults | 16 | 0.972 | 1 | 7.0 | 134.5 | 1515 | 0 | 0/2/0 |
| neither | 16 | 0.972 | 1 | 7.0 | 134.5 | 1515 | 0 | 0/2/0 |
| materiality_only | 16 | 0.972 | 1 | 7.0 | 134.5 | 1515 | 0 | 0/2/0 |
| tiebreak_only | 16 | 0.972 | 1 | 7.0 | 134.5 | 1515 | 0 | 0/2/0 |
| both | 16 | 0.972 | 1 | 7.0 | 134.5 | 1515 | 0 | 0/2/0 |
| p0_defaults | 20 | 0.894 | 3 | 40.9 | 183.7 | 2502 | 0 | 0/3/2 |
| neither | 20 | 0.894 | 3 | 40.9 | 183.7 | 2502 | 0 | 0/3/2 |
| materiality_only | 20 | 0.894 | 3 | 40.9 | 183.7 | 2502 | 0 | 0/3/2 |
| tiebreak_only | 20 | 0.919 | 3 | 31.2 | 188.7 | 2465 | 0 | 0/2/1 |
| both | 20 | 0.919 | 3 | 31.2 | 188.7 | 2465 | 0 | 0/2/1 |
| p0_defaults | 21 | 0.760 | 5 | 93.0 | 130.5 | 3257 | 0 | 7/10/5 |
| neither | 21 | 0.760 | 5 | 93.0 | 119.0 | 3366 | 0 | 9/12/6 |
| materiality_only | 21 | 0.760 | 5 | 93.0 | 119.0 | 3404 | 0 | 9/12/5 |
| tiebreak_only | 21 | 0.760 | 5 | 93.0 | 144.8 | 3364 | 0 | 9/13/6 |
| both | 21 | 0.760 | 5 | 93.0 | 144.8 | 3364 | 0 | 9/13/6 |
| p0_defaults | 90 | 0.863 | 4 | 70.1 | 94.4 | 3315 | 0 | 1/3/1 |
| neither | 90 | 0.863 | 4 | 70.1 | 95.8 | 3317 | 0 | 1/3/1 |
| materiality_only | 90 | 0.863 | 4 | 70.1 | 95.8 | 3317 | 0 | 1/3/1 |
| tiebreak_only | 90 | 0.863 | 4 | 70.1 | 124.5 | 3361 | 0 | 0/5/2 |
| both | 90 | 0.863 | 4 | 70.1 | 124.5 | 3361 | 0 | 0/5/2 |
| p0_defaults | 108 | 0.879 | 4 | 69.8 | 138.6 | 3723 | 0 | 0/5/1 |
| neither | 108 | 0.884 | 5 | 66.9 | 142.4 | 3665 | 0 | 0/5/0 |
| materiality_only | 108 | 0.884 | 5 | 66.9 | 142.4 | 3665 | 0 | 0/5/0 |
| tiebreak_only | 108 | 0.890 | 5 | 63.5 | 135.9 | 3658 | 1 | 0/7/1 |
| both | 108 | 0.890 | 5 | 63.5 | 135.9 | 3658 | 1 | 0/7/1 |


Reading. `neither` (current product defaults, which include the lean-review band guard) is
identical to the P0 record on 15, 16, 20 and 90; cell 21 is identical on service, breaches and
unmet with inventory inside the recorded band (119 against 130-145 across the P0 runs); cell 108
is inside the band of its time-limited solves (service .884 against .879, one more breach, less
unmet). **The materiality gate alone is identical to `neither` on all six cells**: it never fires
on the P0 set. Neutrality demonstrated; it becomes the default. **The tie-break alone** improves
cells 15, 20 and 108 on service, unmet and cost, is identical on 16, lands cell 21 exactly on the
P0 record, and keeps cell 90's inventory inside the recorded band (124.5 against 94-124), but
**cell 108 shows one starved required class** (a required candidate hit its time budget with no
usable plan once the ties were broken differently). Starvation must stay zero, so the tie-break
stays opt-in. `both` equals `tiebreak_only`, as the materiality gate is neutral. The earlier
bundled movement on cells 15 and 21 is therefore the tie-break's (15) and, for 21, the
representation's interaction with it, not the materiality gate's.
## D5. C as a finite-horizon economics problem (objective 3; `scripts/p1_c_economics.py`, `closure/c_economics.json`)

Fixture C unchanged (400-unit MOQ, replace-sold incumbent, three seeds, eleven reviews of a
twelve-period plan, salvage 80% of the $5 price, holding 15% a year, no cost of capital, fill .98).
ZAAD P1 under its declared fixture settings against the best baseline (reorder point with
protection), means over the three seeds:

| component | ZAAD | baseline | delta |
|---|---|---|---|
| purchase (procurement) | 6,359.5 | 6,000.0 | +359.5 |
| carrying (holding) | 57.9 | 30.0 | +27.9 |
| shortage (SLA + lost sales) | 0.0 | 0.0 | 0.0 |
| order / setup | 0.0 | 0.0 | 0.0 |
| terminal credit at salvage (closing assets) | -1,133.4 | -882.4 | -250.9 |
| **total modelled cost** | **6,034** | **5,898** | **+136 (+2.31%)** |
| units purchased | 1,271.9 | 1,200.0 | +71.9 |
| demand served / demand | 1,103 / 1,103 | 1,103 / 1,103 | identical |
| residual at window end (on hand + in transit) | 283.3 (155 on hand, 128 in transit) | 220.6 (all on hand) | +62.7 |
| residual above one period of demand plus lean protection | 169 | 107 | +62 |
| MOQ top-up units attributed in ZAAD's period-0 orders | 562 | - | - |

Both policies serve every unit of demand with no shortage. The entire delta is timing and
end-of-window valuation: ZAAD buys one more MOQ lot inside the window (the 128 units still in
transit at the end are its last lot; the baseline's next lot falls after the window), carries
larger lots earlier (+$28 of holding at a rate of 0.29% a period), and is credited for its 62 extra
residual units at 80% of what it paid.

Terminal valuation sensitivity (post-hoc revaluation of the residual, both policies alike; plans
unchanged):

| valuation of residual stock | ZAAD | baseline | delta |
|---|---|---|---|
| 80% salvage (current default) | 6,034 | 5,898 | +2.31% |
| 100% purchase value (= zero haircut here, asset value equals price) | 5,751 | 5,677 | +1.30% |
| continuation value: price less carrying until consumption at the fitted rate, unit by unit | 5,758 | 5,680 | +1.36% |
| extended horizon: twelve further truth periods drawn from the same fitted distribution, residual consumed at price, carrying charged, remainder at salvage | 5,755 | 5,679 | +1.35% |

Continuation value method: the k-th residual unit is consumed k/mu periods after the window at
the fitted rate mu; its value is the purchase it avoids (price) less the carrying it incurs until
then (holding rate x price x k/mu); no obsolescence term because shelf life is 52 weeks against a
residual of 1.6-2.9 weeks of demand. On the extended truth every residual unit of both policies is
consumed (ZAAD 283 of 283 within 2.9 periods, baseline 221 of 221 within 2.2), so the empirical and
the derived continuation values agree to $3.

Reading: 1.0 of the 2.3 points is the salvage haircut on stock that is consumed within three
weeks of the window's end, a measurement artefact of a twelve-week window on a policy that buys
in four-week lots. The remaining 1.3 points is real and small: $28 of carrying for lots placed
earlier than the reorder-point rule places them, and the window-boundary purchase of the last lot.
Over a longer horizon the two policies buy the same units and serve the same demand; ZAAD's is
not a bad policy, it is a lot-timing choice that costs about $75 on $5,700 at a holding rate that
makes timing nearly free. It is not sampling noise: the sign is the same on all three seeds. No
default was changed on this basis; the salvage treatment stays as it is, and the choice of terminal
valuation for the benchmark is recorded as an open design question, not decided here.

## D3a. Random-stream coupling separated from the tail path (`closure/p0_arm_c90_strat_decoupled.json`, `closure/cell90_trace_c90_strat_decoupled.json`)

The first-pass stratified sampler read its strata uniforms from the main random stream in place
of the bootstrap draws, so every supply shock, PO due date and level draw sampled afterwards came
from a shifted stream: arm B's worlds at review 16 saw orders landing in one period with fill
.96-.98 where P0's saw three to five periods with fill .82, and that is what made B's stochastic
and CVaR candidates feasible there. The stream-preserving construction (strata uniforms read, the
generator state restored, then the stream consumed exactly as an unstratified draw consumes it)
makes fills, arrivals and PO due dates bit-identical to the unstratified draw (checked on the
fixture and on cell 90; `test_stratified_draw_leaves_the_supply_sample_untouched`).

| arm (cell 90) | service | breaches | unmet | inventory | cost | starved |
|---|---|---|---|---|---|---|
| P0 record | .863 | 4 | 70.1 | 94.4 | 3315 | 0 |
| stratified, coupled stream (first pass) | .858 | 5 | 72.6 | 140.4 | 3388 | 0 |
| stratified, stream preserved | .864 | 4 | 69.9 | 127.4 | 3402 | 0 |

With P0's own supply sample the extra breach is gone and service is P0's; the inventory rise
remains (+35%, just above the recorded 94-124 band; +49% to +59% in the arms that also weight or
equal-weight the tail world). The diverging reviews in the PROTECT phase of this arm (orders 23 vs
36 at review 5, and so on) follow a one-unit difference at review 0 and are the known
path-dependence of time-limited solves on this cell, not the representation, which is off in
those reviews.

**Root cause of cell 90, complete.** (i) Inventory: the stratified representation's tail world is
one fixed path at or above the 95th percentile in every period, a ten-period run whose fitted
probability is of order .05^10 but which carries weight .05; under the slow, capacity-capped supply
that follows the disruption, the only plan that covers it is to buy the 100-unit per-period cap at
the first lean review, and the screen then reads that stock as capital to optimise for four
reviews. Mechanism 8 (dependence lost by stratifying per world). (ii) The extra breach: the
selector's weighted service statistic admits, at weight .05, a plan whose service in the tail
world is .677 (mechanism 3), and the coupled random stream (a defect of the first implementation,
now fixed) handed the selector a more benign supply sample to admit it on. The band guard,
probability weighting in the model, MOQ/case-pack, cross-SKU allocation and the tie-break are
cleared for this cell.

## D6. Decisions of the diagnostic pass

| item | decision | causal basis |
|---|---|---|
| stratified representation (`stratified_scenarios`) | stays opt-in; the opt-in sampler now preserves the supply stream | explained (D3, D3a); the inventory effect is intrinsic to a fixed tail path and is not fixed here. A per-period stratification (each period one world in the tail stratum, equal weights) would restore independence and is the candidate design for the next pass; it has not been built or measured |
| band guard | stays tied to lean reviews, on by default | neutral on cell 90 and on the six-cell set (`neither` arm) |
| materiality gate | **becomes default** (.01 / .05 / .005) | identical to product defaults on all six cells; fires only on immaterial improvements (fixture A) |
| timing tie-break | stays opt-in (0) | improves 15, 20, 108 and is exact on 21, but one starved required class on cell 108; starvation must be zero |
| service gate basis | incumbent (unchanged) | first closure pass |
| smoothing rule | unchanged | provable no-op on the six cells |
| C | no change | finite-horizon artefact for 1.0 of 2.3 points, real lot-timing cost for the rest (D5) |

## D7. Justified code changes, reruns and final state of the diagnostic pass

**Code changes (two, both causally justified, neither made to improve the scorecard):**
1. `materiality_*` thresholds default to .01 / .05 / .005: the gate alone is identical to product
   defaults on every cell of the frozen six-cell set (D4).
2. The opt-in stratified sampler preserves the random stream, so the supply sample is identical
   with or without the demand strata (D3a). This corrects a defect of the first implementation; it
   is confined to the opt-in feature and every truth path stays bit-identical.

Everything else stays as decided in the closure pass: representation opt-in, tie-break opt-in,
incumbent gate, conditional smoothing, guard on lean reviews. No tolerance, fixture, expectation,
seed, window, baseline or terminal valuation was changed.

**Targeted C/O/P rerun (`closure/targeted_diag.json`), declared fixture settings:** C +1.05%,
O +1.29%, P +0.18%, all inside the pre-registered 2%; controls A +0.02%, G -4.8%, Q +0.39%,
T -10.9%; service C 1.000, O .923, P .991; shortage unchanged or lower on every one.

**Full A-T (`P1_RESULT_TABLE_none.md`, `fixtures_none.jsonl`):** 17 / 20.

| fixture | incumbent | best baseline | ZAAD P1 | ZAAD vs best baseline | checks |
|---|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 | 5,824 (incumbent) | 5,825 | +0.02% | PASS |
| B_fixed_order_cost_replace_sold | 8,528 | 6,995 (economic_lot) | 6,236 | -10.84% | PASS |
| C_moq_four_weeks | 9,595 | 5,898 (reorder_point) | 5,959 | +1.05% | PASS |
| D_case_multiple | 5,807 | 5,807 (incumbent) | 5,777 | -0.51% | PASS |
| E_pallet_multiple | 6,239 | 6,239 (incumbent) | 6,239 | +0.00% | PASS |
| F_mov_two_skus | 14,040 | 11,766 (periodic:2) | 11,803 | +0.31% | PASS |
| G_freight_tiers | 21,400 | 16,720 (economic_lot) | 15,925 | -4.75% | PASS |
| H_per_pallet_freight | 6,884 | 6,826 (periodic:2) | 6,577 | -3.65% | PASS |
| I_max_pallets_ftl_cap | 16,274 | 9,814 (economic_lot) | 10,206 | +3.99% | FAIL: zaad_not_worse |
| J_net60_cost_of_capital | 7,478 | 6,850 (periodic:2) | 6,077 | -11.29% | PASS |
| K_deposit_early_cash | 7,490 | 6,862 (periodic:2) | 6,077 | -11.44% | PASS |
| L_high_holding_rate | 7,434 | 6,856 (periodic:2) | 6,148 | -10.33% | PASS |
| M_order_calendar_wednesday | 6,256 | 6,256 (incumbent) | 6,276 | +0.32% | PASS |
| N_long_lead_21_days | 5,937 | 5,937 (incumbent) | 6,041 | +1.74% | FAIL: categories |
| O_low_opening_stock | 6,521 | 6,399 (reorder_point) | 6,481 | +1.29% | PASS |
| P_high_opening_stock | 6,282 | 5,786 (reorder_point) | 5,797 | +0.18% | PASS |
| Q_volatile_demand_high_target | 5,971 | 5,971 (incumbent) | 5,994 | +0.39% | PASS |
| R_asymmetric_prices_mov | 63,448 | 63,448 (incumbent) | 63,413 | -0.06% | FAIL: categories |
| S_cash_constrained | 6,924 | 6,234 (economic_lot) | 6,117 | -1.88% | PASS |
| T_combined_realistic | 24,255 | 17,593 (economic_lot) | 15,679 | -10.88% | PASS |

I moves from +1.7% to +4.0% and is the one parity failure. Cause, from the review outcomes on all
three seeds: with the supply sample now P0's, the nil-stress adversary worlds carry the tail world,
and the P0 incumbent-basis stress gate compares service world by world, so the lean full-load
candidates lose to the replace-sold incumbent on the tail world and are retained more often (4.0
orders per run instead of 3.7; freight $3,800 against $3,633). It is the same selector-statistic
mechanism as cell 90's breach (D3), acting through the stress gate rather than the feasibility
floor. Not corrected here: the correction would be a per-period stratification with equal weights
(no fixed tail path) and it has not been designed or measured. N and R remain the two attribution
expectations proven invalid (closure pass, C7).

Runtime, primary arm: p50 0.12 s, p90 0.84 s, p95 1.27 s, max 16.6 s per review.

**Invariants:** 60 / 60. **Unit suite:** 1437 passed, 2 skipped (one new test). **P0 six-cell set
under product defaults:** identical to the frozen record on 15, 16, 20 and 90, inside the recorded
bands on 21 and 108, starvation zero (D4, arm `neither`).

**Verdict: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.** C, O and P now meet the pre-registered
parity under the declared fixture settings; I does not, for a named selector mechanism; the
representation that makes C/O/P pass is not a product default because it raises inventory on P0
cell 90 through a fixed tail path whose correction is designed but not built.

**Best next intervention (not executed):** per-period stratification with equal world weights
(each period exactly one world in the tail stratum, rotating), which removes both the fixed
ten-period tail path (cell 90's inventory) and the .05 weight in the selector statistics (cell
90's breach, fixture I's retentions), then the same isolating arms again. Separately, a benchmark
decision on terminal valuation (D5).


# FINAL SCENARIO-REPRESENTATION CLOSURE (2026-09-08, fourth pass on this close-out; from 70511be)

**Verdict: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.** The per-period equal-weight sampler is
statistically clean, preserves every random stream, removes the cell-90 pathology and brings I and
O inside the gate, but it does not bring P (and, at S=3, C) inside it, and no unbiased equal-weight
representation with three worlds can: the expected number of tail draws per period is 3 x .05 =
.15. It is rejected as the closure fix and kept only as the opt-in representation (it replaces the
fixed-tail construction, which is removed). Nothing else was changed; no tolerance, fixture,
expectation, seed, baseline or terminal valuation moved.

## E1. Sampler architecture (`worlds.draw`, `stratified_scenarios`)

Per-period Latin hypercube with equal weights. For every service and period an independent random
permutation assigns the S worlds to S equal-mass strata of the fitted demand distribution and each
world draws uniformly inside its stratum (through the mixture quantile function of `sample`). So
every period has exactly one world in each stratum (the upper stratum is present in every period),
no world is high in every period, the permutations are independent across periods (no temporal
dependence is introduced), the per-period marginal is the fitted distribution exactly, and the
worlds carry weight 1/S. The strata uniforms are read from the main stream and the generator state
is restored, after which the stream is consumed exactly as an unstratified draw consumes it.

Differences from the fixed-tail stratification of the closure pass: no world is a fixed tail path
(that path was a ten-period run of 95th-percentile weeks with fitted probability of order .05^10
carrying weight .05, and it drove cell 90's capacity-cap buy); no .05 weight enters the selector
(that weight admitted a plan with .677 tail service and caused cell 90's extra breach); and the
supply stream is untouched (the first implementation shifted it).

## E2. Statistical validation (`scripts/p1_sampler_validation.py`, `closure/sampler_validation.json`; 400 seeds x 3 worlds x 12 periods per sampler, fitted reference 1,000 single-world draws)

| statistic | fitted | iid 3 worlds | per-period LHS 3 worlds |
|---|---|---|---|
| mean | 98.87 | 98.95 | 98.89 |
| sd | 6.04 | 6.10 | 6.09 |
| q50 | 98.74 | 98.99 | 98.92 |
| q79 | 104.66 | 104.88 | 104.81 |
| q90 | 107.30 | 107.39 | 107.26 |
| q95 | 108.62 | 108.73 | 108.67 |
| q99 | 110.00 | 110.01 | 109.99 |
| tail frequency above fitted q95 | .050 by definition | 0.055 | 0.052 |
| lag-1 autocorrelation within a world | -0.110 | -0.097 | -0.100 |
| longest tail run (periods above fitted q95) | - | 3 | 3 |
| tail runs of 3+ per world | - | 0.006 | 0.005 |
| periods with some world above fitted q79 | - | 0.523 | 0.651 |
| periods with some world above fitted q90 | - | 0.280 | 0.293 |
| world weights | - | 1/3 | [0.333333] |

No bias in mean, spread or quantiles; tail frequency at the fitted 5%; the negative lag-1
autocorrelation is a property of the bootstrap history and is the same in the fitted and iid
draws; tail runs are the iid ones (no manufactured persistence); coverage of the upper tercile
rises from 52% to 65% of periods by construction, coverage of the top decile barely moves (28% to
29%), which is the limit of three equal-weight worlds.

## E3. Random-stream preservation

Supply fills, arrival periods, PO due dates and PO fills are bit-identical with and without the
strata on 50 seeds of the fixture and on cell 90's request; single-world truth paths and
deterministic draws are bit-identical (`test_stratified_draw_leaves_supply_and_truth_streams_bit_identical`,
`sampler_validation.json`: supply_streams_identical_50_seeds true, truth_paths_identical_50_seeds true).

## E4. Cell 90, three arms (same seed, solver settings, supply and truth paths, gates and selector; P0 defaults otherwise)

| arm | service | breaches | unmet | inventory | cost | starved | joint req/built/chosen |
|---|---|---|---|---|---|---|---|
| ARM 0 frozen P0 representation | 0.863 | 4 | 70.1 | 94.4 | 3315 | 0 | 1/3/1 |
| ARM 1 fixed-tail stratification (closure pass) | 0.858 | 5 | 72.6 | 140.4 | 3388 | 0 | 2/6/0 |
| ARM 2 per-period equal-weight LHS | 0.863 | 4 | 70.1 | 128.8 | 3367 | 0 | 0/6/2 |

ARM 2 is identical to P0 on service, breaches, unmet and starvation. The review-16 pathology is
gone: reviews 0-16 are identical to P0 (the fixed-tail arm diverged at 16 with the 100-unit cap
buy). First divergence is review 18, a recovery-mode review in both arms (every candidate
infeasible, 33 on hand): both propose joint recovery (P0 73 units, ARM 2 81 units); P0's
confirmation rejects it as not a material shortfall improvement, ARM 2's confirmation accepts it.
That is P0's own recovery rule on a statistically equivalent sample; the order is attributed 6
DEMAND_CYCLE / 53 SERVICE_PROTECTION / 23 OTHER_EXPLAINED, the resulting stock is read as
CAPITAL_OPTIMIZATION for three reviews and the difference decays by review 24 (34 vs 35 on hand).
Inventory 128.8 sits above the frozen band's top (94.2 warm, 124.1 pre-warm) by 4%, below the
fixed-tail arms' 140-150. Scenario services of the chosen plan on ARM 2's worlds at review 18: 1.0
/ 1.0 / .758 (P0's: 1.0 / 1.0 / .772).

## E5. Targeted check (`closure/targeted_lhs.json`)

| fixture | ZAAD vs best baseline | service | breaches | unmet | inventory | result |
|---|---|---|---|---|---|---|
| C | +4.27% | 1.000 | 0.3 | 5.9 | 239 | FAIL |
| O | +1.01% | .916 | 2.3 | 93.3 | 54 | pass |
| P | +2.38% | .977 | 2.3 | 25.8 | 145 | FAIL |
| I | +0.43% | 1.000 | 0.0 | 0.0 | 244 | pass |
| T (strong win) | -15.2% | 1.000 | 0 | 0 | 858 | control |
| A (abstention) | +0.00% | .992 | 1.0 | 9.2 | 15 | control, 0 interventions |
| G (freight) | -7.8% | 1.000 | 0 | 0 | 822 | control |
| Q (protection) | -0.15% | .988 | 1.0 | 13.9 | 63 | control |

P's numbers (service .977, breaches 2.3, unmet 25.8) are the iid P0 numbers exactly: on P the
decisive candidate is the deterministic mean-world plan, which no sampler touches, and the LHS
worlds do not make the stochastic candidate cheaper by enough to displace it inside the cost band.

World-count trade-off, diagnostic only (fixture scenario counts unchanged in the record):

| S | C | O | P | I | targeted wall time |
|---|---|---|---|---|---|
| 3 (fixture) | +4.27% | +1.01% | +2.38% | +0.43% | 35 s |
| 6 | +1.30% | +0.96% | +2.31% | +0.47% | 48 s |
| 10 | +0.62% | +0.78% | +2.15% | +3.73% | 134 s |

More worlds close C but never P, and at S=10 lose I again at four times the runtime.

## E6. P0 six-cell regression

Not run for the LHS sampler beyond cell 90: the targeted check failed (step F), and the protocol
requires it to pass first. The product-default six-cell record stands (D4, arm `neither`).

## E7. Full A-T

Declared fixture settings (LHS on, tie-break 1e-4), `P1_RESULT_TABLE_none.md`: **16 / 20**.

| fixture | best baseline | ZAAD P1 | delta | checks |
|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 (incumbent) | 5,824 | +0.00% | PASS |
| B_fixed_order_cost_replace_sold | 6,995 (economic_lot) | 6,265 | -10.43% | PASS |
| C_moq_four_weeks | 5,898 (reorder_point) | 6,149 | +4.27% | FAIL: zaad_not_worse |
| D_case_multiple | 5,807 (incumbent) | 5,762 | -0.78% | PASS |
| E_pallet_multiple | 6,239 (incumbent) | 6,239 | +0.00% | PASS |
| F_mov_two_skus | 11,766 (periodic:2) | 11,865 | +0.84% | PASS |
| G_freight_tiers | 16,720 (economic_lot) | 15,409 | -7.84% | PASS |
| H_per_pallet_freight | 6,826 (periodic:2) | 6,513 | -4.59% | PASS |
| I_max_pallets_ftl_cap | 9,814 (economic_lot) | 9,856 | +0.43% | PASS |
| J_net60_cost_of_capital | 6,850 (periodic:2) | 6,086 | -11.15% | PASS |
| K_deposit_early_cash | 6,862 (periodic:2) | 6,087 | -11.30% | PASS |
| L_high_holding_rate | 6,856 (periodic:2) | 6,180 | -9.85% | PASS |
| M_order_calendar_wednesday | 6,256 (incumbent) | 6,188 | -1.08% | PASS |
| N_long_lead_21_days | 5,937 (incumbent) | 5,982 | +0.76% | FAIL: categories |
| O_low_opening_stock | 6,399 (reorder_point) | 6,464 | +1.01% | PASS |
| P_high_opening_stock | 5,786 (reorder_point) | 5,924 | +2.38% | FAIL: zaad_not_worse |
| Q_volatile_demand_high_target | 5,971 (incumbent) | 5,962 | -0.15% | PASS |
| R_asymmetric_prices_mov | 63,448 (incumbent) | 63,448 | +0.00% | FAIL: categories |
| S_cash_constrained | 6,234 (economic_lot) | 6,183 | -0.83% | PASS |
| T_combined_realistic | 17,593 (economic_lot) | 14,918 | -15.21% | PASS |

Product defaults (iid worlds, no tie-break, incumbent gate, guard on lean reviews, materiality
gate), `P1_RESULT_TABLE_none_product_defaults.md`: **17 / 20**.

| fixture | best baseline | ZAAD P1 | delta | checks |
|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 (incumbent) | 5,829 | +0.09% | PASS |
| B_fixed_order_cost_replace_sold | 6,995 (economic_lot) | 6,341 | -9.35% | PASS |
| C_moq_four_weeks | 5,898 (reorder_point) | 5,914 | +0.27% | PASS |
| D_case_multiple | 5,807 (incumbent) | 5,773 | -0.58% | PASS |
| E_pallet_multiple | 6,239 (incumbent) | 6,239 | -0.00% | PASS |
| F_mov_two_skus | 11,766 (periodic:2) | 11,746 | -0.17% | PASS |
| G_freight_tiers | 16,720 (economic_lot) | 15,346 | -8.21% | PASS |
| H_per_pallet_freight | 6,826 (periodic:2) | 6,551 | -4.04% | PASS |
| I_max_pallets_ftl_cap | 9,814 (economic_lot) | 9,866 | +0.53% | PASS |
| J_net60_cost_of_capital | 6,850 (periodic:2) | 6,093 | -11.06% | PASS |
| K_deposit_early_cash | 6,862 (periodic:2) | 6,093 | -11.20% | PASS |
| L_high_holding_rate | 6,856 (periodic:2) | 6,221 | -9.26% | PASS |
| M_order_calendar_wednesday | 6,256 (incumbent) | 6,209 | -0.76% | PASS |
| N_long_lead_21_days | 5,937 (incumbent) | 5,940 | +0.05% | FAIL: categories |
| O_low_opening_stock | 6,399 (reorder_point) | 6,448 | +0.77% | PASS |
| P_high_opening_stock | 5,786 (reorder_point) | 5,904 | +2.04% | FAIL: zaad_not_worse |
| Q_volatile_demand_high_target | 5,971 (incumbent) | 5,971 | +0.01% | PASS |
| R_asymmetric_prices_mov | 63,448 (incumbent) | 63,425 | -0.04% | FAIL: categories |
| S_cash_constrained | 6,234 (economic_lot) | 6,250 | +0.25% | PASS |
| T_combined_realistic | 17,593 (economic_lot) | 15,300 | -13.04% | PASS |

Interpretation: C, O, I pass under product defaults; P is outside the gate by 0.04 points, an
evaluation-window and sampling case, not a policy failure (service .977 above the .95 target, no
hidden buffer); C under the LHS sampler is the MOQ lot-timing artefact of D5 on a different
sample; N and R are the attribution expectations proven invalid (C7), unchanged by any sampler.

## E8. N / R, attribution, starvation, runtime, tests, invariants

N and R: unchanged; both proven invalid by the fixtures' arithmetic (C7); the new sampler does not
alter that. Attribution: every order partitions exactly on every gated cell of both records
(residual zero); cell 90's largest unexplained amount under ARM 2 is 23 units in one recovery-mode
order. Required starvation: zero on cell 90 under all three arms and on all six cells under product
defaults. Runtime, declared settings: p50 0.10 s, p95 1.48 s, max 12.5 s per
review (product defaults p50 0.11 s, p95 1.46 s); the sampler adds no worlds and no
measurable cost. Tests: 1438 passed, 2 skipped (three LHS tests replace the fixed-tail tests; the
diagnostic switches and their tests are gone). Invariants: 60 / 60.

## E9. Defaulting scope

Outcome 4 of the brief: not safe as a closure default. `stratified_scenarios` stays opt-in with
the LHS construction (the fixed-tail construction is removed); the P1 fixtures keep declaring it.
The materiality gate stays default, smoothing conditional, tie-break opt-in, service gate on the
incumbent basis.

## E10. Exact reason P1 remains open

Freeze gate items 1 (C/O/P/I) and 3/10 by consequence. Under product defaults P fails by 0.04
points; under the declared LHS setting C and P fail. The only representation that met C/O/P/I was
the weighted fixed-tail world, which the cell-90 evidence rejects. With three equal-weight worlds
the tail above the target can appear in at most about 15% of periods, so the remaining gap on P
is not reachable by an unbiased equal-weight sampler at this world count; it would need either a
deliberately weighted tail (rejected), an analytic expected-shortage term in the objective (a
different design, not built), or a cost-of-capital-free fixture economics that makes P's protection
worth more than the cost band tolerates (a fixture change, refused).


# FINAL ECONOMIC CLOSURE (2026-09-08, fifth pass on this close-out; from 0e47afd)

## F1. Lock and reproduction (sections A-B)

Started from 0e47afd: clean tree, no background jobs, fixture definitions, seeds, window, 2% gate,
baselines unchanged; P0 and validation evidence show no diff against 2e30721. Fixture P at product
defaults, full precision: ZAAD 5,904.475730 against reorder point 5,786.383280, absolute
+118.092450, +2.040868%. Reproduction (three repeats per seed, product defaults):

| seed | ZAAD | reorder point | gap | bit-identical over 3 repeats | first diverging period-0 order |
|---|---|---|---|---|---|
| 41001 | 5621.044561 | 5562.732003 | +1.0483% | True | review 3 |
| 41002 | 6019.423974 | 5895.040914 | +2.1100% | True | review 5 |
| 41003 | 6072.958654 | 5901.376923 | +2.9075% | True | review 4 |

The result is deterministic (case A of section B): every solve reports OPTIMAL with gap 0 in
under 0.03 s, so neither solver tolerance nor time limits nor ranking noise is involved.

## F2. First divergence and mechanism (sections C, E)

Reviews 0-2 (CAPITAL_OPTIMIZATION, 600 -> 300 on hand) are identical: both buy nothing. From the
first NO_ACTION review with the stock run down (seed 41001 review 3, 41002 review 5, 41003 review
4) the screen builds only the deterministic mean-world candidate (plus the ever-present incumbent
and base-stock proxy). That candidate orders exactly the fitted mean each period with no
protection; the reorder-point rule orders the mean plus its z-protection (about 10 units). With
demand sd 6 the truth exceeds the mean in roughly half the weeks, and every such week is a
shortage for ZAAD: seed 41001 review 8, 89 on hand, order 100.1, truth 98.2, 9.2 unmet; seed
41003 reviews 5, 8, 9, 10 unmet 6.1 / 11.1 / 9.6 / 5.0 against the baseline's 0 / 0 / 7.5 / 0.

Selector internals at seed 41001 review 8 (state NO_ACTION, lean, worlds equal-weighted iid):

| candidate | period-0 order | weighted service | per world | cost on the 3 worlds | shortage exposure | burden | feasible |
|---|---|---|---|---|---|---|---|
| incumbent (replace sold) | 98.1 | .9695 | .959 / .984 / .966 | 2,170.66 | 148.0 | 9.7 | yes |
| base stock proxy | 124.3 | .9870 | .979 / .985 / .997 | 2,137.20 | 63.4 | 77.6 | yes |
| deterministic | 100.1 | .9783 | .974 / .985 / .976 | **2,041.96** | 105.3 | 18.6 | yes |

The deterministic plan is the cheapest on the three sampled worlds, inside the band, the leanest,
and the guard cannot exclude it because it is itself the exposure floor: chosen, accepted, and 9.2
units short that week in truth. Why it is cheapest on the sample and worst in expectation is
section F4.

## F3. Cost reconciliation to the cent (section D; means of three seeds, ZAAD minus baseline)

| component | ZAAD | baseline | delta |
|---|---|---|---|
| purchase (procurement) | 3,005.81 | 3,123.45 | -117.64 |
| carrying (holding) | 23.12 | 22.83 | +0.29 |
| financing / expedite / freight / fixed order / receiving / pallet / MOQ | 0 | 0 | 0 |
| shortage: lost sales | 247.45 | 79.48 | +167.96 |
| shortage: SLA | 61.86 | 19.87 | +41.99 |
| terminal / salvage credit (closing assets) | -433.76 | -459.26 | +25.49 |
| opening assets | 3,000.00 | 3,000.00 | 0 |
| **total** | **5,904.48** | **5,786.38** | **+118.09** |

Residual against the settlement's economic cost: 0.000000 on both. The +2.04% is shortage:
$209.95 more lost sales and SLA, bought with $117.64 less purchasing and $25.49 less residual
credit. At the declared economics a lost unit costs $7.50 net and a carried unit $0.014 a period.

## F4. Why the deterministic candidate wins (section E) and what the counterfactuals show (section F)

Construction: the deterministic candidate is `solve` on the single mean-demand world with the
service floor; demand in period t is the fitted mean; its objective prices unmet units at the
declared selling price plus SLA, but on the mean path (mean - available)^+ is zero as soon as the
plan covers the mean, so the objective sees no shortage at all and no reason to hold a unit above
the mean. Uncertainty enters candidate generation nowhere for this candidate, enters screening and
selection only through the three sampled worlds, and enters settlement fully. The sampled
evaluation is unbiased but so coarse that a plan with no protection often shows little shortage on
the draw and wins the band as the leanest.

Counterfactual arms (fixture P, three seeds, product defaults; `closure/p_counterfactuals.json`):

| arm | cost | vs baseline | service | unmet |
|---|---|---|---|---|
| baseline reorder_point (through ZAAD settlement, F8) | 5,786.38 | +0.000% | 0.9929 | 7.9 |
| F0 product defaults | 5,904.48 | +2.041% | 0.9777 | 24.7 |
| F1 deterministic candidate not built | 5,799.82 | +0.232% | 0.9908 | 10.3 |
| F2 deterministic built and evaluated but cannot win | 5,799.82 | +0.232% | 0.9908 | 10.3 |
| F7 stochastic candidate forced (deterministic, base stock, incumbent unselectable) | 5,753.09 | -0.575% | 0.9967 | 3.7 |
| F6 incumbent action forced (replace_sold rule) | 6,282.33 | +8.571% | 1.0000 | 0.0 |
| F5 product defaults, residual at full value | 5,707.66 | -1.361% | - | - |
| F5 baseline, residual at full value | 5,671.57 | -1.984% | - | - |

Same physical plans at seed 41001 review 8 evaluated on the 3 selection worlds and on 200 iid worlds:

| plan | period-0 order | cost on 3 worlds | shortage | cost on 200 worlds | shortage |
|---|---|---|---|---|---|
| deterministic candidate | 100.1 | **2,037.84** (cheapest) | 105.3 | **2,116.37** (dearest) | 190.1 |
| reorder-point action | 121.6 | 2,033.23 | 63.4 | 2,089.60 | 115.0 |
| deterministic + 10 units at t=0 | 110.1 | 2,020.21 | 63.4 | 2,086.92 | 130.5 |
| deterministic + 17 units at t=0 | 117.1 | 2,027.89 | 63.4 | 2,086.17 | 117.9 |

Under the fitted mixture at that review E[(D - a)^+] at a = mean is 2.606 units per period ($32.6
at the $12.50 penalty), 0.704 at mean + 5, 0.002 at mean + 10. The mechanism is candidate
valuation: the mean-world objective omits the expected shortage of the fitted distribution, and
the three-world evaluation cannot correct it. Not terminal value (F5 moves both policies alike),
not the incumbent (F6 +8.6%), not lot timing or cadence (no lot rules on P), not the gates (F1/F2
pass with the candidate merely unable to win). The analytic expected-shortage hypothesis is
therefore justified (section G).

## F5. The mechanism implemented (sections H-J)

`zaad/full/shortage.py` and `model.solve(expected_shortage=fits)`, used by the planner for the
deterministic candidate only. For each service and period, the predictive distribution is the one
ZAAD samples from: zero with the fitted zero probability, otherwise a historical size scaled to the
fitted mean, widened by the calibration ratio and capped at the outlier bound exactly as
`worlds.draw` does, times any period event multiplier. That distribution is discrete, so its loss
function L(a) = E[(D - a)^+] is piecewise linear with breakpoints at the atoms and is represented
exactly by one tangent cut per distinct atom: es_t >= L(a_k) - P(D > a_k) (a_t - a_k), plus
es_t >= the mean world's own unmet. Availability a_t is what the service served plus what its
SKU still holds at the location at the end of the period. The objective charges the declared
penalty (selling price + SLA per unit, the same coefficient the model already charges on unmet)
on es_t - unmet_t, so only the part of the expected shortage the mean path cannot see is added.
No coefficient was introduced; the level uncertainty of the fit and firm order lines are not folded
into the atoms (stated omission, slightly understates the tail). Exactness of the envelope, the
hand-calculable cases and monotonicity are unit-tested (`tests/unit/test_zaad_shortage.py`).

Scope (section I): design A, the deterministic candidate's planning objective. Stochastic and CVaR
candidates already price shortage through their sampled worlds and are untouched (no double
count). The term is a planning surrogate: it enters neither the settlement ledger nor the
candidate's projected cost, so realised economics and customer savings are unchanged
(`test_surrogate_never_enters_projected_cost_or_ledger`, and the model-settlement reconciliation
test is unchanged). Hard service floors remain constraints; the surrogate is a cost; the two
interact as constraint and objective, with no unit counted twice.

Smoke at seed 41001 review 8: the deterministic candidate orders 109.4 instead of 99.1; its
200-world cost falls from 2,056.2 to 2,034.7 and its shortage from 88.2 to 43.0; surrogate 2.28
expected units, $28.45, in the objective only.

Second, narrow correction exposed by the first (section L of the brief): the materiality gate's
inventory axis divided the inventory change by the incumbent's carried value, so on fixture A's
lean incumbent (14 units) a one-unit difference read as "-7%" and ZAAD intervened on 28 of 33
reviews for a +0.2% cost effect. The axis is now measured against the larger of the incumbent's
carried value and one period of demand at asset value; fixture A then abstains on every review
(NO MATERIAL IMPROVEMENT AVAILABLE). No fixture-specific logic; the thresholds are unchanged.

## F6. Adversarial tests (section N; `tests/unit/test_zaad_shortage.py`)

Lower shortage economics buy no more protection and protection is monotone in the declared
penalty; near-zero variance collapses to the mean-world plan; sufficient inventory buys nothing
and reports zero expected shortage; a $1.15 per unit-period holding cost against a $5 miss stays
lean while $0.014 against $12.50 protects; the surrogate never reaches the ledger or projected
cost; MOQ keeps orders on the 400 lot; inbound stock counts as availability and forestalls a
purchase; a Monday-only order calendar and a freight tariff are respected; an already-optimal
incumbent yields NO MATERIAL IMPROVEMENT AVAILABLE. 17 tests, all passing.

## F7. P0 six-cell regression (section O; frozen record -> arm; `closure/p0_arm_*.json`)

**surrogate in every state + materiality inventory base = max(carried, one period of demand value)**

| cell | service | p10 | breaches | unmet | worst | inventory | cost | starved | joint req/built/chosen | lat p95 / max s | abstentions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 0.980 -> 0.980 | 0.962 -> 0.962 | 1 -> 1 | 5.0 -> 5.0 | 4.2 -> 4.2 | 46.1 -> 46.2 | 1678 -> 1683 | 0 | 0/1/0 -> 0/1/0 | 2 / 2 | 0 |
| 16 | 0.972 -> 0.972 | 1.000 -> 1.000 | 1 -> 1 | 7.0 -> 7.0 | 7.0 -> 7.0 | 134.5 -> 133.1 | 1515 -> 1514 | 0 | 0/2/0 -> 0/2/0 | 1 / 4 | 0 |
| 20 | 0.894 -> 0.916 | 0.233 -> 0.000 | 3 -> 3 | 40.9 -> 32.3 | 14.0 -> 17.0 | 183.7 -> 170.2 | 2502 -> 2458 | 0 | 0/3/2 -> 0/2/1 | 29 / 59 | 1 |
| 21 | 0.760 -> 0.746 | 0.000 -> 0.000 | 5 -> 6 | 93.0 -> 98.3 | 27.0 -> 27.0 | 130.5 -> 159.9 | 3257 -> 3590 | 0 | 7/10/5 -> 8/12/5 | 29 / 59 | 1 |
| 90 | 0.863 -> 0.866 | 0.220 -> 0.220 | 4 -> 4 | 70.1 -> 68.6 | 22.0 -> 22.0 | 94.4 -> 113.1 | 3315 -> 3341 | 0 | 1/3/1 -> 0/5/3 | 88 / 114 | 0 |
| 108 | 0.879 -> 0.882 | 0.225 -> 0.000 | 4 -> 6 | 69.8 -> 67.8 | 22.0 -> 22.0 | 138.6 -> 269.6 | 3723 -> 3744 | 0 | 0/5/1 -> 0/11/1 | 133 / 153 | 2 |

**surrogate on lean reviews only + the same materiality base**

| cell | service | p10 | breaches | unmet | worst | inventory | cost | starved | joint req/built/chosen | lat p95 / max s | abstentions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 0.980 -> 0.980 | 0.962 -> 0.962 | 1 -> 1 | 5.0 -> 5.0 | 4.2 -> 4.2 | 46.1 -> 46.1 | 1678 -> 1678 | 0 | 0/1/0 -> 0/1/0 | 1 / 2 | 0 |
| 16 | 0.972 -> 0.972 | 1.000 -> 1.000 | 1 -> 1 | 7.0 -> 7.0 | 7.0 -> 7.0 | 134.5 -> 134.5 | 1515 -> 1515 | 0 | 0/2/0 -> 0/2/0 | 1 / 4 | 0 |
| 20 | 0.894 -> 0.883 | 0.233 -> 0.000 | 3 -> 6 | 40.9 -> 45.2 | 14.0 -> 17.0 | 183.7 -> 143.8 | 2502 -> 2512 | 0 | 0/3/2 -> 0/3/2 | 28 / 58 | 1 |
| 21 | 0.760 -> 0.746 | 0.000 -> 0.000 | 5 -> 6 | 93.0 -> 98.3 | 27.0 -> 27.0 | 130.5 -> 145.3 | 3257 -> 3482 | 0 | 7/10/5 -> 9/13/5 | 28 / 57 | 1 |
| 90 | 0.863 -> 0.865 | 0.220 -> 0.220 | 4 -> 4 | 70.1 -> 69.1 | 22.0 -> 22.0 | 94.4 -> 129.5 | 3315 -> 3339 | 0 | 1/3/1 -> 0/5/2 | 88 / 114 | 0 |
| 108 | 0.879 -> 0.882 | 0.225 -> 0.000 | 4 -> 6 | 69.8 -> 67.8 | 22.0 -> 22.0 | 138.6 -> 140.9 | 3723 -> 3673 | 0 | 0/5/1 -> 0/5/0 | 133 / 153 | 1 |

**materiality base alone (surrogate off)**

| cell | service | p10 | breaches | unmet | worst | inventory | cost | starved | joint req/built/chosen | lat p95 / max s | abstentions |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | 0.980 -> 0.980 | 0.962 -> 0.962 | 1 -> 1 | 5.0 -> 5.0 | 4.2 -> 4.2 | 46.1 -> 46.1 | 1678 -> 1678 | 0 | 0/1/0 -> 0/1/0 | 1 / 2 | 0 |
| 16 | 0.972 -> 0.972 | 1.000 -> 1.000 | 1 -> 1 | 7.0 -> 7.0 | 7.0 -> 7.0 | 134.5 -> 134.5 | 1515 -> 1515 | 0 | 0/2/0 -> 0/2/0 | 1 / 4 | 0 |
| 20 | 0.894 -> 0.884 | 0.233 -> 0.000 | 3 -> 6 | 40.9 -> 44.9 | 14.0 -> 17.0 | 183.7 -> 144.0 | 2502 -> 2518 | 0 | 0/3/2 -> 0/3/2 | 28 / 57 | 1 |
| 21 | 0.760 -> 0.746 | 0.000 -> 0.000 | 5 -> 6 | 93.0 -> 98.3 | 27.0 -> 27.0 | 130.5 -> 145.3 | 3257 -> 3483 | 0 | 7/10/5 -> 9/13/5 | 28 / 57 | 1 |
| 90 | 0.863 -> 0.863 | 0.220 -> 0.220 | 4 -> 4 | 70.1 -> 70.1 | 22.0 -> 22.0 | 94.4 -> 95.8 | 3315 -> 3317 | 0 | 1/3/1 -> 1/3/1 | 78 / 114 | 0 |
| 108 | 0.879 -> 0.884 | 0.225 -> 0.241 | 4 -> 5 | 69.8 -> 66.9 | 22.0 -> 22.0 | 138.6 -> 142.4 | 3723 -> 3665 | 0 | 0/5/1 -> 0/5/0 | 132 / 153 | 0 |

Reading. Required starvation is zero in every arm and cell 21's recovery behaviour (joint
recovery required and chosen) is intact throughout, but the six-cell check is not safe in any of
them. With the surrogate in every state cell 21 loses 1.4 points of service (5 -> 6 breaches,
cost +10%) and cell 108 doubles its inventory (139 -> 270) with two more breaches. Lean-only
scoping removes the 108 inventory effect but cell 20 goes from 3 to 6 breaches, cell 21 keeps its
loss and cell 90 rises above its recorded band (94-124) to 130. The materiality-base change alone
reproduces the 20 and 21 movement (one abstention each, in lean reviews, costing service later)
while 15, 16, 90 and 108 stay on the record, so that change is reverted. The surrogate is then
the only new mechanism, and on cells 20 and 21 its lean-review protection changes the path into
the disruption reviews that follow, where P0's own rules take over from a different state.
Product defaults are therefore restored exactly to the state at 0e47afd (surrogate off), whose
six-cell record (arm `neither`, D4) reproduces P0 on 15, 16, 20 and 90 and sits inside the bands
on 21 and 108.

## F8. Defaults after this pass

| field | default | fixtures declare | reason |
|---|---|---|---|
| `analytic_shortage` (new) | False | True | corrects a proven valuation defect (F4, F5) but is not P0-safe (F7) |
| materiality thresholds | .01 / .05 / .005, inventory axis against the incumbent's carried value | same | the period-demand base fired on P0 cells 20 and 21 (F7); the known consequence is that a lean incumbent carrying a few units reads a one-unit change as material (fixture A intervenes 28 of 33 reviews when the surrogate is on) |
| `stratified_scenarios` | False (per-period LHS when on) | True | E9 |
| `timing_tiebreak` | 0 | 1e-4 | cell 108 starvation (D4) |
| `service_gate_basis` | incumbent | incumbent | C6 |
| smoothing | .02, off with explicit order economics | 0 | C6 |

## F9. Full A-T (section P), attribution, runtime, tests, verdict

Product defaults (surrogate off; identical behaviour to 0e47afd), `P1_RESULT_TABLE_none_product_defaults.md`: **17 / 20**.

| fixture | best baseline | ZAAD P1 | delta | checks |
|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 (incumbent) | 5,829 | +0.09% | PASS |
| B_fixed_order_cost_replace_sold | 6,995 (economic_lot) | 6,341 | -9.35% | PASS |
| C_moq_four_weeks | 5,898 (reorder_point) | 5,914 | +0.27% | PASS |
| D_case_multiple | 5,807 (incumbent) | 5,773 | -0.58% | PASS |
| E_pallet_multiple | 6,239 (incumbent) | 6,239 | -0.00% | PASS |
| F_mov_two_skus | 11,766 (periodic:2) | 11,746 | -0.17% | PASS |
| G_freight_tiers | 16,720 (economic_lot) | 15,346 | -8.21% | PASS |
| H_per_pallet_freight | 6,826 (periodic:2) | 6,551 | -4.04% | PASS |
| I_max_pallets_ftl_cap | 9,814 (economic_lot) | 9,866 | +0.53% | PASS |
| J_net60_cost_of_capital | 6,850 (periodic:2) | 6,093 | -11.06% | PASS |
| K_deposit_early_cash | 6,862 (periodic:2) | 6,093 | -11.20% | PASS |
| L_high_holding_rate | 6,856 (periodic:2) | 6,221 | -9.26% | PASS |
| M_order_calendar_wednesday | 6,256 (incumbent) | 6,209 | -0.76% | PASS |
| N_long_lead_21_days | 5,937 (incumbent) | 5,940 | +0.05% | FAIL: categories |
| O_low_opening_stock | 6,399 (reorder_point) | 6,448 | +0.77% | PASS |
| P_high_opening_stock | 5,786 (reorder_point) | 5,904 | +2.04% | FAIL: zaad_not_worse |
| Q_volatile_demand_high_target | 5,971 (incumbent) | 5,971 | +0.01% | PASS |
| R_asymmetric_prices_mov | 63,448 (incumbent) | 63,425 | -0.04% | FAIL: categories |
| S_cash_constrained | 6,234 (economic_lot) | 6,250 | +0.25% | PASS |
| T_combined_realistic | 17,593 (economic_lot) | 15,300 | -13.04% | PASS |

Declared fixture settings (surrogate on, per-period LHS on, tie-break 1e-4), `P1_RESULT_TABLE_none.md`: **16 / 20**.

| fixture | best baseline | ZAAD P1 | delta | checks |
|---|---|---|---|---|
| A_no_terms_good_incumbent | 5,824 (incumbent) | 5,838 | +0.25% | FAIL: action |
| B_fixed_order_cost_replace_sold | 6,995 (economic_lot) | 6,265 | -10.43% | PASS |
| C_moq_four_weeks | 5,898 (reorder_point) | 6,082 | +3.13% | FAIL: zaad_not_worse |
| D_case_multiple | 5,807 (incumbent) | 5,773 | -0.59% | PASS |
| E_pallet_multiple | 6,239 (incumbent) | 6,239 | +0.00% | PASS |
| F_mov_two_skus | 11,766 (periodic:2) | 11,860 | +0.79% | PASS |
| G_freight_tiers | 16,720 (economic_lot) | 15,409 | -7.84% | PASS |
| H_per_pallet_freight | 6,826 (periodic:2) | 6,475 | -5.14% | PASS |
| I_max_pallets_ftl_cap | 9,814 (economic_lot) | 9,856 | +0.43% | PASS |
| J_net60_cost_of_capital | 6,850 (periodic:2) | 6,086 | -11.15% | PASS |
| K_deposit_early_cash | 6,862 (periodic:2) | 6,087 | -11.30% | PASS |
| L_high_holding_rate | 6,856 (periodic:2) | 6,180 | -9.85% | PASS |
| M_order_calendar_wednesday | 6,256 (incumbent) | 6,152 | -1.66% | PASS |
| N_long_lead_21_days | 5,937 (incumbent) | 5,899 | -0.64% | FAIL: categories |
| O_low_opening_stock | 6,399 (reorder_point) | 6,393 | -0.09% | PASS |
| P_high_opening_stock | 5,786 (reorder_point) | 5,790 | +0.07% | PASS |
| Q_volatile_demand_high_target | 5,971 (incumbent) | 5,962 | -0.15% | PASS |
| R_asymmetric_prices_mov | 63,448 (incumbent) | 63,573 | +0.20% | FAIL: categories |
| S_cash_constrained | 6,234 (economic_lot) | 6,173 | -0.98% | PASS |
| T_combined_realistic | 17,593 (economic_lot) | 14,945 | -15.05% | PASS |

Interpretation, per fixture: P under product defaults is the genuine remaining failure (+2.04%,
four hundredths outside the gate) and the mechanism is proven and corrected by the surrogate
(P +0.07% with it on); C with the surrogate on is the finite-horizon MOQ artefact (D5) amplified
by lot-sized protection (+2.59% at product defaults with the surrogate, +0.75% at full terminal
value) plus one P0 stress-gate retention under the nil stress; A with the surrogate on is the
materiality inventory-axis scale defect (interventions worth +0.25%); N and R are the attribution
expectations proven invalid (C7); every other fixture passes under both records.

Attribution: exact partition on every gated cell of both records (residual zero); invariants 60 /
60; no unexplained inventory jump (P's protection is SERVICE_PROTECTION, the C order that carries
OTHER_EXPLAINED units is the 678-unit horizon lot already documented). Runtime, product defaults:
p50 0.10 s, p95 1.41 s, max 16.6 s per review; with the surrogate p50 0.11 s, p95 1.95 s,
max 19.8 s: the cut envelope adds one variable and one row per atom per period to a
single-world solve and no measurable time. Tests: 1455 passed, 2 skipped (17 shortage tests, the
adversarial set among them; nothing skipped that was not skipped at 0e47afd). Invariants: 60 / 60.
P0 six-cell under product defaults: the frozen record (D4, arm `neither`).

**Verdict: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.**

Exact reason. Freeze-gate item 1 (P <= 2%) fails under product defaults by 0.04 points, and the
mechanism that corrects it, the analytic expected-shortage surrogate, fails item 7 (P0 six-cell
safe) in every scope tried and, on the fixtures, moves C outside the gate through the documented
window artefact. The surrogate is a derived, exact, objective-only correction of a real valuation
defect (the mean-world candidate prices no expected shortage and wins a three-world comparison it
loses in expectation), and it ships as an opt-in request setting with its tests; it does not ship
as a default. Nothing was tuned to P, no tolerance, fixture, expectation, seed or baseline was
changed, and the materiality-base change that would have made fixture A abstain was reverted
because it fired on P0 cells 20 and 21.

Best next intervention (not executed): understand why lean-review protection on cells 20 and 21
changes the path into their disruption reviews (a state-sequence question in P0's screen, not an
economics question), and decide the benchmark's terminal valuation, which is what holds C.


# CANDIDATE-COMPARABILITY PASS (2026-09-09, sixth pass on this close-out; from dca4820)

**Verdict: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.** The common ex-ante valuation was built,
validated and applied to every generated candidate at every review of the fixtures with all plans
held fixed. On fixture P it agrees with the selector at every decisive review: the deterministic
plan is the best plan the screen generated there. Selection is not P's defect; the candidate set
is. No selector change was made.

## G1. Lock

Started from dca4820: clean tree, no jobs; P +2.040868% at product defaults; six P0 cells
reproduced (D4, arm `neither`); `analytic_shortage` default off; materiality base reverted;
fixtures, tolerance, seeds unchanged; Validation7/8, holdout4 uninspected.

## G2. Common valuation architecture (`zaad/full/valuation.py`, read-only)

`common_candidate_value(req, solution, fits)` values a fixed plan (its purchase, transfer and
amendment controls) under one lens shared by every candidate: the fitted predictive demand
distribution of every service (the zero probability, bootstrap atoms, calibration widening,
outlier cap and event multipliers the sampler uses, from `shortage.demand_atoms`), the review's
mean supply path (declared lead and mean fill), the declared shortage, SLA, carrying, purchase,
freight, receiving, financing and terminal economics, over the plan's own horizon. The
demand-independent components come from the mean-path settlement of the plan; the
demand-dependent ones (carrying, shortage, terminal credit on stock still on hand) are replaced by
exact expectations under the mixture obtained by propagating the on-hand distribution period by
period on a unit grid, I_t = max(0, I_t-1 + arrivals_t - D_t), lost sales, the demand of every
service at a location convolved atom by atom. The grid is the only approximation (error bounded by
one unit per period). It mutates nothing: not quantities, timings, feasibility, the solver, the
settlement or the ledger (`test_valuation_mutates_nothing`). Candidate-generation objectives,
this comparison value and the realised ledger are three separate things and stay separate.

Validation. Hand-calculable propagation; deterministic demand reproduces the mean-path settlement
to the grid; against a 300-world sampled expectation the value agrees within 1% and ranks
identically; expected shortage falls with added units and is zero with ample stock; components
reconcile to the total (`tests/unit/test_zaad_valuation.py`, 6 tests). At P seed 41001 review 8
against 400 worlds, component by component: deterministic 2,109 vs 2,118; base stock 2,189 vs
2,196; deterministic + 10 units 2,081 vs 2,089; reorder-point action 2,086 vs 2,092. Runtime:
6.0 ms per candidate valuation at p50, 14.7 ms p95, 20.1 ms max (414 valuations).

## G3. P: every generated candidate at every decisive review (`closure/common_valuation_diag.json`)

| seed | review | state | candidates: period-0 order, sampled 3-world cost, common value, E[shortage units] | selector chose | common best | agreement |
|---|---|---|---|---|---|---|


At every NO_ACTION review, on all three seeds, the common valuation's best candidate is the one
the selector chose. The base-stock proxy over-buys inside the shrinking horizon (at review 8 it
orders 124 then keeps ordering, 115 units more than the deterministic plan over four periods, so
its expected shortage saving of $66 costs $146 net of the terminal credit); the incumbent is
worst. The plans that beat the deterministic plan in expectation (about +10 units at period 0:
common 2,081, 400 worlds 2,089) are not in the candidate set. Disagreements occur only in the
three stock-rundown reviews (CAPITAL_OPTIMIZATION, every candidate orders zero at period 0, gaps
$5-97 between zero-order plans) and change no order.

**Answer to the Stage 3 question: no. Common valuation does not reverse P's ranking, because at
the decisive reviews there is no better generated plan to rank first.** The F1/F2 counterfactuals
(+0.23%) improved P by excluding the deterministic plan, which made the over-buying base-stock
proxy win and carry protection forward across reviews; F7 (-0.58%) improved it by forcing the
stochastic class, which the NO_ACTION state does not request. Both change the candidate set, not
the comparison.

## G4. Cross-fixture disagreement table (seed 41001, 11 reviews each; `closure/common_valuation_diag_fixtures.json`)

Common valuation disagrees with the selector's sampled choice on 15 of 77 reviews across C, O, I, A, G, Q, T:

| fixture | review | state | selector chose (status) | common best | common gap $ | candidates (p0 units / common / sampled) |
|---|---|---|---|---|---|---|
| C | 1 | CAPITAL_OPTIMIZATION | stochastic_network (PENDING_REVIEW) | cvar_network | 6.2 | incumb:400/9836/9865 base_s:0/10272/10234 determ:0/5602/5663 stocha:0/5603/5591 cvar_n:0/5597/5594 protec:0/5603/5591 joint_:0/5597/5594 |
| O | 3 | NORMAL_REPLENISHMENT | base_stock (PENDING_REVIEW) | deterministic_network | 55.1 | incumb:0/5521/5416 base_s:108/4741/4653 determ:94/4686/4567 stocha:96/4700/4530 cvar_n:96/4700/4530 |
| O | 5 | NORMAL_REPLENISHMENT | stochastic_network (PENDING_REVIEW) | deterministic_network | 3.7 | incumb:0/4442/4421 base_s:105/3697/3677 determ:90/3637/3609 stocha:293/3641/3552 cvar_n:293/3641/3552 |
| I | 2 | CAPITAL_OPTIMIZATION | cvar_network (PENDING_REVIEW) | joint_recovery | 37.6 | incumb:0/11739/11656 base_s:0/12794/12717 determ:0/7341/7200 stocha:0/7343/7196 cvar_n:0/7349/7198 protec:0/7343/7196 cadenc:399/7376/7203 cadenc:156/7346/7210 joint_:0/7311/7225 |
| I | 3 | NO_ACTION | cadence_2_network (PENDING_REVIEW) | cadence_4_network | 37.3 | incumb:0/11283/11177 base_s:0/12337/12237 determ:0/6882/6733 cadenc:0/6903/6728 cadenc:428/6866/6754 |
| A | 2 | NO_ACTION | deterministic_network (RETAIN_INCUMBENT) | incumbent | 51.1 | incumb:95/5099/5023 base_s:97/5204/5135 determ:83/5150/5014 |
| A | 8 | NO_ACTION | deterministic_network (RETAIN_INCUMBENT) | incumbent | 25.4 | incumb:109/2017/1990 base_s:111/2125/2100 determ:97/2043/1983 |
| A | 9 | NO_ACTION | deterministic_network (RETAIN_INCUMBENT) | incumbent | 22.7 | incumb:101/1513/1477 base_s:103/1620/1588 determ:89/1535/1477 |
| G | 0 | NO_ACTION | cadence_4_network (PENDING_REVIEW) | cadence_2_network | 8.5 | incumb:198/23176/23135 base_s:127/23208/23170 determ:0/14706/14571 cadenc:2000/14649/14514 cadenc:2000/14657/14514 |
| Q | 0 | NORMAL_REPLENISHMENT | cvar_network (RETAIN_INCUMBENT) | incumbent | 186.2 | incumb:112/6049/6244 base_s:116/6150/6345 determ:42/6296/6661 stocha:33/6235/6115 cvar_n:33/6235/6115 |
| Q | 1 | NORMAL_REPLENISHMENT | stochastic_network (RETAIN_INCUMBENT) | cvar_network | 10.6 | incumb:96/5614/5760 base_s:100/5715/5859 determ:26/5851/5867 stocha:165/5686/5571 cvar_n:165/5675/5572 |
| Q | 2 | NO_ACTION | deterministic_network (RETAIN_INCUMBENT) | incumbent | 230.1 | incumb:74/5121/4873 base_s:76/5224/4984 determ:3/5351/4808 |
| Q | 8 | NO_ACTION | deterministic_network (RETAIN_INCUMBENT) | incumbent | 119.5 | incumb:126/1965/1895 base_s:130/2068/2000 determ:56/2085/1865 |
| T | 0 | NO_ACTION | cadence_2_network (PENDING_REVIEW) | cadence_4_network | 15.0 | incumb:312/26498/26444 base_s:0/25871/25760 determ:336/15250/15105 cadenc:336/15214/15065 cadenc:1776/15199/15154 |
| T | 1 | NO_ACTION | cadence_2_network (PENDING_REVIEW) | deterministic_network | 55.9 | incumb:312/24486/24547 base_s:0/23033/23091 determ:0/13145/13319 cadenc:1872/13201/13318 cadenc:1872/13201/13318 |

Reading. The disagreements are of three kinds. (i) Cadence or joint-recovery alternatives worth
$4-56 in expectation (C, I, G, T, O): immaterial and inside the existing band. (ii) Lean
deterministic plans that the sampled comparison rates cheapest and the common lens rates worse
than the incumbent (A reviews 2/8/9 by $23-51; Q reviews 2/8 by $120-230, where the deterministic
plan orders 3 and 56 units against an incumbent ordering 74 and 126): the F4 pattern, a lean plan
looking cheap on three worlds. In every one of those reviews the existing gates retained the
incumbent anyway (status RETAIN), so the sampled comparison's bias was caught downstream. (iii)
None on P's decisive reviews. So the sampled comparison does carry the bias the hypothesis
describes, it is real on A and Q, it is already contained by the gates there, and it is not what
decides P.

## G5. Selector defect, stated precisely

Of the possibilities listed: the candidate cost values do contain different risk representations
(a mean-world plan's cost on three sampled worlds is an unbiased but high-variance estimate of a
tail cost it never planned for), and the exposure floor is self-referential (the cheapest
candidate sets the floor, and on P the cheapest is the lean plan). Neither is what P turns on. P
turns on the candidate set: in the NO_ACTION state the screen requests only the deterministic
mean-world class, whose objective holds no protection; the only protected alternative is the
base-stock proxy, whose order-up-to rule over-buys inside the shrinking horizon; the stochastic
class, which sizes protection from the sampled spread and wins when forced (F7), is not
requested. That is candidate-set architecture, and the brief's failure branch names it.

## G6. The frozen P0 cells under the common lens (`closure/common_valuation_diag_p0.json`)

| cell | reviews | disagreements | material (> $10) | states | common best leaner than chosen | largest gap $ |
|---|---|---|---|---|---|---|
| 15 | 12 | 5 | 1 | ['PROTECT'] | 0 | 32 |
| 20 | 20 | 3 | 1 | ['PROTECT'] | 2 | 37 |
| 21 | 20 | 5 | 4 | ['PROTECT'] | 2 | 51 |
| 90 | 26 | 10 | 5 | ['NORMAL_REPLENISHMENT', 'PROTECT'] | 2 | 32 |
| 108 | 30 | 13 | 8 | ['NORMAL_REPLENISHMENT', 'PROTECT'] | 5 | 263 |

Reading. On the P0 cells the common valuation disagrees with the selector in 36 of 108 reviews,
almost all in PROTECT states, and in the material cases it prefers the leaner plan (cell 108
review 10: deterministic 25 units valued at 2,723 against the chosen protected plan at 2,986;
review 6: 2,891 against the incumbent's 3,003). That is not evidence against the selector. The
common lens values a plan on the review's mean supply path with the fitted demand mixture; it
carries no representation of the supply risk (late and short receipts, the declared stress) that
P0's protected, hedged, CVaR and joint-recovery candidates are built against, so in PROTECT and
recovery states it systematically under-values protection. A selector that ranked on it there
would strip the protection P0 validated, which is precisely the regression the analytic
surrogate produced on cells 20, 21, 90 and 108. Any common lens fit to be a selector standard in
those states would have to represent supply uncertainty as well as demand; this one does not,
and building that is beyond a comparability fix.

## G7. Conclusion of the pass (the brief's failure branch)

Why common valuation failed to close P: not because it is wrong (it is validated to within 1% of
a 400-world expectation and ranks identically), but because at P's decisive reviews the plan it
prefers is the plan the selector already chose. The candidate set at those reviews holds no plan
with modest protection: the NO_ACTION state requests only the mean-world class, and the only
protected alternative is the base-stock proxy, which over-buys inside the shrinking horizon. The
remaining conflict is **candidate-set architecture**, with a secondary **evaluation-architecture**
finding for other states (a single common lens needs supply uncertainty to be a fair standard in
PROTECT and recovery). Neither is a local patch. Consistent with the brief: no selector prototype
was built, no plan was changed, no default moved; `valuation.py` remains a validated diagnostic
instrument (6 tests, 6 ms per candidate) for the reassessment.

What the reassessment has to decide, from this evidence: (1) whether the NO_ACTION state should
request a protected class (the stochastic class wins when forced, F7 -0.58%, but that is a
screen change on the P0-frozen side and needs the six-cell check); (2) whether the mean-world
class should exist as an intervention candidate at all when the review is calm, since its
objective cannot hold protection; (3) what a common standard that includes supply risk would be.

**Final state.** Product defaults unchanged from dca4820 (P0 behaviour); `analytic_shortage`,
`stratified_scenarios`, `timing_tiebreak` opt-in; fixtures at product defaults 17 / 20 with P
+2.040868%, N and R proven-invalid expectations; unit suite 1461 passed, 2 skipped (6 valuation
tests added); invariants 60 / 60; P0 six-cell record unchanged (D4). Validation7, Validation8,
holdout4 uninspected; Network Twin, PR #38, PR #39, frontend, Vercel, production, other worktrees
untouched. P2 not started.

**Verdict: P1 CYCLE-STOCK ECONOMICS — REMAINS OPEN.**

---

# Pass H: candidate-set completeness -> escalation failure diagnostic (2026-09-09)

**Code status: an UNCOMMITTED experimental request mode (`no_action_escalation`, default off) sits on top
of `4f6aedc`. It is not an accepted product change. It failed the P0 six-cell freeze gate (cell 20) and
fixture C.** This section records the complete evidence and the architectural classification. No policy
was changed after the failure; no selector, materiality, sampler, stochastic-candidate or terminal
economics were modified; full A-T was not rerun; P2 not started.

## H1. Lock, request matrix, and what was built

Lock at `4f6aedc`, product defaults (`closure/lock_4f6aedc.json`): P +2.04% FAIL, C +0.27%, O +0.77%,
I +0.53%, A +0.09% (2 actions / 33), G -8.21%, Q +0.01%, T -13.04%. Six P0 cells reproduced by arm
`neither` (D4).

Candidate-request matrix (`zaad/full/screen.py`, unchanged):

| screen state | minimum safe (required) | optional |
|---|---|---|
| NO_ACTION | deterministic | - |
| NORMAL_REPLENISHMENT | deterministic, stochastic | cvar |
| CAPITAL_OPTIMIZATION | deterministic, stochastic, cvar | protected, joint_recovery |
| NETWORK_ALLOCATION | deterministic, stochastic, joint_recovery | cvar, protected, stress |
| PROTECT | deterministic, stochastic, protected | hedged, stress, cvar |
| RECOVER | deterministic, stochastic, cvar | joint_recovery, protected |
| ESCALATE_UNKNOWN | all seven | - |

Incumbent and projected base stock are always present without a solve; cadence classes are added when a
supplier carries order-level economics; joint recovery is escalated on demand when no candidate meets
every target. The stochastic class is absent at NO_ACTION because v8 (`7b4f508`) defined NO_ACTION as
"the incumbent is feasible, meets every target with headroom, no active driver, no material excess:
nothing expensive can improve it" and gave it one cheap deterministic solve as a check. That check is an
intervention candidate in its own right and, on P, wins the sampled comparison while carrying no
protection (pass G).

Read-only diagnostic (`scripts/p1_candidate_completeness_diag.py exclude`; 22 decisive NO_ACTION reviews
of P over three seeds; stochastic generated through the ordinary screen path and excluded from selection):
the existing stochastic candidate passes the service gate at all 22, is the cheapest sampled plan at all
22, and is cheaper under the common valuation at 15 / 22 (2 ties, 5 dearer). Under the current selector
it would have been chosen at 19 / 22 (band guard removes the deterministic whenever the stochastic has
lower exposure).

Experimental mode. `Request.no_action_escalation` (default False). In the planner, after the deterministic
solve at a NO_ACTION review: if the deterministic plan's executable period-0 order differs from the
incumbent's (numerical tolerance 1e-6, no economic threshold), `stochastic_network` is appended to the
required set and built by the same `solve(req, selection, service_floor=True, seed=incumbent)` call as
everywhere else; recorded in `orchestration.escalated`; at most one extra MILP; never outside NO_ACTION,
never when the screen already requests the class, no effect with adaptive escalation off. Bit-identity to
the screen-requested class: proven at all 32 escalated C and P reviews
(`candidate_completeness_escalate_CP.json`, `bit_identical_to_screen_requested` True) and by test.
Scope is a state plus a plan comparison; it reads no fixture, cell or seed.

Known reporting inconsistency in the experimental diff (not fixed, no code change permitted in this
pass): `orchestration.candidate_classes_requested` is copied before the escalation and so omits the
escalated class, while `classification`, `candidates_built` and `escalated` include it.

## H2. Targeted fixtures under the mode (`closure/esc_targeted.json`, product defaults + mode)

| fixture | arm A (product defaults) | arm B (mode) | service A / B | unmet A / B | inventory A / B | escalations (3 seeds) | MILPs B | wall A / B |
|---|---|---|---|---|---|---|---|---|
| P | +2.04% FAIL | **+0.29% PASS** | .978 / .990 | 24.7 / 10.7 | 146 / 179 | 22 | 163 | 6.5 / 7.3 s |
| C | +0.27% | **+3.61% FAIL** | 1.000 / 1.000 | 0 / 0 | 230 / 282 | 10 | 193 | 5.7 / 6.3 s |
| O | +0.77% | -0.21% | .921 / .924 | 87.0 / 83.5 | 41 / 56 | 17 | 140 | 4.6 / 4.8 s |
| I | +0.53% | +0.53% | 1.000 / 1.000 | 0 / 0 | 259 / 258 | 8 | 233 | 18.7 / 23.7 s |
| A | +0.09% (2 actions, abstains) | +0.43% (6 actions, 3 abstentions) | .991 / .989 | 9.8 / 12.7 | 15 / 15 | 32 | 133 | 2.1 / 3.8 s |
| G | -8.21% | -10.01% | 1.000 / 1.000 | .6 / .6 | 867 / 867 | 11 | 252 | 11.8 / 15.5 s |
| Q | +0.01% | +0.85% | .988 / .980 | 14.0 / 22.5 | 62 / 62 | 23 | 144 | 3.8 / 4.8 s |
| T | -13.04% | -11.47% | 1.000 / 1.000 | 0 / 0 | 916 / 806 | 10 | 255 | 15.1 / 21.0 s |

Per seed: P improves on all three (+1.05 -> +0.19, +2.11 -> -0.31, +2.91 -> +0.98). C is identical on
41001 and regresses on 41002 (+1.10 -> +5.37) and 41003 (0.00 -> +5.65). Q 41002 +0.01 -> +2.99
(service .968 -> .946). A 41003 +0.25 -> +1.17. T 41001 -14.0 -> -8.9 (inventory 919 -> 611).

## H3. P0 six-cell arm `escalation` (`closure/p0_arm_escalation.json`, alone; product defaults otherwise)

| cell | arm | service | p10 | breaches | unmet | worst | inventory | cost | starved | infeasible | joint chosen | NO_ACTION reviews | escalations | states |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15 | product defaults | .980 | .962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 0 | 4 | 0 | 0 | - | PROTECT 12 |
| 15 | escalation | .980 | .962 | 1 | 5.0 | 4.2 | 46.1 | 1678 | 0 | 4 | 0 | 0 | 0 | identical |
| 16 | product defaults | .972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 0 | 6 | 0 | 0 | - | PROTECT 12 |
| 16 | escalation | .972 | 1.000 | 1 | 7.0 | 7.0 | 134.5 | 1515 | 0 | 6 | 0 | 0 | 0 | identical |
| 20 | product defaults | .884 | .000 | 6 | 44.9 | 17.0 | 144.0 | 2518 | 0 | 10 | 2 | 4 | - | NO_ACTION 4, PROTECT 16 |
| 20 | escalation | **.837** | .218 | 5 | **63.2** | 21.1 | 182.7 | 2596 | 0 | 12 | 2 | 1 | **1 (r0)** | NO_ACTION 1, PROTECT 19 |
| 21 | product defaults | .746 | .000 | 6 | 98.3 | 27.0 | 145.3 | 3483 | 0 | 17 | 5 | 2 | - | NO_ACTION 2, PROTECT 17, NORMAL 1 |
| 21 | escalation | .770 | .000 | 5 | 89.0 | 27.0 | 145.8 | 3166 | 0 | 16 | 4 | 2 | 2 (r0, r19) | same |
| 90 | product defaults | .863 | .220 | 4 | 70.1 | 22.0 | 95.8 | 3317 | 0 | 6 | 1 | 4 | - | NO_ACTION 4, PROTECT 15, NORMAL 7 |
| 90 | escalation | .858 | .000 | 5 | 72.6 | 22.0 | 122.5 | 3328 | 0 | 5 | 0 | 4 | 4 (r0, r20, r24, r25) | NO_ACTION 4, PROTECT 18, NORMAL 4 |
| 108 | product defaults | .884 | .241 | 5 | 66.9 | 22.0 | 142.4 | 3665 | 0 | 5 | 0 | 3 | - | NO_ACTION 3, PROTECT 18, CAPITAL 3, NORMAL 6 |
| 108 | escalation | .882 | .000 | 6 | 67.8 | 22.0 | 139.8 | 3681 | 0 | 5 | 1 | 3 | 3 (r0, r28, r29) | same |

Hard gates: cell 20 "no worse" FAILS (service, unmet, worst, cost all worse); cell 21 recovery
improves; cell 90 no over-protection but one more breach and +28% inventory; cell 108 starvation 0 but
one more breach. Every cell that has a review-0 NO_ACTION escalates there.

Escalation events (traces `closure/cell{20,21,90,108}_trace_escalation.json`; the cell 21 trace replays
at 3186 against the arm's 3166 with identical selections on 20 / 20 reviews, a time-limit artefact; the
other three traces reproduce the arm exactly):

| cell | review | prior -> state -> next | on hand | protection (regime, activity, units) | flags | incumbent p0 | deterministic p0 | stochastic p0 | chosen -> final | executed (mode) | product-default outcome at the same review |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 20 | 0 | - -> NO_ACTION -> PROTECT | 40 | LEAN, 0, 4.5 | - | 5.9 | 11.3 | 15.5 | stochastic -> accepted | 15.5 | RETAIN incumbent (5.9) |
| 21 | 0 | - -> NO_ACTION -> PROTECT | 40 | LEAN, 0, 4.5 | - | 5.9 | 11.3 | 15.5 | stochastic -> accepted | 15.5 | RETAIN incumbent (5.9) |
| 21 | 19 | NORMAL -> NO_ACTION -> end | 30 | LEAN, 0, 251.9 | FALSE_PROTECTION_RISK | 28.7 | 0 | 0 | deterministic (same plan) | 0 | deterministic 0 (identical) |
| 90 | 0 | - -> NO_ACTION -> PROTECT | 40 | LEAN, 0, 4.5 | - | 5.9 | 11.3 | 13.5 | stochastic -> NO MATERIAL IMPROVEMENT (cost -0.83%, inventory -1.33%) -> RETAIN | **5.9** | deterministic accepted (11.3) |
| 90 | 20 | NORMAL -> NO_ACTION -> NORMAL | 58 | LEAN, 0, 50.0 | FALSE_PROTECTION_RISK | 0 | 11.2 (infeasible on worlds, svc .948) | 0 | stochastic -> accepted | 0 | RETAIN incumbent (0) |
| 90 | 24 | NORMAL -> NO_ACTION -> NO_ACTION | 35 | LEAN, 0, 47.4 | FALSE_PROTECTION_RISK | 13.5 | 1.2 (infeasible, svc .883) | 9.5 | stochastic -> accepted | 9.5 | RETAIN incumbent (13.5) |
| 90 | 25 | NO_ACTION -> NO_ACTION -> end | 19 | LEAN, 0, 49.7 | FALSE_PROTECTION_RISK | 32.0 | 0 | 0 | deterministic (same plan) | 0 | deterministic 0 (identical) |
| 108 | 0 | - -> NO_ACTION -> PROTECT | 40 | LEAN, 0, 4.5 | - | 5.9 | 11.3 | 13.4 | stochastic -> NO MATERIAL IMPROVEMENT (cost -0.83%, inventory +7.84%) -> RETAIN | **5.9** | deterministic accepted (11.3) |
| 108 | 28 | NORMAL -> NO_ACTION -> NO_ACTION | 49 | LEAN, 0, 50.4 | FALSE_PROTECTION_RISK | 1.7 | 0 | 0 | deterministic (same plan) | 0 | identical |
| 108 | 29 | NO_ACTION -> NO_ACTION -> end | 35 | LEAN, 0, 48.7 | FALSE_PROTECTION_RISK | 13.8 | 0 | 0 | deterministic (same plan) | 0 | identical |

Two distinct effects. (i) Cells 20 and 21: the escalated candidate is chosen and accepted; the review-0
order rises from the retained incumbent's 5.9 to 15.5. (ii) Cells 90 and 108: the escalated candidate is
the cheapest, the band guard drops the deterministic plan (exposure 35-73 against 0), the stochastic
plan then fails the materiality gate (cost -0.83% against the 1% threshold) and the review abstains; the
deterministic intervention that product defaults executed (11.3) is displaced and the review-0 order
*falls* to 5.9. The candidate never had to be selected to change the outcome. Downstream: cell 90 r1
unmet 0 -> 1.3, r2 13.1 -> 17.0; cell 108 r1 0 -> 1.2, r2 12.9 -> 17.0.

## H4. Cell 20 first divergence (`scripts/p1_cell90_diff.py p0_defaults escalation 20`)

Review 0, NO_ACTION, lean review, one SKU / one location, on hand 40, no pipeline, no active driver
(LEAN, activity 0, protection 4.5 units against lean 4.1), fitted demand about 20-21 per period, arrivals
1-3 periods, fills .95-.99 on the three selection worlds, target .95, declared stress `operator_adverse`
with credibility 0 at review 0, supply state `deterioration_recovery` (disruption from review 1).

| candidate | period-0 order | schedule (periods 0-7) | sampled cost | service stat | exposure | burden | common valuation | E[short] units | feasible |
|---|---|---|---|---|---|---|---|---|---|
| incumbent / base stock | 5.9 | 6, 21, 21, 21, 21, 21, 21, 21 | 2315 | .994 | 26.4 | 28 | 2302.2 | 2.6 | yes |
| deterministic (product default choice) | 11.3 | 11, 11, 21, 21, 21, 21, 21, 21 | 2303 | .985 | 66.7 | 25 | 2284.2 | 5.6 | yes |
| stochastic (escalated) | 15.5 | 16, 16, 16, 22, 22, 22, 22, 23 | 2277 | 1.000 | 0.0 | 42 | **2269.3** | 1.2 | yes |

Selector ranking (mode): cheapest = stochastic; band = {stochastic} (deterministic and incumbent fail the
exposure guard); chosen stochastic; confirmation, stress and materiality gates: accepted. Common
valuation ranking: stochastic 2269 < deterministic 2284 < incumbent 2302: the same order. The selector and
the common lens agree; the escalated candidate is the ex-ante best plan at review 0 by both.

Path after the divergence (A = product defaults with materiality off, the traced arm; B = mode):

| review | state | A order / B order | A hand / B hand | A unmet / B unmet | decisive difference |
|---|---|---|---|---|---|
| 0 | NO_ACTION | 11.3 / 15.5 | 40 / 40 | 0 / 0 | +4.2 units in B |
| 1 | PROTECT (demand driver .56) | 28.6 / 26.5 | 24 / 28 | 0 / 0 | both choose cvar; B orders 2 fewer |
| 2 | PROTECT | 25.2 / 23.1 (both RETAIN) | 4 / 8 | 13.0 / 9.0 | A in recovery mode (feasible set empty, joint recovery FEASIBLE_TIME_LIMIT rejected); B has feasible protection but the confirmation gate rejects it; B better |
| 3 | PROTECT, recovery mode | **33.9 / 4.3** | 0 / 0 | 14 / 14 | A: joint_recovery OPTIMAL, 33.9 now. B: joint_recovery FEASIBLE_TIME_LIMIT, `well_solved` False, 4.3 now (purchases deferred); same service statistic .936 on the worlds; accepted because every other class is INFEASIBLE in recovery mode |
| 4 | PROTECT | 2.6 / 13.9 | 23 / 21 | 0 / 0 | B catching up |
| 5 | PROTECT | 23.3 accepted / 10.8 (protected 23.9 rejected by the hedged-downside gate, RETAIN) | 25 / 22 | 0 / 0 | B under-orders again |
| 6 | PROTECT | 22.7 / 20.6 | **33 / 5** | **0 / 21.7** | B stocks out: recovery mode |
| 7 | PROTECT, supply driver 1.0 | 15.6 / 15.6 (B RETAIN) | 8 / 12 | 13.9 / 10.4 | |
| 8 | PROTECT | 25.1 / 32.3 (B recovery) | 19 / 9 | 0 / 8.1 | |
| 9-12 | PROTECT | 70.9 / 67.6 then equal | | 0 / 0 | trajectories re-converge at review 13 |

Exact mechanism of .884 -> .837 and 44.9 -> 63.2: the review-0 change (+4 units, or +10 against the
retained incumbent at product defaults) does not itself cost service; it moves the disruption reviews
onto a different path, on which the review-3 joint-recovery MILP hits its time limit and returns a
deferred-purchase plan (4.3 units now against 33.9 proved optimal on A's path) that the recovery ranking
must accept because nothing else is usable; the review-5 hedged-downside gate then rejects the protection
plan on B's confirmation draw; on hand falls to 5 at review 6 and 21.7 units go unmet, with recovery
shortfalls at reviews 7-8 (18.5 more). Total extra unmet 18.3, of which 21.7 at review 6 alone. The
candidate that looked better at review 0 was better at review 0; the worse service is produced by the
frozen P0 recovery machinery's sensitivity to the state it is handed (documented in P0 as solve-quality
exposure) and not by the stochastic candidate's quantity, timing, supply assumptions or the horizon.
Cell 21 receives the identical review-0 change (15.5 for 5.9) and improves (.746 -> .770, unmet 98 ->
89): the sign of the downstream effect is path-dependent, not a property of the candidate.

## H5. The NO_ACTION state, classified (part C)

Escalation events by context:

| context | events | P0 risk context load-bearing? |
|---|---|---|
| P and C fixtures: nil declared stress, no drivers ever, states cycle NO_ACTION / CAPITAL_OPTIMIZATION / NORMAL | 32 (C 10, P 22) | no: a true calm economic state |
| P0 cells, review 0: before a declared disruption (`operator_adverse`, supply state deterioration / closure recovery from review 1), credibility 0, no driver | 4 (cells 20, 21, 90, 108) | yes: the next review is PROTECT on every cell; the order placed here is the stock the disruption is met with |
| P0 cells after the disruption: LEAN regime, activity 0, but `protection_units` 47-252 against a lean base of about 4, flag FALSE_PROTECTION_RISK, incumbent still buying 14-32 | 6 (21 r19; 90 r20, r24, r25; 108 r28, r29) | yes: on-hand stock is inherited protection being unwound; the deterministic plan is infeasible on the worlds at 90 r20 / r24 (service .948 / .883) |

The screen's NO_ACTION test reads the incumbent's projected service, active drivers, material excess,
scarcity and decline; it does not read the declared stress, the pending recovery, or the provenance of
the on-hand stock (`inherited_on_hand`, `protection_units`, FALSE_PROTECTION_RISK are computed but not
consulted). NO_ACTION is therefore a selector label that occurs both in a true calm economic state
(P, C) and while P0 risk or recovery context is load-bearing (all ten P0 events).

**NO_ACTION IS NOT A VALID P1/P0 ARCHITECTURAL BOUNDARY.**

## H6. C: decisive-review forensics (part E; `candidate_completeness_escalate_CP.json`, mode on)

Seed 41001: two escalations (r0, r7); the stochastic and deterministic plans agree; replay identical.

| seed | review | on hand | incumbent | deterministic (schedule) | stochastic (schedule) | sampled stoch - det | common stoch - det | purchase / carry / shortage$ deltas | gate | executed A / B |
|---|---|---|---|---|---|---|---|---|---|---|
| 41002 | 0 | 150 | 400 every period | 453 now + 606 at p5 | 547 now + 501 at p6 | -9.5 (-0.16%) | **+32.9 (+0.53%)** | -53 / -1 / +72 | accepted | 452.6 / 546.9 |
| 41002 | 4 | 295 | 400 | 508 at p1 | 515 now | -80.8 (-1.97%) | -6.6 (-0.16%) | +36 / +8 / -32 | accepted | 400 (RETAIN) / 514.8 |
| 41002 | 9 | 258 | 400 | 400 at p1 | 400 at p1 | 0 | 0 | identical | accepted | 0 / 0 |
| 41003 | 0 | 150 | 400 | 453 + 606 at p5 | 400 + 671 at p4 | -26.3 (-0.43%) | -36.2 (-0.59%) | +63 / +6 / -81 | stress gate rejected both; RETAIN | 400 / 400 |
| 41003 | 3 | 237 | 400 | 687 at p1 | 693 now | -67.3 (-1.43%) | -2.4 (-0.05%) | +28 / +10 / -28 | stress gate rejected stochastic; deterministic accepted | 0 / 0 |
| 41003 | 4 | 142 | 400 | 670 now | 685 now | -31.5 (-0.76%) | -30.1 (-0.72%) | +73 / +1 / -65 | accepted | 400 (RETAIN) / 684.6 |
| 41003 | 9, 10 | 304, 196 | 400 | 0 | 0 | 0 | 0 | identical | | 0 / 0 then 0 / 400 (RETAIN at r10) |

Scale: the declared materiality is 1% of the candidate's cost (40-62 at these reviews) and the selector
band is 5% (205-304). Every stochastic-deterministic difference above is below the materiality
reference on the common lens (largest 36) and below the band on the sampled lens; one (41002 r4, sampled
-1.97%) is above materiality on the sampled lens and a tie on the common lens. By the declared scale the
two plans are NEAR-TIES at every changed review. The selector and the common lens disagree in sign once
(41002 r0, sampled -9.5 against common +32.9: the three worlds under-price the shortage the 547-unit plan
leaves at p5-p6); everywhere else they agree.

What the escalation changes on C is not the quantity purchased over the horizon but *which review the
next 400-unit lot is committed at*: "lot now" (stochastic, protection against the three worlds) against
"lot next period" (deterministic) or "retain the incumbent's 400 this period" (the product-default
outcome when the deterministic plan is gated out). Both seeds end with a full lot landing inside the last
review (B r10 executes 400 on both seeds under a RETAIN) and 463 / 475 units of residual against 262 /
200.

## H7. C: terminal decomposition (part F; declared result stays authoritative)

| seed | arm | units bought | residual | declared (80% salvage) | full terminal value | derived continuation value | extended-horizon empirical |
|---|---|---|---|---|---|---|---|
| 41001 | A / B (identical) | 1200 | 258 | -0.30% | -0.44% | -0.41% | -0.44% |
| 41002 | A product defaults | 1253 | 262 | +1.10% | +0.25% | +0.30% | +0.28% |
| 41002 | B mode | 1462 | 463 | **+5.37%** | +1.16% | +1.39% | +1.35% |
| 41003 | A product defaults | 1200 | 200 | 0.00% | 0.00% | 0.00% | 0.00% |
| 41003 | B mode | 1485 | 475 | **+5.65%** | +1.09% | +1.29% | +1.29% |

Decomposition of the mode's regression on C (mean of 41002 / 41003, percentage points against the best
baseline): declared +4.4 pts, of which +3.4 pts is the 80% haircut on a residual lot consumed within
4.7 weeks of the window's end (measurement) and +1.0 pt is real policy cost (an extra lot's carrying and
the earlier commitment). Both policies serve every unit of demand. The escalation regression on C is
about three quarters finite-horizon measurement and one quarter real.

## H8. Varied-truth diagnostics (parts D, G, H; `scripts/p1_escalation_truths.py`, request seed fixed,
20 truths each, `closure/escalation_truths_*.json`; the registered truths remain the evidence)

| fixture | request seed | parity A (mean; pass) | parity B (mean; pass) | B-A cost mean (se) | B better / worse / equal | at full terminal value B-A | service A / B | unmet A / B | inventory A / B | escalations per truth | actions A / B | abstentions A / B | B parity median / p10 / p90 / worst |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C | 41001 | +0.25%; 20/20 | +0.25%; 20/20 | 0.0 (0) | 0 / 0 / 20 | 0.0 | 1.000 / 1.000 | 0 / 0 | - | 2.2 | - | - | identical |
| C | 41002 | +1.08%; 20/20 | +0.36%; **13/20** | -41.8 (47.7) | 13 / 7 / 0 | +5.6 | 1.000 / 1.000 | .4 / 0 | 242 / 341 | 3.0 | 9.7 / 10.7 | 0 / 0 | -2.12% / -2.73% / +5.65% / +6.93% |
| C | 41003 | -0.30%; 19/20 | -0.89%; 20/20 | -34.6 (21.5) | 4 / 5 / 11 | -0.7 | 1.000 / 1.000 | 0 / 0 | 249 / 261 | 3.5 | 9.2 / 9.4 | 0 / 0 | -0.45% / -2.38% / +0.34% / +0.53% |
| P | 41001 | +1.21%; 18/20 | -0.06%; 20/20 | **-71.4 (9.7)** | 17 / 3 / 0 | -75.5 | .989 / .999 | 11.6 / 1.1 | 145 / 166 | 6.4 | 10.4 / 10.4 | 0 / 0 | |
| P | 41002 | +1.15%; 17/20 | +0.14%; 20/20 | **-56.9 (10.1)** | 17 / 3 / 0 | -62.7 | .989 / .998 | 11.4 / 2.5 | 145 / 166 | 7.3 | 10.4 / 10.4 | 0 / 0 | +0.13% / -0.61% / +0.85% / +1.09% |
| P | 41003 | +1.27%; 17/20 | -0.09%; 20/20 | **-77.2 (11.7)** | 18 / 2 / 0 | -81.2 | .988 / .999 | 12.7 / 0.8 | 149 / 192 | 6.7 | 10.6 / 10.4 | 0 / 0.1 | -0.01% / -0.93% / +0.37% / +0.90% |
| A | 41001 | +0.48%; 20/20 | +0.25%; 20/20 | -12.7 (6.2) | 12 / 5 / 3 | -13.0 | .994 / .996 | 6.5 / 4.7 | 16 / 16 | 11.0 | 1.7 / 1.9 | 0 / 1.0 | +0.01% / -0.20% / +0.96% / +1.61% |
| Q | 41001 | -0.01%; 20/20 | -0.20%; 20/20 | -10.5 (7.1) | 10 / 4 / 6 | +6.6 | 1.000 / .999 | .3 / 1.5 | 71 / 69 | 7.6 | 0.2 / 1.4 | 0 / 0 | -0.02% / -0.79% / +0.08% / +1.81% |

P: the gain is robust to the truth path at every request seed (17-18 of 20 truths better, mean -57 to
-77 on about 5,650, six to eight standard errors; service .989 -> .998-.999; unmet 11-13 -> 1-3; parity
20 / 20 against 17-18 / 20; the same number of interventions). Stochastic-candidate availability on P is
a genuine, path-robust economic gain.

C: on request seed 41001 the mode never changes a decision (20 identical truths). On 41002 it changes the
lot timing and the realised outcome becomes wide: mean better by 42 but the standard error is 48, seven
truths fail parity (worst +6.9%) where product defaults fail none (worst +1.7%), and at full terminal
value the mean effect is +6 (nil). On 41003 it is mildly better on average (-35, se 22) with 11 identical
truths. C's registered +3.61% is therefore (2) a near-tie whose realised path is unfavourable and (3)
mostly a finite-horizon / salvage measurement, driven by (4) MOQ lot timing that (6) the coarse
three-world stochastic candidate resolves differently from the deterministic one. It is not (1) a
clearly inferior ex-ante decision and not (5) a selector-ranking error: the selector agrees with the
common lens at every changed review but one, and that one is below the band.

A: escalation fires at every NO_ACTION review (11 per truth) yet the incumbent-good fixture keeps its
behaviour: actions 1.7 -> 1.9 per truth, abstentions 0 -> 1.0 (the materiality verdict now fires on the
escalated candidate), cost -13 (se 6), service .994 -> .996. No unnecessary intervention.

Q: neutral churn: interventions 0.2 -> 1.4 per truth, cost -10 (se 7) at the declared terminal and +7 at
full value, unmet .3 -> 1.5, worst truth +1.8% against +0.1%.

## H9. Common valuation (part I) and candidate quality (part J)

Selector against the common lens at the changed reviews: cell 20 r0 agree (stochastic best under both);
C agree at 6 of 7 changed reviews and disagree once below the band (H6); P (pass G) agree at every
decisive review. The issue is not selector comparability; the refuted hypothesis of pass G stands.

The same solver class exposes different economic actions by state:

| where | what the escalated stochastic candidate is | size against the deterministic plan |
|---|---|---|
| P (calm, no lot rule, six weeks of stock) | modest incremental protection: 2-100 more units now, 1-4 units of expected shortage removed | 0.1-2% of cost, always below the band |
| cell 20 / 21 / 90 / 108 review 0 (pre-disruption) | modest incremental protection: +2 to +4 units, 4-5 units of expected shortage removed | 0.3-1.2% of cost |
| C (400-unit MOQ) | a whole 400-700 unit lot committed now rather than next period; residual lands in the final review | 0.2-2% of cost sampled; below materiality on the common lens; realised effect up to 5.7% under the salvage haircut |

"Request the stochastic candidate" is therefore too coarse as an architectural statement: under a lot
rule the class is a lot-timing decision on three worlds, under a lean SKU it is a protection top-up, and
before a declared disruption it is the stock the disruption will be met with.

## H10. Existing domain boundary (part K)

Fields already in the model that separate "normal purchasing economics" from "protection / recovery":
`explicit_order_economics(req)` (supplier terms or fixed order fees declared); the screen state; the
per-SKU/location risk state (`regime` LEAN / PROTECT / RECOVER, `activity`, `active_drivers`,
`risk_active`, `flags` including FALSE_PROTECTION_RISK, `periods_to_lean`, `protection_units` against
`lean_baseline_units`); `stress_credibility` / `effective_stress_weight`; the joint-recovery `deficit`;
`inherited_on_hand` (replay-side provenance of stock). None of these is read by the NO_ACTION test or by
the candidate-request matrix beyond the screen state itself, and the events in H5 show that the
combination "screen NO_ACTION, activity 0" holds at review 0 of every P0 cell (before the declared
disruption) and during the unwind of 50-250 units of inherited protection. A boundary that would
separate P (true calm) from the P0 events would have to read the declared stress and the protection
provenance together; that boundary does not exist today as a single field or state. **The P1 purchasing
and P0 protection / recovery responsibilities are entangled inside one selector pass, one candidate
matrix and one state label.** No new threshold or composite gate is proposed here.

## H11. Classification (part L)

**Primary: A. STATE-MACHINE / PLANNER-BOUNDARY DEFECT.**

Evidence: (a) every P0 divergence begins at a NO_ACTION review whose P0 risk context is load-bearing (H5),
where the escalated candidate is either better by both lenses (cells 20 / 21) or displaces the
deterministic intervention through the band and materiality machinery (cells 90 / 108), and the
downstream damage is produced by the frozen recovery machinery's path sensitivity (H4), not by the
candidate; (b) the identical review-0 change improves cell 21 and damages cell 20; (c) on the true calm
fixture the same class is a robust gain (H8, P); (d) the request matrix keys on the screen label alone,
and that label does not distinguish the two situations (H10).
Counter-evidence: cell 90 / 108 review 0 also shows a selector / materiality interaction (a candidate
that is never selected changes the outcome by displacing another); C shows a horizon effect. Neither
explains cell 20, where selector and lens agree and the candidate was accepted.
Alternatives rejected: B (candidate-set completeness) was the hypothesis under test; it is confirmed as
the mechanism of P but cannot be shipped through the current state machine, so completeness is a symptom
of A, not the root. C (selector / materiality) explains only the 90 / 108 displacement and one C review;
the cell 20 selection is right by both lenses. D (horizon) explains three quarters of C's regression
(H7) and nothing on the P0 cells. E (stochastic candidate design) is refuted by bit-identity and by its
robust gain on P. F (P1 / frozen-P0 incompatibility) is the consequence: the six-cell "no worse" gate
cannot be passed by any change that alters a pre-disruption order, because the frozen machinery's
outcome is path-chaotic; that is a property of the frozen benchmark protocol as much as of the code, and
is recorded as the secondary classification rather than the root.

**Secondary: D. HORIZON / TERMINAL ECONOMICS DEFECT** (C only: +3.4 of +4.4 points are the salvage
haircut on a lot consumed within five weeks of the window), with **F** noted for the freeze protocol.

Ruled out in this pass: selector comparability (again); stochastic candidate mathematics; sampler; the
materiality thresholds as a cause of P; "always request" and any fixture / cell / seed keyed scope.

## H12. Recommended direction for the next pass (one)

Separate the planner's responsibilities before touching the candidate matrix again: a P1 purchasing pass
that runs the full economic candidate set (deterministic, stochastic, cadence) only where the request has
no declared stress in credible reach and no inherited protection being unwound, and a P0 protection /
recovery pass that keeps the frozen matrix and machinery everywhere else. The boundary must be built from
the fields in H10 (declared stress and its credibility, regime / activity, protection provenance), not
from the NO_ACTION label and not from a threshold tuned on the six cells; the six-cell gate then tests
that the P0 pass is bit-identical on the cells rather than "no worse" on a chaotic path.

## H13. Tests and state

`tests/unit/test_zaad_p1_candidate_completeness.py`: 15 tests, 13 pass. Two failures are test-design
errors (a validation check that used `model_copy`, which does not validate; a materiality expectation
that the escalated candidate at P review 4 would be immaterial at 10% thresholds, when its inventory
change is material); one is the genuine reporting inconsistency in H1 (`candidate_classes_requested`).
None was fixed: no code change in this pass. Full suite not rerun (no production code is being
finalised). Experimental diff left uncommitted and identified in H1; evidence files under `closure/`
uncommitted alongside it.

Product defaults unchanged from `4f6aedc`. **P1 REMAINS OPEN.** P2 not started (`claude/zaad-meio-p2`
does not exist). Validation7, Validation8, holdout4 untouched. Network Twin, PR #38, PR #39, frontend,
Vercel, production, other worktrees untouched.

---

# Pass I: planner-boundary architecture (purchasing economics against frozen protection / recovery), 2026-09-09

## I1. Clean baseline restored (stage 1)

The rejected escalation experiment was archived as evidence (`closure/archive_pass_h/`: the diff, the
two diagnostic scripts and the 15 tests as text) and its policy code, request field and script flags
were reverted to `4f6aedc`. The targeted lock was reproduced cell for cell (`closure/baseline_restored.json`
against `closure/lock_4f6aedc.json`: 120 cells, maximum absolute difference 0.0). The unit suite on that
baseline: 1461 passed, 2 skipped. Evidence commit `dfd1d30`.

Correction to the P0 record: the six-cell arm `neither` recorded on 2026-09-08 23:12 and used in passes
E-H as "product defaults" for cells 20 and 21 (service .884 / .746) was taken while the later-reverted
materiality-base experiment was live (it retains the incumbent at review 0 where the shipped code
accepts the mean-world plan). The clean reference recorded in this pass on code byte-identical to
`4f6aedc` (`closure/p0_arm_clean_reference.json`) gives cell 20 service .894, unmet 40.9, cost 2502 and
cell 21 service .760, unmet 93.0, cost 3331; cells 15, 16, 90 and 108 are identical to the record. The
pass-H first-divergence trace of cell 20 (`cell20_trace_p0_defaults.json`, cost 2502) was already
against the correct baseline, so its mechanism stands; the escalation arm's cell 20 (.837) is worse
against the true baseline by more than pass H stated. The clean reference is the P0 reference from here.

## I2. Ownership inputs, responsibilities, pre-registered rule (stages 2-6)

Recorded before any run in `P1_PLANNER_OWNERSHIP.md` (sections 2-6). In one line: a review is owned by
the P0 protection / recovery planner when the request declares a non-identity stress envelope, when
adaptive escalation is off, when the screen state is not calm, when any SKU/location has an active or
decaying driver, a non-LEAN regime, a confirmed decline or the FALSE_PROTECTION_RISK flag, or when the
screen reports a recovery obligation; otherwise by the P1 purchasing planner. On risk-state fields
alone review 0 of cell 20 and review 4 of P are the same state (LEAN, activity 0, credibility floored at
.10 for both); the one operator-supplied, review-0-available difference is the declared envelope
(`operator_adverse`: fill x0.7, +28 days, demand x1.1 against `nil`), which condition 1 uses. Fixture
truth (the supply state that starts at review 1) is never read. No per-unit inventory provenance exists;
the regime and the flag are the model's own account of protection under management, and the limitation
(protection stock already returned to LEAN unflagged reads as cycle stock) is recorded.

## I3. Router (stages 7-9)

`zaad/full/ownership.py`: `planner_owner(req, protection_rows, screen_result)` returns
`PURCHASING_ECONOMICS` or `PROTECTION_RECOVERY` with every reason; `purchasing_candidates` adds the
scenario plan to the NO_ACTION set and nothing else. In `plan()` the router runs after the screen and
before candidate assembly; under P0 ownership the frozen sets and path are untouched; the report carries
`orchestration.planner_owner`, `ownership_reasons` and `p1_classes_added`; the replay log records the
owner per review. `Request.planner_ownership` (default True) exists for evidence arms only. Selector,
gates, materiality, recovery, candidate mathematics, terminal economics and every P0 threshold are
unchanged. P1 matrix: NO_ACTION -> deterministic + stochastic; NORMAL_REPLENISHMENT and
CAPITAL_OPTIMIZATION unchanged.

Router tests (`tests/unit/test_zaad_planner_ownership.py`, 14): the twelve required cases (calm explicit
purchasing economics -> P1; active disruption -> P0; recovery deficit -> P0; inherited protection unwind
-> P0; FALSE_PROTECTION_RISK -> P0; ordinary calm cycle inventory -> P1; legacy full-set path -> P0;
declared mandate available now -> P0; future truth cannot influence the router (the same cell-20 request
with the identity envelope routes to P1; seeds change nothing); a P1 candidate cannot alter a P0-owned
review (cell 20 review 0 bit-identical in requested set, built set, every candidate's plan, band inputs,
choice, materiality); P0 ownership adds zero classes and zero MILPs; P1 candidates bit-identical to the
screen-requested classes) plus two structural tests. All pass.

## I4. P0 six-cell gate: decision-level bit-identity (stage 11; `scripts/p1_ownership_compare.py`)

Arm `router` (product defaults, router on) against `clean_reference`, per review: screen state,
requested set, built set, selected candidate, status, period-0 order, recovery admission, feasible set,
chosen candidate, materiality verdict.

| cell | reviews | owner (every review) | P1 classes added | decision-identical reviews | service | unmet | breaches | cost | required starvation |
|---|---|---|---|---|---|---|---|---|---|
| 15 | 12 | PROTECTION_RECOVERY | 0 | 12 / 12 | .980 = .980 | 5.0 = 5.0 | 1 = 1 | 1678 = 1678 | 0 |
| 16 | 12 | PROTECTION_RECOVERY | 0 | 12 / 12 | .972 = .972 | 7.0 = 7.0 | 1 = 1 | 1515 = 1515 | 0 |
| 20 | 20 | PROTECTION_RECOVERY | 0 | 20 / 20 | .894 = .894 | 40.9 = 40.9 | 3 = 3 | 2502 = 2502 | 0 |
| 21 | 20 | PROTECTION_RECOVERY | 0 | 20 / 20 | .760 = .760 | 93.0 = 93.0 | 5 = 5 | 3331 = 3331 | 0 |
| 90 | 26 | PROTECTION_RECOVERY | 0 | first run 5 / 26; rerun 26 / 26 | first run .859, rerun .863 = .863 | 71.9 / 70.1 = 70.1 | 5 / 4 = 4 | 3351 / 3317 = 3317 | 0 |
| 108 | 30 | PROTECTION_RECOVERY | 0 | 30 / 30 | .884 = .884 | 66.9 = 66.9 | 5 = 5 | 3665 = 3665 | 0 |

Cell 90, first router run: identical requested set, built set, worlds, choice, status and period-0
order at review 4, but the hedged candidate (a `FEASIBLE_TIME_LIMIT` solve, latency 70 s against 78 s
in the reference) returned no usable plan and dropped out of the feasible set; the path then diverged
from review 5. A rerun of the router arm on cell 90 alone (`p0_arm_router_rerun.json`) reproduces the
clean reference on all 26 reviews (cost 3317, service .863), as does a rerun of the clean code itself
(`p0_arm_clean_reference_rerun.json`, 26 / 26). Classification: frozen numerical variability of a
wall-clock-limited solve with identical inputs, not a router effect. With the rerun, the P0-owned path
is decision-identical on 120 / 120 reviews; the router added zero classes and zero solves on every one.

Cell 20 review 0 (the pass-H failure point): owner PROTECTION_RECOVERY by the declared mandate;
requested set `deterministic_network` only; the mean-world plan (11.3 units) accepted exactly as in the
reference. On review-0 information the assignment is semantically right: the operator has declared the
envelope the disruption will draw from; nothing else about the state says calm-or-not, and nothing
about the truth is read.

## I5. Targeted fixtures under the router (stage 12-13; `closure/router_targeted.json`, product defaults, realised ledger)

| fixture | lock | router | service | unmet | inventory | actions / 33 | abstentions | owner P1 / P0 reviews | P1 classes added | MILPs | wall |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P | +2.04% FAIL | **+0.29% PASS** | .990 | 10.7 | 179 | 32 | 0 | 32 / 1 | 22 | 163 | 7 s |
| C | +0.27% | **+3.61% FAIL** | 1.000 | 0 | 282 | 30 | 0 | 33 / 0 | 12 | 195 | 6 s |
| O | +0.77% | +0.46% | .920 | 87.9 | 69 | 29 | 0 | 23 / 10 | 22 | 150 | 6 s |
| I | +0.53% | +0.53% | 1.000 | 0 | 258 | 19 | 3 | 33 / 0 | 15 | 240 | 25 s |
| A | +0.09% | +0.43% | .989 | 12.7 | 15 | 6 | 3 | 33 / 0 | 32 | 133 | 4 s |
| G | -8.21% | -10.01% | 1.000 | .6 | 867 | 32 | 0 | 33 / 0 | 11 | 252 | 16 s |
| Q | +0.01% | +0.85% | .980 | 22.5 | 62 | 3 | 0 | 26 / 7 | 23 | 144 | 5 s |
| T | -13.04% | -11.47% | 1.000 | 0 | 806 | 30 | 0 | 33 / 0 | 10 | 255 | 22 s |

P: the router's actions are bit-identical to the pass-H escalation arm on all three seeds (5573.09 /
5876.96 / 5959.05), so its varied-truth robustness (H8: better on 17-18 of 20 truths at every request
seed, six to eight standard errors) carries over without a rerun. The scenario plan is available at
every P1-owned NO_ACTION review, bit-identical to the forced class (test 12), no analytic-shortage
surrogate, no buffer. A keeps its abstention (3 NO MATERIAL IMPROVEMENT verdicts; 6 of 33 actions).
O and I inside 2%. G and T improve or stay far ahead; Q moves from +0.01% to +0.85%, inside tolerance
and neutral on varied truths (H8). C fails at +3.61% with exactly the H6 / H7 mechanism (the router's C
plans equal the escalation arm's: 5761 / 6255 / 6316).

## I6. Terminal continuation valuation (stage 15; `zaad/full/terminal.py`, evaluation only)

Conditions for the optional stage held: the boundary is P0-safe (I4), P passes, O / I / A / G / Q / T
are safe, C is the only substantive blocker and reproduces the proven terminal mechanism. The module
values residual stock beyond the window from the last review's fitted demand and the declared economics
only: units become available at arrival (on hand at once, in transit at their due period), are consumed
in availability-then-expiry order at the fitted mean rate, and each unit is worth the purchase it avoids
(`asset_value`) less carrying and cost of capital until its consumption, floored at salvage, capped at
unit value, salvage when it would expire first or when demand is zero. No fixture constant, no cap, no
policy term. The settlement ledger is untouched: the replay reports `terminal_continuation` and
`economic_cost_continuation` beside the realised `economic_cost`. Nine tests
(`tests/unit/test_zaad_terminal.py`): zero demand -> salvage only; consumption next period -> nearly
the unit value; slower consumption and a cost of capital reduce the value monotonically, never below
salvage; expiry before consumption -> salvage; in-transit timing matters; a 400-unit lot straddling the
window has no cliff; the derived value of fixture C's residual agrees with twelve further truth periods
consumed empirically within 1% of the residual's value; lengthening the window by one review moves the
continuation-valued cost by about one period of operating cost and less erratically than the salvage
ledger; the ledger is not falsified.

## I7. Full A-T under the router (stage 16; `fixtures_product_defaults_terminal_continuation.jsonl`, both evaluations stored; `scripts/p1_dual_terminal_table.py`)

Fixture definitions, seeds, tolerance and the N / R proven-invalid classification unchanged. Every cell
COMPLETE; attribution partitions reconcile on 60 / 60 ZAAD cells; invariants 720 / 720 on 60 fixture
seeds (`P1_INVARIANTS.json`).

| fixture | realised ledger (declared salvage) | continuation evaluation | service | owner P1 / P0 | actions | abstentions |
|---|---|---|---|---|---|---|
| A | +0.43% | +0.46% | .989 | 33 / 0 | 6 | 3 |
| B | -10.70% | -1.06% | 1.000 | 33 / 0 | 33 | 0 |
| C | **+3.61% FAIL** | +0.77% | 1.000 | 33 / 0 | 30 | 0 |
| D | -0.58% | +0.17% | .998 | 33 / 0 | 12 | 3 |
| E | -0.00% | +0.00% | 1.000 | 33 / 0 | 1 | 1 |
| F | +0.24% | +0.28% | .998 | 33 / 0 | 27 | 0 |
| G | -10.01% | -0.41% | 1.000 | 33 / 0 | 32 | 0 |
| H | -3.73% | -2.29% | .999 | 33 / 0 | 27 | 1 |
| I | +0.53% | **+3.05% FAIL** | 1.000 | 33 / 0 | 19 | 3 |
| J | -11.06% | -3.52% | 1.000 | 33 / 0 | 10 | 6 |
| K | -11.20% | -3.64% | 1.000 | 33 / 0 | 10 | 6 |
| L | -10.16% | -4.74% | 1.000 | 33 / 0 | 33 | 0 |
| M | -0.54% | +0.44% | .950 | 12 / 21 | 23 | 0 |
| N | -0.71% (categories: proven invalid) | +0.42% (same) | .988 | 30 / 3 | 26 | 1 |
| O | +0.46% | +0.44% | .920 | 23 / 10 | 29 | 0 |
| P | +0.29% | +0.39% | .990 | 32 / 1 | 32 | 0 |
| Q | +0.85% | +1.08% | .980 | 26 / 7 | 3 | 0 |
| R | -0.05% (categories: proven invalid) | -0.04% (same) | .992 | 33 / 0 | 3 | 3 |
| S | +0.26% | **+3.59% FAIL** | 1.000 | 33 / 0 | 27 | 2 |
| T | -11.47% | -4.21% | 1.000 | 33 / 0 | 30 | 0 |
| **raw** | **17 / 20** | **16 / 20** | | | | |
| **valid (N, R excluded)** | **17 / 18: C fails** | **16 / 18: I, S fail** | | | | |

Ownership over the 660 ZAAD reviews: 619 P1-owned, 41 P0-owned (M 21: order-calendar reviews with an
active supply driver; O 10, Q 7, N 3, P 1: reviews with an active demand or supply driver). Runtime
(660 reviews, 4 workers): p50 .13 s, p90 1.16 s, p95 2.5 s, max 33 s, total 94 s against the lock's
.10 / .76 / 1.41 / 16.6 / 81 s: the added scenario solve at P1-owned NO_ACTION reviews costs about a
sixth more wall time.

The continuation evaluation closes C (+0.77%) and opens I (+3.05%) and S (+3.59%): on both, the
EOQ-style baseline ends the window holding a full late load (341-404 units on I, 292-356 on S) that the
realised ledger credits at the declared 80% salvage and the continuation lens credits at 98-99% of
unit value; ZAAD ends with 106-139 units. The residual sensitivity is symmetric: whichever terminal
rule is declared, some lot-cycle fixture ends the twelve-week window one lot apart from its baseline
and the gap is decided by the terminal rule, not by the policies. Neither evaluation passes C, I and S
together at the declared window.

## I8. Horizon-extension diagnostic (not the declared evaluation; `scripts/p1_horizon_extension_diag.py`, `closure/horizon_extension_diag.json`)

The same fixtures built with a 24-period horizon (23 reviews), every other field as declared, all five
policies, three seeds, both evaluations:

| fixture | realised ledger, 24 periods | continuation, 24 periods | reading |
|---|---|---|---|
| C | +0.26% (seeds -0.55 / +1.25 / +0.09) | +0.30% | the two rules converge; the declared +3.61% is the window, as pass H said |
| P | +0.62% | +0.50% | robust under both rules and both windows |
| I | +4.54% (seeds +11.04 / +1.21 / +1.37) | +5.68% (+11.13 / +2.97 / +2.93) | the two rules agree that ZAAD is dearer than the full-load EOQ baseline; on seed 41001 the gap is 11% with equal residuals (137 against 138 units), a within-window freight / lot-sizing difference the twelve-week salvage haircut on the baseline's late load had masked |
| S | +3.48% on seed 41001; seeds 41002 / 41003 ABSTAIN (incumbent unfinanceable at the longer horizon: the fixture's receivables and credit are sized for its declared window) | +3.54% | not a valid extension for S; one seed suggests the same masking as I |

Reading: the terminal sensitivity is a benchmark-window property (a twelve-week window on four-week
lots ends one lot apart), and lengthening the window resolves C and P but not I. I therefore carries a
real P1 economics question under a freight cap (full-load consolidation against ZAAD's smaller, more
frequent loads) that the declared window did not measure. It is recorded here and not chased in this
pass.

## I9. Freeze gate

| # | condition | result |
|---|---|---|
| 1 | planner ownership semantic and pre-registered | yes (`P1_PLANNER_OWNERSHIP.md`, rule unchanged after the runs) |
| 2 | no fixture / cell / seed routing | yes (the rule reads declared stress, screen state, risk state, recovery rule) |
| 3 | no future-truth leakage | yes (test 9; the declared envelope is a request input; the truth's supply state is never read) |
| 4 | P0-owned path frozen and isolated | yes (zero classes added on every P0-owned review; tests 10-11) |
| 5 | P0 six-cell gate | decision-identical 120 / 120 (cell 90 after a rerun; frozen numerical variability of a time-limited solve recorded) |
| 6 | required starvation zero | yes on all six cells |
| 7 | P <= 2% | yes: +0.29% (robust, H8) |
| 8 | C <= 2% | **no under the declared realised ledger (+3.61%); yes under the continuation evaluation (+0.77%) and at a doubled window (+0.26%)** |
| 9 | O <= 2% | yes: +0.46% |
| 10 | I <= 2% | yes under the declared ledger (+0.53%); **no under the continuation evaluation (+3.05%) and at a doubled window (+4.54%)** |
| 11 | A abstention safe | yes: 3 NO MATERIAL IMPROVEMENT verdicts, 6 of 33 actions, +0.43% |
| 12 | G / Q / T safe | yes: G -10.0%, T -11.5%, Q +0.85% (inside tolerance, neutral on varied truths) |
| 13 | valid A-T fixtures pass | 17 / 18 under the declared ledger (C), 16 / 18 under continuation (I, S) |
| 14 | N / R honest | proven-invalid classification preserved, both fail on `categories` as recorded |
| 15 | no hidden safety buffer | none added |
| 16 | stochastic candidate mathematics unchanged | unchanged (bit-identity tests) |
| 17 | selector not benchmark-tuned | unchanged |
| 18 | terminal economics general and principled if changed | the continuation valuation is general, tested and evaluation-only; it is NOT adopted as the declared evaluation because it moves I and S out as it moves C in |
| 19 | attribution reconciles | 60 / 60 |
| 20 | tests | 1484 passed, 2 skipped (1461 baseline + 14 router + 9 terminal) |
| 21 | invariants | 720 / 720 |
| 22 | runtime | p50 .13 s, p95 2.5 s, max 33 s, 94 s for 660 reviews |
| 23 | Validation7 / 8 / holdout4 untouched | yes |
| 24 | unrelated work untouched | yes (Network Twin, PR #38, PR #39, frontend, Vercel, production, other worktrees) |

**Verdict: P1 CORE ARCHITECTURE PASS — TERMINAL/HORIZON ECONOMICS REMAINS OPEN.** Not frozen. The
exact remaining blocker: the declared twelve-week window ends one lot cycle apart from the baselines on
C, I and S, so their parity is decided by the terminal rule; the realised ledger fails C, the
principled continuation evaluation fails I and S, and a doubled window clears C and P but shows I
dearer than its full-load baseline under either rule. The decision needed next is a benchmark one
(window and terminal evaluation design, then a look at I's lot sizing under a freight cap), not an
optimizer patch. P2 NOT STARTED — P1 FREEZE GATE NOT MET.

## I10. Defaults and state after this pass

Product defaults: `planner_ownership=True` (the router) is the one behavioural change from `4f6aedc`;
under a declared non-identity stress envelope, or any risk activity, every review runs the frozen P0
path. `stratified_scenarios`, `analytic_shortage`, `timing_tiebreak` remain opt-in. The continuation
valuation is reported by every replay beside the realised cost and used by no gate. Validation7,
Validation8, holdout4 uninspected. `claude/zaad-meio-p2` does not exist.

# Pass J: benchmark / horizon closure (2026-09-09; from de4e771)

Pre-registration: `P1_BENCHMARK_PREREGISTRATION.md` (written before any extended run; correction 1
appended before any extended ZAAD result was read). Tables: `P1_HORIZON_CONVERGENCE.md`,
`P1_HORIZON_SUMMARY.json`; run record `closure/horizon52.jsonl` (300 cells).

## J1. Lock (stage 1)

Branch `claude/zaad-cycle-stock-p1` at `de4e771`, clean tree, no jobs, no `claude/zaad-meio-p2`.
Targeted reproduction under the legacy benchmark (`closure/stage1_lock_P.json`, product defaults,
realised ledger): C +3.61% FAIL, I +0.53%, P +0.29%, all bit-identical to `closure/router_targeted.json`.
No terminal method was declared default; the realised ledger was the authoritative benchmark;
Validation7 / Validation8 / holdout4 untouched. The planner's own in-model terminal continuation
(`terminal_continuation`, contracts) is off by default, so the planner's objective haircuts end-of-plan
stock at the declared salvage; this is product policy and was not changed in this pass.

## J2. Horizon inventory (stage 2)

Full table in the pre-registration, section 2. Planning horizon 12 periods and evaluation window 11
reviews on every fixture; lead one period (M two, N three); next order opportunity the following review.
Lot cycles from the recorded legacy evidence: the EOQ-style baseline buys 10-20 weeks of demand per order
on B, G, J, K, L and T (its lot cycle is LONGER than the evaluation window), 4-7 weeks on C, F and I;
ZAAD 7-8 weeks on B / G / J / K / L / T and 3-5 on C / I. The twelve-week window therefore ends inside a
lot cycle on half the family, and the legacy salvage / continuation deltas on C (+3.61 / +0.77), I
(+0.53 / +3.05) and S (+0.26 / +3.59) are decided by the terminal rule.

## J3. Extension mechanics (stage 3; `zaad/full/replay.py` opt-in `rolling=True`, `zaad/full/evaluation.py`)

* Rolling mode: every review replans on a fresh twelve-period snapshot (the replay's own production
  note); declared period data roll by repeating the last declared value, committed payments roll into
  `other_payments` at their due period, none dropped. The legacy shrinking path is untouched: after the
  patch C reorder_point, C ZAAD and P ZAAD reproduce the lock to the cent, the full unit suite passes
  (1,484 passed, 2 skipped), and the six-cell P0 arm was rerun (J11).
* Truth: `long_truth` stitches twelve-period draws with `as_of` advanced by 12k periods and seed +k;
  segment 0 is the legacy truth bit for bit (demand, arrivals, fills checked on C).
* Endpoint reconstruction `endpoint(initial, log, W)`: opening assets of review 0, ledger components of
  reviews 0..W-1, terminal state of review W-1 under each rule. Equal to a replay stopped at W to 1e-6
  (test 10). One run per cell therefore yields the whole convergence curve, W = 1..52.
* Three terminal rules scored at every endpoint on identical trajectories: A salvage (the ledger), B
  continuation at unit price (`terminal.py` as pre-registered), B' continuation at the policy's own
  landed unit cost (correction 1: unit price plus the freight, ordering and receiving cost per unit the
  policy incurred over the window; carrying on asset value; salvage floor, landed cap, expiry and
  zero-demand impairment unchanged; `terminal.py` `landed=` argument, default bit-identical).
* Run: 300 cells, 52 reviews requested, four workers, 2,205 s wall. ZAAD reviews at full horizon: n 3,013,
  p50 .99 s, p90 5.9 s, p95 11.4 s, max 79 s. Every cell complete except S (J7).

## J4. Endpoint sensitivity and convergence classification (stages 3-4; `P1_HORIZON_CONVERGENCE.md`)

Delta of ZAAD against the best baseline at W in {11, 23, 35, 47, 52}, seed means, under B':

| fixture | @11 (rolling) | @23 | @35 | @47 | @52 | max dev over 40..52 | class |
|---|---|---|---|---|---|---|---|
| A | +1.70 | +1.19 | +1.06 | +0.96 | +0.87 | .23 pp | A stable pass |
| B | +3.41 | +0.83 | +2.78 | +2.30 | +2.49 | 1.44 pp | E non-convergent |
| C | +2.32 | +0.77 | +0.74 | +0.61 | +0.30 | .36 pp | C boundary-sensitive, converges to pass |
| D | -0.16 | +0.30 | +0.73 | +0.70 | +0.63 | .17 pp | A |
| E | +0.04 | -0.02 | -0.03 | -0.06 | -0.10 | .07 pp | A |
| F | +1.28 | +1.27 | +0.83 | +0.64 | +0.72 | .08 pp | A |
| G | +11.01 | +9.27 | +6.26 | +6.15 | +6.18 | .83 pp | D boundary-sensitive, converges to FAIL |
| H | -2.36 | -1.75 | -1.31 | -1.32 | -1.27 | .19 pp | A |
| I | +6.87 | +9.85 | +7.46 | +7.16 | +7.14 | .68 pp | D converges to FAIL |
| J | +0.88 | -0.15 | -0.01 | -0.14 | +0.15 | .65 pp | A |
| K | +0.94 | -0.15 | -0.01 | -0.15 | +0.15 | .67 pp | A |
| L | +1.30 | +2.04 | +1.45 | +1.35 | +0.81 | .60 pp | A |
| M | +0.94 | +0.53 | +0.23 | +0.04 | +0.05 | .17 pp | A |
| N | +0.50 | +1.13 | +0.89 | +1.14 | +1.07 | .18 pp | A (proven-invalid classification kept) |
| O | -0.37 | -0.10 | -0.07 | +0.12 | +0.09 | .13 pp | A |
| P | -0.43 | -0.29 | +0.02 | +0.14 | +0.16 | .11 pp | A |
| Q | +0.05 | +0.05 | +0.03 | +0.22 | +0.19 | .04 pp | A |
| R | +0.69 | +0.38 | +0.41 | +0.51 | +0.65 | .18 pp | A (proven-invalid classification kept) |
| S | +4.21 | - | - | - | - | - | invalid at 52 (J7) |
| T | +5.40 | +5.22 | +6.80 | +7.30 | +6.87 | .96 pp | D converges to FAIL |

Under the salvage rule 9 / 19 fixtures are stable at 52 (B, C, F, G, H, I, J, K, L, T all non-convergent:
the salvage haircut on whichever policy holds the late lot swings the delta by 1-6 pp between adjacent
endpoints); under unit-price continuation 12 / 19; under landed-cost continuation 18 / 19 (B alone,
whose EOQ baseline buys 18.6 weeks of demand per lot, so 52 weeks is 2.8 cycles).

Special attention: C converges to PASS under every rule once the planning horizon rolls (salvage -0.24%,
B / B' +0.30% at 52); the legacy +3.61% was the window. I converges to FAIL under every rule (+8.30 /
+8.16 / +7.14% at 52); the legacy +0.53% was the window masking a real lot-sizing gap, as pass I's
doubled-horizon diagnostic suggested. S cannot be run to 52 (J7). P is stable within +/-0.5% throughout.

## J5. Benchmark options (stage 5)

* **A fixed window + salvage** (legacy). Strength: the ledger's own conservative rule, no model of the
  future. Weakness, now measured: BSI 1.635 pp per two-review shift (1.391 on baseline-only pairs), 10 of
  19 fixtures non-convergent at 52 reviews; the rule fails validation test 2 (a unit consumed the week
  after the cutoff is written down 20%). Salvage percentage sensitivity was not explored because the rule
  fails on a property, not a parameter: any haircut below the landed price penalises the late lot holder,
  any haircut above it rewards them.
* **B continuation at unit price**. Mathematics in `terminal.py`; removes the 20% cliff; BSI .904 (.795
  baseline-only); fails test 8 on freight-heavy fixtures because an endpoint just after a load charges
  the load's freight and ordering with no offsetting credit (correction 1). 12 / 19 stable.
* **B' continuation at landed cost**. Passes all twelve tests; BSI .477 (.426 baseline-only); 18 / 19
  stable. Approximation error against the actual extension: over matched-state windows on I the salvage
  and B' window costs agree within .1-.5% and B' cost per unit of demand agrees with the 40-review value
  within 1.5% (test 8); on C the derived value of the residual agrees with twelve further truth periods
  within 1% (`test_zaad_terminal` test 7).
* **C extended realised evaluation**: the endpoint grid itself, every policy replanning on the same
  constant horizon; no policy frozen while another operates. It is the declared window (52 reviews).
* **D warm-up + scored window + settled tail** (start-offset diagnostic s = 0 / 4 / 8 with symmetric
  endpoint handling, Option D table): under B' the deltas move by at most .5 pp on the stable fixtures
  and 1.0 pp on T; under salvage by up to 3.2 pp (B) and 5.5 pp (T). B' already has the property D was
  meant to buy, so D is not implemented.
* **E lot-cycle normalisation** (Option E table): scoring each policy at its own cycle minimum in [40, 52]
  and normalising per week changes no verdict (largest move +0.8 pp on T, L +.5 pp); a policy-specific
  endpoint is not a common benchmark and stays diagnostic.

## J6. Pre-registered benchmark and selection (stage 6)

Declared P1 evaluation: constant rolling twelve-period planning horizon; realised ledger scored at W* = 52
reviews (one commercial year) on the stitched truth; residual on-hand and in-transit units valued under
the landed-cost continuation rule B'; service, breaches and unmet inside the window only; the same rule for
ZAAD and every baseline, no policy, fixture, C- or I-specific term; tolerance unchanged. Selected by the
pre-registered rule of section 6: B' is the only rule passing the twelve validation tests, and it also
has the lowest boundary-sensitivity index (.477 against .904 and 1.635; .426 / .795 / 1.391 on pairs that
do not involve ZAAD). The a-priori expectation recorded in the pre-registration (salvage fails test 2,
continuation has the lower BSI) held; the correction (unit price to landed cost) came from test 8 on a
baseline-only pair before any extended ZAAD number existed.

Mathematical definition. For a policy's trajectory scored at W: cost(W) = opening assets at review 0 +
sum over reviews t < W of every ledger component of the one-step settlement at t, minus the terminal
credit at W. Terminal credit: for each SKU / location, residual units (on hand at 0, in transit at their
due period) consumed in availability-then-expiry order at the fitted mean rate mu; the k-th unit consumed
at time tau_k is worth min(L, max(s, L - a (h + c) tau_k)), where L is the policy's landed unit cost over
the window (unit price a plus its freight, ordering and receiving per unit bought; a when it bought
nothing), s the declared salvage, h the location's holding rate per value-period and c the cost of
capital; a unit expiring before tau_k, or never consumed (mu = 0), is worth s. Stability criterion: over
W in [40, 52] the delta stays within +/-1 pp of its value at 52 and the verdict is identical.

## J7. Validity at the declared endpoint (section 7)

S: its declared receivables (450 / week) are below every policy's cash-out, so the declared cash plus
credit is exhausted between reviews 12 and 45 (ZAAD abstains at reviews 12-19 once the declared incumbent
is unfinanceable; the baselines hit physical financing failures at 24-45). S is PROVEN INVALID at the
declared benchmark: a transient cash-squeeze fixture whose inputs cannot carry any policy through a year.
Its legacy verdict (+0.26% under the realised ledger) is kept as a legacy record; the diagnostic to the
last common endpoint (W = 12: +4.21%) is not a verdict. N and R keep their proven-invalid classification
(both `categories` checks fail exactly as recorded); their costs are inside tolerance at 52.

## J8. Benchmark validation tests (stage 7; `tests/unit/test_zaad_benchmark_horizon.py`, 12 tests)

1 phase-offset policies (periodic:4 on C, phase shifted one review, window [4, 52] after the opening
transient): B' .20% apart, salvage .24%; 2 residual consumed immediately: B' credits > 99% of price,
salvage 80%; 3 never consumed: salvage only; 4 in-transit valued consistently (on hand > due next period
> due later > salvage); 5 carrying reduces it (L against C); 6 cost of capital reduces it; 7 zero demand:
salvage; 8 complete lot cycle (matched-state windows on I EOQ): salvage and B' window costs within 1%, B'
per-unit cost within 1.5% of the 40-review value, unit-price B further away; 9 increasing horizon converges
the EOQ-versus-periodic ranking on I under both rules; 10 identical trajectory, identical result (endpoint
reconstruction = stopped replay to 1e-6); 11 service after the nominal window not scored; 12 the scorer has
no policy argument (same terminal state, same credit). All pass; the nine `terminal.py` tests unchanged.

## J9. A-T under the declared benchmark beside the legacy record (stage 9)

Full table with every component in `P1_HORIZON_CONVERGENCE.md` (Stage 9). Summary, ZAAD against the best
baseline, B' at 52, product policy UNCHANGED (stage 8):

| fixture | legacy 12-week (salvage) | declared @52 | verdict | service | actions / abstentions (156 reviews) |
|---|---|---|---|---|---|
| A | +0.43% | +0.87% vs incumbent | PASS | .989 | 38 / 11 |
| B | -10.70% | +2.49% vs EOQ | FAIL (non-convergent) | 1.000 | 150 / 0 |
| C | +3.61% | +0.30% vs reorder_point | PASS | 1.000 | 139 / 0 |
| D | -0.58% | +0.63% | PASS | .995 | 70 / 13 |
| E | -0.00% | -0.10% | PASS | 1.000 | 39 / 4 |
| F | +0.24% | +0.72% vs periodic:2 | PASS | 1.000 | 118 / 0 |
| G | -10.01% | +6.18% vs EOQ | FAIL | 1.000 | 144 / 0 |
| H | -3.73% | -1.27% vs periodic:2 | PASS | .995 | 117 / 11 |
| I | +0.53% | +7.14% vs EOQ | FAIL | 1.000 | 138 / 0 |
| J | -11.06% | +0.15% vs EOQ | PASS | 1.000 | 142 / 5 |
| K | -11.20% | +0.15% vs EOQ | PASS | 1.000 | 142 / 5 |
| L | -10.16% | +0.81% vs EOQ | PASS | 1.000 | 151 / 0 |
| M | -0.54% | +0.05% | PASS | .987 | 144 / 0 |
| N | -0.71% | +1.07% | proven invalid (kept); inside tolerance | .987 | 124 / 5 |
| O | +0.46% | +0.09% | PASS | .980 | 151 / 2 |
| P | +0.29% | +0.16% | PASS | .995 | 128 / 9 |
| Q | +0.85% | +0.19% | PASS | .991 | 19 / 0 |
| R | -0.05% | +0.65% | proven invalid (kept); inside tolerance | .991 | 27 / 9 |
| S | +0.26% | invalid at 52 | PROVEN INVALID at the declared benchmark | - | - |
| T | -11.47% | +6.87% vs EOQ | FAIL | 1.000 | 141 / 0 |

Valid fixtures at the declared benchmark: 17 (A-M, O, P, Q, T less nothing; S, N, R invalid). Passing:
13 / 17. Failing: B, G, I, T. Reading: the legacy double-digit "wins" on B, G, J, K, L and T were the
salvage haircut on the EOQ baseline's late 10-20-week lot; once the planning horizon rolls and the
residual is valued at what it avoids, J, K and L are ties (+0.15 to +0.81%), and B, G, I and T show ZAAD
paying more freight and ordering than the full-load / EOQ baseline. Ownership over the 3,013 ZAAD reviews:
2,631 P1-owned, 382 P0-owned (M 143: order-calendar reviews with an active supply driver; Q 87, O 57; the
rest 17-33 per fixture). Attribution on the first review is unchanged from the legacy record (review 0
plans on the identical request).

## J10. True remaining failures under the fair benchmark (stage 10)

| fixture | declared @52 | class | mechanism (from J11-J13) |
|---|---|---|---|
| B | +2.49% vs EOQ, non-convergent (18.6-week EOQ lots, 2.8 cycles in a year) | A LOT-SIZING (+ E residual: the fixture's own cycle is a fifth of the window) | ZAAD lots half the EOQ (767 against 1,884 units) with 100-unit top-ups; 8 orders against 3 |
| G | +6.18% vs EOQ | A LOT-SIZING / B FREIGHT / C ORDER TIMING | one-week top-up orders ($800 tier + $100) the review before each 20-pallet load; 13 orders against 7; freight +$3,400, ordering +$600 |
| I | +7.14% vs EOQ | A LOT-SIZING / B FREIGHT | 200 / 315 / 66 / 200 / 148-unit orders interleaved with near-full loads; 16 orders against 12; freight +$3,200, ordering +$600 |
| T | +6.87% vs EOQ | A LOT-SIZING / B FREIGHT / C ORDER TIMING | as G with case rounding; 13 orders against 7; freight +$3,700, ordering +$1,200 |
| C | +0.30% PASS | resolved: the legacy +3.61% was the window | - |
| S | invalid at the declared benchmark | F/G: fixture design (receivables below cash-out) | - |
| all others | PASS, stable | - | - |

One mechanism, general to every fixture with order-level economics, established in J12.

## J11. I forensics (stage 11; `scripts/p1_i_forensics.py`, `closure/forensics_I_max_pallets_ftl_cap_41001.json`)

Rolling replay of ZAAD on I seed 41001 with every candidate traced and the EOQ baseline's order from
the identical snapshot. Review table (opening stock, inbound, demand, order, tier charged):

| review | ZAAD open | inbound | demand | ZAAD order | tier | EOQ open | EOQ order | ZAAD state / candidate chosen |
|---|---|---|---|---|---|---|---|---|
| 0 | 150 | 0 | 98 | 442 | 1,100 | 150 | 450 | NO_ACTION / stochastic |
| 4 | 186 | 0 | 102 | 400 | 1,100 | 195 | 450 | NO_ACTION |
| 6 | **375** | 0 | 88 | **438** | 1,100 | 432 | 0 | CAPITAL_OPTIMIZATION / stochastic_network (a load bought with 3.75 weeks on hand; EOQ waits to 139 at review 9) |
| 13 | 141 | 0 | 100 | 398 | 1,100 | 209 | 0 (450 at 14) | NO_ACTION / cadence_4_network |
| 17 | 130 | 0 | 110 | **200** | 800 | 240 | 0 (450 at 18) | NO_ACTION / stochastic_network |
| 19 | 114 | 0 | 108 | **315** | 1,100 | 29 (+440 due) | 0 | NO_ACTION / stochastic_network |
| 21 | 204 | 0 | 90 | 440 | 1,100 | 250 | 0 (450 at 22) | NO_ACTION / cadence_2_network |
| 26 | 146 | 0 | 104 | 442 | 1,100 | 198 | 450 | NO_ACTION |

Every review P1-owned (52 / 52), no abstention, no recovery mode; the full-load candidate is built and
chosen at 0, 4, 13, 21, 26; the departures from EOQ are the early load at 6 and the small loads at 17
and 19 (and later 42 / 43 / 50: 66, 200, 148 units). Selector: at 17 and 19 the chosen stochastic
candidate itself carries the small first order; the selector did not overrule a full-load candidate.

## J12. I lot-size economic frontier at the decisive reviews (stage 12)

Twelve-period plan cost on the mean world with the first order allowed up to q (the optimizer's own
preference, x0 = what it chose) and pinned at exactly q with the envelope's later schedule:

| review | q <= 100 | q <= 150 | q <= 200 | q <= 300 | q <= 450 | reading |
|---|---|---|---|---|---|---|
| 13 (on hand 141) | x0 0: 9,561 (shortage 1,835) | x0 150: 9,435 | x0 155: **9,428.8** | x0 155: 9,428.8 | x0 401: **9,428.8** (pinned 450: 9,489) | flat: 155 and 401 cost the same to the cent; freight 3,000 (three shipments) in every schedule |
| 17 (on hand 130) | x0 0: 9,661 | x0 150: 9,530 | x0 166: **9,438.0** | x0 166: 9,438.0 | x0 166: 9,438.0 (pinned 450: 10,087) | the optimizer, allowed a full load, prefers 166 |
| 19 (on hand 114) | 10,580 | 10,580 | x0 200: 10,360 | x0 289: 10,182 | x0 418: 10,176.8 (x0 311 at q <= 350: 10,176.8) | flat above 300 |
| 21 (on hand 204) | 10,102 | 10,102 | x0 200: 10,072.7 | x0 200: 10,072.7 | x0 450: 10,066.3 | 450 preferred by $6 |
| 6 (on hand 375) | x0 0: 8,553.7 in every envelope | | | | pinned 438: 10,359 | the mean-world optimum is no order; the stochastic candidate bought 438 at 8,605 settled |

Objective and settlement reconcile: every envelope's `projected_cost` equals its mean-world settled cost
to the cent (nine rows per review). Freight per unit at the tiers: 200 units $4.00 + $0.75 order, 450
units $2.44 + $0.33, so the full load is $2.00 per unit cheaper; the twelve-period objective cannot see
it because every schedule inside the window needs the same three shipments, and the lot boundary is then
decided by carrying (a cent per unit-week) and the salvage haircut on end-of-plan stock ($1 per unit),
both of which favour "small now, large later". Only the small first order is ever executed; next review
the same window shows the same preference. Same snapshot re-solved with a landed-cost continuation term
(end-of-horizon stock up to one economic lot credited at landed cost less salvage and carrying): at 13
and 17 the optimum becomes 450 now on a 4-5 week cadence (450 / 450 / 450), the EOQ schedule, and the
"small now" envelope loses by $250-300. On G (two SKUs, 20-pallet loads) the same re-solve at the review
before a big load is recorded in J13.

Classification per stage 12: **D, with a proven planner defect** - the finite-horizon terminal valuation
of the planner's objective (end-of-plan stock at the declared salvage, `terminal_continuation` off) is
inconsistent with lumpy replenishment economics, so the plan defers the large lot and executes a small
one; not A (the full-load candidate is generated), not B (the selector followed the solve), not C
(freight modelled and settled correctly).

## J13. Freight-cap / load audit (stage 13)

From the 45 run cells on G, I and T (all five policies, three seeds): no period-0 load exceeds the
supplier's maximum (450 units on I, 2,000 on G, 1,920 on T); every ledger FREIGHT total equals the sum
of the tier charges implied by the executed loads (I: four $800 and twelve $1,100 loads = $16,400 for
ZAAD seed 41001); ORDERING equals the order count times the fixed order cost; no fractional shipment
economics (tiers are integer per shipment in the model, `freight_tier` binaries, and per shipment in the
settlement). The MOV / case / pallet interactions on T reconcile as on the legacy run (attribution
60 / 60). Objective-to-settlement reconciliation at the I decisive reviews: exact (J12).

## J14. The correction (stage 14; `zaad/full/lotsizing.py`, planner wiring, `lot_terminal_valuation`)

Smallest general correction to the proven defect: on a review the P1 purchasing planner owns, and only
there, end-of-plan stock and committed arrivals are valued in every candidate solve and in every
candidate evaluation at the landed cost of the purchase they avoid, less carrying and cost of capital
until consumption, never below salvage: the benchmark's own rule B' applied ex ante.

* `reference_lots(req, fits)`: per supplier, the economic lot = min(load limit, max(EOQ on the supplier's
  fixed order cost and fee, MOQ, MOV in units, one period of demand)) and the order-level cost per unit
  of that lot (fixed order cost + shipment tariff at that load + receiving) / lot. I: 450 units, $2.78;
  G / T: 2,000 / 1,920 units, $0.80 / $0.90; B: the EOQ 1,854 units, $0.13; suppliers without
  order-level economics: premium 0.
* `landed_unit_costs`: per SKU, unit price + per-unit freight and handling + the premium of its cheapest
  approved source's supplier. `terminal_terms`: per SKU / location, (this line's share of one lot,
  landed - salvage - carrying and capital over half the lot's consumption time), floored at zero;
  passed to `model.solve(continuation=...)`, the existing bounded-continuation mechanism (end-of-horizon
  stock and committed post-horizon arrivals may earn the margin; new purchases landing after the horizon
  never do). No change to `model.py`.
* `planner.evaluate(..., terminal=, fits=)`: every candidate, incumbent, stress, confirmation and
  materiality row of a P1-owned review carries the same landed-cost continuation adjustment
  (`terminal.py`, `landed=`), recorded in the row's ledger as `terminal_continuation` under
  INVENTORY_VALUE_CHANGE so components still reconcile to the cent. The settlement itself is unchanged.
  The screening row that feeds ownership (`incumbent_screen_rows`) is unadjusted.
* Contract flag `lot_terminal_valuation` (default on, documented); orchestration reports
  `p1_terminal_landed`. A P0-owned review is untouched: the term is built after the router's decision
  and the frozen path never sees it (J15).
* Tests (`tests/unit/test_zaad_lotsizing.py`, 6): reference lot under a cap = the full load; = the EOQ
  without one; no premium without order-level economics; margin formula and zero floor; the J12 review-17
  snapshot flips from 166 to 450 now on a 4-5 week cadence; the term is reported on a P1-owned review,
  absent with the flag off and absent on a P0-owned (stressed) review. Ownership test 12 (routing
  bit-identity) now runs with the flag off on both sides, because the valuation is the declared change.
  Full unit suite 1,502 passed, 2 skipped.

Not done, by the brief: no fixture-specific logic, no quantity tuning, no benchmark change, no baseline
change, no tolerance change; the selector, materiality, router, candidate matrix, sampler and order
smoothing are untouched.

## J15. Regressions after the correction (stage 15)

Declared benchmark (rolling horizon, 52 reviews, B'; `closure/horizon52_lot.jsonl`, 300 cells, 1,526 s;
`P1_HORIZON_CONVERGENCE_lot.md`; the pre-correction tables kept as `*_frozen_policy.*`):

| fixture | before (J9) | after | class after | ZAAD orders / EOQ orders (seed 41001) |
|---|---|---|---|---|
| I | +7.14% FAIL | **+0.57% PASS**, stable (.14 pp) | A | 12 x 450 on the EOQ cadence / 12 x 450 |
| G | +6.18% FAIL | **+0.46% PASS**, stable (.88 pp) | C (boundary-sensitive, converges to pass) | 7 / 7 |
| T | +6.87% FAIL | **+2.06% FAIL** (seeds -1.02 / +1.99 / +5.24), stable (.38 pp) | D | 7 / 7 on seed 41001; 12 / 7 on 41003 (J16) |
| B | +2.49% FAIL | +2.49% unchanged, non-convergent | E | 8 / 3 (J16) |
| C | +0.30% | +0.46% PASS | C | |
| A, D, E, F, H, J, K, L, M, O, P, Q | all PASS | all PASS (largest move P +0.16 -> +0.40, H -1.27 -> -1.53) | A | |
| N, R | inside tolerance, proven invalid | same | | |
| S | invalid at 52 | invalid at 52 | | |

Valid fixtures 17; passing 15 / 17 (from 13 / 17). The declared rule and the BSI ordering are unchanged
by the correction (B' .453, B .922, A 1.665; baseline-only pairs .426 / .795 / 1.391), as they must be:
the benchmark was fixed before the policy. Runtime, ZAAD reviews: p50 .97 s, p90 4.4 s, p95 6.6 s, max
79 s (the correction removes time from the D and H cells: 6,063 s of cell wall against 8,775 s).

Legacy twelve-week record under the correction (`fixtures_product_defaults_lot.jsonl`,
`P1_RESULT_TABLE_none_product_defaults_lot.md`; the earlier record untouched): 18 / 20 pass, only N and
R (`categories`, proven invalid) fail. C +1.88% (was +3.61%), I +0.08% (was +0.53%), S +0.26%, P -0.29%,
A +0.27%, O +0.98%, Q +0.85%; the legacy double-digit wins shrink where ZAAD now buys the larger lot that
the twelve-week salvage ledger haircuts (G -3.98% from -10.0%, T -3.97% from -11.5%; B / J / K / L
unchanged at -10.7 / -11.1 / -11.2 / -10.2%). Attribution partitions 60 / 60.

P0 six-cell gate after the correction (`closure/p0_arm_router_lot.json`, run alone): J15a below.

## J15a. P0 six-cell gate after each change (run alone; `scripts/p1_ownership_compare.py` against `closure/p0_arm_clean_reference.json`)

| arm | code state | decision-identical P0-owned reviews | note |
|---|---|---|---|
| `router_passj` | after the opt-in rolling replay mode, before the correction | **120 / 120**; every cell's cost, service and unmet equal | the legacy replay path is bit-identical |
| `router_lot` | after the correction | 110 / 120: cells 15, 16, 20, 90, 108 identical (12 / 12, 12 / 12, 20 / 20, 26 / 26, 30 / 30); cell 21 diverges at r5 with identical requested / built / selected / chosen sets and the same unmet, a different period-0 quantity from the chosen `joint_recovery` candidate (42.4 against 50.1) | cost 3,331 -> 3,366 |
| `router_lot_rerun21` | same code, cell 21 alone | 11 / 20, first divergence r5 again, cost 3,404 | same code, a third value: run-to-run variability |
| `router_lot_off21` | cell 21 alone with `lot_terminal_valuation=False` | 6 / 20, first divergence r4, cost 3,364 | the variability is independent of the change |

All 120 P0-owned reviews are P0-owned under the router in every arm (owners `PROTECTION_RECOVERY` 12 /
12 / 20 / 20 / 26 / 30), no P1 class is added, no P1 terminal term is built (`p1_terminal_landed` is None
on every one), and no required candidate is starved. Cell 21's `joint_recovery` solve is a wall-clock-
limited recovery solve whose incumbent varies with the machine's timing on identical inputs, the same
frozen numerical variability recorded for cells 20 / 21 / 90 in passes H and I (`router_passj` matching
20 / 20 was one draw). With the flag off the cell diverges as much: the correction is not the cause.
P0 isolation therefore holds at decision level on every architectural quantity; the P0 gate is unchanged.

## J16. What remains after the correction, and why (stage 10 revisited on the corrected run)

**T (+2.06% at 52 on the corrected run; seeds -1.02 / +1.99 / +5.24).** On seed 41001 ZAAD now buys the
seven 20-pallet loads the EOQ baseline buys and is 1% cheaper. Seed 41003 still carries seven small
orders (192 + 120 units: the incumbent's weekly replace-sold lifted to the $1,500 MOV) beside five big
loads. Traced (`closure/forensics_T_combined_realistic_41003.json`, per-review ownership from the run):

* five of the seven sit inside P0-owned stretches (reviews 16-25, 29-35, 39-43: an active demand driver
  on this seed's path hands the review to the frozen protection path), and every one is a
  RETAIN_INCUMBENT outcome there: the frozen path retains the operator's declared weekly order. The
  frozen path never had order-level economics; on a purchasing fixture it executes the incumbent's lot
  pattern for as long as the driver stays active.
* the other two (reviews 9 and 47) are P1-owned RETAIN_INCUMBENT outcomes with the reason
  "Out-of-model stress confirmation rejected physical feasibility, downside risk, or required service
  recovery": at review 9 every candidate (deterministic, stochastic, cadence 2 and 4) proposed the
  1,056 + 864 load at hedged cost 14,352 against the incumbent's 23,314, the confirmation under the
  declared nil stress rejected it, and the same load was accepted one review later. The same outcome
  appears once on G (review 37) and twice on B (reviews 4 and 41).

Both are P0-gate semantics on P1-owned or P0-owned reviews of a purchasing fixture, not lot-sizing
economics; the brief's rule ("do not reopen the planner router unless this pass uncovers a real
semantic defect") is respected: the evidence is recorded here for that decision, and nothing in the
router, the stress confirmation or the materiality gate was changed. Classification: C ORDER TIMING via
G OTHER (frozen-path ownership and out-of-model confirmation on a purchasing review).

**B (+2.49% at 52, non-convergent).** The correction changes nothing on B (bit-identical trajectory):
B's economic lot is 1,854 units, 18.6 weeks of demand, longer than the twelve-period planning horizon,
so no twelve-week plan contains the second order whose $250 the larger lot would save, and the terminal
credit (landed $5.13 against a $5 purchase, less carrying) cannot make holding 760 extra units for a
saving outside the window worthwhile. ZAAD's lots are 55% of the EOQ (767 against 1,884 units), eight
orders against three, plus two retained 100-unit incumbent orders (the confirmation outcome above).
Classification: A LOT-SIZING via E HORIZON: a planning horizon shorter than the economic lot cycle. A
general remedy is a planning horizon at least one lot cycle long (a product horizon design question,
not a fixture patch); the fixture is also non-convergent at 52 reviews by the pre-registered criterion
(2.8 cycles in a year, delta range 1.44 pp over 40-52), so the benchmark itself cannot settle B at the
declared endpoint to within a point.

**S** proven invalid at the declared benchmark (J7). **N / R** proven invalid (categories), inside
tolerance. **C** resolved by the benchmark (+0.46%). **I, G** resolved by the correction.

## J15b. FINAL-CODE reruns (authoritative; supersede J15 and every earlier post-fix table)

The ledger key of J14 (evaluation rows carry `terminal_continuation` under INVENTORY_VALUE_CHANGE) reaches
the materiality gate, which reads the component total; it moved A, P and O by a few tenths of a point
and nothing else. Both A-T runs were therefore repeated on the final code: `closure/horizon52_final.jsonl`
(300 cells, 1,503 s) and `fixtures_product_defaults_final.jsonl` (`P1_RESULT_TABLE_none_product_defaults_final.md`).
The one authoritative table, with the pre-fix record beside it, is `P1_FINAL_RESULT_TABLE.md`
(`scripts/p1_final_table.py`, `P1_FINAL_SUMMARY.json`); the convergence tables for the final run are
`P1_HORIZON_CONVERGENCE_final.md` (pre-fix: `*_frozen_policy.md`; intermediate: `*_lot.md`).

| fixture | legacy PRE-FIX | legacy FINAL | declared PRE-FIX @52 | **declared FINAL @52** | FINAL verdict |
|---|---|---|---|---|---|
| A | +0.43% | +0.27% | +0.87% | +0.81% vs incumbent | PASS, stable |
| B | -10.70% | -10.70% | +2.49% | **+2.49%** vs EOQ | FAIL, non-convergent (1.44 pp) |
| C | +3.61% | +1.88% | +0.30% | +0.46% vs reorder_point | PASS |
| D | -0.58% | -0.51% | +0.63% | +0.66% | PASS |
| E | -0.00% | +0.00% | -0.10% | -0.01% | PASS |
| F | +0.24% | +0.30% | +0.72% | +0.70% | PASS |
| G | -10.01% | -0.98% | +6.18% | **+0.46%** vs EOQ | PASS |
| H | -3.73% | -5.00% | -1.27% | -1.67% | PASS |
| I | +0.53% | +0.08% | +7.14% | **+0.57%** vs EOQ | PASS |
| J | -11.06% | -11.06% | +0.15% | +0.15% | PASS |
| K | -11.20% | -11.20% | +0.15% | +0.15% | PASS |
| L | -10.16% | -10.16% | +0.81% | +0.81% | PASS |
| M | -0.54% | -1.11% | +0.05% | -0.17% | PASS |
| N | -0.71% | -1.08% (categories) | +1.07% | +0.61% | proven invalid, inside tolerance |
| O | +0.46% | +1.04% | +0.09% | +0.21% | PASS |
| P | +0.29% | +0.41% | +0.16% | +0.35% | PASS |
| Q | +0.85% | +0.85% | +0.19% | +0.17% | PASS |
| R | -0.05% | -0.02% (categories) | +0.65% | +0.55% | proven invalid, inside tolerance |
| S | +0.26% | +0.26% | invalid | invalid at 52 (to W = 12) | proven invalid at the declared benchmark |
| T | -11.47% | -3.97% | +6.87% | **+2.06%** vs EOQ (seeds -1.02 / +1.99 / +5.24) | FAIL, stable (.38 pp) |

Legacy final: 18 / 20 (N, R categories). Declared final: valid 17, passing 15, failing B and T. Service
on every valid fixture at or above its legacy level; A abstains on 18 of 156 reviews (legacy 4 of 33).
Runtime, ZAAD reviews: p50 .96 s, p90 4.3 s, p95 6.5 s, max 79 s. Unit suite on the final code: J17.

## J16b. B classification (stage 5 of the continuation)

B fails the declared benchmark (+2.49%) and is non-convergent by the pre-registered criterion. Ownership
decomposition (`scripts/p1_t_decomposition.py`): seeds +2.99 / +0.51 / +3.99%; ZAAD 5-9 orders against
EOQ's 3; sub-economic orders are 100-unit RETAIN_INCUMBENT outcomes (the confirmation mechanism of J16)
plus 800-900-unit lots that are half the EOQ. Classification: **B, planning-horizon limitation** (the
economic lot of 18.6 weeks exceeds the twelve-period planning horizon, so no plan can contain the second
order whose fixed cost a full EOQ lot saves; the landed terminal credit cannot represent a saving that
falls outside the window), compounded by **A, benchmark design** at this endpoint (2.8 lot cycles in a
year; delta range 1.44 pp over 40-52 under the declared rule). Not a policy defect the current planner
can address without a longer planning horizon; not fixed in this continuation, per the brief.

## J16c. T on the final code: decomposition and classification (continuation brief, stages 3-4)

Final-code T: +2.06% (seeds -1.02 / +1.99 / +5.24%), stable (.38 pp). Ownership decomposition
(`scripts/p1_t_decomposition.py` on `closure/horizon52_final.jsonl.gz`; per-review ledger differences by
the owner of ZAAD's review, terminal credit difference as the boundary part; reconciles to the gap to
1e-6 on every seed):

| seed | gap | P1-owned reviews | P0-owned reviews | terminal / boundary | ZAAD orders (P0-owned reviews) / EOQ orders |
|---|---|---|---|---|---|
| 41001 | -657 (-1.02%) | +2,702 | -5,390 | +2,030 | 7 (2) / 7 |
| 41002 | +1,250 (+1.99%) | +22,213 | -19,937 | -1,026 | 7 (11) / 6 |
| 41003 | +3,331 (+5.24%) | +11,998 | -9,333 | +666 | 12 (19) / 7 |

The per-review ledger split is dominated by purchase timing (the two trajectories buy in different
weeks), so the informative partition is by shipment: ZAAD's nine sub-economic orders (312-384 units at the
$800 tier plus $200 order and $25 receiving, $1,025 each, against $1,725 for a 1,920-unit load) are the
whole excess. Traced with the gate detail (`closure/forensics_T_combined_realistic_4100{1,2,3}.json`):

| seed, review | owner (router reason) | state / status | what happened |
|---|---|---|---|
| 41001 r46 | P0 (B@branch inherited protection under management, FALSE_PROTECTION_RISK) | NO_ACTION / PENDING_REVIEW | frozen objective (no lot valuation) chose the 72 + 240 deferral candidate, $100 cheaper than the 888 + 864 load on the twelve-week plan: J12 mechanism on a P0-owned review |
| 41002 r36 | P0 (A@branch FALSE_PROTECTION_RISK) | NO_ACTION / RETAIN_INCUMBENT | candidate deferred; stress gate rejected; incumbent's 192 + 120 executed |
| 41003 r9 | **P1** (calm, no driver) | NO_ACTION / RETAIN_INCUMBENT | every candidate proposed 1,056 + 864; stress gate ("nil") rejected on `within_downside` only: physically usable, service met (.964 / .969 against the .95 target), cost 14,790 against the incumbent's 23,423 on every world, but below the incumbent's 1.000 service on the stress worlds (per-service no-worse floor, planner line 1143) |
| 41003 r20 | P0 (B@branch FALSE_PROTECTION_RISK) | NO_ACTION / PENDING_REVIEW | frozen objective chose 120 + 264 over the 840 + 1,080 cadence candidate |
| 41003 r21, r22, r25 | P0 (FALSE_PROTECTION_RISK) | NO_ACTION, CAPITAL_OPTIMIZATION / RETAIN_INCUMBENT | candidate deferred or full load; stress gate rejected; incumbent's 312 executed |
| 41003 r40 | P0 (screen PROTECT) | PROTECT / RETAIN_INCUMBENT | as above |
| 41003 r47 | **P1** (calm, no driver) | NO_ACTION / RETAIN_INCUMBENT | cadence candidates proposed 936 + 984; chosen deterministic deferred; stress gate rejected; incumbent's 312 executed |

Partition of the nine: seven are RETAIN_INCUMBENT outcomes of the declared-stress gate's per-service
no-worse-than-incumbent floor on the nil stress (two on P1-owned reviews, five on P0-owned), two are
frozen-objective deferrals on P0-owned reviews. The P1-owned share (two orders on one seed, about $1,500
net on that seed, about 0.8 pp of the seed mean) would not on its own take T outside tolerance; the
P0-owned share (seven, about 2.7 pp) would.

Two semantic findings, recorded for decision and NOT changed here:

1. **FALSE_PROTECTION_RISK ownership on P1 lots.** After each full load the stock sits far above the lean
   baseline; the protection machinery reads that as inherited protection under management, the router
   (pre-registered rule: any flag or driver -> P0) hands the next reviews to the frozen path, and the
   frozen objective, which has no lot valuation, reproduces the J12 deferral there. A cycle-stock lot is
   being classified as protection.
2. **The stress gate's per-service floor on purchasing reviews.** Under a declared nil stress the
   "stress" worlds are fitted worlds, and the rule that a candidate may not serve less than the incumbent
   on them, even above target, structurally prevents any lot plan from replacing a weekly-ordering
   incumbent whenever the fitted draw shows a fraction of a point of shortfall. It applies on P1-owned
   reviews as it does on P0-owned ones; it is P0 acceptance machinery (V6 / V7 floors).

Classification per the continuation's decision tree: **CASE T3, P1 / FROZEN-P0 COMPATIBILITY BLOCKER**.
The router's ownership is what the pre-registered rule says it is, with the information at decision time;
the material part of the gap sits on P0-owned reviews and the P1-owned part comes from the same P0 gate
rule. No P0 or gate code was modified; T is not waived. B: J16b (planning horizon shorter than the lot
cycle; not fixed). No further optimizer change was made in this continuation (one-fix limit: the
lot-sizing terminal valuation is the one general correction of pass J).

## J17. Freeze gate (continuation brief, stage 9) and verdict

| # | requirement | state |
|---|---|---|
| 1 | planner-boundary architecture accepted | yes (I2-I4, J15a) |
| 2 | benchmark pre-registered and stable | yes: `P1_BENCHMARK_PREREGISTRATION.md`; 18 / 19 fixtures stable under the declared rule (B non-convergent) |
| 3 | final benchmark tests pass | 12 / 12 |
| 4 | P0 isolation safe | yes: final-code arm 120 / 120 decision-identical (`closure/p0_arm_router_final.json`) |
| 5 | required starvation zero | yes, every arm |
| 6 | P <= 2% | +0.35% |
| 7 | C <= 2% | +0.46% |
| 8 | I <= 2% | +0.57% |
| 9 | O <= 2% | +0.21% (service floor .80 met: .980) |
| 10 | B passes if valid | **NO: +2.49%, non-convergent** (J16b) |
| 11 | S valid and passing, or invalidity proven | invalidity proven: declared receivables below every policy's cash-out; no policy completes the year (J7) |
| 12 | T passes if valid | **NO: +2.06%** (J16c, compatibility blocker) |
| 13 | A preserves meaningful abstention | yes: 18 abstentions / 156 reviews, +0.81% |
| 14 | G / Q safe | G +0.46%, Q +0.17% |
| 15 | all other valid fixtures pass | yes (D, E, F, H, J, K, L, M) |
| 16 | N / R preserved honestly | yes (categories fail as recorded; costs inside tolerance) |
| 17 | no fixture-specific code | none |
| 18 | no widened tolerance | 2% (3% on Q, S as declared) |
| 19 | no arbitrary buffer | none |
| 20 | freight accounting reconciles | yes (J13, 45 cells) |
| 21 | terminal accounting reconciles | yes: evaluation rows reconcile to the cent with the `terminal_continuation` key; realised ledger untouched (stage 8 check) |
| 22 | materiality uses consistent economics | yes: materiality reads the same adjusted rows (the reason for the final-code rerun) |
| 23 | tests | 1,502 passed, 2 skipped (unchanged skip count) |
| 24 | invariants | 720 / 720 (`P1_INVARIANTS.json`; pass-I record kept as `_pass_i`) |
| 25 | runtime | p50 .96 s, p95 6.5 s, max 79 s per ZAAD review at full horizon |
| 26-28 | Validation7 / Validation8 / holdout4 | untouched, unrun |
| 29 | Network Twin / frontend / Vercel | untouched |

**Verdict: P1 CORE ARCHITECTURE PASS — T (P1 / FROZEN-P0 COMPATIBILITY: FALSE_PROTECTION_RISK
ownership of cycle-stock lots and the stress gate's per-service floor on purchasing reviews) AND B
(PLANNING HORIZON SHORTER THAN THE ECONOMIC LOT CYCLE) REMAIN OPEN.** Not frozen. P2 NOT STARTED —
P1 FREEZE GATE NOT MET.

## J18. State after pass J

Product defaults changed: `lot_terminal_valuation=True` (P1-owned reviews only). Evaluation-only
additions: rolling replay mode, stitched truth, endpoint scoring, landed-cost continuation. The declared
P1 benchmark is the rolling 52-review landed-cost evaluation; the legacy twelve-week record is kept and
reported beside it. `claude/zaad-meio-p2` does not exist.

# Pass K: two-blocker closure, T and B (2026-09-09; from 4f49322)

Pre-registration: `P1_TWO_BLOCKER_PREREGISTRATION.md` (rules T-A, T-B, B-A written before any run;
dated notes appended after). Benchmark unchanged: the declared rolling 52-review landed-cost evaluation.

## K1. T: where FALSE_PROTECTION_RISK comes from (stage T1; `scripts/p1_flag_trace.py`, `closure/flag_trace_*.json`)

`protection.py`: the flag is `activity <= .05 and protection > 1.25 * lean_baseline + 1`, where protection
is the quantile recommendation on the fitted spread WITH calibration widening, level error, observed
supply spread and open orders at late risk, and the lean baseline is the same recommendation on the fitted
spread and the declared supply spread. No inventory field enters it: not on-hand, not pipeline, not
inherited stock, not the previous action. Traced on T: every flagged SKU-review has zero units in the
pipeline and on-hand anywhere between 116 and 1,036; the ratio (1.41-1.53 at reviews 16 / 20 / 24 of seed
41003) equals the demand forecast's calibration ratio to two decimals (realized one-step errors 8.8-9.5
against a fitted spread of 6.2, regime age none, level error about 1 unit), below the threshold at which
calibration becomes an active demand driver. The flag on T is a forecast-calibration state. Occurrence:
A, I, P never; G once in 52 reviews; T 2 / 14 / 18 SKU-reviews per seed; P0 cells 15, 16, 20 never, cell 21
twice with ratio 8 (a real supply driver, and the cell is P0-owned by its declared mandate anyway).

## K2. T: provenance state (stage T2) and the two pre-registered rules (stages T3, T5)

No new provenance state: protection or recovery stock exists only downstream of PROTECT / RECOVER
decisions, and every such situation is canonical state the router already reads (active or decaying
driver, non-LEAN regime, confirmed decline, non-calm state, mandate, recovery obligation); cycle stock is
stock held while all of those are absent. **Rule T-A** (`ownership.py`): FALSE_PROTECTION_RISK alone is not
an ownership reason; it is reported as a note; P0's own machinery still uses the flag whenever P0 owns.
**Rule T-B** (`planner.py`): on a P1-owned review every gate that compares a candidate with the incumbent
uses the target service basis (a candidate meeting every target has not worsened service); on a P0-owned
review the basis is exactly the request's own rule as before. Ownership is now decided before the basis,
still from the snapshot only; the report carries `gate_basis` and `ownership_notes`. Mapped gate (stage
T4): at T 41003 review 9 the lot candidate was physically usable, met service (.964 / .969 against .95) and
cost 14,790 against the incumbent's 23,423 on every fitted world, and was rejected only because the
weekly-ordering incumbent served 1.000 there. Tests: `tests/unit/test_zaad_protection_provenance.py` (8:
flag alone stays P1, real protection routes to P0, protection accounting bounded on the family,
deterministic flag, the review-9 snapshot now accepts the load under the target basis, a P0-owned review
keeps the incumbent basis, a credible declared stress keeps P0 and its floor, routing and basis are
snapshot-pure); pass-I ownership test 5 rewritten to rule T-A.

## K3. T under the rules (stage T7; `closure/horizon52_tA.jsonl`)

| | before (J15b) | after |
|---|---|---|
| delta @52 vs EOQ | +2.06% (seeds -1.02 / +1.99 / +5.24) | **-0.57%** (seeds -2.23 / +0.56 / -0.01) |
| stable (max dev 40..52) | yes (.38 pp) | yes (.76 pp) |
| orders per seed (EOQ 7 / 6 / 7) | 7 / 7 / 12 | 6 / 6 / 7 |
| sub-economic orders | 9 | 1 (41003 review 40: PROTECT regime, P0-owned by regime, incumbent retained) |
| P1 / P0 owned reviews | 124 / 32 | 153 / 3 |
| service | .999 | 1.000 / .997 / .999 |
| actions / abstentions | 149 / 0 | 155 / 0 |

Every remaining order is a 1,700-2,000-unit load on the EOQ cadence except the one PROTECT review.
Ownership decomposition (`scripts/p1_t_decomposition.py`): seed means gap -362 = P1 -3,879 + P0 +874 +
terminal +2,643; shipment part P1 -1,150 (ZAAD ships less than EOQ), P0 +342 (the one retained order).

## K4. Controls (stage T8; `closure/horizon52_tA_controls.jsonl`)

| fixture | before | after | stable | P1 / P0 owned before -> after | abstentions | service |
|---|---|---|---|---|---|---|
| A | +0.81% | +0.89% | yes (.24) | 138 / 18 -> 153 / 3 | 21 | .989 |
| G | +0.46% | -1.02% | yes (.50) | 125 / 31 -> 151 / 5 | 0 | .998 |
| I | +0.57% | +0.24% | yes (.45) | 137 / 19 -> 153 / 3 | 0 | 1.000 |
| P | +0.35% | +0.59% | yes (.19) | 138 / 18 -> 152 / 4 | 23 | .992 |
| Q | +0.17% | +0.17% | yes (.04) | 69 / 87 -> 72 / 84 | 2 | .991 |
| C | +0.46% | +0.13% | yes (.14) | 137 / 19 -> 153 / 3 | 0 | 1.000 |
| O | +0.21% | +0.12% | yes (.13) | 96 / 60 -> 108 / 48 | 18 | .980 |

Ordinary large lots on G and I no longer hand reviews to P0; Q and O keep most of their P0 ownership
(real demand drivers on those paths). A still abstains (21 of 156).

## K5. B (part II)

Under rules T-A / T-B alone B is **+1.60%** at the base horizon (from +2.49%: its two 100-unit
RETAIN_INCUMBENT orders were the gate floor), with the verdict PASS at every endpoint from 40 to 52
(range +0.05..+1.60, magnitude not inside the +/-1 pp band: class E by the pre-registered criterion, a
property of an 18.6-week cycle in a 52-week window). Diagnostic sweep of ZAAD's planning horizon
(`closure/horizon52_B_h{12,16,20,24,32}.jsonl`, baselines at 12): +1.60 / +0.15 / +0.59 / +1.57 / +2.21%
(32: one seed, 64 s median per review, stopped), first lots 1,071 / 1,478 / 1,870 / 2,281 / 1,613 against
the EOQ 1,854, magnitude-stable only at 20. The pre-registered derived horizon (lead 1 + cycle 19 + 1 = 21)
sits in the passing region, but the first lot moves by a fifth between 20 and 24 (overshoot past the EOQ
once more than one cycle is visible) and solve time grows with the square of the horizon (max 44 s at 20,
116 s at 24). Per the brief ("if B passes the declared benchmark: record limitation and move on") and the
pre-registered condition for a horizon redesign (B a valid, economically material freeze blocker, which it
no longer is), rule B-A is NOT implemented; the sweep is the recorded limitation: planning horizon shorter
than the lot cycle costs B about 1-1.5 points against an EOQ buyer, and a visibility horizon of one lot
cycle would recover most of it at 5-10x the solve time on such fixtures.

## K6. Rule T-B rejected; final code is rule T-A only

The full A-T under T-A + T-B (`closure/horizon52_tA_full.jsonl.gz`, `fixtures_product_defaults_tA.jsonl`,
`P1_FINAL_RESULT_TABLE_tA.md`) closed T (-0.57%), G (-1.02%), I (+0.24%), C (+0.13%) and moved B to
+1.60%, but created a valid failure: A intervened on 12 of 33 legacy reviews (36%) and 46 of 156
declared reviews against its pre-registered "mostly abstain" expectation (at most a quarter), through
three capital tie-break and three "next qualified candidate" acceptances of leaner plans that serve less
than the incumbent (.986 against .992) at +0.80% cost; Q's legacy service fell from .980 to .965 against a
.98 target (declared benchmark unchanged, .991). By the brief's rule ("if it creates another valid
failure: reject it; do not continue patching") T-B was reverted: the gate basis is the request's own on
every review, reported as `gate_basis`; rule T-A (the flag is not an ownership reason) stands. The
narrower candidate (target basis on the disruption stress-gate floor only; capital tie-break retired
where the terminal valuation already prices closing stock) is recorded, not applied.

## K7. Final code (rule T-A only): A-T, legacy, P0 (`closure/horizon52_tAonly.jsonl.gz`, `fixtures_product_defaults_tAonly.jsonl`, `P1_FINAL_RESULT_TABLE_tAonly.md`, `P1_HORIZON_CONVERGENCE_tAonly.md`)

| fixture | pass J final (4f49322) | **final (T-A)** | verdict | stable |
|---|---|---|---|---|
| A | +0.81% | +0.81% | PASS (21 abstentions / 156; legacy action check passes) | yes (.22) |
| B | +2.49% | **+2.66%** vs EOQ | **FAIL** (PASS at 40-44, FAIL from 45; rising) | NO (1.77 pp) |
| C | +0.46% | +0.39% | PASS | yes |
| D / E / F | +0.66 / -0.01 / +0.70% | +0.65 / -0.02 / +0.80% | PASS | yes |
| G | +0.46% | **-0.76%** | PASS | yes (.72) |
| H | -1.67% | -1.97% | PASS | yes |
| I | +0.57% | **+0.07%** | PASS | yes (.12) |
| J / K | +0.15 / +0.15% | +0.34 / +0.34% | PASS at 52 and every endpoint 40-52; magnitude 1.25 / 1.28 pp (one dip to -0.9 at 44) | NO |
| L | +0.81% | +1.07% | PASS | yes (.54) |
| M / O / P / Q | -0.17 / +0.21 / +0.35 / +0.17% | -0.17 / +0.13 / +0.29 / +0.17% | PASS | yes |
| N / R | inside tolerance, proven invalid | +0.61 / +0.59%, proven invalid (kept) | | yes |
| S | invalid at 52 | invalid at 52 | | |
| T | **+2.06% FAIL** | **-0.28% PASS** (seeds -2.17 / +0.62 / +0.70) | PASS | yes (.86) |

Legacy record: 18 / 20 (N, R categories). Ownership: P0-owned reviews 3 / 156 on every fixture except
M (144, order calendar with an active supply driver), Q (84), O (48), all real drivers. B's remaining
mechanism: seven 100-unit RETAIN_INCUMBENT orders across the seeds (the incumbent-level stress-gate floor
on P1-owned reviews, the target of the rejected T-B) and lots at about 55% of the EOQ (planning horizon
shorter than the 18.6-week lot cycle, K5). Per the brief's B classification: mixed, gate-floor (the T-B
candidate) and planning-horizon limitation (the B-A candidate); the horizon redesign is not authorized
because the failure is not convergent at the declared endpoint (verdict flips inside 40-52). P0 six-cell
arm on the final code (`closure/p0_arm_router_tAonly.json`, run alone): cells 15, 16, 20, 90, 108
decision-identical (108 30 / 30 after a hedged-candidate time-out in the T-A + T-B arm, rerun alone
`router_tA_rerun108`), cell 21 10 / 20 at its recorded wall-clock variability (cost 3,366, the same value
as in three earlier arms); ownership 100% P0 on every cell, no P1 class added, starvation zero. Tests:
1,510 passed, 2 skipped (8 new); invariants 720 / 720. Runtime p50 1.0 s, p95 6.3 s, max 67 s.

## K8. Freeze gate (continuation brief, stage 9) and verdict

| # | requirement | state |
|---|---|---|
| 1 | planner boundary semantically correct | yes; rule T-A removes a forecast-calibration flag from ownership |
| 2 | economic cycle stock no longer enters protection ownership | yes: G / I / T P0-owned reviews 31 / 19 / 32 -> 3 |
| 3 | real protection still does | yes: Q 84, O 48, M 144 P0-owned; synthetic states tested |
| 4 | P0 stress gate frozen inside P0 | yes (T-B reverted; basis unchanged everywhere) |
| 5 | P1 nil-stress decisions not vetoed by P0-only risk semantics | **NO**: the incumbent-level floor still vetoes lot plans on P1-owned reviews (B: seven retained 100-unit orders); the rule that lifts it (T-B) was rejected on A / Q |
| 6 | T <= 2% | yes, -0.28% |
| 7 | adaptive horizon economically derived | not implemented (K5; not authorized) |
| 8 | B <= 2% | **NO: +2.66%**, verdict flips inside 40-52 |
| 9 | horizon decisions stable | n/a (no adaptive horizon) |
| 10 | runtime | p50 1.0 s, p95 6.3 s, max 67 s |
| 11 | P0 six-cell isolation | 110 / 120 with cell 21 variability classified |
| 12 | starvation zero | yes |
| 13-16 | P, C, I, O | +0.29, +0.39, +0.07, +0.13% |
| 17 | G / Q / A safe | -0.76 / +0.17 / +0.81%, A abstains 21 / 156 |
| 18 | every valid A-T fixture passes | **NO: B** |
| 19-20 | N / R, S | preserved |
| 21-23 | no fixture logic, no widened tolerance, no buffer | none |
| 24 | economics reconcile | yes (K7 tables reconcile; evaluation rows carry the terminal key) |
| 25-26 | tests, invariants | 1,510 passed / 2 skipped; 720 / 720 |
| 27-30 | Validation7 / 8 / holdout4 / Network Twin, frontend, Vercel | untouched |

**Verdict: P1 CORE ARCHITECTURE PASS — B (INCUMBENT-LEVEL STRESS-GATE FLOOR ON P1-OWNED PURCHASING
REVIEWS, AND A PLANNING HORIZON SHORTER THAN THE ECONOMIC LOT CYCLE) REMAINS OPEN.** T is closed by rule
T-A. Not frozen. P2 NOT STARTED — P1 FREEZE GATE NOT MET.
